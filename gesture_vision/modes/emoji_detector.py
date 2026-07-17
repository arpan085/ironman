"""Emoji detector mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode


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
        cv2.putText(frame, f"F9 Emoji Detector: {emoji}", (18, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (200, 255, 255), 2)
        return frame
