"""
summarizer.py
Generates financial summary across all processed receipts.
"""

import re
import logging
from collections import defaultdict

logger = logging.getLogger(__name__)

AMOUNT_RE = re.compile(r"[\$£€₹]?\s*(\d{1,6}[.,]\d{2})")


def _parse_amount(value: str) -> float:
    if not value:
        return 0.0
    m = AMOUNT_RE.search(str(value))
    if not m:
        return 0.0
    return float(m.group(1).replace(",", ""))


class FinancialSummarizer:

    def generate(self, all_results: list) -> dict:
        total_spend = 0.0
        num_transactions = 0
        per_store = defaultdict(float)
        failed = []

        for r in all_results:
            if "error" in r:
                failed.append(r["file"])
                continue

            conf_out = r.get("confidence_output", {})
            structured = r.get("structured", {})

            # Get total amount
            total_field = conf_out.get("total_amount", {})
            raw_total = total_field.get("value") or structured.get("total_amount")
            amount = _parse_amount(raw_total)

            if amount > 0:
                total_spend += amount
                num_transactions += 1

                store_field = conf_out.get("store_name", {})
                store = store_field.get("value") or structured.get("store_name") or "Unknown"
                per_store[store] += amount

        return {
            "total_spend": round(total_spend, 2),
            "num_transactions": num_transactions,
            "spend_per_store": {k: round(v, 2) for k, v in sorted(
                per_store.items(), key=lambda x: -x[1]
            )},
            "failed_files": failed,
            "currency_note": "All amounts in document currency (not normalised)",
        }
