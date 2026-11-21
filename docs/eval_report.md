# Actual validation record — M1

Status: **specification checkpoint, awaiting approval**. No application or evaluation
harness has been implemented; no tier pass counts are claimed.

Environment: local macOS, Python 3.14.7, Git 2.55.0. No third-party Python packages
required or installed for profiling. Proposed as_of_date: 2026-11-21. Source hash
is recorded in input_checksums.json and the generated quality report. No production
build hash exists. No model calls, token/cost measurements or live latency results.

## Checks actually run

| Check | Actual result |
|---|---|
| `python3 scripts/profile_data.py` | PASS after currency-prefix fix; generated aggregate report |
| `python3 -m py_compile scripts/profile_data.py` | PASS |
| Independent CSV/set counts vs report | PASS: 5,125 rows, 5,000 IDs, 82 exact duplicate losers |
| Proposed row reconciliation | PASS: 5,000 +125 +0 =5,125 |
| Raw vs selected negative-paid counts | PASS: 2 raw; 0 selected after refunded precedence |
| Raw vs parsed conflicting signup counts | PASS: 980 raw; 979 parsed |
| Retained future invoices vs proposed horizon | PASS: 103 |
| Three input SHA-256 checks vs preservation manifest | PASS: original bytes unchanged |
| Repeat generation | PASS: report byte-identical |
| Fresh stdlib-only virtual environment | PASS: `venv.EnvBuilder(with_pip=False)`; removed Anthropic/CloudNova/PYTHONPATH variables; regenerated identical report |
| Report source-PII check | PASS: no source nonblank emails, account names or invoice IDs appear in report |
| `git check-ignore data/cloudnova_invoices.csv` | PASS: private raw CSV excluded |
| Staged whitespace check and final tracked-text scan | PASS: no whitespace errors; no source emails, names or invoice IDs in tracked text |

The independent checks above were an executed inline Python verification, not an
installed test suite. The profile itself is committed and reproducible. Initial
profiling failed on unhandled € and £ amount prefixes; the parser was corrected,
and all checks above ran after that fix. No source values were modified.

## Not run / not implemented

Formatting/lint/strict typing tooling, unit/integration tests, DuckDB builds,
independent six-question reference SQL, tier 1, tier 2 and clean-environment app
demo are **NOT RUN**. Required packages (ruff, mypy, pytest, duckdb, anthropic)
were not installed in the current interpreter. Their implementation/configuration
and a resolved runtime/tooling lock follow M1 approval. Current requirements.lock
accurately contains no M1 dependencies. No fake test or live model passes are used.

No GitHub remote, publication or reviewer invitations were attempted. Application
security/timeout claims are specifications only and have not been verified.

## Effort

M1 active effort is approximately **8 minutes (estimate)** for reading, profiling,
specifying and verification. The observed wall-clock interval began at
20:08:52 UTC and reached 20:14:09 UTC on 2026-11-21; preliminary inspection before
the first clock reading was not timed. Final checkpoint cleanup is additional.
This is not a precise stopwatch measurement or a claim of one-hour compliance.
Time awaiting M1 review is excluded; the complete build remains unfinished under
the user's selected 24-hour maximum. Later work must update cumulative effort.
