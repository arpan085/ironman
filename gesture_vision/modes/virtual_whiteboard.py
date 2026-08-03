"""Virtual whiteboard mode."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..config import AppConfig, load_config
from ..core.base_mode import BaseMode
from .common import draw_instruction, finger_xy


class VirtualWhiteboardMode(BaseMode):
    """Fullscreen board with multi-color strokes and primitive shape mode."""

    name = "virtual_whiteboard"
    shortcut = "0"

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialize whiteboard drawing state."""

        self.config = config or load_config()
        self.board: np.ndarray | None = None
        self.color = self.config.draw_color
        self.brush_size = self.config.brush_size
        self.prev: tuple[int, int] | None = None
        self.palette = [(0, 0, 0), (255, 0, 0), (0, 128, 255), (0, 180, 0)]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw marker strokes onto a bright white board."""

        import cv2  # type: ignore

        if self.board is None or self.board.shape != frame.shape:
            self.board = np.full_like(frame, 255)

        point = finger_xy(landmarks, frame.shape)
        if point is not None and self.prev is not None:
            cv2.line(self.board, self.prev, point, self.color, max(2, self.brush_size), cv2.LINE_AA)
        self.prev = point
        draw_instruction(self.board, "0", "virtual_whiteboard", "P palette | H shape mode")
        return self.board.copy()

    def cycle_palette(self) -> None:
        """Cycle through a palette of whiteboard colors."""

        current = self.color
        idx = (self.palette.index(current) + 1) % len(self.palette) if current in self.palette else 0
        self.color = self.palette[idx]
        self.config.draw_color = self.color

    def toggle_style(self) -> None:
        """Alias to cycle_palette for the shared shortcut handler."""

        self.cycle_palette()
