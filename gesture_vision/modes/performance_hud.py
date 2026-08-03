"""Performance HUD mode for FPS/CPU/resolution."""

from __future__ import annotations

import time
from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction


class PerformanceHUDMode(BaseMode):
    """Shows live FPS, CPU usage, and camera resolution."""

    name = "performance_hud"
    shortcut = "F10"

    def __init__(self) -> None:
        """Initialize timing state for FPS calculation."""

        self.prev = time.perf_counter()
        self.fps = 0.0

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Compute performance metrics and draw overlays."""

        import cv2  # type: ignore

        now = time.perf_counter()
        dt = max(1e-6, now - self.prev)
        self.prev = now
        self.fps = 1.0 / dt
        cpu = float(context.get("cpu_load", 0.0))
        temperature_c = float(context.get("temperature_c", 0.0))
        battery_percent = context.get("battery_percent")
        h, w = frame.shape[:2]
        draw_instruction(frame, "F10", "performance_hud", "FPS CPU temp battery")
        cv2.putText(frame, f"FPS: {self.fps:.1f}", (18, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (80, 255, 120), 2)
        cv2.putText(frame, f"CPU(load1): {cpu:.2f}", (18, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 230, 255), 2)
        cv2.putText(frame, f"Temp(est): {temperature_c:.1f} C", (18, 114), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 208, 120), 2)
        batt_label = "--" if battery_percent is None else f"{battery_percent}%"
        cv2.putText(frame, f"Battery: {batt_label}", (18, 142), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 245, 180), 2)
        cv2.putText(frame, f"Res: {w}x{h}", (18, 170), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 2)
        return frame
