"""Virtual finger keyboard mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import finger_xy


class FingerKeyboardMode(BaseMode):
    """Grid keyboard typed by hovering the index fingertip over a key."""

    name = "finger_keyboard"
    shortcut = "8"

    def __init__(self) -> None:
        """Initialize keyboard state."""

        self.typed = ""
        self.keys = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM<"]
        self.layout: list[tuple[tuple[int, int, int, int], str]] = []
        self._cooldown = 0
        self._highlight = None

    def _build_layout(self, height: int) -> list[tuple[tuple[int, int, int, int], str]]:
        """Return key rectangles for the current frame height."""

        if self.layout:
            return self.layout
        y = 100
        layout = []
        for row in self.keys:
            x = 20
            for key in row:
                layout.append(((x, y, x + 42, y + 42), key))
                x += 46
            y += 48
        return layout

    def type_key(self, key: str) -> None:
        """Append key to current text buffer."""

        if key == "<":
            self.typed = self.typed[:-1]
        else:
            self.typed += key
            if len(self.typed) > 80:
                self.typed = self.typed[-80:]

    def clear(self) -> None:
        """Clear the typed text."""

        self.typed = ""

    def on_key(self, key: int, char: str) -> bool:
        """Support backspace, clear, and physical keys from the keyboard."""

        if key == 8:
            self.typed = self.typed[:-1]
            return True
        if key == ord("c"):
            self.clear()
            return True
        if char and len(char) == 1 and (char.isalnum() or char in " .,!?-"):
            self.type_key(char.upper())
            return True
        return False

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw keyboard and output typed text."""

        import cv2  # type: ignore

        self.layout = self._build_layout(frame.shape[0])
        point = finger_xy(landmarks, frame.shape)

        if self._cooldown > 0:
            self._cooldown -= 1

        self._highlight = None
        if point is not None:
            for (x1, y1, x2, y2), key in self.layout:
                if x1 <= point[0] <= x2 and y1 <= point[1] <= y2:
                    self._highlight = (x1, y1, x2, y2)
                    if self._cooldown == 0:
                        self.type_key(key)
                        self._cooldown = 18
                    break

        cv2.putText(frame, "8 Finger Keyboard | hover to type", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Typed: {self.typed[-40:]}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 200), 2)
        for (x1, y1, x2, y2), key in self.layout:
            if self._highlight == (x1, y1, x2, y2):
                cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 220, 255), -1)
                cv2.putText(frame, key, (x1 + 12, y1 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            else:
                cv2.rectangle(frame, (x1, y1), (x2, y2), (80, 80, 80), 2)
                cv2.putText(frame, key, (x1 + 12, y1 + 28), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 1)
        if point is not None:
            cv2.circle(frame, point, 8, (0, 220, 255), 2)
        return frame
