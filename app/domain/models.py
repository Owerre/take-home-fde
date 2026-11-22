"""Immutable domain contracts (S-RAW-01, N-TYPE-01, N-ANS-01)."""

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from enum import StrEnum


class Metric(StrEnum):
    PAID = "paid_revenue"
    MRR = "average_mrr"
    REFUNDS = "refunds"
    CHURN = "churn_rate"
    TOP = "account_revenue"
    EXPOSURE = "exposure"
    NET = "net_revenue"


class Dimension(StrEnum):
    REGION = "region"
    PLAN = "plan"
    CYCLE = "billing_cycle"
    CURRENCY = "currency"
    STATUS = "status"
    ACCOUNT = "account_id"


class Operator(StrEnum):
    EQ = "eq"
    IN = "in"


class Order(StrEnum):
    ASC = "asc"
    DESC = "desc"


class Status(StrEnum):
    PAID = "paid"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"
    VOID = "void"


class Plan(StrEnum):
    STARTER = "Starter"
    PRO = "Pro"
    ENTERPRISE = "Enterprise"


class Cycle(StrEnum):
    MONTHLY = "monthly"
    ANNUAL = "annual"


class Region(StrEnum):
    NA = "NA"
    EMEA = "EMEA"
    APAC = "APAC"
    LATAM = "LATAM"


class Currency(StrEnum):
    USD = "USD"
    EUR = "EUR"
    GBP = "GBP"


class ResponseKind(StrEnum):
    METRIC = "metric"
    CLARIFICATION = "clarification"
    UNSUPPORTED = "unsupported"


@dataclass(frozen=True)
class Filter:
    dimension: Dimension
    operator: Operator
    values: tuple[str, ...]


@dataclass(frozen=True)
class MetricRequest:
    metric: Metric
    group_by: Dimension | None = None
    filters: tuple[Filter, ...] = ()
    start_date: date | None = None
    end_date: date | None = None
    order: Order = Order.DESC
    limit: int = 100


@dataclass(frozen=True)
class MetricDefinition:
    metric: Metric
    rule_id: str
    description: str
    units: str
    statuses: tuple[Status, ...]
    account_grain: bool = False


@dataclass(frozen=True)
class RunReport:
    build_id: str
    source_sha256: str
    as_of_date: date
    raw_rows: int
    retained: int
    duplicate_losers: int
    rejects: int
    future_invoices: int
    conflicting_accounts: int
    systematic_fx_rows: int
    pricing_discrepancies: int
    reused: bool = False


SqlValue = str | int | bool | Decimal | date | None


@dataclass(frozen=True)
class Answer:
    kind: ResponseKind
    explanation: str = ""
    rows: tuple[dict[str, object], ...] = ()
    units: str = ""
    definition: str = ""
    sql: str = ""
    parameters: tuple[SqlValue, ...] = ()
    assumptions: tuple[str, ...] = ()
    caveats: tuple[str, ...] = ()
    build_id: str = ""
    source_sha256: str = ""
    as_of_date: date | None = None


@dataclass(frozen=True)
class EvalCase:
    case_id: str
    question: str
    rule_ids: tuple[str, ...]
    request: MetricRequest | None = None
    expected_kind: ResponseKind = ResponseKind.METRIC
    expected_failure: bool = False


@dataclass(frozen=True)
class EvalOutcome:
    case_id: str
    passed: bool
    explanation: str
    expected_failure: bool = False
