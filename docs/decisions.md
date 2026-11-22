# Significant decisions

## D-001 — Specifications before implementation

The four M1 contracts were committed in `867d07d`; explicit approval was recorded
in `f754d6f` before application implementation. The current consolidated brief
incorporates the user's requirements. Git retains the actual revisions and dates.
Code changes follow stable rule IDs; source preservation and profiling were separate
commits. Application commit `cad1370` follows the committed specifications and approval.

## D-002 — Business authority over source-generation pattern

The briefing requires multiplying local amounts by fixed USD conversion rates,
although the export fits USD list×FX. The implementation preserves ledger amounts,
reports that systematic issue once, and derives MRR from USD list price. Residual
source anomalies are checked separately. No inverse conversion or amount repair.

## D-003 — Visible account uncertainty

Use account_id and coherent latest eligible invoice snapshots. Preserve NULL CSAT
and quantify composite-key sensitivity. Conflicting names do not prove separate
customers. Paid/nonchurned MRR is an active-subscription proxy; observed churn-flag
prevalence is not historical churn. These limits appear in metric contracts and
answers, rather than being hidden behind a successful query.

## D-004 — Narrow interpretation and exact arithmetic

Anthropic interprets metadata into a validated request; allowlisted SQL templates
execute locally. No arbitrary SQL fallback or customer rows in model context.
Read-only access, external-access restrictions, value binding, output bounds and
interrupt deadlines implement the hardening requirement. Python Decimal finalizes
SQL numerators/denominators because DuckDB decimal division returns floating-point
values ([DuckDB numeric types](https://duckdb.org/docs/stable/sql/data_types/numeric.html)).
The SDK adapter follows the [official Python SDK](https://platform.claude.com/docs/en/api/sdks/python);
actual live behavior remains unverified without credentials.

## D-005 — Source privacy and honest attribution

The unchanged CSV contains contact data and stays Git-ignored. Track the briefing,
original exercise and source checksums. Docker mounts the source read-only; the
image excludes CSV, databases, .env and keys. Git identity was not configured, so
commits explicitly use `Codex <codex@localhost>`; global identity was not changed.
Publication is on hold. Reviewers need the exercise CSV through an authorized channel.

## D-006 — Maintainable scope and reproducibility

Separate domain, pipeline, metrics, agent, evaluation and infrastructure packages.
Keep configuration constants flat and interpretation prompts in YAML. Use uv.lock
for runtime/development dependencies and the same CLI in the non-root Docker image.
No API, UI, vector store, cloud deployment, CI or cache was added. Another day
should prioritize reconciled customer identity and subscription/payment history.
Actual checks, failures, limitations and effort are recorded in eval_report.md.
