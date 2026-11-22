"""S-REC/DEDUP/DATE/FX/PRICE/ACCT/MRR and atomic-build acceptance checks."""

import fcntl
import hashlib
import shutil
from dataclasses import replace
from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from app.config import Settings
from app.domain.errors import BuildError
from app.domain.models import RunReport
from app.evaluation.fixtures import fixture_rows, write_fixture
from app.infrastructure.database import fetch_one, read_connection
from app.pipeline.builder import Pipeline, build_identity


def test_reconciliation_dedup_and_rejects(dataset: tuple[Settings, RunReport]) -> None:
    settings, report = dataset
    assert (report.raw_rows, report.retained, report.duplicate_losers, report.rejects) == (
        24,
        16,
        3,
        5,
    )
    with read_connection(settings.database) as connection:
        assert (
            fetch_one(connection, "SELECT count(DISTINCT source_row_number) FROM row_dispositions")[
                0
            ]
            == 24
        )
        assert (
            fetch_one(connection, "SELECT status FROM mart_invoices WHERE invoice_id='F-08'")[0]
            == "void"
        )
        assert (
            fetch_one(connection, "SELECT status FROM mart_invoices WHERE invoice_id='F-21'")[0]
            == "refunded"
        )
        assert (
            fetch_one(connection, "SELECT count(*) FROM rejects WHERE reason LIKE '%sign%'")[0] == 2
        )
        assert (
            fetch_one(
                connection, "SELECT count(*) FROM stg_invoices WHERE invoice_id IN ('F-11','F-12')"
            )[0]
            == 0
        )


def test_dates_fx_annual_and_missing_csat(dataset: tuple[Settings, RunReport]) -> None:
    settings, report = dataset
    with read_connection(settings.database) as connection:
        assert fetch_one(
            connection, "SELECT invoice_date FROM mart_invoices WHERE invoice_id='F-01'"
        )[0] == date(2024, 1, 5)
        assert fetch_one(
            connection, "SELECT invoice_date FROM mart_invoices WHERE invoice_id='F-05'"
        )[0] == date(2024, 1, 5)
        assert fetch_one(
            connection, "SELECT amount_usd FROM mart_invoices WHERE invoice_id='F-02'"
        )[0] == Decimal("108.00")
        assert fetch_one(
            connection, "SELECT amount_usd FROM mart_invoices WHERE invoice_id='F-16'"
        )[0] == Decimal("0.64")
        assert fetch_one(
            connection, "SELECT round(1.005::DECIMAL(8,3),2), round(-1.005::DECIMAL(8,3),2)"
        ) == (Decimal("1.01"), Decimal("-1.01"))
        assert fetch_one(
            connection,
            "SELECT list_mrr_usd, expected_invoice_usd FROM mart_invoices WHERE invoice_id='F-10'",
        ) == (Decimal("88.20"), Decimal("882.00"))
        assert fetch_one(
            connection, "SELECT account_mrr_usd FROM mart_accounts WHERE account_id='H'"
        )[0] == Decimal("88.20")
        assert fetch_one(
            connection,
            "SELECT snapshot_invoice_id, csat_score FROM mart_accounts WHERE account_id='P'",
        ) == ("F-19", None)
        assert (
            fetch_one(connection, "SELECT count(*) FROM mart_accounts WHERE account_id='G'")[0] == 0
        )
        assert (
            fetch_one(
                connection, "SELECT pricing_discrepancy FROM mart_invoices WHERE invoice_id='F-16'"
            )[0]
            is True
        )
        assert "contact_email" not in [
            r[0] for r in connection.execute("DESCRIBE mart_invoices").fetchall()
        ]
    assert report.future_invoices == 1


def test_reuse_reference_date_and_atomic_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.csv"
    write_fixture(source)
    settings = Settings(source=source, database=tmp_path / "db.duckdb")
    pipeline = Pipeline(settings)
    original = pipeline.build()
    assert pipeline.build().reused
    changed = replace(settings, as_of_date=date(2027, 1, 1))
    assert build_identity(settings) != build_identity(changed)
    assert Pipeline(changed).build().future_invoices == 0
    before = hashlib.sha256(settings.database.read_bytes()).digest()
    source.write_text("bad,header\nnot,a,record\n")
    with pytest.raises(BuildError):
        pipeline.build()
    assert hashlib.sha256(settings.database.read_bytes()).digest() == before
    assert not list(tmp_path.glob(".cloudnova-*"))
    assert original.raw_rows == 24


def test_all_invalid_and_exact_duplicates_count_once(tmp_path: Path) -> None:
    rows = fixture_rows()[:1]
    rows[0]["status"] = "unknown"
    rows.append(rows[0].copy())
    source = tmp_path / "invalid.csv"
    write_fixture(source, rows)
    report = Pipeline(Settings(source=source, database=tmp_path / "db.duckdb")).build()
    assert (report.retained, report.rejects, report.duplicate_losers) == (0, 1, 1)


def test_build_lock_is_bounded(dataset: tuple[Settings, RunReport]) -> None:
    settings, _ = dataset
    with settings.database.with_suffix(".lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(BuildError, match="lock busy"):
            Pipeline(replace(settings, lock_timeout=0.05)).build()


@pytest.mark.parametrize(
    "directory,suffix", [("seeds", ".csv"), ("sql", ".sql"), ("specs", ".md"), ("prompts", ".yaml")]
)
def test_identity_covers_behavior_inputs(tmp_path: Path, directory: str, suffix: str) -> None:
    root = Settings().root
    for name in ("app", "sql", "seeds", "specs", "prompts"):
        shutil.copytree(root / name, tmp_path / name, ignore=shutil.ignore_patterns("__pycache__"))
    (tmp_path / "data").mkdir()
    shutil.copy(root / "data/BUSINESS_CONTEXT.md", tmp_path / "data/BUSINESS_CONTEXT.md")
    for name in ("pyproject.toml", "uv.lock"):
        shutil.copy(root / name, tmp_path / name)
    source = tmp_path / "source.csv"
    write_fixture(source)
    settings = Settings(root=tmp_path, source=source, database=tmp_path / "db.duckdb")
    before = build_identity(settings)
    target = next((tmp_path / directory).glob("*" + suffix))
    target.write_text(target.read_text() + "\n")
    assert build_identity(settings) != before
