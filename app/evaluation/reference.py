"""Independent reference-query loading and result comparison (E-OFF-01)."""

import re
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

from app.config import REFERENCE_SQL_FILE, Settings
from app.domain.models import Answer, Metric, MetricRequest
from app.infrastructure.database import execute_bounded, read_connection


def reference_queries(root: Path) -> dict[str, str]:
    text = (root / REFERENCE_SQL_FILE).read_text()
    pieces = re.split(r"-- (Q[1-6])\n", text)
    return {pieces[i]: pieces[i + 1].strip() for i in range(1, len(pieces), 2)}


def reference_rows(settings: Settings, case_id: str) -> list[dict[str, object]]:
    if case_id == "LIVE-FILTER":
        sql = (
            "SELECT coalesce(sum(amount_usd),0) AS total, "
            "count(*) AS contributing_invoice_count FROM mart_invoices "
            "WHERE status='paid' AND region='NA' AND invoice_date >= DATE '2024-01-01' "
            "AND invoice_date < DATE '2025-01-01' AND invoice_date <= ?"
        )
    else:
        sql = reference_queries(settings.root)[case_id]
    with read_connection(settings.database) as connection:
        rows = execute_bounded(
            connection, sql, (settings.as_of_date,) if "?" in sql else (), settings.query_timeout
        )
    if case_id == "Q2":
        rows.sort(key=lambda r: str(r["group_key"]))
        rows.sort(key=lambda r: exact_ratio(r), reverse=True)
        rows = rows[:1]
    return rows


def exact_ratio(row: dict[str, object]) -> Decimal:
    total, denominator = row["total"], row["denominator"]
    if (
        not isinstance(total, (int, Decimal))
        or not isinstance(denominator, int)
        or denominator == 0
    ):
        raise AssertionError("Invalid reference denominator")
    return Decimal(total) / denominator


def assert_reference(
    actual: Answer, expected: list[dict[str, object]], metric: Metric | None = None
) -> None:
    by_group = {str(row.get("group_key", "")): row for row in actual.rows}
    assert len(actual.rows) == len(expected), (
        "Result cardinality differs from independent reference"
    )
    if metric == Metric.TOP:
        assert [r["group_key"] for r in actual.rows] == [r["group_key"] for r in expected]
    for expected_row in expected:
        key = str(expected_row.get("group_key", ""))
        assert key in by_group, "Missing expected group"
        actual_row = by_group[key]
        for name, value in expected_row.items():
            assert actual_row[name] == value, f"Reference mismatch in {name}"
        if metric is not None:
            total = expected_row["total"]
            assert isinstance(total, (int, Decimal))
            value = exact_ratio(expected_row) if "denominator" in expected_row else Decimal(total)
            if metric == Metric.CHURN:
                value *= 100
            assert actual_row["value"] == value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            if metric == Metric.TOP:
                score = expected_row["csat_score"]
                assert actual_row["low_csat"] == (score <= 2 if isinstance(score, int) else None)


def assert_evidence(settings: Settings, request: MetricRequest, answer: Answer) -> None:
    """Check actual count + every sample's membership with independent predicates."""
    from app.domain.models import Metric

    account_grain = request.metric in (Metric.MRR, Metric.CHURN)
    table = "mart_accounts" if account_grain else "mart_invoices"
    key = "snapshot_invoice_id" if account_grain else "invoice_id"
    statuses = {
        Metric.PAID: ("paid",),
        Metric.REFUNDS: ("refunded",),
        Metric.NET: ("paid", "refunded"),
        Metric.TOP: ("paid", "refunded"),
        Metric.EXPOSURE: ("pending", "failed"),
    }.get(request.metric, ())
    with read_connection(settings.database) as connection:
        for row in answer.rows:
            where = ["invoice_date <= ?"]
            parameters: list[object] = [settings.as_of_date]
            if statuses:
                where.append(f"status IN ({','.join('?' for _ in statuses)})")
                parameters.extend(statuses)
            for bound, op in ((request.start_date, ">="), (request.end_date, "<")):
                if bound:
                    where.append(f"invoice_date {op} ?")
                    parameters.append(bound)
            for f in request.filters:
                where.append(f"{f.dimension.value} IN ({','.join('?' for _ in f.values)})")
                parameters.extend(f.values)
            dimension = "account_id" if request.metric == Metric.TOP else request.group_by
            if dimension:
                where.append(f"{dimension} = ?")
                parameters.append(row["group_key"])
            ids = [
                r[0]
                for r in connection.execute(
                    f"SELECT {key} FROM {table} WHERE {' AND '.join(where)} ORDER BY {key}",
                    parameters,
                ).fetchall()
            ]
            assert row["contributing_invoice_count"] == len(ids), "Evidence count differs"
            sample = row["invoice_id_sample"]
            assert isinstance(sample, list)
            assert sample == ids[: len(sample)] and len(sample) <= 10, (
                "Evidence membership/order differs"
            )
            assert row["sample_truncated"] == (len(sample) < len(ids))
