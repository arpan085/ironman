"""Color tracking mode."""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from ..core.base_mode import BaseMode
from .common import draw_instruction


class ColorTrackingMode(BaseMode):
    """Track selected color blob and draw motion trail."""

    name = "color_tracking"
    shortcut = "F1"

    def __init__(self) -> None:
        """Initialize HSV bounds and history."""

        self.lower = np.array([20, 100, 100])
        self.upper = np.array([40, 255, 255])
        self.trail: deque[tuple[int, int]] = deque(maxlen=64)

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect object centroid and visualize movement trajectory."""

        import cv2  # type: ignore

        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, self.lower, self.upper)
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        if cnts:
            c = max(cnts, key=cv2.contourArea)
            x, y, w, h = cv2.boundingRect(c)
            cx, cy = x + w // 2, y + h // 2
            self.trail.appendleft((cx, cy))
            cv2.rectangle(frame, (x, y), (x + w, y + h), (30, 240, 240), 2)
            cv2.putText(frame, f"Coord: ({cx}, {cy})", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        for i in range(1, len(self.trail)):
            cv2.line(frame, self.trail[i - 1], self.trail[i], (255, 150, 0), 2)
        draw_instruction(frame, "F1", "color_tracking", "Track color blob")
        return frame
