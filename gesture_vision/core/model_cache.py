"""Runtime model/asset download and cache helpers."""

from __future__ import annotations

import logging
from pathlib import Path
import urllib.error
import urllib.request

logger = logging.getLogger(__name__)

MODELS_DIR = Path(__file__).resolve().parent.parent / "assets" / "models"

HAND_LANDMARKER_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
HAAR_FRONTALFACE_URL = (
    "https://raw.githubusercontent.com/opencv/opencv/4.x/data/haarcascades/"
    "haarcascade_frontalface_default.xml"
)


def _download(url: str, target: Path) -> bool:
    """Download a URL to a file with retries and a timeout."""

    for attempt in range(3):
        try:
            logger.info("Downloading %s (attempt %d/3)", url.rsplit("/", 1)[-1], attempt + 1)
            request = urllib.request.Request(url, headers={"User-Agent": "ironman-gesture-vision"})
            with urllib.request.urlopen(request, timeout=30) as response, open(target, "wb") as out:
                out.write(response.read())
            if target.stat().st_size > 0:
                return True
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            logger.warning("Download failed (%s); retrying", exc)
    return False


def ensure_model(name: str, url: str) -> Path | None:
    """Download a model to the local cache when missing.

    Returns the cached file path, or None when the model cannot be fetched.
    """

    try:
        MODELS_DIR.mkdir(parents=True, exist_ok=True)
        target = MODELS_DIR / name
        if not target.exists() or target.stat().st_size == 0:
            if not _download(url, target):
                logger.warning("Could not fetch model %s; related features disabled", name)
                return None
        if target.exists() and target.stat().st_size > 0:
            return target
    except Exception as exc:  # noqa: BLE001
        logger.warning("Model cache error for %s: %s", name, exc)
    return None
