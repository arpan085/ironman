"""Focused tests for config and mode manager behavior."""

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
from gesture_vision.core.mode_manager import ModeManager
from gesture_vision.core.smoothing import PointFilter
from gesture_vision.modes.gesture_calculator import GestureCalculatorMode


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


if __name__ == "__main__":
    unittest.main()
