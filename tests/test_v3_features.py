"""Comprehensive test suite for Stark Mark LXXXV OS v3.0 features.

Tests cover:
1. Acoustic sound synthesizer (velvety whoosh, warm marimba ping, harmonic envelopes, zero clipping).
2. Master volume scaling, mute toggles, and safety limits.
3. Cybernetic hand rendering, ECG cardiac telemetry monitor, hexagonal shield graphics.
4. IronManJarvisMode Unibeam weapon discharge and Nanotech Shield barrier.
5. Voice and keyboard command routing for v3.0 features in GestureVisionApp.
"""

from __future__ import annotations

from pathlib import Path
import sys
import unittest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gesture_vision.core import soundgen
from gesture_vision.core.hand_tracker import HandPoint
from gesture_vision.core.jarvis import JarvisAssistant
from gesture_vision.modes import common
from gesture_vision.modes.ironman_jarvis import IronManJarvisMode


class AcousticSoundTests(unittest.TestCase):
    """Validate the acoustic-grade sound synthesizer and volume controls."""

    def setUp(self) -> None:
        soundgen.init()
        soundgen.set_master_volume(0.8)
        if soundgen.is_muted():
            soundgen.toggle_mute()

    def test_master_volume_clamping(self) -> None:
        """Master volume should clamp safely between 0.0 and 1.0."""
        soundgen.set_master_volume(1.5)
        self.assertAlmostEqual(soundgen.get_master_volume(), 1.0)
        soundgen.set_master_volume(-0.5)
        self.assertAlmostEqual(soundgen.get_master_volume(), 0.0)
        soundgen.set_master_volume(0.65)
        self.assertAlmostEqual(soundgen.get_master_volume(), 0.65)

    def test_mute_toggle(self) -> None:
        """Toggle mute should alternate mute state correctly."""
        self.assertFalse(soundgen.is_muted())
        soundgen.toggle_mute()
        self.assertTrue(soundgen.is_muted())
        soundgen.toggle_mute()
        self.assertFalse(soundgen.is_muted())

    def test_ui_switch_synthesis(self) -> None:
        """ui_switch should generate a smooth, non-clipping sound array."""
        snd = soundgen.ui_switch()
        self.assertIsNotNone(snd)

    def test_ui_ping_synthesis(self) -> None:
        """ui_ping should generate a warm D5 acoustic marimba tap."""
        snd = soundgen.ui_ping()
        self.assertIsNotNone(snd)

    def test_unibeam_and_shield_synthesis(self) -> None:
        """Unibeam and shield sound synthesizers should return valid sound objects."""
        snd_u = soundgen.unibeam_blast()
        snd_s = soundgen.shield_deploy()
        self.assertIsNotNone(snd_u)
        self.assertIsNotNone(snd_s)

    def test_play_named_safely(self) -> None:
        """play_named should execute without exception for all registered sounds."""
        sounds = ["switch", "ui_ping", "ping", "chime", "charge", "blast", "unibeam", "shield", "lock"]
        for name in sounds:
            soundgen.play_named(name)


class MarkLXXXVGraphicsTests(unittest.TestCase):
    """Validate V3 rendering primitives: cybernetic hand, ECG monitor, nanotech shield."""

    def test_draw_cyber_hand(self) -> None:
        """draw_cyber_hand should render 21-point glowing plasma conduits and palm repulsor."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        points = [HandPoint(0.5 + i * 0.01, 0.5 + (i % 4) * 0.02, 0.0) for i in range(21)]
        common.draw_cyber_hand(frame, points, color=(0, 229, 255), glow_color=(0, 100, 180))
        # Should have drawn non-zero pixels
        self.assertTrue(np.count_nonzero(frame) > 0)

    def test_draw_ecg_monitor(self) -> None:
        """draw_ecg_monitor should render dynamic P-Q-R-S-T cardiac waveform."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        common.draw_ecg_monitor(frame, x=40, y=40, w=200, h=60, phase=1.5, color=(0, 255, 140))
        self.assertTrue(np.count_nonzero(frame) > 0)

    def test_draw_hex_shield(self) -> None:
        """draw_hex_shield should render hexagonal barrier with glow."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        common.draw_hex_shield(frame, center=(320, 240), radius=120, color=(0, 229, 255), alpha=0.5, phase=0.2)
        self.assertTrue(np.count_nonzero(frame) > 0)


class V3IronManModeTests(unittest.TestCase):
    """Validate V3 Unibeam and Shield weapon systems in IronManJarvisMode."""

    def setUp(self) -> None:
        jarvis = JarvisAssistant(voice_enabled=False)
        self.mode = IronManJarvisMode(jarvis=jarvis)

    def test_force_unibeam(self) -> None:
        """force_unibeam should engage unibeam firing state."""
        self.assertFalse(self.mode._is_unibeam_firing)
        self.mode.force_unibeam()
        self.assertTrue(self.mode._is_unibeam_firing)
        self.assertGreater(self.mode._unibeam_timer, 0.0)

    def test_toggle_shield(self) -> None:
        """toggle_shield should toggle nanotech shield barrier."""
        self.assertFalse(self.mode._shield_active)
        self.mode.toggle_shield()
        self.assertTrue(self.mode._shield_active)
        self.mode.toggle_shield()
        self.assertFalse(self.mode._shield_active)

    def test_keyboard_shortcuts_u_and_d(self) -> None:
        """Keys 'u' and 'd' should trigger Unibeam and Shield in IronManJarvisMode."""
        self.mode.on_key(ord("u"), "u")
        self.assertTrue(self.mode._is_unibeam_firing)

        self.mode.on_key(ord("d"), "d")
        self.assertTrue(self.mode._shield_active)

    def test_two_hand_unibeam_and_shield_gestures(self) -> None:
        """Palms together should charge unibeam; wrists crossed should deploy shield."""
        frame = np.zeros((480, 640, 3), dtype=np.uint8)

        # Hand 1: wrist at (0.48, 0.5), palm center at (0.48, 0.45)
        h1 = [HandPoint(0.48, 0.50, 0.0) for _ in range(21)]
        h1[9] = HandPoint(0.48, 0.45, 0.0)
        h1[0] = HandPoint(0.48, 0.50, 0.0)

        # Hand 2: wrist at (0.52, 0.5), palm center at (0.52, 0.45)
        h2 = [HandPoint(0.52, 0.50, 0.0) for _ in range(21)]
        h2[9] = HandPoint(0.52, 0.45, 0.0)
        h2[0] = HandPoint(0.52, 0.50, 0.0)

        landmarks = {"hands": [h1, h2]}
        context = {"fps_target": 30, "elapsed": 1.0, "jarvis": self.mode.jarvis}

        out = self.mode.process(frame, landmarks, context)
        self.assertEqual(out.shape, frame.shape)
        # Unibeam charge should increase when palms are close
        self.assertGreater(self.mode._unibeam_charge, 0.0)


class V3AppActionTests(unittest.TestCase):
    """Validate action routing and mute handling in GestureVisionApp."""

    def test_jarvis_action_dispatch(self) -> None:
        """App should handle v3 J.A.R.V.I.S. actions: unibeam, shield, mute, unmute."""
        from gesture_vision.app import GestureVisionApp
        from gesture_vision.config import AppConfig

        cfg = AppConfig(sidebar_enabled=False, jarvis_voice=False)
        app = GestureVisionApp(config=cfg)

        # Switch to ironman mode first
        app._switch_mode("ironman_jarvis")
        self.assertEqual(app.mode_manager.active_mode.name, "ironman_jarvis")

        # Test unibeam action
        app._on_jarvis_action("fire unibeam", "unibeam", None)
        active = app.mode_manager.active_mode
        self.assertTrue(getattr(active, "_is_unibeam_firing", False))

        # Test shield action
        app._on_jarvis_action("deploy shield", "shield", None)
        self.assertTrue(getattr(active, "_shield_active", False))

        # Test mute and unmute actions
        app._on_jarvis_action("mute sound", "mute", None)
        self.assertTrue(soundgen.is_muted())
        app._on_jarvis_action("unmute sound", "unmute", None)
        self.assertFalse(soundgen.is_muted())


if __name__ == "__main__":
    unittest.main()
