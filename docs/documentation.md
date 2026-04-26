# Carbon Crunch – AI OCR Pipeline
## Technical Documentation

---

### 1. Approach

The pipeline follows a four-stage architecture:

**Stage 1 – Image Preprocessing**  
Each receipt image is normalised before OCR to maximise text recognition accuracy:
- *Resize*: images narrower than 800 px are upscaled with bicubic interpolation.  
- *Deskew*: Hough line transform detects dominant text angle; images rotated > 0.5° are corrected.  
- *Contrast*: CLAHE (Contrast Limited Adaptive Histogram Equalisation) applied in LAB colour space.  
- *Denoise*: OpenCV Non-Local Means denoising removes sensor and compression noise.  
- *Binarise*: Adaptive Gaussian thresholding converts the image to clean black/white text.

**Stage 2 – Text Extraction (OCR)**  
EasyOCR is the primary engine. It returns per-detection confidence scores and handles rotated or curved text. If EasyOCR is not installed, pytesseract (Tesseract 5) is used as an automatic fallback. Both engines return:
- Full concatenated text
- Per-line/word confidence scores (0–1)

**Stage 3 – Key Field Extraction**  
A rule-and-regex extractor pulls five fields from the raw OCR text:

| Field | Strategy |
|-------|-----------|
| Store Name | First 1–4 non-price, non-keyword lines |
| Date | Regex matching ISO, DMY, MDY, and long-form date patterns |
| Items | Lines containing a price pattern, excluding header/footer keywords |
| Item Prices | Captured alongside item name via currency regex |
| Total Amount | Keyword anchor (`total`, `amount due`, …) + last-price fallback |

**Stage 4 – Confidence Scoring**  
Each extracted field is assigned a composite confidence score (0–1):

```
field_conf = w₁ × avg_ocr_conf + w₂ × pattern_bonus + w₃ × heuristic_bonus
```

- *OCR confidence* sourced from EasyOCR/Tesseract per-detection scores.  
- *Pattern validation*: dates matched against known formats, prices against `\d+[.,]\d{2}`.  
- *Heuristics*: presence of keywords like `"total"`, position of store name in first lines.  
- Fields scoring below **0.70** are flagged for manual review.

**Stage 5 – Financial Summary**  
Across all processed receipts: total spend, transaction count, and per-store breakdown are aggregated. Receipts that fail processing are tracked separately.

---

### 2. Tools Used

| Tool | Purpose |
|------|---------|
| **EasyOCR** | Primary OCR engine; deep-learning based, handles diverse fonts |
| **pytesseract** | Fallback OCR engine wrapping Tesseract 5 |
| **OpenCV** | All image preprocessing (skew, contrast, denoise, binarise) |
| **NumPy** | Array operations within preprocessing |
| **Python `re`** | Regex-based field extraction and pattern validation |
| **pytest** | Unit test suite covering extractor, scorer, and summarizer |

---

### 3. Challenges Faced

**Diverse receipt layouts**  
Receipts have no standard structure. Store names appear at varying line numbers; totals can be labelled differently ("Balance Due", "Grand Total", "Net Payable"). Solved with keyword lists and multi-strategy fallbacks.

**Inconsistent price formats**  
Prices appear as `$5.00`, `5.00`, `5,00` (European), and sometimes with trailing symbols. The currency regex handles all these variants.

**Noise and low-quality scans**  
Real-world receipts are crumpled, over-exposed, or poorly scanned. Combining CLAHE + Non-Local Means denoising significantly improves binarisation quality before OCR.

**Confidence calibration**  
OCR confidence alone is insufficient — a word like "TOTEL" may have high OCR confidence but wrong semantics. Pattern validation and keyword heuristics compensate.

**No ground-truth labels**  
Without annotated data, extraction accuracy cannot be measured with standard metrics. The confidence scoring framework is therefore rule-based rather than learned.

---

### 4. Possible Improvements

1. **Fine-tune a LayoutLM or Donut model** on labelled receipt data (e.g., CORD, SROIE datasets) for significantly higher extraction accuracy without hand-crafted rules.
2. **Multi-language support**: enable EasyOCR with additional language packs for non-English receipts.
3. **Currency normalisation**: convert all amounts to a single base currency using an exchange-rate API.
4. **Table detection**: use OpenCV contour detection to identify structured item tables before line-by-line parsing.
5. **Confidence learning**: replace heuristic confidence weights with a logistic regression trained on hand-labelled confidence labels.
6. **PDF/scan support**: add a PDF-to-image conversion step (via `pdf2image`) so the pipeline accepts scanned PDF receipts.
7. **REST API**: wrap `main.py` in a FastAPI endpoint for integration with downstream finance applications.

---

### 5. Output Format Reference

**Per-receipt JSON** (`output/receipts/<name>_output.json`):
```json
{
  "file": "receipt_001.jpg",
  "raw_text": "...",
  "structured": {
    "store_name": "...",
    "date": "...",
    "items": [{ "name": "...", "price": "..." }],
    "total_amount": "..."
  },
  "confidence_output": {
    "store_name":    { "value": "...", "confidence": 0.90 },
    "date":          { "value": "...", "confidence": 0.88 },
    "total_amount":  { "value": "...", "confidence": 0.93 },
    "items": [
      {
        "name":  { "value": "...", "confidence": 0.85 },
        "price": { "value": "...", "confidence": 0.87 }
      }
    ],
    "flags": []
  }
}
```

**Financial summary** (`output/financial_summary.json`):
```json
{
  "total_spend": 63.88,
  "num_transactions": 3,
  "spend_per_store": { "Whole Foods": 30.88, "CVS": 33.00 },
  "failed_files": [],
  "currency_note": "All amounts in document currency (not normalised)"
}
```
