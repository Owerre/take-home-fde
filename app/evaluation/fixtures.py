"""Synthetic invoice fixtures and hand-computed goldens; never real customer rows."""

import csv
from pathlib import Path

from app.pipeline.ingestion import columns


def fixture_rows() -> list[dict[str, str]]:
    """Small ledger with explicit known anomalies (S-REC/FX/DATE/MRR)."""

    def row(invoice: str, account: str, **changes: str) -> dict[str, str]:
        result = dict(
            zip(
                columns(),
                (
                    invoice,
                    account,
                    "Synthetic " + account,
                    "",
                    "NA",
                    "",
                    "Starter",
                    "monthly",
                    "1",
                    "USD",
                    "49.00",
                    "0",
                    "paid",
                    "",
                    "2023-01-01",
                    "2024-01-05",
                    "false",
                    "5",
                    "0",
                ),
                strict=True,
            )
        )
        result.update(changes)
        return result

    rows = [
        row("F-01", "A", seats="2", discount_pct="10", amount="$88.20", invoice_date="05-01-2024"),
        row(
            "F-02",
            "A",
            plan="Professional",
            currency="EUR",
            amount="€100.00",
            invoice_date="2024/02/01",
            csat_score="",
        ),
        row(
            "F-03",
            "A",
            plan="Pro",
            currency="GBP",
            amount="£-20.00",
            status="REFUND",
            invoice_date="Mar 1 2024",
            csat_score="2",
        ),
        row("F-04", "B", plan="Enterprise", amount="299.00", churned="Y", csat_score="1"),
        row("F-05", "C", region="APAC", invoice_date="01/05/2024"),
        row("F-06", "D", region="EMEA", status="pending", csat_score=""),
        row("F-07", "E", region="EMEA", status="FAILED", currency="EUR", amount="100 EUR"),
        row("F-08", "F", plan="ENT", amount="299.00"),
        row("F-08", "F", plan="ENT", amount="299.00", status="VOID"),
        row("F-09", "G", invoice_date="2027-01-01"),
        row(
            "F-10",
            "H",
            region="LATAM",
            seats="2",
            discount_pct="10",
            billing_cycle="yearly",
            amount="882.00",
            csat_score="1",
        ),
        row("F-11", "I", amount="-4"),
        row("F-12", "J", status="refunded", amount="10"),
        row("F-13", "K", invoice_date="2024-02-30"),
        row("F-14", "L", csat_score="9"),
        row("F-15", "M", status="mystery"),
        row("F-16", "N", currency="GBP", amount="0.50"),
        row("F-17", "O", invoice_date="2023-12-31"),
        row("F-18", "P", csat_score="1"),
        row("F-19", "P", csat_score=""),
        row("F-20", "Q", amount="0"),
        row("F-21", "R", amount="-10", status="paid"),
        row("F-21", "R", amount="-10", status="refunded"),
    ]
    rows.append(rows[0].copy())
    return rows


def write_fixture(path: Path, rows: list[dict[str, str]] | None = None) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns())
        writer.writeheader()
        writer.writerows(fixture_rows() if rows is None else rows)
