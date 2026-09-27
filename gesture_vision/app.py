"""Main application orchestration for the Ironman Gesture Vision Suite v2.0 with J.A.R.V.I.S."""

from __future__ import annotations

import ctypes
from dataclasses import dataclass
import logging
import math
import os
from pathlib import Path
import time
from typing import Any
import numpy as np

from .config import AppConfig, load_config
from .core.base_mode import BaseMode
from .core.hand_tracker import HandTracker
from .core.jarvis import JarvisAssistant
from .core.mode_manager import ModeManager
from .core.recorder import Recorder
from .core.soundgen import get_master_volume, is_muted, play_named, set_master_volume, toggle_mute
from .core.suit_ai import SuitAssistant, TelemetrySnapshot, VoiceCommand
from .logger import setup_logging
from .modes.air_drums import AirDrumsMode
from .modes.air_guitar import AirGuitarMode
from .modes.air_painter import AirPainterMode
from .modes.air_piano import AirPianoMode
from .modes.air_signature import AirSignatureMode
from .modes.brightness_controller import BrightnessControllerMode
from .modes.color_tracking import ColorTrackingMode
from .modes.common import draw_cyber_circle, draw_hud_panel
from .modes.drawing_canvas import VirtualDrawingCanvasMode
from .modes.emoji_detector import EmojiDetectorMode
from .modes.face_filter import FaceFilterMode
from .modes.finger_counter import FingerCounterMode
from .modes.finger_keyboard import FingerKeyboardMode
from .modes.finger_magic import FingerMagicMode
from .modes.gesture_calculator import GestureCalculatorMode
from .modes.gesture_games import GestureGamesMode
from .modes.gesture_snake import GestureSnakeMode
from .modes.hand_animation import HandAnimationEffectsMode
from .modes.image_viewer import ImageViewerMode
from .modes.ironman_jarvis import IronManJarvisMode
from .modes.macro_pad import MacroPadMode
from .modes.magnifier import MagnifierMode
from .modes.magic_wand import MagicWandMode
from .modes.music_player import MusicPlayerMode
from .modes.object_measurement import ObjectMeasurementMode
from .modes.performance_hud import PerformanceHUDMode
from .modes.rps_ai import RockPaperScissorsMode
from .modes.slide_controller import SlideControllerMode
from .modes.theremin import ThereminMode
from .modes.virtual_mouse import VirtualMouseMode
from .modes.virtual_whiteboard import VirtualWhiteboardMode
from .modes.volume_controller import VolumeControllerMode
from .ui.tkinter_ui import SidebarUI

logger = logging.getLogger(__name__)


def _resolve_fkey(key: int) -> str | None:
    """Map a waitKey code to an F1..F21 shortcut across backends.

    Windows OpenCV encodes function keys as ``VK << 16`` (F1 -> 0x00700000),
    X11/GTK builds return raw codes 65470..65490, and older highgui builds
    expose them as 190..210 after the low byte.
    """

    high = key >> 16
    if 0x70 <= high <= 0x84:
        return f"F{high - 0x70 + 1}"
    if 65470 <= key <= 65490:
        return f"F{key - 65470 + 1}"
    if 63236 <= key <= 63256:
        return f"F{key - 63236 + 1}"
    if 0 < key < 256 and 190 <= key <= 210:
        return f"F{key - 190 + 1}"
    return None


@dataclass(slots=True)
class RectButton:
    """Clickable Stark HUD on-screen button."""

    id: str
    label: str
    x: int
    y: int
    w: int
    h: int
    category: str = "main"
    active: bool = False
    color: tuple[int, int, int] = (0, 229, 255)


class GestureVisionApp:
    """Version 2.0: Composes hand tracker, J.A.R.V.I.S. AI, 31 modes, interactive HUD, and camera loop."""

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialize application services, J.A.R.V.I.S., and mode registry."""

        self.config = config or load_config()
        setup_logging()
        self.tracker = HandTracker(max_num_hands=2)

        # Initialize J.A.R.V.I.S. AI assistant
        self.jarvis = JarvisAssistant(
            api_key=self.config.gemini_api_key,
            model=self.config.jarvis_model,
            voice_enabled=self.config.jarvis_voice,
        )
        self.jarvis.set_action_handler(lambda act, arg: self._on_jarvis_action("", act, arg))
        self.jarvis.set_frame_provider(lambda: self._latest_frame)

        # Register all 31 modes
        self.mode_manager = ModeManager(
            [
                VirtualDrawingCanvasMode(config=self.config),
                AirPainterMode(),
                FingerCounterMode(),
                RockPaperScissorsMode(),
                VolumeControllerMode(),
                BrightnessControllerMode(),
                VirtualMouseMode(),
                FingerKeyboardMode(),
                GestureCalculatorMode(),
                VirtualWhiteboardMode(config=self.config),
                ColorTrackingMode(),
                ObjectMeasurementMode(),
                FaceFilterMode(),
                ImageViewerMode(),
                MusicPlayerMode(),
                HandAnimationEffectsMode(),
                GestureGamesMode(),
                FingerMagicMode(),
                EmojiDetectorMode(),
                PerformanceHUDMode(),
                GestureSnakeMode(),
                AirDrumsMode(),
                AirPianoMode(),
                SlideControllerMode(),
                ThereminMode(),
                AirGuitarMode(),
                MagicWandMode(),
                MagnifierMode(),
                MacroPadMode(),
                AirSignatureMode(),
                IronManJarvisMode(jarvis=self.jarvis),
            ]
        )
        self.recorder = Recorder(Path(self.config.record_output_dir))
        self.assistant = SuitAssistant(self.config, self.mode_manager)
        self.running = False
        self._show_help = False
        self.show_help = False
        self._fps = 0.0
        self.fps_live = 0.0
        self.cpu_load = 0.0
        self.temperature_c = 0.0
        self.battery_percent: int | None = None
        self._latest_frame: np.ndarray | None = None

        # Boot Sequence State (Version 2.0)
        self._in_boot_sequence = True
        self._boot_progress = 0.0
        self._boot_start_time = 0.0

        # On-Screen Interactive Controls & Mouse State
        self._mouse_pos: tuple[int, int] = (0, 0)
        self._mouse_clicked: tuple[int, int] | None = None
        self._mode_drawer_open = False
        self._jarvis_prompt_active = False
        self._jarvis_input_text = ""
        self._buttons: list[RectButton] = []

    def launch_sidebar(self) -> None:
        """Start optional sidebar with all shortcuts."""

        if not self.config.sidebar_enabled:
            return
        shortcuts = [(m.name, m.shortcut) for m in self.mode_manager.list_modes()]
        try:
            SidebarUI(self.config.app_name, shortcuts).start()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Sidebar UI unavailable: %s", exc)

    def _open_camera(self) -> Any:
        """Open the configured camera and apply requested resolution."""

        import cv2  # type: ignore

        cap = cv2.VideoCapture(self.config.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.window_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.window_height)
        return cap

    def _on_mouse(self, event: int, x: int, y: int, flags: int, param: Any) -> None:
        """Track mouse position and handle clicks on interactive buttons."""

        import cv2  # type: ignore

        self._mouse_pos = (x, y)
        if event == cv2.EVENT_LBUTTONDOWN:
            self._mouse_clicked = (x, y)
            self._handle_mouse_click(x, y)

    def _handle_mouse_click(self, x: int, y: int) -> None:
        """Process click actions on HUD buttons or mode drawer."""

        # 1. Check if clicking inside boot screen
        if self._in_boot_sequence:
            self._finish_boot()
            return

        # 2. Check if Mode Drawer is open
        if self._mode_drawer_open:
            # Check drawer buttons
            for btn in self._buttons:
                if btn.category == "drawer" and btn.x <= x <= btn.x + btn.w and btn.y <= y <= btn.y + btn.h:
                    self._switch_mode(btn.id)
                    self._mode_drawer_open = False
                    return
            # Click outside closes drawer
            self._mode_drawer_open = False
            return

        # 3. Check Top & Bottom Bar buttons
        for btn in self._buttons:
            if btn.category in ("nav", "status") and btn.x <= x <= btn.x + btn.w and btn.y <= y <= btn.y + btn.h:
                if btn.id not in ("toggle_audio", "prev_mode", "next_mode", "goto_ironman"):
                    play_named("ui_ping")
                self._dispatch_button_action(btn.id)
                return

    def _dispatch_button_action(self, button_id: str) -> None:
        """Execute action for on-screen clickable buttons."""

        if button_id == "toggle_audio":
            toggle_mute()
            if not is_muted():
                play_named("ui_ping")
                logger.info("Master audio unmuted (%d%%)", int(get_master_volume() * 100))
            else:
                logger.info("Master audio muted")

        elif button_id == "toggle_jarvis":
            new_state = not self.jarvis.voice.enabled
            self.jarvis.voice.enabled = new_state
            self.config.jarvis_voice = new_state
            if new_state:
                play_named("chime")
                self.jarvis.voice.speak("J.A.R.V.I.S. online. All neural channels active, Sir.")
            else:
                play_named("ui_ping")

        elif button_id == "toggle_mic":
            if hasattr(self.jarvis, "ear"):
                new_mic = not self.jarvis.ear.enabled
                self.jarvis.ear.enabled = new_mic
                if new_mic:
                    self.jarvis.ear.start()
                    play_named("chime")
                else:
                    self.jarvis.ear.stop()
                    play_named("ui_ping")

        elif button_id == "toggle_modes":
            self._mode_drawer_open = not self._mode_drawer_open

        elif button_id == "goto_ironman":
            self._switch_mode("ironman_jarvis")

        elif button_id == "prev_mode":
            self._cycle_mode(-1)

        elif button_id == "next_mode":
            self._cycle_mode(1)

        elif button_id == "help":
            self._show_help = not self._show_help
            self.show_help = self._show_help

        elif button_id == "chat":
            self._jarvis_prompt_active = not self._jarvis_prompt_active
            self._jarvis_input_text = ""

        elif button_id == "snapshot":
            if self._latest_frame is not None:
                self.recorder.screenshot(self._latest_frame)

        elif button_id == "record":
            if self.recorder.is_recording():
                self.recorder.stop_video()
            elif self._latest_frame is not None:
                self.recorder.start_video(
                    self._latest_frame.shape[1],
                    self._latest_frame.shape[0],
                    self.config.target_fps,
                )

        elif button_id == "clear":
            active = self.mode_manager.active_mode
            if hasattr(active, "clear"):
                active.clear()

        elif button_id == "quit":
            self.running = False

    def _switch_mode(self, name: str) -> None:
        """Switch active mode safely and play acoustic switch audio."""

        if name == self.mode_manager.active_mode.name:
            return
        try:
            self.mode_manager.switch(name)
            play_named("switch")
        except KeyError:
            logger.warning("Attempted to switch to unknown mode: %s", name)

    def _switch_mode_by_shortcut(self, shortcut: str) -> None:
        """Switch active mode by shortcut and play acoustic switch audio."""

        old_mode = self.mode_manager.active_mode.name
        res = self.mode_manager.switch_by_shortcut(shortcut)
        if res and res.name != old_mode:
            play_named("switch")

    def _cycle_mode(self, direction: int) -> None:
        """Cycle through modes forward or backward."""

        modes = self.mode_manager.list_modes()
        names = [m.name for m in modes]
        current = self.mode_manager.active_mode.name
        idx = names.index(current) if current in names else 0
        new_idx = (idx + direction) % len(names)
        self._switch_mode(names[new_idx])

    def _finish_boot(self) -> None:
        """Complete boot sequence and transition into suit HUD."""

        self._in_boot_sequence = False
        play_named("chime")
        model_name = self.jarvis.gemini.model.upper()
        self.jarvis.voice.speak(f"Stark Mark LXXXV systems nominal. J.A.R.V.I.S. active with {model_name}, Sir.")

    def run(self) -> None:
        """Start webcam loop and process each frame with active mode."""

        try:
            import cv2  # type: ignore
        except Exception as exc:
            raise RuntimeError("OpenCV is required to run this app") from exc

        cap = self._open_camera()
        if not cap.isOpened():
            raise RuntimeError(
                f"Unable to open webcam (index {self.config.camera_index}). "
                "Check that a camera is connected and not used by another app."
            )

        # Set up interactive window & mouse listener
        cv2.namedWindow(self.config.app_name, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(self.config.app_name, self._on_mouse)

        if self.config.sidebar_enabled:
            self.launch_sidebar()

        self.assistant.play_startup_chime()
        self.assistant.start()
        self.running = True
        self._boot_start_time = time.time()
        start = time.time()
        frame_interval = 1.0 / max(1, self.config.target_fps)
        logger.info("%s v2.0 started (Mark LXXXV Stark Tech)", self.config.app_name)

        while self.running:
            loop_start = time.perf_counter()

            ok, frame = cap.read()
            if not ok:
                logger.warning("Frame read failed; re-opening camera")
                cap.release()
                cap = self._open_camera()
                if not cap.isOpened():
                    logger.error("Camera re-open failed; shutting down")
                    break
                continue

            frame = cv2.flip(frame, 1)
            self._latest_frame = frame
            now = time.perf_counter()
            self.fps_live = self._fps
            self.cpu_load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
            self.temperature_c = 34.0 + min(46.0, self.cpu_load * 8.0 + self.fps_live * 0.08)
            self.battery_percent = self._read_battery_percent()

            # Render Boot Sequence or Main Suite HUD
            if self._in_boot_sequence:
                self._draw_boot_screen(frame)
            else:
                landmarks = self.tracker.process(frame)
                context: dict[str, Any] = {
                    "fps_target": self.config.target_fps,
                    "fps_live": self.fps_live,
                    "cpu_load": self.cpu_load,
                    "temperature_c": self.temperature_c,
                    "battery_percent": self.battery_percent,
                    "elapsed": time.time() - start,
                    "jarvis": self.jarvis,
                }
                frame = self.mode_manager.active_mode.process(frame, landmarks, context)
                if self._show_help or self.show_help:
                    self._render_help_overlay(frame)
                self._draw_shell(frame)

            self.recorder.write(frame)
            cv2.imshow(self.config.app_name, frame)

            voice_command = self.assistant.poll_command()
            if voice_command is not None and not self._handle_voice_command(voice_command):
                break

            key = cv2.waitKey(1)
            if not self._handle_key(key, frame):
                break

            elapsed_loop = time.perf_counter() - loop_start
            inst_fps = 1.0 / max(elapsed_loop, 1e-6)
            self._fps = inst_fps * 0.1 + self._fps * 0.9
            delay = frame_interval - elapsed_loop
            if delay > 0:
                time.sleep(delay)

        self.recorder.stop_video()
        self.assistant.play_shutdown_chime()
        self.assistant.stop()
        cap.release()
        cv2.destroyAllWindows()
        self.running = False

    def _draw_boot_screen(self, frame: np.ndarray) -> None:
        """Render high-tech Stark Industries Mark LXXXV boot and loading screen."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        elapsed = time.time() - self._boot_start_time
        # Progress 0.0 to 1.0 over 2.4 seconds
        self._boot_progress = min(1.0, elapsed / 2.4)

        # Darkened high-tech background
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (8, 12, 16), -1)
        frame[:] = cv2.addWeighted(frame, 0.25, overlay, 0.75, 0)

        # Subtle tactical grid lines
        for y in range(60, h, 80):
            cv2.line(frame, (0, y), (w, y), (0, 45, 60), 1)

        # Central Arc Reactor Power-Up
        cx, cy = w // 2, h // 2 - 40
        angle = (elapsed * 120.0) % 360.0
        c_cyan = (0, 229, 255)
        c_gold = (0, 215, 255)
        c_core = (255, 255, 255)

        draw_cyber_circle(frame, (cx, cy), radius=70, color=(0, 100, 140), thickness=2, segments=12, angle_offset=angle, gap_ratio=0.3)
        draw_cyber_circle(frame, (cx, cy), radius=50, color=c_cyan, thickness=2, segments=6, angle_offset=-angle * 1.5, gap_ratio=0.35)
        cv2.circle(frame, (cx, cy), int(24 + 6 * math.sin(elapsed * 6.0)), c_cyan, -1, cv2.LINE_AA)
        cv2.circle(frame, (cx, cy), 14, c_core, -1, cv2.LINE_AA)

        # Title
        cv2.putText(frame, "STARK INDUSTRIES // MARK LXXXV OS v3.0", (cx - 240, cy - 110), cv2.FONT_HERSHEY_SIMPLEX, 0.72, c_cyan, 2, cv2.LINE_AA)
        cv2.putText(frame, "ADVANCED COMPUTER VISION & J.A.R.V.I.S. MULTIMODAL SUITE", (cx - 275, cy - 85), cv2.FONT_HERSHEY_SIMPLEX, 0.44, c_gold, 1, cv2.LINE_AA)

        # Diagnostics checklist
        items = [
            ("NANOTECH CYBERNETIC SKELETON", "CALIBRATED"),
            ("ARC REACTOR POWER CORE", "100% [8.21 GJ/s]"),
            (f"J.A.R.V.I.S. AI CORTEX ({self.jarvis.gemini.model.upper()})", "LINKED"),
            ("UNIBEAM & NANOTECH SHIELD ARRAYS", "ARMED"),
            ("ACOUSTIC CINEMA AUDIO SYNTHESIZER", "VELVET ACTIVE"),
            ("31 GESTURE & FLIGHT SUBSYSTEMS", "READY"),
        ]

        active_count = int(self._boot_progress * len(items))
        dy = cy + 95
        for i, (name, status) in enumerate(items):
            if i <= active_count:
                c_st = (100, 255, 140) if i < active_count else (0, 255, 255)
                cv2.putText(frame, f"[+] {name}:", (cx - 220, dy + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (200, 220, 240), 1, cv2.LINE_AA)
                cv2.putText(frame, status, (cx + 120, dy + i * 20), cv2.FONT_HERSHEY_SIMPLEX, 0.38, c_st, 1, cv2.LINE_AA)

        # Loading Progress Bar
        bar_w = 460
        bar_x = cx - bar_w // 2
        bar_y = h - 65
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + bar_w, bar_y + 12), (0, 60, 80), 1)
        fill_w = int(bar_w * self._boot_progress)
        cv2.rectangle(frame, (bar_x, bar_y), (bar_x + fill_w, bar_y + 12), c_cyan, -1)

        pct = int(self._boot_progress * 100)
        cv2.putText(frame, f"INITIALIZING: {pct}%", (bar_x, bar_y - 8), cv2.FONT_HERSHEY_SIMPLEX, 0.4, c_cyan, 1, cv2.LINE_AA)

        prompt_text = "ENGAGING SYSTEMS..." if self._boot_progress < 1.0 else "PRESS SPACE / ENTER OR CLICK TO ENGAGE HUD"
        cv2.putText(frame, prompt_text, (cx - 190, bar_y + 32), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (255, 255, 255) if self._boot_progress >= 1.0 else (140, 180, 200), 1, cv2.LINE_AA)

        if self._boot_progress >= 1.0 and elapsed > 2.8:
            self._finish_boot()

    def _draw_shell(self, frame: np.ndarray) -> None:
        """Draw interactive Stark Tech chrome, buttons, status bar, and dialog overlays."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        name = self.mode_manager.active_mode.name.replace("_", " ").title()
        shortcut = self.mode_manager.active_mode.shortcut

        self._buttons = []
        bar_bg = (14, 18, 24)
        c_cyan = (0, 229, 255)
        c_gold = (0, 215, 255)
        c_dim = (140, 160, 180)
        mx, my = self._mouse_pos

        # -------------------------------------------------------------
        # TOP BAR: Interactive Header Dock
        # -------------------------------------------------------------
        cv2.rectangle(frame, (0, 0), (w, 44), bar_bg, -1)
        cv2.line(frame, (0, 44), (w, 44), (0, 100, 130), 1)
        cv2.rectangle(frame, (0, 0), (6, 44), c_cyan, -1)

        # Title / Brand
        cv2.putText(frame, "MARK LXXXV", (16, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.52, c_gold, 2, cv2.LINE_AA)

        # Mode Navigation Buttons [ < ] and [ > ]
        prev_btn = RectButton("prev_mode", "<", 130, 8, 28, 28, category="nav")
        next_btn = RectButton("next_mode", ">", 164, 8, 28, 28, category="nav")
        self._buttons.extend([prev_btn, next_btn])
        self._render_button(frame, prev_btn, mx, my)
        self._render_button(frame, next_btn, mx, my)

        # Active Mode Title
        mode_label = f"MODE: {name.upper()} [{shortcut}]"
        cv2.putText(frame, mode_label, (206, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.52, c_cyan, 2, cv2.LINE_AA)

        # Top Right Interactive Action Buttons:
        # [ 🔊 / 🔇 AUDIO ]
        muted = is_muted()
        vol_pct = int(get_master_volume() * 100)
        audio_label = "🔇 MUTED" if muted else f"VOL {vol_pct}%"
        audio_col = (100, 100, 255) if muted else (100, 255, 140)
        audio_btn = RectButton("toggle_audio", audio_label, w - 665, 8, 85, 28, category="nav", active=not muted, color=audio_col)
        # [ 📂 MODES ]
        modes_btn = RectButton("toggle_modes", "MODES", w - 575, 8, 75, 28, category="nav")
        # [ ⚡ IRON MAN ]
        ironman_btn = RectButton("goto_ironman", "IRON MAN", w - 495, 8, 92, 28, category="nav")
        # [ 🎙️ MIC: ON / OFF ]
        mic_on = hasattr(self.jarvis, "ear") and self.jarvis.ear.enabled
        mic_hearing = hasattr(self.jarvis, "ear") and self.jarvis.ear.is_hearing_voice
        mic_label = "MIC: HEAR" if mic_hearing else ("MIC: ON" if mic_on else "MIC: OFF")
        mic_col = (0, 255, 100) if mic_hearing else ((100, 255, 140) if mic_on else (100, 100, 255))
        mic_btn = RectButton("toggle_mic", mic_label, w - 398, 8, 95, 28, category="nav", active=mic_on, color=mic_col)
        # [ J.A.R.V.I.S.: ON / OFF ]
        j_on = self.jarvis.voice.enabled
        j_label = "JARVIS: ON" if j_on else "JARVIS: OFF"
        j_color = (100, 255, 140) if j_on else (100, 100, 255)
        jarvis_btn = RectButton("toggle_jarvis", j_label, w - 298, 8, 120, 28, category="nav", active=j_on, color=j_color)
        # [ ? HELP ]
        help_btn = RectButton("help", "? HELP", w - 173, 8, 75, 28, category="nav")
        # [ X QUIT ]
        quit_top_btn = RectButton("quit", "X", w - 93, 8, 38, 28, category="nav", color=(100, 100, 255))

        self._buttons.extend([audio_btn, modes_btn, ironman_btn, mic_btn, jarvis_btn, help_btn, quit_top_btn])
        for btn in (audio_btn, modes_btn, ironman_btn, mic_btn, jarvis_btn, help_btn, quit_top_btn):
            self._render_button(frame, btn, mx, my)

        # -------------------------------------------------------------
        # BOTTOM BAR: Telemetry & Interactive Actions Dock
        # -------------------------------------------------------------
        cv2.rectangle(frame, (0, h - 32), (w, h), bar_bg, -1)
        cv2.line(frame, (0, h - 32), (w, h - 32), (0, 100, 130), 1)

        recording = self.recorder.is_recording()
        batt = "--" if self.battery_percent is None else f"{self.battery_percent}%"
        fps_info = f"FPS: {self._fps:4.0f} | CPU: {self.cpu_load:3.1f}% | TEMP: {self.temperature_c:4.1f}C | BAT: {batt}"
        if recording:
            fps_info += "  |  REC [ACTIVE]"
            cv2.circle(frame, (14, h - 16), 5, (0, 0, 255), -1, cv2.LINE_AA)
            cv2.putText(frame, fps_info, (26, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (80, 100, 255), 1, cv2.LINE_AA)
        else:
            cv2.putText(frame, fps_info, (14, h - 11), cv2.FONT_HERSHEY_SIMPLEX, 0.45, c_dim, 1, cv2.LINE_AA)

        # Bottom Bar Buttons
        chat_btn = RectButton("chat", "CHAT (J)", w - 460, h - 28, 82, 24, category="status")
        snap_btn = RectButton("snapshot", "SNAP (S)", w - 370, h - 28, 82, 24, category="status")
        rec_label = "STOP (Z)" if recording else "REC (R)"
        rec_btn = RectButton("record", rec_label, w - 280, h - 28, 80, 24, category="status", color=(0, 0, 255) if recording else c_cyan)
        clear_btn = RectButton("clear", "CLEAR (C)", w - 192, h - 28, 88, 24, category="status")
        quit_btn = RectButton("quit", "QUIT (Q)", w - 96, h - 28, 84, 24, category="status", color=(100, 100, 255))

        self._buttons.extend([chat_btn, snap_btn, rec_btn, clear_btn, quit_btn])
        for btn in (chat_btn, snap_btn, rec_btn, clear_btn, quit_btn):
            self._render_button(frame, btn, mx, my)

        # Floating J.A.R.V.I.S. voice communication toast across modes
        self._draw_global_jarvis_toast(frame)

        # Mode Selection Drawer Modal (when opened)
        if self._mode_drawer_open:
            self._render_mode_drawer(frame, mx, my)

        # Global J.A.R.V.I.S. Prompt Overlay (when opened)
        if self._jarvis_prompt_active:
            self._render_jarvis_global_overlay(frame)

        # Help Overlay (when opened)
        if self._show_help or self.show_help:
            self._render_help_overlay(frame)

    def _draw_global_jarvis_toast(self, frame: np.ndarray) -> None:
        """Render floating holographic J.A.R.V.I.S. voice communication toast across any mode."""

        import cv2  # type: ignore

        if self.mode_manager.active_mode.name == "ironman_jarvis":
            return

        subtitle = self.jarvis.voice.get_subtitle()
        is_speaking = self.jarvis.voice.is_speaking
        is_hearing = hasattr(self.jarvis, "ear") and self.jarvis.ear.is_hearing_voice
        is_thinking = self.jarvis.is_thinking

        if not (subtitle or is_speaking or is_hearing or is_thinking):
            return

        h, w = frame.shape[:2]
        bw = min(680, w - 80)
        bh = 54
        bx = (w - bw) // 2
        by = h - 94

        toast_title = "🎙️ PILOT VOICE DETECTED" if is_hearing else ("🤖 J.A.R.V.I.S. COMM LINK" if is_speaking else "J.A.R.V.I.S. AI")
        draw_hud_panel(frame, bx, by, bw, bh, title=toast_title)

        bars = self.jarvis.voice.get_waveform(10)
        for i, val in enumerate(bars):
            bar_h = int(val * 18)
            x_pos = bx + 14 + i * 8
            c = (0, 255, 100) if is_hearing else ((0, 255, 255) if is_speaking else (0, 160, 200))
            cv2.rectangle(frame, (x_pos, by + bh - 10 - bar_h), (x_pos + 5, by + bh - 10), c, -1)

        disp_text = "Processing tactical command, Sir..." if is_thinking else (f"J.A.R.V.I.S.: {subtitle[:58]}" if subtitle else "Listening to your voice command, Sir...")
        cv2.putText(frame, disp_text, (bx + 105, by + 34), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (255, 255, 255), 1, cv2.LINE_AA)

    def _render_button(self, frame: np.ndarray, btn: RectButton, mx: int, my: int) -> None:
        """Render a high-tech clickable Stark button with hover glow."""

        import cv2  # type: ignore

        is_hover = btn.x <= mx <= btn.x + btn.w and btn.y <= my <= btn.y + btn.h
        bg_col = (35, 48, 65) if is_hover else (20, 28, 38)
        border_col = (255, 255, 255) if is_hover else btn.color

        cv2.rectangle(frame, (btn.x, btn.y), (btn.x + btn.w, btn.y + btn.h), bg_col, -1)
        cv2.rectangle(frame, (btn.x, btn.y), (btn.x + btn.w, btn.y + btn.h), border_col, 1)

        # Corner notches
        notch = 4
        cv2.line(frame, (btn.x, btn.y), (btn.x + notch, btn.y), border_col, 2)
        cv2.line(frame, (btn.x, btn.y), (btn.x, btn.y + notch), border_col, 2)
        cv2.line(frame, (btn.x + btn.w, btn.y + btn.h), (btn.x + btn.w - notch, btn.y + btn.h), border_col, 2)
        cv2.line(frame, (btn.x + btn.w, btn.y + btn.h), (btn.x + btn.w, btn.y + btn.h - notch), border_col, 2)

        # Center label
        (tw, th), _ = cv2.getTextSize(btn.label, cv2.FONT_HERSHEY_SIMPLEX, 0.38, 1)
        tx = btn.x + (btn.w - tw) // 2
        ty = btn.y + (btn.h + th) // 2
        cv2.putText(frame, btn.label, (tx, ty), cv2.FONT_HERSHEY_SIMPLEX, 0.38, border_col, 1, cv2.LINE_AA)

    def _render_mode_drawer(self, frame: np.ndarray, mx: int, my: int) -> None:
        """Render high-tech holographic mode selection grid drawer."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        dw = min(920, w - 60)
        dh = min(540, h - 90)
        dx = (w - dw) // 2
        dy = 50

        draw_hud_panel(frame, dx, dy, dw, dh, title="STARK SUITE // MODE SELECTION DRAWER (CLICK TO ENGAGE)")

        modes = self.mode_manager.list_modes()
        ncols = 3
        nrows = (len(modes) + ncols - 1) // ncols
        card_w = (dw - 40) // ncols
        card_h = min(40, (dh - 60) // nrows)

        for i, m in enumerate(modes):
            col = i % ncols
            row = i // ncols
            bx = dx + 20 + col * card_w
            by = dy + 32 + row * card_h
            bw = card_w - 10
            bh = card_h - 6

            is_active = m.name == self.mode_manager.active_mode.name
            btn = RectButton(m.name, f"[{m.shortcut}] {m.name.replace('_', ' ').title()}", bx, by, bw, bh, category="drawer", active=is_active)
            if is_active:
                btn.color = (0, 255, 255)
            self._buttons.append(btn)
            self._render_button(frame, btn, mx, my)

    def _render_jarvis_global_overlay(self, frame: np.ndarray) -> None:
        """Render floating holographic J.A.R.V.I.S. chat dialog on top of any mode."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        bw = min(820, w - 80)
        bh = 175
        bx = (w - bw) // 2
        by = (h - bh) // 2

        overlay = frame.copy()
        cv2.rectangle(overlay, (bx, by), (bx + bw, by + bh), (10, 14, 18), -1)
        frame[:] = cv2.addWeighted(frame, 0.35, overlay, 0.65, 0)

        c = (0, 229, 255)
        arm = 20
        cv2.line(frame, (bx, by), (bx + arm, by), c, 2, cv2.LINE_AA)
        cv2.line(frame, (bx, by), (bx, by + arm), c, 2, cv2.LINE_AA)
        cv2.line(frame, (bx + bw, by), (bx + bw - arm, by), c, 2, cv2.LINE_AA)
        cv2.line(frame, (bx + bw, by), (bx + bw, by + arm), c, 2, cv2.LINE_AA)
        cv2.line(frame, (bx, by + bh), (bx + arm, by + bh), c, 2, cv2.LINE_AA)
        cv2.line(frame, (bx, by + bh), (bx, by + bh - arm), c, 2, cv2.LINE_AA)
        cv2.line(frame, (bx + bw, by + bh), (bx + bw - arm, by + bh), c, 2, cv2.LINE_AA)
        cv2.line(frame, (bx + bw, by + bh), (bx + bw - arm, by + bh), c, 2, cv2.LINE_AA)

        cv2.putText(
            frame,
            f"/// J.A.R.V.I.S. NEURAL LINK ({self.jarvis.gemini.model.upper()}) // ENTER TO SEND // ESC TO CLOSE ///",
            (bx + 16, by + 28),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.48,
            c,
            1,
            cv2.LINE_AA,
        )

        prompt = f">> {self._jarvis_input_text}_"
        cv2.rectangle(frame, (bx + 14, by + 42), (bx + bw - 14, by + 86), (20, 28, 38), -1)
        cv2.rectangle(frame, (bx + 14, by + 42), (bx + bw - 14, by + 86), (0, 160, 200), 1)
        cv2.putText(frame, prompt, (bx + 24, by + 72), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2, cv2.LINE_AA)

        resp_prefix = "J.A.R.V.I.S.: " if not self.jarvis.is_thinking else "THINKING: "
        resp_text = self.jarvis.last_response if not self.jarvis.is_thinking else "Analyzing sensor telemetry..."
        cv2.putText(
            frame,
            f"{resp_prefix}{resp_text[:85]}",
            (bx + 16, by + 118),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.46,
            (0, 255, 200) if not self.jarvis.is_thinking else (0, 220, 255),
            1,
            cv2.LINE_AA,
        )

        hint = "Try: 'switch to guitar', 'status report', 'what do you see?', 'clear', 'screenshot', 'volume up'"
        cv2.putText(frame, hint, (bx + 16, by + 152), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (160, 180, 200), 1, cv2.LINE_AA)

    def _render_help_overlay(self, frame: np.ndarray) -> None:
        """Render complete Stark shortcuts cheat sheet."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, h), (10, 14, 20), -1)
        frame[:] = cv2.addWeighted(frame, 0.25, overlay, 0.75, 0)

        cv2.putText(frame, "MARK LXXXV // IRONMAN GESTURE VISION SUITE v3.0", (60, 68), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 229, 255), 2, cv2.LINE_AA)

        modes = self.mode_manager.list_modes()
        top = 112
        cv2.putText(frame, f"Installed Modes ({len(modes)}) - Click or use Keys:", (60, top), cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2, cv2.LINE_AA)
        top += 26

        ncols = 2 if len(modes) > 18 else 1
        rows = (len(modes) + ncols - 1) // ncols
        col_step = max(60, (w - 120) // ncols)
        row_h = min(24, max(16, (h - 90 - top) // rows))

        for i, m in enumerate(modes):
            col, row = divmod(i, rows)
            line = f"{m.shortcut:>4}  {m.name.replace('_', ' ').title()}"
            is_jarvis = "jarvis" in m.name.lower() or m.shortcut == "F21"
            color = (0, 255, 255) if is_jarvis else (200, 220, 230)
            cv2.putText(frame, line, (60 + col * col_step, top + row * row_h), cv2.FONT_HERSHEY_SIMPLEX, 0.46, color, 1, cv2.LINE_AA)

        y = h - 64
        for text in (
            "M: Mute/Unmute  |  +/-: Master Volume  |  V: Mic Voice Hearing  |  J: Chat Prompt  |  Tab/[/]: Cycle",
            "Iron Man Mark LXXXV: U: Unibeam  |  D: Nanotech Shield  |  R/Fist: Repulsor  |  Space: Vision Scan",
            "Controls: R/Z: Record  |  S: Snap  |  C: Clear  |  U: Undo  |  E: Eraser  |  P: Palette  |  Q/Esc: Quit",
        ):
            cv2.putText(frame, text, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.44, (0, 229, 255), 1, cv2.LINE_AA)
            y += 20

    def _on_jarvis_action(self, text: str, action: str | None, action_arg: str | None) -> None:
        """Execute suit actions dispatched by J.A.R.V.I.S."""

        if not action:
            return

        logger.info("Executing J.A.R.V.I.S. action: %s (arg: %s)", action, action_arg)

        active = self.mode_manager.active_mode

        if action == "switch_mode" and action_arg:
            try:
                self._switch_mode(action_arg)
            except KeyError:
                self._switch_mode_by_shortcut(action_arg)
        elif action == "screenshot" and self._latest_frame is not None:
            self.recorder.screenshot(self._latest_frame)
        elif action == "record_start" and self._latest_frame is not None:
            self.recorder.start_video(self._latest_frame.shape[1], self._latest_frame.shape[0], self.config.target_fps)
        elif action == "record_stop":
            self.recorder.stop_video()
        elif action == "clear" and hasattr(active, "clear"):
            active.clear()
        elif action == "undo" and hasattr(active, "undo"):
            active.undo()
        elif action == "volume_up":
            from .core.system_controls import get_volume, set_volume
            set_volume(min(100, get_volume() + 15))
        elif action == "volume_down":
            from .core.system_controls import get_volume, set_volume
            set_volume(max(0, get_volume() - 15))
        elif action == "brightness_up":
            from .core.system_controls import get_brightness, set_brightness
            set_brightness(min(100, get_brightness() + 15))
        elif action == "brightness_down":
            from .core.system_controls import get_brightness, set_brightness
            set_brightness(max(0, get_brightness() - 15))
        elif action == "blast":
            if self.mode_manager.active_mode.name != "ironman_jarvis":
                self._switch_mode("ironman_jarvis")
            active_mode = self.mode_manager.active_mode
            if hasattr(active_mode, "force_blast"):
                active_mode.force_blast()
        elif action == "unibeam":
            if self.mode_manager.active_mode.name != "ironman_jarvis":
                self._switch_mode("ironman_jarvis")
            active_mode = self.mode_manager.active_mode
            if hasattr(active_mode, "force_unibeam"):
                active_mode.force_unibeam()
        elif action == "shield":
            if self.mode_manager.active_mode.name != "ironman_jarvis":
                self._switch_mode("ironman_jarvis")
            active_mode = self.mode_manager.active_mode
            if hasattr(active_mode, "toggle_shield"):
                active_mode.toggle_shield()
        elif action == "mute":
            if not is_muted():
                toggle_mute()
        elif action == "unmute":
            if is_muted():
                toggle_mute()
                play_named("ui_ping")
        elif action == "scan" and self._latest_frame is not None:
            self.jarvis.ask_async(
                "Tactically analyze this frame. Report what you observe, threats, and surroundings, Sir.",
                frame_bgr=self._latest_frame.copy(),
                callback=self._on_jarvis_action,
            )
        elif action == "quit":
            self.running = False

    def _handle_key(self, key: int, frame: Any) -> bool:
        """Unified, resilient key handler for all keyboard configurations."""

        if key == -1:
            return True

        # If in boot sequence, any key finishes boot immediately
        if self._in_boot_sequence:
            self._finish_boot()
            return True

        # If Mode Drawer is open, Esc closes it
        if self._mode_drawer_open:
            if key in (27, ord("q"), ord("Q")):
                self._mode_drawer_open = False
                return True

        # If Global J.A.R.V.I.S. Prompt Overlay is active, capture input
        if self._jarvis_prompt_active:
            if key in (10, 13):  # Enter
                if self._jarvis_input_text.strip():
                    query = self._jarvis_input_text.strip()
                    self._jarvis_input_text = ""
                    self._jarvis_prompt_active = False
                    self.jarvis.ask_async(query, frame_bgr=frame.copy(), callback=self._on_jarvis_action)
                else:
                    self._jarvis_prompt_active = False
                return True
            elif key == 27:  # Esc
                self._jarvis_prompt_active = False
                self._jarvis_input_text = ""
                return True
            elif key == 8:  # Backspace
                self._jarvis_input_text = self._jarvis_input_text[:-1]
                return True
            elif 32 <= (key & 0xFF) <= 126:
                self._jarvis_input_text += chr(key & 0xFF)
                return True
            return True

        # Check function keys (F1..F21) across all OS backends
        fkey = _resolve_fkey(key)
        if fkey:
            self._switch_mode_by_shortcut(fkey)
            return True

        # Universal Navigation Keys:
        # Tab (9), Left Arrow (81 / 2424832), Right Arrow (83 / 2555904), '[' and ']'
        low_byte = key & 0xFF
        if key == 9 or low_byte == ord("]") or key in (83, 2555904):
            self._cycle_mode(1)
            return True
        elif low_byte == ord("[") or key in (81, 2424832):
            self._cycle_mode(-1)
            return True

        if low_byte in (27, ord("q"), ord("Q")):
            return False

        typed = chr(low_byte).lower() if 32 <= low_byte <= 126 else ""

        if typed == "h":
            self._show_help = not self._show_help
            self.show_help = self._show_help
            return True

        # Global J.A.R.V.I.S. Prompt toggle
        if typed == "j":
            self._jarvis_prompt_active = True
            self._jarvis_input_text = ""
            play_named("ui_ping")
            return True

        # Voice Mic Ear toggle ('v')
        if typed == "v":
            if hasattr(self.jarvis, "ear"):
                self.jarvis.ear.enabled = not self.jarvis.ear.enabled
                if self.jarvis.ear.enabled:
                    self.jarvis.ear.start()
                    play_named("chime")
                else:
                    self.jarvis.ear.stop()
                    play_named("ui_ping")
            return True

        active = self.mode_manager.active_mode

        # Allow active mode first chance to consume the key
        if hasattr(active, "on_key"):
            try:
                if active.on_key(key, typed):
                    return True
            except TypeError:
                try:
                    if active.on_key(key):
                        return True
                except Exception:
                    pass
            except Exception:  # noqa: BLE001
                pass

        # Master Mute Toggle ('m')
        if typed == "m":
            toggle_mute()
            if not is_muted():
                play_named("ui_ping")
            return True

        # Master Volume Adjustments ('+' / '=') and ('-' / '_')
        if low_byte in (ord("+"), ord("=")):
            set_master_volume(min(1.0, get_master_volume() + 0.10))
            play_named("ui_ping")
            return True
        elif low_byte in (ord("-"), ord("_")):
            set_master_volume(max(0.0, get_master_volume() - 0.10))
            play_named("ui_ping")
            return True

        # Handle Numpad keys (VK_NUMPAD0..VK_NUMPAD9 -> 0x60..0x69)
        high = (key >> 16) & 0xFF
        if 0x60 <= high <= 0x69:
            typed = str(high - 0x60)

        # Direct number shortcuts (1..9, 0)
        if typed in "1234567890":
            self._switch_mode_by_shortcut(typed)
            return True

        if low_byte == ord("c") and hasattr(active, "clear"):
            active.clear()
        elif low_byte == ord("u") and hasattr(active, "undo"):
            active.undo()
        elif low_byte == ord("e") and hasattr(active, "eraser"):
            active.eraser = not bool(active.eraser)
        elif low_byte == ord("p") and hasattr(active, "toggle_style"):
            active.toggle_style()
        elif low_byte == ord("x") and hasattr(active, "next_effect"):
            active.next_effect()
        elif low_byte == ord("g") and hasattr(active, "next_game"):
            active.next_game()
        elif low_byte == ord("y") and hasattr(active, "toggle_style"):
            active.toggle_style()
        elif low_byte == ord("s"):
            if hasattr(active, "snapshot"):
                active.snapshot()
            self.recorder.screenshot(frame)
        elif low_byte == ord("r"):
            if self.recorder.is_recording():
                self.recorder.stop_video()
            else:
                self.recorder.start_video(frame.shape[1], frame.shape[0], self.config.target_fps)
        elif low_byte == ord("z"):
            self.recorder.stop_video()
        elif low_byte == ord("\r") and hasattr(active, "play_round"):
            try:
                active.play_round()
            except TypeError:
                active.play_round(0)

        return True

    def _telemetry_snapshot(self) -> TelemetrySnapshot:
        """Build suit-status telemetry payload."""

        return TelemetrySnapshot(
            fps=self.fps_live,
            cpu_load=self.cpu_load,
            temperature_c=self.temperature_c,
            battery_percent=self.battery_percent,
        )

    def _speak_status(self) -> None:
        """Speak current suit telemetry summary."""

        if not self.config.suit_status_voice_enabled:
            return
        self.assistant.speak_status(self._telemetry_snapshot())

    def _handle_voice_command(self, command: VoiceCommand) -> bool:
        """Route parsed wake-word commands."""

        if command.kind == "wake_ack":
            self.assistant.speak("At your service, sir.")
            return True
        if command.kind == "status_report":
            self._speak_status()
            return True
        if command.kind == "help_overlay":
            self.show_help = not self.show_help
            self._show_help = self.show_help
            self.assistant.confirm("Opening tactical help overlay.")
            return True
        if command.kind == "switch_mode":
            switched = self.mode_manager.switch(command.payload)
            self.assistant.confirm(f"Switching to {switched.name.replace('_', ' ')} mode.")
            return True
        if command.kind == "shutdown":
            self.assistant.confirm("Powering down.")
            return False
        self.assistant.speak("Command not recognized.")
        return True

    def _read_battery_percent(self) -> int | None:
        """Read host battery percent when available."""

        if os.name != "nt":
            return None

        class _PowerStatus(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong),
                ("BatteryFullLifeTime", ctypes.c_ulong),
            ]

        status = _PowerStatus()
        try:
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)) == 0:
                return None
            percent = int(status.BatteryLifePercent)
            if percent < 0 or percent > 100:
                return None
            return percent
        except Exception:
            return None
