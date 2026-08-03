"""Finger counter mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction


class FingerCounterMode(BaseMode):
    """Display finger count in real time."""

    name = "finger_counter"
    shortcut = "3"

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render detected finger count overlay."""

        import cv2  # type: ignore

        count = int(landmarks.get("fingers_up", 0))
        draw_instruction(frame, "3", "finger_counter", f"Count {count}")
        cv2.putText(frame, f"Detected: {count}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (60, 255, 120), 2)
        return frame
