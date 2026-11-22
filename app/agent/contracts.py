"""agent contracts."""

import json
from dataclasses import asdict
from pathlib import Path

import yaml

from app.config import PROMPT_FILE
from app.domain.errors import ConfigurationError
from app.domain.models import Dimension, Metric, ResponseKind
from app.metrics.catalog import definition


def tool_schema() -> dict[str, object]:
    """Separate closed tools avoid unsupported top-level union schemas."""
    request_schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["metric"],
        "properties": {
            "metric": {"type": "string", "enum": [v.value for v in Metric]},
            "group_by": {"type": ["string", "null"], "enum": [None, *[v.value for v in Dimension]]},
            "filters": {
                "type": "array",
                "maxItems": 10,
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": ["dimension", "operator", "values"],
                    "properties": {
                        "dimension": {"type": "string", "enum": [v.value for v in Dimension]},
                        "operator": {"type": "string", "enum": ["eq", "in"]},
                        "values": {
                            "type": "array",
                            "minItems": 1,
                            "maxItems": 20,
                            "items": {"type": "string", "maxLength": 128},
                        },
                    },
                },
            },
            "start_date": {"type": ["string", "null"]},
            "end_date": {"type": ["string", "null"]},
            "order": {"type": "string", "enum": ["asc", "desc"]},
            "limit": {"type": "integer", "minimum": 1, "maximum": 100},
        },
    }
    explanation_schema: dict[str, object] = {
        "type": "object",
        "additionalProperties": False,
        "required": ["explanation"],
        "properties": {"explanation": {"type": "string", "minLength": 1, "maxLength": 1000}},
    }
    return {
        ResponseKind.METRIC.value: request_schema,
        ResponseKind.CLARIFICATION.value: explanation_schema,
        ResponseKind.UNSUPPORTED.value: explanation_schema,
    }


def system_metadata(root: Path) -> str:
    """Load the versioned external prompt; attach schema/metric metadata only."""
    path = root / PROMPT_FILE
    try:
        data = yaml.safe_load(path.read_text())
    except (OSError, yaml.YAMLError) as exc:
        raise ConfigurationError("Cannot load prompts/query_agent.yaml.") from exc
    if (
        not isinstance(data, dict)
        or set(data) != {"version", "system"}
        or data["version"] != 1
        or not isinstance(data["system"], str)
        or not 1 <= len(data["system"]) <= 16000
    ):
        raise ConfigurationError("Prompt YAML must contain version 1 and bounded system text.")
    return data["system"] + json.dumps([asdict(definition(m)) for m in Metric])
