# OCR-Based Receipt Information Extraction

## Overview

This project extracts structured information from receipt images using an OCR pipeline. It handles real-world variations such as noise, skew, and inconsistent layouts, and outputs data in a structured JSON format along with confidence scores.

---

## Features

* Image preprocessing (denoising, contrast enhancement, deskewing)
* Text extraction using OCR
* Key field extraction:

  * Store name
  * Date
  * Items and prices
  * Total amount
* Field-level confidence scoring
* Handles noisy and partially visible receipts

---

## How to Run

1. Install dependencies:
   pip install -r requirements.txt

2. Run the pipeline:
   python main.py

3. Outputs will be saved in the `outputs/` folder as JSON files.

---

## Sample Output

```json
{
  "store_name": {
    "value": "ABC Store",
    "confidence": 0.92
  },
  "date": {
    "value": "12/03/2024",
    "confidence": 0.88
  },
  "total_amount": {
    "value": "₹450",
    "confidence": 0.95
  }
}
```

---

## Confidence Scoring

Confidence is calculated by combining:

* OCR confidence scores
* Pattern validation (date, currency format)
* Keyword detection (e.g., "Total", "Amount")

Low-confidence fields (< 0.7) are flagged.

---

## Challenges

* Handling different receipt layouts
* Low-quality and noisy images
* Missing or ambiguous fields

---

## Improvements

* Use layout-aware models (e.g., document understanding models)
* Fine-tune OCR for receipt-specific data
* Improve extraction using ML instead of heuristics

---

