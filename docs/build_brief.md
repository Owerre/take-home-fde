Act as a senior Forward Deployed Engineer. Build and validate Track B of the
CloudNova take-home: a spec-driven data pipeline and natural-language query agent.

Read the original exercise, BUSINESS_CONTEXT.md, and cloudnova_invoices.csv.
Follow applicable repository instructions. The exercise and business briefing
are authoritative; do not silently replace their rules with dataset assumptions.

The exercise requests approximately one hour. I have chosen a maximum of
24 hours. Report actual effort honestly; do not claim one-hour compliance.
Prioritize a complete, narrow submission over additional features.

## Workflow

1. Inspect existing files and Git history; preserve existing work and raw inputs.
   Initialise Git if the folder is not a repository, and move the two inputs
   into data/ unchanged.
2. Save this prompt in docs/build_brief.md. Configure AGENTS.md for Codex,
   .gitignore, .env.example, and reproducible dependencies.
3. Profile the data with a committed script and report.
4. Before implementation, write and commit:
   - specs/schema.md: types, constraints, normalization, dates, duplicates,
     rejects, FX, rounding, account snapshots, and MRR.
   - specs/metrics.md: formulas, grain, filters, denominators, and caveats.
   - specs/nl_query.md: request/answer contracts and security.
   - specs/evals.md: acceptance cases and expected behavior.
   Give substantive rules stable IDs.
5. Present unresolved business decisions and proposed defaults; stop for my
   review of the specs (M1). After approval, implement and validate without
   repeatedly asking permission for routine choices.
6. Update approved specs before implementing material deviations.
7. Use small, honest commits. Never fabricate history, results, or prompt logs.

## Required implementation

Use Python, DuckDB, and set-based SQL transformations:
raw CSV → raw → staging → marts → metric request → SQL → answer.

- raw: original text columns plus source-row metadata.
- staging: typed, normalized, deduplicated invoices.
- marts: business-facing invoices and one-row-per-account snapshots.
- Keep aliases, list prices, and FX rates in seed files.
- Preserve rejects, duplicate decisions, quality flags, and source lineage.
- Reconcile input rows into retained rows, duplicate losers, and rejects,
  counting each source row once.
- Validate contracts, keys, ranges, required fields, categories, and signs.
- Report pricing discrepancies instead of silently correcting amounts.
- Build atomically and deterministically. Invalidate builds when inputs,
  rules, SQL, seeds, relevant configuration, or as_of_date change.

Implement:
- python -m app "question"
- python -m app build
- python -m app eval --tier 1
- python -m app eval --tier 2

The question command builds when necessary, then answers.
Pipeline and tier 1 run without credentials.

Use the Anthropic SDK for natural-language interpretation, with a configurable
model. Convert model output into a validated MetricRequest, then compile SQL
deterministically. Support all six stakeholder questions, including ranking,
filters, and low-CSAT flags. Unsupported requests receive clear explanations.
Do not add arbitrary SQL fallback.

Answers show result and units, SQL and parameters, metric definition,
assumptions, caveats, build/reference date, contributing invoice count, and a
bounded invoice-ID sample. Evidence must match the result's actual population.

## Business rules

Follow BUSINESS_CONTEXT.md exactly:
- Fixed USD conversion: USD 1, EUR 1.08, GBP 1.27.
- Annual invoices bill ten months.
- MRR = USD list price × seats × (1 − discount_pct/100), once per account.
- Separate paid revenue, positive refund magnitude, and net revenue after
  negative refunds. Pending, failed, and void are not recognized revenue.
- Use Decimal/DECIMAL with explicit precision and rounding.

At M1, settle date parsing, conflict precedence, negative paid records,
account snapshots, active-subscription proxy, revenue timing, and as_of_date.

Use account_id as the baseline account key unless I approve otherwise.
Conflicting names do not prove separate customers. Document account-level
uncertainty and avoid claiming historical subscription/churn states the data
cannot establish. Preserve unknown CSAT and other missing attributes.

## Prior profiling findings

From my first pass. Verify each in your own profile, and look for more:

- 5,125 rows, 5,000 distinct invoice IDs, 82 exact duplicate rows, and 43 IDs
  with two rows that differ only in status, some paid versus void. There is no
  timestamp to choose a winner.
- account_id: all 980 IDs with more than one invoice carry conflicting signup
  dates; 976 conflicting names, 774 regions, 334 churn flags. account_id plus
  account_name yields 4,992 groups for 5,000 invoices. Report questions 2, 4
  and 5 under the baseline key and state how far each moves under the
  composite key.
- EUR and GBP amounts already equal the USD list price multiplied by 1.08 and
  1.27, so converting per the briefing puts them above list. Treat this as one
  systematic finding, not as per-row pricing discrepancies. MRR is unaffected
  because it derives from list price.
- plan has unlisted variants: Tier 1, Tier 3, Start, ENT, and padded values.
  status also appears in upper case.
- In NN-NN-YYYY dates the second number never exceeds 12 and the first often
  does; slash dates are month/day/year.
- Two rows are paid with negative amounts. Invoice dates run to July 2027.

## Code standards

- Frozen, typed dataclasses for Settings, RunReport, MetricDefinition,
  MetricRequest, Answer, EvalCase, and EvalOutcome; add others only as needed.
- Enums for closed domain categories.
- Classes for state/resources: Pipeline, MetricCompiler, QueryAgent, EvalRunner.
  Plain functions for stateless logic; no speculative inheritance or factories.
- Inject the model client through a typed Protocol for credential-free tests.
- Separate pipeline, metrics, agent, CLI, and evaluations. Keep entry points thin.
- Clear business names, cohesive functions, useful docstrings, no duplicated
  formulas, dead code, or mutable global application state.
- Validated configuration, reliable resource cleanup, and a small exception
  hierarchy rooted at CloudNovaError. No swallowed errors.
- Configure formatting, linting, strict typing, a lock file, and common commands.

## Security and reliability

Validate questions and structured model output. Allowlist metrics, identifiers,
operators, and ordering; bind values safely. Use read-only restricted query
connections, disable unnecessary external access, and enforce output limits,
execution timeouts, and bounded model retries.

Keep emails out of agent-accessible marts. Send schema/metric metadata and the
question to the model, not customer rows. Format answers locally.
Never commit or log secrets or personal data.

Use structured run/request logs and actionable failures with non-zero exits.
If caching is added, include build and agent configuration in its identity and
bypass it during repeated evaluations.

## Validation

Tier 1: offline fixtures and independent reference SQL for all six stakeholder
questions. Cover FX, annual MRR, refunds, deduplication, dates, account
denominators, ranking, and missing CSAT. Link tests to rule IDs.
Do not generate expected answers using the compiler under test.

Tier 2: real natural-language questions, paraphrases, filters, ambiguity,
unsupported requests, injection attempts, and personal-data requests.
Compare results and behavior, not SQL strings. Repeat representative cases
without caching. Mark live evaluations as not run when credentials are absent.

Include at least one case marked as an expected failure, scored as a failure
and explained, as the exercise requires. Choose a reasonable finance question
the system cannot answer correctly, such as exact historical MRR without
subscription history. Refusals of out-of-scope or unsafe requests count as
correct. Do not mark any of the six stakeholder questions as expected failures.

For stakeholder questions 1, 3 and 6, give me the plain-language definition
and row filter so I can reproduce the expected value by hand.

Print per-case results and summaries; fail on unexpected errors.
Commit docs/eval_report.md with actual results, configuration, failures, and
limitations. Report latency/cost only if measured.

Run formatting, linting, typing, tests, pipeline, and offline evals.
Verify documented setup and demo commands from a clean environment.

## Deliverables

- README.md readable in three minutes: purpose, setup, single demo command,
  which commands need an Anthropic API key, key requirements, specs, results,
  decisions, limitations, actual effort, and what another day would improve.
- AGENTS.md showing actual AI configuration.
- specs/ and runnable evals/.
- docs/build_brief.md, data_quality.md, eval_report.md, architecture.md
  with an accurate Mermaid diagram, and brief significant decision records.
- Authentic docs/prompt_log.md using supplied transcripts; identify missing
  history rather than inventing it.
- Dependency/configuration files, .env.example, and honest Git history.
- A GitHub repository link, public or private with reviewer access as instructed.
  Check tracked files before publication and obtain publication authorization
  if it has not already been provided.

Query guardrails satisfy the hardening requirement. API, Docker, CI, caching,
and sensitivity analysis are optional after the required submission passes.
No frontend, vector store, cloud deployment, or unrelated features.

Finish with what was built, checks actually run, failures, remaining limits,
and exact run commands. Never claim unexecuted checks passed.