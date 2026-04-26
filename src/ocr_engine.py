"""
ocr_engine.py
Wraps EasyOCR (primary) with Tesseract fallback.
Returns raw text + per-word confidence scores.
"""

import numpy as np
import logging

logger = logging.getLogger(__name__)


class OCREngine:
    """
    Primary: EasyOCR
    Fallback: pytesseract
    """

    def __init__(self, languages: list = None, engine: str = "easyocr"):
        self.languages = languages or ["en"]
        self.engine = engine
        self._reader = None

    def _get_reader(self):
        if self._reader is None:
            if self.engine == "easyocr":
                try:
                    import easyocr
                    self._reader = easyocr.Reader(self.languages, gpu=False)
                    logger.info("EasyOCR reader initialised.")
                except ImportError:
                    logger.warning("EasyOCR not installed – falling back to Tesseract.")
                    self.engine = "tesseract"
            if self.engine == "tesseract":
                try:
                    import pytesseract
                    self._reader = pytesseract
                    logger.info("Tesseract reader initialised.")
                except ImportError:
                    raise RuntimeError(
                        "No OCR backend found. "
                        "Install easyocr or pytesseract."
                    )
        return self._reader

    # ------------------------------------------------------------------ #
    def extract_text(self, img: np.ndarray) -> dict:
        """
        Returns:
            {
              "text": str,                         # full concatenated text
              "word_confidences": list[float],     # 0-1 per word/line
              "lines": list[str],                  # individual lines
              "raw": list                          # engine-native output
            }
        """
        reader = self._get_reader()

        if self.engine == "easyocr":
            return self._run_easyocr(reader, img)
        return self._run_tesseract(reader, img)

    # ------------------------------------------------------------------ #
    def _run_easyocr(self, reader, img: np.ndarray) -> dict:
        results = reader.readtext(img, detail=1, paragraph=False)
        lines, confs = [], []
        for bbox, text, conf in results:
            if text.strip():
                lines.append(text.strip())
                confs.append(float(conf))
        return {
            "text": "\n".join(lines),
            "lines": lines,
            "word_confidences": confs,
            "raw": results,
        }

    def _run_tesseract(self, tess, img: np.ndarray) -> dict:
        import pytesseract
        data = tess.image_to_data(
            img,
            output_type=pytesseract.Output.DICT,
            config="--oem 3 --psm 6",
        )
        lines, confs = [], []
        current_line_words, current_line_confs = [], []
        prev_line_num = -1

        for i, word in enumerate(data["text"]):
            word = word.strip()
            conf = int(data["conf"][i])
            line_num = data["line_num"][i]

            if conf == -1:          # separator row
                if current_line_words:
                    lines.append(" ".join(current_line_words))
                    confs.append(
                        sum(current_line_confs) / len(current_line_confs) / 100
                    )
                    current_line_words, current_line_confs = [], []
                continue

            if word:
                if line_num != prev_line_num and current_line_words:
                    lines.append(" ".join(current_line_words))
                    confs.append(
                        sum(current_line_confs) / len(current_line_confs) / 100
                    )
                    current_line_words, current_line_confs = [], []
                current_line_words.append(word)
                current_line_confs.append(conf)
                prev_line_num = line_num

        if current_line_words:
            lines.append(" ".join(current_line_words))
            confs.append(sum(current_line_confs) / len(current_line_confs) / 100)

        return {
            "text": "\n".join(lines),
            "lines": lines,
            "word_confidences": confs,
            "raw": data,
        }
