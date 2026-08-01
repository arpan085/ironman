"""Gesture Macro Pad - pick an action with finger count, confirm with a fist."""

from __future__ import annotations

import os
import subprocess
from typing import Any

from ..core.base_mode import BaseMode
from .common import hand_count, hands_of

ACTIONS: dict[int, tuple[str, str]] = {
    1: ("Notepad", "notepad"),
    2: ("Calculator", "calc"),
    3: ("Browser", "start https://www.google.com"),
    4: ("Paint", "mspaint"),
    5: ("File Explorer", "explorer"),
}


class MacroPadMode(BaseMode):
    """Select one of five launchers and fire it with a closed-fist confirm."""

    name = "macro_pad"
    shortcut = "F19"

    def __init__(self) -> None:
        """Reset slot and hold counters."""

        self.slot: int | None = None
        self._hold = 0
        self._prev = 0
        self._armed = False
        self._triggered = ""

    def on_key(self, key: int, char: str) -> bool:
        """Allow launching the currently selected slot with the Enter key."""

        if char in "12345":
            self.slot = int(char)
            self._armed = True
            return True
        if char in ("\r", "\n") and self.slot:
            self._fire(self.slot)
            return True
        return False

    def _fire(self, slot: int) -> None:
        """Launch the mapped action (best effort, never crashes)."""

        if slot not in ACTIONS:
            return
        name, command = ACTIONS[slot]
        self._triggered = name
        try:
            if command.startswith("start "):
                subprocess.Popen(command, shell=True)
            elif os.name == "nt":
                os.startfile(command)  # type: ignore[attr-defined]
            else:
                subprocess.Popen([command])
        except Exception:
            pass

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect select/confirm gestures and render the macro grid."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        counts = [c for c in (landmarks.get("fingers") or [])]

        if len(counts) >= 2:
            selector, confirmer = counts
            if selector in (1, 2, 3, 4, 5) and confirmer == 0:
                self.slot = selector
                self._hold += 1
                if self._hold >= 3 and self.slot:
                    self._fire(self.slot)
                    self._hold = 0
            elif selector != 0:
                self._hold = 0
        elif len(counts) == 1:
            current = counts[0]
            if current != self._prev:
                self._hold = 0
                self._prev = current
            if current in (1, 2, 3, 4, 5):
                self.slot = current
                self._armed = True
                self._hold = 0
            elif current == 0 and self._armed and self.slot:
                self._hold += 1
                if self._hold >= 3:
                    self._fire(self.slot)
                    self._armed = False
                    self._hold = 0

        cv2.putText(frame, "F19 Macro Pad | 1-5 fingers select, fist (or Enter) fires", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        for i, (slot, (name, _)) in enumerate(ACTIONS.items()):
            cx = int(w * 0.08) + i * int(w * 0.18)
            cy = int(h * 0.55)
            active = slot == self.slot
            cv2.circle(frame, (cx, cy), 52, (80, 255, 120) if active else (70, 70, 90), -1)
            cv2.putText(frame, str(slot), (cx - 14, cy + 16), cv2.FONT_HERSHEY_SIMPLEX, 1.2, (0, 0, 0), 4)
            cv2.putText(frame, name, (cx - 52, cy + 55), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255) if active else (200, 200, 200), 2)

        if self._triggered:
            cv2.putText(frame, f"Launched: {self._triggered}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (120, 255, 160), 2)
        if not hands_of(landmarks):
            cv2.putText(frame, "Show 1-5 fingers to select, make a fist to launch", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 2)
        return frame
