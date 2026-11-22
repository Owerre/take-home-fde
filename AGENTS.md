# Codex repository instructions

## Actual AI configuration
This work uses OpenAI Codex through the desktop/API agent environment. No Claude
Code, Cursor, or Copilot configuration is active. The exact runtime model ID was
not exposed to this session; do not invent one. No subagents were used.
Tools used: shell, Python, Git, uv, Ruff, mypy, pytest and local Docker.
No customer rows were sent to an external model endpoint. Live Anthropic calls
were not run because credentials/model configuration were absent. The SDK was
verified with an injected client and HTTP mock transport. No subagents were used.

## Working agreement
- Read docs/build_brief.md, data/BUSINESS_CONTEXT.md and the original exercise.
- Stop after committing the M1 profile and specs; obtain explicit spec approval
  before pipeline, agent, or eval implementation.
- After approval, specs precede changes; use stable rule IDs and small honest commits.
- Python, DuckDB, set-based SQL, Decimal, typed frozen dataclasses, closed enums.
- No arbitrary model SQL, customer data in model prompts, secrets, or PII in Git.
- Keep raw inputs unchanged and private. Profile only aggregate statistics.
- Record executed checks separately from planned checks; do not claim unrun passes.
- User subsequently said “do not push yet”; do not publish until authorization is renewed.
  Inspect tracked files before publishing; never publish private CSV, secrets or answers.
- Do not delegate to subagents unless the user explicitly requests it.

## Structure and commands
- Keep domain, pipeline, metrics, agent, evaluation and infrastructure packages cohesive.
- Interpretation instructions belong in prompts/query_agent.yaml, not Python strings.
- Flat uppercase constants belong in app/config.py; Settings validates overrides.
- `uv sync --locked` installs the exact environment; `make check test` validates it.
- `python -m app build` and `python -m app eval --tier 1` require no credentials.
- Questions and tier 2 require explicit ANTHROPIC_API_KEY and ANTHROPIC_MODEL.
- `python -m evals --tier 1` runs the evaluation package directly.
- Validate Docker locally; private CSV is a read-only runtime mount, never image input.
- M1 was approved before implementation. Record actual results in docs/eval_report.md.
