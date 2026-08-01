"""Tests for the F15-F20 feature modes (theremin, guitar, wand, etc.)."""

from __future__ import annotations

import tempfile
from pathlib import Path
import sys
import unittest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import numpy as np  # noqa: E402

from gesture_vision.app import _resolve_fkey  # noqa: E402
from gesture_vision.modes.air_guitar import AirGuitarMode, CHORDS  # noqa: E402
from gesture_vision.modes.air_signature import AirSignatureMode  # noqa: E402
from gesture_vision.modes.macro_pad import MacroPadMode, ACTIONS  # noqa: E402
from gesture_vision.modes.magic_wand import MagicWandMode  # noqa: E402
from gesture_vision.modes.magnifier import MagnifierMode  # noqa: E402
from gesture_vision.modes.theremin import ThereminMode, PENTATONIC  # noqa: E402


class _Tip:
    """Minimal normalized landmark stand-in."""

    def __init__(self, x: float, y: float) -> None:
        """Store normalized coordinates."""

        self.x = x
        self.y = y
        self.z = 0.0


def _frame():
    """Return a blank BGR frame."""

    return np.zeros((480, 640, 3), dtype=np.uint8)


def _hand(start_x: float, start_y: float, raised: int = 0) -> list[_Tip]:
    """Build a 21-point hand with a few raised fingers."""

    points = [_Tip(start_x + i * 0.01, start_y + 0.1) for i in range(21)]
    for tip in (8, 12, 16, 20)[:raised]:
        points[tip] = _Tip(points[tip].x, start_y - 0.05)
    return points


class FKeyFeatureTests(unittest.TestCase):
    """Validate F15-F20 mapping across backend encodings."""

    def test_windows_vk_shifted(self) -> None:
        """VK << 16 encodings (0x7E..0x83) map to F15..F20."""

        for i, key in enumerate(range(0x7E, 0x84)):
            self.assertEqual(_resolve_fkey(key << 16), f"F{15 + i}")

    def test_gtk_and_legacy(self) -> None:
        """Raw GTK and legacy low-byte codes map to F15..F20."""

        self.assertEqual(_resolve_fkey(65484), "F15")
        self.assertEqual(_resolve_fkey(65489), "F20")
        self.assertEqual(_resolve_fkey(204), "F15")
        self.assertEqual(_resolve_fkey(209), "F20")


class ThereminTests(unittest.TestCase):
    """Validate pitch stepping and volume mapping."""

    def test_note_stepping(self) -> None:
        """Raising the hand should move up the pentatonic scale."""

        theremin = ThereminMode()
        frame = _frame()
        theremin.process(frame, {"hands": [_hand(0.5, 0.2)], "handedness": ["Right"]}, {})
        low_step = theremin._current_step
        theremin.process(frame, {"hands": [_hand(0.5, 0.8)], "handedness": ["Right"]}, {})
        high_step = theremin._current_step
        self.assertIsNotNone(low_step)
        self.assertGreaterEqual(low_step, high_step)

    def test_two_hand_volume(self) -> None:
        """Two hands should drive the channel volume without crashing."""

        theremin = ThereminMode()
        frame = _frame()
        hands = [_hand(0.2, 0.5), _hand(0.8, 0.5)]
        out = theremin.process(frame, {"hands": hands, "handedness": ["Left", "Right"]}, {})
        self.assertEqual(out.shape, frame.shape)


class AirGuitarTests(unittest.TestCase):
    """Validate chord selection and strum crossing detection."""

    def test_chord_table(self) -> None:
        """Five chords should be defined for fingers 1-5."""

        self.assertEqual(sorted(CHORDS), [1, 2, 3, 4, 5])

    def test_strum_crossing(self) -> None:
        """Crossing the string line with the right hand should strum."""

        guitar = AirGuitarMode()
        frame = _frame()
        h = frame.shape[0]
        line_y = int(h * 0.55)
        left = _hand(0.2, 0.4, raised=2)
        above = _hand(0.5, (line_y - 80) / h)
        below = _hand(0.5, (line_y + 60) / h)
        guitar.process(frame, {"hands": [left, above], "handedness": ["Left", "Right"]}, {})
        guitar._cooldown = 0
        guitar.process(frame, {"hands": [left, below], "handedness": ["Left", "Right"]}, {})
        self.assertGreater(guitar._cooldown, 0)

    def test_chord_visual_no_hands(self) -> None:
        """Processing with no hands should keep the default chord."""

        guitar = AirGuitarMode()
        out = guitar.process(_frame(), {"hands": [], "handedness": []}, {})
        self.assertEqual(out.shape, _frame().shape)
        self.assertEqual(guitar.chord_count, 1)


class MagicWandTests(unittest.TestCase):
    """Validate particle emission."""

    def test_movement_spawns_particles(self) -> None:
        """Moving the fingertip should add particles to the system."""

        wand = MagicWandMode()
        frame = _frame()
        wand.process(frame, {"hands": [_hand(0.2, 0.2)], "index_tip": _Tip(0.2, 0.2)}, {})
        before = len(wand.particles)
        wand.process(frame, {"hands": [_hand(0.5, 0.5)], "index_tip": _Tip(0.5, 0.5)}, {})
        self.assertGreater(len(wand.particles), before)


class MagnifierTests(unittest.TestCase):
    """Validate zoom key handling and PiP rendering."""

    def test_zoom_keys(self) -> None:
        """+/- should adjust zoom and be consumed."""

        mag = MagnifierMode()
        base = mag.zoom
        self.assertTrue(mag.on_key(ord("+"), "+"))
        self.assertGreater(mag.zoom, base)
        self.assertTrue(mag.on_key(ord("-"), "-"))
        self.assertAlmostEqual(mag.zoom, base, places=3)

    def test_pip_render(self) -> None:
        """Rendering with a fingertip should not crash."""

        mag = MagnifierMode()
        out = mag.process(_frame(), {"hands": [_hand(0.3, 0.3)], "index_tip": _Tip(0.3, 0.3)}, {})
        self.assertEqual(out.shape, _frame().shape)


class MacroPadTests(unittest.TestCase):
    """Validate slot selection and single-hand confirm."""

    def test_keyboard_selection(self) -> None:
        """Keys 1-5 select a slot and Enter fires it."""

        pad = MacroPadMode()
        self.assertTrue(pad.on_key(ord("3"), "3"))
        self.assertEqual(pad.slot, 3)
        pad.on_key(ord("\r"), "\r")
        self.assertEqual(pad._triggered, ACTIONS[3][0])

    def test_single_hand_fist_confirm(self) -> None:
        """Showing 1-5 fingers then a fist should launch the slot."""

        pad = MacroPadMode()
        frame = _frame()
        pad.process(frame, {"hands": [_hand(0.3, 0.3, raised=2)], "handedness": ["Right"], "fingers": [2]}, {})
        for _ in range(4):
            pad.process(frame, {"hands": [_hand(0.3, 0.3, raised=0)], "handedness": ["Right"], "fingers": [0]}, {})
        self.assertEqual(pad._triggered, ACTIONS[2][0])


class AirSignatureTests(unittest.TestCase):
    """Validate drawing, saving, and clearing."""

    def test_draw_and_save(self) -> None:
        """Drawing strokes should persist and S should write a PNG."""

        with tempfile.TemporaryDirectory() as tmp:
            sig = AirSignatureMode(output_dir=str(Path(tmp) / "sig"))
            frame = _frame()
            for x in range(5):
                pt = _Tip(0.1 + x * 0.05, 0.5)
                sig.process(frame, {"hands": [_hand(0.1, 0.5, raised=1)], "index_tip": pt}, {})
            self.assertTrue(bool(sig.canvas.any()))
            self.assertTrue(sig.on_key(ord("s"), "s"))
            files = list(Path(tmp, "sig").glob("*.png"))
            self.assertEqual(len(files), 1)

    def test_clear(self) -> None:
        """Clear should empty the canvas."""

        sig = AirSignatureMode(output_dir=str(Path("tmp_none")))
        frame = _frame()
        sig.process(frame, {"hands": [_hand(0.1, 0.5, raised=1)], "index_tip": _Tip(0.1, 0.5)}, {})
        sig.clear()
        self.assertFalse(bool(sig.canvas.any()))


if __name__ == "__main__":
    unittest.main()
