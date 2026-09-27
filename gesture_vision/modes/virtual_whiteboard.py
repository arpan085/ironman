"""Virtual whiteboard mode."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.base_mode import BaseMode
from ..core.smoothing import PointFilter
from .common import finger_xy


class VirtualWhiteboardMode(BaseMode):
    """Fullscreen board with multi-color strokes and eraser support."""

    name = "virtual_whiteboard"
    shortcut = "0"

    def __init__(
        self,
        brush_size: int = 4,
        eraser_size: int = 18,
        draw_color: tuple[int, int, int] = (0, 0, 0),
        smooth_factor: float = 0.35,
    ) -> None:
        """Initialize whiteboard drawing state from config values."""

        self.board: np.ndarray | None = None
        self.color = draw_color
        self.brush_size = brush_size
        self.eraser_size = eraser_size
        self.smooth_factor = smooth_factor
        self.filter = PointFilter(alpha=smooth_factor)
        self.eraser = False
        self.prev: tuple[int, int] | None = None
        self.palette = [(0, 0, 0), (220, 40, 40), (40, 140, 220), (30, 180, 90), (200, 120, 220)]

    def cycle_palette(self) -> None:
        """Cycle through marker colors."""

        idx = (self.palette.index(self.color) + 1) % len(self.palette) if self.color in self.palette else 0
        self.color = self.palette[idx]

    def toggle_style(self) -> None:
        """Cycle the marker color (bound to the global P key)."""

        self.cycle_palette()

    def clear(self) -> None:
        """Clear the board back to white."""

        if self.board is not None:
            self.board[:] = 255

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw marker strokes onto a bright white board."""

        import cv2  # type: ignore

        if self.board is None or self.board.shape != frame.shape:
            self.board = np.full_like(frame, 255)

        point = finger_xy(landmarks, frame.shape)
        if point is None:
            self.prev = None
            self.filter.initialized = False
        else:
            smooth = self.filter.apply(*point)
            if self.prev is not None:
                color = (255, 255, 255) if self.eraser else self.color
                size = self.eraser_size if self.eraser else self.brush_size
                cv2.line(self.board, self.prev, smooth, color, size, cv2.LINE_AA)
            self.prev = smooth

        cv2.putText(self.board, "0 Whiteboard | E Eraser | P Palette | C Clear", (18, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (60, 60, 60), 2, cv2.LINE_AA)
        return self.board.copy()
