# CloudNova Track B

**M1 checkpoint: profile and proposed specs are ready for review. The application
is not implemented yet.** This project will clean a private invoice ledger with
Python, DuckDB and set-based SQL, then answer six stakeholder questions through
an Anthropic interpretation layer and a deterministic metric compiler.

Start with [M1 decisions and sensitivity](docs/m1_review.md). Explicit approval
is required before implementing the pipeline, agent and evaluations.

## Run what exists

Use Python 3.13 or 3.14 (verified locally on 3.14.7). No packages or key required:

```sh
python3 scripts/profile_data.py
```

This regenerates [data quality](docs/data_quality.md) from
`data/cloudnova_invoices.csv`. Raw CSV is private and Git-ignored; reviewers need
their authorized exercise CSV at that path. Verify bytes with
[input checksums](docs/input_checksums.json). Original sources were moved unchanged.

## Commands after approval (specified, not runnable yet)

```sh
python -m app build
python -m app eval --tier 1
python -m app "What was our total recognized revenue in USD for paid invoices in 2024?"
python -m app eval --tier 2
```

The question/demo and live tier 2 need ANTHROPIC_API_KEY and ANTHROPIC_MODEL.
Build and offline tier 1 will not. `.env.example` documents proposed settings;
no dotenv loader exists yet. The final clean-environment setup and package lock
will be supplied with implementation.

## Contract and findings

[Schema](specs/schema.md), [metrics](specs/metrics.md), [query/security](specs/nl_query.md),
[evals](specs/evals.md) define stable rule IDs. Q1/Q3/Q6 include hand-reproduction
filters. The profile verified 5,125 rows, 5,000 invoice IDs, 82 exact duplicate
losers and 43 status-only conflicts. Account attributes conflict extensively.
The M1 review quantifies Q2/Q4/Q5 movement under the alternate account-name key.

Proposals: day-first hyphens; void/refunded precedence; latest eligible invoice
snapshot keyed by account_id; paid/nonchurned active proxy; all-account average
MRR denominator; invoice-date revenue; reference date 2026-11-21. Fixed FX follows
the briefing despite the systematic source anomaly. Annual invoices bill ten
months; annual MRR is still list×seats×discount once per active account.

## Validation and limits

[Evaluation report](docs/eval_report.md) distinguishes actual checks from planned
ones. There are no pipeline, tier-1 or live eval results yet. Missing subscription
history prevents exact historical MRR and period churn. Future invoice dates
require an explicit horizon. No GitHub publication has been authorized or attempted.

[Architecture](docs/architecture.md) marks implemented vs proposed paths.
[AGENTS.md](AGENTS.md), [build brief](docs/build_brief.md),
[prompt record](docs/prompt_log.md) and [decision records](docs/decisions.md) show
actual AI use and scope. M1 active effort is recorded in the evaluation report;
review waiting time is excluded. No claim of one-hour compliance is made.
After completing the narrow required submission, another day would be best spent
reconciling customer identity and obtaining subscription/payment history with Finance.
