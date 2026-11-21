# Codex repository instructions

## Actual AI configuration
This work uses OpenAI Codex through the desktop/API agent environment. No Claude
Code, Cursor, or Copilot configuration is active. The exact runtime model ID was
not exposed to this session; do not invent one. No subagents were used.
Tools used at M1: shell, Python standard library, and Git. No customer rows were
sent to an external model endpoint. Aggregate profiling remains local.

## Working agreement
- Read docs/build_brief.md, data/BUSINESS_CONTEXT.md and the original exercise.
- Stop after committing the M1 profile and specs; obtain explicit spec approval
  before pipeline, agent, or eval implementation.
- After approval, specs precede changes; use stable rule IDs and small honest commits.
- Python, DuckDB, set-based SQL, Decimal, typed frozen dataclasses, closed enums.
- No arbitrary model SQL, customer data in model prompts, secrets, or PII in Git.
- Keep raw inputs unchanged and private. Profile only aggregate statistics.
- Record executed checks separately from planned checks; do not claim unrun passes.
- No publication until user authorizes a concrete reviewed tracked-file set.
- Do not delegate to subagents unless the user explicitly requests it.

## Current runnable command
`python3 scripts/profile_data.py` regenerates docs/data_quality.md without credentials.
Application/demo/evaluation commands are specified but not implemented at M1.
