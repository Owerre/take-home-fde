# User guidance and AI build log

This selected chronological record connects the user’s direction to the AI’s work
and the resulting evidence. Guidance is **paraphrased, not quoted**. It was expanded
from the visible conversation and Git history after the initial publication;
it is not a complete transcript or a contemporaneous record of every tool call.
Messages the user asked to exclude are omitted. No earlier AI session transcript
was supplied, so missing history has not been reconstructed.

The [original supplied brief](https://github.com/Owerre/take-home-fde/blob/35e1b93ea40737a152bdf40da5d23d3c1de638c0/docs/build_brief.md) is
preserved in [35e1b93](https://github.com/Owerre/take-home-fde/commit/35e1b93ea40737a152bdf40da5d23d3c1de638c0). The [current build brief](build_brief.md)
consolidates the final requirements and is not presented as the untouched original.
Commit links below identify actual work; one user instruction may span several commits.
Steps 1–3 and 5–6 unpack sections of the same initial brief; step 4 is the review
checkpoint. They are build stages rather than separate user messages.

## Step-by-step record

| Step | User direction (paraphrase) | AI action and correction | Result / evidence |
|---|---|---|---|
| 1. Establish scope | Supplied the Track B brief: use Python, DuckDB and set-based SQL; follow the exercise and business briefing; preserve inputs; use a maximum of 24 hours and report effort honestly. | Read the original exercise and briefing, inspected the folder and Git state, initialized Git, moved the two data inputs unchanged into data/, and recorded the brief and Codex instructions. | [35e1b93](https://github.com/Owerre/take-home-fde/commit/35e1b93ea40737a152bdf40da5d23d3c1de638c0); [current consolidated brief](build_brief.md) and [AI configuration](../AGENTS.md). |
| 2. Verify the data | Provided prior profiling findings and required independent verification, including duplicate conflicts, dates, account identity and the systematic currency pattern. | Wrote a reproducible aggregate-only profiler. Verified 5,125 rows, 5,000 invoice IDs, 82 exact duplicate losers and 43 status-only conflicts. Distinguished 980 conflicting signup strings from 979 conflicting parsed dates. Kept the briefing’s FX rule instead of silently reversing it. | [c8151e2](https://github.com/Owerre/take-home-fde/commit/c8151e2c9193913583910a6a63174f2c8353e56c); [profiler](../scripts/profile_data.py) and [data-quality report](data_quality.md). |
| 3. Specify before coding | Required four committed specifications with stable rule IDs and an M1 review before implementation. Business choices had to be explicit rather than inferred silently from dirty data. | Wrote schema, metrics, query/security and evaluation contracts. Presented date parsing, status precedence, negative-paid handling, account snapshots, active-MRR proxy, revenue timing and reference-date defaults for review. | [867d07d](https://github.com/Owerre/take-home-fde/commit/867d07d3e019fe9d08b03faa39e5dc47af69031e); [schema](../specs/schema.md), [metrics](../specs/metrics.md), [query contract](../specs/nl_query.md), [eval contract](../specs/evals.md). Application code had not yet been committed. |
| 4. Review the business defaults | Approved the M1 proposals before implementation proceeded. | Used account_id as the baseline key, coherent latest-eligible-invoice snapshots, unknown CSAT preservation and the approved active-subscription proxy. Quantified Q2/Q4/Q5 movement under the composite account-name key rather than changing customer identity silently. | Approval recorded in [f754d6f](https://github.com/Owerre/take-home-fde/commit/f754d6f9cc9e382246cdda3e4edcbc0b10b4dcb6); [approved decisions and sensitivity](decisions.md). |
| 5. Implement the approved contracts | Required a narrow pipeline and query agent: raw → staging → marts → validated metric request → deterministic SQL → evidence-backed answer. The model must not generate executable SQL or receive customer rows. | Built raw lineage, typed/deduplicated invoices, account snapshots, rejects and duplicate decisions, seed-driven normalization/pricing/FX, atomic builds, typed contracts and the query compiler. Kept interpretation separate from SQL execution and answer formatting. | [cad1370](https://github.com/Owerre/take-home-fde/commit/cad1370859cd8617cbbfa14f070604751c3b0d22); [architecture](architecture.md), [pipeline](../app/pipeline/builder.py), [SQL transforms](../sql/transform.sql) and [metric compiler](../app/metrics/compiler.py). |
| 6. Prove correctness independently | Required hand-computed fixtures, independent reference SQL for all six stakeholder questions, credential-free tests, explicit limitations and honest reporting of checks actually run. | Added synthetic ledger fixtures, independent reference queries, security/reliability tests and runnable evaluations. Verified offline results and Docker operation. The initial regression suite passed 34 tests; live model evaluations were initially reported NOT RUN while credentials were unavailable. | [401a900](https://github.com/Owerre/take-home-fde/commit/401a9008fe2ae3e4c926521d7128280bbe798c3b) and [306bfa5](https://github.com/Owerre/take-home-fde/commit/306bfa578040bed6e911609b8d00203e6e84bb0d); [reference SQL](../evals/reference.sql), [tests](../tests/) and [actual evaluation results](eval_report.md). |
| 7. Reduce documentation clutter | Asked which files were required and requested removal of optional copies and redundant documentation. | Removed the optional checksum manifest and extracted exercise copy, merged M1 decisions and sensitivity into decisions.md, removed the redundant evaluation README, and updated references. Preserved the original exercise, required decision content and runtime build hashing. | [d2f7b86](https://github.com/Owerre/take-home-fde/commit/d2f7b86636820ef539567214b74db53e29cee0f3), [eff91f6](https://github.com/Owerre/take-home-fde/commit/eff91f6716ed24c007fecb1a6a9e426bcadb11e9) and [ffce498](https://github.com/Owerre/take-home-fde/commit/ffce498df03f97cd2e6ec62d3a1a22e5ac61c3d9). The current docs retain required content without those extra files. |
| 8. Challenge the readiness claims | Requested a careful check against the required deliverables. | Inspected the actual harness and found that the offline HISTORY outcome merely declared a limitation. Replaced it with an executed dated-MRR request and regression checks that detect unexpected acceptance. Also corrected the shortened README MRR formula to show (1 − discount_pct/100). | [6447702](https://github.com/Owerre/take-home-fde/commit/6447702760b32789537c48dc05cf0f4a6cc89145); the suite increased to 36 tests. The history case remained a scored expected failure, now grounded in a real backend rejection. |
| 9. Clarify how to run it | Asked whether the README included a one-line run command and what remained before submission. | Identified the documented natural-language and offline demo commands. Distinguished verified metric correctness from unverified live interpretation, and identified live validation and GitHub delivery as the remaining work at that stage. | [README](../README.md) and [validation report](eval_report.md). This clarification preceded the live setup work; it was not a new implementation commit. |
| 10. Troubleshoot the real live run | Reported a ConfigurationError after setting up the local API configuration. | Checked whether settings were present without displaying the key. Corrected explicit .env loading and the model API ID. Live testing exposed unsupported forced-tool selection and top-level union schemas; switched to automatic selection among three simple tools while retaining local validation and deterministic SQL. Expanded SDK adapter tests and ran the live suite. | [2817c4d](https://github.com/Owerre/take-home-fde/commit/2817c4d87ce439a8c44655b3b39161709a07a58a); 38 tests passed. The real 2024 paid-revenue question returned USD 32,686,371.20 from 891 invoices. Tier 2 passed 29/30 cases, with one expected historical-MRR limitation and zero unexpected failures. |
| 11. Publish the real build history | Asked whether the project was ready to push and emphasized preserving small, honest commits. | Reran local quality gates and offline evaluations, checked tracked files and the full reachable history for the real API key and source customer identifiers, verified the empty public target repository, then pushed the existing history to main without squashing. | [b4b932a](https://github.com/Owerre/take-home-fde/commit/b4b932abccf685b77ae60cfb306b751b381845fd); verified 15 commits on GitHub and a matching local/remote HEAD at the initial publication. Later documentation commits are additional history. |

## How the user’s direction affected the result

- **Authority over data assumptions:** the briefing’s FX and annual-billing rules
  controlled implementation even when source amounts suggested a different convention.
- **Visible business uncertainty:** account_id stayed the baseline; conflicting
  attributes, composite-key sensitivity, unknown CSAT and the MRR/churn proxies
  were documented instead of being treated as verified customer history.
- **Checks over assertions:** the readiness review changed the expected-failure
  case from a declared limitation into an executed backend test.
- **A real run over mock-only confidence:** the live setup report exposed API
  compatibility issues that offline mocks had not caught. Those were fixed before
  reporting successful live evaluations.

Development corrections also included support for € and £ amount prefixes,
replacement of slow per-cell ingestion with a bulk text load, correction of a test
that confused a rule-ID substring with an invoice ID, and strict-typing fixes.
These were AI implementation corrections, not invented user prompts.

The latest counts, model configuration, limitations and commands are recorded in
[eval_report.md](eval_report.md). No API keys, customer rows, hidden reasoning or
verbatim content from excluded messages are included in this log.
