"""pipeline validation."""

import duckdb

from app.domain.errors import BuildError
from app.infrastructure.database import fetch_one


def validate_build(connection: duckdb.DuckDBPyConnection) -> None:
    checks = (
        "SELECT (SELECT count(*) FROM raw) <> (SELECT count(*) FROM row_dispositions)",
        "SELECT count(*) <> count(DISTINCT source_row_number) FROM row_dispositions",
        "SELECT count(*) <> count(DISTINCT invoice_id) FROM stg_invoices",
        "SELECT count(*) <> count(DISTINCT account_id) FROM mart_accounts",
        "SELECT (SELECT count(*) FROM stg_invoices) <> (SELECT count(*) FROM mart_invoices)",
        "SELECT count(*) > 0 FROM row_dispositions WHERE disposition NOT IN "
        "('retained','duplicate_loser','reject')",
        "SELECT count(*) > 0 FROM duplicate_decisions d LEFT JOIN raw r ON "
        "d.selected_source_row_number = r.source_row_number WHERE r.source_row_number IS NULL",
        "SELECT count(*) > 0 FROM stg_invoices WHERE invoice_id = '' OR account_id = '' "
        "OR seats NOT BETWEEN 1 AND 1000000 OR discount_pct NOT BETWEEN 0 AND 100 "
        "OR (status = 'refunded' AND amount_local >= 0) "
        "OR (status <> 'refunded' AND amount_local < 0)",
    )
    for check in checks:
        if fetch_one(connection, check)[0]:
            raise BuildError(
                "Output contract or row reconciliation violated; inspect local audit tables."
            )
