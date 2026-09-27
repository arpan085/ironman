"""Gesture calculator mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction


class GestureCalculatorMode(BaseMode):
    """Air-digit inspired calculator backed by safe eval."""

    name = "gesture_calculator"
    shortcut = "9"

    def __init__(self) -> None:
        """Initialize expression state."""

        self.expression = ""
        self.result = ""

    def evaluate(self) -> None:
        """Evaluate expression with strict character whitelist."""

        allowed = set("0123456789+-*/(). ")
        if not self.expression or any(ch not in allowed for ch in self.expression):
            self.result = "Invalid"
            return
        try:
            self.result = str(eval(self.expression, {"__builtins__": {}}, {}))
        except Exception:
            self.result = "Error"

    def clear(self) -> None:
        """Reset the current expression."""

        self.expression = ""
        self.result = ""

    def backspace(self) -> None:
        """Remove the last character of the expression."""

        self.expression = self.expression[:-1]

    def on_key(self, key: int, char: str) -> bool:
        """Consume digits, operators, and action keys while active."""

        if key == 8:
            self.backspace()
            return True
        if key in (ord("="), ord("\r")):
            self.evaluate()
            return True
        if char in "0123456789+-*/(). ":
            self.expression += char
            self.expression = self.expression[:64]
            return True
        return False

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render expression and result panel."""

        import cv2  # type: ignore

        draw_instruction(frame, "9", "gesture_calculator", "Type digits/ops, = or ENTER to eval")
        cv2.putText(frame, f"Expr: {self.expression[:42]}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 220, 120), 2)
        cv2.putText(frame, f"Result: {self.result}", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 200), 2)
        return frame
