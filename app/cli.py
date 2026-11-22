"""Thin CLI: configure resources, dispatch, serialize; no business formulas."""

import argparse
import json
import sys
import uuid
from dataclasses import asdict
from datetime import date
from decimal import Decimal

from app.agent.client import AnthropicClient
from app.agent.service import QueryAgent
from app.config import Settings
from app.domain.errors import CloudNovaError, QueryError
from app.infrastructure.logging import event
from app.metrics.compiler import MetricCompiler
from app.pipeline.builder import Pipeline


def json_default(value: object) -> str:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    raise TypeError("Unexpected result type")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="CloudNova pipeline and constrained metric query agent"
    )
    parser.add_argument("command", help="build, eval, or a quoted natural-language question")
    parser.add_argument("--tier", type=int, choices=(1, 2))
    parser.add_argument("--require-live", action="store_true")
    parser.add_argument("--force", action="store_true", help="Force an atomic rebuild")
    args = parser.parse_args(argv)
    request_id = str(uuid.uuid4())
    try:
        settings = Settings.from_env()
        if args.command == "eval":
            if args.tier is None:
                parser.error("eval requires --tier 1 or --tier 2")
            from app.evaluation.runner import EvalRunner

            return EvalRunner(settings).run(args.tier, require_live=args.require_live)
        if args.tier is not None or args.require_live:
            parser.error("--tier and --require-live apply only to eval")
        pipeline = Pipeline(settings)
        report = pipeline.build(force=args.force)
        if args.command == "build":
            print(json.dumps(asdict(report), default=json_default, indent=2))
        else:
            client = AnthropicClient(settings)
            answer = QueryAgent(MetricCompiler(settings), client).ask(args.command, report)
            serialized = json.dumps(asdict(answer), default=json_default, indent=2)
            if len(serialized.encode()) > 65536:
                raise QueryError(
                    "Answer exceeds output limit; use a smaller top N or narrower filters."
                )
            event(
                "request", request_id=request_id, build_id=report.build_id, status=answer.kind.value
            )
            print(serialized)
        return 0
    except CloudNovaError as exc:
        event("failure", request_id=request_id, code=type(exc).__name__)
        print(f"{type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
