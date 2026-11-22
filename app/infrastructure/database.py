"""Restricted short-lived query connections and bounded execution (N-SEC-01)."""

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from threading import Timer
from typing import Any

import duckdb

from app.domain.errors import QueryError
from app.domain.models import SqlValue


@contextmanager
def read_connection(database: Path) -> Iterator[duckdb.DuckDBPyConnection]:
    try:
        connection = duckdb.connect(
            str(database),
            read_only=True,
            config={
                "enable_external_access": "false",
                "autoload_known_extensions": "false",
                "autoinstall_known_extensions": "false",
                "threads": "1",
                "memory_limit": "256MB",
            },
        )
    except duckdb.Error as exc:
        raise QueryError(
            "Cannot open the built database; run build and check file access."
        ) from exc
    try:
        try:
            connection.execute("SET lock_configuration = true")
        except duckdb.Error as exc:
            raise QueryError(
                "Cannot apply required query restrictions; check DuckDB version."
            ) from exc
        yield connection
    finally:
        connection.close()


def execute_bounded(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    parameters: tuple[SqlValue, ...],
    timeout: float,
) -> list[dict[str, object]]:
    """Execute compiler-owned SQL; the caller never accepts SQL from a model."""
    timer = Timer(timeout, connection.interrupt)
    timer.daemon = True
    timer.start()
    try:
        cursor = connection.execute(sql, parameters)
        names = [column[0] for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]
    except duckdb.Error as exc:
        raise QueryError(
            "Metric query failed or exceeded its deadline; rebuild and retry."
        ) from exc
    finally:
        timer.cancel()
        timer.join()


def fetch_one(
    connection: duckdb.DuckDBPyConnection,
    sql: str,
    parameters: list[object] | tuple[SqlValue, ...] = (),
) -> tuple[Any, ...]:
    """Narrow DuckDB's optional dynamically typed row at the storage boundary."""
    row = connection.execute(sql, parameters).fetchone()
    if row is None:
        raise QueryError("Expected a metadata/aggregate row but query returned none.")
    return row
