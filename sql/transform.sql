-- Contracts: S-NORM-01, S-DATE-01, S-AMT-01. No inferred column types.
CREATE MACRO canon(d, v) AS (
    SELECT canonical FROM aliases WHERE domain = d AND alias = lower(trim(v))
);
CREATE MACRO parsed_date(v) AS CASE
    WHEN regexp_full_match(trim(v), '[0-9]{4}-[0-9]{2}-[0-9]{2}')
        THEN try_strptime(trim(v), '%Y-%m-%d')::DATE
    WHEN regexp_full_match(trim(v), '[0-9]{4}/[0-9]{2}/[0-9]{2}')
        THEN try_strptime(trim(v), '%Y/%m/%d')::DATE
    WHEN regexp_full_match(trim(v), '[0-9]{2}/[0-9]{2}/[0-9]{4}')
        THEN try_strptime(trim(v), '%m/%d/%Y')::DATE
    WHEN regexp_full_match(trim(v), '[A-Z][a-z]{2} [0-9]{1,2} [0-9]{4}')
        THEN try_strptime(trim(v), '%b %d %Y')::DATE
    WHEN regexp_full_match(trim(v), '[0-9]{2}-[0-9]{2}-[0-9]{4}')
        THEN try_strptime(trim(v), '%d-%m-%Y')::DATE
END;

CREATE TABLE normalized AS
SELECT
    source_row_number, source_sha256, source_row_sha256,
    trim(invoice_id) AS invoice_id, trim(account_id) AS account_id,
    trim(account_name) AS account_name, nullif(trim(industry), '') AS industry,
    canon('region', region) AS region, canon('plan', plan) AS plan,
    canon('billing_cycle', billing_cycle) AS billing_cycle,
    canon('currency', currency) AS currency, canon('status', status) AS status,
    canon('payment_method', payment_method) AS payment_method,
    try_cast(canon('churned', churned) AS BOOLEAN) AS churned,
    parsed_date(signup_date) AS signup_date, parsed_date(invoice_date) AS invoice_date,
    CASE WHEN regexp_full_match(trim(seats), '[0-9]+') THEN try_cast(seats AS INTEGER) END AS seats,
    CASE WHEN regexp_full_match(trim(discount_pct), '[0-9]+(\.[0-9]{1,4})?')
        THEN try_cast(discount_pct AS DECIMAL(7,4)) END AS discount_pct,
    CASE WHEN regexp_full_match(trim(csat_score), '[0-9]+')
        THEN try_cast(csat_score AS INTEGER) END AS csat_score,
    CASE WHEN regexp_full_match(trim(support_tickets), '[0-9]+')
        THEN try_cast(support_tickets AS INTEGER) END AS support_tickets,
    CASE WHEN regexp_full_match(trim(amount),
        '[$€£]?-?([0-9]+|[0-9]{1,3}(,[0-9]{3})+)(\.[0-9]{1,2})?( (USD|EUR|GBP))?')
        AND (left(trim(amount), 1) NOT IN ('$', '€', '£')
             OR left(trim(amount), 1) = CASE upper(trim(currency))
                 WHEN 'USD' THEN '$' WHEN 'EUR' THEN '€' WHEN 'GBP' THEN '£' END)
        AND (NOT regexp_matches(trim(amount), ' (USD|EUR|GBP)$')
             OR right(trim(amount), 3) = upper(trim(currency)))
    THEN try_cast(regexp_replace(regexp_replace(replace(trim(amount), ',', ''),
         '^[$€£]', ''), ' (USD|EUR|GBP)$', '') AS DECIMAL(18,2)) END AS amount_local,
    NOT contains(amount, '.') AS integer_amount_source,
    regexp_full_match(trim(invoice_date), '[0-9]{2}-[0-9]{2}-[0-9]{4}')
        AND try_cast(left(trim(invoice_date), 2) AS INTEGER) <= 12 AS ambiguous_invoice_date,
    regexp_full_match(trim(signup_date), '[0-9]{2}-[0-9]{2}-[0-9]{4}')
        AND try_cast(left(trim(signup_date), 2) AS INTEGER) <= 12 AS ambiguous_signup_date,
    nullif(trim(csat_score), '') IS NULL AS csat_missing,
    nullif(trim(payment_method), '') IS NULL AS payment_method_missing,
    nullif(trim(contact_email), '') IS NULL AS email_missing,
    nullif(trim(contact_email), '') IS NOT NULL
        AND NOT regexp_full_match(trim(contact_email), '[^\s@]+@[^\s@]+\.[^\s@]+') AS email_malformed,
    row_number() OVER (PARTITION BY source_row_sha256 ORDER BY source_row_number) AS exact_rank,
    min(source_row_number) OVER (PARTITION BY source_row_sha256) AS exact_representative
FROM raw;

CREATE TABLE candidates AS
SELECT *, concat_ws(',',
    CASE WHEN invoice_id = '' OR account_id = '' OR account_name = '' THEN 'required_key' END,
    CASE WHEN region IS NULL OR plan IS NULL OR billing_cycle IS NULL OR currency IS NULL
        OR status IS NULL OR churned IS NULL
        OR (payment_method IS NULL AND NOT payment_method_missing) THEN 'category' END,
    CASE WHEN signup_date IS NULL OR invoice_date IS NULL THEN 'date' END,
    CASE WHEN amount_local IS NULL THEN 'amount' END,
    CASE WHEN seats IS NULL OR discount_pct IS NULL OR support_tickets IS NULL
        OR (csat_score IS NULL AND NOT csat_missing) THEN 'numeric' END
) AS parse_errors,
concat_ws(',',
    CASE WHEN seats NOT BETWEEN 1 AND 1000000 OR discount_pct NOT BETWEEN 0 AND 100
        OR support_tickets < 0 OR csat_score NOT BETWEEN 1 AND 5 THEN 'range' END,
    CASE WHEN (status = 'refunded' AND amount_local >= 0)
        OR (status <> 'refunded' AND amount_local < 0) THEN 'sign' END
) AS validation_errors
FROM normalized;

CREATE TABLE ranked AS
SELECT source_row_number,
    row_number() OVER (PARTITION BY invoice_id ORDER BY
        CASE status WHEN 'void' THEN 5 WHEN 'refunded' THEN 4 WHEN 'paid' THEN 3
                    WHEN 'failed' THEN 2 WHEN 'pending' THEN 1 END DESC,
        source_row_number) AS invoice_rank,
    first_value(source_row_number) OVER (PARTITION BY invoice_id ORDER BY
        CASE status WHEN 'void' THEN 5 WHEN 'refunded' THEN 4 WHEN 'paid' THEN 3
                    WHEN 'failed' THEN 2 WHEN 'pending' THEN 1 END DESC,
        source_row_number) AS selected_representative
FROM candidates WHERE exact_rank = 1 AND parse_errors = '';

-- S-REC-01: exactly one terminal disposition per original source ordinal.
CREATE TABLE row_dispositions AS
SELECT c.source_row_number, c.invoice_id, c.source_row_sha256,
    CASE WHEN c.exact_rank > 1 THEN 'duplicate_loser'
         WHEN c.parse_errors <> '' THEN 'reject'
         WHEN r.invoice_rank > 1 THEN 'duplicate_loser'
         WHEN c.validation_errors <> '' THEN 'reject' ELSE 'retained' END AS disposition,
    CASE WHEN c.exact_rank > 1 THEN 'exact_copy'
         WHEN c.parse_errors <> '' THEN c.parse_errors
         WHEN r.invoice_rank > 1 THEN 'S-DEDUP-01_status_precedence_or_source_order'
         WHEN c.validation_errors <> '' THEN c.validation_errors ELSE 'valid' END AS reason,
    CASE WHEN c.exact_rank > 1 THEN c.exact_representative
         ELSE r.selected_representative END AS selected_source_row_number
FROM candidates c LEFT JOIN ranked r USING (source_row_number);
CREATE TABLE rejects AS SELECT * FROM row_dispositions WHERE disposition = 'reject';
CREATE TABLE duplicate_decisions AS
SELECT d.*, c.status AS normalized_status, selected.status AS selected_status,
       c.amount_local AS candidate_amount_local, selected.amount_local AS selected_amount_local
FROM row_dispositions d JOIN candidates c USING(source_row_number)
LEFT JOIN candidates selected ON d.selected_source_row_number = selected.source_row_number
WHERE disposition = 'duplicate_loser';

CREATE TABLE stg_invoices AS
SELECT c.* EXCLUDE (parse_errors, validation_errors, exact_rank, exact_representative)
FROM candidates c JOIN row_dispositions d USING(source_row_number)
WHERE d.disposition = 'retained';

-- Multiplication by DECIMAL 0.01 avoids DuckDB's floating-point decimal division.
CREATE TABLE mart_invoices AS
WITH priced AS (
    SELECT i.*, p.usd_per_seat_month, fx.usd_per_local,
        cast(round(i.amount_local * fx.usd_per_local, 2) AS DECIMAL(18,2)) AS amount_usd,
        cast(p.usd_per_seat_month * i.seats *
             (1::DECIMAL(2,0) - i.discount_pct * 0.01::DECIMAL(3,2))
             AS DECIMAL(38,8)) AS unrounded_list_mrr_usd
    FROM stg_invoices i JOIN list_prices p USING(plan) JOIN fx_rates fx USING(currency)
), expected AS (
    SELECT *, cast(round(unrounded_list_mrr_usd, 2) AS DECIMAL(18,2)) AS list_mrr_usd,
        cast(round(unrounded_list_mrr_usd * CASE billing_cycle WHEN 'annual' THEN 10 ELSE 1 END, 2)
                  AS DECIMAL(18,2)) AS expected_invoice_usd FROM priced
)
SELECT *,
    CASE WHEN status = 'paid' THEN amount_usd ELSE 0::DECIMAL(18,2) END AS paid_revenue_usd,
    CASE WHEN status = 'refunded' THEN -amount_usd ELSE 0::DECIMAL(18,2) END AS refund_magnitude_usd,
    CASE WHEN status IN ('paid','refunded') THEN amount_usd ELSE 0::DECIMAL(18,2) END AS net_revenue_usd,
    abs(amount_usd) - expected_invoice_usd AS pricing_difference_usd,
    abs(amount_local) - expected_invoice_usd * usd_per_local AS source_pattern_residual,
    currency <> 'USD' AND
        ((integer_amount_source AND abs(abs(amount_local) - expected_invoice_usd * usd_per_local) < 1)
         OR (NOT integer_amount_source AND
             abs(abs(amount_local) - expected_invoice_usd * usd_per_local) <= 0.01)) AS systematic_fx_pattern,
    NOT ((integer_amount_source AND abs(abs(amount_local) - expected_invoice_usd * usd_per_local) < 1)
         OR (NOT integer_amount_source AND
             abs(abs(amount_local) - expected_invoice_usd * usd_per_local) <= 0.01)) AS pricing_discrepancy
FROM expected;

CREATE TABLE quality_flags AS
SELECT source_row_number, flag FROM candidates,
LATERAL (VALUES
    ('ambiguous_invoice_date', ambiguous_invoice_date),
    ('ambiguous_signup_date', ambiguous_signup_date),
    ('missing_csat', csat_missing), ('missing_email', email_missing),
    ('malformed_email', email_malformed),
    ('future_invoice', invoice_date > (SELECT as_of_date FROM build_metadata)),
    ('invoice_before_signup', invoice_date < signup_date),
    ('zero_paid', status = 'paid' AND amount_local = 0)
) flags(flag, present) WHERE present
UNION ALL SELECT source_row_number, 'pricing_discrepancy' FROM mart_invoices WHERE pricing_discrepancy;

CREATE TABLE account_conflicts AS
SELECT account_id, count(*) AS invoice_count,
    count(DISTINCT account_name) > 1 AS name_conflict,
    count(DISTINCT signup_date) > 1 AS signup_conflict,
    count(DISTINCT region) > 1 AS region_conflict,
    count(DISTINCT churned) > 1 AS churn_conflict
FROM mart_invoices
WHERE invoice_date <= (SELECT as_of_date FROM build_metadata)
GROUP BY account_id;

CREATE TABLE mart_accounts AS
WITH snapshots AS (
    SELECT * FROM mart_invoices
    WHERE invoice_date <= (SELECT as_of_date FROM build_metadata)
    QUALIFY row_number() OVER (PARTITION BY account_id ORDER BY invoice_date DESC, invoice_id DESC) = 1
)
SELECT s.* EXCLUDE(invoice_id), s.invoice_id AS snapshot_invoice_id,
       c.* EXCLUDE(account_id),
       s.status = 'paid' AND NOT s.churned AS active_proxy,
       CASE WHEN s.status = 'paid' AND NOT s.churned THEN s.list_mrr_usd
            ELSE 0::DECIMAL(18,2) END AS account_mrr_usd
FROM snapshots s JOIN account_conflicts c USING(account_id);

CREATE UNIQUE INDEX stg_invoice_key ON stg_invoices(invoice_id);
CREATE UNIQUE INDEX mart_invoice_key ON mart_invoices(invoice_id);
CREATE UNIQUE INDEX mart_account_key ON mart_accounts(account_id);
