# M1 business decision review

**Status: proposed, not approved. Implementation is paused for the review required
by step 5 of docs/build_brief.md.** The original exercise/briefing has been read;
source bytes are preserved and aggregate profiling is reproducible.

## Decisions for approval

| Decision | Proposed default | Consequence / uncertainty |
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

## Verified profile

5,125 raw rows; 5,000 invoice IDs; 82 exact duplicate losers; 43 status-only
near-duplicate IDs. Proposed reconciliation: 5,000 retained +125 duplicate losers
+0 rejects. 980 account IDs have multiple invoices; 976 conflicting names,
774 regions, 334 normalized churn flags. All 980 have differing signup strings;
979 still differ as dates. No selected invoice precedes its own parsed signup date.
There are 142 malformed nonblank email rows and 623 missing CSAT rows in raw data.
Amounts use €, £ and $ prefixes as well as currency suffixes and grouped integers.
All local/list comparisons fit the systematic pattern within source precision
tolerance; there are no extra residual pricing anomalies under that check.

See [full generated profile](data_quality.md) for counts, ranges and exact method.
The preview is exploratory analysis of proposed rules, not an implemented pipeline
or an approved expected-answer oracle.

## Account-key sensitivity (reference date 2026-11-21)

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

## Review boundary

Approve these defaults and the four specs, or identify rule IDs to change. Approval
authorizes local implementation and routine validation; it does not authorize
GitHub publication. No repository remote or reviewer identity has been supplied.
Publication review will occur after a concrete completed submission is checked.
