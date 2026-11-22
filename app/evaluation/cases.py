"""evaluation cases."""

from datetime import date

from app.domain.models import (
    Dimension,
    EvalCase,
    Metric,
    MetricRequest,
    ResponseKind,
)


def historical_mrr_case() -> EvalCase:
    """E-FAIL-01: exact historical MRR cannot be derived from invoice snapshots."""
    return EvalCase(
        "HISTORY",
        "What was exact MRR on 2023-06-30 including subscriptions without invoices?",
        ("E-FAIL-01", "N-AMB-01", "S-ACCT-01"),
        MetricRequest(Metric.MRR, start_date=date(2023, 6, 30), end_date=date(2023, 7, 1)),
        expected_kind=ResponseKind.UNSUPPORTED,
        expected_failure=True,
    )


def question_cases() -> tuple[tuple[str, MetricRequest], ...]:
    """Canonical requests are shared metadata, not an offline NL heuristic."""
    from app.domain.models import Filter, Operator

    return (
        (
            "What was our total recognized revenue in USD for paid invoices in 2024?",
            MetricRequest(Metric.PAID, start_date=date(2024, 1, 1), end_date=date(2025, 1, 1)),
        ),
        (
            "Which region has the highest average MRR per account?",
            MetricRequest(Metric.MRR, Dimension.REGION, limit=1),
        ),
        ("How much have we given back in refunds?", MetricRequest(Metric.REFUNDS)),
        (
            "What's the churn rate among Enterprise accounts vs Starter?",
            MetricRequest(
                Metric.CHURN,
                Dimension.PLAN,
                (Filter(Dimension.PLAN, Operator.IN, ("Enterprise", "Starter")),),
            ),
        ),
        (
            "List the top 5 accounts by revenue, and flag any with CSAT <= 2.",
            MetricRequest(Metric.TOP, limit=5),
        ),
        (
            "How many invoices are stuck in pending/failed and what's the exposed $?",
            MetricRequest(Metric.EXPOSURE),
        ),
    )
