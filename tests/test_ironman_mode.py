"""Tests for IronManJarvisMode, extended hand tracking gestures, and v2.0 interactive HUD."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gesture_vision.app import GestureVisionApp, _resolve_fkey
from gesture_vision.config import load_config
from gesture_vision.core.hand_tracker import HandPoint, HandTracker
from gesture_vision.core.jarvis import JarvisAssistant
from gesture_vision.core.system_controls import get_brightness, get_volume
from gesture_vision.modes.ironman_jarvis import IronManJarvisMode, Particle


class _Tip:
    """Minimal normalized landmark stand-in."""

    def __init__(self, x: float, y: float) -> None:
        self.x = x
        self.y = y
        self.z = 0.0


def _build_hand(start_x: float, start_y: float, raised: int = 5) -> list[HandPoint]:
    """Build a 21-point hand."""

    points = [HandPoint(start_x + i * 0.01, start_y + 0.1, 0.0) for i in range(21)]
    tips = [4, 8, 12, 16, 20]
    for tip in tips[:raised]:
        points[tip] = HandPoint(points[tip].x, start_y - 0.05, 0.0)
    return points


class IronManModeTests(unittest.TestCase):
    """Validate IronManJarvisMode lifecycle and repulsor charging."""

    def test_mode_initialization(self) -> None:
        """Mode should have correct name and shortcut."""

        jarvis = JarvisAssistant(voice_enabled=False)
        mode = IronManJarvisMode(jarvis=jarvis)
        self.assertEqual(mode.name, "ironman_jarvis")
        self.assertEqual(mode.shortcut, "F21")
        self.assertEqual(mode._blast_count, 0)

    def test_f21_key_resolution(self) -> None:
        """F21 should correctly resolve across VK shifted, GTK raw, and legacy encodings."""

        # Windows VK << 16 for F21 (0x70 + 20 = 0x84)
        self.assertEqual(_resolve_fkey(0x84 << 16), "F21")
        # GTK raw code 65490
        self.assertEqual(_resolve_fkey(65490), "F21")
        # Legacy low-byte 210
        self.assertEqual(_resolve_fkey(210), "F21")

    def test_process_blank_frame(self) -> None:
        """Processing a blank frame without hands should not crash."""

        jarvis = JarvisAssistant(voice_enabled=False)
        mode = IronManJarvisMode(jarvis=jarvis)
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        landmarks = {"hands": [], "is_open_palm": False, "palm_center": None}
        out = mode.process(frame, landmarks, {})
        self.assertEqual(out.shape, frame.shape)

    def test_repulsor_charge_and_blast(self) -> None:
        """Open palm should charge the repulsor capacitor and trigger blast."""

        jarvis = JarvisAssistant(voice_enabled=False)
        mode = IronManJarvisMode(jarvis=jarvis)
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)

        # Feed open palm for several frames until 100% charge triggers blast
        landmarks = {
            "hands": [_build_hand(0.5, 0.5, 5)],
            "is_open_palm": True,
            "palm_center": HandPoint(0.5, 0.5, 0.0),
        }

        for _ in range(28):
            mode.process(frame, landmarks, {})

        self.assertGreater(mode._blast_count, 0)

    def test_manual_keys(self) -> None:
        """Manual blast (R), clear (C), and status (S) keys should be handled."""

        jarvis = JarvisAssistant(voice_enabled=False)
        mode = IronManJarvisMode(jarvis=jarvis)

        # Manual blast
        self.assertTrue(mode.on_key(ord("r"), "r"))
        self.assertEqual(mode._blast_count, 1)

        # Clear blast count
        self.assertTrue(mode.on_key(ord("c"), "c"))
        self.assertEqual(mode._blast_count, 0)

        # Status report
        self.assertTrue(mode.on_key(ord("s"), "s"))

        # Typing mode
        self.assertTrue(mode.on_key(ord("t"), "t"))
        self.assertTrue(mode._typing_mode)

        # Type chars
        mode.on_key(ord("h"), "h")
        mode.on_key(ord("i"), "i")
        self.assertEqual(mode._input_buffer, "hi")

        # Esc exits typing mode
        mode.on_key(27, "")
        self.assertFalse(mode._typing_mode)

    def test_particle_physics(self) -> None:
        """Particles should update position and die after lifetime expires."""

        p = Particle(x=10.0, y=10.0, vx=50.0, vy=50.0, life=0.05, color=(0, 229, 255))
        alive = p.update(0.02)
        self.assertTrue(alive)
        self.assertGreater(p.x, 10.0)
        alive2 = p.update(0.05)
        self.assertFalse(alive2)


class InteractiveHUDTests(unittest.TestCase):
    """Validate v2.0 boot sequence, mouse clicks, and on-screen controls."""

    def test_boot_sequence_and_finish(self) -> None:
        """Boot screen should render and transition cleanly."""

        cfg = load_config()
        cfg.sidebar_enabled = False
        app = GestureVisionApp(cfg)
        self.assertTrue(app._in_boot_sequence)

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        app._draw_boot_screen(frame)
        self.assertGreaterEqual(app._boot_progress, 0.0)

        app._finish_boot()
        self.assertFalse(app._in_boot_sequence)

    def test_dock_buttons_and_drawer(self) -> None:
        """On-screen dock buttons and mode drawer should handle clicks."""

        cfg = load_config()
        cfg.sidebar_enabled = False
        app = GestureVisionApp(cfg)
        app._finish_boot()

        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        app._draw_shell(frame)

        # Total dock buttons registered
        self.assertGreaterEqual(len(app._buttons), 8)

        # Click JARVIS toggle button
        j_btn = next(b for b in app._buttons if b.id == "toggle_jarvis")
        initial_voice = app.jarvis.voice.enabled
        app._handle_mouse_click(j_btn.x + 2, j_btn.y + 2)
        self.assertNotEqual(app.jarvis.voice.enabled, initial_voice)

        # Click Mode Drawer button
        drawer_btn = next(b for b in app._buttons if b.id == "toggle_modes")
        app._handle_mouse_click(drawer_btn.x + 2, drawer_btn.y + 2)
        self.assertTrue(app._mode_drawer_open)

        # Re-render shell with open drawer
        app._draw_shell(frame)
        drawer_cards = [b for b in app._buttons if b.category == "drawer"]
        self.assertEqual(len(drawer_cards), 31)

        # Click Iron Man mode from drawer
        im_card = next(b for b in drawer_cards if b.id == "ironman_jarvis")
        app._handle_mouse_click(im_card.x + 2, im_card.y + 2)
        self.assertEqual(app.mode_manager.active_mode.name, "ironman_jarvis")
        self.assertFalse(app._mode_drawer_open)

    def test_cycle_modes(self) -> None:
        """_cycle_mode should advance and wrap correctly."""

        cfg = load_config()
        cfg.sidebar_enabled = False
        app = GestureVisionApp(cfg)
        app._finish_boot()

        first_mode = app.mode_manager.active_mode.name
        app._cycle_mode(1)
        self.assertNotEqual(app.mode_manager.active_mode.name, first_mode)
        app._cycle_mode(-1)
        self.assertEqual(app.mode_manager.active_mode.name, first_mode)


class SystemControlsTests(unittest.TestCase):
    """Validate system control getters."""

    def test_get_volume_and_brightness(self) -> None:
        """get_volume and get_brightness should return integers in 0-100 range."""

        vol = get_volume()
        self.assertIsInstance(vol, int)
        self.assertGreaterEqual(vol, 0)
        self.assertLessEqual(vol, 100)

        bright = get_brightness()
        self.assertIsInstance(bright, int)
        self.assertGreaterEqual(bright, 0)
        self.assertLessEqual(bright, 100)


if __name__ == "__main__":
    unittest.main()
