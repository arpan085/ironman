"""Gesture Snake game mode."""

from __future__ import annotations

import random
from typing import Any

from ..core.base_mode import BaseMode
from .common import finger_xy


class GestureSnakeMode(BaseMode):
    """A follow-the-finger snake: move your fingertip and the snake chases it."""

    name = "gesture_snake"
    shortcut = "F11"

    def __init__(self) -> None:
        """Initialize snake state."""

        self.body: list[tuple[int, int]] = []
        self.food = [240, 240]
        self.score = 0
        self.game_over = False
        self._max_len = 12
        self._frames = 0

    def reset(self) -> None:
        """Start a fresh game."""

        self.body = []
        self.score = 0
        self.game_over = False
        self._max_len = 12
        self._place_food()

    def _place_food(self) -> None:
        """Drop an apple somewhere random on the board."""

        self.food = [random.randint(60, 580), random.randint(80, 400)]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Update the snake and render the game board."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        if not self.body:
            self.reset()

        pt = finger_xy(landmarks, frame.shape)
        if pt is not None and not self.game_over:
            head = pt
            if self.body:
                prev = self.body[0]
                if abs(head[0] - prev[0]) + abs(head[1] - prev[1]) >= 12:
                    self.body.insert(0, head)
                else:
                    self.body[0] = head
            else:
                self.body.append(head)

            if len(self.body) > self._max_len + self.score:
                self.body.pop()

            fx, fy = self.food
            if abs(head[0] - fx) < 22 and abs(head[1] - fy) < 22:
                self.score += 1
                self._place_food()

            if head[0] < 5 or head[0] > w - 5 or head[1] < 45 or head[1] > h - 5:
                self.game_over = True

            if len(self.body) > 8:
                for seg in self.body[3:]:
                    if abs(seg[0] - head[0]) < 10 and abs(seg[1] - head[1]) < 10:
                        self.game_over = True
                        break

        for i, seg in enumerate(self.body):
            intensity = 255 - min(200, i * 3)
            cv2.circle(frame, seg, 9, (intensity // 4, intensity, intensity // 2), -1)
        cv2.circle(frame, (int(self.food[0]), int(self.food[1])), 12, (60, 60, 220), -1)
        cv2.putText(frame, "F11 Gesture Snake | follow the apple, avoid walls + tail", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Score: {self.score}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (120, 255, 160), 2)
        if self.game_over:
            cv2.putText(frame, "GAME OVER - press C to restart", (w // 2 - 190, h // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (60, 60, 255), 3)
        return frame

    def clear(self) -> None:
        """Restart the game (bound to the global C key)."""

        self.reset()
