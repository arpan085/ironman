"""MediaPipe hand tracking wrapper using the modern tasks API."""

from __future__ import annotations

import math
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

        empty: dict[str, Any] = {
            "hands": [],
            "handedness": [],
            "fingers": [],
            "fingers_up": 0,
            "index_tip": None,
            "thumb_tip": None,
            "wrist": None,
            "palm_center": None,
            "is_pinch": False,
            "pinch_distance": 1.0,
            "is_open_palm": False,
            "is_fist": False,
            "finger_states": [],
        }

        if not self.available or self._landmarker is None:
            return empty

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
        wrist = hands[0][0] if hands else None

        # Derive palm center (average of base knuckles + wrist)
        palm_center = None
        is_pinch = False
        pinch_dist = 1.0
        finger_states: list[bool] = []
        is_open_palm = False
        is_fist = False

        if hands:
            h0 = hands[0]
            palm_x = (h0[0].x + h0[5].x + h0[9].x + h0[13].x + h0[17].x) / 5.0
            palm_y = (h0[0].y + h0[5].y + h0[9].y + h0[13].y + h0[17].y) / 5.0
            palm_z = (h0[0].z + h0[5].z + h0[9].z + h0[13].z + h0[17].z) / 5.0
            palm_center = HandPoint(palm_x, palm_y, palm_z)

            # Pinch calculation (thumb tip to index tip normalized distance)
            if index_tip and thumb_tip:
                pinch_dist = math.hypot(index_tip.x - thumb_tip.x, index_tip.y - thumb_tip.y)
                is_pinch = pinch_dist < 0.07

            lbl = handedness[0] if handedness else "Right"
            finger_states = self._get_finger_states(h0, lbl)
            raised = fingers[0] if fingers else 0
            is_open_palm = raised >= 4
            is_fist = raised == 0

        return {
            "hands": hands,
            "handedness": handedness,
            "fingers": fingers,
            "fingers_up": fingers[0] if fingers else 0,
            "index_tip": index_tip,
            "thumb_tip": thumb_tip,
            "wrist": wrist,
            "palm_center": palm_center,
            "is_pinch": is_pinch,
            "pinch_distance": pinch_dist,
            "is_open_palm": is_open_palm,
            "is_fist": is_fist,
            "finger_states": finger_states,
        }

    def _get_finger_states(self, points: list[HandPoint], label: str) -> list[bool]:
        """Return boolean states [thumb, index, middle, ring, pinky] for raised fingers."""

        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        states: list[bool] = []

        # Thumb
        if label == "Left":
            states.append(points[tips[0]].x < points[pips[0]].x)
        else:
            states.append(points[tips[0]].x > points[pips[0]].x)

        # 4 fingers
        for tip, pip in zip(tips[1:], pips[1:]):
            states.append(points[tip].y < points[pip].y)

        return states

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
