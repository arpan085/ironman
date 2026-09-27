"""Tests for the newly added F11-F14 modes and extended key resolution."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from gesture_vision.app import _resolve_fkey  # noqa: E402
from gesture_vision.modes.air_drums import AirDrumsMode  # noqa: E402
from gesture_vision.modes.air_piano import AirPianoMode  # noqa: E402
from gesture_vision.modes.gesture_snake import GestureSnakeMode  # noqa: E402
from gesture_vision.modes.slide_controller import SlideControllerMode  # noqa: E402


class _Tip:
    """Minimal normalized landmark stand-in."""

    def __init__(self, x: float, y: float) -> None:
        """Store normalized coordinates."""

        self.x = x
        self.y = y
        self.z = 0.0


class FKeyResolutionTests(unittest.TestCase):
    """Validate F11-F14 mapping across backend encodings."""

    def test_windows_vk_shifted(self) -> None:
        """VK << 16 encodings (0x7A..0x7D) map to F11..F14."""

        for i, key in enumerate(range(0x7A, 0x7E)):
            self.assertEqual(_resolve_fkey(key << 16), f"F{11 + i}")

    def test_gtk_raw_codes(self) -> None:
        """Raw GTK codes 65480..65483 map to F11..F14."""

        for i, key in enumerate(range(65480, 65484)):
            self.assertEqual(_resolve_fkey(key), f"F{11 + i}")

    def test_legacy_low_byte(self) -> None:
        """Legacy codes 200..203 map to F11..F14."""

        for i, key in enumerate(range(200, 204)):
            self.assertEqual(_resolve_fkey(key), f"F{11 + i}")

    def test_printable_key_not_fkey(self) -> None:
        """Printable letters should never resolve to a function key."""

        self.assertIsNone(_resolve_fkey(ord("q")))
        self.assertIsNone(_resolve_fkey(ord("h")))


class GestureSnakeTests(unittest.TestCase):
    """Validate snake reset and movement growth."""

    def test_reset_initializes(self) -> None:
        """Reset should clear the body and score."""

        snake = GestureSnakeMode()
        snake.body = [(1, 1), (2, 2)]
        snake.score = 5
        snake.game_over = True
        snake.reset()
        self.assertEqual(snake.body, [])
        self.assertEqual(snake.score, 0)
        self.assertFalse(snake.game_over)

    def test_process_grows_body(self) -> None:
        """Moving the fingertip should extend the snake body."""

        snake = GestureSnakeMode()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        snake.process(frame, {"index_tip": _Tip(0.3, 0.3)}, {})
        snake.process(frame, {"index_tip": _Tip(0.4, 0.3)}, {})
        self.assertGreaterEqual(len(snake.body), 1)

    def test_clear_restarts(self) -> None:
        """The global C key should restart the game."""

        snake = GestureSnakeMode()
        snake.score = 9
        snake.clear()
        self.assertEqual(snake.score, 0)


class AirPianoTests(unittest.TestCase):
    """Validate keyboard note triggering."""

    def test_on_key_number_plays_note(self) -> None:
        """Keys 1-8 should map to notes and be consumed."""

        piano = AirPianoMode()
        self.assertTrue(piano.on_key(ord("1"), "1"))
        self.assertGreaterEqual(piano._cooldowns["C4"], 0)

    def test_on_key_unrelated_ignored(self) -> None:
        """Non-note keys should not be consumed."""

        piano = AirPianoMode()
        self.assertFalse(piano.on_key(ord("p"), "p"))

    def test_process_with_tip(self) -> None:
        """Processing a hand frame should not crash."""

        piano = AirPianoMode()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        out = piano.process(frame, {"index_tip": _Tip(0.1, 0.9)}, {})
        self.assertEqual(out.shape, frame.shape)


class AirDrumsTests(unittest.TestCase):
    """Validate pad hits and cooldown decrement."""

    def test_process_hit_and_cooldown(self) -> None:
        """Hitting a pad should flash it and set a cooldown."""

        drums = AirDrumsMode()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        drums.process(frame, {"index_tip": None}, {})
        x, y, pw, ph, kind, _ = drums.pads[0]
        out = drums.process(frame, {"index_tip": _Tip((x + 5) / 640, (y + 5) / 480)}, {})
        self.assertEqual(out.shape, frame.shape)
        self.assertGreater(drums._cooldowns[kind], 0)
        drums.process(frame, {"index_tip": None}, {})
        self.assertLessEqual(drums._cooldowns[kind], 11)


class SlideControllerTests(unittest.TestCase):
    """Validate swipe-based slide navigation."""

    def test_swipe_advances_slide(self) -> None:
        """A rightward swipe should advance to the next slide."""

        controller = SlideControllerMode()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        controller._cooldown = 0
        controller.process(frame, {"index_tip": _Tip(0.2, 0.5)}, {})
        for _ in range(3):
            controller._cooldown = 0
            controller.process(frame, {"index_tip": _Tip(0.8, 0.5)}, {})
        self.assertGreater(controller.slide, 1)

    def test_key_toggles_ppt(self) -> None:
        """The P key should toggle external presentation control."""

        controller = SlideControllerMode()
        self.assertTrue(controller.on_key(ord("p"), "p"))
        self.assertTrue(controller.control_ppt)
        self.assertTrue(controller.on_key(ord("p"), "p"))
        self.assertFalse(controller.control_ppt)


if __name__ == "__main__":
    unittest.main()
