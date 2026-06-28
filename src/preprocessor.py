"""
preprocessor.py
Handles noise removal, deskewing, and contrast normalization.
"""

import cv2
import numpy as np
import logging

logger = logging.getLogger(__name__)


class ImagePreprocessor:
    """Prepares receipt images for OCR."""

    def preprocess(self, image_path: str) -> np.ndarray:
        img = self._load(image_path)
        img = self._resize_if_small(img)
        img = self._deskew(img)
        img = self._enhance_contrast(img)
        img = self._denoise(img)
        img = self._binarize(img)
        return img

    # ------------------------------------------------------------------ #
    def _load(self, path: str) -> np.ndarray:
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Cannot read image: {path}")
        return img

    def _resize_if_small(self, img: np.ndarray, min_width: int = 800) -> np.ndarray:
        h, w = img.shape[:2]
        if w < min_width:
            scale = min_width / w
            img = cv2.resize(img, None, fx=scale, fy=scale,
                             interpolation=cv2.INTER_CUBIC)
        return img

    def _deskew(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        edges = cv2.Canny(cv2.GaussianBlur(gray, (5, 5), 0), 50, 150)
        lines = cv2.HoughLinesP(edges, 1, np.pi / 180,
                                threshold=80, minLineLength=50, maxLineGap=10)
        if lines is None:
            return img
        angles = [
            np.degrees(np.arctan2(y2 - y1, x2 - x1))
            for x1, y1, x2, y2 in lines[:, 0]
            if x2 != x1 and abs(np.degrees(np.arctan2(y2 - y1, x2 - x1))) < 45
        ]
        if not angles:
            return img
        angle = np.median(angles)
        if abs(angle) < 0.5:
            return img
        h, w = img.shape[:2]
        M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
        return cv2.warpAffine(img, M, (w, h),
                              flags=cv2.INTER_CUBIC,
                              borderMode=cv2.BORDER_REPLICATE)

    def _enhance_contrast(self, img: np.ndarray) -> np.ndarray:
        if img.ndim == 3:
            lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
            l, a, b = cv2.split(lab)
            l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
            return cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
        return cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(img)

    def _denoise(self, img: np.ndarray) -> np.ndarray:
        if img.ndim == 3:
            return cv2.fastNlMeansDenoisingColored(img, None, 10, 10, 7, 21)
        return cv2.fastNlMeansDenoising(img, None, 10, 7, 21)

    def _binarize(self, img: np.ndarray) -> np.ndarray:
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if img.ndim == 3 else img
        return cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=15, C=10
        )
