"""Session-scoped synthetic ledger, built without credentials or network."""

from pathlib import Path

import pytest

from app.config import Settings
from app.domain.models import RunReport
from app.evaluation.fixtures import write_fixture
from app.pipeline.builder import Pipeline


@pytest.fixture(scope="session")
def dataset(tmp_path_factory: pytest.TempPathFactory) -> tuple[Settings, RunReport]:
    directory: Path = tmp_path_factory.mktemp("ledger")
    source = directory / "invoices.csv"
    write_fixture(source)
    settings = Settings(source=source, database=directory / "ledger.duckdb")
    return settings, Pipeline(settings).build()
