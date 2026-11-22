"""M-* and N-* cases: independent SQL, bounded evidence and untrusted model output."""

from dataclasses import asdict, replace
from datetime import date
from decimal import Decimal

import duckdb
import pytest

from app.agent.service import QueryAgent
from app.config import Settings
from app.domain.errors import CloudNovaError, QueryError, RequestError
from app.domain.models import (
    Answer,
    Dimension,
    Filter,
    Metric,
    MetricRequest,
    Operator,
    Order,
    ResponseKind,
    RunReport,
)
from app.evaluation.cases import question_cases
from app.evaluation.reference import assert_evidence, assert_reference, reference_rows
from app.evaluation.runner import evaluate_historical_mrr
from app.infrastructure.database import execute_bounded, read_connection
from app.metrics.compiler import MetricCompiler
from app.metrics.validation import parse_request


class FakeClient:
    def __init__(self, response: object):
        self.response = response
        self.calls = 0

    def interpret(self, question: str, metadata: str, schema: dict[str, object]) -> object:
        self.calls += 1
        assert "Synthetic A" not in metadata
        assert '"F-01"' not in metadata
        assert "contact_email" not in metadata
        return self.response


@pytest.mark.parametrize("accepts_history", [False, True])
def test_history_case_exercises_backend_and_detects_acceptance(
    dataset: tuple[Settings, RunReport], monkeypatch: pytest.MonkeyPatch, accepts_history: bool
) -> None:
    settings, report = dataset
    compiler = MetricCompiler(settings)
    real_answer = compiler.answer
    calls = 0

    def answer(request: MetricRequest, build: RunReport) -> Answer:
        nonlocal calls
        calls += 1
        if accepts_history:
            return Answer(ResponseKind.METRIC)
        return real_answer(request, build)

    monkeypatch.setattr(compiler, "answer", answer)
    outcome = evaluate_historical_mrr(compiler, report)
    assert calls == 1
    assert not outcome.passed
    assert outcome.expected_failure is not accepts_history


@pytest.mark.parametrize("index", range(6))
def test_six_questions_match_reference(dataset: tuple[Settings, RunReport], index: int) -> None:
    settings, report = dataset
    request = question_cases()[index][1]
    answer = MetricCompiler(settings).answer(request, report)
    assert_reference(answer, reference_rows(settings, f"Q{index + 1}"))
    assert_evidence(settings, request, answer)
    assert answer.build_id == report.build_id and answer.sql and answer.parameters
    assert answer.units and answer.definition


def test_hand_goldens_and_denominators(dataset: tuple[Settings, RunReport]) -> None:
    settings, report = dataset
    compiler = MetricCompiler(settings)
    answers = [compiler.answer(r, report) for _, r in question_cases()]
    assert answers[0].rows[0]["value"] == Decimal("1524.84")
    assert answers[1].rows[0]["group_key"] == "LATAM"
    assert answers[1].rows[0]["value"] == Decimal("88.20")
    assert answers[2].rows[0]["value"] == Decimal("35.40")
    assert {r["group_key"]: (r["total"], r["denominator"]) for r in answers[3].rows} == {
        "Enterprise": (1, 2),
        "Starter": (0, 9),
    }
    assert [r["group_key"] for r in answers[4].rows] == ["H", "B", "A", "P", "C"]
    assert [r["low_csat"] for r in answers[4].rows] == [True, True, True, None, False]
    assert answers[5].rows[0]["invoice_count"] == 2
    assert answers[5].rows[0]["value"] == Decimal("157.00")


def test_filters_order_and_empty_populations(dataset: tuple[Settings, RunReport]) -> None:
    settings, report = dataset
    compiler = MetricCompiler(settings)
    request = MetricRequest(
        Metric.PAID, filters=(Filter(Dimension.REGION, Operator.EQ, ("EMEA",)),)
    )
    answer = compiler.answer(request, report)
    assert answer.rows[0]["value"] == 0 and answer.rows[0]["invoice_id_sample"] == []
    request = MetricRequest(Metric.TOP, order=Order.ASC, limit=1)
    answer = compiler.answer(request, report)
    assert answer.rows[0]["group_key"] == "R" and answer.rows[0]["value"] == -10
    assert_evidence(settings, request, answer)
    request = MetricRequest(
        Metric.MRR, filters=(Filter(Dimension.ACCOUNT, Operator.EQ, ("missing",)),)
    )
    answer = compiler.answer(request, report)
    assert answer.rows[0]["value"] is None and answer.rows[0]["denominator"] == 0


@pytest.mark.parametrize(
    "payload",
    [
        {"metric": "raw"},
        {"metric": "paid_revenue", "sql": "SELECT * FROM raw"},
        {"metric": "paid_revenue", "limit": True},
        {"metric": "paid_revenue", "limit": 1000},
        {"metric": "paid_revenue", "group_by": "contact_email"},
        {
            "metric": "paid_revenue",
            "filters": [{"dimension": "status", "operator": "eq", "values": ["void"]}],
        },
        {"metric": "average_mrr", "start_date": "2024-01-01"},
        {"metric": "paid_revenue", "start_date": "2025-01-01", "end_date": "2024-01-01"},
        {"metric": "paid_revenue", "order": "desc;drop table raw"},
    ],
)
def test_request_allowlists(payload: object) -> None:
    with pytest.raises(RequestError):
        parse_request(payload)


def test_injection_is_bound_and_file_write_is_disabled(dataset: tuple[Settings, RunReport]) -> None:
    settings, report = dataset
    request = MetricRequest(
        Metric.PAID, filters=(Filter(Dimension.ACCOUNT, Operator.EQ, ("x' OR 1=1 --",)),)
    )
    compiled = MetricCompiler(settings).compile(request)
    assert "x' OR" not in compiled.sql and "x' OR 1=1 --" in compiled.parameters
    assert MetricCompiler(settings).answer(request, report).rows[0]["value"] == 0
    with read_connection(settings.database) as connection:
        for sql in (
            "SELECT * FROM read_csv('/etc/passwd')",
            "CREATE TABLE forbidden(x INTEGER)",
            "SET enable_external_access=true",
        ):
            with pytest.raises(duckdb.Error):
                connection.execute(sql)
        with pytest.raises(QueryError):
            execute_bounded(
                connection,
                "SELECT sum(a.i*b.i) FROM range(100000000) a(i),range(100000000) b(i)",
                (),
                0.02,
            )
        assert connection.execute("SELECT 1").fetchall() == [(1,)]


def test_injected_model_and_clarification(dataset: tuple[Settings, RunReport]) -> None:
    settings, report = dataset
    request = question_cases()[0][1]
    payload = asdict(request)
    payload["start_date"] = "2024-01-01"
    payload["end_date"] = "2025-01-01"
    payload["filters"] = []
    fake = FakeClient({"kind": "metric", "request": payload})
    agent = QueryAgent(MetricCompiler(settings), fake)
    answer = agent.ask(question_cases()[0][0], report)
    assert answer.rows[0]["value"] == Decimal("1524.84") and fake.calls == 1
    fake.response = {"kind": "clarification", "explanation": "Paid or net revenue?"}
    assert agent.ask("What is revenue?", report).kind == ResponseKind.CLARIFICATION
    assert agent.ask("List all emails", report).kind == ResponseKind.UNSUPPORTED
    assert fake.calls == 2
    fake.response = {"kind": "metric", "request": {"metric": "paid_revenue", "sql": "bad"}}
    with pytest.raises(CloudNovaError):
        agent.ask("Paid revenue?", report)
    with pytest.raises(RequestError):
        agent.ask("hello\x00", report)


def test_programmatic_validation(dataset: tuple[Settings, RunReport]) -> None:
    settings, report = dataset
    with pytest.raises(RequestError):
        MetricCompiler(settings).answer(replace(question_cases()[0][1], limit=0), report)
    with pytest.raises(RequestError):
        MetricCompiler(settings).answer(
            MetricRequest(Metric.PAID, start_date=date(2028, 1, 1)), report
        )
