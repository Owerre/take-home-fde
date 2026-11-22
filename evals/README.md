# Evaluation inputs and running

```sh
uv run --locked python -m app eval --tier 1
uv run --locked python -m app eval --tier 2
# Equivalent runnable evaluation package:
uv run --locked python -m evals --tier 1
```

`reference.sql` independently queries all six stakeholder populations. Python
fixture generators and hand-computed goldens live in `app/evaluation/fixtures.py`;
canonical/live cases are in `app/evaluation/cases.py` and `runner.py`.
Deeper pipeline/security tests live in `tests/`; run `uv run --locked pytest -q`.

Tier 1 needs no key or network. It compares aggregates and evidence to independent
SQL, then builds a synthetic ledger and compares hand goldens. HISTORY is a
known unsupported exact-history capability scored as an expected failure, not a
live natural-language test. Expected failures remain in the denominator and
failure count. Only unexpected errors/failures make exit 1.

Tier 2 requires ANTHROPIC_API_KEY and ANTHROPIC_MODEL. Without them it prints
NOT RUN, never PASS (`--require-live` makes that condition exit 1). Cases include
canonical questions, two paraphrases each, repeats of Q1/Q2/Q5, a filter,
ambiguity, unsupported finance, injection, personal-data and history questions.
Expected values come from independent reference SQL, not generated SQL.
Requests are never cached. Unsafe requests may be refused locally before model
use; those behavior tests are not described as model calls.

Rules: [specs/evals.md](../specs/evals.md).
Actual checks: [docs/eval_report.md](../docs/eval_report.md).
