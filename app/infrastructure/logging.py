"""Aggregate-only structured operational events."""

import json
import sys


def event(name: str, **fields: str | int | bool) -> None:
    print(json.dumps({"event": name, **fields}, sort_keys=True), file=sys.stderr)
