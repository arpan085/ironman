"""Virtual Drawing Canvas mode."""

from __future__ import annotations

from collections import deque
from typing import Any

import numpy as np

from ..config import AppConfig, load_config
from ..core.base_mode import BaseMode
from ..core.smoothing import PointFilter
from .common import draw_instruction, finger_xy


class VirtualDrawingCanvasMode(BaseMode):
    """Finger-based drawing with palette, undo, clear, and save support."""

    name = "virtual_drawing_canvas"
    shortcut = "1"

    def __init__(
        self,
        config: AppConfig | None = None,
        brush_size: int | None = None,
        eraser_size: int | None = None,
        draw_color: tuple[int, int, int] | None = None,
        smooth_factor: float | None = None,
    ) -> None:
        """Initialize drawing state from config values or defaults."""

        self.config = config or load_config()
        self.canvas: np.ndarray | None = None
        self.brush_size = brush_size if brush_size is not None else self.config.brush_size
        self.eraser_size = eraser_size if eraser_size is not None else self.config.eraser_size
        self.color = draw_color if draw_color is not None else self.config.draw_color
        self.smooth_factor = smooth_factor if smooth_factor is not None else self.config.smooth_factor
        self.filter = PointFilter(alpha=self.smooth_factor)
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
            self.filter.initialized = False
        else:
            smooth = self.filter.apply(*point)
            if self.prev is None:
                self.snapshot()
            if self.prev is not None:
                color = (0, 0, 0) if self.eraser else self.color
                size = max(2, self.eraser_size if self.eraser else self.brush_size)
                cv2.line(canvas, self.prev, smooth, color, size, cv2.LINE_AA)
            self.prev = smooth

        blended = cv2.addWeighted(frame, 1.0, canvas, 0.95, 0)
        draw_instruction(blended, "1", "virtual_drawing_canvas", "C clear | U undo | E eraser | P palette | S save")
        return blended

    def on_key(self, key: int, char: str = "") -> bool:
        """Cycle palette with the P key or toggle eraser with E."""

        if key in {ord("p"), ord("P")}:
            self.cycle_palette()
            return True
        if key in {ord("e"), ord("E")}:
            self.eraser = not self.eraser
            return True
        if key in {ord("u"), ord("U")}:
            self.undo()
            return True
        if key in {ord("c"), ord("C")}:
            self.clear()
            return True
        return False

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
