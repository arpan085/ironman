"""Virtual mouse mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from ..core.smoothing import PointFilter
from .common import finger_xy


class VirtualMouseMode(BaseMode):
    """Move cursor and issue click/scroll gestures."""

    name = "virtual_mouse"
    shortcut = "7"

    def __init__(self) -> None:
        """Initialize smoothing and interaction flags."""

        self.filter = PointFilter(alpha=0.4)
        self.drag_mode = False

    def _mouse(self) -> Any:
        """Return optional pyautogui module when available."""

        try:
            import pyautogui  # type: ignore

            return pyautogui
        except Exception:
            return None

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Move cursor with index and support click actions by finger count."""

        import cv2  # type: ignore

        pointer = finger_xy(landmarks, frame.shape)
        fingers = int(landmarks.get("fingers_up", 0))
        mouse = self._mouse()

        if pointer is not None and mouse is not None:
            h, w = frame.shape[:2]
            sx, sy = mouse.size()
            smoothed = self.filter.apply(*pointer)
            mouse.moveTo(smoothed[0] * sx / w, smoothed[1] * sy / h, duration=0)
            if fingers == 2:
                mouse.click()
            elif fingers == 3:
                mouse.rightClick()
            elif fingers == 4:
                mouse.doubleClick()
            elif fingers == 5:
                mouse.scroll(40)

        cv2.putText(frame, "7 Virtual Mouse | 2 left 3 right 4 double 5 scroll", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return frame
