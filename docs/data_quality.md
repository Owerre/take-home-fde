# Source data profile — M1 proposal

Regenerate: `python3 scripts/profile_data.py`. Python standard library only.
Source SHA-256: `f542bc1f8193ab367e0a009a7afe56620335ce23b5817f5edc0ed4f896c89d84`.
Provisional reference date: **2026-11-21** (inclusive). No customer rows or IDs below.

## Method and interpretation

Counts explicitly distinguish raw rows from one selected invoice per ID. The preview uses proposed day-first hyphens, status precedence void > refunded > paid > failed > pending, rejection of negative paid rows, and latest eligible invoice snapshots (invoice ID descending breaks date ties). Active proxy: latest snapshot paid and not churned; inactive MRR is zero. These are exploratory proposed-policy calculations, not implemented pipeline results or acceptance-test goldens. The alternate key is a sensitivity diagnostic only.

The currency/list pattern is one systematic finding: local amounts equal USD list × FX in this export. The briefing still requires multiplying local amounts by FX to obtain USD. No inverse-FX repair is proposed. MRR uses USD list directly. List matching uses absolute amounts to include refunds and negative-paid anomalies.

Account conflicts use parsed signup dates and normalized booleans; they are not merely spelling differences. All 980 multi-invoice accounts have differing raw signup strings; 979 still conflict after date parsing. Both negative paid raw rows lose to refunded versions under proposed precedence, so they are duplicate losers, not additional rejects. Missing CSAT remains unknown. Future invoices remain in staging but are excluded from reference-date previews.

The two key variants below report Q2 regional means, Q4 churn numerators and denominators, and Q5 ranked revenue/CSAT flags without publishing identities. Compare values by region/plan/rank; rank rows need not refer to the same entity.

```json
{
  "account_id_plus_name_groups_all_dates": 4992,
  "account_ids": 3815,
  "conflict_fields": {
    "status": 43
  },
  "conflicting_account_attributes_after_date_boolean_normalization": {
    "account_name": 976,
    "churned": 334,
    "region": 774,
    "signup_date": 979
  },
  "conflicting_invoice_ids": 43,
  "date_profile_raw": {
    "invoice_date": {
      "hyphen_ambiguous": 88,
      "hyphen_first_gt_12": 151,
      "hyphen_rows": 239,
      "hyphen_second_gt_12": 0,
      "max": "2027-07-23",
      "min": "2021-01-19"
    },
    "signup_date": {
      "hyphen_ambiguous": 131,
      "hyphen_first_gt_12": 162,
      "hyphen_rows": 293,
      "hyphen_second_gt_12": 0,
      "max": "2024-11-01",
      "min": "2021-01-01"
    }
  },
  "distinct_invoice_ids": 5000,
  "exact_duplicate_losers": 82,
  "invoice_before_own_signup_winners": 0,
  "local_amount_absolute_vs_list_winners": {
    "EUR": {
      "matches_USD_list_times_FX": 970,
      "matches_pattern_with_source_precision_tolerance": 78
    },
    "GBP": {
      "matches_USD_list_times_FX": 391,
      "matches_pattern_with_source_precision_tolerance": 85
    },
    "USD": {
      "matches_USD_list_times_FX": 3439,
      "matches_pattern_with_source_precision_tolerance": 37
    }
  },
  "malformed_nonblank_email_raw": 142,
  "missing_raw": {
    "account_id": 0,
    "account_name": 0,
    "amount": 0,
    "billing_cycle": 0,
    "churned": 0,
    "contact_email": 292,
    "csat_score": 623,
    "currency": 0,
    "discount_pct": 0,
    "industry": 422,
    "invoice_date": 0,
    "invoice_id": 0,
    "payment_method": 637,
    "plan": 0,
    "region": 0,
    "seats": 0,
    "signup_date": 0,
    "status": 0,
    "support_tickets": 0
  },
  "multi_invoice_account_ids": 980,
  "negative_amount_status_raw": {
    "paid": 2,
    "refunded": 294
  },
  "negative_amount_status_winners": {
    "refunded": 292
  },
  "normalized_conflict_status_pairs": {
    "failed/paid": 2,
    "paid": 27,
    "paid/pending": 7,
    "paid/refunded": 2,
    "paid/void": 5
  },
  "numeric_ranges_raw": {
    "csat_score": {
      "max": 5,
      "min": 1
    },
    "discount_pct": {
      "max": 25,
      "min": 0
    },
    "seats": {
      "max": 250,
      "min": 1
    },
    "support_tickets": {
      "max": 8,
      "min": 0
    }
  },
  "other_categories_raw": {
    "billing_cycle": {
      "Annual": 687,
      "Monthly": 1251,
      "annual": 684,
      "annually": 636,
      "monthly": 1241,
      "yearly": 626
    },
    "churned": {
      "0": 875,
      "1": 206,
      "FALSE": 818,
      "N": 837,
      "No": 788,
      "TRUE": 211,
      "Y": 187,
      "Yes": 208,
      "false": 817,
      "true": 178
    },
    "currency": {
      "EUR": 1080,
      "GBP": 486,
      "USD": 3559
    },
    "payment_method": {
      "": 637,
      "ACH": 672,
      "Credit Card": 625,
      "Wire Transfer": 649,
      "ach": 641,
      "credit_card": 662,
      "invoice": 639,
      "wire": 600
    },
    "region": {
      "APAC": 1264,
      "EMEA": 1309,
      "LATAM": 1264,
      "NA": 1288
    }
  },
  "plan_aliases_raw": {
    " Starter ": 444,
    "ENT": 156,
    "Enterprise": 183,
    "Enterprise ": 173,
    "PRO": 277,
    "Pro": 244,
    "Pro ": 229,
    "Professional": 282,
    "STARTER": 406,
    "Start": 403,
    "Starter": 426,
    "Tier 1": 408,
    "Tier 2": 247,
    "Tier 3": 176,
    "enterprise": 165,
    "enterprise ": 177,
    "pro": 271,
    "starter": 458
  },
  "proposed_row_reconciliation": {
    "duplicate_losers": 125,
    "rejects": 0,
    "retained": 5000
  },
  "provisional_sensitivity": {
    "account_id": {
      "accounts": 3752,
      "churn": {
        "Enterprise": {
          "accounts": 769,
          "churned": 169,
          "percent": "21.98"
        },
        "Pro": {
          "accounts": 1125,
          "churned": 222,
          "percent": "19.73"
        },
        "Starter": {
          "accounts": 1858,
          "churned": 351,
          "percent": "18.89"
        }
      },
      "region_average_mrr_USD": {
        "APAC": "3526.12",
        "EMEA": "3097.07",
        "LATAM": "2813.69",
        "NA": "3309.19"
      },
      "top_5_net_revenue_USD_and_low_csat": [
        {
          "low_csat": false,
          "rank": 1,
          "revenue_USD": "1210592.75"
        },
        {
          "low_csat": null,
          "rank": 2,
          "revenue_USD": "1208092.75"
        },
        {
          "low_csat": false,
          "rank": 3,
          "revenue_USD": "1205642.75"
        },
        {
          "low_csat": false,
          "rank": 4,
          "revenue_USD": "1107352.84"
        },
        {
          "low_csat": false,
          "rank": 5,
          "revenue_USD": "1085078.48"
        }
      ]
    },
    "account_id_plus_name": {
      "accounts": 4889,
      "churn": {
        "Enterprise": {
          "accounts": 981,
          "churned": 211,
          "percent": "21.51"
        },
        "Pro": {
          "accounts": 1466,
          "churned": 283,
          "percent": "19.30"
        },
        "Starter": {
          "accounts": 2442,
          "churned": 451,
          "percent": "18.47"
        }
      },
      "region_average_mrr_USD": {
        "APAC": "3355.90",
        "EMEA": "3142.97",
        "LATAM": "2827.90",
        "NA": "3186.43"
      },
      "top_5_net_revenue_USD_and_low_csat": [
        {
          "low_csat": null,
          "rank": 1,
          "revenue_USD": "1205642.75"
        },
        {
          "low_csat": false,
          "rank": 2,
          "revenue_USD": "1205642.75"
        },
        {
          "low_csat": false,
          "rank": 3,
          "revenue_USD": "1205642.75"
        },
        {
          "low_csat": false,
          "rank": 4,
          "revenue_USD": "1085078.48"
        },
        {
          "low_csat": false,
          "rank": 5,
          "revenue_USD": "1085077.84"
        }
      ]
    }
  },
  "raw_rows": 5125,
  "retained_future_invoices": 103,
  "signup_date_conflicting_raw_strings": 980,
  "status_aliases_raw": {
    "Complete": 590,
    "FAILED": 86,
    "Failed": 71,
    "PAID": 586,
    "PENDING": 110,
    "Paid": 586,
    "Pending": 105,
    "REFUND": 94,
    "Refunded": 61,
    "VOID": 84,
    "Void": 74,
    "awaiting": 94,
    "canceled": 82,
    "cancelled": 90,
    "charged_back": 64,
    "completed": 600,
    "declined": 91,
    "error": 74,
    "failed": 82,
    "in_review": 107,
    "paid": 590,
    "pending": 97,
    "refunded": 75,
    "success": 564,
    "void": 68
  }
}
```
