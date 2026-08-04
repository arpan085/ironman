"""Main application orchestration for gesture suite."""

from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Any, Callable
import webbrowser

import numpy as np

from .config import AppConfig, load_config
from .core.hand_tracker import HandTracker
from .core.mode_manager import ModeManager
from .core.recorder import Recorder
from .core.suit_ai import SuitAssistant, TelemetrySnapshot, VoiceCommand
from .logger import setup_logging
from .modes.air_painter import AirPainterMode
from .modes.brightness_controller import BrightnessControllerMode
from .modes.color_tracking import ColorTrackingMode
from .modes.drawing_canvas import VirtualDrawingCanvasMode
from .modes.emoji_detector import EmojiDetectorMode
from .modes.face_filter import FaceFilterMode
from .modes.finger_counter import FingerCounterMode
from .modes.finger_keyboard import FingerKeyboardMode
from .modes.finger_magic import FingerMagicMode
from .modes.gesture_calculator import GestureCalculatorMode
from .modes.gesture_games import GestureGamesMode
from .modes.hand_animation import HandAnimationEffectsMode
from .modes.image_viewer import ImageViewerMode
from .modes.music_player import MusicPlayerMode
from .modes.object_measurement import ObjectMeasurementMode
from .modes.performance_hud import PerformanceHUDMode
from .modes.rps_ai import RockPaperScissorsMode
from .modes.virtual_mouse import VirtualMouseMode
from .modes.virtual_whiteboard import VirtualWhiteboardMode
from .modes.volume_controller import VolumeControllerMode
from .ui.tkinter_ui import SidebarUI
from .ui.jarvis_hud import JarvisHUD


HUD_ACCENT = (0, 229, 255)
HUD_BG = (16, 16, 24)
HUD_LINE = (30, 120, 180)
HUD_SWEEP = (255, 180, 0)


class GestureVisionApp:
    """Composes tracker, modes, UI, and camera loop."""

    def __init__(self, config: AppConfig | None = None, show_splash_override: bool | None = None) -> None:
        """Initialize application services and mode registry."""

        self.config = config or load_config()
        self.show_splash_screen = self.config.show_splash_screen if show_splash_override is None else show_splash_override
        setup_logging()
        self.tracker = HandTracker(max_num_hands=2)
        self._mode_factories = self._build_mode_factories()
        self.mode_manager = self._create_mode_manager()
        self.recorder = Recorder(Path(self.config.record_output_dir))
        self.assistant = SuitAssistant(self.config, self.mode_manager)
        self.assistant_enabled = self.config.assistant_enabled
        self.running = False
        self.show_help = False
        self.show_mode_list = False
        self.fps_live = 0.0
        self.cpu_load = 0.0
        self.temperature_c = 0.0
        self.battery_percent: int | None = None
        self._overlay_until = 0.0
        self._overlay_text = ""
        self.assistant_overlay_active = False
        self._assistant_overlay_title = "JARVIS"
        self._assistant_overlay_details = "Standby"
        self._jarvis_hud = JarvisHUD()
        self._camera_stream_open = False

    def _build_mode_factories(self) -> list[Callable[[], Any]]:
        """Return mode constructors for normal startup and soft reset."""

        return [
            lambda: VirtualDrawingCanvasMode(self.config),
            AirPainterMode,
            FingerCounterMode,
            RockPaperScissorsMode,
            VolumeControllerMode,
            BrightnessControllerMode,
            VirtualMouseMode,
            FingerKeyboardMode,
            GestureCalculatorMode,
            lambda: VirtualWhiteboardMode(self.config),
            ColorTrackingMode,
            ObjectMeasurementMode,
            FaceFilterMode,
            ImageViewerMode,
            MusicPlayerMode,
            HandAnimationEffectsMode,
            GestureGamesMode,
            FingerMagicMode,
            EmojiDetectorMode,
            PerformanceHUDMode,
        ]

    def _create_mode_manager(self) -> ModeManager:
        """Create a fresh mode manager from stored constructors."""

        return ModeManager([factory() for factory in self._mode_factories])

    def launch_sidebar(self) -> None:
        """Start optional sidebar with all shortcuts."""

        if not self.config.sidebar_enabled:
            return
        # Build triples (display name, keybind, callback) for the improved SidebarUI
        shortcuts: list[tuple[str, str, callable | None]] = []
        for m in self.mode_manager.list_modes():
            name = m.name.replace("_", " ").title()
            key = m.shortcut
            def make_cb(k: str):
                def cb() -> None:
                    switched = self.mode_manager.switch_by_shortcut(k)
                    if switched:
                        self._assistant_confirm(f"Switching to {switched.name.replace('_', ' ')} mode.")
                return cb
            shortcuts.append((name, key, make_cb(key)))

        SidebarUI(self.config.app_name, shortcuts, width=self.config.window_width, height=self.config.window_height, fullscreen=self.config.fullscreen_enabled).start()

    def run(self) -> None:
        """Start splash, then webcam loop, and process each frame with active mode."""

        try:
            import cv2  # type: ignore
        except Exception as exc:
            raise RuntimeError("OpenCV is required to run this app") from exc

        self._setup_window(cv2)
        if self.show_splash_screen and not self._show_startup_splash(cv2):
            cv2.destroyAllWindows()
            return
        if not self._play_boot_animation(cv2):
            cv2.destroyAllWindows()
            return

        cap = cv2.VideoCapture(self.config.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.window_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.window_height)
        if not cap.isOpened():
            cv2.destroyAllWindows()
            raise RuntimeError("Unable to open webcam")

        self.launch_sidebar()
        if self.assistant_enabled:
            self.assistant.play_startup_chime()
            self.assistant.start()
        self.running = True
        self._camera_stream_open = True
        start = time.time()
        prev = time.perf_counter()

        while self.running:
            if self.assistant_overlay_active:
                if self._camera_stream_open:
                    cap.release()
                    self._camera_stream_open = False
                frame = self._render_assistant_overlay()
                if self.assistant_enabled:
                    voice_command = self.assistant.poll_command()
                    if voice_command is not None and not self._handle_voice_command(voice_command):
                        break
                key = self._read_key(cv2)
                if not self._handle_key(key, frame):
                    break
                continue

            if not self._camera_stream_open:
                cap = cv2.VideoCapture(self.config.camera_index)
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.window_width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.window_height)
                if not cap.isOpened():
                    cv2.destroyAllWindows()
                    raise RuntimeError("Unable to open webcam")
                self._camera_stream_open = True

            ok, frame = cap.read()
            if not ok:
                continue
            now = time.perf_counter()
            dt = max(1e-6, now - prev)
            prev = now
            self.fps_live = 1.0 / dt
            self.cpu_load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
            self.temperature_c = self._read_cpu_temperature_c()
            self.battery_percent = self._read_battery_percent()
            frame = cv2.flip(frame, 1)
            landmarks = self.tracker.process(frame)
            context: dict[str, Any] = {
                "fps_target": self.config.target_fps,
                "fps_live": self.fps_live,
                "cpu_load": self.cpu_load,
                "temperature_c": self.temperature_c,
                "battery_percent": self.battery_percent,
                "elapsed": time.time() - start,
                "temperature_is_estimated": self._temperature_estimated,
            }
            frame = self.mode_manager.active_mode.process(frame, landmarks, context)
            if self.show_help:
                self._draw_help_overlay(frame)
            if self.show_mode_list:
                self._draw_mode_list_overlay(frame)
            self._draw_shell(frame)
            self.recorder.write(frame)
            cv2.imshow(self.config.app_name, frame)

            if self.assistant_enabled:
                voice_command = self.assistant.poll_command()
                if voice_command is not None and not self._handle_voice_command(voice_command):
                    break

            key = self._read_key(cv2)
            if not self._handle_key(key, frame):
                break

        self.recorder.stop_video()
        if self.assistant_enabled:
            self.assistant.play_shutdown_chime()
            self.assistant.stop()
        cap.release()
        cv2.destroyAllWindows()

    def _setup_window(self, cv2: Any) -> None:
        """Initialize display window and fullscreen behavior."""

        cv2.namedWindow(self.config.app_name, cv2.WINDOW_NORMAL)
        if self.config.fullscreen_enabled:
            cv2.setWindowProperty(self.config.app_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN)

    def _read_key(self, cv2_module: Any) -> int:
        """Read keyboard input without losing special-key codes."""

        if not hasattr(cv2_module, "waitKeyEx"):
            return int(cv2_module.waitKey(1))
        return int(cv2_module.waitKeyEx(1))

    def _draw_cinematic_layers(self, frame: Any, now: float) -> None:
        """Render reusable cinematic HUD effects."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        sweep_y = int((now * 150) % h)
        cv2.line(frame, (0, sweep_y), (w, sweep_y), HUD_SWEEP, 1)
        cv2.rectangle(frame, (10, 10), (w - 10, h - 10), HUD_LINE, 1)
        core_center = (w - 44, 26)
        glow = int(150 + 105 * (0.5 + 0.5 * math.sin(now * 3.2)))
        radius = 8 + int(5 * (0.5 + 0.5 * math.sin(now * 2.6)))
        cv2.circle(frame, core_center, 18, (30, 160, 255), 1)
        cv2.circle(frame, core_center, radius, (40, glow, 255), -1)

    def _show_startup_splash(self, cv2: Any) -> bool:
        """Show startup splash and wait for enter/click before camera initialization."""

        height = max(360, self.config.window_height)
        width = max(640, self.config.window_width)
        pressed = {"go": False}
        button_w, button_h = 360, 72
        x1 = (width - button_w) // 2
        y1 = (height - button_h) // 2 + 54
        x2 = x1 + button_w
        y2 = y1 + button_h

        def on_mouse(event: int, x: int, y: int, flags: int, param: Any) -> None:  # noqa: ARG001
            if event == cv2.EVENT_LBUTTONDOWN and x1 <= x <= x2 and y1 <= y <= y2:
                pressed["go"] = True

        cv2.setMouseCallback(self.config.app_name, on_mouse)

        while True:
            now = time.time()
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = HUD_BG
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (width, 64), (20, 20, 28), -1)
            self._draw_cinematic_layers(overlay, now)
            cv2.addWeighted(overlay, 0.62, frame, 0.38, 0, frame)
            cv2.putText(frame, self.config.app_name, (24, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.9, HUD_ACCENT, 2)
            cv2.putText(frame, "SYSTEM STANDBY", (width // 2 - 128, height // 2 - 46), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (210, 240, 255), 2)
            pulse = int(170 + 70 * (0.5 + 0.5 * math.sin(now * 4.0)))
            cv2.rectangle(frame, (x1, y1), (x2, y2), (60, pulse, 255), 2)
            cv2.putText(frame, "PRESS ENTER / CLICK TO INITIALIZE", (x1 + 20, y1 + 44), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (230, 250, 255), 2)
            cv2.putText(frame, "ESC or Q to quit", (width // 2 - 78, y2 + 36), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (170, 200, 220), 1)
            cv2.imshow(self.config.app_name, frame)
            key = self._read_key(cv2)
            if key in (27, ord("q"), ord("Q")):
                cv2.setMouseCallback(self.config.app_name, lambda *_: None)
                return False
            if key in (13, 10, ord(" ")) or pressed["go"]:
                cv2.setMouseCallback(self.config.app_name, lambda *_: None)
                return True

    def _play_boot_animation(self, cv2: Any) -> bool:
        """Render short boot-up transition before camera startup."""

        duration = 0.8
        start = time.perf_counter()
        height = max(360, self.config.window_height)
        width = max(640, self.config.window_width)
        while True:
            elapsed = time.perf_counter() - start
            if elapsed >= duration:
                return True
            now = time.time()
            frame = np.zeros((height, width, 3), dtype=np.uint8)
            frame[:] = HUD_BG
            self._draw_cinematic_layers(frame, now)
            alpha = min(1.0, elapsed / duration)
            color = (40, int(160 + 80 * alpha), 255)
            cv2.putText(frame, "ARC REACTOR ONLINE", (width // 2 - 190, height // 2), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
            cv2.imshow(self.config.app_name, frame)
            key = self._read_key(cv2)
            if key in (27, ord("q"), ord("Q")):
                return False

    def _render_assistant_overlay(self) -> Any:
        """Render a cinematic black-space overlay while Jarvis is active."""

        import cv2  # type: ignore

        height = max(360, self.config.window_height)
        width = max(640, self.config.window_width)
        frame = np.zeros((height, width, 3), dtype=np.uint8)
        frame[:] = HUD_BG
        overlay = frame.copy()
        self._draw_cinematic_layers(overlay, time.time())
        cv2.addWeighted(overlay, 0.55, frame, 0.45, 0, frame)

        star_count = 90
        if not hasattr(self, "_assistant_stars") or len(self._assistant_stars) != star_count:
            rng = np.random.RandomState(7)
            self._assistant_stars = [(int(x), int(y)) for x, y in rng.randint(0, [width, height], size=(star_count, 2))]
        for x, y in self._assistant_stars:
            cv2.circle(frame, (x, y), 1 + (x % 2), (220, 235, 255), 1)

        center = (width // 2, height // 2)
        now = time.time()
        pulse = 0.5 + 0.5 * math.sin(now * 2.8)
        for ring in range(3):
            radius = int(54 + ring * 24 + 6 * pulse)
            color = (40 + ring * 20, 90 + ring * 25, 220)
            cv2.circle(frame, center, radius, color, 2)
        cv2.circle(frame, center, int(20 + 6 * pulse), (255, 210, 80), -1)
        cv2.circle(frame, center, int(12 + 3 * pulse), (255, 255, 255), -1)

        cv2.putText(frame, self._assistant_overlay_title, (width // 2 - 120, height // 2 + 120), cv2.FONT_HERSHEY_SIMPLEX, 1.0, HUD_ACCENT, 2)
        cv2.putText(frame, self._assistant_overlay_details, (width // 2 - 160, height // 2 + 160), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (220, 240, 255), 1)
        cv2.putText(frame, "Press J to return", (width // 2 - 110, height - 46), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (180, 210, 235), 1)
        cv2.imshow(self.config.app_name, frame)
        return frame

    def _draw_help_overlay(self, frame: Any) -> None:
        """Render a compact two-column help overlay for all modes."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (24, 50), (w - 24, h - 24), (12, 12, 12), -1)
        cv2.addWeighted(overlay, 0.84, frame, 0.16, 0, frame)
        cv2.putText(frame, "Help & Shortcuts", (44, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.7, HUD_ACCENT, 2)
        modes = self.mode_manager.list_modes()
        half = max(1, len(modes) // 2)
        left = modes[:half]
        right = modes[half:]
        col_gap = 24
        column_width = (w - 2 * 44 - col_gap) // 2
        for idx, mode in enumerate(left):
            y = 110 + idx * 22
            cv2.putText(frame, f"{mode.shortcut} {mode.name.replace('_', ' ').title()}", (44, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
        for idx, mode in enumerate(right):
            y = 110 + idx * 22
            x = 44 + column_width + col_gap
            cv2.putText(frame, f"{mode.shortcut} {mode.name.replace('_', ' ').title()}", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)

    def _draw_mode_list_overlay(self, frame: Any) -> None:
        """Render mode list overlay for quick reference."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        overlay = frame.copy()
        panel_w = min(380, w - 40)
        cv2.rectangle(overlay, (20, 58), (20 + panel_w, h - 20), (10, 10, 14), -1)
        cv2.addWeighted(overlay, 0.82, frame, 0.18, 0, frame)
        cv2.putText(frame, "Mode List", (36, 86), cv2.FONT_HERSHEY_SIMPLEX, 0.68, HUD_ACCENT, 2)
        y = 114
        for info in self.mode_manager.list_modes():
            title = info.name.replace("_", " ").title()
            cv2.putText(frame, f"{info.shortcut:>4}  {title}", (36, y), cv2.FONT_HERSHEY_SIMPLEX, 0.46, (235, 235, 235), 1)
            y += 21
            if y > h - 30:
                break

    def _draw_shell(self, frame: Any) -> None:
        """Draw dark-themed shell chrome, overlays, and mode title."""

        import cv2  # type: ignore

        name = self.mode_manager.active_mode.name
        now = time.time()
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 52), HUD_BG, -1)
        if self.config.cinematic_hud_enabled:
            self._draw_cinematic_layers(overlay, now)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        cv2.putText(frame, f"{self.config.app_name} | Mode: {name}", (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.62, HUD_ACCENT, 2)
        batt = "--" if self.battery_percent is None else f"{self.battery_percent}%"
        cv2.putText(
            frame,
            f"FPS {self.fps_live:4.1f} | CPU {self.cpu_load:3.1f} | TEMP {self.temperature_c:4.1f}C | BAT {batt}",
            (16, h - 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.52,
            (110, 240, 255),
            1,
        )
        if now < self._overlay_until:
            cv2.rectangle(frame, (w // 2 - 230, h // 2 - 40), (w // 2 + 230, h // 2 + 40), (18, 18, 22), -1)
            cv2.rectangle(frame, (w // 2 - 230, h // 2 - 40), (w // 2 + 230, h // 2 + 40), HUD_LINE, 2)
            cv2.putText(frame, self._overlay_text, (w // 2 - 190, h // 2 + 10), cv2.FONT_HERSHEY_SIMPLEX, 0.9, (240, 248, 255), 2)

        # Draw Jarvis HUD overlay on top of all shell elements
        try:
            self._jarvis_hud.draw(frame, self.assistant)
        except Exception:
            # Never let overlay errors break the main loop
            pass

    def _trigger_overlay(self, text: str, duration_seconds: float = 0.75) -> None:
        """Schedule a short status animation overlay."""

        self._overlay_text = text
        self._overlay_until = time.time() + duration_seconds

    def _handle_key(self, key: int, frame: Any) -> bool:
        """Handle global keyboard shortcuts and mode shortcuts."""

        if key in (27, ord("q"), ord("Q")):
            return False

        active = self.mode_manager.active_mode
        if active.on_key(key):
            return True

        if key in (ord("h"), ord("H")):
            self.show_help = not self.show_help
            self._assistant_confirm("Toggling heads-up help.")
            return True
        if key in (ord("l"), ord("L")):
            self.show_mode_list = not self.show_mode_list
            return True
        if key in (ord("j"), ord("J")):
            if not self.assistant_enabled:
                self._trigger_overlay("JARVIS DISABLED", duration_seconds=0.8)
                return True
            if self.assistant_overlay_active:
                self.assistant_overlay_active = False
                self._assistant_overlay_title = "JARVIS"
                self._assistant_overlay_details = "Standby"
                if self.assistant.listening:
                    self.assistant.stop()
                self._trigger_overlay("JARVIS OFFLINE", duration_seconds=0.8)
                self._assistant_confirm("Jarvis offline.")
            else:
                self.assistant_overlay_active = True
                self.assistant.start()
                time.sleep(0.2)
                self.assistant.speak_intro_sequence()
                if self.assistant.listening and self.assistant.microphone_available:
                    self._assistant_overlay_title = "JARVIS ONLINE"
                    self._assistant_overlay_details = "Listening for wake word"
                    self._trigger_overlay("JARVIS ONLINE", duration_seconds=0.8)
                    self._assistant_confirm("Jarvis online.")
                elif self.assistant.microphone_available:
                    self._assistant_overlay_title = "JARVIS READY"
                    self._assistant_overlay_details = "Speech output ready; voice input pending"
                    self._trigger_overlay("JARVIS READY", duration_seconds=0.8)
                    self._assistant_confirm("Jarvis ready.")
                else:
                    self._assistant_overlay_title = "JARVIS READY"
                    self._assistant_overlay_details = "Speech output ready; voice input unavailable"
                    self._trigger_overlay("JARVIS READY", duration_seconds=0.8)
                    self._assistant_confirm("Jarvis ready.")
            return True

        typed = self._shortcut_from_key(key)
        if typed:
            previous = self.mode_manager.active_mode.name
            switched = self.mode_manager.switch_by_shortcut(typed)
            if switched is not None and switched.name != previous:
                self._assistant_confirm(f"Switching to {switched.name.replace('_', ' ')} mode.")

        if key in (ord("r"), ord("R")):
            self._reset_active_mode()
            return True
        if key == ord("c") and hasattr(active, "clear"):
            active.clear()
        elif key == ord("u") and hasattr(active, "undo"):
            active.undo()
        elif key == ord("e") and hasattr(active, "eraser"):
            active.eraser = not bool(active.eraser)
        elif key == ord("p") and hasattr(active, "toggle_style"):
            active.toggle_style()
        elif key == ord("x") and hasattr(active, "next_effect"):
            active.next_effect()
        elif key == ord("g") and hasattr(active, "next_game"):
            active.next_game()
        elif key == ord("y") and hasattr(active, "toggle_style"):
            active.toggle_style()
        elif key == ord("s"):
            if hasattr(active, "snapshot"):
                active.snapshot()
            self.recorder.screenshot(frame)
        elif key == ord("v"):
            self.recorder.start_video(frame.shape[1], frame.shape[0], self.config.target_fps)
            self._assistant_confirm("Recording started.")
        elif key == ord("z"):
            self.recorder.stop_video()
            self._assistant_confirm("Recording stopped.")
        elif key in (ord("t"), ord("T")):
            self._speak_status()
        elif key == ord("\r") and hasattr(active, "play_round"):
            active.play_round(0)

        return True

    def _shortcut_from_key(self, key: int) -> str | None:
        """Translate keyboard input into a mode shortcut string when possible."""

        normalized = key & 0xFFFF
        if 0x70 <= normalized <= 0x7B:
            return f"F{normalized - 0x6F}"
        if 32 <= key <= 126:
            return chr(key).lower()
        return None

    def _reset_active_mode(self) -> None:
        """Soft-reset active mode and local performance counters."""

        active_name = self.mode_manager.active_mode.name
        self.mode_manager.active_mode.on_exit()
        self.mode_manager = self._create_mode_manager()
        self.mode_manager.switch(active_name)
        self.assistant.attach_mode_manager(self.mode_manager)
        self.fps_live = 0.0
        self.cpu_load = 0.0
        self.temperature_c = 0.0
        self._trigger_overlay("RESETTING SUIT SYSTEM", duration_seconds=0.8)
        self._assistant_confirm("Reset complete.")

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

        if not self.assistant_enabled or not self.config.suit_status_voice_enabled:
            return
        self.assistant.speak_status(self._telemetry_snapshot())

    def _assistant_confirm(self, action: str) -> None:
        """Speak assistant confirmation line when assistant is enabled."""

        if not self.assistant_enabled:
            return
        self.assistant.confirm(action)

    def _handle_voice_command(self, command: VoiceCommand) -> bool:
        """Route parsed wake-word commands."""

        if command.kind == "wake_ack":
            self.assistant.speak("At your service, sir. I am ready for your command.")
            return True
        if command.kind == "greeting":
            self.assistant.speak("Hello, sir. I am doing great. How may I assist you today?")
            return True
        if command.kind == "introduction":
            self.assistant.speak("I am Jarvis, your immersive assistant. I can switch modes, open websites, report suit status, and control overlays.")
            return True
        if command.kind == "status_report":
            self._speak_status()
            return True
        if command.kind == "help_overlay":
            self.show_help = not self.show_help
            self._assistant_confirm("Opening tactical help overlay.")
            return True
        if command.kind == "switch_mode":
            try:
                switched = self.mode_manager.switch(command.payload)
            except KeyError:
                self.assistant.speak("I could not find that mode.")
                return True
            self.assistant.speak(f"Switching to {switched.name.replace('_', ' ')} mode.")
            return True
        if command.kind == "open_target":
            opened = self._open_target(command.payload)
            if opened:
                self.assistant.speak(f"Opening {command.payload} for you, sir.")
            else:
                self.assistant.speak("I could not open that target right now.")
            return True
        if command.kind == "close_target":
            closed = self._close_target(command.payload)
            if closed:
                self.assistant.speak(f"Closing {command.payload} for you, sir.")
            else:
                self.assistant.speak("I could not close that target right now.")
            return True
        if command.kind == "system_action":
            handled = self._handle_system_action(command.payload)
            if handled:
                self.assistant.speak(f"Executing {command.payload}.")
            else:
                self.assistant.speak("I could not perform that action right now.")
            return True
        if command.kind == "shutdown":
            self.assistant.speak("Powering down the suit systems.")
            return False
        self.assistant.speak("Command not recognized. I can switch modes, open websites, report status, or show help.")
        return True

    def _open_target(self, target: str) -> bool:
        """Open a known browser target or desktop app from a spoken command."""

        normalized = target.strip().lower()
        url_map = {
            "chrome": "https://www.google.com",
            "google": "https://www.google.com",
            "youtube": "https://www.youtube.com",
            "github": "https://github.com",
            "gmail": "https://mail.google.com",
            "netflix": "https://www.netflix.com",
            "spotify": "https://www.spotify.com",
            "twitter": "https://x.com",
            "facebook": "https://www.facebook.com",
            "linkedin": "https://www.linkedin.com",
            "reddit": "https://www.reddit.com",
            "docs": "https://docs.python.org/3/",
            "stack overflow": "https://stackoverflow.com",
            "news": "https://news.google.com",
        }
        if normalized in url_map:
            try:
                return webbrowser.open(url_map[normalized])
            except Exception:
                return False

        app_candidates = {
            "calculator": ["calc.exe", "gnome-calculator", "kcalc"],
            "notepad": ["notepad.exe", "gnome-text-editor"],
            "paint": ["mspaint.exe", "gimp"],
            "terminal": ["wt.exe", "cmd.exe", "gnome-terminal"],
        }
        if normalized in app_candidates:
            for candidate in app_candidates[normalized]:
                resolved = shutil.which(candidate)
                if resolved:
                    try:
                        subprocess.Popen([resolved])
                        return True
                    except Exception:
                        continue
        return False

    def _close_target(self, target: str) -> bool:
        """Try to close a known app or browser target."""

        normalized = target.strip().lower()
        app_map = {
            "chrome": ["chrome.exe", "google-chrome", "chromium", "chromium-browser"],
            "google": ["chrome.exe", "google-chrome", "chromium", "chromium-browser"],
            "youtube": ["chrome.exe", "google-chrome", "chromium", "chromium-browser"],
            "calculator": ["calc.exe"],
            "notepad": ["notepad.exe"],
        }
        if normalized in app_map:
            for proc_name in app_map[normalized]:
                try:
                    if os.name == "nt":
                        subprocess.run(["taskkill", "/F", "/IM", proc_name], check=False, capture_output=True)
                    else:
                        subprocess.run(["pkill", "-f", proc_name], check=False, capture_output=True)
                    return True
                except Exception:
                    continue
        return False

    def _handle_system_action(self, action: str) -> bool:
        """Perform supported in-app voice actions."""

        active = self.mode_manager.active_mode
        if action == "reset":
            self._reset_active_mode()
            return True
        if action == "clear" and hasattr(active, "clear"):
            active.clear()
            return True
        if action == "undo" and hasattr(active, "undo"):
            active.undo()
            return True
        if action == "eraser" and hasattr(active, "eraser"):
            active.eraser = not bool(active.eraser)
            return True
        if action == "snapshot":
            if hasattr(active, "snapshot"):
                active.snapshot()
            self.recorder.screenshot(None)
            return True
        if action == "record":
            self.recorder.start_video(self.config.window_width, self.config.window_height, self.config.target_fps)
            return True
        if action == "stop_recording":
            self.recorder.stop_video()
            return True
        return False

    @property
    def _temperature_estimated(self) -> bool:
        """Whether current temperature value is an estimate."""

        return not bool(getattr(self, "_temperature_real", False))

    def _read_cpu_temperature_c(self) -> float:
        """Read CPU temp via psutil when available; otherwise return estimated demo value."""

        fallback = 34.0 + min(46.0, self.cpu_load * 8.0 + self.fps_live * 0.08)
        try:
            import psutil  # type: ignore
        except ImportError:
            self._temperature_real = False
            return fallback

        sensors_temperatures = getattr(psutil, "sensors_temperatures", None)
        if not callable(sensors_temperatures):
            self._temperature_real = False
            return fallback

        try:
            temps = sensors_temperatures(fahrenheit=False)
        except (AttributeError, NotImplementedError):
            self._temperature_real = False
            return fallback
        if not temps:
            self._temperature_real = False
            return fallback

        values: list[float] = []
        for entries in temps.values():
            for entry in entries:
                current = getattr(entry, "current", None)
                if isinstance(current, (int, float)):
                    values.append(float(current))
        if not values:
            self._temperature_real = False
            return fallback
        self._temperature_real = True
        return sum(values) / len(values)

    def _read_battery_percent(self) -> int | None:
        """Read host battery percent when available."""

        try:
            import psutil  # type: ignore
        except ImportError:
            pass
        else:
            sensors_battery = getattr(psutil, "sensors_battery", None)
            if callable(sensors_battery):
                battery = sensors_battery()
                if battery is not None and battery.percent is not None:
                    return max(0, min(100, int(round(battery.percent))))

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
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)) == 0:
            return None
        percent = int(status.BatteryLifePercent)
        if percent < 0 or percent > 100:
            return None
        return percent
