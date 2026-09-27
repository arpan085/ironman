"""Emoji detector mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import clamp_point, draw_instruction


class EmojiDetectorMode(BaseMode):
    """Maps hand poses to emoji overlays."""

    name = "emoji_detector"
    shortcut = "F9"

    def __init__(self) -> None:
        """Initialize emoji lookup by finger count."""

        self.map = {0: "😴", 1: "☝️", 2: "✌️", 3: "🤟", 4: "🖖", 5: "🖐️"}
        self._font = None

    def _load_font(self) -> Any:
        """Load a unicode-capable font for emoji rendering."""

        if self._font is not None:
            return self._font
        try:
            from PIL import ImageFont

            for name in ("seguiemj.ttf", "seguisym.ttf", "arial.ttf", "DejaVuSans.ttf"):
                try:
                    self._font = ImageFont.truetype(name, 72)
                    return self._font
                except OSError:
                    continue
        except Exception:
            self._font = None
        return None

    def _draw_emoji(self, frame: Any, emoji: str, x: int, y: int) -> None:
        """Blit a large emoji onto the frame with alpha blending."""

        import numpy as np

        try:
            from PIL import Image, ImageDraw

            font = self._load_font()
            if font is None:
                return
            img = Image.new("RGBA", (160, 160), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            draw.text((10, 10), emoji, font=font, embedded_color=True, fill=(255, 255, 255, 255))
            rgba = np.array(img)
            bgr = rgba[:, :, [2, 1, 0]]
            alpha = rgba[:, :, 3] / 255.0
            hh, ww = frame.shape[:2]
            overlay = bgr[: min(alpha.shape[0], hh - y), : min(alpha.shape[1], ww - x)]
            mask = alpha[: overlay.shape[0], : overlay.shape[1], None]
            if overlay.shape[0] > 0 and overlay.shape[1] > 0:
                frame[y : y + overlay.shape[0], x : x + overlay.shape[1]] = (
                    frame[y : y + overlay.shape[0], x : x + overlay.shape[1]] * (1 - mask) + overlay * mask
                ).astype(frame.dtype)
        except Exception:
            pass

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render floating emoji for current gesture."""

        import cv2  # type: ignore

        fingers = int(landmarks.get("fingers_up", 0))
        emoji = self.map.get(fingers, "🙂")
        self._draw_emoji(frame, emoji, frame.shape[1] - 180, 60)
        label = {0: "Sleep", 1: "One", 2: "Peace", 3: "Love", 4: "Vulcan", 5: "High Five"}.get(fingers, "Neutral")
        draw_instruction(frame, "F9", "emoji_detector", f"{fingers} fingers: {label}")
        return frame
