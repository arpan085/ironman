"""MediaPipe hand tracking wrapper."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class HandPoint:
    """Single normalized hand landmark."""

    x: float
    y: float
    z: float


class HandTracker:
    """Extract hand landmarks with graceful dependency fallback."""

    def __init__(self, max_num_hands: int = 2) -> None:
        """Initialize MediaPipe Hands if installed."""

        self.available = False
        self._hands = None
        self._mp = None
        try:
            import mediapipe as mp  # type: ignore

            self._mp = mp
            self._hands = mp.solutions.hands.Hands(
                static_image_mode=False,
                max_num_hands=max_num_hands,
                min_detection_confidence=0.6,
                min_tracking_confidence=0.6,
            )
            self.available = True
        except Exception:
            self.available = False

    def process(self, frame_bgr: Any) -> dict[str, Any]:
        """Return parsed landmarks and derived gesture values."""

        if not self.available or self._hands is None:
            return {"hands": [], "index_tip": None, "thumb_tip": None, "fingers_up": 0}

        import cv2  # type: ignore

        rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self._hands.process(rgb)
        hands: list[list[HandPoint]] = []

        if result.multi_hand_landmarks:
            for hand_landmarks in result.multi_hand_landmarks:
                points = [HandPoint(lm.x, lm.y, lm.z) for lm in hand_landmarks.landmark]
                hands.append(points)

        index_tip = hands[0][8] if hands else None
        thumb_tip = hands[0][4] if hands else None
        fingers_up = self._count_fingers(hands[0]) if hands else 0
        return {
            "hands": hands,
            "index_tip": index_tip,
            "thumb_tip": thumb_tip,
            "fingers_up": fingers_up,
        }

    def _count_fingers(self, points: list[HandPoint]) -> int:
        """Estimate number of raised fingers for first hand."""

        tips = [4, 8, 12, 16, 20]
        pips = [3, 6, 10, 14, 18]
        count = 0

        if points[tips[0]].x > points[pips[0]].x:
            count += 1

        for tip, pip in zip(tips[1:], pips[1:]):
            if points[tip].y < points[pip].y:
                count += 1

        return count
