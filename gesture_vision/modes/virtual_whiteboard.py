"""Virtual whiteboard mode."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..core.base_mode import BaseMode
from .common import finger_xy


class VirtualWhiteboardMode(BaseMode):
    """Fullscreen board with multi-color strokes and primitive shape mode."""

    name = "virtual_whiteboard"
    shortcut = "0"

    def __init__(self) -> None:
        """Initialize whiteboard drawing state."""

        self.board: np.ndarray | None = None
        self.color = (0, 0, 0)
        self.prev: tuple[int, int] | None = None

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw marker strokes onto a bright white board."""

        import cv2  # type: ignore

        if self.board is None or self.board.shape != frame.shape:
            self.board = np.full_like(frame, 255)

        point = finger_xy(landmarks, frame.shape)
        if point is not None and self.prev is not None:
            cv2.line(self.board, self.prev, point, self.color, 4, cv2.LINE_AA)
        self.prev = point
        cv2.putText(self.board, "0 Whiteboard | T text placeholder | H shape mode", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (40, 40, 40), 2)
        return self.board.copy()
