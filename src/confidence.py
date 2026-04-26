"""
confidence.py
Assigns field-level confidence scores using OCR confidence,
pattern validation, and keyword heuristics.
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)

DATE_RE = re.compile(
    r"(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"
    r"|(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})"
    r"|(\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{2,4})",
    re.I
)
CURRENCY_RE = re.compile(r"^[\$£€₹]?\s*\d{1,6}[.,]\d{2}$")
TOTAL_KW_RE = re.compile(r"\b(total|grand total|amount due|balance)\b", re.I)
LOW_CONF_THRESHOLD = 0.70


class ConfidenceScorer:

    def score(self, extracted: dict, ocr_result: dict) -> dict:
        avg_ocr = extracted["_meta"]["avg_ocr_confidence"]
        out = {}

        out["store_name"] = self._score_store(
            extracted["store_name"], avg_ocr, ocr_result
        )
        out["date"] = self._score_date(extracted["date"], avg_ocr)
        out["total_amount"] = self._score_total(
            extracted["total_amount"], avg_ocr, ocr_result["text"]
        )
        out["items"] = self._score_items(extracted["items"], avg_ocr)
        out["flags"] = self._flag_low_confidence(out)

        return out

    # ── helpers ─────────────────────────────────────────────────────────── #

    def _field(self, value, confidence: float) -> dict:
        return {
            "value": value,
            "confidence": round(min(max(confidence, 0.0), 1.0), 4),
        }

    def _score_store(self, value: Optional[str], avg_ocr: float, ocr_result: dict) -> dict:
        if not value:
            return self._field(None, 0.0)
        # Boost if it appears in first two lines
        lines = ocr_result.get("lines", [])
        position_boost = 0.05 if value in lines[:2] else 0.0
        conf = avg_ocr * 0.6 + 0.35 + position_boost
        return self._field(value, conf)

    def _score_date(self, value: Optional[str], avg_ocr: float) -> dict:
        if not value:
            return self._field(None, 0.0)
        pattern_ok = bool(DATE_RE.fullmatch(value.strip()))
        pattern_bonus = 0.15 if pattern_ok else -0.10
        return self._field(value, avg_ocr * 0.7 + 0.20 + pattern_bonus)

    def _score_total(self, value: Optional[str], avg_ocr: float, text: str) -> dict:
        if not value:
            return self._field(None, 0.0)
        currency_ok = bool(CURRENCY_RE.match(value.strip()))
        keyword_near = bool(TOTAL_KW_RE.search(text))
        bonus = (0.10 if currency_ok else -0.05) + (0.08 if keyword_near else 0.0)
        return self._field(value, avg_ocr * 0.65 + 0.25 + bonus)

    def _score_items(self, items: list, avg_ocr: float) -> list:
        scored = []
        for item in items:
            price_ok = bool(CURRENCY_RE.match(item["price"].strip()))
            price_conf = avg_ocr * 0.65 + (0.20 if price_ok else 0.05)
            name_conf = avg_ocr * 0.55 + 0.30
            scored.append({
                "name": self._field(item["name"], name_conf),
                "price": self._field(item["price"], price_conf),
            })
        return scored

    def _flag_low_confidence(self, out: dict) -> list:
        flags = []
        for field in ("store_name", "date", "total_amount"):
            entry = out.get(field, {})
            if entry.get("confidence", 1.0) < LOW_CONF_THRESHOLD:
                flags.append({
                    "field": field,
                    "confidence": entry.get("confidence"),
                    "warning": "Low confidence – manual review recommended",
                })
        for i, item in enumerate(out.get("items", [])):
            for sub in ("name", "price"):
                c = item.get(sub, {}).get("confidence", 1.0)
                if c < LOW_CONF_THRESHOLD:
                    flags.append({
                        "field": f"items[{i}].{sub}",
                        "confidence": c,
                        "warning": "Low confidence – manual review recommended",
                    })
        return flags
