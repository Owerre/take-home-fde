"""Reproducible, aggregate-only source profile and provisional M1 sensitivity.

This is exploratory analysis, not the production transformation or metric compiler.
It uses the proposed rules in specs/; all preview values await M1 approval.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
from collections import Counter, defaultdict
from collections.abc import Mapping
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def parse_date(value: str) -> date:
    """Apply proposed S-DATE-01; ambiguous hyphens are day-first."""
    for pattern in ("%Y-%m-%d", "%m/%d/%Y", "%Y/%m/%d", "%b %d %Y", "%d-%m-%Y"):
        try:
            return datetime.strptime(value.strip(), pattern).date()
        except ValueError:
            continue
    raise ValueError("Date outside the proposed format allowlist")


def canonical(value: str, groups: Mapping[str, tuple[str, ...]]) -> str:
    """Normalize known categorical aliases, failing on unknown categories."""
    token = value.strip().casefold()
    for name, aliases in groups.items():
        if token in aliases:
            return name
    raise ValueError("Unknown categorical value")


def money(value: str) -> Decimal:
    """Parse the observed source formats without guessing currency or cents."""
    token = re.sub(r"\s*(USD|EUR|GBP)$", "", value.strip())
    token = re.sub(r"^[$€£]", "", token).replace(",", "")
    if not re.fullmatch(r"-?\d+(?:\.\d{1,2})?", token):
        raise ValueError("Invalid monetary format")
    return Decimal(token)


def rounded(value: Decimal) -> str:
    return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def profile(source: Path, as_of: date) -> str:
    """Return a deterministic report containing counts and aggregates, never PII."""
    plans = {
        "Starter": ("starter", "start", "tier 1"),
        "Pro": ("pro", "professional", "tier 2"),
        "Enterprise": ("enterprise", "ent", "tier 3"),
    }
    statuses = {
        "paid": ("paid", "complete", "completed", "success"),
        "pending": ("pending", "in_review", "awaiting"),
        "failed": ("failed", "declined", "error"),
        "refunded": ("refunded", "refund", "charged_back"),
        "void": ("void", "cancelled", "canceled"),
    }
    cycles = {"monthly": ("monthly",), "annual": ("annual", "annually", "yearly")}
    prices = {"Starter": Decimal(49), "Pro": Decimal(99), "Enterprise": Decimal(299)}
    fx = {"USD": Decimal(1), "EUR": Decimal("1.08"), "GBP": Decimal("1.27")}
    priority = {"void": 5, "refunded": 4, "paid": 3, "failed": 2, "pending": 1}
    with source.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    unique = list({tuple(row.items()): row for row in rows}.values())
    by_invoice: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in unique:
        by_invoice[row["invoice_id"]].append(row)
    conflicts = [group for group in by_invoice.values() if len(group) > 1]
    different_fields = Counter(
        column
        for group in conflicts
        for column in rows[0]
        if len({row[column] for row in group}) > 1
    )
    pairs = Counter(
        "/".join(sorted({canonical(row["status"], statuses) for row in group}))
        for group in conflicts
    )
    winners = [
        max(group, key=lambda row: priority[canonical(row["status"], statuses)])
        for group in by_invoice.values()
    ]
    date_checks: dict[str, dict[str, int | str]] = {}
    for column in ("signup_date", "invoice_date"):
        hyphens = [r[column] for r in rows if re.fullmatch(r"\d{2}-\d{2}-\d{4}", r[column])]
        parsed = [parse_date(r[column]) for r in rows]
        date_checks[column] = {
            "min": str(min(parsed)),
            "max": str(max(parsed)),
            "hyphen_rows": len(hyphens),
            "hyphen_first_gt_12": sum(int(v[:2]) > 12 for v in hyphens),
            "hyphen_second_gt_12": sum(int(v[3:5]) > 12 for v in hyphens),
            "hyphen_ambiguous": sum(int(v[:2]) <= 12 for v in hyphens),
        }
    account_groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in winners:
        account_groups[row["account_id"]].append(row)
    conflict_counts = {
        field: sum(
            len({normalize_field(r, field) for r in group}) > 1 for group in account_groups.values()
        )
        for field in ("signup_date", "account_name", "region", "churned")
    }
    raw_signup_conflicts = sum(
        len({r["signup_date"] for r in group}) > 1 for group in account_groups.values()
    )
    sign_counts: Counter[str] = Counter()
    fit: dict[str, Counter[str]] = defaultdict(Counter)
    for row in winners:
        amount = money(row["amount"])
        status = canonical(row["status"], statuses)
        if amount < 0:
            sign_counts[status] += 1
        expected = prices[canonical(row["plan"], plans)] * Decimal(row["seats"])
        expected *= 1 - Decimal(row["discount_pct"]) / 100
        if canonical(row["billing_cycle"], cycles) == "annual":
            expected *= 10
        currency = row["currency"]
        target = expected * fx[currency]
        if abs(amount) == target:
            fit[currency]["matches_USD_list_times_FX"] += 1
        elif ("." not in row["amount"] and abs(abs(amount) - target) < 1) or (
            "." in row["amount"] and abs(abs(amount) - target) <= Decimal("0.01")
        ):
            fit[currency]["matches_pattern_with_source_precision_tolerance"] += 1
        else:
            fit[currency]["outside_source_precision_tolerance"] += 1
    retained = [
        r
        for r in winners
        if not (canonical(r["status"], statuses) == "paid" and money(r["amount"]) < 0)
    ]
    eligible = [r for r in retained if parse_date(r["invoice_date"]) <= as_of]

    def sensitivity(composite: bool) -> dict[str, object]:
        groups: dict[tuple[str, ...], list[dict[str, str]]] = defaultdict(list)
        for row in eligible:
            key: tuple[str, ...] = (
                (row["account_id"], row["account_name"].strip())
                if composite
                else (row["account_id"],)
            )
            groups[key].append(row)
        region_mrr: dict[str, list[Decimal]] = defaultdict(list)
        churn: dict[str, list[bool]] = defaultdict(list)
        revenues: list[tuple[Decimal, str, bool | None]] = []
        for key, group in groups.items():
            snapshot = max(group, key=lambda r: (parse_date(r["invoice_date"]), r["invoice_id"]))
            plan = canonical(snapshot["plan"], plans)
            is_churned = normalize_field(snapshot, "churned") == "true"
            active = not is_churned and canonical(snapshot["status"], statuses) == "paid"
            mrr = (
                prices[plan]
                * Decimal(snapshot["seats"])
                * (1 - Decimal(snapshot["discount_pct"]) / 100)
                if active
                else Decimal(0)
            )
            region_mrr[snapshot["region"]].append(mrr)
            churn[plan].append(is_churned)
            revenue = sum(
                (
                    (money(r["amount"]) * fx[r["currency"]]).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    for r in group
                    if canonical(r["status"], statuses) in ("paid", "refunded")
                ),
                Decimal(0),
            )
            score = snapshot["csat_score"].strip()
            # Do not expose customer identifiers in the committed report.
            revenues.append((revenue, "|".join(key), int(score) <= 2 if score else None))
        top = sorted(revenues, key=lambda item: (-item[0], item[1]))[:5]
        return {
            "accounts": len(groups),
            "region_average_mrr_USD": {
                region: rounded(sum(values, Decimal(0)) / len(values))
                for region, values in sorted(region_mrr.items())
            },
            "churn": {
                plan: {
                    "churned": sum(values),
                    "accounts": len(values),
                    "percent": rounded(Decimal(sum(values)) / len(values) * 100),
                }
                for plan, values in sorted(churn.items())
            },
            "top_5_net_revenue_USD_and_low_csat": [
                {"rank": i, "revenue_USD": rounded(value), "low_csat": low}
                for i, (value, _, low) in enumerate(top, 1)
            ],
        }

    report = {
        "raw_rows": len(rows),
        "distinct_invoice_ids": len(by_invoice),
        "exact_duplicate_losers": len(rows) - len(unique),
        "conflicting_invoice_ids": len(conflicts),
        "conflict_fields": dict(different_fields),
        "normalized_conflict_status_pairs": dict(sorted(pairs.items())),
        "account_ids": len(account_groups),
        "multi_invoice_account_ids": sum(len(g) > 1 for g in account_groups.values()),
        "conflicting_account_attributes_after_date_boolean_normalization": conflict_counts,
        "signup_date_conflicting_raw_strings": raw_signup_conflicts,
        "account_id_plus_name_groups_all_dates": len(
            {(r["account_id"], r["account_name"]) for r in winners}
        ),
        "missing_raw": {c: sum(not r[c].strip() for r in rows) for c in rows[0]},
        "malformed_nonblank_email_raw": sum(
            bool(r["contact_email"].strip())
            and not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", r["contact_email"].strip())
            for r in rows
        ),
        "date_profile_raw": date_checks,
        "invoice_before_own_signup_winners": sum(
            parse_date(r["invoice_date"]) < parse_date(r["signup_date"]) for r in winners
        ),
        "negative_amount_status_winners": dict(sorted(sign_counts.items())),
        "negative_amount_status_raw": dict(
            sorted(
                Counter(
                    canonical(r["status"], statuses) for r in rows if money(r["amount"]) < 0
                ).items()
            )
        ),
        "numeric_ranges_raw": {
            field: {
                "min": min(int(r[field]) for r in rows if r[field].strip()),
                "max": max(int(r[field]) for r in rows if r[field].strip()),
            }
            for field in ("seats", "discount_pct", "csat_score", "support_tickets")
        },
        "local_amount_absolute_vs_list_winners": {k: dict(v) for k, v in sorted(fit.items())},
        "plan_aliases_raw": dict(sorted(Counter(r["plan"] for r in rows).items())),
        "status_aliases_raw": dict(sorted(Counter(r["status"] for r in rows).items())),
        "other_categories_raw": {
            field: dict(sorted(Counter(r[field] for r in rows).items()))
            for field in ("billing_cycle", "currency", "region", "payment_method", "churned")
        },
        "proposed_row_reconciliation": {
            "retained": len(retained),
            "duplicate_losers": len(rows) - len(winners),
            "rejects": len(winners) - len(retained),
        },
        "retained_future_invoices": len(retained) - len(eligible),
        "provisional_sensitivity": {
            "account_id": sensitivity(False),
            "account_id_plus_name": sensitivity(True),
        },
    }
    return (
        "# Source data profile — M1 proposal\n\n"
        "Regenerate: `python3 scripts/profile_data.py`. Python standard library only.\n"
        f"Source SHA-256: `{hashlib.sha256(source.read_bytes()).hexdigest()}`.\n"
        f"Provisional reference date: **{as_of}** (inclusive). No customer rows or IDs below.\n\n"
        "## Method and interpretation\n\n"
        "Counts explicitly distinguish raw rows from one selected invoice per ID. "
        "The preview uses proposed day-first hyphens, status precedence "
        "void > refunded > paid > failed > pending, rejection of negative paid rows, "
        "and latest eligible invoice snapshots (invoice ID descending breaks date ties). "
        "Active proxy: latest snapshot paid and not churned; inactive MRR is zero. "
        "These are exploratory proposed-policy calculations, not implemented pipeline results "
        "or acceptance-test goldens. The alternate key is a sensitivity diagnostic only.\n\n"
        "The currency/list pattern is one systematic finding: local amounts equal USD "
        "list × FX in this export. The briefing still requires multiplying local amounts "
        "by FX to obtain USD. No inverse-FX repair is proposed. MRR uses USD list directly. "
        "List matching uses absolute amounts to include refunds and negative-paid anomalies.\n\n"
        "Account conflicts use parsed signup dates and normalized booleans; they are not "
        "merely spelling differences. All 980 multi-invoice accounts have differing raw "
        "signup strings; 979 still conflict after date parsing. Both negative paid raw "
        "rows lose to refunded versions under proposed precedence, so they are duplicate "
        "losers, not additional rejects. Missing CSAT remains unknown. Future invoices remain "
        "in staging but are excluded from reference-date previews.\n\n"
        "The two key variants below report Q2 regional means, Q4 churn numerators and "
        "denominators, and Q5 ranked revenue/CSAT flags without publishing identities. "
        "Compare values by region/plan/rank; rank rows need not refer to the same entity.\n\n"
        "```json\n" + json.dumps(report, indent=2, sort_keys=True) + "\n```\n"
    )


def normalize_field(row: dict[str, str], field: str) -> str:
    if field == "signup_date":
        return str(parse_date(row[field]))
    if field == "churned":
        return canonical(
            row[field], {"true": ("true", "yes", "1", "y"), "false": ("false", "no", "0", "n")}
        )
    return row[field].strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=ROOT / "data/cloudnova_invoices.csv")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/data_quality.md")
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date(2026, 11, 21))
    args = parser.parse_args()
    args.output.write_text(profile(args.input, args.as_of_date), encoding="utf-8")
    print("Wrote aggregate source profile")


if __name__ == "__main__":
    main()
