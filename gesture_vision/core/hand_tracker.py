"""MediaPipe hand tracking wrapper using the modern tasks API."""

from __future__ import annotations

import os

os.environ.setdefault("GLOG_minloglevel", "2")
os.environ.setdefault("TF_CPP_MIN_LOG_LEVEL", "3")

from dataclasses import dataclass
import logging
from typing import Any

from .model_cache import HAND_LANDMARKER_URL, ensure_model

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class HandPoint:
    """Single normalized hand landmark."""

    x: float
    y: float
    z: float


class HandTracker:
    """Extract hand landmarks with graceful dependency fallback.

    Uses the current ``mediapipe.tasks`` HandLandmarker (VIDEO mode) and
    auto-downloads the model on first run.
    """

    def __init__(self, max_num_hands: int = 2) -> None:
        """Initialize the HandLandmarker when the model is available."""

        self.available = False
        self._landmarker = None
        self._mp = None
        self._frame_id = 0

        model = ensure_model("hand_landmarker.task", HAND_LANDMARKER_URL)
        if model is None:
            logger.warning("Hand landmarker model unavailable; hand tracking disabled")
            return

        try:
            import mediapipe as mp
            from mediapipe.tasks.python import vision
            from mediapipe.tasks.python.core.base_options import BaseOptions

            self._mp = mp
            options = vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(model)),
                running_mode=vision.RunningMode.VIDEO,
                num_hands=max_num_hands,
                min_hand_detection_confidence=0.5,
                min_hand_presence_confidence=0.5,
                min_tracking_confidence=0.5,
            )
            self._landmarker = vision.HandLandmarker.create_from_options(options)
            self.available = True
        except Exception as exc:  # noqa: BLE001
            logger.warning("Hand landmarker init failed: %s", exc)
            self.available = False

    def process(self, frame_bgr: Any) -> dict[str, Any]:
        """Return parsed landmarks and derived gesture values."""

        if not self.available or self._landmarker is None:
            return {"hands": [], "index_tip": None, "thumb_tip": None, "fingers_up": 0}

        import cv2  # type: ignore

        self._frame_id += 1
        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        image = self._mp.Image(image_format=self._mp.ImageFormat.SRGB, data=rgb)
        result = self._landmarker.detect_for_video(image, self._frame_id)

        hands: list[list[HandPoint]] = [
            [HandPoint(p.x, p.y, p.z) for p in points] for points in result.hand_landmarks
        ]
        handedness = [
            hd[0].category_name if hd else "Unknown" for hd in result.handedness
        ]
        fingers = [
            self._count_fingers(points, label) for points, label in zip(hands, handedness)
        ]

        index_tip = hands[0][8] if hands else None
        thumb_tip = hands[0][4] if hands else None
        return {
            "hands": hands,
            "handedness": handedness,
            "fingers": fingers,
            "fingers_up": fingers[0] if fingers else 0,
            "index_tip": index_tip,
            "thumb_tip": thumb_tip,
        }

    def _count_fingers(self, points: list[HandPoint], label: str) -> int:
        """Estimate number of raised fingers using handedness-aware thumb logic."""

        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        count = 0

        if label == "Left":
            if points[tips[0]].x < points[pips[0]].x:
                count += 1
        else:
            if points[tips[0]].x > points[pips[0]].x:
                count += 1

        for tip, pip in zip(tips[1:], pips[1:]):
            if points[tip].y < points[pip].y:
                count += 1

        return count
