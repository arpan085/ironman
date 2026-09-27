"""Virtual mouse mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from ..core.smoothing import PointFilter
from ..core.system_controls import is_pinch
from .common import draw_instruction, finger_xy


class VirtualMouseMode(BaseMode):
    """Move cursor and issue click/scroll gestures."""

    name = "virtual_mouse"
    shortcut = "7"

    def __init__(self) -> None:
        """Initialize smoothing and interaction flags."""

        self.filter = PointFilter(alpha=0.4)
        self._last_fingers = 0
        self._cooldown = 0
        self.drag_mode = False
        self.active = False

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
        thumb = landmarks.get("thumb_tip")
        index = landmarks.get("index_tip")
        activated = is_pinch(thumb, index) and fingers <= 2

        if pointer is not None and mouse is not None and activated:
            self.active = True
            h, w = frame.shape[:2]
            sx, sy = mouse.size()
            smoothed = self.filter.apply(*pointer)
            mouse.moveTo(smoothed[0] * sx / w, smoothed[1] * sy / h, duration=0)

            if self._cooldown > 0:
                self._cooldown -= 1
            elif fingers != self._last_fingers and fingers >= 2:
                if fingers == 2:
                    mouse.click()
                elif fingers == 3:
                    mouse.rightClick()
                elif fingers == 4:
                    mouse.doubleClick()
                elif fingers == 5:
                    mouse.scroll(40)
                self._cooldown = 8
        else:
            self.active = False

        self._last_fingers = fingers
        draw_instruction(frame, "7", "virtual_mouse", "Pinch to move | 2 left | 3 right | 4 double | 5 scroll")
        return frame
