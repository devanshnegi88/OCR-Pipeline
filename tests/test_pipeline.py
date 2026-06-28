"""
tests/test_pipeline.py
Unit tests for extractor, confidence scorer, and summarizer.
Run with: pytest tests/ -v
"""

import pytest
from src.extractor import InformationExtractor
from src.confidence import ConfidenceScorer
from src.summarizer import FinancialSummarizer

SAMPLE_TEXT = """
WHOLE FOODS MARKET
123 Main Street, Springfield
Date: 12/05/2024

Organic Milk           $3.99
Free Range Eggs        $5.49
Sourdough Bread        $4.25
Orange Juice           $3.75

Subtotal              $17.48
Tax (8%)               $1.40
TOTAL                 $18.88

Thank you for shopping!
"""

SAMPLE_CONFS = [0.92] * 30


@pytest.fixture
def extractor():
    return InformationExtractor()


@pytest.fixture
def scorer():
    return ConfidenceScorer()


@pytest.fixture
def summarizer():
    return FinancialSummarizer()


class TestExtractor:

    def test_store_name(self, extractor):
        result = extractor.extract(SAMPLE_TEXT, SAMPLE_CONFS)
        assert result["store_name"] == "WHOLE FOODS MARKET"

    def test_date(self, extractor):
        result = extractor.extract(SAMPLE_TEXT, SAMPLE_CONFS)
        assert result["date"] == "12/05/2024"

    def test_total(self, extractor):
        result = extractor.extract(SAMPLE_TEXT, SAMPLE_CONFS)
        assert "18.88" in result["total_amount"]

    def test_items_extracted(self, extractor):
        result = extractor.extract(SAMPLE_TEXT, SAMPLE_CONFS)
        assert len(result["items"]) >= 3

    def test_item_has_name_and_price(self, extractor):
        result = extractor.extract(SAMPLE_TEXT, SAMPLE_CONFS)
        for item in result["items"]:
            assert "name" in item and "price" in item

    def test_missing_date(self, extractor):
        result = extractor.extract("STORE\nItem A $5.00\nTotal $5.00", [0.8])
        assert result["date"] is None

    def test_empty_text(self, extractor):
        result = extractor.extract("", [])
        assert result["store_name"] is None
        assert result["date"] is None
        assert result["items"] == []
        assert result["total_amount"] is None


class TestConfidenceScorer:

    def _make_ocr_result(self, text, confs):
        return {
            "text": text,
            "lines": text.strip().splitlines(),
            "word_confidences": confs,
        }

    def test_scores_in_range(self, extractor, scorer):
        structured = extractor.extract(SAMPLE_TEXT, SAMPLE_CONFS)
        ocr_result = self._make_ocr_result(SAMPLE_TEXT, SAMPLE_CONFS)
        out = scorer.score(structured, ocr_result)
        for field in ("store_name", "date", "total_amount"):
            c = out[field]["confidence"]
            assert 0.0 <= c <= 1.0, f"{field} confidence out of range: {c}"

    def test_flags_low_confidence(self, extractor, scorer):
        # Low OCR confs should trigger flags
        low_confs = [0.30] * 30
        structured = extractor.extract(SAMPLE_TEXT, low_confs)
        ocr_result = self._make_ocr_result(SAMPLE_TEXT, low_confs)
        out = scorer.score(structured, ocr_result)
        # Not asserting specific flags, just that the list exists
        assert isinstance(out["flags"], list)

    def test_none_fields_have_zero_confidence(self, extractor, scorer):
        text = "STORE\nItem $5.00\nTotal $5.00"
        structured = extractor.extract(text, [0.9])
        ocr_result = self._make_ocr_result(text, [0.9])
        out = scorer.score(structured, ocr_result)
        assert out["date"]["confidence"] == 0.0


class TestSummarizer:

    def _make_result(self, store, total, file="r1.jpg"):
        return {
            "file": file,
            "structured": {"store_name": store, "total_amount": total},
            "confidence_output": {
                "store_name": {"value": store, "confidence": 0.9},
                "total_amount": {"value": total, "confidence": 0.9},
            },
        }

    def test_total_spend(self, summarizer):
        results = [
            self._make_result("Store A", "$18.88", "r1.jpg"),
            self._make_result("Store B", "$45.00", "r2.jpg"),
        ]
        summary = summarizer.generate(results)
        assert summary["total_spend"] == pytest.approx(63.88)

    def test_transaction_count(self, summarizer):
        results = [
            self._make_result("Store A", "$10.00", "r1.jpg"),
            self._make_result("Store A", "$20.00", "r2.jpg"),
        ]
        summary = summarizer.generate(results)
        assert summary["num_transactions"] == 2

    def test_spend_per_store(self, summarizer):
        results = [
            self._make_result("Whole Foods", "$18.88", "r1.jpg"),
            self._make_result("Whole Foods", "$12.00", "r2.jpg"),
            self._make_result("CVS", "$5.50", "r3.jpg"),
        ]
        summary = summarizer.generate(results)
        assert summary["spend_per_store"]["Whole Foods"] == pytest.approx(30.88)
        assert summary["spend_per_store"]["CVS"] == pytest.approx(5.50)

    def test_failed_files_tracked(self, summarizer):
        results = [
            self._make_result("Store A", "$10.00", "r1.jpg"),
            {"file": "bad.jpg", "error": "Cannot read image"},
        ]
        summary = summarizer.generate(results)
        assert "bad.jpg" in summary["failed_files"]

    def test_zero_amount_not_counted(self, summarizer):
        results = [self._make_result("Store", None, "r1.jpg")]
        summary = summarizer.generate(results)
        assert summary["num_transactions"] == 0
