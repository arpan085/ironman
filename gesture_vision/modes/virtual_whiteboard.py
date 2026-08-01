"""Virtual whiteboard mode."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.base_mode import BaseMode
from .common import finger_xy


class VirtualWhiteboardMode(BaseMode):
    """Fullscreen board with multi-color strokes and eraser support."""

    name = "virtual_whiteboard"
    shortcut = "0"

    def __init__(self) -> None:
        """Initialize whiteboard drawing state."""

        self.board: np.ndarray | None = None
        self.color = (0, 0, 0)
        self.eraser = False
        self.prev: tuple[int, int] | None = None
        self.palette = [(0, 0, 0), (220, 40, 40), (40, 140, 220), (30, 180, 90), (200, 120, 220)]

    def cycle_palette(self) -> None:
        """Cycle through marker colors."""

        idx = (self.palette.index(self.color) + 1) % len(self.palette) if self.color in self.palette else 0
        self.color = self.palette[idx]

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
        else:
            if self.prev is not None:
                color = (255, 255, 255) if self.eraser else self.color
                size = 18 if self.eraser else 4
                cv2.line(self.board, self.prev, point, color, size, cv2.LINE_AA)
            self.prev = point

        cv2.putText(self.board, "0 Whiteboard | E Eraser | P Palette | C Clear", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (60, 60, 60), 2)
        return self.board.copy()
