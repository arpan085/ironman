"""Gesture image viewer mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.base_mode import BaseMode


class ImageViewerMode(BaseMode):
    """Swipe/zoom/rotate image viewer controlled by gestures and keys."""

    name = "image_viewer"
    shortcut = "F4"

    def __init__(self, image_dir: str = "images") -> None:
        """Load images from configured folder."""

        p = Path(image_dir)
        if not p.is_absolute() and not p.exists():
            root_candidate = Path(__file__).resolve().parents[2] / image_dir
            if root_candidate.exists():
                p = root_candidate
        self.image_dir = p
        self.index = 0
        self.zoom = 1.0
        self.angle = 0.0
        self.paths = sorted([img for img in self.image_dir.glob("*.*") if img.suffix.lower() in {".png", ".jpg", ".jpeg"}]) if self.image_dir.exists() else []

    def next(self) -> None:
        """Move to next image."""

        if self.paths:
            self.index = (self.index + 1) % len(self.paths)

    def prev(self) -> None:
        """Move to previous image."""

        if self.paths:
            self.index = (self.index - 1) % len(self.paths)

    def zoom_in(self) -> None:
        """Zoom into the current image."""

        self.zoom = min(4.0, self.zoom * 1.15)

    def zoom_out(self) -> None:
        """Zoom out of the current image."""

        self.zoom = max(0.25, self.zoom / 1.15)

    def reset_view(self) -> None:
        """Reset zoom and rotation."""

        self.zoom = 1.0
        self.angle = 0.0

    def on_key(self, key: int, char: str) -> bool:
        """Handle navigation, zoom, and rotation keys."""

        if key == ord("]") or key == ord("n"):
            self.next()
            return True
        if key == ord("[") or key == ord("p"):
            self.prev()
            return True
        if key == ord("+") or key == ord("="):
            self.zoom_in()
            return True
        if key == ord("-") or key == ord("_"):
            self.zoom_out()
            return True
        if key == ord("r"):
            self.reset_view()
            return True
        return False

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render selected image with transform parameters."""

        import cv2  # type: ignore

        canvas = frame.copy()
        cv2.putText(canvas, "F4 Image Viewer | [ ] swipe | -/+ zoom | R reset", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if not self.paths:
            cv2.putText(canvas, "No images found - add png/jpg to ./images", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
            return canvas
        image = cv2.imread(str(self.paths[self.index]))
        if image is None:
            cv2.putText(canvas, f"Failed to load {self.paths[self.index].name}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 80, 200), 2)
            return canvas
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
        cv2.putText(canvas, f"{self.paths[self.index].name} | {len(self.paths)} files | x{self.zoom:.1f}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 220, 220), 2)
        return canvas
