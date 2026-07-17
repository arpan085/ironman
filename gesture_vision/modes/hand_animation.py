"""Hand animation effects mode."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import finger_xy


class HandAnimationEffectsMode(BaseMode):
    """Applies particle-style visual effects around fingertips."""

    name = "hand_animation_effects"
    shortcut = "F6"

    def __init__(self) -> None:
        """Initialize effect selector."""

        self.effect = "fire"

    def next_effect(self) -> None:
        """Cycle animation effect type."""

        effects = ["fire", "electric", "smoke", "neon", "sparkles", "ripple"]
        self.effect = effects[(effects.index(self.effect) + 1) % len(effects)]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render selected effect around index fingertip."""

        import cv2  # type: ignore

        pt = finger_xy(landmarks, frame.shape)
        if pt is not None:
            color_map = {
                "fire": (30, 120, 255),
                "electric": (255, 255, 20),
                "smoke": (180, 180, 180),
                "neon": (255, 0, 255),
                "sparkles": (255, 255, 255),
                "ripple": (255, 200, 0),
            }
            color = color_map[self.effect]
            for radius in range(8, 34, 6):
                cv2.circle(frame, pt, radius, color, 1)
        cv2.putText(frame, f"F6 Hand FX ({self.effect}) | X next", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return frame
