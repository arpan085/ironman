"""Finger counter mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode


class FingerCounterMode(BaseMode):
    """Display finger count in real time."""

    name = "finger_counter"
    shortcut = "3"

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render detected finger count overlay."""

        import cv2  # type: ignore

        count = int(landmarks.get("fingers_up", 0))
        cv2.putText(frame, f"3 Finger Counter: {count}", (18, 38), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (60, 255, 120), 2)
        return frame
