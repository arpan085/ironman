from __future__ import annotations

import math
import time
from collections import deque
from typing import Any

import cv2  # type: ignore
import numpy as np  # type: ignore

# ---- palette -----------------------------------------------------------
CYAN = (255, 225, 78)        # BGR: bright cyan-blue
CYAN_DIM = (170, 130, 40)
GOLD = (60, 170, 255)        # BGR: amber/gold (repulsor)
WHITE = (255, 255, 255)
PANEL_BG = (28, 18, 8)       # very dark blue-black, BGR

STATE_COLORS = {
    "idle": CYAN_DIM,
    "listening": CYAN,
    "thinking": GOLD,
    "speaking": WHITE,
}


def _blend(frame: np.ndarray, overlay: np.ndarray, alpha: float) -> None:
    """In-place alpha blend of a same-size overlay onto frame."""
    cv2.addWeighted(overlay, alpha, frame, 1 - alpha, 0, dst=frame)


def _glow_circle(layer: np.ndarray, center, radius, color, thickness=2, glow=3):
    """Draw a circle with a soft outer glow by stacking blurred passes."""
    cv2.circle(layer, center, radius, color, thickness, cv2.LINE_AA)
    if glow:
        blur = cv2.GaussianBlur(layer, (0, 0), sigmaX=glow)
        cv2.addWeighted(blur, 0.55, layer, 1.0, 0, dst=layer)


class JarvisHUD:
    """Stateful renderer: owns animation phase + a scrolling log of lines."""

    def __init__(self, max_log_lines: int = 5) -> None:
        self._t0 = time.time()
        self.log: deque[tuple[str, float]] = deque(maxlen=max_log_lines)

    def push_log(self, text: str) -> None:
        self.log.append((text, time.time()))

    # ---------------------------------------------------------------

    def draw(self, frame: np.ndarray, jarvis: Any) -> np.ndarray:
        """jarvis: your JarvisAssistant instance (state.active/listening/etc)."""

        if not jarvis.state.active:
            return frame

        h, w = frame.shape[:2]
        t = time.time() - self._t0

        # figure out a coarse animation state
        if jarvis.state.listening:
            state = "listening"
        elif getattr(jarvis.state, "thinking", False):
            state = "thinking"
        elif jarvis.state.last_reply and (time.time() - jarvis.state.last_action_time) < 2.2:
            state = "speaking"
        else:
            state = "idle"
        color = STATE_COLORS[state]

        overlay = frame.copy()

        self._draw_reticle(overlay, w, h, t, state, color)
        self._draw_system_panel(overlay, w, h, t, state, color, jarvis)
        self._draw_scanline_flicker(overlay, w, h, t)

        _blend(frame, overlay, 0.88)
        return frame

    # ---------------------------------------------------------------
    # Iron-Man-style rotating targeting reticle, top-right corner
    # ---------------------------------------------------------------

    def _draw_reticle(self, layer, w, h, t, state, color):
        cx, cy, r = w - 90, 90, 46
        speed = 2.2 if state == "listening" else 0.6

        # outer rotating dashed ring
        n_dashes = 16
        for i in range(n_dashes):
            a0 = (i / n_dashes) * 2 * math.pi + t * speed
            a1 = a0 + (math.pi / n_dashes) * 0.6
            p0 = (int(cx + r * math.cos(a0)), int(cy + r * math.sin(a0)))
            p1 = (int(cx + r * math.cos(a1)), int(cy + r * math.sin(a1)))
            cv2.line(layer, p0, p1, color, 2, cv2.LINE_AA)

        # inner solid ring
        cv2.circle(layer, (cx, cy), r - 14, color, 1, cv2.LINE_AA)

        # crosshair ticks
        for ang in (0, 90, 180, 270):
            a = math.radians(ang) + t * (speed * 0.4)
            p0 = (int(cx + (r - 24) * math.cos(a)), int(cy + (r - 24) * math.sin(a)))
            p1 = (int(cx + (r - 10) * math.cos(a)), int(cy + (r - 10) * math.sin(a)))
            cv2.line(layer, p0, p1, color, 2, cv2.LINE_AA)

        # pulsing core dot (breathes on idle, snaps bright on speaking)
        pulse = 0.5 + 0.5 * math.sin(t * (5 if state != "idle" else 2))
        core_r = int(5 + pulse * 3)
        _glow_circle(layer, (cx, cy), core_r, color, thickness=-1, glow=6)

        label = {"idle": "STANDBY", "listening": "LISTENING",
                 "thinking": "PROCESSING", "speaking": "SPEAKING"}[state]
        (tw, _), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
        cv2.putText(layer, label, (cx - tw // 2, cy + r + 22),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.45, color, 1, cv2.LINE_AA)

    # ---------------------------------------------------------------
    # Solo-Leveling-style "System Window": angled-corner panel with
    # glowing border + fading-in log lines
    # ---------------------------------------------------------------

    def _draw_system_panel(self, layer, w, h, t, state, color, jarvis):
        pw, ph = 340, 150
        x0, y0 = w - pw - 26, 150
        x1, y1 = x0 + pw, y0 + ph
        cut = 16  # corner notch size, gives it the "system window" silhouette

        pts = np.array([
            [x0 + cut, y0], [x1, y0], [x1, y1 - cut],
            [x1 - cut, y1], [x0, y1], [x0, y0 + cut],
        ], dtype=np.int32)

        panel = layer.copy()
        cv2.fillPoly(panel, [pts], PANEL_BG)
        cv2.addWeighted(panel, 0.55, layer, 0.45, 0, dst=layer)
        cv2.polylines(layer, [pts], True, color, 1, cv2.LINE_AA)
        # double-line accent just inside the border
        pts_in = pts.copy()
        pts_in[:, 0] += np.where(pts_in[:, 0] < (x0 + x1) / 2, 4, -4)
        pts_in[:, 1] += np.where(pts_in[:, 1] < (y0 + y1) / 2, 4, -4)
        cv2.polylines(layer, [pts_in], True, color, 1, cv2.LINE_AA)

        header = "J.A.R.V.I.S"
        cv2.putText(layer, header, (x0 + 20, y0 + 26),
                    cv2.FONT_HERSHEY_DUPLEX, 0.55, color, 1, cv2.LINE_AA)
        cv2.line(layer, (x0 + 18, y0 + 34), (x1 - 18, y0 + 34), CYAN_DIM, 1, cv2.LINE_AA)

        # listening waveform bars (fake but responsive-feeling)
        bar_y = y0 + 48
        bar_x = x0 + 20
        n_bars = 26
        bar_w = (pw - 40) / n_bars
        for i in range(n_bars):
            if state == "listening":
                amp = 3 + 10 * abs(math.sin(t * 9 + i * 0.5)) * (0.4 + 0.6 * math.sin(t * 1.7 + i))
                amp = max(2, abs(amp))
            elif state == "speaking":
                amp = 3 + 7 * abs(math.sin(t * 6 + i * 0.8))
            else:
                amp = 2
            bx = int(bar_x + i * bar_w)
            cv2.line(layer, (bx, int(bar_y)), (bx, int(bar_y - amp)), color, 2)

        # scrolling system log, fading in per-line
        log_y = bar_y + 26
        for text, ts in list(self.log)[-4:]:
            age = time.time() - ts
            alpha = min(1.0, age / 0.25)  # fade in over 0.25s
            c = tuple(int(ch * alpha + PANEL_BG[i] * (1 - alpha)) for i, ch in enumerate(color))
            line = f"> {text}"
            if len(line) > 42:
                line = line[:39] + "..."
            cv2.putText(layer, line, (x0 + 20, log_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, c, 1, cv2.LINE_AA)
            log_y += 20

        if not self.log:
            cv2.putText(layer, "> awaiting command...", (x0 + 20, log_y),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.42, CYAN_DIM, 1, cv2.LINE_AA)

    # ---------------------------------------------------------------
    # Subtle scanline sweep + occasional glitch flicker across the
    # whole overlay region, for that "holographic" feel without being
    # distracting during normal use
    # ---------------------------------------------------------------

    def _draw_scanline_flicker(self, layer, w, h, t):
        band_h = 3
        y = int((h * 0.15) + (h * 0.7) * ((t * 60) % 100) / 100)
        cv2.line(layer, (w - 420, y), (w - 20, y), (90, 60, 20), 1, cv2.LINE_AA)

        # rare glitch: brief bright flash on the panel border every ~4s
        if int(t * 10) % 40 == 0:
            cv2.rectangle(layer, (w - 366, 148), (w - 20, 302), CYAN, 1, cv2.LINE_AA)
