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

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render floating emoji for current gesture."""

        import cv2  # type: ignore

        fingers = int(landmarks.get("fingers_up", 0))
        emoji = self.map.get(fingers, "🙂")
        h, w = frame.shape[:2]
        pos = clamp_point((w // 2, 80), frame.shape)
        cv2.putText(frame, emoji, pos, cv2.FONT_HERSHEY_SIMPLEX, 1.8, (200, 255, 255), 2)
        draw_instruction(frame, "F9", "emoji_detector", "Gesture emoji")
        return frame
