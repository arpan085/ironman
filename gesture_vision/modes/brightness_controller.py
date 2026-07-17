"""Gesture brightness control mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from ..core.system_controls import distance, normalize_percentage, set_brightness


class BrightnessControllerMode(BaseMode):
    """Control monitor brightness from finger distance."""

    name = "brightness_controller"
    shortcut = "6"

    def __init__(self) -> None:
        """Initialize brightness percentage cache."""

        self.brightness = 50

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Apply brightness update and draw live percentage."""

        import cv2  # type: ignore

        thumb = landmarks.get("thumb_tip")
        index = landmarks.get("index_tip")
        if thumb is not None and index is not None:
            self.brightness = normalize_percentage(distance(thumb, index))
            set_brightness(self.brightness)

        cv2.putText(frame, f"6 Brightness: {self.brightness}%", (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 255, 120), 2)
        return frame
