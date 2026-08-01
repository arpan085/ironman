"""Air Signature - write your signature in the air and save it as a PNG."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import cv2  # type: ignore
import numpy as np  # type: ignore

from ..core.base_mode import BaseMode
from .common import finger_xy, hands_of


class AirSignatureMode(BaseMode):
    """Index finger draws; a pinch lifts the pen; palm clears; S saves."""

    name = "air_signature"
    shortcut = "F20"

    def __init__(self, output_dir: str = "signatures") -> None:
        """Open a transparent drawing surface."""

        self.output_dir = Path(output_dir)
        self.canvas: np.ndarray | None = None
        self._last: tuple[int, int] | None = None
        self._saved = ""

    def _ensure_canvas(self, h: int, w: int) -> None:
        """Allocate the drawing layer once the frame size is known."""

        if self.canvas is None or self.canvas.shape[0] != h or self.canvas.shape[1] != w:
            self.canvas = np.zeros((h, w, 4), dtype=np.uint8)

    def _pen_down(self, landmarks: dict[str, Any]) -> bool:
        """Return True when the index finger is extended (drawing)."""

        if not hands_of(landmarks):
            return False
        points = hands_of(landmarks)[0]
        return points[8].y < points[6].y

    def clear(self) -> None:
        """Erase the canvas and reset the stroke."""

        if self.canvas is not None:
            self.canvas[:] = 0
        self._last = None

    def on_key(self, key: int, char: str) -> bool:
        """Save the signature to a PNG on S."""

        if char == "s" and self.canvas is not None and self.canvas.any():
            self._save()
            return True
        return False

    def _save(self) -> None:
        """Write the transparent signature to a timestamped PNG."""

        from datetime import datetime

        try:
            self.output_dir.mkdir(parents=True, exist_ok=True)
            path = self.output_dir / f"signature_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            cv2.imwrite(str(path), self.canvas)
            self._saved = str(path)
        except Exception:
            self._saved = ""

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Track the fingertip and composite the signature over the video."""

        h, w = frame.shape[:2]
        self._ensure_canvas(h, w)
        pt = finger_xy(landmarks, frame.shape)
        drawing = pt is not None and self._pen_down(landmarks)

        if drawing and self.canvas is not None:
            if self._last is not None:
                cv2.line(self.canvas, self._last, pt, (255, 80, 200, 255), 6, cv2.LINE_AA)
            cv2.circle(self.canvas, pt, 3, (255, 80, 200, 255), -1)
            self._last = pt
        else:
            self._last = None

        rgb = self.canvas[:, :, :3]
        mask = self.canvas[:, :, 3:4] // 255
        frame[:] = frame * (1 - mask) + rgb * mask

        cv2.putText(frame, "F20 Air Signature | index draws, pinch lifts, S saves, C clears", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if self._saved:
            cv2.putText(frame, f"Saved: {Path(self._saved).name}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 160), 2)
        return frame
