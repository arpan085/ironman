"""Air painter with neon/rainbow/glow effects."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.base_mode import BaseMode
from ..core.smoothing import PointFilter
from .common import finger_xy


class AirPainterMode(BaseMode):
    """Smooth painter with visual effects for reels."""

    name = "air_painter"
    shortcut = "2"

    def __init__(self) -> None:
        """Initialize painter state and style options."""

        self.canvas: np.ndarray | None = None
        self.filter = PointFilter(alpha=0.3)
        self.frame_count = 0
        self.prev: tuple[int, int] | None = None
        self.style = "neon"

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render anti-shake smooth air brush strokes."""

        import cv2  # type: ignore

        if self.canvas is None or self.canvas.shape != frame.shape:
            self.canvas = np.zeros_like(frame)
        pt = finger_xy(landmarks, frame.shape)
        self.frame_count += 1

        if pt is not None:
            smooth = self.filter.apply(*pt)
            if self.prev is not None:
                if self.style == "rainbow":
                    color = (self.frame_count * 5 % 255, self.frame_count * 9 % 255, self.frame_count * 3 % 255)
                else:
                    color = (255, 255, 20)
                cv2.line(self.canvas, self.prev, smooth, color, 4, cv2.LINE_AA)
            self.prev = smooth
        else:
            self.prev = None

        glow = cv2.GaussianBlur(self.canvas, (0, 0), 3)
        mixed = cv2.addWeighted(frame, 1.0, self.canvas, 0.7, 0)
        mixed = cv2.addWeighted(mixed, 1.0, glow, 0.8, 0)
        cv2.putText(mixed, f"2 Air Painter ({self.style}) | P Style", (18, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return mixed

    def toggle_style(self) -> None:
        """Switch between neon and rainbow brushes."""

        self.style = "rainbow" if self.style == "neon" else "neon"
