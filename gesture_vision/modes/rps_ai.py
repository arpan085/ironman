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

    def _gesture_to_move(self, fingers_up: int) -> str:
        """Map finger count to RPS gesture."""

        if fingers_up <= 1:
            return "rock"
        if fingers_up <= 3:
            return "scissors"
        return "paper"

    def play_round(self, fingers_up: int) -> None:
        """Resolve one round and update scoreboard."""

        self.player_choice = self._gesture_to_move(fingers_up)
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

        cv2.putText(frame, "4 RPS AI | ENTER play", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
        cv2.putText(frame, f"You: {self.player_choice}  AI: {self.ai_choice}", (18, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 220, 100), 2)
        cv2.putText(frame, f"Score {self.player_score} : {self.ai_score}", (18, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (80, 255, 100), 2)
        return frame
