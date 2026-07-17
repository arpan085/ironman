"""Main application orchestration for gesture suite."""

from __future__ import annotations

from pathlib import Path
import time
from typing import Any

from .config import AppConfig, load_config
from .core.hand_tracker import HandTracker
from .core.mode_manager import ModeManager
from .core.recorder import Recorder
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
            ]
        )
        self.recorder = Recorder(Path(self.config.record_output_dir))
        self.running = False

    def launch_sidebar(self) -> None:
        """Start optional sidebar with all shortcuts."""

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
        self.running = True
        start = time.time()

        while self.running:
            ok, frame = cap.read()
            if not ok:
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

            key = cv2.waitKey(1) & 0xFF
            if not self._handle_key(key, frame):
                break

        self.recorder.stop_video()
        cap.release()
        cv2.destroyAllWindows()

    def _draw_shell(self, frame: Any) -> None:
        """Draw dark-themed shell chrome and mode title."""

        import cv2  # type: ignore

        name = self.mode_manager.active_mode.name
        cv2.rectangle(frame, (0, 0), (frame.shape[1], 42), (20, 20, 20), -1)
        cv2.putText(frame, f"{self.config.app_name} | Mode: {name}", (16, 27), cv2.FONT_HERSHEY_SIMPLEX, 0.62, (0, 229, 255), 2)

    def _handle_key(self, key: int, frame: Any) -> bool:
        """Handle global keyboard shortcuts and mode shortcuts."""

        if key in (27, ord("q")):
            return False

        typed = chr(key).lower() if 32 <= key <= 126 else ""
        if typed:
            self.mode_manager.switch_by_shortcut(typed)

        active = self.mode_manager.active_mode
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
        elif key == ord("z"):
            self.recorder.stop_video()
        elif key == ord("\r") and hasattr(active, "play_round"):
            active.play_round(0)

        if key == ord("f"):
            return False

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
            self.mode_manager.switch_by_shortcut(function_map[key])

        return True
