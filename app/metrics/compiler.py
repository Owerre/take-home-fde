"""metrics compiler."""

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from app.config import Settings
from app.domain.errors import QueryError, RequestError
from app.domain.models import (
    Answer,
    Dimension,
    Metric,
    MetricRequest,
    Order,
    ResponseKind,
    RunReport,
    SqlValue,
)
from app.infrastructure.database import execute_bounded, fetch_one, read_connection
from app.metrics.catalog import definition
from app.metrics.validation import validate_request


@dataclass(frozen=True)
class CompiledMetric:
    sql: str
    parameters: tuple[SqlValue, ...]


class MetricCompiler:
    """Own validated configuration, never accept arbitrary SQL identifiers."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def compile(self, request: MetricRequest) -> CompiledMetric:
        validate_request(request)
        d = definition(request.metric)
        if request.start_date and request.start_date > self.settings.as_of_date:
            raise RequestError(
                "Requested period starts after build reference date; change reference date."
            )
        parameters: list[SqlValue] = [self.settings.as_of_date]
        where = ["invoice_date <= ?"]
        if d.statuses:
            where.append(f"status IN ({','.join('?' for _ in d.statuses)})")
            parameters.extend(d.statuses)
        for bound, operator in ((request.start_date, ">="), (request.end_date, "<")):
            if bound:
                where.append(f"invoice_date {operator} ?")
                parameters.append(bound)
        for f in request.filters:
            where.append(f"{f.dimension.value} IN ({','.join('?' for _ in f.values)})")
            parameters.extend(f.values)
        table = "mart_accounts" if d.account_grain else "mart_invoices"
        evidence = "snapshot_invoice_id" if d.account_grain else "invoice_id"
        group = Dimension.ACCOUNT if request.metric == Metric.TOP else request.group_by
        key = f"{group.value} AS group_key," if group else ""
        group_clause = f"GROUP BY {group.value}" if group else ""
        measure = {
            Metric.PAID: "coalesce(sum(paid_revenue_usd), 0::DECIMAL(38,2))",
            Metric.REFUNDS: "coalesce(sum(refund_magnitude_usd), 0::DECIMAL(38,2))",
            Metric.NET: "coalesce(sum(net_revenue_usd), 0::DECIMAL(38,2))",
            Metric.TOP: "coalesce(sum(net_revenue_usd), 0::DECIMAL(38,2))",
            Metric.EXPOSURE: "coalesce(sum(amount_usd), 0::DECIMAL(38,2))",
            Metric.MRR: "coalesce(sum(account_mrr_usd), 0::DECIMAL(38,2))",
            Metric.CHURN: "count(*) FILTER (WHERE churned)",
        }[request.metric]
        extras = ""
        if d.account_grain:
            extras = (
                ", count(*) AS denominator, count(*) FILTER (WHERE active_proxy) AS active_accounts"
            )
        sql = (
            f"WITH population AS (SELECT * FROM {table} WHERE {' AND '.join(where)}), "
            f"aggregated AS (SELECT {key} {measure} AS total, "
            "count(*) AS contributing_invoice_count, "
            f"coalesce(list({evidence} ORDER BY {evidence})[:10], []) AS invoice_id_sample"
            f"{extras} FROM population {group_clause}) "
        )
        if request.metric == Metric.TOP:
            sql += (
                "SELECT g.*, a.csat_score, a.snapshot_invoice_id AS csat_snapshot_invoice_id "
                "FROM aggregated g LEFT JOIN mart_accounts a ON g.group_key = a.account_id "
            )
        else:
            sql += "SELECT * FROM aggregated "
        if d.account_grain:
            sql += "ORDER BY group_key ASC" if group else ""
        else:
            sql += f"ORDER BY total {request.order.value.upper()}"
            if group:
                sql += ", group_key ASC"
            sql += " LIMIT ?"
            parameters.append(request.limit)
        return CompiledMetric(sql, tuple(parameters))

    def answer(self, request: MetricRequest, report: RunReport) -> Answer:
        compiled = self.compile(request)
        if report.as_of_date != self.settings.as_of_date:
            raise QueryError("Build reference date differs from query configuration; rebuild.")
        with read_connection(self.settings.database) as connection:
            identity = fetch_one(connection, "SELECT build_id FROM build_metadata")[0]
            if identity != report.build_id:
                raise QueryError("Build changed during request; retry.")
            rows = execute_bounded(
                connection, compiled.sql, compiled.parameters, self.settings.query_timeout
            )
        d = definition(request.metric)
        for row in rows:
            total = row["total"]
            if not isinstance(total, (Decimal, int)):
                raise QueryError("Unexpected non-exact numeric result.")
            numeric_value = Decimal(total)
            value: Decimal | None = numeric_value
            if d.account_grain:
                denominator = row["denominator"]
                if not isinstance(denominator, int):
                    raise QueryError("Unexpected account denominator.")
                value = numeric_value / denominator if denominator else None
                if value is not None and request.metric == Metric.CHURN:
                    value *= 100
            row["value"] = value
            if request.metric == Metric.EXPOSURE:
                row["invoice_count"] = row["contributing_invoice_count"]
            if request.metric == Metric.TOP:
                score = row["csat_score"]
                row["low_csat"] = score <= 2 if isinstance(score, int) else None
        if d.account_grain:
            rows.sort(key=lambda r: str(r.get("group_key", "")))
            rows.sort(key=lambda r: decimal_sort(r["value"]), reverse=request.order == Order.DESC)
            rows = rows[: request.limit]
        budget = 50
        for row in rows:
            sample = row["invoice_id_sample"]
            if not isinstance(sample, list):
                raise QueryError("Invalid evidence sample.")
            bounded_sample = sample[:budget]
            row["invoice_id_sample"] = bounded_sample
            budget -= len(bounded_sample)
            row["sample_truncated"] = row["contributing_invoice_count"] != len(bounded_sample)
            row["evidence_kind"] = (
                "snapshot invoices" if d.account_grain else "revenue/exposure invoices"
            )
            display_value = row["value"]
            if isinstance(display_value, Decimal):
                row["value"] = display_value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        assumptions: tuple[str, ...] = (
            "Reference date inclusive; invoice dates, not payment dates, determine ledger timing.",
            f"Requested limit={request.limit}, order={request.order.value}; "
            "SQL parameters show filters.",
        )
        if d.account_grain:
            assumptions += (
                "Exact totals/denominators finalized and ranked locally using Decimal.",
            )
        caveats = (
            f"Build excluded {report.future_invoices} future invoices from answers.",
            f"Build has {report.conflicting_accounts} snapshots with conflicting attributes.",
            f"Systematic source FX pattern: {report.systematic_fx_rows} non-USD invoices; "
            "briefing FX applied.",
            f"Residual pricing discrepancies: {report.pricing_discrepancies}; "
            "billed amounts unchanged.",
            "Snapshot MRR is a paid/nonchurned proxy; "
            "churn is flag prevalence, not a historical event rate.",
            "Baseline account_id; alternate-key Q2/Q4/Q5 sensitivity: docs/decisions.md.",
        )
        return Answer(
            ResponseKind.METRIC,
            rows=tuple(rows),
            units=d.units,
            definition=f"{d.rule_id}: {d.description}",
            sql=compiled.sql,
            parameters=compiled.parameters,
            assumptions=assumptions,
            caveats=caveats,
            build_id=report.build_id,
            source_sha256=report.source_sha256,
            as_of_date=report.as_of_date,
        )


def decimal_sort(value: object) -> Decimal:
    if value is None:
        return Decimal("-Infinity")
    if not isinstance(value, Decimal):
        raise QueryError("Expected exact aggregate value.")
    return value
