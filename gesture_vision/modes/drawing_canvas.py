"""Virtual Drawing Canvas mode."""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from ..config import AppConfig, load_config
from ..core.base_mode import BaseMode
from .common import draw_instruction, finger_xy


class VirtualDrawingCanvasMode(BaseMode):
    """Finger-based drawing with palette, undo, clear, and save support."""

    name = "virtual_drawing_canvas"
    shortcut = "1"

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialize drawing state."""

        self.config = config or load_config()
        self.canvas: np.ndarray | None = None
        self.color = self.config.draw_color
        self.brush_size = self.config.brush_size
        self.eraser_size = self.config.eraser_size
        self.eraser = False
        self.prev: tuple[int, int] | None = None
        self.history: deque[np.ndarray] = deque(maxlen=15)

    def _ensure_canvas(self, frame: np.ndarray) -> np.ndarray:
        """Create transparent canvas matching frame size."""

        if self.canvas is None or self.canvas.shape != frame.shape:
            self.canvas = np.zeros_like(frame)
        return self.canvas

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw strokes when index finger is present."""

        import cv2  # type: ignore

        canvas = self._ensure_canvas(frame)
        point = finger_xy(landmarks, frame.shape)
        if point is None:
            self.prev = None
        else:
            if self.prev is not None:
                color = (0, 0, 0) if self.eraser else self.color
                size = max(2, (self.eraser_size if self.eraser else self.brush_size) * (2 if self.eraser else 1))
                cv2.line(canvas, self.prev, point, color, size, cv2.LINE_AA)
            self.prev = point

        blended = cv2.addWeighted(frame, 1.0, canvas, 0.95, 0)
        draw_instruction(blended, "1", "virtual_drawing_canvas", "C clear | U undo | E eraser | P palette | S save")
        return blended

    def cycle_palette(self) -> None:
        """Cycle through a fixed color palette."""

        palette = [(0, 255, 255), (255, 80, 80), (80, 255, 120), (200, 100, 255), (255, 255, 255)]
        idx = (palette.index(self.color) + 1) % len(palette) if self.color in palette else 0
        self.color = palette[idx]
        self.config.draw_color = self.color

    def snapshot(self) -> None:
        """Store current canvas for undo."""

        if self.canvas is not None:
            self.history.append(self.canvas.copy())

    def undo(self) -> None:
        """Restore the previous canvas state."""

        if self.history:
            self.canvas = self.history.pop()
        self.prev = None

    def clear(self) -> None:
        """Clear canvas content."""

        if self.canvas is not None:
            self.snapshot()
            self.canvas[:] = 0
