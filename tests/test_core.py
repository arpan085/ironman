"""Focused tests for config, mode manager, and core mode behaviors."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gesture_vision.config import load_config
from gesture_vision.core.base_mode import BaseMode
from gesture_vision.core.hand_tracker import HandPoint
from gesture_vision.core.mode_manager import ModeManager
from gesture_vision.core.smoothing import PointFilter
from gesture_vision.core.system_controls import distance, normalize_percentage
from gesture_vision.modes.drawing_canvas import VirtualDrawingCanvasMode
from gesture_vision.modes.finger_keyboard import FingerKeyboardMode
from gesture_vision.modes.gesture_calculator import GestureCalculatorMode
from gesture_vision.modes.gesture_games import GestureGamesMode
from gesture_vision.modes.image_viewer import ImageViewerMode
from gesture_vision.modes.music_player import MusicPlayerMode
from gesture_vision.modes.virtual_whiteboard import VirtualWhiteboardMode


class _DummyMode(BaseMode):
    """Minimal concrete mode for manager tests."""

    def __init__(self, name: str, shortcut: str) -> None:
        """Assign name and shortcut."""

        self.name = name
        self.shortcut = shortcut
        self.entered = 0
        self.exited = 0

    def on_enter(self) -> None:
        """Increment enter counter."""

        self.entered += 1

    def on_exit(self) -> None:
        """Increment exit counter."""

        self.exited += 1

    def process(self, frame, landmarks, context):  # noqa: ANN001
        """Return frame unchanged."""

        return frame


class _Tip:
    """Minimal normalized landmark stand-in for finger_xy."""

    def __init__(self, x: float, y: float) -> None:
        """Store normalized coordinates."""

        self.x = x
        self.y = y
        self.z = 0.0


class ConfigTests(unittest.TestCase):
    """Validate configuration loading behavior."""

    def test_load_config_defaults_and_overrides(self) -> None:
        """Config loader should apply defaults and valid overrides."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            path.write_text(json.dumps({"target_fps": 55, "draw_color": [1, 2, 3]}), encoding="utf-8")
            cfg = load_config(path)
            self.assertEqual(cfg.target_fps, 55)
            self.assertEqual(cfg.draw_color, (1, 2, 3))

    def test_load_config_clamps_absurd_values(self) -> None:
        """Config loader should clamp invalid window/FPS values."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            path.write_text(json.dumps({"target_fps": -5, "window_width": 0}), encoding="utf-8")
            cfg = load_config(path)
            self.assertEqual(cfg.target_fps, 1)
            self.assertEqual(cfg.window_width, 320)


class ManagerTests(unittest.TestCase):
    """Validate mode manager switching behavior."""

    def test_switch_and_shortcut(self) -> None:
        """Switch should trigger enter/exit lifecycle hooks."""

        m1 = _DummyMode("one", "1")
        m2 = _DummyMode("two", "2")
        manager = ModeManager([m1, m2])
        self.assertEqual(manager.active_mode.name, "one")
        manager.switch("two")
        self.assertEqual(manager.active_mode.name, "two")
        self.assertEqual(m1.exited, 1)
        manager.switch_by_shortcut("1")
        self.assertEqual(manager.active_mode.name, "one")


class UtilityTests(unittest.TestCase):
    """Validate utility and security-sensitive logic."""

    def test_point_filter_smoothing(self) -> None:
        """Point filter should return integer smoothed points."""

        filt = PointFilter(alpha=0.5)
        self.assertEqual(filt.apply(10, 10), (10, 10))
        self.assertEqual(filt.apply(20, 20), (15, 15))

    def test_distance_and_normalize(self) -> None:
        """Distance mapping should clamp into the 0-100 range."""

        self.assertEqual(normalize_percentage(0.0), 0)
        self.assertEqual(normalize_percentage(0.99), 100)
        self.assertEqual(distance(_Tip(0, 0), _Tip(3, 4)), 5.0)

    def test_calculator_rejects_disallowed_tokens(self) -> None:
        """Calculator should block unsupported expression characters."""

        calc = GestureCalculatorMode()
        calc.expression = "__import__('os').system('echo bad')"
        calc.evaluate()
        self.assertEqual(calc.result, "Invalid")

    def test_calculator_accepts_safe_expression(self) -> None:
        """Calculator should evaluate whitelisted arithmetic."""

        calc = GestureCalculatorMode()
        calc.on_key(ord("1"), "1")
        calc.on_key(ord("+"), "+")
        calc.on_key(ord("2"), "2")
        calc.on_key(ord("="), "=")
        self.assertEqual(calc.result, "3")

    def test_calculator_backspace_and_clear(self) -> None:
        """Calculator should support backspace and clear."""

        calc = GestureCalculatorMode()
        calc.on_key(ord("5"), "5")
        calc.on_key(8, "")
        self.assertEqual(calc.expression, "")
        calc.on_key(ord("7"), "7")
        calc.clear()
        self.assertEqual(calc.expression, "")


class FingerCountingTests(unittest.TestCase):
    """Validate handedness-aware finger counting."""

    def test_right_hand_thumb_up(self) -> None:
        """Right hand thumb tip on the right counts as raised."""

        from gesture_vision.core.hand_tracker import HandTracker

        points = [
            HandPoint(0.0, 0.0, 0.0),   # wrist
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.4, 0.5, 0.0),   # thumb IP
            HandPoint(0.6, 0.5, 0.0),   # thumb tip (right of IP)
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.3, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.2, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.3, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.2, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.3, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.2, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.3, 0.0),
            HandPoint(0.0, 0.0, 0.0),
            HandPoint(0.0, 0.2, 0.0),
        ]
        count = HandTracker._count_fingers(None, points, "Right")
        self.assertEqual(count, 5)

    def test_left_hand_thumb_up(self) -> None:
        """Left hand thumb tip on the left counts as raised."""

        from gesture_vision.core.hand_tracker import HandTracker

        points = [HandPoint(0.0, 0.0, 0.0) for _ in range(21)]
        points[3] = HandPoint(0.6, 0.5, 0.0)
        points[4] = HandPoint(0.4, 0.5, 0.0)
        for i, tip in enumerate([8, 12, 16, 20]):
            points[tip] = HandPoint(0.0, 0.2, 0.0)
            points[tip - 2] = HandPoint(0.0, 0.4, 0.0)
        count = HandTracker._count_fingers(None, points, "Left")
        self.assertEqual(count, 5)


class ModeBehaviorTests(unittest.TestCase):
    """Validate mode-specific behaviors."""

    def test_finger_keyboard_type_and_backspace(self) -> None:
        """Keyboard buffer should append and backspace correctly."""

        kb = FingerKeyboardMode()
        kb.type_key("A")
        kb.type_key("B")
        self.assertEqual(kb.typed, "AB")
        kb.type_key("<")
        self.assertEqual(kb.typed, "A")
        kb.clear()
        self.assertEqual(kb.typed, "")

    def test_image_viewer_navigation(self) -> None:
        """Viewer should cycle through a temp image directory."""

        with tempfile.TemporaryDirectory() as tmp:
            for i in range(3):
                Path(tmp, f"img{i}.png").write_bytes(b"\x00")
            viewer = ImageViewerMode(tmp)
            self.assertEqual(len(viewer.paths), 3)
            viewer.next()
            self.assertEqual(viewer.index, 1)
            viewer.on_key(ord("["), "[")
            self.assertEqual(viewer.index, 0)
            viewer.on_key(ord("+"), "+")
            self.assertGreater(viewer.zoom, 1.0)
            viewer.on_key(ord("r"), "r")
            self.assertEqual(viewer.zoom, 1.0)

    def test_music_player_on_key_without_tracks(self) -> None:
        """Transport keys should be safe with no audio files."""

        with tempfile.TemporaryDirectory() as tmp:
            player = MusicPlayerMode(tmp)
            self.assertTrue(player.on_key(ord("n"), "n"))
            self.assertTrue(player.on_key(32, ""))
            self.assertFalse(player.is_playing)

    def test_games_cycle_and_score(self) -> None:
        """Games should cycle modes and score balloon pops."""

        import numpy as np

        games = GestureGamesMode()
        games.next_game()
        self.assertEqual(games.mode, "balloon")
        games.next_game()
        self.assertEqual(games.mode, "catch")
        games.next_game()
        self.assertEqual(games.mode, "maze")
        games.mode = "balloon"
        games.balloons = [[100, 100, 28]]
        games._update_balloon(np.zeros((300, 400, 3), dtype=np.uint8), (100, 100))
        self.assertEqual(games.score, 1)

    def test_drawing_canvas_undo(self) -> None:
        """Canvas snapshot on stroke start should make undo work."""

        import numpy as np

        mode = VirtualDrawingCanvasMode()
        frame = np.zeros((100, 100, 3), dtype=np.uint8)
        mode.process(frame, {"index_tip": _Tip(0.2, 0.2)}, {})
        mode.process(frame, {"index_tip": _Tip(0.5, 0.5)}, {})
        self.assertTrue(bool(mode.canvas.any()))
        mode.undo()
        self.assertFalse(bool(mode.canvas.any()))

    def test_whiteboard_eraser_and_clear(self) -> None:
        """Whiteboard should clear and support eraser strokes."""

        import numpy as np

        mode = VirtualWhiteboardMode()
        frame = np.ones((100, 100, 3), dtype=np.uint8) * 255
        mode.process(frame, {"index_tip": _Tip(0.2, 0.2)}, {})
        mode.process(frame, {"index_tip": _Tip(0.5, 0.5)}, {})
        self.assertTrue((mode.board < 255).any())
        mode.clear()
        self.assertFalse((mode.board < 255).any())


if __name__ == "__main__":
    unittest.main()
