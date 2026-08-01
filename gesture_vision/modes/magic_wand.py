"""Magic Wand - glowing particle trail + pinch-triggered spark bursts."""

from __future__ import annotations

import random
from typing import Any

from ..core.base_mode import BaseMode
from .common import finger_xy


class MagicWandMode(BaseMode):
    """Fingertip spawns a colorful particle trail; a pinch fires a burst."""

    name = "magic_wand"
    shortcut = "F17"

    def __init__(self) -> None:
        """Start with an empty particle system."""

        self.particles: list[dict[str, float]] = []
        self._pinched = False
        self._hue = 0.0

    def _spawn(self, x: float, y: float, burst: bool) -> None:
        """Emit one or many particles at a point."""

        count = 12 if burst else 3
        for _ in range(count):
            angle = random.uniform(0, 6.283)
            speed = random.uniform(1.0, 5.0) if burst else random.uniform(0.5, 2.0)
            self.particles.append(
                {
                    "x": float(x),
                    "y": float(y),
                    "vx": float(speed * 0.8) * random.choice((-1, 1)) * abs(random.uniform(0.2, 1)),
                    "vy": random.uniform(-2.2, -0.2) if burst else random.uniform(-1.2, -0.2),
                    "vx2": float(angle),
                    "life": random.uniform(20, 45),
                    "max": 45.0,
                }
            )

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Advance the particle system and render it on the frame."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        hands = landmarks.get("hands") or []
        pinching = False
        if hands:
            a = hands[0][8]
            b = hands[0][4]
            pinch_px = ((a.x - b.x) ** 2 + (a.y - b.y) ** 2) ** 0.5 * max(w, h)
            pinching = pinch_px < 45

        pt = finger_xy(landmarks, frame.shape)
        if pt is not None:
            self._spawn(pt[0], pt[1], burst=pinching and not self._pinched)
        self._pinched = pinching

        self._hue = (self._hue + 0.4) % 360
        hsv = frame.copy()
        cv2.cvtColor(frame, cv2.COLOR_BGR2HSV, dst=hsv)
        for p in self.particles:
            p["x"] += p["vx2"] * 0.2
            p["y"] += p["vy"]
            p["vy"] += 0.12
            p["life"] -= 1
            alpha = max(0.0, p["life"] / p["max"])
            hue = int((self._hue + (p["x"] * 0.5)) % 360)
            cv2.circle(hsv, (int(p["x"]), int(p["y"])), max(1, int(7 * alpha)), (hue, 255, 255), -1)
        cv2.cvtColor(hsv, cv2.COLOR_HSV2BGR, dst=frame)
        self.particles = [p for p in self.particles if p["life"] > 0 and 0 <= p["y"] < h + 40]

        cv2.putText(frame, "F17 Magic Wand | move to leave a trail, pinch to burst", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if pt is not None:
            cv2.circle(frame, pt, 5, (255, 255, 255), -1)
        return frame
