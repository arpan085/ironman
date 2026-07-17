"""Smoothing helpers used by drawing and mouse modes."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class PointFilter:
    """Exponential moving average filter for points."""

    alpha: float = 0.35
    x: float = 0.0
    y: float = 0.0
    initialized: bool = False

    def apply(self, x: float, y: float) -> tuple[int, int]:
        """Return smoothed coordinates."""

        if not self.initialized:
            self.x, self.y = x, y
            self.initialized = True
        else:
            self.x = (1.0 - self.alpha) * self.x + self.alpha * x
            self.y = (1.0 - self.alpha) * self.y + self.alpha * y
        return int(self.x), int(self.y)
