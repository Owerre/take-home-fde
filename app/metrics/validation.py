"""Strict, independently reusable validation for model and programmatic requests."""

from datetime import date
from enum import StrEnum
from typing import TypeVar

from app.domain.errors import RequestError
from app.domain.models import (
    Currency,
    Cycle,
    Dimension,
    Filter,
    Metric,
    MetricRequest,
    Operator,
    Order,
    Plan,
    Region,
    Status,
)

E = TypeVar("E", bound=StrEnum)


def enum_value[E: StrEnum](enum: type[E], value: object) -> E:
    if not isinstance(value, str):
        raise RequestError("Expected an allowlisted string value.")
    try:
        return enum(value)
    except ValueError as exc:
        raise RequestError("Unsupported category or identifier.") from exc


def mapping(value: object, allowed: set[str], required: set[str]) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise RequestError("Expected a structured object.")
    result: dict[str, object] = dict(value)
    if set(result) - allowed or required - set(result):
        raise RequestError("Missing required fields or unexpected structured fields.")
    return result


def iso_date(value: object) -> date | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise RequestError("Date must use ISO YYYY-MM-DD.")
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise RequestError("Date must use ISO YYYY-MM-DD.") from exc
    if str(parsed) != value:
        raise RequestError("Date must use ISO YYYY-MM-DD.")
    return parsed


def parse_request(value: object) -> MetricRequest:
    data = mapping(
        value,
        {"metric", "group_by", "filters", "start_date", "end_date", "order", "limit"},
        {"metric"},
    )
    raw_filters = data.get("filters", [])
    if not isinstance(raw_filters, list) or len(raw_filters) > 10:
        raise RequestError("At most ten filters are supported.")
    filters: list[Filter] = []
    for raw in raw_filters:
        f = mapping(raw, {"dimension", "operator", "values"}, {"dimension", "operator", "values"})
        values = f["values"]
        if not isinstance(values, list) or not 1 <= len(values) <= 20:
            raise RequestError("Filters need 1–20 values.")
        if not all(isinstance(v, str) for v in values):
            raise RequestError("Filter values must be strings.")
        filters.append(
            Filter(
                enum_value(Dimension, f["dimension"]),
                enum_value(Operator, f["operator"]),
                tuple(values),
            )
        )
    limit = data.get("limit", 100)
    if type(limit) is not int or not 1 <= limit <= 100:
        raise RequestError("Limit must be an integer from 1 to 100.")
    request = MetricRequest(
        enum_value(Metric, data["metric"]),
        enum_value(Dimension, data["group_by"]) if data.get("group_by") is not None else None,
        tuple(filters),
        iso_date(data.get("start_date")),
        iso_date(data.get("end_date")),
        enum_value(Order, data.get("order", "desc")),
        limit,
    )
    validate_request(request)
    return request


def validate_request(request: MetricRequest) -> None:
    """N-REQ-02/03: applies even when callers bypass model JSON parsing."""
    if not isinstance(request.metric, Metric) or not isinstance(request.order, Order):
        raise RequestError("Metric and ordering must use allowlisted enum values.")
    if type(request.limit) is not int or not 1 <= request.limit <= 100:
        raise RequestError("Limit must be an integer from 1 to 100.")
    if not isinstance(request.filters, tuple) or len(request.filters) > 10:
        raise RequestError("Invalid filter collection.")
    for d in (request.start_date, request.end_date):
        if d is not None and type(d) is not date:
            raise RequestError("Date bounds must be dates.")
    if request.start_date and request.end_date and request.start_date >= request.end_date:
        raise RequestError("Start date must precede exclusive end date.")
    account_metric = request.metric in (Metric.MRR, Metric.CHURN)
    if account_metric and (request.start_date or request.end_date):
        raise RequestError(
            "Snapshot metrics use build reference date; change as_of_date and rebuild."
        )
    groups = {Dimension.REGION, Dimension.PLAN}
    if request.metric == Metric.EXPOSURE:
        groups.add(Dimension.STATUS)
    if request.metric == Metric.TOP:
        groups = {Dimension.ACCOUNT}
    if request.group_by is not None and (
        not isinstance(request.group_by, Dimension) or request.group_by not in groups
    ):
        raise RequestError("Grouping is incompatible with this metric.")
    allowed_filters = (
        {Dimension.REGION, Dimension.PLAN, Dimension.ACCOUNT} if account_metric else set(Dimension)
    )
    from app.metrics.catalog import definition

    statuses = definition(request.metric).statuses
    seen: set[Dimension] = set()
    domains: dict[Dimension, type[StrEnum]] = {
        Dimension.REGION: Region,
        Dimension.PLAN: Plan,
        Dimension.CYCLE: Cycle,
        Dimension.CURRENCY: Currency,
        Dimension.STATUS: Status,
    }
    for f in request.filters:
        if not isinstance(f, Filter) or not isinstance(f.dimension, Dimension):
            raise RequestError("Invalid filter.")
        if f.dimension not in allowed_filters or f.dimension in seen:
            raise RequestError("Incompatible or duplicate filter dimension.")
        seen.add(f.dimension)
        if not isinstance(f.operator, Operator) or not isinstance(f.values, tuple):
            raise RequestError("Invalid filter operator or values.")
        if not 1 <= len(f.values) <= 20 or (f.operator == Operator.EQ and len(f.values) != 1):
            raise RequestError("Invalid filter cardinality.")
        for v in f.values:
            if not isinstance(v, str) or not 1 <= len(v) <= 128 or any(ord(c) < 32 for c in v):
                raise RequestError(
                    "Filter strings must be bounded and contain no control characters."
                )
            if f.dimension in domains:
                enum_value(domains[f.dimension], v)
            if f.dimension == Dimension.STATUS and v not in statuses:
                raise RequestError("Status filter conflicts with the metric definition.")
