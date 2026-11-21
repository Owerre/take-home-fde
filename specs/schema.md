# Schema contract — proposed, awaiting M1 approval

Authority: the original exercise and `data/BUSINESS_CONTEXT.md`; user-specific
constraints in `docs/build_brief.md` take precedence. IDs below are stable.
No production pipeline has been implemented. Decisions requiring approval are
summarized in `docs/m1_review.md`.

## Storage and lineage

- **S-RAW-01:** Preserve input bytes. Load the 19 named CSV columns as VARCHAR
  without type inference, including blanks. Add `source_row_number BIGINT`
  (1-based data-record ordinal, excluding header), `source_sha256 VARCHAR`, and
  `source_row_sha256 VARCHAR` (canonical JSON array of original field strings).
  Reject malformed CSV structure/header as a whole-build error, not a guessed row.
- **S-LINE-01:** Raw, staging, rejects, duplicate decisions, quality flags and marts
  live in one versioned DuckDB artifact. Every staged invoice links to its winning
  raw ordinal; every loser links to winner ordinal and reason. All tables include
  build identity where needed. Only authorized marts are agent-accessible.
- **S-PII-01:** Emails remain in raw only; malformed/missing email produces an
  aggregate quality flag, never an ingestion failure. Account names may exist in
  local marts for display; never send names, IDs, emails, or rows to Anthropic.
  Keep raw CSV, databases, answer outputs and row-level diagnostics out of Git/logs.

## Typed staging invoices (one per invoice ID)

| Column | Type | Contract |
|---|---|---|
| invoice_id | VARCHAR NOT NULL | trimmed, nonempty, unique; preserve case |
| account_id | VARCHAR NOT NULL | trimmed, nonempty; baseline account key |
| account_name | VARCHAR NOT NULL | trimmed, nonempty, display only |
| region | VARCHAR NOT NULL | NA, EMEA, APAC, LATAM after trim/uppercase |
| industry | VARCHAR NULL | trim, blank → NULL; no invented industry taxonomy |
| plan | VARCHAR NOT NULL | Starter, Pro, Enterprise |
| billing_cycle | VARCHAR NOT NULL | monthly, annual |
| seats | INTEGER NOT NULL | exact positive integer, max 1,000,000 |
| currency | VARCHAR NOT NULL | USD, EUR, GBP |
| amount_local | DECIMAL(18,2) NOT NULL | parsed signed local amount |
| discount_pct | DECIMAL(7,4) NOT NULL | 0–100 inclusive |
| status | VARCHAR NOT NULL | paid, pending, failed, refunded, void |
| payment_method | VARCHAR NULL | credit_card, ACH, wire, invoice; blank → NULL |
| signup_date, invoice_date | DATE NOT NULL | valid allowlisted formats |
| churned | BOOLEAN NOT NULL | explicit boolean aliases only |
| csat_score | INTEGER NULL | 1–5; blank stays unknown |
| support_tickets | INTEGER NOT NULL | exact nonnegative integer |
| source_row_number | BIGINT NOT NULL | winning raw ordinal |

- **S-NORM-01:** Trim and casefold category lookup keys. Seed aliases include all
  briefing variants plus Starter: `start`, `tier 1`; Pro: `professional`, `tier 2`;
  Enterprise: `ent`, `tier 3`. Annual: `annual`, `annually`, `yearly`; monthly:
  `monthly`. Status aliases follow the briefing, case-insensitively (including
  FAILED/VOID). Payment aliases: `credit card`/`credit_card`, `ach`, `wire transfer`/
  `wire`, `invoice`. Boolean true: true/yes/1/y; false: false/no/0/n.
  Prices, FX and aliases must be explicit seed files, versioned in Git. Unknown
  closed categories reject; optional missing fields do not become fabricated values.
- **S-DATE-01:** Allow exactly ISO YYYY-MM-DD, YYYY/MM/DD, US MM/DD/YYYY,
  English abbreviated `Mon D YYYY`, and DD-MM-YYYY. Hyphen day-first is a proposed
  business decision, applied even when both numbers ≤12; flag those ambiguous
  values. Use explicit parsers, not locale inference. Invalid/missing dates reject.
- **S-AMT-01:** Amount grammar: optional matching `$`/`€`/`£` prefix, optional
  minus, digits with valid thousands grouping or no commas, optional 1–2 fractional
  digits, optional matching USD/EUR/GBP suffix. Trim outer spaces. Currency markers
  must agree with the currency column. Integer strings are whole currency units,
  never implicit cents. Reject unexpected text, nonfinite values and overflows.
- **S-SIGN-01:** Paid amount must be ≥0. Refunded amount must be <0. All other
  statuses must be ≥0. Zero paid is allowed and flagged. Violations reject the
  selected invoice; do not relabel status or apply abs() to repair the source.
- **S-VALID-01:** Validate raw candidate keys and category/date parsing before
  dedup selection; preserve invalid candidate reasons. Required/range/sign rules
  apply to the selected record. Invalid candidates cannot outrank parseable ones;
  if all candidates are invalid, all are rejects. Never fall back to a lower-ranked
  candidate after a selected record fails sign/range validation. Date before signup
  is retained with a quality flag (uncertain account attributes); no chronological
  repair. Future invoice dates are retained and flagged, not rejects.

## Duplicate policy and exhaustive reconciliation

- **S-DEDUP-01:** Within a parseable invoice ID, collapse exact original-field
  duplicates first, keeping lowest raw ordinal. Prefer parseable candidates over
  invalid ones. Among distinct parseable candidates, select canonical status by
  `void > refunded > paid > failed > pending`; break ties by lowest source ordinal.
  This precedence is a conservative convention, not an inferred event history.
  Preserve all conflicting fields/statuses and the decision rule. Canonically
  equivalent status spellings still receive a near-duplicate decision.
- **S-REC-01:** Each raw ordinal has exactly one terminal disposition: retained,
  duplicate_loser, or reject. Invalid candidates are rejects, not duplicate losers.
  Parseable nonwinning candidates are duplicate losers, even if the winner later
  fails range/sign validation. If a chosen candidate is invalid, its exact copies
  are losers and it is rejected. Assert raw_count = retained + losers + rejects
  and disjoint ordinals; stg keys unique; no orphan lineage. The current profile
  predicts 5,000 retained + 125 losers + 0 rejects under this proposed policy.

## Money and business-facing invoice mart

- **S-FX-01:** USD 1.00, EUR 1.08, GBP 1.27, fixed. `amount_usd =
  round_half_up(amount_local × usd_per_local, 2)`. No inverse conversion despite
  the systematic source pattern. Currency seed type DECIMAL(9,6). List prices
  DECIMAL(12,2): Starter 49, Pro 99, Enterprise 299 USD/seat/month.
- **S-ROUND-01:** Use Python Decimal and SQL DECIMAL, never binary floating-point
  money. Intermediate DECIMAL(38,8), stored money DECIMAL(18,2), aggregate money
  DECIMAL(38,2). Explicit half-away-from-zero/Decimal ROUND_HALF_UP; guard overflow.
  Sum rounded invoice USD values. Account MRR rounded per account before aggregate;
  means/percentages rounded only for presentation to two decimals. Rates retain
  numerator and denominator so display rounding is auditable.
- **S-PRICE-01:** Expected USD invoice = list × seats × (1−discount/100) ×
  (10 for annual, 1 monthly). Annual bills ten months, never twelve. Compare
  observed converted USD magnitude against expected USD, but classify the
  observed local≈USD-list×FX pattern once as a systematic source issue for EUR/GBP;
  do not flood row-level pricing discrepancies with this same issue. Check residual
  source anomalies against local pattern: tolerance <1 local unit for integer
  source strings, ≤0.01 for fractional strings; report residual discrepancies
  separately, preserving exact differences. Never replace billed amounts.
- **S-MART-01:** `mart_invoices` contains typed staging attributes except email,
  amount_usd, expected_invoice_usd, paid_revenue_usd (paid amount else zero),
  refund_magnitude_usd (−amount_usd for refunded else zero), net_revenue_usd
  (paid amount plus negative refunded amount, else zero), quality flags and lineage.
  Recognition is an invoice-date ledger proxy, not accrual accounting.

## Account snapshot mart and reference date

- **S-ASOF-01:** Explicit default `as_of_date = 2026-11-21` (user's session date),
  inclusive. Do not default to max invoice date or silently use machine today.
  Retain all valid invoices, but every answer filters invoice_date ≤ as_of_date.
  CLI/environment can override ISO date; include it in the build identity and answer.
- **S-ACCT-01:** One `mart_accounts` row per account_id with at least one eligible
  invoice. Latest eligible invoice_date wins; descending invoice_id breaks same-day
  ties. Copy that one row's plan, region, name, signup_date, churned, seats, discount,
  industry, support_tickets and CSAT together. Do not coalesce from older rows.
  Preserve NULL CSAT. Link snapshot_invoice_id, ordinal, invoice count and distinct
  attribute/conflict flags. These are latest observed invoice attributes, not a
  verified customer master or historical subscription state.
- **S-MRR-01:** `active_proxy = snapshot.status = paid AND NOT snapshot.churned`.
  Active MRR = USD list price × snapshot seats × (1−discount_pct/100), once/account,
  rounded to cents; inactive MRR = 0. Annual billing has the same MRR formula.
  No recency/expiration inference or annual/12 factor. This is a conservative proxy;
  latest pending invoice could hide an active subscriber. Expose proxy caveat.
- **S-SENS-01:** Baseline key remains account_id. An independent diagnostic reruns
  Q2/Q4/Q5 grouped by `(account_id, trimmed account_name)` and quantifies movement;
  do not silently switch keys or claim conflicting names prove separate customers.

## Build contract

Seed contracts (all required, unique lookup keys, no overlapping aliases):
`aliases.csv(domain, alias, canonical)`, `list_prices.csv(plan, usd_per_seat_month)`
and `fx_rates.csv(currency, usd_per_local)`. Validate seed completeness and positive
DECIMAL prices/rates; unsupported or conflicting seed rows fail the whole build.
No effective-date FX lookup or external market-rate service is implied.

- **S-BUILD-01:** `Pipeline` uses set-based SQL raw → staging → marts. Build in a
  same-filesystem temporary database under a single-writer lock, run all checks,
  close connections and atomically replace the published artifact. Failure leaves
  the last valid artifact intact and removes temporary files. Readers use complete
  immutable build artifacts; concurrent builders wait within a bounded timeout.
- **S-BUILD-02:** SHA-256 manifest includes source bytes, briefing, approved specs,
  transformation SQL, seeds, pipeline code, lock file, schema version and relevant
  validated configuration including as_of_date. Rebuild on any difference. Exclude
  secrets and volatile timestamps from identity. Repeated builds yield the same
  selected rows, rounded aggregates and identity; do not claim byte-identical
  database files. Retain metadata/aggregate run report; logs contain no source data.
