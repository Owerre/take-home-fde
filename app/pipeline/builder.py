"""pipeline builder."""

import csv
import fcntl
import hashlib
import os
import tempfile
import time
from dataclasses import replace
from pathlib import Path

import duckdb

from app.config import (
    BUSINESS_CONTEXT_FILE,
    DEPENDENCY_LOCK_FILE,
    PROJECT_FILE,
    TRANSFORM_SQL_FILE,
    Settings,
)
from app.domain.errors import BuildError
from app.domain.models import RunReport
from app.infrastructure.database import fetch_one, read_connection
from app.infrastructure.logging import event
from app.pipeline.ingestion import load_raw, load_seeds
from app.pipeline.validation import validate_build


def build_identity(settings: Settings) -> tuple[str, str]:
    """Hash behavior and input bytes; no key/model or nondeterministic timestamps."""
    digest = hashlib.sha256()
    source_hash = hashlib.sha256(settings.source.read_bytes()).hexdigest()
    digest.update(source_hash.encode())
    digest.update(str(settings.as_of_date).encode())
    for directory in ("app", "sql", "seeds", "specs", "prompts"):
        for path in sorted((settings.root / directory).rglob("*")):
            if path.is_file() and path.suffix in (".py", ".sql", ".csv", ".md", ".yaml"):
                digest.update(str(path.relative_to(settings.root)).encode())
                digest.update(path.read_bytes())
    for name in (BUSINESS_CONTEXT_FILE, PROJECT_FILE, DEPENDENCY_LOCK_FILE):
        path = settings.root / name
        if not path.is_file():
            raise BuildError("Required rules or dependency lock missing from project root.")
        digest.update(str(name).encode())
        digest.update(path.read_bytes())
    return (digest.hexdigest(), source_hash)


def run_report(connection: duckdb.DuckDBPyConnection) -> RunReport:
    identity, source_hash, reference_date = fetch_one(connection, "SELECT * FROM build_metadata")
    counts = dict(
        connection.execute(
            "SELECT disposition, count(*) FROM row_dispositions GROUP BY disposition"
        ).fetchall()
    )
    future, systematic, discrepancies = fetch_one(
        connection,
        "SELECT count(*) FILTER (WHERE invoice_date > ?), "
        "count(*) FILTER (WHERE systematic_fx_pattern), "
        "count(*) FILTER (WHERE pricing_discrepancy) FROM mart_invoices",
        [reference_date],
    )
    conflicts = fetch_one(
        connection,
        "SELECT count(*) FROM account_conflicts WHERE name_conflict OR signup_conflict "
        "OR region_conflict OR churn_conflict",
    )[0]
    return RunReport(
        identity,
        source_hash,
        reference_date,
        sum(counts.values()),
        counts.get("retained", 0),
        counts.get("duplicate_loser", 0),
        counts.get("reject", 0),
        future,
        conflicts,
        systematic,
        discrepancies,
    )


class Pipeline:
    """Own the build lock and atomic publication; never mutate a valid artifact."""

    def __init__(self, settings: Settings):
        self.settings = settings

    def build(self, *, force: bool = False) -> RunReport:
        settings = self.settings
        try:
            with settings.database.with_suffix(".lock").open("a") as lock:
                deadline = time.monotonic() + settings.lock_timeout
                while True:
                    try:
                        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        break
                    except BlockingIOError:
                        if time.monotonic() >= deadline:
                            raise BuildError(
                                "Build lock busy; wait for the other builder and retry."
                            ) from None
                        time.sleep(0.05)
                return self._locked_build(force)
        except (OSError, csv.Error, duckdb.Error) as exc:
            raise BuildError(
                "Build failed; prior artifact preserved. Check input/seed files and disk access."
            ) from exc

    def _locked_build(self, force: bool) -> RunReport:
        settings = self.settings
        identity, source_hash = build_identity(settings)
        if settings.database.exists() and (not force):
            with read_connection(settings.database) as connection:
                report = run_report(connection)
                if report.build_id == identity:
                    event("build", build_id=identity, reused=True, retained=report.retained)
                    return replace(report, reused=True)
        descriptor, name = tempfile.mkstemp(
            prefix=".cloudnova-", suffix=".duckdb", dir=settings.database.parent
        )
        os.close(descriptor)
        temporary = Path(name)
        temporary.unlink()
        try:
            with duckdb.connect(str(temporary)) as connection:
                os.chmod(temporary, 0o600)
                connection.execute("SET threads = 1")
                connection.execute("BEGIN TRANSACTION")
                connection.execute(
                    "CREATE TABLE build_metadata "
                    "(build_id VARCHAR, source_sha256 VARCHAR, as_of_date DATE)"
                )
                connection.execute(
                    "INSERT INTO build_metadata VALUES (?, ?, ?)",
                    [identity, source_hash, settings.as_of_date],
                )
                load_raw(connection, settings, source_hash)
                event("build_stage", stage="raw_loaded")
                load_seeds(connection, settings.root)
                event("build_stage", stage="seeds_loaded")
                connection.execute((settings.root / TRANSFORM_SQL_FILE).read_text())
                event("build_stage", stage="transformed")
                validate_build(connection)
                if build_identity(settings) != (identity, source_hash):
                    raise BuildError(
                        "Inputs or rules changed during build; retry with stable files."
                    )
                report = run_report(connection)
                connection.execute("COMMIT")
            os.chmod(temporary, 384)
            os.replace(temporary, settings.database)
        finally:
            temporary.unlink(missing_ok=True)
            Path(str(temporary) + ".wal").unlink(missing_ok=True)
        event(
            "build",
            build_id=identity,
            reused=False,
            retained=report.retained,
            rejects=report.rejects,
            duplicate_losers=report.duplicate_losers,
        )
        return report
