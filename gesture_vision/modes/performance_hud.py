"""Performance HUD mode for FPS/CPU/RAM/resolution with Stark styling."""

from __future__ import annotations

import time
from typing import Any
import numpy as np

from ..core.base_mode import BaseMode
from .common import draw_hud_panel, draw_instruction


class PerformanceHUDMode(BaseMode):
    """Shows live FPS, CPU usage, RAM consumption, and camera resolution."""

    name = "performance_hud"
    shortcut = "F10"

    def __init__(self) -> None:
        """Initialize timing state for FPS calculation."""

        self.prev = time.perf_counter()
        self.fps = 0.0
        self.cpu = 0.0
        self.ram = 0.0
        self._psutil = None
        try:
            import psutil  # type: ignore

            self._psutil = psutil
        except Exception:
            self._psutil = None

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Compute performance metrics and draw Stark-styled overlays."""

        import cv2  # type: ignore

        now = time.perf_counter()
        dt = max(1e-6, now - self.prev)
        self.prev = now
        instant_fps = 1.0 / dt
        self.fps = self.fps * 0.9 + instant_fps * 0.1 if self.fps else instant_fps

        if self._psutil is not None:
            try:
                self.cpu = float(self._psutil.cpu_percent(interval=None) or 0.0)
                self.ram = float(self._psutil.virtual_memory().percent or 0.0)
            except Exception:
                self.cpu = float(context.get("cpu_load", 0.0))
                self.ram = 0.0
        else:
            self.cpu = float(context.get("cpu_load", 0.0))

        temperature_c = float(context.get("temperature_c", 0.0))
        battery_percent = context.get("battery_percent")
        h, w = frame.shape[:2]
        target = int(context.get("fps_target", 0) or 0)

        draw_instruction(frame, "F10", "performance_hud", "System telemetry")

        # Draw HUD Panel
        panel_h = 200 if (temperature_c or battery_percent is not None) else 165
        draw_hud_panel(frame, 18, 56, 320, panel_h, title="PERFORMANCE TELEMETRY")

        fps_text = f"FPS: {self.fps:.1f} / {target} TARGET" if target else f"FPS: {self.fps:.1f}"
        cpu_text = f"CPU LOAD: {self.cpu:.1f}%"
        ram_text = f"RAM USAGE: {self.ram:.1f}%"
        res_text = f"RESOLUTION: {w}x{h}"

        c_cyan = (0, 229, 255)
        c_green = (100, 255, 140)

        cv2.putText(frame, fps_text, (28, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c_green, 1, cv2.LINE_AA)
        cv2.putText(frame, cpu_text, (28, 108), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, ram_text, (28, 130), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, res_text, (28, 152), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (220, 220, 220), 1, cv2.LINE_AA)

        # FPS gauge bar
        max_bar = 180
        bar_ratio = min(1.0, max(0.0, self.fps / max(1, target or 30)))
        fill_w = int(max_bar * bar_ratio)
        cv2.rectangle(frame, (110, 170), (110 + max_bar, 184), (0, 80, 100), 1)
        cv2.rectangle(frame, (110, 170), (110 + fill_w, 184), c_green, -1)
        cv2.putText(frame, "FPS GAUGE:", (28, 180), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (180, 180, 180), 1, cv2.LINE_AA)

        if temperature_c or battery_percent is not None:
            batt_label = "--" if battery_percent is None else f"{battery_percent}%"
            extra_text = f"TEMP: {temperature_c:.1f}C | BATT: {batt_label}"
            cv2.putText(frame, extra_text, (28, 202), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 208, 120), 1, cv2.LINE_AA)

        return frame
