# Metric contracts — proposed, awaiting M1 approval

All money is USD; all invoice populations are deduplicated, retained and bounded
by `invoice_date <= as_of_date` (S-ASOF-01). Refunds are negative source records.
No metric uses pending/failed/void as recognized revenue. Filters must be explicit
and echoed. Empty sums/counts return zero; empty averages/rates return NULL with
an explanation, never a division error. SQL returns numerator/denominator where
applicable; evidence uses the identical population CTE as the numeric result.

| ID / allowlisted metric | Grain, formula and default filters | Evidence |
|---|---|---|
| **M-REV-01** `paid_revenue` (Q1) | SUM(paid_revenue_usd), status=paid; Q1 invoice_date in [2024-01-01,2025-01-01) | contributing paid invoices, including zero paid |
| **M-MRR-01** `average_mrr` (Q2) | AVG(account_mrr_usd) over all snapshot accounts per snapshot region, including inactive accounts at 0; rank descending; Q2 returns highest region | one snapshot invoice per denominator account, plus total/active account counts |
| **M-REF-01** `refunds` (Q3) | SUM(refund_magnitude_usd), status=refunded, all eligible dates; positive magnitude | refunded invoices only |
| **M-CHURN-01** `churn_rate` (Q4) | 100 × COUNT(churned=true)/COUNT(all snapshot accounts), grouped by snapshot plan; Q4 Enterprise vs Starter | one snapshot invoice per denominator account; show churned/total |
| **M-TOP-01** `account_revenue` (Q5) | SUM(net_revenue_usd) per account_id, paid/refunded only; eligible period; rank descending, default top 5; ties by account_id ascending | paid/refunded invoices for each returned account; separate snapshot ID for its CSAT |
| **M-EXP-01** `exposure` (Q6) | COUNT(*) and SUM(amount_usd), status IN (pending,failed), all eligible dates | pending/failed invoices only |
| **M-NET-01** `net_revenue` | SUM(net_revenue_usd), statuses paid/refunded only | paid/refunded invoices only |

- **M-TIME-01:** Revenue timing uses invoice_date, since payment/refund transaction
  timestamps and accrual schedules are absent. Date bounds are start-inclusive,
  end-exclusive and clipped at the inclusive reference date. A request after that
  date is explained as outside the build horizon; never silently move the date.
  Snapshot MRR/churn use the build reference date. Historical snapshot queries
  require a rebuild/reference-date change and remain proxies, not exact history.
- **M-FILTER-01:** Invoice metrics filter on invoice attributes; account MRR/churn
  filter on snapshot attributes. Q5 region/plan filters apply to invoice rows and
  are labeled accordingly; CSAT flags use the latest overall eligible snapshot.
  Only declared dimensions/operators in nl_query.md are supported. Region and plan
  breakdowns are allowed for invoice metrics; account_revenue always groups by
  account. Q6 may also group by status. Do not mix invoice and account denominators.
- **M-RANK-01:** Ranking sorts the unrounded aggregate, then deterministic ascending
  group key on ties; configurable top N 1–100. Q2 top 1, Q5 top 5. Account revenue
  excludes accounts with no paid/refunded invoice in the selected population.
  Negative net revenue remains negative. Low CSAT flag is true if snapshot score
  ≤2, false if >2, NULL/“unknown” if missing; return actual score or unknown.
- **M-CAVEAT-01:** Q2/Q4/Q5 must disclose unstable account attributes and baseline
  account_id key. Include alternate-key sensitivity link/table from the approved
  diagnostic. Q4 is an observed churn-flag prevalence, not a time-based churn rate.
  Q6 is uncollected invoice face value, not aged receivables or probability-weighted
  loss; there is no due date. Q3 measures recorded refunds, not payment cash dates.

## Hand-reproduction instructions (Q1, Q3 and Q6)

First apply the approved date/alias/dedup/sign rules in schema.md. Work with the
one retained row per invoice ID, not the 5,125-row raw export. Convert every
included local amount using USD=1, EUR=1.08, GBP=1.27, round each to cents with
ROUND_HALF_UP, then sum. No list-price replacement or division by FX.

1. **Q1 — paid revenue in 2024:** keep normalized status `paid` and invoice dates
   on/after 2024-01-01 and before 2025-01-01, also ≤as_of_date. Add their converted
   nonnegative amounts. Exclude refunds entirely from this particular question.
2. **Q3 — refunds given back:** keep normalized status `refunded` and invoice_date
   ≤as_of_date. Add the negatives of their converted negative amounts. The answer
   is a positive USD magnitude. Net revenue is a separate metric.
3. **Q6 — pending/failed exposure:** keep normalized status `pending` or `failed`
   and invoice_date ≤as_of_date. Count those invoices once each and add their
   converted face amounts. Neither paid nor void nor refunded rows belong here.

At M1 no production expected values are claimed. Tier 1 will use independently
written reference SQL and hand-computed fixture values, not compiler-derived goldens.
