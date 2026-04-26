"""
extractor.py
Extracts store name, date, items, prices, and total from OCR text.
Uses regex patterns + keyword heuristics.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Patterns ────────────────────────────────────────────────────────────────
DATE_PATTERNS = [
    r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})\b",
    r"\b(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})\b",
    r"\b(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})\b",
    r"\b((?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{2,4})\b",
]

TOTAL_KEYWORDS = [
    "total", "grand total", "amount due", "balance due",
    "total amount", "net amount", "subtotal", "sum"
]

PRICE_RE = re.compile(r"[\$£€₹]?\s*(\d{1,6}[.,]\d{2})\b")
SKIP_ITEM_RE = re.compile(
    r"^\s*(total|subtotal|tax|vat|gst|discount|change|cash|card|"
    r"tip|service|amount|balance|date|time|receipt|invoice|thank|"
    r"tel|phone|www|http|\.com|address|^\d{4,})\b",
    re.I
)


class InformationExtractor:

    def extract(self, text: str, word_confidences: list) -> dict:
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        avg_conf = sum(word_confidences) / len(word_confidences) if word_confidences else 0.5

        return {
            "store_name": self._store_name(lines),
            "date": self._date(text),
            "items": self._items(lines),
            "total_amount": self._total(lines, text),
            "_meta": {"avg_ocr_confidence": round(avg_conf, 4), "line_count": len(lines)},
        }

    # ── Store name ──────────────────────────────────────────────────────── #
    def _store_name(self, lines: list) -> Optional[str]:
        """
        Heuristic: store name is usually in the first 1-4 lines,
        all-caps or title-case, no price pattern, reasonably short.
        """
        for line in lines[:5]:
            if PRICE_RE.search(line):
                continue
            if re.search(r"\b(date|time|receipt|invoice|tel|phone|tax)\b", line, re.I):
                continue
            if 3 <= len(line) <= 60:
                return line
        return lines[0] if lines else None

    # ── Date ────────────────────────────────────────────────────────────── #
    def _date(self, text: str) -> Optional[str]:
        for pattern in DATE_PATTERNS:
            m = re.search(pattern, text, re.I)
            if m:
                return m.group(1)
        return None

    # ── Items ────────────────────────────────────────────────────────────── #
    def _items(self, lines: list) -> list:
        items = []
        for line in lines:
            if SKIP_ITEM_RE.search(line):
                continue
            m = PRICE_RE.search(line)
            if not m:
                continue
            price_str = m.group(0).strip()
            name = line[: m.start()].strip().rstrip(".-: ")
            if not name or len(name) < 2:
                continue
            items.append({"name": name, "price": price_str})
        return items

    # ── Total ───────────────────────────────────────────────────────────── #
    def _total(self, lines: list, text: str) -> Optional[str]:
        # Strategy 1: keyword-anchored line
        for line in lines:
            lower = line.lower()
            if any(kw in lower for kw in TOTAL_KEYWORDS):
                m = PRICE_RE.search(line)
                if m:
                    return m.group(0).strip()

        # Strategy 2: last price on the receipt
        all_prices = PRICE_RE.findall(text)
        if all_prices:
            return all_prices[-1]

        return None
