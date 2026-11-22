"""pipeline ingestion."""

import csv
from pathlib import Path

import duckdb

from app.config import ALIASES_FILE, FX_RATES_FILE, LIST_PRICES_FILE, Settings
from app.domain.errors import BuildError
from app.infrastructure.database import fetch_one


def columns() -> tuple[str, ...]:
    return (
        "invoice_id",
        "account_id",
        "account_name",
        "contact_email",
        "region",
        "industry",
        "plan",
        "billing_cycle",
        "seats",
        "currency",
        "amount",
        "discount_pct",
        "status",
        "payment_method",
        "signup_date",
        "invoice_date",
        "churned",
        "csat_score",
        "support_tickets",
    )


def load_raw(connection: duckdb.DuckDBPyConnection, settings: Settings, source_hash: str) -> None:
    names = columns()
    fields = ", ".join(f'"{name}" VARCHAR NOT NULL' for name in names)
    connection.execute(
        f"CREATE TABLE raw ({fields}, source_row_number BIGINT PRIMARY KEY, "
        "source_sha256 VARCHAR, source_row_sha256 VARCHAR)"
    )
    count = 0
    try:
        with settings.source.open(newline="", encoding="utf-8") as handle:
            reader = csv.reader(handle, strict=True)
            if tuple(next(reader, ())) != names:
                raise BuildError("CSV header must exactly match the 19-column source contract.")
            for row in reader:
                if len(row) != len(names) or any("\x00" in value for value in row):
                    raise BuildError("Malformed CSV record; verify column count and encoding.")
                count += 1
    except (csv.Error, UnicodeError, OSError) as exc:
        raise BuildError("Cannot parse source CSV; verify encoding and structure.") from exc
    if not count:
        raise BuildError("Source CSV contains no invoice records.")
    selected = ", ".join(f'''coalesce("{name}", '')''' for name in names)
    csv_types = "{" + ", ".join(f"'{name}': 'VARCHAR'" for name in names) + "}"
    connection.execute(
        f"INSERT INTO raw SELECT {selected}, ordinality, ?, sha256(to_json([{selected}])) "
        f"FROM read_csv(?, header=true, auto_detect=false, columns={csv_types}, "
        "nullstr='', parallel=false) WITH ORDINALITY",
        [source_hash, str(settings.source)],
    )
    if fetch_one(connection, "SELECT count(*) FROM raw")[0] != count:
        raise BuildError("CSV parser row counts disagree.")


def load_seeds(connection: duckdb.DuckDBPyConnection, root: Path) -> None:
    """Read fixed seed schemas, reject missing, overlapping or unsupported keys."""
    layouts = {
        "aliases": ("domain VARCHAR, alias VARCHAR, canonical VARCHAR", 3),
        "list_prices": ("plan VARCHAR, usd_per_seat_month DECIMAL(12,2)", 2),
        "fx_rates": ("currency VARCHAR, usd_per_local DECIMAL(9,6)", 2),
    }
    expected_headers = {
        "aliases": ["domain", "alias", "canonical"],
        "list_prices": ["plan", "usd_per_seat_month"],
        "fx_rates": ["currency", "usd_per_local"],
    }
    seed_files = {
        "aliases": ALIASES_FILE,
        "list_prices": LIST_PRICES_FILE,
        "fx_rates": FX_RATES_FILE,
    }
    for table, (schema, size) in layouts.items():
        with (root / seed_files[table]).open(newline="") as handle:
            reader = csv.reader(handle, strict=True)
            if next(reader, []) != expected_headers[table]:
                raise BuildError("Seed header violates its schema contract.")
            values = list(reader)
        if not values or any(len(row) != size or any(not v.strip() for v in row) for row in values):
            raise BuildError("Seed values are missing or malformed.")
        connection.execute(f"CREATE TABLE {table} ({schema})")
        types = "{" + ", ".join(f"'{key}': 'VARCHAR'" for key in expected_headers[table]) + "}"
        connection.execute(
            f"INSERT INTO {table} SELECT * FROM read_csv(?, header=true, "
            f"auto_detect=false, columns={types}, nullstr='')",
            [str(root / seed_files[table])],
        )

    if fetch_one(
        connection,
        "SELECT count(*) FROM (SELECT domain, alias FROM aliases GROUP BY ALL HAVING count(*) > 1)",
    )[0]:
        raise BuildError("Overlapping alias seed keys.")
    if fetch_one(connection, "SELECT count(*) FROM list_prices")[0] != 3:
        raise BuildError("List price seed must contain exactly three plans.")
    if fetch_one(connection, "SELECT count(*) FROM fx_rates")[0] != 3:
        raise BuildError("FX seed must contain exactly three currencies.")
    for table, key, value in (
        ("list_prices", "plan", "usd_per_seat_month"),
        ("fx_rates", "currency", "usd_per_local"),
    ):
        if fetch_one(connection, f"SELECT count(DISTINCT {key}), min({value}) FROM {table}") == (
            3,
            None,
        ):
            raise BuildError("Missing seed values.")
        total, minimum = fetch_one(
            connection, f"SELECT count(DISTINCT {key}), min({value}) FROM {table}"
        )
        if total != 3 or minimum <= 0:
            raise BuildError("Seed keys must be unique and values positive.")
    allowed = {
        "plan": {"Starter", "Pro", "Enterprise"},
        "currency": {"USD", "EUR", "GBP"},
        "status": {"paid", "pending", "failed", "refunded", "void"},
        "billing_cycle": {"monthly", "annual"},
        "region": {"NA", "EMEA", "APAC", "LATAM"},
        "churned": {"true", "false"},
        "payment_method": {"credit_card", "ACH", "wire", "invoice"},
    }
    seen: dict[str, set[str]] = {}
    for domain, alias, canonical in connection.execute("SELECT * FROM aliases").fetchall():
        if (
            domain not in allowed
            or canonical not in allowed[domain]
            or alias != alias.strip().lower()
        ):
            raise BuildError("Unsupported seed alias domain, category or lookup key.")
        seen.setdefault(domain, set()).add(canonical)
    if seen != allowed:
        raise BuildError("Alias seeds must cover all canonical categories.")
    if {r[0] for r in connection.execute("SELECT plan FROM list_prices").fetchall()} != allowed[
        "plan"
    ]:
        raise BuildError("Unsupported list-price plan.")
    if {r[0] for r in connection.execute("SELECT currency FROM fx_rates").fetchall()} != allowed[
        "currency"
    ]:
        raise BuildError("Unsupported FX currency.")
