"""Virtual finger keyboard mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode


class FingerKeyboardMode(BaseMode):
    """Simple grid keyboard controlled by index tip."""

    name = "finger_keyboard"
    shortcut = "8"

    def __init__(self) -> None:
        """Initialize keyboard state."""

        self.typed = ""
        self.keys = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM<"]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw keyboard and output typed text."""

        import cv2  # type: ignore

        cv2.putText(frame, "8 Finger Keyboard", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Typed: {self.typed[-40:]}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 200), 2)
        y = 100
        for row in self.keys:
            x = 20
            for key in row:
                cv2.rectangle(frame, (x, y), (x + 42, y + 42), (80, 80, 80), 2)
                cv2.putText(frame, key, (x + 12, y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1)
                x += 46
            y += 48
        return frame

    def type_key(self, key: str) -> None:
        """Append key to current text buffer."""

        if key == "<":
            self.typed = self.typed[:-1]
        else:
            self.typed += key
