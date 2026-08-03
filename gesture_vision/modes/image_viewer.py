"""Gesture image viewer mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction, resolve_package_path


class ImageViewerMode(BaseMode):
    """Swipe/zoom/rotate image viewer controlled by gesture counts."""

    name = "image_viewer"
    shortcut = "F4"

    def __init__(self, image_dir: str | Path | None = None) -> None:
        """Load images from configured folder."""

        self.image_dir = Path(image_dir) if image_dir is not None else resolve_package_path("images")
        self.index = 0
        self.zoom = 1.0
        self.angle = 0.0
        self.paths = sorted([p for p in self.image_dir.glob("*.*") if p.suffix.lower() in {".png", ".jpg", ".jpeg"}])

    def next(self) -> None:
        """Move to next image."""

        if self.paths:
            self.index = (self.index + 1) % len(self.paths)

    def prev(self) -> None:
        """Move to previous image."""

        if self.paths:
            self.index = (self.index - 1) % len(self.paths)

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render selected image with transform parameters."""

        import cv2  # type: ignore

        canvas = frame.copy()
        if self.paths:
            image = cv2.imread(str(self.paths[self.index]))
            if image is not None:
                h, w = image.shape[:2]
                resized = cv2.resize(image, (max(1, int(w * self.zoom)), max(1, int(h * self.zoom))))
                center = (resized.shape[1] // 2, resized.shape[0] // 2)
                matrix = cv2.getRotationMatrix2D(center, self.angle, 1.0)
                rotated = cv2.warpAffine(resized, matrix, (resized.shape[1], resized.shape[0]))
                hh, ww = canvas.shape[:2]
                rh, rw = rotated.shape[:2]
                x = max(0, (ww - rw) // 2)
                y = max(0, (hh - rh) // 2)
                canvas[y : y + min(hh - y, rh), x : x + min(ww - x, rw)] = rotated[: min(hh - y, rh), : min(ww - x, rw)]

        draw_instruction(canvas, "F4", "image_viewer", "[ ] swipe | -/+ zoom | R rotate")
        return canvas
