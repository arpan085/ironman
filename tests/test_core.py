"""Focused tests for config and mode manager behavior."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import sys

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gesture_vision.config import AppConfig, load_config
from gesture_vision.core.base_mode import BaseMode
from gesture_vision.core.mode_manager import ModeManager
from gesture_vision.core.recorder import Recorder
from gesture_vision.core.smoothing import PointFilter
from gesture_vision.core.suit_ai import SuitAssistant
from gesture_vision.core.system_controls import is_pinch
from gesture_vision.modes.finger_keyboard import FingerKeyboardMode
from gesture_vision.modes.gesture_calculator import GestureCalculatorMode
from gesture_vision.modes.music_player import MusicPlayerMode
from gesture_vision.modes.common import resolve_package_path


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

    def test_load_config_parses_string_bool(self) -> None:
        """String booleans should be coerced correctly for config fields."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            path.write_text(json.dumps({"sidebar_enabled": "false"}), encoding="utf-8")
            cfg = load_config(path)
            self.assertFalse(cfg.sidebar_enabled)

    def test_load_config_supports_jarvis_fields(self) -> None:
        """New suit assistant config fields should load from JSON."""

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "cfg.json"
            path.write_text(
                json.dumps(
                    {
                        "wake_word": "JARVIS",
                        "startup_chime_enabled": "false",
                        "command_confirmations": ["Certainly, sir", "Engaging now"],
                    }
                ),
                encoding="utf-8",
            )
            cfg = load_config(path)
            self.assertEqual(cfg.wake_word, "jarvis")
            self.assertFalse(cfg.startup_chime_enabled)
            self.assertEqual(cfg.command_confirmations, ("Certainly, sir", "Engaging now"))


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

    def test_calculator_rejects_disallowed_tokens(self) -> None:
        """Calculator should block unsupported expression characters."""

        calc = GestureCalculatorMode()
        calc.expression = "__import__('os').system('echo bad')"
        calc.evaluate()
        self.assertEqual(calc.result, "Invalid")

    def test_is_pinch_and_recorder_state(self) -> None:
        """Pinch helper should detect close fingers while recorder reports unopened writer state."""

        class _Writer:
            def isOpened(self) -> bool:
                return False

        thumb = type("Point", (), {"x": 0.1, "y": 0.1})()
        index = type("Point", (), {"x": 0.11, "y": 0.11})()
        self.assertTrue(is_pinch(thumb, index, threshold=0.02))

        recorder = Recorder(Path("captures"))
        recorder.writer = _Writer()
        self.assertFalse(recorder.is_open())

    def test_music_player_uses_package_relative_default_dir(self) -> None:
        """Music mode should resolve asset directories relative to the package root."""

        player = MusicPlayerMode()
        self.assertEqual(player.music_dir, resolve_package_path("music"))

    def test_finger_keyboard_types_once_per_hover(self) -> None:
        """The keyboard should only type once when hovering over a key cell."""

        keyboard = FingerKeyboardMode()
        frame = np.zeros((200, 400, 3), dtype=np.uint8)
        landmarks = {"index_tip": type("Point", (), {"x": 0.05, "y": 0.5})()}
        keyboard.process(frame, landmarks, {})
        keyboard.process(frame, landmarks, {})
        self.assertEqual(keyboard.typed, "Q")

    def test_suit_assistant_parses_wake_word_commands(self) -> None:
        """Wake-word parser should route known directives to command kinds."""

        manager = ModeManager([_DummyMode("virtual_mouse", "7"), _DummyMode("performance_hud", "F10")])
        assistant = SuitAssistant(AppConfig(), manager)
        self.assertEqual(assistant.parse_command("jarvis"), assistant.parse_command("Jarvis"))
        self.assertEqual(assistant.parse_command("jarvis status").kind, "status_report")
        self.assertEqual(assistant.parse_command("jarvis virtual mouse").payload, "virtual_mouse")


if __name__ == "__main__":
    unittest.main()
