# Validation report

**Local submission validated; publication is on hold.** All six stakeholder metric
cases pass independent SQL and evidence checks. Tier 1 reports **12/13 PASS,
1 expected limitation failure, 0 unexpected failures**. The regression suite passes
**34 tests**. Live Anthropic accuracy is **NOT RUN** because credentials and model
configuration were absent.

## Configuration and reproducibility

- Reference date: **2026-11-21**, inclusive; fixed FX and approved M1 conventions.
- Local Python 3.14.7; container Python 3.13.18, non-root UID 10001.
- uv 0.13.9; DuckDB 1.5.6; Anthropic SDK 0.125.0; PyYAML 6.0.4; exact graph in uv.lock.
- Source SHA-256: `f542bc1f8193ab367e0a009a7afe56620335ce23b5817f5edc0ed4f896c89d84`.
- Verified host/container build identity: `3477ce9fcf5ef23af9e92fd5cd52d943823d9df3b36006db8d0364cf93dbaf04`.
- Baseline account_id key; no answer cache. No model, cost or live latency figures
  were measured. HTTP mock transport results are not live model results.

## Checks actually executed

| Check / command | Result |
|---|---|
| `uv sync --locked` in a fresh temporary virtual environment | PASS; exact dependencies installed |
| `ruff format --check app tests evals scripts` | PASS; 35 files formatted |
| `ruff check app tests evals scripts` | PASS |
| `mypy` with strict configuration | PASS; 34 source files |
| `pytest -q` | PASS; 34 tests |
| `python -m app build` on the real source | PASS; atomic artifact and complete row reconciliation |
| `python -m app eval --tier 1` | 12 PASS; 1 expected FAIL; exit 0 |
| Documented `uv run --locked python -m app eval --tier 1` in fresh environment, credentials removed | Same result; exit 0 |
| `python -m evals --tier 1` in fresh environment | Same result; exit 0 |
| `python -m app eval --tier 2` | NOT RUN; no key/model configured |
| Natural-language command without key/model | Expected actionable ConfigurationError; exit 1 |
| `docker build -t cloudnova-track-b:local .` | PASS |
| Non-root image / source and .env exclusion check | PASS; UID 10001; no private source or .env baked in |
| Docker tier 1 with read-only CSV and writable named volume | Same 12 PASS / 1 expected FAIL; exit 0 |
| Input hash verification and tracked-text privacy/token scan | PASS; original inputs unchanged; private CSV untracked |
| Additional synthetic FX-overflow build (inline check) | PASS; prior artifact bytes preserved and temporary files removed |
| Profiler regeneration, repeatability and clean stdlib environment | PASS (M1); regenerated after final formatting |

The test suite covers types/categories/ranges/signs, ambiguous dates and future
records, fixed FX and half-up rounding, annual ten-month billing and list-derived
MRR, exact/near duplicates, all-invalid groups, row reconciliation, snapshot ties,
NULL CSAT, denominators, top-N/order/filters, bound injection values, file/write/config
restrictions, SQL interruption and cleanup, build reuse/invalidation, lock deadlines,
atomic preservation, strict model output, and bounded SDK retries via mock transport.
Independent reference SQL and evidence membership checks run for all six questions.

## Stakeholder outcomes

These values use the approved policies and reference date, not an inference of
true historical customer/subscription state. Source customer identities are omitted
from this committed report; local answers contain bounded invoice-ID evidence.

| Case | Independently verified result | Contributing population |
|---|---|---|
| Q1 — paid recognized revenue in 2024 | **USD 32,686,371.20** | 891 paid invoices dated in 2024 |
| Q2 — highest mean MRR/account | **APAC: USD 3,526.12/account/month** | 921 account snapshots; total MRR USD 3,247,560.15 |
| Q3 — refunds given back | **USD 8,453,611.21**, positive magnitude | 287 refunded invoices |
| Q4 — Enterprise vs Starter churn | **21.98% (169/769)** vs **18.89% (351/1,858)** | Snapshot plan and churn flags; all accounts in each denominator |
| Q5 — top five net-revenue accounts | Ranking and population match reference SQL; top USD 1,210,592.75 | Revenue invoice counts by rank: 2, 2, 1, 2, 1; rank 2 CSAT unknown; others >2 |
| Q6 — pending/failed exposure | **873 invoices; USD 28,682,929.79** | Pending/failed invoices only |

Plain-language definitions and exact hand-reproduction filters for Q1/Q3/Q6 are
in [metrics.md](../specs/metrics.md). [M1 sensitivity](decisions.md#account-key-sensitivity) quantifies
Q2/Q4/Q5 movement under the composite account-name key. Full-data build:
**5,125 = 5,000 retained + 125 duplicate losers + 0 rejects**; 103 future invoices
remain stored and are excluded from answers; 3,752 eligible account snapshots;
952 have conflicting attributes within the eligible horizon. The 1,524 non-USD
invoices fit one systematic source FX issue, with **0 residual pricing discrepancies**
under source-precision tolerance. No source amount was replaced.

## Tier 1 per-case results

| Case | Status | Evidence |
|---|---|---|
| Q1–Q6 (six separate printed cases) | PASS each | Independent SQL totals/groups, denominators and sample population |
| FIX-RECON | PASS | Hand golden: 24 source = 16 retained + 3 losers + 5 rejects |
| FIX-PAID | PASS | Hand golden USD 1,524.84 |
| FIX-REFUNDS | PASS | Hand golden USD 35.40 |
| FIX-EXPOSURE | PASS | Hand golden USD 157.00 |
| FIX-MRR | PASS | Hand golden highest region MRR/account USD 88.20 |
| FIX-CSAT | PASS | Low/known/unknown flags preserved on ranked accounts |
| HISTORY | **FAIL — expected limitation** | Exact historical MRR needs subscription history not present in the ledger |

HISTORY is an explicit capability limitation scored as a failure and included in
the denominator. It is not represented as a live NL execution or a model accuracy
result. Ordinary unsupported/unsafe refusals are separate PASS expectations.
No stakeholder question is marked as an expected failure. Unexpected failures or
errors produce nonzero exits; missing live configuration is reported as NOT RUN.

## Failures encountered and resolved

The first profiler rejected € and £ prefixes; parsing was corrected. Per-cell raw
inserts were slow, so ingestion became a bulk text load. One test incorrectly
matched an invoice-ID substring inside a rule ID; the test was fixed. Strict typing
errors were corrected, not suppressed. Generated alias CSV line endings were
normalized for a clean Git diff. An initial clean-demo attempt was blocked by the
execution sandbox's uv-cache permissions before the app ran; the documented demo
then passed with cache access. All affected checks were rerun successfully.

## Remaining limits and effort

Live NL/paraphrase/repeat accuracy, real provider credentials, model latency and
cost remain unmeasured. Tier 2 contains 30 defined cases and runs only when a key
and model are provided. Snapshot MRR/churn cannot establish exact historical
subscription states, causal churn or cash settlement. Status precedence is a
convention without event timestamps; account identity remains uncertain. Raw data
must be supplied through an authorized channel to reproduce a fresh clone.

The user selected a 24-hour maximum. Estimated active effort so far is roughly
**55 minutes**, including tool waits and excluding the multi-hour M1 review wait;
this is an estimate, not a stopwatch measurement or a one-hour-compliance claim.
M1 was approximately 8 minutes; the observed implementation/check interval began
at 00:30:44 UTC on 2026-11-22 and reached 01:11:42 UTC, with preliminary setup and
final cleanup outside those clock readings. No GitHub push or image publication
was performed. Another day should prioritize Finance reconciliation of customer
identity/status conflicts and obtaining subscription/payment history.
