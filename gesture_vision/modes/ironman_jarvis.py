"""Iron Man J.A.R.V.I.S. Mark LXXXV Tactical Cockpit Mode.

Features:
- Center pulsating Stark Arc Reactor with rotating energy rings
- Hand-directed Repulsor Beam blaster (raise open palm -> charge -> blast!)
- Tactical facial target lock-on with biometric readouts
- Real-time holographic audio waveform visualizer for J.A.R.V.I.S. voice
- Deep Gemini multimodal vision analysis of the live camera feed
- Full suit telemetry readouts (armor, thrusters, core temperature, energy)
"""

from __future__ import annotations

import math
from pathlib import Path
import random
import time
from typing import Any
import numpy as np

from ..core.base_mode import BaseMode
from ..core.jarvis import JarvisAssistant
from ..core.model_cache import HAAR_FRONTALFACE_URL, ensure_model
from ..core.soundgen import play_named
from .common import (
    draw_cyber_circle,
    draw_cyber_hand,
    draw_ecg_monitor,
    draw_hex_shield,
    draw_hud_panel,
    draw_target_reticle,
    hands_of,
    palm_xy,
    point_xy,
)


class Particle:
    """Repulsor particle for charge-up vortex and blast explosion."""

    __slots__ = ("x", "y", "vx", "vy", "life", "max_life", "color", "size")

    def __init__(self, x: float, y: float, vx: float, vy: float, life: float, color: tuple[int, int, int], size: int = 2) -> None:
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.life = life
        self.max_life = life
        self.color = color
        self.size = size

    def update(self, dt: float = 0.033) -> bool:
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.life -= dt
        return self.life > 0


class IronManJarvisMode(BaseMode):
    """Complete Iron Man HUD with J.A.R.V.I.S. AI, Repulsor Blaster, and Arc Reactor."""

    name = "ironman_jarvis"
    shortcut = "F21"

    def __init__(self, jarvis: JarvisAssistant | None = None) -> None:
        self.jarvis = jarvis or JarvisAssistant()
        self._face_cascade = None

        # Arc Reactor animation state
        self._angle1 = 0.0
        self._angle2 = 0.0
        self._pulse_phase = 0.0

        # Repulsor blaster state
        self._charge_level = 0.0
        self._is_charging = False
        self._blast_flash = 0.0
        self._blast_ring_radius = 0.0
        self._blast_center: tuple[int, int] = (640, 360)
        self._blast_count = 0
        self._particles: list[Particle] = []

        # V3 Unibeam weapon state
        self._unibeam_charge = 0.0
        self._is_unibeam_firing = False
        self._unibeam_timer = 0.0
        self._unibeam_flash = 0.0

        # V3 Nanotech Energy Shield state
        self._shield_active = False
        self._shield_timer = 0.0
        self._shield_phase = 0.0

        # V3 Dynamic Biometrics telemetry
        self._ecg_phase = 0.0
        self._heart_rate = 74

        # Interactive typing state
        self._typing_mode = False
        self._input_buffer = ""

        # Target tracking lock state
        self._locked_target: tuple[int, int, int, int] | None = None
        self._lock_smooth: list[float] = [0.0, 0.0, 0.0, 0.0]

    def _detector(self) -> Any:
        """Lazily load OpenCV face cascade."""

        if self._face_cascade is not None:
            return self._face_cascade
        try:
            import cv2  # type: ignore

            candidates: list[Path] = []
            data_dir = getattr(getattr(cv2, "data", None), "haarcascades", "")
            if data_dir:
                candidates.append(Path(data_dir) / "haarcascade_frontalface_default.xml")
            cached = ensure_model("haarcascade_frontalface_default.xml", HAAR_FRONTALFACE_URL)
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

    def on_enter(self) -> None:
        """Play Iron Man suit power-up chime and announce J.A.R.V.I.S. status."""

        play_named("chime")
        self.jarvis.voice.speak("Mark LXXXV tactical HUD online. All repulsor systems armed, Sir.")

    def on_key(self, key: int, char: str) -> bool:
        """Handle mode-specific keyboard interaction."""

        import cv2  # type: ignore

        if self._typing_mode:
            if key in (10, 13):  # Enter
                if self._input_buffer.strip():
                    query = self._input_buffer.strip()
                    self._input_buffer = ""
                    self._typing_mode = False
                    self.jarvis.ask_async(query)
                else:
                    self._typing_mode = False
                return True
            elif key == 27:  # Esc
                self._typing_mode = False
                self._input_buffer = ""
                return True
            elif key == 8:  # Backspace
                self._input_buffer = self._input_buffer[:-1]
                return True
            elif char and len(char) == 1 and 32 <= key <= 126:
                self._input_buffer += char
                return True
            return True

        if char == "t" or char == "/":
            self._typing_mode = True
            self._input_buffer = ""
            return True

        if char == " " or key == 13:
            # Trigger Deep Multimodal Vision scan
            self._trigger_vision_scan()
            return True

        if char == "s":
            # Status report query
            self.jarvis.ask_async("status report")
            return True

        if char == "r":
            # Manual repulsor blast test
            self._trigger_blast((640, 360))
            return True

        if char == "u":
            # Unibeam weapon discharge
            self.force_unibeam()
            return True

        if char == "d":
            # Nanotech Shield toggle
            self.toggle_shield()
            return True

        if char == "c":
            # Clear blast count
            self._blast_count = 0
            return True

        return False

    def force_blast(self, center: tuple[int, int] | None = None) -> None:
        """Trigger an instant repulsor blast discharge via voice or keyboard command."""

        target = center or self._blast_center or (640, 360)
        self._trigger_blast(target)

    def force_unibeam(self) -> None:
        """Discharge full-power chest Arc Reactor Unibeam."""

        self._is_unibeam_firing = True
        self._unibeam_timer = time.time() + 1.2
        self._unibeam_flash = 0.95
        play_named("unibeam")
        self.jarvis.voice.speak("Unibeam engaged at maximum output, Sir.")

    def toggle_shield(self) -> None:
        """Toggle nanotech hexagonal energy barrier."""

        self._shield_active = not self._shield_active
        if self._shield_active:
            self._shield_timer = time.time() + 5.0
            play_named("shield")
            self.jarvis.voice.speak("Nanotech energy shield deployed, Sir.")
        else:
            play_named("ui_ping")

    def _trigger_vision_scan(self) -> None:
        """Trigger J.A.R.V.I.S. to visually analyze the current frame with Gemini."""

        play_named("lock")
        self.jarvis.voice.speak("Initiating multi-spectral visual scan, Sir.")
        self._need_vision_scan = True

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render complete Mark LXXXV tactical cockpit HUD."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]

        # Check if vision scan was requested
        if getattr(self, "_need_vision_scan", False):
            self._need_vision_scan = False
            self.jarvis.ask_async("Tactically analyze this frame. Report what you observe, threats, and surroundings, Sir.", frame_bgr=frame.copy())

        # Update animation timers
        self._angle1 = (self._angle1 + 2.5) % 360.0
        self._angle2 = (self._angle2 - 1.8) % 360.0
        self._pulse_phase = (self._pulse_phase + 0.1) % (2 * math.pi)

        # 1. Subtle dark vignette / tactical tint
        self._draw_cockpit_vignette(frame)

        # 2. Render Mark LXXXV Cybernetic Nanotech Hand Skeletons
        for hand_pts in hands_of(landmarks):
            draw_cyber_hand(frame, hand_pts)

        # 3. Two-hand tactical gestures (Unibeam aperture & Shield)
        self._process_two_hand_gestures(frame, landmarks)

        # 4. Face tracking & tactical biometric reticle
        self._draw_face_targeting(frame)

        # 5. Center Arc Reactor
        self._draw_arc_reactor(frame, (w // 2, h - 85))

        # 6. Repulsor Blaster tracking & discharge
        self._process_repulsor(frame, landmarks)

        # 7. Render Active Unibeam
        if self._is_unibeam_firing:
            if time.time() > self._unibeam_timer:
                self._is_unibeam_firing = False
            else:
                self._draw_unibeam(frame)

        # 8. Render Active Nanotech Shield
        if self._shield_active:
            if time.time() > self._shield_timer:
                self._shield_active = False
            else:
                self._draw_shield(frame)

        # 9. Artificial Horizon / Gyro Ladder
        self._draw_gyro_horizon(frame, (w // 2, h // 2 - 20))

        # 10. Telemetry Panels (Left & Right)
        self._draw_telemetry_hud(frame)

        # 11. Holographic Audio Waveform & Speech Subtitles
        self._draw_jarvis_speech_hud(frame)

        # 12. Interactive Typing Bar (if active)
        if self._typing_mode:
            self._draw_typing_bar(frame)

        # 13. Top Mode Banner
        cv2.putText(
            frame,
            "MARK LXXXV TACTICAL COCKPIT // J.A.R.V.I.S. READY",
            (18, 64),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.55,
            (0, 229, 255),
            2,
            cv2.LINE_AA,
        )
        sub_help = "Palm=Blast  |  Hands Center=Unibeam  |  Both Palms=Shield  |  U=Unibeam  |  D=Shield  |  SPACE=Scan"
        cv2.putText(
            frame,
            sub_help,
            (18, 86),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            (180, 240, 255),
            1,
            cv2.LINE_AA,
        )

        return frame

    def _draw_cockpit_vignette(self, frame: np.ndarray) -> None:
        """Overlay subtle high-tech HUD grid lines and corner telemetry."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        cyan = (0, 229, 255)

        # Subtle tactical frame border
        cv2.rectangle(frame, (8, 48), (w - 8, h - 34), (0, 80, 100), 1)

        # Corner notches
        notch = 24
        cv2.line(frame, (8, 48), (8 + notch, 48), cyan, 2)
        cv2.line(frame, (8, 48), (8, 48 + notch), cyan, 2)
        cv2.line(frame, (w - 8, 48), (w - 8 - notch, 48), cyan, 2)
        cv2.line(frame, (w - 8, 48), (w - 8, 48 + notch), cyan, 2)

        # Stark Industries watermark
        cv2.putText(
            frame,
            "STARK INDUSTRIES // ADVANCED WEAPONS DIVISION",
            (w - 380, h - 38),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.38,
            (0, 160, 200),
            1,
            cv2.LINE_AA,
        )

    def _draw_face_targeting(self, frame: np.ndarray) -> None:
        """Target human face with Stark biometric tracking bracket."""

        import cv2  # type: ignore

        detector = self._detector()
        if detector is None:
            return

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.2, 5, minSize=(60, 60))

        if len(faces) > 0:
            x, y, fw, fh = faces[0]
            # Smooth tracking box
            alpha = 0.4
            if self._lock_smooth[2] == 0:
                self._lock_smooth = [float(x), float(y), float(fw), float(fh)]
            else:
                self._lock_smooth[0] = self._lock_smooth[0] * (1 - alpha) + x * alpha
                self._lock_smooth[1] = self._lock_smooth[1] * (1 - alpha) + y * alpha
                self._lock_smooth[2] = self._lock_smooth[2] * (1 - alpha) + fw * alpha
                self._lock_smooth[3] = self._lock_smooth[3] * (1 - alpha) + fh * alpha

            sx, sy, sfw, sfh = [int(v) for v in self._lock_smooth]
            cx, cy = sx + sfw // 2, sy + sfh // 2

            # Tactical brackets
            c = (0, 229, 255)
            draw_target_reticle(frame, (cx, cy), size=max(sfw, sfh) + 18, color=c, label="PILOT // T. STARK")

            # Biometric telemetry next to face
            tx = sx + sfw + 14
            ty = sy + 20
            cv2.putText(frame, "ID: TONY STARK", (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, c, 1, cv2.LINE_AA)
            cv2.putText(frame, "HEART RATE: 72 BPM", (tx, ty + 16), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (100, 255, 120), 1, cv2.LINE_AA)
            cv2.putText(frame, "NEURAL LINK: SYNC 99.4%", (tx, ty + 30), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 220, 255), 1, cv2.LINE_AA)
            cv2.putText(frame, "THREAT: MINIMAL", (tx, ty + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (80, 240, 140), 1, cv2.LINE_AA)

    def _draw_arc_reactor(self, frame: np.ndarray, center: tuple[int, int]) -> None:
        """Render multi-ring animated Arc Reactor at the center bottom."""

        import cv2  # type: ignore

        cx, cy = center
        pulse = 0.5 + 0.5 * math.sin(self._pulse_phase)
        c_core = (255, 255, 255)
        c_cyan = (0, int(200 + 55 * pulse), 255)
        c_deep = (0, 140, 220)

        # Outer segmented ring
        draw_cyber_circle(frame, (cx, cy), radius=46, color=c_deep, thickness=2, segments=12, angle_offset=self._angle1, gap_ratio=0.3)
        # Inner counter-rotating ring
        draw_cyber_circle(frame, (cx, cy), radius=32, color=c_cyan, thickness=2, segments=6, angle_offset=self._angle2, gap_ratio=0.35)

        # Arc Reactor Core Glow
        cv2.circle(frame, (cx, cy), int(18 + 4 * pulse), c_cyan, -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), int(10 + 2 * pulse), c_core, -1, cv2.LINE_AA)

        # Unibeam triangle inside core
        pts = []
        for i in range(3):
            ang = self._angle1 * 0.5 + i * (2 * math.pi / 3.0)
            pts.append([int(cx + 14 * math.cos(ang)), int(cy + 14 * math.sin(ang))])
        cv2.polylines(frame, [np.array(pts, dtype=np.int32)], True, c_core, 1, cv2.LINE_AA)

        # Core Label
        cv2.putText(frame, "ARC REACTOR // 100%", (cx - 72, cy + 42), cv2.FONT_HERSHEY_SIMPLEX, 0.4, c_cyan, 1, cv2.LINE_AA)

    def _process_repulsor(self, frame: np.ndarray, landmarks: dict[str, Any]) -> None:
        """Detect open palm, charge capacitor, and fire Repulsor Blast."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        palm = palm_xy(landmarks, frame.shape)
        is_open = bool(landmarks.get("is_open_palm", False))

        dt = 0.033

        # Update existing particles
        self._particles = [p for p in self._particles if p.update(dt)]
        for p in self._particles:
            cv2.circle(frame, (int(p.x), int(p.y)), p.size, p.color, -1, cv2.LINE_AA)

        # Render active blast shockwave ring
        if self._blast_ring_radius > 0:
            bx, by = self._blast_center
            rad = int(self._blast_ring_radius)
            thick = max(2, int(8 * (1.0 - rad / (w * 0.75))))
            cv2.circle(frame, (bx, by), rad, (255, 255, 255), thick, cv2.LINE_AA)
            cv2.circle(frame, (bx, by), max(1, rad - 12), (0, 229, 255), max(1, thick - 1), cv2.LINE_AA)
            self._blast_ring_radius += 48.0
            if self._blast_ring_radius > w * 0.75:
                self._blast_ring_radius = 0.0

        # Full-screen blast flash
        if self._blast_flash > 0.05:
            overlay = frame.copy()
            overlay[:] = (255, 255, 255)
            frame[:] = cv2.addWeighted(frame, 1.0 - self._blast_flash, overlay, self._blast_flash, 0)
            self._blast_flash = max(0.0, self._blast_flash - 0.12)

        if palm is not None and is_open:
            px, py = palm
            self._is_charging = True

            # Repulsor targeting reticle on palm
            draw_target_reticle(frame, (px, py), size=60, color=(0, 229, 255), label="REPULSOR LOCK")

            # Charging progress
            if self._charge_level == 0.0:
                play_named("charge")

            self._charge_level = min(1.0, self._charge_level + 0.04)

            # Spawn vortex particles towards palm center
            for _ in range(3):
                ang = random.uniform(0, 2 * math.pi)
                dist = random.uniform(50, 130)
                sx = px + dist * math.cos(ang)
                sy = py + dist * math.sin(ang)
                vx = (px - sx) * 6.0
                vy = (py - sy) * 6.0
                color = random.choice([(0, 229, 255), (100, 255, 255), (255, 255, 255)])
                self._particles.append(Particle(sx, sy, vx, vy, life=0.35, color=color, size=random.randint(2, 4)))

            # Draw charging circle on palm
            charge_rad = int(14 + 28 * self._charge_level)
            cv2.circle(frame, (px, py), charge_rad, (0, 229, 255), 2, cv2.LINE_AA)
            cv2.circle(frame, (px, py), int(charge_rad * 0.5), (255, 255, 255), -1, cv2.LINE_AA)

            # Charge gauge bar
            bar_w = 120
            bar_x = px - bar_w // 2
            bar_y = py + 48
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 8), (0, 80, 100), 1)
            fill_w = int(bar_w * self._charge_level)
            cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + 8), (0, 229, 255), -1)
            pct = int(self._charge_level * 100)
            cv2.putText(frame, f"CAPACITOR: {pct}%", (bar_x, bar_y - 4), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 229, 255), 1, cv2.LINE_AA)

            # Firing at 100% charge
            if self._charge_level >= 1.0:
                self._trigger_blast((px, py))
                self._charge_level = 0.0

        else:
            self._is_charging = False
            self._charge_level = max(0.0, self._charge_level - 0.08)

    def _trigger_blast(self, center: tuple[int, int]) -> None:
        """Execute full Repulsor blast explosion."""

        play_named("blast")
        self._blast_flash = 0.75
        self._blast_ring_radius = 20.0
        self._blast_center = center
        self._blast_count += 1

        bx, by = center
        # Spawn explosive particle burst
        for _ in range(50):
            ang = random.uniform(0, 2 * math.pi)
            speed = random.uniform(150, 480)
            vx = speed * math.cos(ang)
            vy = speed * math.sin(ang)
            color = random.choice([(0, 229, 255), (255, 255, 255), (0, 180, 255)])
            self._particles.append(Particle(bx, by, vx, vy, life=random.uniform(0.3, 0.7), color=color, size=random.randint(2, 5)))

    def _draw_gyro_horizon(self, frame: np.ndarray, center: tuple[int, int]) -> None:
        """Draw tactical flight gyro pitch ladder in center."""

        import cv2  # type: ignore

        cx, cy = center
        c = (0, 180, 220)

        # Crosshair center
        cv2.line(frame, (cx - 24, cy), (cx - 8, cy), c, 1, cv2.LINE_AA)
        cv2.line(frame, (cx + 8, cy), (cx + 24, cy), c, 1, cv2.LINE_AA)
        cv2.line(frame, (cx, cy - 14), (cx, cy - 6), c, 1, cv2.LINE_AA)

        # Pitch bars +10 and -10 degrees
        for dy in (-36, 36):
            cv2.line(frame, (cx - 30, cy + dy), (cx - 10, cy + dy), c, 1, cv2.LINE_AA)
            cv2.line(frame, (cx + 10, cy + dy), (cx + 30, cy + dy), c, 1, cv2.LINE_AA)

    def _process_two_hand_gestures(self, frame: np.ndarray, landmarks: dict[str, Any]) -> None:
        """Track multi-hand gestures for Unibeam charging and Nanotech Shield deployment."""

        hands = hands_of(landmarks)
        h, w = frame.shape[:2]

        if len(hands) >= 2:
            h1, h2 = hands[0], hands[1]
            p1_tip = (int(h1[8].x * w), int(h1[8].y * h))
            p2_tip = (int(h2[8].x * w), int(h2[8].y * h))
            p1_thumb = (int(h1[4].x * w), int(h1[4].y * h))
            p2_thumb = (int(h2[4].x * w), int(h2[4].y * h))

            dist_tips = math.hypot(p1_tip[0] - p2_tip[0], p1_tip[1] - p2_tip[1])
            dist_thumbs = math.hypot(p1_thumb[0] - p2_thumb[0], p1_thumb[1] - p2_thumb[1])

            # Check if thumbs & index fingers are touching to form chest aperture (Unibeam)
            if dist_tips < 95 and dist_thumbs < 95:
                mid_x = (p1_tip[0] + p2_tip[0]) // 2
                mid_y = (p1_tip[1] + p2_tip[1]) // 2
                # Charge Unibeam
                self._unibeam_charge = min(1.0, self._unibeam_charge + 0.05)
                # Holographic charging focus reticle
                draw_cyber_circle(frame, (mid_x, mid_y), radius=int(25 + 40 * self._unibeam_charge), color=(0, 215, 255), thickness=2, segments=6, angle_offset=time.time() * 180.0)
                draw_target_reticle(frame, (mid_x, mid_y), size=55, color=(255, 255, 255), label=f"UNIBEAM {int(self._unibeam_charge * 100)}%")
                if self._unibeam_charge >= 1.0 and not self._is_unibeam_firing:
                    self.force_unibeam()
                    self._unibeam_charge = 0.0
                return

            # Check if both palms are raised wide facing camera (Shield)
            fingers = list(landmarks.get("fingers") or [])
            if len(fingers) >= 2 and fingers[0] >= 4 and fingers[1] >= 4 and dist_tips > 180:
                if not self._shield_active:
                    self.toggle_shield()

        # Decay unibeam charge when hands break aperture
        self._unibeam_charge = max(0.0, self._unibeam_charge - 0.04)

    def _draw_unibeam(self, frame: np.ndarray) -> None:
        """Render colossal chest Arc Reactor Unibeam laser with screen distortion."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        cx, cy = w // 2, h - 85
        target_x, target_y = w // 2, h // 2 - 20

        # Subtle frame vibration shake
        shake_x = random.randint(-4, 4)
        shake_y = random.randint(-4, 4)
        M = np.float32([[1, 0, shake_x], [0, 1, shake_y]])
        cv2.warpAffine(frame, M, (w, h), dst=frame, borderMode=cv2.BORDER_REFLECT)

        # Beam polygon from reactor outwards
        beam_w = 95
        pts = np.array([
            [cx - 35, cy],
            [cx + 35, cy],
            [target_x + beam_w, -60],
            [target_x - beam_w, -60],
        ], dtype=np.int32)

        # Outer plasma flare
        overlay = frame.copy()
        cv2.fillPoly(overlay, [pts], (0, 215, 255))
        frame[:] = cv2.addWeighted(frame, 0.45, overlay, 0.55, 0)

        # Inner laser core
        core_pts = np.array([
            [cx - 18, cy],
            [cx + 18, cy],
            [target_x + 36, -60],
            [target_x - 36, -60],
        ], dtype=np.int32)
        cv2.fillPoly(frame, [core_pts], (255, 255, 255), cv2.LINE_AA)

        # Shockwave rings expanding up the beam
        for i in range(4):
            ring_y = int(cy - ((time.time() * 850.0 + i * 160) % max(1, cy)))
            rw = int(35 + (cy - ring_y) * 0.22)
            cv2.ellipse(frame, (cx, ring_y), (rw, 14), 0, 0, 360, (0, 240, 255), 2, cv2.LINE_AA)

        # Chest reactor explosion flare
        cv2.circle(frame, (cx, cy), 80, (0, 229, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 42, (255, 255, 255), -1, cv2.LINE_AA)

    def _draw_shield(self, frame: np.ndarray) -> None:
        """Render hexagonal nanotech forcefield barrier across the viewport."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        self._shield_phase = (self._shield_phase + 0.08) % (2 * math.pi)
        draw_hex_shield(frame, (w // 2, h // 2), radius=int(min(w, h) * 0.44), color=(0, 229, 255), alpha=0.45, phase=self._shield_phase)
        cv2.putText(frame, "NANOTECH ENERGY BARRIER // ACTIVE", (w // 2 - 170, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.52, (0, 255, 255), 2, cv2.LINE_AA)

    def _draw_telemetry_hud(self, frame: np.ndarray) -> None:
        """Render left and right Mark LXXXV status telemetry panels."""

        import cv2  # type: ignore
        import psutil  # type: ignore

        h, w = frame.shape[:2]

        # Left Panel: Armor, Propulsion & Biometric ECG
        draw_hud_panel(frame, 18, 105, 205, 205, title="SUIT TELEMETRY // V3")
        lx = 28
        ly = 135
        c_cyan = (0, 229, 255)
        c_val = (100, 255, 140)

        cv2.putText(frame, "ARMOR INTEGRITY:", (lx, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, "100% [NOMINAL]", (lx + 105, ly), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_val, 1, cv2.LINE_AA)

        cv2.putText(frame, "THRUSTER GAIN:", (lx, ly + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, "MACH 3.2 READY", (lx + 105, ly + 20), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_val, 1, cv2.LINE_AA)

        cv2.putText(frame, "CORE TEMP:", (lx, ly + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, "86.4 C", (lx + 105, ly + 40), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 220, 255), 1, cv2.LINE_AA)

        cv2.putText(frame, "REPULSOR SHOTS:", (lx, ly + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, str(self._blast_count), (lx + 115, ly + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 255, 255), 2, cv2.LINE_AA)

        # Dynamic Biometric ECG Waveform
        self._ecg_phase = (self._ecg_phase + 0.04) % 1.0
        draw_ecg_monitor(frame, lx, ly + 76, 185, 34, phase=self._ecg_phase)

        cv2.putText(frame, "PULSE: 74 BPM  |  SPO2: 99%", (lx, ly + 124), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_val, 1, cv2.LINE_AA)
        cv2.putText(frame, "UNIBEAM: PRIMED  |  SHIELD: READY", (lx, ly + 144), cv2.FONT_HERSHEY_SIMPLEX, 0.33, c_cyan, 1, cv2.LINE_AA)

        # Right Panel: J.A.R.V.I.S. & AI Diagnostics
        draw_hud_panel(frame, w - 218, 105, 200, 165, title="AI CORTEX // JARVIS")
        rx = w - 208
        ry = 135

        cpu = psutil.cpu_percent(interval=None)
        ram = psutil.virtual_memory().percent
        gemini_status = "ONLINE (DEEP)" if self.jarvis.gemini.is_configured else "LOCAL PROTOCOL"
        gemini_color = (100, 255, 140) if self.jarvis.gemini.is_configured else (0, 220, 255)

        cv2.putText(frame, "AI NEURAL LINK:", (rx, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, "J.A.R.V.I.S. V8", (rx + 95, ry), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_val, 1, cv2.LINE_AA)

        cv2.putText(frame, "GEMINI REASONING:", (rx, ry + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, gemini_status, (rx + 115, ry + 22), cv2.FONT_HERSHEY_SIMPLEX, 0.33, gemini_color, 1, cv2.LINE_AA)

        cv2.putText(frame, "HOST CPU LOAD:", (rx, ry + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{cpu:.0f}%", (rx + 105, ry + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_val, 1, cv2.LINE_AA)

        cv2.putText(frame, "SYSTEM RAM:", (rx, ry + 66), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, f"{ram:.0f}%", (rx + 105, ry + 66), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_val, 1, cv2.LINE_AA)

        voice_st = "ACTIVE" if self.jarvis.voice.enabled else "MUTED"
        cv2.putText(frame, "SPEECH SYNTH:", (rx, ry + 88), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, voice_st, (rx + 105, ry + 88), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 255), 1, cv2.LINE_AA)

        ear_st = self.jarvis.ear.status_text if hasattr(self.jarvis, "ear") else "ONLINE"
        ear_col = (100, 255, 140) if "LISTENING" in ear_st or "HEARD" in ear_st else (0, 220, 255)
        cv2.putText(frame, "VOICE MIC EAR:", (rx, ry + 110), cv2.FONT_HERSHEY_SIMPLEX, 0.35, c_cyan, 1, cv2.LINE_AA)
        cv2.putText(frame, ear_st[:15], (rx + 115, ry + 110), cv2.FONT_HERSHEY_SIMPLEX, 0.35, ear_col, 1, cv2.LINE_AA)

    def _draw_jarvis_speech_hud(self, frame: np.ndarray) -> None:
        """Render audio waveform bars and holographic J.A.R.V.I.S. speech dialog."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]

        subtitle = self.jarvis.voice.get_subtitle()
        if not subtitle and not self.jarvis.is_thinking:
            subtitle = self.jarvis.last_response

        # Equalizer audio waveform visualizer at bottom right
        eq_x = w - 218
        eq_y = h - 90
        num_bars = 14
        bars = self.jarvis.voice.get_waveform(num_bars)
        is_hearing = hasattr(self.jarvis, "ear") and self.jarvis.ear.is_hearing_voice
        for i, val in enumerate(bars):
            bar_h = int(val * 24)
            bx = eq_x + i * 12
            if is_hearing:
                c = (0, 255, 100)  # Bright green when pilot is speaking into mic
            elif self.jarvis.voice.is_speaking:
                c = (0, 255, 255)  # Cyan-yellow when Jarvis is speaking
            else:
                c = (0, 160, 200)  # Calm blue-cyan baseline
            cv2.rectangle(frame, (bx, eq_y - bar_h), (bx + 8, eq_y), c, -1)

        # Holographic Speech Dialogue Box
        diag_w = min(740, w - 440)
        diag_h = 68
        diag_x = (w - diag_w) // 2
        diag_y = h - 145

        comm_title = "🎙️ J.A.R.V.I.S. VOICE COMM // MIC ACTIVE" if is_hearing else "J.A.R.V.I.S. TACTICAL LINK"
        draw_hud_panel(frame, diag_x, diag_y, diag_w, diag_h, title=comm_title)

        status_prefix = "THINKING..." if self.jarvis.is_thinking else "J.A.R.V.I.S.: "
        prefix_color = (0, 255, 255) if self.jarvis.is_thinking else (120, 255, 140)

        # If user recently spoke, show PILOT line
        recent_pilot = getattr(self.jarvis, "last_query", "")
        if recent_pilot:
            pilot_disp = f"PILOT: \"{recent_pilot[:48]}\""
            cv2.putText(
                frame,
                pilot_disp,
                (diag_x + 12, diag_y + 26),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.40,
                (0, 230, 255),
                1,
                cv2.LINE_AA,
            )

        # Word wrap subtitle
        words = subtitle.split()
        lines = []
        cur_line = ""
        for word in words:
            if len(cur_line) + len(word) + 1 <= 58:
                cur_line += (" " if cur_line else "") + word
            else:
                lines.append(cur_line)
                cur_line = word
        if cur_line:
            lines.append(cur_line)

        # Print Jarvis response lines
        y_offset = 45 if recent_pilot else 30
        for idx, line in enumerate(lines[:2]):
            cv2.putText(
                frame,
                f"{status_prefix if idx == 0 and not recent_pilot else ''}{line}",
                (diag_x + 12, diag_y + y_offset + idx * 17),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.42,
                (255, 255, 255),
                1,
                cv2.LINE_AA,
            )

    def _draw_typing_bar(self, frame: np.ndarray) -> None:
        """Render live holographic text prompt for talking directly to J.A.R.V.I.S."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        bw = min(680, w - 80)
        bx = (w - bw) // 2
        by = h // 2 - 30

        draw_hud_panel(frame, bx, by, bw, 60, title="STARK VOICE & TEXT INPUT // PRESS ENTER TO SEND")
        prompt = f">> {self._input_buffer}_"
        cv2.putText(frame, prompt, (bx + 14, by + 38), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 255), 2, cv2.LINE_AA)
