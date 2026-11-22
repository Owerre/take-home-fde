# CloudNova Track B

A local, spec-driven invoice pipeline and natural-language metric agent. Python
and set-based DuckDB SQL preserve raw lineage, normalize/deduplicate invoices,
build account snapshots, and answer all six stakeholder questions with the exact
query, parameters, definitions, caveats and bounded invoice evidence.

## Setup and a single demo command

Use Python 3.13 or 3.14 on macOS/Linux and uv **0.13.9** (`python3 -m pip install uv==0.13.9`).
From this repository, place the authorized exercise CSV at
`data/cloudnova_invoices.csv` (already present locally, deliberately Git-ignored):

```sh
uv sync --locked
uv run --locked python -m app eval --tier 1
```

The demo checks six metrics against independent SQL, hand-computed fixtures,
and invoice evidence. No credentials required. An expected historical-MRR
failure is counted; unexpected failures exit nonzero.

## Natural-language questions

Copy `.env.example` to `.env`, set `ANTHROPIC_API_KEY` and an [API model ID](https://platform.claude.com/docs/en/models/overview)
(not a display name) in `ANTHROPIC_MODEL`, then run:

```sh
uv run --env-file .env --locked python -m app "What was our total recognized revenue in USD for paid invoices in 2024?"
```

This builds automatically when source/rules change. Anthropic receives the question
and metadata only; validated structured output becomes deterministic SQL. Answers
are formatted locally. Model-generated SQL is never accepted. Missing credentials
cause an actionable nonzero exit. `--env-file .env` loads the settings explicitly;
omit that option if both variables are already exported. File/default constants live in [app/config.py](app/config.py);
interpretation instructions live in [prompts/query_agent.yaml](prompts/query_agent.yaml).

Other commands:

```sh
uv run --locked python -m app build
uv run --locked python -m app eval --tier 2
make check test
```

Build and tier 1 need no key. Tier 2 is live and requires a key/model; without them
it prints **NOT RUN**, never PASS. Add `--require-live` to fail when unavailable.
The SDK uses bounded retries; query connections restrict access and execution.

## Rules, results and trade-offs

The user approved M1 before implementation. [Schema](specs/schema.md),
[metrics](specs/metrics.md), [query/security](specs/nl_query.md), and
[evals](specs/evals.md) carry stable rule IDs; Q1/Q3/Q6 include hand-reproduction
instructions. [Actual checks and results](docs/eval_report.md) record offline
and live validation.

Offline: 12/13; live: 29/30. Both include one expected historical-MRR failure.

The source reconciles **5,125 = 5,000 retained + 125 duplicate losers + 0 rejects**.
At reference date **2026-11-21**, 103 future invoices remain stored and are excluded
from answers. Fixed FX follows the briefing despite the source-generation anomaly;
no billed amount is silently repaired. Annual bills ten months; MRR uses list
price × seats × (1 − discount_pct/100) once/account, independent of billing cycle.

Baseline account identity is account_id, with coherent latest eligible invoice
snapshots. Active MRR is a paid/nonchurned proxy; regional averages include inactive
accounts at zero. Conflicting names and dates do not prove separate customers.
[Account-key sensitivity](docs/decisions.md#account-key-sensitivity) quantifies Q2/Q4/Q5 movement. Churn is
observed flag prevalence; exact historical MRR, churn events and cash settlement
cannot be recovered from this ledger. Missing CSAT stays unknown. MRR/rates use
exact Decimal finalization of SQL totals and denominators.

## Docker

```sh
docker build -t cloudnova-track-b:local .
docker run --rm \
  --mount type=bind,src="$PWD/data/cloudnova_invoices.csv",dst=/input/invoices.csv,readonly \
  --mount type=volume,src=cloudnova-build,dst=/app/build \
  cloudnova-track-b:local eval --tier 1
```

The image runs as a non-root user. Private CSV, databases and secrets are excluded
from its build context. The same command with `build` builds only. Pass environment
variables using Docker's `--env ANTHROPIC_API_KEY --env ANTHROPIC_MODEL` for live
questions; never bake keys into the image.

[Architecture and package map](docs/architecture.md), [AI configuration](AGENTS.md),
[consolidated brief](docs/build_brief.md), [trimmed prompt record](docs/prompt_log.md),
and [decisions](docs/decisions.md) explain how this was built. Actual effort is
reported in the evaluation report; no one-hour-compliance claim is made. With
another day, prioritize Finance reconciliation of identity/status conflicts and
subscription/payment history. Publication is on hold at the user's request;
[the intended GitHub repository](https://github.com/Owerre/take-home-fde) has not
been pushed by this agent.
