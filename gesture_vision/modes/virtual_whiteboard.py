"""Virtual whiteboard mode."""

from __future__ import annotations

from typing import Any

import numpy as np

from ..config import AppConfig, load_config
from ..core.base_mode import BaseMode
from ..core.smoothing import PointFilter
from .common import draw_instruction, finger_xy


class VirtualWhiteboardMode(BaseMode):
    """Fullscreen board with multi-color strokes and eraser support."""

    name = "virtual_whiteboard"
    shortcut = "0"

    def __init__(
        self,
        config: AppConfig | None = None,
        brush_size: int | None = None,
        eraser_size: int = 18,
        draw_color: tuple[int, int, int] | None = None,
        smooth_factor: float = 0.35,
    ) -> None:
        """Initialize whiteboard drawing state from config values."""

        self.config = config or load_config()
        self.board: np.ndarray | None = None
        self.brush_size = brush_size if brush_size is not None else 4
        self.eraser_size = eraser_size
        self.smooth_factor = smooth_factor
        self.filter = PointFilter(alpha=smooth_factor)
        self.color = draw_color if draw_color is not None else (0, 0, 0)
        self.eraser = False
        self.prev: tuple[int, int] | None = None
        self.palette = [(0, 0, 0), (220, 40, 40), (40, 140, 220), (30, 180, 90), (200, 120, 220)]

    def cycle_palette(self) -> None:
        """Cycle through marker colors."""

        current = self.color
        idx = (self.palette.index(current) + 1) % len(self.palette) if current in self.palette else 0
        self.color = self.palette[idx]
        self.config.draw_color = self.color

    def toggle_style(self) -> None:
        """Cycle the marker color (bound to the global P key)."""

        self.cycle_palette()

    def clear(self) -> None:
        """Clear the board back to white."""

        if self.board is not None:
            self.board[:] = 255

    def on_key(self, key: int, char: str = "") -> bool:
        """Handle hotkeys: E for eraser, P for palette, C for clear."""

        if key in {ord("p"), ord("P")}:
            self.cycle_palette()
            return True
        if key in {ord("e"), ord("E")}:
            self.eraser = not self.eraser
            return True
        if key in {ord("c"), ord("C")}:
            self.clear()
            return True
        return False

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

        draw_instruction(self.board, "0", "virtual_whiteboard", "E eraser | P palette | C clear")
        return self.board.copy()
