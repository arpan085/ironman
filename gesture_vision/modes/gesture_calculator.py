"""Gesture calculator mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode


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

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render expression and result panel."""

        import cv2  # type: ignore

        cv2.putText(frame, "9 Gesture Calculator", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        cv2.putText(frame, f"Expr: {self.expression[:42]}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 220, 120), 2)
        cv2.putText(frame, f"Result: {self.result}", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 200), 2)
        return frame
