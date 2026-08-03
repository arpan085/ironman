"""Main application orchestration for gesture suite."""

from __future__ import annotations

import ctypes
import math
import os
from pathlib import Path
import time
from typing import Any

from .config import AppConfig, load_config
from .core.base_mode import BaseMode
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


class GestureVisionApp:
    """Composes tracker, modes, UI, and camera loop."""

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialize application services and mode registry."""

        self.config = config or load_config()
        setup_logging()
        self.tracker = HandTracker(max_num_hands=2)
        self.mode_manager = ModeManager(
            [
                VirtualDrawingCanvasMode(self.config),
                AirPainterMode(),
                FingerCounterMode(),
                RockPaperScissorsMode(),
                VolumeControllerMode(),
                BrightnessControllerMode(),
                VirtualMouseMode(),
                FingerKeyboardMode(),
                GestureCalculatorMode(),
                VirtualWhiteboardMode(self.config),
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
            ]
        )
        self.recorder = Recorder(Path(self.config.record_output_dir))
        self.assistant = SuitAssistant(self.config, self.mode_manager)
        self.running = False
        self.show_help = False
        self.fps_live = 0.0
        self.cpu_load = 0.0
        self.temperature_c = 0.0
        self.battery_percent: int | None = None

    def launch_sidebar(self) -> None:
        """Start optional sidebar with all shortcuts."""

        if not self.config.sidebar_enabled:
            return
        shortcuts = [(m.name, m.shortcut) for m in self.mode_manager.list_modes()]
        SidebarUI(self.config.app_name, shortcuts).start()

    def run(self) -> None:
        """Start webcam loop and process each frame with active mode."""

        try:
            import cv2  # type: ignore
        except Exception as exc:
            raise RuntimeError("OpenCV is required to run this app") from exc

        cap = cv2.VideoCapture(self.config.camera_index)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.window_width)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.window_height)
        if not cap.isOpened():
            raise RuntimeError("Unable to open webcam")

        self.launch_sidebar()
        self.assistant.play_startup_chime()
        self.assistant.start()
        self.running = True
        start = time.time()
        prev = time.perf_counter()

        while self.running:
            ok, frame = cap.read()
            if not ok:
                continue
            now = time.perf_counter()
            dt = max(1e-6, now - prev)
            prev = now
            self.fps_live = 1.0 / dt
            self.cpu_load = os.getloadavg()[0] if hasattr(os, "getloadavg") else 0.0
            self.temperature_c = 34.0 + min(46.0, self.cpu_load * 8.0 + self.fps_live * 0.08)
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
            }
            frame = self.mode_manager.active_mode.process(frame, landmarks, context)
            if self.show_help:
                self._draw_help_overlay(frame)
            self._draw_shell(frame)
            self.recorder.write(frame)
            cv2.imshow(self.config.app_name, frame)

            voice_command = self.assistant.poll_command()
            if voice_command is not None and not self._handle_voice_command(voice_command):
                break

            key = cv2.waitKey(1) & 0xFF
            if not self._handle_key(key, frame):
                break

        self.recorder.stop_video()
        self.assistant.play_shutdown_chime()
        self.assistant.stop()
        cap.release()
        cv2.destroyAllWindows()

    def _draw_help_overlay(self, frame: Any) -> None:
        """Render a compact two-column help overlay for all modes."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (24, 50), (w - 24, h - 24), (12, 12, 12), -1)
        cv2.addWeighted(overlay, 0.84, frame, 0.16, 0, frame)
        cv2.putText(frame, "Help & Shortcuts", (44, 76), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 229, 255), 2)
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

    def _draw_shell(self, frame: Any) -> None:
        """Draw dark-themed shell chrome and mode title."""

        import cv2  # type: ignore

        name = self.mode_manager.active_mode.name
        elapsed = time.time()
        h, w = frame.shape[:2]
        overlay = frame.copy()
        cv2.rectangle(overlay, (0, 0), (w, 52), (16, 16, 24), -1)
        if self.config.cinematic_hud_enabled:
            sweep_y = int((elapsed * 150) % h)
            cv2.line(overlay, (0, sweep_y), (w, sweep_y), (255, 180, 0), 1)
            cv2.rectangle(overlay, (10, 10), (w - 10, h - 10), (30, 120, 180), 1)
            core_center = (w - 44, 26)
            glow = int(150 + 105 * (0.5 + 0.5 * math.sin(elapsed * 3.2)))
            radius = 8 + int(5 * (0.5 + 0.5 * math.sin(elapsed * 2.6)))
            cv2.circle(overlay, core_center, 18, (30, 160, 255), 1)
            cv2.circle(overlay, core_center, radius, (40, glow, 255), -1)
        cv2.addWeighted(overlay, 0.65, frame, 0.35, 0, frame)
        cv2.putText(frame, f"{self.config.app_name} | Mode: {name}", (16, 34), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 229, 255), 2)
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

    def _handle_key(self, key: int, frame: Any) -> bool:
        """Handle global keyboard shortcuts and mode shortcuts."""

        if key in (27, ord("q")):
            return False

        active = self.mode_manager.active_mode
        if active.on_key(key):
            return True

        if key in (ord("h"), ord("H")):
            self.show_help = not self.show_help
            self.assistant.confirm("Toggling heads-up help.")
            return True

        typed = chr(key).lower() if 32 <= key <= 126 else ""
        if typed:
            previous = self.mode_manager.active_mode.name
            switched = self.mode_manager.switch_by_shortcut(typed)
            if switched is not None and switched.name != previous:
                self.assistant.confirm(f"Switching to {switched.name.replace('_', ' ')} mode.")

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
            self.assistant.confirm("Recording started.")
        elif key == ord("z"):
            self.recorder.stop_video()
            self.assistant.confirm("Recording stopped.")
        elif key == ord("r"):
            self._speak_status()
        elif key == ord("\r") and hasattr(active, "play_round"):
            active.play_round(0)

        function_map = {
            190: "F1",
            191: "F2",
            192: "F3",
            193: "F4",
            194: "F5",
            195: "F6",
            196: "F7",
            197: "F8",
            198: "F9",
            199: "F10",
        }
        if key in function_map:
            previous = self.mode_manager.active_mode.name
            switched = self.mode_manager.switch_by_shortcut(function_map[key])
            if switched is not None and switched.name != previous:
                self.assistant.confirm(f"Switching to {switched.name.replace('_', ' ')} mode.")

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
        if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)) == 0:
            return None
        percent = int(status.BatteryLifePercent)
        if percent < 0 or percent > 100:
            return None
        return percent
