"""evaluation cases."""

from datetime import date

from app.domain.models import (
    Dimension,
    Metric,
    MetricRequest,
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
