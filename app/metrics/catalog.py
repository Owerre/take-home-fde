"""metrics catalog."""

from app.domain.models import (
    Metric,
    MetricDefinition,
    Status,
)


def definition(metric: Metric) -> MetricDefinition:
    definitions = (
        MetricDefinition(
            Metric.PAID,
            "M-REV-01",
            "Sum of paid invoice-date ledger amounts",
            "USD",
            (Status.PAID,),
        ),
        MetricDefinition(
            Metric.MRR,
            "M-MRR-01",
            "Mean snapshot MRR, inactive accounts at zero",
            "USD/account/month",
            (),
            True,
        ),
        MetricDefinition(
            Metric.REFUNDS,
            "M-REF-01",
            "Positive magnitude of negative refunded invoices",
            "USD",
            (Status.REFUNDED,),
        ),
        MetricDefinition(
            Metric.CHURN,
            "M-CHURN-01",
            "Snapshot churned flags / all observed accounts",
            "percent",
            (),
            True,
        ),
        MetricDefinition(
            Metric.TOP,
            "M-TOP-01",
            "Account paid revenue plus negative refunds",
            "USD",
            (Status.PAID, Status.REFUNDED),
        ),
        MetricDefinition(
            Metric.EXPOSURE,
            "M-EXP-01",
            "Pending/failed face value and invoice count",
            "USD and invoices",
            (Status.PENDING, Status.FAILED),
        ),
        MetricDefinition(
            Metric.NET,
            "M-NET-01",
            "Paid revenue plus negative refunded amounts",
            "USD",
            (Status.PAID, Status.REFUNDED),
        ),
    )
    return next(d for d in definitions if d.metric == metric)
