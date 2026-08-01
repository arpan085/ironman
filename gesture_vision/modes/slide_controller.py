"""Slide Controller mode - swipe left/right to advance presentation slides."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import finger_xy


class SlideControllerMode(BaseMode):
    """Presents a virtual slide deck; optionally drives PowerPoint/PDF."""

    name = "slide_controller"
    shortcut = "F14"

    def __init__(self) -> None:
        """Start on slide one with no external control."""

        self.slide = 1
        self.total = 12
        self.control_ppt = False
        self._last_x: int | None = None
        self._cooldown = 0
        self._last_action = ""

    def on_key(self, key: int, char: str) -> bool:
        """Toggle external PPT control with the P key."""

        if char == "p":
            self.control_ppt = not self.control_ppt
            return True
        return False

    def _advance(self, direction: int) -> None:
        """Move one slide and optionally press the matching keyboard key."""

        self.slide += direction
        if self.slide < 1:
            self.slide = 1
        if self.slide > self.total:
            self.slide = self.total
        self._cooldown = 15
        self._last_action = "next" if direction > 0 else "prev"
        if self.control_ppt:
            try:
                import pyautogui  # type: ignore

                pyautogui.press("right" if direction > 0 else "left")
            except Exception:
                pass

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect horizontal swipes and render the deck preview."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        if self._cooldown > 0:
            self._cooldown -= 1

        pt = finger_xy(landmarks, frame.shape)
        if pt is not None:
            if self._last_x is not None and self._cooldown <= 0:
                dx = pt[0] - self._last_x
                if abs(dx) > max(70, w * 0.12):
                    self._advance(1 if dx > 0 else -1)
            self._last_x = pt[0]
        else:
            self._last_x = None

        cv2.putText(frame, "F14 Slide Controller | swipe finger to change slide", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Press P to toggle PPT control: {'ON' if self.control_ppt else 'OFF'}", (18, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 120) if self.control_ppt else (200, 200, 200), 2)

        cv2.rectangle(frame, (w // 2 - 220, h // 2 - 140), (w // 2 + 220, h // 2 + 140), (70, 70, 90), 3)
        cv2.putText(frame, str(self.slide), (w // 2 - 40, h // 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, 1.6, (255, 255, 255), 3)
        cv2.putText(frame, f"Slide {self.slide} of {self.total}", (w // 2 - 80, h // 2 + 70), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (180, 180, 180), 2)

        arrow_color = (80, 255, 140) if self._last_action == "next" else (200, 200, 200)
        cv2.arrowedLine(frame, (w // 2 - 150, h // 2), (w // 2 - 50, h // 2), arrow_color, 12, tipLength=0.6)
        arrow_color = (255, 140, 80) if self._last_action == "prev" else (200, 200, 200)
        cv2.arrowedLine(frame, (w // 2 + 150, h // 2), (w // 2 + 50, h // 2), arrow_color, 12, tipLength=0.6)
        return frame
