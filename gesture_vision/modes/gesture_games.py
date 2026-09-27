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
        self.score = 0
        self.points = 0
        self.fruit: list[list[float]] = []
        self.balloons: list[list[float]] = []
        self.falling = [320, 0]
        self.paddle_x = 320
        self.walls: list[tuple[int, int, int, int]] = []
        self.goal = (560, 400)
        self.prev_point: tuple[int, int] | None = None
        self.ball_pos: tuple[int, int] | None = None
        self.seed_fruit()

    def next_game(self) -> None:
        """Cycle through game variants."""

        modes = ["fruit", "balloon", "catch", "maze"]
        self.mode = modes[(modes.index(self.mode) + 1) % len(modes)]
        self.score = 0
        if self.mode == "fruit":
            self.seed_fruit()
        elif self.mode == "balloon":
            self.seed_balloons()
        elif self.mode == "maze":
            self.seed_maze()

    def seed_fruit(self) -> None:
        """Create an initial fruit field."""

        self.fruit = [[random.randint(80, 560), random.randint(80, 360), 22, random.choice([-1, 1]), random.choice([-1, 1])] for _ in range(6)]

    def seed_balloons(self) -> None:
        """Create an initial balloon field."""

        self.balloons = [[random.randint(80, 560), random.randint(60, 320), 28] for _ in range(7)]

    def seed_maze(self) -> None:
        """Generate a simple set of maze walls and a goal."""

        self.walls = [(260, 0, 280, 160), (80, 200, 100, 380), (440, 120, 460, 300), (280, 320, 300, 480), (0, 120, 160, 140)]
        self.goal = (560, 400)
        self.ball_pos = None

    def _slice_line_hits(self, ax: int, ay: int, bx: int, by: int, cx: float, cy: float, r: float) -> bool:
        """Return True when a finger swipe segment hits a target circle."""

        import math

        dx, dy = bx - ax, by - ay
        seg_len2 = dx * dx + dy * dy
        if seg_len2 == 0:
            return math.hypot(cx - ax, cy - ay) <= r
        t = max(0.0, min(1.0, ((cx - ax) * dx + (cy - ay) * dy) / seg_len2))
        px, py = ax + t * dx, ay + t * dy
        return math.hypot(cx - px, cy - py) <= r

    def _update_fruit(self, frame: Any, pt: tuple[int, int] | None) -> None:
        """Move fruits and slice them with a finger swipe."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        for f in self.fruit:
            f[0] += f[3] * 2
            f[1] += f[4] * 2
            if f[0] < 30 or f[0] > w - 30:
                f[3] *= -1
            if f[1] < 60 or f[1] > h - 30:
                f[4] *= -1
            cv2.circle(frame, (int(f[0]), int(f[1])), int(f[2]), (60, 140, 255), -1)
        if self.prev_point is not None and pt is not None:
            for f in self.fruit:
                if self._slice_line_hits(self.prev_point[0], self.prev_point[1], pt[0], pt[1], f[0], f[1], f[2]):
                    self.score += 1
                    self.fruit.remove(f)
                    self.fruit.append([random.randint(80, w - 80), random.randint(80, h - 80), 22, random.choice([-1, 1]), random.choice([-1, 1])])
                    break

    def _update_balloon(self, frame: Any, pt: tuple[int, int] | None) -> None:
        """Pop balloons when touched."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        for b in self.balloons:
            cv2.circle(frame, (int(b[0]), int(b[1])), int(b[2]), (80, 220, 120), 2)
        if pt is not None:
            for b in self.balloons:
                if self._slice_line_hits(pt[0], pt[1], pt[0], pt[1], b[0], b[1], b[2] + 6):
                    self.score += 1
                    self.balloons.remove(b)
                    self.balloons.append([random.randint(80, w - 80), random.randint(60, h - 200), 28])
                    break

    def _update_catch(self, frame: Any, pt: tuple[int, int] | None) -> None:
        """Catch a falling object with a finger-controlled paddle."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        if pt is not None:
            self.paddle_x = pt[0]
        self.falling[1] += 5
        if self.falling[1] > h - 40:
            self.falling = [random.randint(60, w - 60), 0]
        cv2.circle(frame, (int(self.falling[0]), int(self.falling[1])), 16, (255, 200, 60), -1)
        px = int(self.paddle_x)
        cv2.rectangle(frame, (px - 50, h - 40), (px + 50, h - 20), (100, 220, 255), -1)
        if abs(self.falling[0] - px) < 55 and self.falling[1] >= h - 55:
            self.score += 1
            self.falling = [random.randint(60, w - 60), 0]

    def _update_maze(self, frame: Any, pt: tuple[int, int] | None) -> None:
        """Navigate a ball through walls to reach the goal."""

        import cv2  # type: ignore

        if self.ball_pos is None and pt is not None:
            self.ball_pos = pt
        if pt is not None:
            candidate = pt
            blocked = False
            for (wx, wy, wx2, wy2) in self.walls:
                if wx <= candidate[0] <= wx2 and wy <= candidate[1] <= wy2:
                    blocked = True
                    break
            if not blocked:
                self.ball_pos = candidate
        for (wx, wy, wx2, wy2) in self.walls:
            cv2.rectangle(frame, (wx, wy), (wx2, wy2), (120, 120, 140), -1)
        gx, gy = self.goal
        cv2.circle(frame, (gx, gy), 18, (80, 255, 120), -1)
        cv2.putText(frame, "GOAL", (gx - 26, gy - 24), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (80, 255, 120), 1)
        if self.ball_pos is not None:
            bx, by = self.ball_pos
            cv2.circle(frame, (bx, by), 12, (255, 220, 60), -1)
            if abs(bx - gx) < 20 and abs(by - gy) < 20:
                self.score += 1
                self.seed_maze()
                self.ball_pos = (30, 30)

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Run active mini-game and draw HUD."""

        import cv2  # type: ignore

        pt = finger_xy(landmarks, frame.shape)
        if self.mode == "fruit":
            self._update_fruit(frame, pt)
        elif self.mode == "balloon":
            self._update_balloon(frame, pt)
        elif self.mode == "catch":
            self._update_catch(frame, pt)
        else:
            self._update_maze(frame, pt)
        self.prev_point = pt

        draw_instruction(frame, "F7", "gesture_games", f"G next ({self.mode})")
        cv2.putText(frame, f"Score: {self.score}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (100, 255, 120), 2)
        return frame
