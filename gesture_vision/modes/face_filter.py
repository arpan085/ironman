"""Face filter mode with Iron Man HUD, Stark Visor, and styled effects."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any
import numpy as np

from ..core.base_mode import BaseMode
from ..core.model_cache import HAAR_FRONTALFACE_URL, ensure_model
from .common import draw_cyber_circle, draw_target_reticle


class FaceFilterMode(BaseMode):
    """Applies Iron Man HUD, Stark Visor, sunglasses, hat, or cartoon effect using face detection."""

    name = "face_filter"
    shortcut = "F3"

    def __init__(self) -> None:
        """Initialize filter style and detector cache."""

        self.styles = ["ironman_hud", "stark_visor", "sunglasses", "hat", "cartoon"]
        self.style = "ironman_hud"
        self._face_cascade = None
        self._anim_timer = 0.0

    def _detector(self) -> Any:
        """Lazily create the OpenCV Haar face detector from local sources."""

        if self._face_cascade is not None:
            return self._face_cascade
        try:
            import cv2  # type: ignore

            candidates: list[Path] = []
            data_dir = getattr(getattr(cv2, "data", None), "haarcascades", "")
            if data_dir:
                candidates.append(Path(data_dir) / "haarcascade_frontalface_default.xml")
            cached = ensure_model(
                "haarcascade_frontalface_default.xml", HAAR_FRONTALFACE_URL
            )
            if cached is not None:
                candidates.append(cached)

            for candidate in candidates:
                if candidate.exists():
                    cascade = cv2.CascadeClassifier(str(candidate))
                    if not cascade.empty():
                        self._face_cascade = cascade
                        break
        except Exception:
            self._face_cascade = None
        return self._face_cascade

    def toggle_style(self) -> None:
        """Rotate through available face filter styles."""

        idx = (self.styles.index(self.style) + 1) % len(self.styles)
        self.style = self.styles[idx]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect faces and overlay selected filter effect."""

        import cv2  # type: ignore

        self._anim_timer = (self._anim_timer + 3.0) % 360.0
        detector = self._detector()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.15, 4, minSize=(60, 60)) if detector is not None else []

        for (x, y, w, h) in faces:
            if self.style == "ironman_hud":
                # Iron Man Mark LXXXV Helmet Visor & Targeting HUD
                eye_y = y + int(h * 0.38)
                left_eye_x = x + int(w * 0.3)
                right_eye_x = x + int(w * 0.7)

                # Eye targeting reticles
                draw_cyber_circle(frame, (left_eye_x, eye_y), radius=int(w * 0.12), color=(0, 229, 255), thickness=1, segments=6, angle_offset=self._anim_timer)
                draw_cyber_circle(frame, (right_eye_x, eye_y), radius=int(w * 0.12), color=(0, 229, 255), thickness=1, segments=6, angle_offset=-self._anim_timer)

                # Connecting tactical bridge line
                cv2.line(frame, (left_eye_x, eye_y), (right_eye_x, eye_y), (0, 229, 255), 1, cv2.LINE_AA)

                # Golden/Crimson Helmet Brow
                brow_y = y + int(h * 0.18)
                cv2.line(frame, (x + int(w * 0.1), brow_y), (x + int(w * 0.35), brow_y - 10), (0, 215, 255), 2, cv2.LINE_AA)
                cv2.line(frame, (x + int(w * 0.65), brow_y - 10), (x + int(w * 0.9), brow_y), (0, 215, 255), 2, cv2.LINE_AA)
                cv2.line(frame, (x + int(w * 0.35), brow_y - 10), (x + int(w * 0.65), brow_y - 10), (0, 69, 255), 2, cv2.LINE_AA)

                # Target readout
                cv2.putText(frame, "TARGET: ACQUIRED", (x, y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 229, 255), 1, cv2.LINE_AA)

            elif self.style == "stark_visor":
                # Sleek cyan cyberpunk visor
                vy1 = y + int(h * 0.3)
                vy2 = y + int(h * 0.52)
                vx1 = x + int(w * 0.08)
                vx2 = x + int(w * 0.92)

                sub = frame[vy1:vy2, vx1:vx2]
                if sub.size > 0:
                    overlay = sub.copy()
                    cv2.rectangle(overlay, (0, 0), (vx2 - vx1, vy2 - vy1), (0, 180, 255), -1)
                    frame[vy1:vy2, vx1:vx2] = cv2.addWeighted(sub, 0.35, overlay, 0.65, 0)
                    cv2.rectangle(frame, (vx1, vy1), (vx2, vy2), (0, 255, 255), 2)
                    # Visor scanline
                    scan_y = vy1 + int((vy2 - vy1) * (0.5 + 0.5 * math.sin(self._anim_timer * 0.05)))
                    cv2.line(frame, (vx1, scan_y), (vx2, scan_y), (255, 255, 255), 1, cv2.LINE_AA)

            elif self.style == "sunglasses":
                # Sleek shaded Aviators
                sy1 = y + int(h * 0.32)
                sy2 = y + int(h * 0.52)
                # Left lens
                cv2.ellipse(frame, (x + int(w * 0.32), (sy1 + sy2) // 2), (int(w * 0.16), (sy2 - sy1) // 2), 0, 0, 360, (20, 20, 20), -1)
                cv2.ellipse(frame, (x + int(w * 0.32), (sy1 + sy2) // 2), (int(w * 0.16), (sy2 - sy1) // 2), 0, 0, 360, (0, 215, 255), 2)
                # Right lens
                cv2.ellipse(frame, (x + int(w * 0.68), (sy1 + sy2) // 2), (int(w * 0.16), (sy2 - sy1) // 2), 0, 0, 360, (20, 20, 20), -1)
                cv2.ellipse(frame, (x + int(w * 0.68), (sy1 + sy2) // 2), (int(w * 0.16), (sy2 - sy1) // 2), 0, 0, 360, (0, 215, 255), 2)
                # Bridge
                cv2.line(frame, (x + int(w * 0.42), (sy1 + sy2) // 2), (x + int(w * 0.58), (sy1 + sy2) // 2), (0, 215, 255), 2)

            elif self.style == "hat":
                # High-tech Stark Tech tactical cap
                hy1 = max(0, y - int(h * 0.4))
                hy2 = y + int(h * 0.1)
                cv2.rectangle(frame, (x - 10, hy1), (x + w + 10, hy2), (25, 25, 30), -1)
                cv2.line(frame, (x - 18, hy2), (x + w + 18, hy2), (0, 229, 255), 3)
                cv2.putText(frame, "STARK", (x + int(w * 0.25), hy2 - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 229, 255), 1, cv2.LINE_AA)

            else:  # cartoon
                roi = frame[y : y + h, x : x + w]
                if roi.size > 0:
                    frame[y : y + h, x : x + w] = cv2.bilateralFilter(roi, 7, 50, 50)

        cv2.putText(frame, f"F3 Face Filter ({self.style.upper()}) | Y/P Toggle Style", (18, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 229, 255), 2, cv2.LINE_AA)
        return frame
