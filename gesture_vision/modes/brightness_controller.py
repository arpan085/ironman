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
        """Initialize brightness percentage cache and throttle."""

        self.brightness = 50
        self._last_applied = -1
        self._frame = 0

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Apply brightness update and draw live percentage."""

        import cv2  # type: ignore

        thumb = landmarks.get("thumb_tip")
        index = landmarks.get("index_tip")
        self._frame += 1
        if thumb is not None and index is not None:
            self.brightness = normalize_percentage(distance(thumb, index))
            if self._frame % 4 == 0 and abs(self.brightness - self._last_applied) >= 2:
                set_brightness(self.brightness)
                self._last_applied = self.brightness

        cv2.putText(frame, f"6 Brightness: {self.brightness}%", (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 255, 120), 2)
        return frame
