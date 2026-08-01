"""Main application orchestration for gesture suite."""

from __future__ import annotations

import logging
from pathlib import Path
import time
from typing import Any

from .config import AppConfig, load_config
from .core.hand_tracker import HandTracker
from .core.mode_manager import ModeManager
from .core.recorder import Recorder
from .logger import setup_logging
from .modes.air_drums import AirDrumsMode
from .modes.air_guitar import AirGuitarMode
from .modes.air_painter import AirPainterMode
from .modes.air_piano import AirPianoMode
from .modes.air_signature import AirSignatureMode
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
from .modes.gesture_snake import GestureSnakeMode
from .modes.hand_animation import HandAnimationEffectsMode
from .modes.image_viewer import ImageViewerMode
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
    """Map a waitKey code to an F1..F20 shortcut across backends.

    Windows OpenCV encodes function keys as ``VK << 16`` (F1 -> 0x00700000),
    X11/GTK builds return raw codes 65470..65489, and older highgui builds
    expose them as 190..209 after the low byte.
    """

    high = key >> 16
    if 0x70 <= high <= 0x83:
        return f"F{high - 0x70 + 1}"
    if 65470 <= key <= 65489:
        return f"F{key - 65470 + 1}"
    if 63236 <= key <= 63255:
        return f"F{key - 63236 + 1}"
    if 0 < key < 256 and 190 <= key <= 209:
        return f"F{key - 190 + 1}"
    return None


class GestureVisionApp:
    """Composes tracker, modes, UI, and camera loop."""

    def __init__(self, config: AppConfig | None = None) -> None:
        """Initialize application services and mode registry."""

        self.config = config or load_config()
        setup_logging()
        self.tracker = HandTracker(max_num_hands=2)
        self.mode_manager = ModeManager(
            [
                VirtualDrawingCanvasMode(),
                AirPainterMode(),
                FingerCounterMode(),
                RockPaperScissorsMode(),
                VolumeControllerMode(),
                BrightnessControllerMode(),
                VirtualMouseMode(),
                FingerKeyboardMode(),
                GestureCalculatorMode(),
                VirtualWhiteboardMode(),
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
            ]
        )
        self.recorder = Recorder(Path(self.config.record_output_dir))
        self.running = False
        self._show_help = False
        self._fps = 0.0

    def launch_sidebar(self) -> None:
        """Start optional sidebar with all shortcuts."""

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

        if self.config.sidebar_enabled:
            self.launch_sidebar()
        self.running = True
        start = time.time()
        frame_interval = 1.0 / max(1, self.config.target_fps)
        logger.info("%s started", self.config.app_name)

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
            landmarks = self.tracker.process(frame)
            context: dict[str, Any] = {
                "fps_target": self.config.target_fps,
                "elapsed": time.time() - start,
            }
            frame = self.mode_manager.active_mode.process(frame, landmarks, context)
            self._draw_shell(frame)
            self.recorder.write(frame)
            cv2.imshow(self.config.app_name, frame)

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
        cap.release()
        cv2.destroyAllWindows()
        self.running = False

    def _draw_shell(self, frame: Any) -> None:
        """Draw dark-themed shell chrome, status bar, and optional help overlay."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        name = self.mode_manager.active_mode.name
        cv2.rectangle(frame, (0, 0), (w, 42), (20, 20, 20), -1)
        cv2.putText(frame, f"{self.config.app_name} | Mode: {name}", (16, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 229, 255), 2)

        recording = self.recorder.is_recording()
        cv2.rectangle(frame, (0, h - 28), (w, h), (20, 20, 20), -1)
        status = f"FPS: {self._fps:4.0f}"
        if recording:
            status += " | REC"
        status += "  |  H=help"
        cv2.putText(frame, status, (12, h - 9), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (120, 255, 120) if recording else (180, 180, 180), 1)

        if self._show_help:
            overlay = frame.copy()
            cv2.rectangle(overlay, (0, 0), (w, h), (10, 10, 10), -1)
            frame[:] = cv2.addWeighted(frame, 0.35, overlay, 0.65, 0)
            cv2.putText(frame, "IRONMAN GESTURE SUITE - SHORTCUTS", (60, 70), cv2.FONT_HERSHEY_SIMPLEX, 0.85, (0, 229, 255), 2)
            y = 115
            cv2.putText(frame, "Modes (F1-F14):", (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
            y += 30
            for m in self.mode_manager.list_modes():
                line = f"  {m.shortcut:>4}  {m.name}"
                cv2.putText(frame, line, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (200, 200, 200), 1)
                y += 24
                if y > h - 60:
                    break
            y += 14
            for text in ("Global: Q/Esc=quit  S=snapshot  V=record  Z=stop  H=help", "Active mode keys: C=clear/restart  U=undo  E=eraser  P=style  X/G=next"):
                cv2.putText(frame, text, (60, y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 240, 140), 1)
                y += 26

    def _handle_key(self, key: int, frame: Any) -> bool:
        """Handle global keyboard shortcuts and mode shortcuts."""

        if key == -1:
            return True

        fkey = _resolve_fkey(key)
        if fkey:
            self.mode_manager.switch_by_shortcut(fkey)
            return True

        if key >= 256:
            return True

        if key in (27, ord("q")):
            return False

        active = self.mode_manager.active_mode
        typed = chr(key).lower() if 32 <= key <= 126 else ""

        if typed == "h":
            self._show_help = not self._show_help
            return True

        if hasattr(active, "on_key"):
            try:
                if active.on_key(key, typed):
                    return True
            except Exception:  # noqa: BLE001
                pass

        if typed:
            self.mode_manager.switch_by_shortcut(typed)

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
        elif key == ord("m") and hasattr(active, "next_effect"):
            active.next_effect()
        elif key == ord("s"):
            if hasattr(active, "snapshot"):
                active.snapshot()
            self.recorder.screenshot(frame)
        elif key == ord("v"):
            self.recorder.start_video(frame.shape[1], frame.shape[0], self.config.target_fps)
        elif key == ord("z"):
            self.recorder.stop_video()
        elif key == ord("\r") and hasattr(active, "play_round"):
            active.play_round()

        return True
