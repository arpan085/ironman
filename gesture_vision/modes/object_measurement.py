"""Object and finger measurement mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from ..core.smoothing import FloatFilter
from ..core.system_controls import distance
from .common import draw_instruction


class ObjectMeasurementMode(BaseMode):
    """Measure distances using fingertip calibration ratio."""

    name = "object_measurement"
    shortcut = "F2"

    def __init__(self) -> None:
        """Initialize pixels-per-unit calibration."""

        self.px_per_cm = 400.0
        self.filter = FloatFilter(alpha=0.25)

    def calibrate(self, distance_norm: float, real_cm: float = 5.0) -> None:
        """Update calibration ratio from known reference distance."""

        if distance_norm > 1e-6 and real_cm > 0:
            self.px_per_cm = (distance_norm * 1000.0) / real_cm

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Display pinch distance converted to approximate centimeters."""

        import cv2  # type: ignore

        thumb = landmarks.get("thumb_tip")
        index = landmarks.get("index_tip")
        cm = 0.0
        if thumb is not None and index is not None:
            d = distance(thumb, index)
            smoothed = self.filter.apply((d * 1000.0) / max(self.px_per_cm, 1e-6))
            cm = smoothed
        draw_instruction(frame, "F2", "object_measurement", "Pinch to measure")
        cv2.putText(frame, f"Pinch distance: {cm:.2f} cm", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (80, 255, 180), 2)
        return frame
