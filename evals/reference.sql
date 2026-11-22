-- Independently authored reference SQL; does not call compiler or metric columns.
-- Q1
SELECT coalesce(sum(amount_usd),0) AS total, count(*) AS contributing_invoice_count
FROM mart_invoices
WHERE status = 'paid' AND invoice_date >= DATE '2024-01-01'
  AND invoice_date < DATE '2025-01-01' AND invoice_date <= ?;
-- Q2
SELECT region AS group_key, sum(account_mrr_usd) AS total, count(*) AS denominator,
       count(*) AS contributing_invoice_count
FROM mart_accounts GROUP BY region;
-- Q3
SELECT coalesce(-sum(amount_usd),0) AS total, count(*) AS contributing_invoice_count
FROM mart_invoices WHERE status = 'refunded' AND invoice_date <= ?;
-- Q4
SELECT plan AS group_key, count(*) FILTER (WHERE churned) AS total,
       count(*) AS denominator, count(*) AS contributing_invoice_count
FROM mart_accounts WHERE plan IN ('Enterprise','Starter') GROUP BY plan;
-- Q5
SELECT i.account_id AS group_key, sum(i.amount_usd) AS total,
       count(*) AS contributing_invoice_count,
       a.csat_score, a.snapshot_invoice_id AS csat_snapshot_invoice_id
FROM mart_invoices i JOIN mart_accounts a USING (account_id)
WHERE i.status IN ('paid','refunded') AND i.invoice_date <= ?
GROUP BY i.account_id, a.csat_score, a.snapshot_invoice_id
ORDER BY total DESC, group_key ASC LIMIT 5;
-- Q6
SELECT coalesce(sum(amount_usd),0) AS total, count(*) AS contributing_invoice_count
FROM mart_invoices WHERE status IN ('pending','failed') AND invoice_date <= ?;
