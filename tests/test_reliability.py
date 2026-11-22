"""Additional ingestion/security and real SDK-transport behavior, without credentials."""

from dataclasses import replace
from decimal import Decimal
from pathlib import Path
from typing import Any

import anthropic
import httpx
import pytest

from app.agent.client import AnthropicClient
from app.agent.contracts import system_metadata, tool_schema
from app.config import Settings
from app.domain.errors import ConfigurationError, InterpretationError, QueryError
from app.domain.models import RunReport
from app.evaluation.fixtures import fixture_rows, write_fixture
from app.infrastructure.database import fetch_one, read_connection
from app.pipeline.builder import Pipeline


def test_missing_artifact_has_actionable_error(tmp_path: Path) -> None:
    with pytest.raises(QueryError, match="run build"):
        with read_connection(tmp_path / "missing.duckdb"):
            pytest.fail("Missing database unexpectedly opened")


def test_systematic_fx_is_one_issue_without_repair(tmp_path: Path) -> None:
    # S-FX-01/S-PRICE-01: source generation pattern does not override the briefing.
    source = tmp_path / "source.csv"
    write_fixture(
        source,
        [
            {
                **fixture_rows()[0],
                "seats": "1",
                "discount_pct": "0",
                "currency": "GBP",
                "amount": "62.23",
            }
        ],
    )
    settings = Settings(source=source, database=tmp_path / "db.duckdb")
    report = Pipeline(settings).build()
    assert report.systematic_fx_rows == 1 and report.pricing_discrepancies == 0
    with read_connection(settings.database) as connection:
        assert fetch_one(
            connection, "SELECT amount_local, amount_usd, list_mrr_usd FROM mart_invoices"
        ) == (Decimal("62.23"), Decimal("79.03"), Decimal("49"))


def test_numeric_category_and_currency_contracts(tmp_path: Path) -> None:
    base = fixture_rows()[0]
    changes = [
        {"seats": "0"},
        {"discount_pct": "101"},
        {"support_tickets": "-1"},
        {"currency": "CAD"},
        {"currency": "EUR", "amount": "$100"},
        {"amount": "12,34.00"},
        {"amount": "NaN"},
        {"billing_cycle": "weekly"},
        {"churned": "unknown"},
        {"csat_score": "0"},
        {"signup_date": "2023-02-29"},
    ]
    rows = [{**base, **change, "invoice_id": f"BAD-{i}"} for i, change in enumerate(changes)]
    rows += [{**base, "invoice_id": "GOOD", "csat_score": "", "industry": ""}]
    source = tmp_path / "source.csv"
    write_fixture(source, rows)
    settings = Settings(source=source, database=tmp_path / "db.duckdb")
    report = Pipeline(settings).build()
    assert (report.retained, report.rejects) == (1, 11)
    with read_connection(settings.database) as connection:
        assert fetch_one(connection, "SELECT csat_score,industry FROM stg_invoices") == (None, None)


def test_sdk_retries_transport_only(
    dataset: tuple[Settings, RunReport], monkeypatch: pytest.MonkeyPatch
) -> None:
    settings, _ = dataset
    calls = 0
    real_client = anthropic.Anthropic

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls < 3:
            return httpx.Response(
                429,
                headers={"retry-after-ms": "1"},
                json={"type": "error", "error": {"type": "rate_limit_error", "message": "retry"}},
            )
        return httpx.Response(
            200,
            json={
                "id": "synthetic-message",
                "type": "message",
                "role": "assistant",
                "model": "test-model",
                "content": [
                    {
                        "type": "tool_use",
                        "id": "synthetic-tool",
                        "name": "interpret",
                        "input": {"kind": "unsupported", "explanation": "No subscription history"},
                    }
                ],
                "stop_reason": "tool_use",
                "stop_sequence": None,
                "usage": {"input_tokens": 1, "output_tokens": 1},
            },
        )

    def factory(**kwargs: Any) -> anthropic.Anthropic:
        return real_client(
            **kwargs, http_client=httpx.Client(transport=httpx.MockTransport(handler))
        )

    monkeypatch.setattr(anthropic, "Anthropic", factory)
    client = AnthropicClient(replace(settings, api_key="synthetic-test-key", model="test-model"))
    result = client.interpret("Historical MRR?", system_metadata(settings.root), tool_schema())
    assert (
        result == {"kind": "unsupported", "explanation": "No subscription history"} and calls == 3
    )
    calls = 0
    client = AnthropicClient(
        replace(settings, api_key="synthetic-test-key", model="test-model", model_retries=0)
    )
    with pytest.raises(InterpretationError):
        client.interpret("Historical MRR?", system_metadata(settings.root), tool_schema())
    assert calls == 1


def test_invalid_configuration(dataset: tuple[Settings, RunReport]) -> None:
    settings, _ = dataset
    for kwargs in ({"model_retries": 3}, {"query_timeout": float("nan")}, {"model_timeout": 0}):
        with pytest.raises(ConfigurationError):
            replace(settings, **kwargs)
