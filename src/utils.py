"""
utils.py
Shared helpers: logging setup, JSON I/O, edge-case guards.
"""

import json
import logging
from pathlib import Path


def setup_logging(name: str = __name__, level: int = logging.INFO) -> logging.Logger:
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s – %(message)s",
        datefmt="%H:%M:%S",
    )
    return logging.getLogger(name)


def save_json(data: dict, path) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_json(path) -> dict:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)
