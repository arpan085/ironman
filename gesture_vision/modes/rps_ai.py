"""Rock Paper Scissors AI mode."""

from __future__ import annotations

import random
from typing import Any

from ..core.base_mode import BaseMode


class RockPaperScissorsMode(BaseMode):
    """Play RPS against computer with countdown and score."""

    name = "rock_paper_scissors"
    shortcut = "4"

    def __init__(self) -> None:
        """Initialize score and round state."""

        self.player_score = 0
        self.ai_score = 0
        self.player_choice = "-"
        self.ai_choice = "-"
        self.last_fingers = 0

    def _gesture_to_move(self, fingers_up: int) -> str:
        """Map finger count to RPS gesture."""

        if fingers_up <= 1:
            return "rock"
        if fingers_up <= 3:
            return "scissors"
        return "paper"

    def play_round(self, fingers_up: int | None = None) -> None:
        """Resolve one round and update scoreboard."""

        if fingers_up is not None:
            self.last_fingers = fingers_up
        self.player_choice = self._gesture_to_move(self.last_fingers)
        self.ai_choice = random.choice(["rock", "paper", "scissors"])
        rules = {
            ("rock", "scissors"),
            ("scissors", "paper"),
            ("paper", "rock"),
        }
        if self.player_choice == self.ai_choice:
            return
        if (self.player_choice, self.ai_choice) in rules:
            self.player_score += 1
        else:
            self.ai_score += 1

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render RPS game UI."""

        import cv2  # type: ignore

        self.last_fingers = int(landmarks.get("fingers_up", 0))
        hint = f"Fingers: {self.last_fingers} | ENTER play"
        cv2.putText(frame, "4 RPS AI", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        cv2.putText(frame, hint, (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 255), 1)
        cv2.putText(frame, f"You: {self.player_choice}  AI: {self.ai_choice}", (18, 98), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 220, 100), 2)
        cv2.putText(frame, f"Score {self.player_score} : {self.ai_score}", (18, 132), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 255, 100), 2)
        return frame
