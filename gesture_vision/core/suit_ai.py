"""Voice/chime assistant helpers for the Ironman-style shell."""

from __future__ import annotations

from dataclasses import dataclass
import logging
import queue
import random
import re
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
        self._listening = False
        self._voice_api = None
        self._recognizer = None
        self._microphone = None
        self._tts = None
        self._tts_lock = threading.Lock()
        self._tts_queue: queue.Queue[str] = queue.Queue()
        self._tts_thread: threading.Thread | None = None
        self._tts_stop_event = threading.Event()
        self._rng = random.Random()
        self._microphone_available = False
        self._tts_engine_name = ""
        # Start a dedicated TTS thread so the pyttsx3 engine is always used from one thread.
        self._init_tts()

    def _init_tts(self) -> None:
        """Start a dedicated TTS thread that initializes and owns the TTS engine.

        This avoids calling pyttsx3.runAndWait() from multiple threads or from a
        different thread than the engine was created on (which is a common
        source of silent failures).
        """

        def _tts_thread_main(stop_event: threading.Event, queue_obj: queue.Queue[str]) -> None:
            try:
                import pyttsx3  # type: ignore
            except ImportError:
                LOGGER.info("pyttsx3 not installed: voice responses disabled.")
                return

            engine = None
            engine_name = ""

            # Try pyttsx3 init first (preferred)
            for driver_name in (None, "sapi5"):
                try:
                    engine = pyttsx3.init(driver_name) if driver_name else pyttsx3.init()
                    engine.setProperty("rate", 176)
                    engine_name = "pyttsx3"
                    break
                except Exception as exc:  # noqa: BLE001
                    LOGGER.debug("TTS driver failed in tts thread: %s", exc)

            # If pyttsx3 didn't work, try Windows SAPI via comtypes/win32com
            if engine is None:
                try:
                    import win32com.client as wincl  # type: ignore
                    engine = wincl.Dispatch("SAPI.SpVoice")
                    engine_name = "sapi"
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("No supported speech engine available in tts thread; voice disabled: %s", exc)
                    return

            # Publish engine handles back to the outer object so other code may inspect state.
            self._tts = engine
            self._tts_engine_name = engine_name

            # Drain queue until stop_event is set
            while not stop_event.is_set():
                try:
                    text = queue_obj.get(timeout=0.2)
                except queue.Empty:
                    continue
                try:
                    if engine_name == "sapi":
                        engine.Speak(text)
                    else:
                        engine.say(text)
                        engine.runAndWait()
                except Exception as exc:  # noqa: BLE001
                    LOGGER.warning("TTS playback in thread failed: %s", exc)

        # Start thread
        if self._tts_thread is None or not (self._tts_thread.is_alive()):
            self._tts_stop_event.clear()
            self._tts_thread = threading.Thread(target=_tts_thread_main, args=(self._tts_stop_event, self._tts_queue), name="suit-assistant-tts", daemon=True)
            self._tts_thread.start()

    def start(self) -> None:
        """Start wake-word listener if speech dependencies are present."""

        if self._thread is not None and self._thread.is_alive():
            return
        self._microphone_available = False
        try:
            import speech_recognition as sr  # type: ignore
        except ImportError:
            LOGGER.info("SpeechRecognition not installed: wake-word listener disabled.")
            return
        try:
            recognizer = sr.Recognizer()
            microphone = sr.Microphone()
        except (AttributeError, OSError) as exc:
            LOGGER.warning("Voice unavailable: microphone backend is not ready (%s).", exc)
            return
        self._stop_event.clear()
        self._voice_api = sr
        self._recognizer = recognizer
        self._microphone = microphone
        self._microphone_available = True
        self._thread = threading.Thread(target=self._listen_loop, name="suit-assistant-listener", daemon=True)
        self._thread.start()
        self._listening = True

    def stop(self) -> None:
        """Stop listener thread and release resources, and stop the TTS thread."""

        self._stop_event.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=1.5)
            if thread.is_alive():
                LOGGER.warning("Assistant listener did not stop cleanly; keeping the thread handle until it exits.")
                self._listening = True
            else:
                self._listening = False
        else:
            self._listening = False
        self._thread = None
        self._voice_api = None
        self._recognizer = None
        self._microphone = None

        # Stop TTS thread
        try:
            self._tts_stop_event.set()
            if self._tts_thread is not None:
                self._tts_thread.join(timeout=1.5)
        except Exception:
            pass
        finally:
            self._tts_thread = None
            self._tts = None
            # empty the queue
            try:
                while not self._tts_queue.empty():
                    self._tts_queue.get_nowait()
            except Exception:
                pass

    @property
    def listening(self) -> bool:
        """Return True when wake-word listener thread is running."""

        return self._listening

    @property
    def microphone_available(self) -> bool:
        """Return True when the assistant has a usable microphone backend."""

        return self._microphone_available

    def attach_mode_manager(self, mode_manager: ModeManager) -> None:
        """Refresh mode manager reference after app-level mode reset."""

        self._mode_manager = mode_manager

    def _listen_loop(self) -> None:
        """Capture phrase transcripts and enqueue them for app-loop parsing."""

        if self._voice_api is None or self._recognizer is None or self._microphone is None:
            self._listening = False
            return
        sr = self._voice_api
        try:
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
        except (AssertionError, AttributeError, OSError) as exc:
            LOGGER.warning("Voice listener stopped due to microphone backend error: %s", exc)
            self._microphone_available = False
        finally:
            self._listening = False

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

        tail = re.sub(r"\s+", " ", lowered[wake_index + len(self._wake_word) :]).strip(" ,.!?")
        if not tail:
            return VoiceCommand(kind="wake_ack")

        if any(token in tail for token in ("hello", "hi", "hey", "greetings", "good morning", "good afternoon", "good evening")):
            return VoiceCommand(kind="greeting")
        if any(token in tail for token in ("how are you", "how are u", "how are you doing", "what's up", "whats up")):
            return VoiceCommand(kind="greeting")
        if any(token in tail for token in ("who are you", "introduce yourself", "what can you do", "what can you help me with")):
            return VoiceCommand(kind="introduction")
        if "status" in tail or "telemetry" in tail:
            return VoiceCommand(kind="status_report")
        if any(token in tail for token in ("show help", "toggle help", "open help", "help overlay")):
            return VoiceCommand(kind="help_overlay")
        if "shutdown" in tail or "power down" in tail:
            return VoiceCommand(kind="shutdown")
        if any(token in tail for token in ("reset", "restart")):
            return VoiceCommand(kind="system_action", payload="reset")
        if "clear" in tail:
            return VoiceCommand(kind="system_action", payload="clear")
        if "undo" in tail:
            return VoiceCommand(kind="system_action", payload="undo")
        if "eraser" in tail:
            return VoiceCommand(kind="system_action", payload="eraser")
        if "snapshot" in tail or "screenshot" in tail:
            return VoiceCommand(kind="system_action", payload="snapshot")
        if "record" in tail and "stop" not in tail:
            return VoiceCommand(kind="system_action", payload="record")
        if "stop recording" in tail or "stop video" in tail:
            return VoiceCommand(kind="system_action", payload="stop_recording")

        for prefix in ("open ", "launch ", "start ", "show "):
            if tail.startswith(prefix):
                target = tail[len(prefix) :].strip()
                if target:
                    return VoiceCommand(kind="open_target", payload=target)

        for prefix in ("close ", "exit ", "quit ", "stop "):
            if tail.startswith(prefix):
                target = tail[len(prefix) :].strip()
                if target:
                    return VoiceCommand(kind="close_target", payload=target)

        mode_match = re.search(r"(?:change|switch|go to|open|activate) (?:mode )?(?:to )?(.*)$", tail)
        if mode_match:
            target = mode_match.group(1).strip()
            if target:
                best_mode = self._resolve_mode_name(target)
                if best_mode:
                    return VoiceCommand(kind="switch_mode", payload=best_mode)

        best_mode = self._resolve_mode_name(tail)
        if best_mode:
            return VoiceCommand(kind="switch_mode", payload=best_mode)

        return VoiceCommand(kind="unknown", payload=tail)

    def _resolve_mode_name(self, phrase: str) -> str:
        """Resolve a spoken mode phrase to a registered mode name."""

        normalized = phrase.replace("_", " ").strip().lower()

        aliases = {
            "virtual drawing canvas": "virtual_drawing_canvas",
            "drawing canvas": "virtual_drawing_canvas",
            "draw": "virtual_drawing_canvas",
            "air painter": "air_painter",
            "finger counter": "finger_counter",
            "rock paper scissors": "rps_ai",
            "rock paper scissors ai": "rps_ai",
            "volume controller": "volume_controller",
            "brightness controller": "brightness_controller",
            "virtual mouse": "virtual_mouse",
            "finger keyboard": "finger_keyboard",
            "gesture calculator": "gesture_calculator",
            "virtual whiteboard": "virtual_whiteboard",
            "color tracking": "color_tracking",
            "object measurement": "object_measurement",
            "face filter": "face_filter",
            "image viewer": "image_viewer",
            "music player": "music_player",
            "hand animation": "hand_animation",
            "gesture games": "gesture_games",
            "finger magic": "finger_magic",
            "emoji detector": "emoji_detector",
            "performance hud": "performance_hud",
        }
        if normalized in aliases:
            return aliases[normalized]

        for info in self._mode_manager.list_modes():
            spoken = info.name.replace("_", " ")
            if spoken == normalized:
                return info.name
            if spoken.replace(" ", "") == normalized.replace(" ", ""):
                return info.name
        return ""

    def speak(self, text: str) -> None:
        """Enqueue a phrase for the TTS thread to speak.

        If the TTS thread/engine is not available, this is a no-op (but logged).
        """

        if self._tts_thread is None or not self._tts_thread.is_alive():
            LOGGER.debug("TTS thread unavailable; cannot speak: %s", text)
            return
        try:
            self._tts_queue.put_nowait(text)
        except Exception as exc:  # pragma: no cover - defensive
            LOGGER.warning("Failed to enqueue TTS text: %s", exc)

    def speak_intro_sequence(self) -> None:
        """Speak a richer startup sequence for Jarvis."""

        self.speak("Initializing neural interface.")
        time.sleep(0.2)
        self.speak("Primary systems online.")
        time.sleep(0.2)
        self.speak("Visual tracking and gesture controls are ready.")
        time.sleep(0.2)
        self.speak("At your service, sir.")

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
