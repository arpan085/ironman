"""Virtual finger keyboard mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction, finger_xy


class FingerKeyboardMode(BaseMode):
    """Simple grid keyboard controlled by index tip."""

    name = "finger_keyboard"
    shortcut = "8"

    def __init__(self) -> None:
        """Initialize keyboard state."""

        self.typed = ""
        self.keys = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM<"]
        self.hover_key: str | None = None

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw keyboard and output typed text."""

        import cv2  # type: ignore

        draw_instruction(frame, "8", "finger_keyboard", "Hover to type | H adds H")
        cv2.putText(frame, f"Typed: {self.typed[-40:]}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 200), 2)
        pointer = finger_xy(landmarks, frame.shape)
        y = 100
        hovered_key: str | None = None
        for row in self.keys:
            x = 20
            for key in row:
                rect = (x, y, x + 42, y + 42)
                cv2.rectangle(frame, (x, y), (x + 42, y + 42), (80, 80, 80), 2)
                cv2.putText(frame, key, (x + 12, y + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1)
                if pointer is not None and rect[0] <= pointer[0] <= rect[2] and rect[1] <= pointer[1] <= rect[3]:
                    hovered_key = key
                    cv2.rectangle(frame, (x, y), (x + 42, y + 42), (120, 255, 120), 3)
                x += 46
            y += 48

        if hovered_key is None:
            self.hover_key = None
        elif hovered_key != self.hover_key:
            self.type_key(hovered_key)
            self.hover_key = hovered_key

        return frame

    def type_key(self, key: str) -> None:
        """Append key to current text buffer."""

        if key == "<":
            self.typed = self.typed[:-1]
        else:
            self.typed += key

    def on_key(self, key: int) -> bool:
        """Allow the keyboard mode to capture the H key before global help toggling."""

        if key in {ord("h"), ord("H")}:
            self.type_key("H" if key == ord("H") else "h")
            return True
        return False
