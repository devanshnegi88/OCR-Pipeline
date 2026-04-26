"""
main.py
Carbon Crunch – AI OCR Pipeline entry point.

Usage:
    python main.py --input data/receipts --output output
"""

import os
import argparse
import logging
from pathlib import Path

from src.preprocessor import ImagePreprocessor
from src.ocr_engine import OCREngine
from src.extractor import InformationExtractor
from src.confidence import ConfidenceScorer
from src.summarizer import FinancialSummarizer
from src.utils import setup_logging, save_json

logger = setup_logging(__name__)

IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".tiff", ".tif", ".webp"}


def process_one(path: str, preprocessor, ocr, extractor, scorer) -> dict:
    preprocessed = preprocessor.preprocess(path)
    ocr_result = ocr.extract_text(preprocessed)
    structured = extractor.extract(ocr_result["text"], ocr_result["word_confidences"])
    confidence_output = scorer.score(structured, ocr_result)
    return {
        "file": os.path.basename(path),
        "raw_text": ocr_result["text"],
        "structured": structured,
        "confidence_output": confidence_output,
    }


def run(input_dir: str, output_dir: str):
    in_path = Path(input_dir)
    out_path = Path(output_dir)
    (out_path / "receipts").mkdir(parents=True, exist_ok=True)

    preprocessor = ImagePreprocessor()
    ocr = OCREngine()
    extractor = InformationExtractor()
    scorer = ConfidenceScorer()
    summarizer = FinancialSummarizer()

    images = sorted(f for f in in_path.iterdir() if f.suffix.lower() in IMAGE_EXTS)
    if not images:
        logger.warning(f"No images found in {input_dir}")
        return

    all_results = []
    for img in images:
        logger.info(f"Processing {img.name} ...")
        try:
            result = process_one(str(img), preprocessor, ocr, extractor, scorer)
            save_json(result, out_path / "receipts" / f"{img.stem}_output.json")
            logger.info(f"  ✓ Saved {img.stem}_output.json")
        except Exception as e:
            logger.error(f"  ✗ Failed: {e}")
            result = {"file": img.name, "error": str(e)}
        all_results.append(result)

    summary = summarizer.generate(all_results)
    save_json(summary, out_path / "financial_summary.json")
    save_json({"receipts": all_results, "summary": summary}, out_path / "all_results.json")

    logger.info(f"\nDone — {len(images)} images processed.")
    logger.info(f"Total spend: {summary['total_spend']}")
    logger.info(f"Transactions: {summary['num_transactions']}")
    return {"receipts": all_results, "summary": summary}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Carbon Crunch AI-OCR Pipeline")
    parser.add_argument("--input", "-i", default="data/receipts", help="Folder with receipt images")
    parser.add_argument("--output", "-o", default="output", help="Output folder")
    args = parser.parse_args()
    run(args.input, args.output)
