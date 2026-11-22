"""agent client."""

from typing import Protocol

import anthropic
from anthropic.types import ToolParam

from app.config import Settings
from app.domain.errors import ConfigurationError, InterpretationError
from app.domain.models import ResponseKind
from app.metrics.validation import mapping


class ModelClient(Protocol):
    def interpret(self, question: str, metadata: str, schema: dict[str, object]) -> object:
        """Return an untrusted tool payload, never SQL or customer-facing answers."""
        ...


class AnthropicClient:
    """Short-lived SDK resource, with bounded transport retries and model timeout."""

    def __init__(self, settings: Settings):
        if not settings.api_key or not settings.model.strip():
            raise ConfigurationError(
                "Set ANTHROPIC_API_KEY and ANTHROPIC_MODEL for live questions."
            )
        self.settings = settings

    def interpret(self, question: str, metadata: str, schema: dict[str, object]) -> object:
        tools: list[ToolParam] = []
        allowed_names: dict[str, ResponseKind] = {}
        for kind in ResponseKind:
            name = f"interpret_{kind.value}"
            definition = schema[kind.value]
            if not isinstance(definition, dict):
                raise ConfigurationError("Interpretation tool schema must be an object.")
            tools.append(
                {
                    "name": name,
                    "description": f"Return a {kind.value} interpretation",
                    "input_schema": definition,
                }
            )
            allowed_names[name] = kind
        try:
            with anthropic.Anthropic(
                api_key=self.settings.api_key,
                timeout=self.settings.model_timeout,
                max_retries=self.settings.model_retries,
            ) as client:
                message = client.messages.create(
                    model=self.settings.model,
                    max_tokens=1200,
                    system=metadata,
                    messages=[{"role": "user", "content": question}],
                    tools=tools,
                    tool_choice={
                        "type": "auto",
                        "disable_parallel_tool_use": True,
                    },
                )
            calls = [block for block in message.content if block.type == "tool_use"]
            if len(calls) != 1 or calls[0].name not in allowed_names:
                raise InterpretationError(
                    "Model did not supply exactly one interpretation tool call."
                )
            kind = allowed_names[calls[0].name]
            if kind == ResponseKind.METRIC:
                return {"kind": kind.value, "request": calls[0].input}
            explanation = mapping(calls[0].input, {"explanation"}, {"explanation"})
            return {"kind": kind.value, "explanation": explanation["explanation"]}
        except anthropic.APIError as exc:
            raise InterpretationError(
                "Anthropic request failed; verify credentials/model/network or retry."
            ) from exc
