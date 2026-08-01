"""Smart Magnifier - picture-in-picture zoom that follows your fingertip."""

from __future__ import annotations

from typing import Any

import cv2  # type: ignore
import numpy as np  # type: ignore

from ..core.base_mode import BaseMode
from .common import finger_xy


class MagnifierMode(BaseMode):
    """Shows a zoomed circular inset centered on the index fingertip."""

    name = "magnifier"
    shortcut = "F18"

    def __init__(self) -> None:
        """Configure the zoom strength."""

        self.zoom = 2.5
        self.radius = 110

    def on_key(self, key: int, char: str) -> bool:
        """Adjust zoom with +/- keys."""

        if char == "+":
            self.zoom = min(6.0, self.zoom + 0.5)
            return True
        if char == "-":
            self.zoom = max(1.5, self.zoom - 0.5)
            return True
        return False

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw the magnified inset and a crosshair on the fingertip."""

        h, w = frame.shape[:2]
        pt = finger_xy(landmarks, frame.shape)
        if pt is not None:
            cx, cy = pt
            half = int(self.radius / self.zoom)
            x1, y1 = max(0, cx - half), max(0, cy - half)
            x2, y2 = min(w, cx + half), min(h, cy + half)
            if x2 > x1 and y2 > y1:
                region = frame[y1:y2, x1:x2]
                zoomed = cv2.resize(region, (self.radius * 2, self.radius * 2), interpolation=cv2.INTER_LINEAR)
                mask = np.zeros((self.radius * 2, self.radius * 2), dtype=np.uint8)
                cv2.circle(mask, (self.radius, self.radius), self.radius, 255, -1)
                pip = np.zeros_like(zoomed)
                pip[mask == 255] = zoomed[mask == 255]

                fx, fy = w - self.radius - 16, self.radius + 16
                x0, y0 = fx - self.radius, fy - self.radius
                pip = pip[0 : min(2 * self.radius, h - y0), 0 : min(2 * self.radius, w - x0)]
                frame[y0 : y0 + pip.shape[0], x0 : x0 + pip.shape[1]] = pip
                cv2.circle(frame, (fx, fy), self.radius, (0, 229, 255), 3)
                cv2.line(frame, (cx - 14, cy), (cx + 14, cy), (0, 229, 255), 2)
                cv2.line(frame, (cx, cy - 14), (cx, cy + 14), (0, 229, 255), 2)

        cv2.putText(frame, "F18 Magnifier | fingertip zooms, +/- adjusts strength", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Zoom x{self.zoom:.1f}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 200), 2)
        return frame
