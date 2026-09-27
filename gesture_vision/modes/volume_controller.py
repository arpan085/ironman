"""Gesture volume control mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from ..core.smoothing import FloatFilter
from ..core.system_controls import distance, normalize_percentage, set_volume
from .common import draw_instruction


class VolumeControllerMode(BaseMode):
    """Control system volume via thumb-index pinch distance."""

    name = "gesture_volume_controller"
    shortcut = "5"

    def __init__(self) -> None:
        """Initialize last known percentage and update throttle."""

        self.volume = 0
        self._last_applied = -1
        self._frame = 0
        self.filter = FloatFilter(alpha=0.25)

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Apply distance-to-volume mapping and show bar."""

        import cv2  # type: ignore

        thumb = landmarks.get("thumb_tip")
        index = landmarks.get("index_tip")
        self._frame += 1
        if thumb is not None and index is not None:
            raw_distance = distance(thumb, index)
            self.volume = int(self.filter.apply(normalize_percentage(raw_distance)))
            if self._frame % 4 == 0 and abs(self.volume - self._last_applied) >= 2:
                set_volume(self.volume)
                self._last_applied = self.volume

        cv2.rectangle(frame, (20, 130), (55, 360), (70, 70, 70), 2)
        top = int(360 - (230 * self.volume / 100))
        cv2.rectangle(frame, (22, top), (53, 358), (0, 220, 255), -1)
        draw_instruction(frame, "5", "gesture_volume_controller", "Pinch to adjust")
        cv2.putText(frame, f"Volume: {self.volume}%", (18, 115), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        return frame
