"""Performance HUD mode for FPS/CPU/resolution."""

from __future__ import annotations

import time
from typing import Any

from ..core.base_mode import BaseMode


class PerformanceHUDMode(BaseMode):
    """Shows live FPS, CPU usage, and camera resolution."""

    name = "performance_hud"
    shortcut = "F10"

    def __init__(self) -> None:
        """Initialize timing state for FPS calculation."""

        self.prev = time.perf_counter()
        self.fps = 0.0
        self.cpu = 0.0
        self._psutil = None
        try:
            import psutil  # type: ignore

            self._psutil = psutil
        except Exception:
            self._psutil = None

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Compute performance metrics and draw overlays."""

        import cv2  # type: ignore

        now = time.perf_counter()
        dt = max(1e-6, now - self.prev)
        self.prev = now
        instant_fps = 1.0 / dt
        self.fps = self.fps * 0.9 + instant_fps * 0.1 if self.fps else instant_fps

        if self._psutil is not None:
            try:
                self.cpu = float(self._psutil.cpu_percent(interval=None) or 0.0)
            except Exception:
                self.cpu = 0.0

        h, w = frame.shape[:2]
        target = int(context.get("fps_target", 0) or 0)
        fps_text = f"F10 HUD FPS: {self.fps:.1f} (target {target})"
        cpu_text = f"CPU: {self.cpu:.1f}%"
        cv2.putText(frame, fps_text, (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (80, 255, 120), 2)
        cv2.putText(frame, cpu_text, (18, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (160, 230, 255), 2)
        cv2.putText(frame, f"Res: {w}x{h}", (18, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (230, 230, 230), 2)
        cv2.putText(frame, "FPS graph", (18, 118), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 2)
        bar_w = max(0, min(w - 60, int(self.fps * 4)))
        cv2.rectangle(frame, (60, 108), (60 + bar_w, 124), (80, 255, 120), -1)
        return frame
