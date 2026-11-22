"""Run with python -m evals --tier 1 (same implementation as the application CLI)."""

import sys

from app.cli import main

raise SystemExit(main(["eval", *sys.argv[1:]]))
