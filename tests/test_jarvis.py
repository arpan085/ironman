"""Tests for J.A.R.V.I.S. AI engine, offline command parsing, and Gemini integration."""

from __future__ import annotations

from pathlib import Path
import sys
import unittest
import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from gesture_vision.core.jarvis import GeminiClient, JarvisAssistant, JarvisVoice
from gesture_vision.core import soundgen


class JarvisCoreTests(unittest.TestCase):
    """Validate core J.A.R.V.I.S. assistant and Gemini client logic."""

    def test_gemini_client_configuration(self) -> None:
        """Client should correctly report configured status."""

        client_unconfigured = GeminiClient()
        self.assertFalse(client_unconfigured.is_configured)

        client_configured = GeminiClient(api_key="test_api_key_123", model="gemini-3.8-flash")
        self.assertTrue(client_configured.is_configured)
        self.assertEqual(client_configured.model, "gemini-3.8-flash")

    def test_gemini_unconfigured_error(self) -> None:
        """Calling generate without an API key should raise ValueError."""

        client = GeminiClient(api_key="")
        with self.assertRaises(ValueError):
            client.generate("hello")

    def test_jarvis_offline_mode_switching(self) -> None:
        """Offline parser should correctly parse mode switch requests."""

        jarvis = JarvisAssistant(voice_enabled=False)

        # Drawing mode
        text, action, arg = jarvis._process_query("switch to drawing mode", None)
        self.assertEqual(action, "switch_mode")
        self.assertEqual(arg, "virtual_drawing_canvas")
        self.assertIn("Drawing", text)

        # Snake game
        text, action, arg = jarvis._process_query("activate snake game", None)
        self.assertEqual(action, "switch_mode")
        self.assertEqual(arg, "gesture_snake")

        # Guitar mode
        text, action, arg = jarvis._process_query("launch guitar mode", None)
        self.assertEqual(action, "switch_mode")
        self.assertEqual(arg, "air_guitar")

        # Repulsor / Iron Man mode
        text, action, arg = jarvis._process_query("activate repulsor", None)
        self.assertEqual(action, "switch_mode")
        self.assertEqual(arg, "ironman_jarvis")

    def test_jarvis_offline_system_actions(self) -> None:
        """Offline parser should correctly dispatch screenshot, record, clear, undo, and volume."""

        jarvis = JarvisAssistant(voice_enabled=False)

        # Screenshot
        _, action, _ = jarvis._process_query("take a screenshot please", None)
        self.assertEqual(action, "screenshot")

        # Start recording
        _, action, _ = jarvis._process_query("start recording flight video", None)
        self.assertEqual(action, "record_start")

        # Stop recording
        _, action, _ = jarvis._process_query("stop recording", None)
        self.assertEqual(action, "record_stop")

        # Clear
        _, action, _ = jarvis._process_query("clear active canvas", None)
        self.assertEqual(action, "clear")

        # Undo
        _, action, _ = jarvis._process_query("undo previous stroke", None)
        self.assertEqual(action, "undo")

        # Volume
        _, action, _ = jarvis._process_query("volume up", None)
        self.assertEqual(action, "volume_up")

        # Brightness
        _, action, _ = jarvis._process_query("brightness down", None)
        self.assertEqual(action, "brightness_down")

        # Status report
        text, action, _ = jarvis._process_query("status report", None)
        self.assertEqual(action, "status")
        self.assertIn("Mark LXXXV", text)

    def test_jarvis_conversational_responses(self) -> None:
        """Jarvis should answer basic conversational questions in character."""

        jarvis = JarvisAssistant(voice_enabled=False)

        resp = jarvis._offline_conversation("who are you?")
        self.assertIn("J.A.R.V.I.S.", resp)

        resp = jarvis._offline_conversation("hello")
        self.assertIn("Sir", resp)

    def test_jarvis_voice_waveform_simulation(self) -> None:
        """JarvisVoice should generate valid waveform arrays for HUD rendering."""

        voice = JarvisVoice(enabled=False)
        wave = voice.get_waveform(16)
        self.assertEqual(len(wave), 16)
        for v in wave:
            self.assertGreaterEqual(v, 0.0)
            self.assertLessEqual(v, 1.0)

    def test_jarvis_voice_clip_matching(self) -> None:
        """JarvisVoice should match common tactical phrases to pre-rendered clips."""

        voice = JarvisVoice(enabled=False)
        self.assertEqual(voice._match_predefined_clip("Mark eighty-five systems operational"), "online")
        self.assertEqual(voice._match_predefined_clip("Switching to Iron Man tactical mode"), "switch_ironman")
        self.assertEqual(voice._match_predefined_clip("Virtual drawing canvas active, Sir."), "switch_drawing")
        self.assertEqual(voice._match_predefined_clip("Capacitors charging to one point two gigawatts"), "repulsor_charge")
        self.assertEqual(voice._match_predefined_clip("Repulsor discharged, Sir."), "repulsor_fire")
        self.assertEqual(voice._match_predefined_clip("Tactical snapshot captured and archived"), "screenshot")
        self.assertEqual(voice._match_predefined_clip("Flight recorder engaged, Sir."), "record_start")
        self.assertEqual(voice._match_predefined_clip("Workspace buffer purged, Sir."), "clear")

    def test_jarvis_ear_initialization_and_control(self) -> None:
        """JarvisEar should initialize and handle start/stop controls."""

        jarvis = JarvisAssistant(voice_enabled=False)
        self.assertTrue(hasattr(jarvis, "ear"))
        self.assertIsNotNone(jarvis.ear)

        # Toggle ear
        jarvis.ear.stop()
        self.assertFalse(jarvis.ear.is_listening)
        self.assertEqual(jarvis.ear.status_text, "MUTED")

    def test_jarvis_action_handler_callback(self) -> None:
        """Jarvis should invoke registered action handler when commands are recognized."""

        jarvis = JarvisAssistant(voice_enabled=False)
        dispatched_actions: list[tuple[str, str | None]] = []

        jarvis.set_action_handler(lambda action, arg: dispatched_actions.append((action, arg)))

        # Process a local command
        text, action, arg = jarvis._process_query("switch to air guitar", None)
        self.assertEqual(action, "switch_mode")
        self.assertEqual(arg, "air_guitar")

        # Tactical blast command
        text, action, _ = jarvis._process_query("Jarvis fire repulsor blast", None)
        self.assertEqual(action, "blast")
        self.assertIn("Repulsor discharged", text)

        # Tactical scan command
        text, action, _ = jarvis._process_query("Jarvis scan the room", None)
        self.assertEqual(action, "scan")
        self.assertIn("visual scan", text)


class SoundSynthesisTests(unittest.TestCase):
    """Validate Iron Man and J.A.R.V.I.S. audio effect synthesis."""

    def test_repulsor_charge_sound(self) -> None:
        """Repulsor charge sound should synthesize without error."""

        sound = soundgen.repulsor_charge(0.2)
        self.assertIsNotNone(sound)

    def test_repulsor_blast_sound(self) -> None:
        """Repulsor blast sound should synthesize without error."""

        sound = soundgen.repulsor_blast(0.2)
        self.assertIsNotNone(sound)

    def test_jarvis_chime_sound(self) -> None:
        """Jarvis chime sound should synthesize without error."""

        sound = soundgen.jarvis_chime(0.2)
        self.assertIsNotNone(sound)

    def test_target_lock_sound(self) -> None:
        """Target lock sound should synthesize without error."""

        sound = soundgen.target_lock(0.1)
        self.assertIsNotNone(sound)

    def test_arc_reactor_pulse_sound(self) -> None:
        """Arc reactor pulse sound should synthesize without error."""

        sound = soundgen.arc_reactor_pulse(0.2)
        self.assertIsNotNone(sound)

    def test_play_named_safe(self) -> None:
        """play_named should safely execute without raising exceptions."""

        soundgen.play_named("chime")
        soundgen.play_named("nonexistent_sound")


if __name__ == "__main__":
    unittest.main()
