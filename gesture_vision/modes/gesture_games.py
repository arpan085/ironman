"""Gesture game collection mode."""

from __future__ import annotations

import random
from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction, finger_xy


class GestureGamesMode(BaseMode):
    """Mini games: fruit slice, balloon pop, catcher, maze."""

    name = "gesture_games"
    shortcut = "F7"

    def __init__(self) -> None:
        """Initialize game objects and score."""

        self.mode = "fruit"
        self.target = [300, 240]
        self.score = 0

    def next_game(self) -> None:
        """Cycle through game variants."""

        modes = ["fruit", "balloon", "catch", "maze"]
        self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Run active mini-game and draw HUD."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        pt = finger_xy(landmarks, frame.shape)
        tx, ty = self.target
        cv2.circle(frame, (tx, ty), 35, (60, 140, 255), -1)

        if pt is not None:
            cv2.circle(frame, pt, 14, (255, 255, 255), 2)
            if abs(pt[0] - tx) < 35 and abs(pt[1] - ty) < 35:
                self.score += 1
                self.target = [random.randint(60, w - 60), random.randint(80, h - 60)]

        draw_instruction(frame, "F7", "gesture_games", f"G next ({self.mode})")
        cv2.putText(frame, f"Score: {self.score}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 120), 2)
        return frame
