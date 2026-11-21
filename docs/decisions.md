# Significant decisions

## D-001 — M1 precedes implementation (proposed checkpoint)

The user explicitly requires review of committed specs before implementation.
Only aggregate profiling, preservation and specification work are in scope now.
This preserves evidence that the specs drove the implementation. Pipeline and
evaluation results must not be invented while awaiting review.

## D-002 — Source authority over source-generation pattern (proposed)

The briefing requires multiplying local amounts by fixed USD conversion rates,
despite the export matching USD list×FX. Preserve ledger amounts, report the
systematic discrepancy once, and derive MRR from list price directly. An inverse
conversion would silently change the exercise's authoritative rule.

## D-003 — Account uncertainty is visible (proposed)

Use account_id and coherent latest-row snapshots, preserve NULL CSAT, and quantify
composite-key sensitivity. Do not infer a new customer identity from each name
or claim the ledger establishes historical subscription/churn state.

## D-004 — Private raw input and honest Git attribution (applied)

The source CSV contains contact emails, so it stays unchanged locally and is
ignored by Git. The original exercise, briefing and input checksums are tracked.
No Git author identity was configured. Commits explicitly use `Codex
<codex@localhost>` with real timestamps; no global identity setting was changed.
The user can configure their preferred identity for later commits. Raw source
distribution to reviewers must use an authorized private mechanism.

## D-005 — Effort and dependency status (applied)

The user selected a 24-hour maximum instead of the exercise's approximate hour.
Report observed active work, excluding time waiting for review. At M1 Python
standard-library profiling is reproducible without dependencies. Runtime/tooling
packages and their real resolved lock will be installed after spec approval; the
current empty requirements.lock deliberately describes only the M1 state.
