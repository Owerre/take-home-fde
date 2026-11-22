"""Validated settings. Environment files are never implicitly loaded."""

import math
import os
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

from app.domain.errors import ConfigurationError

ROOT_DIR = Path(__file__).resolve().parents[1]
SOURCE_FILE = Path("data/cloudnova_invoices.csv")
DATABASE_FILE = Path("build/cloudnova.duckdb")
PROMPT_FILE = Path("prompts/query_agent.yaml")
TRANSFORM_SQL_FILE = Path("sql/transform.sql")
ALIASES_FILE = Path("seeds/aliases.csv")
LIST_PRICES_FILE = Path("seeds/list_prices.csv")
FX_RATES_FILE = Path("seeds/fx_rates.csv")
BUSINESS_CONTEXT_FILE = Path("data/BUSINESS_CONTEXT.md")
DEPENDENCY_LOCK_FILE = Path("uv.lock")
PROJECT_FILE = Path("pyproject.toml")
REFERENCE_SQL_FILE = Path("evals/reference.sql")
REFERENCE_DATE = date(2026, 11, 21)
QUERY_TIMEOUT = 5.0
MODEL_TIMEOUT = 30.0
MODEL_RETRIES = 2
LOCK_TIMEOUT = 10.0


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT_DIR
    source: Path = SOURCE_FILE
    database: Path = DATABASE_FILE
    as_of_date: date = REFERENCE_DATE
    model: str = ""
    api_key: str = field(default="", repr=False)
    query_timeout: float = QUERY_TIMEOUT
    model_timeout: float = MODEL_TIMEOUT
    model_retries: int = MODEL_RETRIES
    lock_timeout: float = LOCK_TIMEOUT

    def __post_init__(self) -> None:
        object.__setattr__(self, "root", self.root.resolve())
        for name in ("source", "database"):
            path = getattr(self, name)
            object.__setattr__(self, name, (self.root / path).resolve())
        if not self.source.is_file():
            raise ConfigurationError("Source CSV missing; set CLOUDNOVA_DATA_PATH.")
        if self.database == self.source:
            raise ConfigurationError("Database and source must be different paths.")
        if not isinstance(self.as_of_date, date):
            raise ConfigurationError("Reference date must be an ISO date.")
        if not 0 <= self.model_retries <= 2:
            raise ConfigurationError("Model retry count must be between 0 and 2.")
        for value in (self.query_timeout, self.model_timeout, self.lock_timeout):
            if not math.isfinite(value) or not 0 < value <= 300:
                raise ConfigurationError("Timeouts must be positive and at most 300 seconds.")
        try:
            self.database.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise ConfigurationError("Database directory must be writable.") from exc
        if not os.access(self.source, os.R_OK) or not os.access(self.database.parent, os.W_OK):
            raise ConfigurationError("Source must be readable and database directory writable.")

    @classmethod
    def from_env(cls) -> "Settings":
        try:
            return cls(
                source=Path(os.environ.get("CLOUDNOVA_DATA_PATH", str(SOURCE_FILE))),
                database=Path(os.environ.get("CLOUDNOVA_DB_PATH", str(DATABASE_FILE))),
                as_of_date=date.fromisoformat(
                    os.environ.get("CLOUDNOVA_AS_OF_DATE", str(REFERENCE_DATE))
                ),
                model=os.environ.get("ANTHROPIC_MODEL", ""),
                api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
                query_timeout=float(os.environ.get("CLOUDNOVA_QUERY_TIMEOUT", str(QUERY_TIMEOUT))),
                model_timeout=float(os.environ.get("CLOUDNOVA_MODEL_TIMEOUT", str(MODEL_TIMEOUT))),
                model_retries=int(os.environ.get("CLOUDNOVA_MODEL_RETRIES", str(MODEL_RETRIES))),
            )
        except ValueError as exc:
            raise ConfigurationError("Invalid date, timeout or retry environment setting.") from exc
