"""Gesture brightness control mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from ..core.smoothing import FloatFilter
from ..core.system_controls import distance, normalize_percentage, set_brightness
from .common import draw_instruction


class BrightnessControllerMode(BaseMode):
    """Control monitor brightness from finger distance."""

    name = "brightness_controller"
    shortcut = "6"

    def __init__(self) -> None:
        """Initialize brightness percentage cache and throttle."""

        self.brightness = 50
        self._last_applied = -1
        self._frame = 0
        self.filter = FloatFilter(alpha=0.25)

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Apply brightness update and draw live percentage."""

        import cv2  # type: ignore

        thumb = landmarks.get("thumb_tip")
        index = landmarks.get("index_tip")
        self._frame += 1
        if thumb is not None and index is not None:
            raw_distance = distance(thumb, index)
            self.brightness = int(self.filter.apply(normalize_percentage(raw_distance)))
            if self._frame % 4 == 0 and abs(self.brightness - self._last_applied) >= 2:
                set_brightness(self.brightness)
                self._last_applied = self.brightness

        draw_instruction(frame, "6", "brightness_controller", "Pinch to adjust")
        cv2.putText(frame, f"Brightness: {self.brightness}%", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (200, 255, 120), 2)
        return frame
