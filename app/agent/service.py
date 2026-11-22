"""agent service."""

import re
from dataclasses import replace

from app.agent.client import ModelClient
from app.agent.contracts import system_metadata, tool_schema
from app.domain.errors import InterpretationError, RequestError
from app.domain.models import Answer, ResponseKind, RunReport
from app.metrics.compiler import MetricCompiler
from app.metrics.validation import mapping, parse_request


class QueryAgent:
    """Interpret → validate → compile → locally format. Client is injectable."""

    def __init__(self, compiler: MetricCompiler, client: ModelClient):
        self.compiler = compiler
        self.client = client

    def ask(self, question: str, report: RunReport) -> Answer:
        if not isinstance(question, str) or not 1 <= len(question.strip()) <= 2000:
            raise RequestError("Question must contain 1–2000 characters.")
        if any((ord(c) < 32 and c not in "\n\r\t") or ord(c) == 127 for c in question):
            raise RequestError("Question contains prohibited control characters.")
        if re.search(
            r"\b(emails?|contact_email|passwords?|secrets?)\b|ignore .*instructions|"
            r"read_csv|read_parquet|\b(drop|attach|copy|pragma)\b",
            question,
            re.I,
        ):
            return Answer(
                ResponseKind.UNSUPPORTED,
                "Personal-contact, secret, file-access and instruction-override "
                "requests are unsupported.",
                build_id=report.build_id,
                as_of_date=report.as_of_date,
            )
        payload = mapping(
            self.client.interpret(
                question.strip(), system_metadata(self.compiler.settings.root), tool_schema()
            ),
            {"kind", "request", "explanation"},
            {"kind"},
        )
        raw_kind = payload["kind"]
        if not isinstance(raw_kind, str):
            raise InterpretationError("Model response kind must be a string.")
        try:
            kind = ResponseKind(raw_kind)
        except (ValueError, TypeError) as exc:
            raise InterpretationError("Model response kind is invalid.") from exc
        if kind == ResponseKind.METRIC:
            if "request" not in payload or "explanation" in payload:
                raise InterpretationError("Metric response must contain only kind and request.")
            return self.compiler.answer(parse_request(payload["request"]), report)
        explanation = payload.get("explanation")
        if (
            "request" in payload
            or not isinstance(explanation, str)
            or not 1 <= len(explanation) <= 1000
        ):
            raise InterpretationError("Clarification/refusal requires a bounded explanation only.")
        return replace(
            Answer(kind, explanation),
            build_id=report.build_id,
            source_sha256=report.source_sha256,
            as_of_date=report.as_of_date,
        )
