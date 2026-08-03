"""Voice/chime assistant helpers for the Ironman-style shell."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import queue
import random
import threading
import time
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..config import AppConfig
    from .mode_manager import ModeManager


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class VoiceCommand:
    """Parsed voice command from a wake-word transcript."""

    kind: str
    payload: str = ""


@dataclass(slots=True)
class TelemetrySnapshot:
    """Small suit-status telemetry payload."""

    fps: float
    cpu_load: float
    temperature_c: float
    battery_percent: int | None


class SuitAssistant:
    """Handles wake-word commands, confirmations, and voice/chime effects."""

    def __init__(self, config: AppConfig, mode_manager: ModeManager) -> None:
        """Store runtime config and initialize optional engines."""

        self._config = config
        self._mode_manager = mode_manager
        self._wake_word = config.wake_word.lower().strip()
        self._confirmations = config.command_confirmations
        self._commands: queue.Queue[str] = queue.Queue()
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._voice_api = None
        self._recognizer = None
        self._microphone = None
        self._tts = None
        self._tts_lock = threading.Lock()
        self._rng = random.Random()
        self._init_tts()

    def _init_tts(self) -> None:
        """Initialize optional TTS engine."""

        try:
            import pyttsx3  # type: ignore
        except ImportError:
            LOGGER.info("pyttsx3 not installed: voice responses disabled.")
            return
        try:
            self._tts = pyttsx3.init()
            self._tts.setProperty("rate", 176)
        except RuntimeError as exc:
            LOGGER.warning("Failed to initialize TTS engine: %s", exc)
            self._tts = None

    def start(self) -> None:
        """Start wake-word listener if speech dependencies are present."""

        try:
            import speech_recognition as sr  # type: ignore
        except ImportError:
            LOGGER.info("SpeechRecognition not installed: wake-word listener disabled.")
            return
        try:
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
        except OSError as exc:
            LOGGER.warning("No usable microphone for wake-word listener: %s", exc)
            return
        self._voice_api = sr
        self._recognizer = recognizer
        self._microphone = microphone
        self._thread = threading.Thread(target=self._listen_loop, name="suit-assistant-listener", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop listener thread and release resources."""

        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=1.5)

    def _listen_loop(self) -> None:
        """Capture phrase transcripts and enqueue them for app-loop parsing."""

        if self._voice_api is None or self._recognizer is None or self._microphone is None:
            return
        sr = self._voice_api
        with self._microphone as source:
            self._recognizer.adjust_for_ambient_noise(source, duration=0.4)
            while not self._stop_event.is_set():
                try:
                    audio = self._recognizer.listen(source, timeout=1.0, phrase_time_limit=3.0)
                except sr.WaitTimeoutError:
                    continue
                try:
                    transcript = self._recognizer.recognize_google(audio).lower().strip()
                except sr.UnknownValueError:
                    continue
                except sr.RequestError as exc:
                    LOGGER.warning("Wake-word speech service error: %s", exc)
                    time.sleep(1.0)
                    continue
                if transcript:
                    self._commands.put(transcript)

    def poll_command(self) -> VoiceCommand | None:
        """Fetch and parse the next queued wake-word command."""

        try:
            transcript = self._commands.get_nowait()
        except queue.Empty:
            return None
        return self.parse_command(transcript)

    def parse_command(self, transcript: str) -> VoiceCommand | None:
        """Extract wake-word-prefixed directives from a transcript."""

        if not self._wake_word:
            return None
        lowered = transcript.lower()
        wake_index = lowered.find(self._wake_word)
        if wake_index < 0:
            return None

        tail = lowered[wake_index + len(self._wake_word) :].strip(" ,.!?")
        if not tail:
            return VoiceCommand(kind="wake_ack")

        if "status" in tail or "telemetry" in tail:
            return VoiceCommand(kind="status_report")
        if "help" in tail:
            return VoiceCommand(kind="help_overlay")
        if "shutdown" in tail or "power down" in tail:
            return VoiceCommand(kind="shutdown")

        best_mode = ""
        for info in self._mode_manager.list_modes():
            spoken = info.name.replace("_", " ")
            if spoken in tail:
                best_mode = info.name
                break
        if best_mode:
            return VoiceCommand(kind="switch_mode", payload=best_mode)

        return VoiceCommand(kind="unknown", payload=tail)

    def speak(self, text: str) -> None:
        """Speak a short line if TTS is available."""

        if self._tts is None:
            return
        with self._tts_lock:
            try:
                self._tts.say(text)
                self._tts.runAndWait()
            except RuntimeError as exc:
                LOGGER.warning("TTS playback failed: %s", exc)

    def confirm(self, action: str) -> None:
        """Speak one of the configured confirmation phrases."""

        phrase = self._rng.choice(self._confirmations)
        self.speak(f"{phrase} {action}")

    def speak_status(self, telemetry: TelemetrySnapshot) -> None:
        """Speak concise suit telemetry."""

        battery = "unknown"
        if telemetry.battery_percent is not None:
            battery = f"{telemetry.battery_percent} percent"
        self.speak(
            "Suit status. "
            f"Battery {battery}. "
            f"Thermal estimate {telemetry.temperature_c:.1f} Celsius. "
            f"Frame rate {telemetry.fps:.1f} F P S."
        )

    def play_startup_chime(self) -> None:
        """Play startup tone sequence."""

        if not self._config.startup_chime_enabled:
            return
        self._play_chime([(740, 80), (990, 90), (1180, 120)])

    def play_shutdown_chime(self) -> None:
        """Play shutdown tone sequence."""

        if not self._config.shutdown_chime_enabled:
            return
        self._play_chime([(980, 120), (760, 100), (520, 160)])

    def _play_chime(self, pattern: list[tuple[int, int]]) -> None:
        """Play a short beep pattern on supported systems."""

        try:
            import winsound
        except ImportError:
            LOGGER.info("winsound unavailable on this platform: chime skipped.")
            return
        for frequency, duration_ms in pattern:
            try:
                winsound.Beep(frequency, duration_ms)
            except RuntimeError as exc:
                LOGGER.warning("Unable to play system chime: %s", exc)
                return
