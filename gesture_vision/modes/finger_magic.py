"""Finger magic visual effects mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction, finger_xy


class FingerMagicMode(BaseMode):
    """Laser, magic circle, energy ball, and lightning visuals."""

    name = "finger_magic"
    shortcut = "F8"

    def __init__(self) -> None:
        """Initialize selected spell effect."""

        self.effect = "laser"

    def next_effect(self) -> None:
        """Cycle magic effect style."""

        effects = ["laser", "circle", "energy", "lightning"]
        self.effect = effects[(effects.index(self.effect) + 1) % len(effects)]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Draw active magic effect using index fingertip anchor."""

        import cv2  # type: ignore

        pt = finger_xy(landmarks, frame.shape)
        h, w = frame.shape[:2]
        if pt is not None:
            if self.effect == "laser":
                cv2.line(frame, pt, (w // 2, h // 2), (0, 0, 255), 3)
            elif self.effect == "circle":
                cv2.circle(frame, pt, 48, (255, 0, 255), 2)
            elif self.effect == "energy":
                cv2.circle(frame, pt, 26, (255, 255, 0), -1)
            else:
                cv2.polylines(frame, [
                    __import__("numpy").array([[pt[0], pt[1]], [pt[0] + 10, pt[1] + 20], [pt[0] - 8, pt[1] + 36], [pt[0] + 16, pt[1] + 56]])
                ], False, (255, 255, 255), 2)
        draw_instruction(frame, "F8", "finger_magic", f"M next ({self.effect})")
        return frame
