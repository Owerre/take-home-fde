"""agent client."""

from typing import Protocol

import anthropic
from anthropic.types import ToolParam

from app.config import Settings
from app.domain.errors import ConfigurationError, InterpretationError


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
        tool: ToolParam = {
            "name": "interpret",
            "description": "Classify a supported metric request",
            "input_schema": schema,
        }
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
                    tools=[tool],
                    tool_choice={
                        "type": "tool",
                        "name": "interpret",
                        "disable_parallel_tool_use": True,
                    },
                )
            calls = [block for block in message.content if block.type == "tool_use"]
            if len(calls) != 1 or calls[0].name != "interpret":
                raise InterpretationError(
                    "Model did not supply exactly one interpretation tool call."
                )
            return calls[0].input
        except anthropic.APIError as exc:
            raise InterpretationError(
                "Anthropic request failed; verify credentials/model/network or retry."
            ) from exc
