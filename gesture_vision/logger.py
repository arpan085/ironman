"""Logging utilities for the application."""

from __future__ import annotations

import logging
from pathlib import Path


def setup_logging(log_path: str = "gesture_vision.log") -> None:
    """Configure file and console logging handlers."""

    root = logging.getLogger()
    if root.handlers:
        return

    Path(log_path).parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(log_path, encoding="utf-8"),
        ],
    )
