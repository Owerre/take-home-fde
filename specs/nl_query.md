# Query interface and security — approved at M1

- **N-CLI-01:** Commands: `python -m app build`; `python -m app "question"`;
  `python -m app eval --tier 1`; `python -m app eval --tier 2`. Question command
  builds when necessary, then interprets and answers. Build/tier 1 need no key.
  Questions/tier 2 use ANTHROPIC_API_KEY and configurable ANTHROPIC_MODEL; missing
  credentials produce actionable nonzero errors for question command. Tier 2
  without credentials prints NOT RUN (not pass), exits 0 unless `--require-live`.
- **N-TYPE-01:** Frozen typed dataclasses: Settings, RunReport, MetricDefinition,
  MetricRequest, Answer, EvalCase, EvalOutcome. Enums for metric, dimension,
  operator, order, status, plan, cycle, region, currency and response kind.
  Classes owning resources/state: Pipeline, MetricCompiler, QueryAgent, EvalRunner.
  Inject model client through a typed Protocol; stateless helpers are functions.
  CloudNovaError root; configuration/input/build/interpretation/query/eval errors
  are distinct subclasses. Deterministic context-managed cleanup; no swallowed errors.
- **N-CONFIG-01:** Validate ISO reference date, readable source path, writable build
  directory, nonempty model when live use requested, positive timeouts, limit bounds
  and bounded retry counts. Default SQL timeout 5s, model timeout 30s, ≤2 additional
  retries for transient model transport/rate-limit failures. No retry of unsafe
  content or invalid requests into arbitrary alternate execution. No answer cache.

## Structured request

- **N-REQ-01:** Question: stripped Unicode text, 1–2,000 chars, no NUL/control
  characters except whitespace. Model receives only question, schema/metric
  metadata and contract/rules. Use Anthropic SDK structured/tool output parsed
  locally into exactly one of:
  - `{kind: "metric", request: MetricRequest}`
  - `{kind: "clarification", explanation: string}`
  - `{kind: "unsupported", explanation: string}`
  Explanations are bounded; final answers formatted locally. Raw model output is
  not executed, displayed as trusted evidence, or logged. Unknown fields reject.
- **N-REQ-02:** MetricRequest fields: `metric` (metrics.md allowlist), `group_by`
  (zero or one supported dimension), `filters` (≤10 typed filter objects), optional
  `start_date`, `end_date` (ISO exclusive upper), `order` (asc/desc), `limit` (1–100).
  Filters: `{dimension, operator, values}`; dimension one of region, plan,
  billing_cycle, currency, status, account_id; operator eq/in; values 1–20 exact
  validated enum values or bounded account ID strings (≤128 chars, no controls).
  account_id is accepted as a bound filter, never resolved by sending rows to model.
  Duplicate/conflicting date ranges reject. No expressions, identifiers, joins,
  SQL fragments, offsets, arbitrary sorting columns, or model-specified reference date.
- **N-REQ-03:** Compatibility validation uses metric-specific allowlists:
  invoice metrics allow region/plan/cycle/currency/status/account_id filters;
  account metrics allow region/plan/account_id. Grouping supports region or plan
  for paid/refunds/net/exposure; exposure additionally status; average_mrr region
  or plan; churn_rate plan or region; account_revenue requires account grain.
  Status filters must be subsets of the metric's intrinsic statuses; incompatible
  status requests are unsupported rather than redefining a formula. Low-CSAT is
  a local derived flag on account_revenue, not an arbitrary SQL predicate.
- **N-AMB-01:** Six briefing questions map explicitly to M-REV/M-MRR/M-REF/M-CHURN/
  M-TOP/M-EXP. Bare “revenue” requires clarification paid vs net; bare “MRR” may
  clarify total vs average unless phrasing establishes the aggregation. Defaults
  such as as_of_date/top N are shown. Exact historical MRR, causal churn analysis,
  cash-settlement revenue, unprovided dimensions and personal-contact retrieval
  are unsupported with a concrete reason. Do not fabricate missing history.

## Compilation and containment

- **N-SQL-01:** MetricCompiler turns validated requests into predetermined SQL
  templates; table/column/operator/order identifiers come only from code allowlists.
  Bind every filter/date/limit value. No arbitrary SQL fallback, even after model
  failure or injection. Revalidate model and direct programmatic requests equally.
- **N-SEC-01:** Use read-only DuckDB connections with external access and extension
  auto-install/load disabled, configuration locked, bounded memory and thread
  settings. Expose only dedicated marts through compiler templates; raw/rejects
  and email are never selectable. Apply a connection interrupt timer for SQL
  deadlines and close connections after success/error. Cap result rows at 100,
  evidence samples at 10 per result and 50 total, and answer payload at 64 KiB.
  Security tests must prove prohibited access cannot run; a read-only flag alone
  is insufficient. Run no model-generated statements, PRAGMAs, or file functions.
- **N-LOG-01:** Structured JSON run/request logs record request UUID, build hash,
  metric ID, counts, elapsed time if measured, and sanitized error code. Do not log
  questions, model responses, parameters, customer IDs/names/emails, secrets or
  row values. Exception CLI output must not echo secret-bearing configuration.

## Answer contract

- **N-ANS-01:** Answer includes status, result rows, units (USD, USD/account/month,
  percent or invoice count), definition/rule ID, SQL, safely represented parameters,
  explicit filters/defaults, assumptions, caveats, reference date, source/build hash,
  contributing invoice count, bounded sorted invoice-ID sample and truncation flag.
  Sample IDs display only locally. No claim the sample is the full population.
  SQL and parameter display must match actual execution, not reconstructed prose.
- **N-EVID-01:** Result, count and sample derive from one shared eligible-population
  CTE per metric and consistent build. Grouped answers attach group-specific evidence.
  Account metrics count snapshot invoices (one/account), explicitly named snapshot
  evidence. Q5 separately labels revenue invoice evidence and CSAT snapshot evidence;
  do not inflate revenue contribution counts with snapshot-only records. Empty
  results have zero contributions and empty samples. Include conflict/future/FX
  caveats from the actual build rather than generic invented issue counts.
