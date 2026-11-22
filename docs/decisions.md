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

The unchanged CSV contains contact data and stays Git-ignored. Track the briefing
and original exercise. Docker mounts the source read-only; the
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

## Approved business defaults

The following defaults were approved at M1 before implementation. Stable rule IDs
link each decision to its schema or metric contract.

| Decision | Approved default | Consequence / uncertainty |
|---|---|---|
| Dates | DD-MM-YYYY; slash MM/DD/YYYY; explicit other formats (S-DATE-01) | 88 raw invoice-date and 131 raw signup-date hyphen strings are ambiguous; interpretation is a convention |
| Invoice conflicts | void > refunded > paid > failed > pending; first ordinal breaks equivalent-status ties (S-DEDUP-01) | Conservative deterministic precedence, not chronological truth. Of 43 conflicts: 27 normalize to paid/paid, 5 paid/void, 2 paid/refunded, 2 paid/failed, 7 paid/pending |
| Negative paid records | Reject when selected, never change sign/status (S-SIGN-01) | Both observed negative paid rows lose to refunded versions; don't count those source rows again as rejects |
| Account key and snapshot | account_id; latest eligible invoice, descending ID tie-break; all attributes copied together (S-ACCT-01) | Conflicting names do not create new customers; latest missing CSAT stays unknown |
| Active subscription proxy | latest snapshot paid and churned=false; otherwise MRR=0 (S-MRR-01) | No subscription or cancellation timeline. Annual MRR uses list×seats×discount without /12 |
| Average MRR denominator | All eligible account snapshots per region, including inactive at zero (M-MRR-01) | Answer means USD/account/month across observed accounts, not average among only active subscribers |
| Revenue timing | invoice_date; Q1 paid only; Q3 positive refund magnitude; Q5 net paid+negative refunds (M-TIME-01) | No payment timestamp or accrual recognition history |
| Reference date | Explicit 2026-11-21 inclusive, overridable and part of build hash (S-ASOF-01) | Excludes 103 retained future invoices from answers; retains them in staging |
| Currency inconsistency | Apply required local→USD multiplication; report observed pattern once (S-FX-01, S-PRICE-01) | No inverse-FX repair; non-USD ledger amounts end above USD list; MRR unaffected |
| Churn question | Snapshot churn-flag prevalence per latest plan (M-CHURN-01) | Cannot establish historical or period churn events |

## Account-key sensitivity

Reference date: **2026-11-21**, inclusive. This diagnostic uses the approved policies;
it is not evidence that the composite key identifies distinct customers.

Eligible snapshots: **3,752 account_id groups vs 4,889 composite groups**. All-date
groups before horizon filtering are 3,815 vs 4,992. These are different grains,
not proof of 4,992 distinct customers.

| Q2 region | Baseline USD/account/month | Composite | Movement |
|---|---:|---:|---:|
| APAC | 3,526.12 | 3,355.90 | −170.22 |
| EMEA | 3,097.07 | 3,142.97 | +45.90 |
| LATAM | 2,813.69 | 2,827.90 | +14.21 |
| NA | 3,309.19 | 3,186.43 | −122.76 |

APAC remains highest. Q4 Enterprise: **169/769 = 21.98%** vs **211/981 = 21.51%**
(−0.47 percentage points). Starter: **351/1,858 = 18.89%** vs **451/2,442 = 18.47%**
(−0.42 points). Movements here subtract displayed rounded percentages.

| Q5 rank | Baseline net revenue USD | Composite net revenue USD | Movement |
|---|---:|---:|---:|
| 1 | 1,210,592.75 | 1,205,642.75 | −4,950.00 |
| 2 | 1,208,092.75 | 1,205,642.75 | −2,450.00 |
| 3 | 1,205,642.75 | 1,205,642.75 | 0.00 |
| 4 | 1,107,352.84 | 1,085,078.48 | −22,274.36 |
| 5 | 1,085,078.48 | 1,085,077.84 | −0.64 |

Baseline rank 2 CSAT is unknown; composite rank 1 CSAT is unknown. All remaining
ranked rows have known CSAT >2. Rank comparisons may be different entities;
customer identities are intentionally omitted from committed profiling outputs.
