"""Focused tests for config and mode manager behavior."""

from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
import sys
import types
from unittest.mock import patch

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gesture_vision.config import AppConfig, load_config
from gesture_vision.app import GestureVisionApp
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

    def test_suit_assistant_degrades_without_pyaudio(self) -> None:
        """Assistant start should degrade gracefully when microphone backend is unavailable."""

        manager = ModeManager([_DummyMode("virtual_mouse", "7")])
        with patch.object(SuitAssistant, "_init_tts", lambda self: None):
            assistant = SuitAssistant(AppConfig(), manager)
        fake_sr = types.SimpleNamespace(
            Recognizer=lambda: object(),
            Microphone=lambda: (_ for _ in ()).throw(AttributeError("Could not find PyAudio")),
            WaitTimeoutError=Exception,
        )
        with patch.dict(sys.modules, {"speech_recognition": fake_sr}):
            assistant.start()
        self.assertFalse(assistant.listening)
        self.assertIsNone(assistant.poll_command())


class AppBehaviorTests(unittest.TestCase):
    """Validate app-level splash and reset behavior."""

    def test_splash_flag_can_be_disabled_by_override(self) -> None:
        """CLI override should disable splash even when config enables it."""

        cfg = AppConfig(show_splash_screen=True, assistant_enabled=False)
        app = GestureVisionApp(config=cfg, show_splash_override=False)
        self.assertFalse(app.show_splash_screen)

    def test_soft_reset_reinitializes_active_mode_and_counters(self) -> None:
        """Global reset should rebuild active mode state without restarting app process."""

        cfg = AppConfig(show_splash_screen=False, assistant_enabled=False)
        app = GestureVisionApp(config=cfg)
        app.mode_manager.switch("finger_keyboard")
        mode_before = app.mode_manager.active_mode
        setattr(mode_before, "typed", "IRON")
        app.fps_live = 61.2
        app.cpu_load = 1.7
        app.temperature_c = 52.5
        app._reset_active_mode()
        mode_after = app.mode_manager.active_mode
        self.assertEqual(mode_after.name, "finger_keyboard")
        self.assertNotEqual(id(mode_before), id(mode_after))
        self.assertEqual(getattr(mode_after, "typed", ""), "")
        self.assertEqual(app.fps_live, 0.0)
        self.assertEqual(app.cpu_load, 0.0)
        self.assertEqual(app.temperature_c, 0.0)

    def test_quit_keys_are_handled_globally_first(self) -> None:
        """Esc and Q should always return False from global key handler."""

        cfg = AppConfig(show_splash_screen=False, assistant_enabled=False)
        app = GestureVisionApp(config=cfg)
        frame = np.zeros((200, 300, 3), dtype=np.uint8)
        self.assertFalse(app._handle_key(27, frame))
        self.assertFalse(app._handle_key(ord("q"), frame))
        self.assertFalse(app._handle_key(ord("Q"), frame))

    def test_mode_specific_r_consumption_blocks_global_reset(self) -> None:
        """Global reset should not run when active mode consumes R/r key."""

        cfg = AppConfig(show_splash_screen=False, assistant_enabled=False)
        app = GestureVisionApp(config=cfg)
        app.mode_manager.switch("image_viewer")
        calls = {"reset": 0}
        original = app._reset_active_mode
        app._reset_active_mode = lambda: calls.__setitem__("reset", calls["reset"] + 1)
        frame = np.zeros((200, 300, 3), dtype=np.uint8)
        app._handle_key(ord("r"), frame)
        app._reset_active_mode = original
        self.assertEqual(calls["reset"], 0)


if __name__ == "__main__":
    unittest.main()
