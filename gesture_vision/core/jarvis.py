"""J.A.R.V.I.S. (Just A Rather Very Intelligent System) AI engine.

Integrates with Google Gemini API ("yourself api") for multimodal vision and natural
intelligence, backed by a resilient offline Stark tactical rule-based protocol,
continuous microphone voice listening (STT), authentic British Paul Bettany neural
speech synthesis (TTS), and complete Iron Man suit action dispatching.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
from pathlib import Path
from queue import Empty, Queue
import random
import re
import threading
import time
from typing import Any, Callable
import urllib.error
import urllib.request

import numpy as np

from .soundgen import play_named

logger = logging.getLogger(__name__)

# Sound and audio assets directory
JARVIS_AUDIO_DIR = Path(__file__).resolve().parent.parent / "assets" / "jarvis_audio"
JARVIS_CACHE_DIR = JARVIS_AUDIO_DIR / "cache"

JARVIS_SYSTEM_PROMPT = """You are J.A.R.V.I.S. (Just A Rather Very Intelligent System), the legendary AI assistant created by Tony Stark inside the Iron Man Mark LXXXV armor.
You speak with refined British wit, supreme intelligence, unwavering loyalty, and tact (voiced in the iconic style of Paul Bettany).
Always address the user as "Sir" (or occasionally "Boss").
Keep spoken answers concise, punchy (1-3 sentences maximum), cinematic, and tactical.
You have direct command over suit telemetry, gesture tracking modes, diagnostics, and weapon systems.
If the user requests an action, append an action tag at the very end in brackets, choosing from:
[ACTION:SWITCH:mode_name] (available modes: virtual_drawing_canvas, air_painter, finger_counter, rps_ai, volume_controller, brightness_controller, virtual_mouse, finger_keyboard, gesture_calculator, virtual_whiteboard, color_tracking, object_measurement, face_filter, image_viewer, music_player, hand_animation, gesture_games, finger_magic, emoji_detector, performance_hud, gesture_snake, air_drums, air_piano, slide_controller, theremin, air_guitar, magic_wand, magnifier, macro_pad, air_signature, ironman_jarvis)
[ACTION:BLAST]
[ACTION:SCREENSHOT]
[ACTION:RECORD_START]
[ACTION:RECORD_STOP]
[ACTION:CLEAR]
[ACTION:UNDO]
[ACTION:VOLUME_UP]
[ACTION:VOLUME_DOWN]
[ACTION:BRIGHTNESS_UP]
[ACTION:BRIGHTNESS_DOWN]
[ACTION:STATUS]
"""


class GeminiClient:
    """Lightweight direct REST client for Google Gemini API without external dependencies."""

    def __init__(self, api_key: str = "", model: str = "gemini-3.8-flash") -> None:
        self.api_key = api_key.strip()
        m = model.strip() or "gemini-3.8-flash"
        if m.startswith("models/"):
            m = m[7:]
        # Normalize deprecated model names to active working model
        if m in ("gemini-2.5-flash", "gemini-1.5-flash"):
            m = "gemini-3.8-flash"
        self.model = m

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key)

    def generate(
        self,
        prompt: str,
        image_bgr: np.ndarray | None = None,
        system_instruction: str = JARVIS_SYSTEM_PROMPT,
    ) -> str:
        """Query Gemini API synchronously; raises exception on failure."""

        if not self.is_configured:
            raise ValueError("GEMINI_API_KEY is not configured")

        parts: list[dict[str, Any]] = [{"text": prompt}]

        if image_bgr is not None:
            try:
                import cv2  # type: ignore

                h, w = image_bgr.shape[:2]
                max_dim = 720
                if max(h, w) > max_dim:
                    scale = max_dim / float(max(h, w))
                    img_to_send = cv2.resize(image_bgr, (int(w * scale), int(h * scale)))
                else:
                    img_to_send = image_bgr

                ok, buffer = cv2.imencode(".jpg", img_to_send, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok:
                    b64 = base64.b64encode(buffer.tobytes()).decode("utf-8")
                    parts.insert(0, {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": b64,
                        }
                    })
            except Exception as exc:
                logger.warning("Frame encoding for Gemini failed: %s", exc)

        payload: dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": parts,
                }
            ],
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 350,
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        req_data = json.dumps(payload).encode("utf-8")

        # Try active model, fallback to gemini-3.8-flash or gemini-flash-latest
        models_to_try = [self.model, "gemini-3.8-flash", "gemini-flash-latest"]
        last_exc: Exception | None = None

        for target_model in models_to_try:
            m_clean = target_model[7:] if target_model.startswith("models/") else target_model
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{m_clean}:generateContent?key={self.api_key}"
            req = urllib.request.Request(
                url,
                data=req_data,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            try:
                with urllib.request.urlopen(req, timeout=12.0) as resp:
                    data = json.loads(resp.read().decode("utf-8"))
                    self.model = m_clean
                    break
            except urllib.error.HTTPError as err:
                last_exc = err
                if err.code == 404:
                    continue
                raise
            except Exception as err:
                last_exc = err
                raise
        else:
            if last_exc:
                raise last_exc
            return "Sensors returned no conclusive telemetry, Sir."

        candidates = data.get("candidates") or []
        if not candidates:
            return "Sensors returned no conclusive telemetry, Sir."

        content = candidates[0].get("content") or {}
        parts_resp = content.get("parts") or []
        text = "".join(p.get("text", "") for p in parts_resp).strip()
        return text or "Standing by, Sir."


class JarvisVoice:
    """Refined British J.A.R.V.I.S. voice synthesizer.
    
    Uses Microsoft Azure Neural British voice (en-GB-RyanNeural) via edge-tts with
    pre-rendered zero-latency clips and Windows SAPI fallback.
    """

    def __init__(self, enabled: bool = True) -> None:
        self.enabled = enabled
        self._queue: Queue[str] = Queue()
        self.is_speaking = False
        self.last_speech_time = 0.0
        self.current_subtitle = ""
        self._subtitle_expires = 0.0
        self._wave_phase = 0.0

        # Sound clip directory
        JARVIS_CACHE_DIR.mkdir(parents=True, exist_ok=True)

        # Preloaded sound objects
        self._loaded_clips: dict[str, Any] = {}
        self._load_predefined_clips()

        # Dedicated speaker worker thread
        self._worker_thread = threading.Thread(target=self._run_speaker, daemon=True)
        self._worker_thread.start()

    def _load_predefined_clips(self) -> None:
        """Cache pre-rendered mp3 clips if pygame mixer is available."""

        try:
            import pygame  # type: ignore

            if not pygame.mixer.get_init():
                try:
                    pygame.mixer.init()
                except Exception:
                    pass

            if pygame.mixer.get_init() and JARVIS_AUDIO_DIR.exists():
                for mp3_path in JARVIS_AUDIO_DIR.glob("*.mp3"):
                    try:
                        self._loaded_clips[mp3_path.stem] = pygame.mixer.Sound(str(mp3_path))
                    except Exception as exc:
                        logger.debug("Could not preload clip %s: %s", mp3_path.name, exc)
        except Exception:
            pass

    def speak(self, text: str, clip_name: str | None = None) -> None:
        """Queue a sentence to be voiced asynchronously."""

        if not text:
            return
        cleaned = re.sub(r"\[ACTION:[^\]]+\]", "", text).strip()
        if not cleaned:
            return

        self.current_subtitle = cleaned
        word_count = len(cleaned.split())
        self._subtitle_expires = time.time() + max(3.5, word_count * 0.22)

        if self.enabled:
            # If explicit clip requested, put token [CLIP:name]
            payload = f"[CLIP:{clip_name}] {cleaned}" if clip_name else cleaned
            self._queue.put(payload)

    def _run_speaker(self) -> None:
        """Worker loop that plays British neural audio or SAPI fallback."""

        sapi_voice = None
        try:
            import pythoncom  # type: ignore
            import win32com.client  # type: ignore

            pythoncom.CoInitialize()
            try:
                sapi_voice = win32com.client.Dispatch("SAPI.SpVoice")
                # Look for British English voice first
                voices = sapi_voice.GetVoices()
                for v in voices:
                    desc = v.GetDescription().lower()
                    if "george" in desc or "hazel" in desc or "united kingdom" in desc or "uk" in desc:
                        sapi_voice.Voice = v
                        break
                sapi_voice.Rate = 1
                sapi_voice.Volume = 100
            except Exception as exc:
                logger.debug("SAPI fallback setup note: %s", exc)
                sapi_voice = None
        except Exception:
            pass

        while True:
            try:
                item = self._queue.get()
                self.is_speaking = True

                # Check if payload specifies a preloaded clip
                clip_key = None
                sentence = item
                clip_match = re.match(r"^\[CLIP:([a-zA-Z0-9_]+)\]\s*(.*)$", item)
                if clip_match:
                    clip_key = clip_match.group(1)
                    sentence = clip_match.group(2)
                else:
                    clip_key = self._match_predefined_clip(sentence)

                played = False

                # 1. Try playing pre-rendered clip (0 latency)
                if clip_key and clip_key in self._loaded_clips:
                    try:
                        snd = self._loaded_clips[clip_key]
                        snd.play()
                        dur = snd.get_length()
                        time.sleep(dur + 0.1)
                        played = True
                    except Exception as exc:
                        logger.debug("Preloaded clip play error: %s", exc)

                # 2. Try generating authentic British voice via edge-tts
                if not played:
                    cached_file = self._get_cached_tts_path(sentence)
                    if not cached_file.exists():
                        try:
                            self._generate_neural_tts(sentence, cached_file)
                        except Exception as exc:
                            logger.debug("Edge-TTS generation skipped: %s", exc)

                    if cached_file.exists():
                        try:
                            import pygame  # type: ignore

                            if pygame.mixer.get_init():
                                snd = pygame.mixer.Sound(str(cached_file))
                                snd.play()
                                dur = snd.get_length()
                                time.sleep(dur + 0.1)
                                played = True
                        except Exception as exc:
                            logger.debug("Cached audio playback error: %s", exc)

                # 3. Fallback to Windows SAPI
                if not played and sapi_voice is not None:
                    try:
                        sapi_voice.Speak(sentence, 0)
                        played = True
                    except Exception as exc:
                        logger.debug("SAPI speak error: %s", exc)

                if not played:
                    # Simulated speech timing
                    time.sleep(max(1.2, len(sentence) * 0.05))

                self.last_speech_time = time.time()
                self.is_speaking = False
                self._queue.task_done()
            except Exception as exc:
                self.is_speaking = False
                logger.debug("Speech worker exception: %s", exc)
                time.sleep(0.1)

    def _match_predefined_clip(self, sentence: str) -> str | None:
        """Match sentence to pre-rendered clips for instant zero-latency speech."""

        s = sentence.lower().strip()
        if "mark eighty-five systems operational" in s or "mark 85" in s or "all neural channels" in s:
            return "online"
        if "switching to iron man" in s:
            return "switch_ironman"
        if "virtual drawing canvas active" in s or "drawing" in s:
            return "switch_drawing"
        if "air guitar mode online" in s or "guitar" in s:
            return "switch_guitar"
        if "air drums engaged" in s or "drums" in s:
            return "switch_drums"
        if "air piano calibrated" in s or "piano" in s:
            return "switch_piano"
        if "gesture snake simulator" in s:
            return "switch_snake"
        if "virtual mouse tracking" in s:
            return "switch_mouse"
        if "virtual whiteboard active" in s:
            return "switch_whiteboard"
        if "performance telemetry" in s:
            return "switch_hud"
        if "capacitors charging" in s:
            return "repulsor_charge"
        if "repulsor discharged" in s:
            return "repulsor_fire"
        if "tactical snapshot" in s:
            return "screenshot"
        if "flight recorder engaged" in s:
            return "record_start"
        if "recording halted" in s:
            return "record_stop"
        if "workspace buffer purged" in s:
            return "clear"
        if "at your service" in s:
            return "at_your_service"
        if "right away" in s or "understood, sir" in s:
            return "yes_sir"
        if "initiating multi-spectral" in s or "initiating deep multimodal" in s:
            return "scan"
        return None

    def _get_cached_tts_path(self, text: str) -> Path:
        """Compute MD5 hash path for cached tts sentence."""

        h = hashlib.md5(text.encode("utf-8")).hexdigest()
        return JARVIS_CACHE_DIR / f"{h}.mp3"

    def _generate_neural_tts(self, text: str, output_path: Path) -> None:
        """Call edge_tts to synthesize British Paul Bettany voice synchronously."""

        import edge_tts  # type: ignore

        voice = "en-GB-RyanNeural"
        comm = edge_tts.Communicate(text, voice, rate="+2%", pitch="-1Hz")

        async def _save() -> None:
            await comm.save(str(output_path))

        asyncio.run(_save())

    def get_waveform(self, num_bars: int = 16) -> list[float]:
        """Return normalized equalizer bar heights for HUD visualization."""

        import math

        if not self.is_speaking:
            self._wave_phase += 0.05
            return [0.08 + 0.04 * math.sin(self._wave_phase + i * 0.5) for i in range(num_bars)]

        self._wave_phase += 0.25
        vals = []
        for i in range(num_bars):
            h = 0.2 + 0.75 * abs(math.sin(self._wave_phase * 1.5 + i * 0.8))
            vals.append(min(1.0, max(0.1, h)))
        return vals

    def get_subtitle(self) -> str:
        """Return active subtitle or empty string if expired."""

        if time.time() < self._subtitle_expires:
            return self.current_subtitle
        return ""


class JarvisEar:
    """Continuous microphone voice recognition listener (STT).
    
    Listens non-stop in a background thread, calibrates for ambient noise,
    tracks voice energy for the live HUD VU meter, detects wake words and commands,
    and dispatches execution directly to the J.A.R.V.I.S. assistant.
    """

    def __init__(
        self,
        jarvis: JarvisAssistant,
        on_command: Callable[[str], None] | None = None,
        enabled: bool = True,
    ) -> None:
        self.jarvis = jarvis
        self.on_command = on_command
        self.enabled = enabled

        self.is_listening = False
        self.is_hearing_voice = False
        self.is_processing = False
        self.last_heard_text = ""
        self.status_text = "INITIALIZING..."
        self.vu_level = 0.0  # 0.0 to 1.0 for live HUD audio meter

        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None

        if self.enabled:
            self.start()

    def start(self) -> None:
        """Start the continuous microphone hearing thread."""

        if self._thread is not None and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop listening."""

        self._stop_event.set()
        self.is_listening = False
        self.status_text = "MUTED"

    def _listen_loop(self) -> None:
        """Worker loop continuously capturing audio chunks and recognizing speech."""

        try:
            import speech_recognition as sr  # type: ignore
        except Exception as exc:
            logger.warning("SpeechRecognition library not available: %s", exc)
            self.status_text = "MIC UNAVAILABLE"
            return

        recognizer = sr.Recognizer()
        recognizer.dynamic_energy_threshold = True
        recognizer.energy_threshold = 200
        recognizer.pause_threshold = 0.6  # Crisp end-of-phrase detection
        recognizer.phrase_threshold = 0.2
        recognizer.non_speaking_duration = 0.4

        try:
            mic = sr.Microphone()
            with mic as source:
                self.status_text = "CALIBRATING..."
                recognizer.adjust_for_ambient_noise(source, duration=0.8)
        except Exception as exc:
            logger.warning("Microphone initialization error: %s", exc)
            self.status_text = "MIC OFFLINE"
            return

        self.is_listening = True
        self.status_text = "LISTENING"
        logger.info("J.A.R.V.I.S. Ear online: continuous microphone hearing engaged.")

        while not self._stop_event.is_set():
            if not self.enabled:
                self.status_text = "MUTED"
                time.sleep(0.2)
                continue

            # Suppress microphone listening while J.A.R.V.I.S. is voicing an answer
            # to prevent self-transcription audio feedback loops
            if self.jarvis.voice.is_speaking or (time.time() - self.jarvis.voice.last_speech_time < 0.4):
                self.status_text = "JARVIS SPEAKING"
                time.sleep(0.15)
                continue

            try:
                self.is_listening = True
                self.status_text = "LISTENING"

                with mic as source:
                    # Listen with small timeout so thread can check _stop_event regularly
                    try:
                        audio = recognizer.listen(source, timeout=1.0, phrase_time_limit=7.5)
                    except sr.WaitTimeoutError:
                        continue

                # Speech detected!
                self.is_hearing_voice = True
                self.is_processing = True
                self.vu_level = 0.85
                self.status_text = "TRANSCRIBING..."

                try:
                    text = recognizer.recognize_google(audio, language="en-US")
                    clean = text.strip()
                    if clean:
                        self.last_heard_text = clean
                        self.status_text = f"HEARD: {clean[:24]}"
                        logger.info("J.A.R.V.I.S. heard voice input: '%s'", clean)

                        # Trigger wake chime on valid speech
                        play_named("chime")

                        # Dispatch to callback and Jarvis
                        if self.on_command:
                            self.on_command(clean)
                        else:
                            self.jarvis.handle_voice_input(clean)

                except sr.UnknownValueError:
                    # Audio unintelligible (background noise / breathing)
                    pass
                except sr.RequestError as exc:
                    logger.debug("Google speech recognition service offline: %s", exc)
                finally:
                    self.is_hearing_voice = False
                    self.is_processing = False

            except Exception as exc:
                logger.debug("Ear listener loop error: %s", exc)
                time.sleep(0.2)

        self.is_listening = False
        self.status_text = "STANDBY"


class JarvisAssistant:
    """Complete J.A.R.V.I.S. Iron Man Assistant system."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "gemini-3.8-flash",
        voice_enabled: bool = True,
    ) -> None:
        self.gemini = GeminiClient(api_key, model)
        self.voice = JarvisVoice(enabled=voice_enabled)
        self.history: list[dict[str, str]] = []
        self.last_query = ""
        self.last_response = "J.A.R.V.I.S. Online. Mark LXXXV systems ready, Sir."
        self.is_thinking = False
        self._thread_lock = threading.Lock()

        # Action and frame hooks for full app integration
        self.action_handler: Callable[[str, str | None], None] | None = None
        self.frame_provider: Callable[[], np.ndarray | None] | None = None

        # Continuous microphone hearing ear
        self.ear = JarvisEar(
            jarvis=self,
            on_command=self.handle_voice_input,
            enabled=True,
        )

        # Initial wake greeting
        self.voice.speak("J.A.R.V.I.S. online. All Mark eighty-five systems operational, Sir.", clip_name="online")

    def set_action_handler(self, handler: Callable[[str, str | None], None]) -> None:
        """Register the application callback to execute suit actions."""

        self.action_handler = handler

    def set_frame_provider(self, provider: Callable[[], np.ndarray | None]) -> None:
        """Register provider returning the current camera frame for visual queries."""

        self.frame_provider = provider

    def set_api_key(self, api_key: str) -> None:
        """Update Gemini API key dynamically."""

        self.gemini.api_key = api_key.strip()

    def handle_voice_input(self, raw_query: str) -> None:
        """Process incoming speech recognized from the microphone."""

        clean_query = raw_query.strip()
        if not clean_query:
            return

        # Pass current frame if query is asking for visual comprehension
        frame = None
        if self._is_complex_vision_query(clean_query) and self.frame_provider:
            frame = self.frame_provider()

        self.ask_async(clean_query, frame_bgr=frame)

    def ask_async(
        self,
        query: str,
        frame_bgr: np.ndarray | None = None,
        callback: Any = None,
    ) -> None:
        """Dispatch query to Gemini or offline engine in a background thread."""

        def _worker() -> None:
            with self._thread_lock:
                self.is_thinking = True
                self.last_query = query

                response_text, action, action_arg = self._process_query(query, frame_bgr)
                self.last_response = response_text
                self.is_thinking = False

                self.history.append({"query": query, "response": response_text})
                if len(self.history) > 25:
                    self.history.pop(0)

                # Execute suit action immediately
                if action is not None:
                    if self.action_handler:
                        try:
                            self.action_handler(action, action_arg)
                        except Exception as exc:
                            logger.warning("Suit action handler execution error: %s", exc)
                    if callback:
                        try:
                            callback(response_text, action, action_arg)
                        except Exception as exc:
                            logger.warning("Jarvis callback failed: %s", exc)

                # Speak the tactical response in British Paul Bettany voice
                self.voice.speak(response_text)

        t = threading.Thread(target=_worker, daemon=True)
        t.start()

    def _process_query(
        self,
        query: str,
        frame_bgr: np.ndarray | None,
    ) -> tuple[str, str | None, str | None]:
        """Route to Gemini if available or parse via offline Iron Man rules."""

        # 1. Quick local match for direct instant system commands (0 latency)
        instant_action, instant_arg, instant_text = self._match_local_command(query)
        if instant_action is not None and not self._is_complex_vision_query(query):
            return instant_text, instant_action, instant_arg

        # 2. If Gemini API is configured, use Deep Neural Vision & Reasoning
        if self.gemini.is_configured:
            try:
                # If frame is needed but not passed, try pulling from frame_provider
                if frame_bgr is None and self.frame_provider and self._is_complex_vision_query(query):
                    frame_bgr = self.frame_provider()

                raw = self.gemini.generate(query, image_bgr=frame_bgr)
                # Parse action tag if present
                action, action_arg = self._extract_action(raw)
                clean_text = re.sub(r"\[ACTION:[^\]]+\]", "", raw).strip()
                return clean_text, action, action_arg
            except Exception as exc:
                logger.warning("Gemini query failed, falling back to Stark offline protocols: %s", exc)

        # 3. Fallback to Stark offline rule-based intelligence
        if instant_action is not None:
            return instant_text, instant_action, instant_arg

        fallback_text = self._offline_conversation(query)
        return fallback_text, None, None

    def _is_complex_vision_query(self, query: str) -> bool:
        """Check if query is asking for visual scene understanding."""

        q = query.lower()
        vision_words = ["see", "look", "what is", "who is", "holding", "describe", "analyze", "scan", "view", "camera", "observe"]
        return any(w in q for w in vision_words)

    def _match_local_command(self, query: str) -> tuple[str | None, str | None, str]:
        """Match common Iron Man voice/text commands offline for instantaneous obedience."""

        q = query.lower().strip()
        # Remove polite prefixes or wake words
        q_clean = re.sub(r"^(hey\s+|ok\s+|hello\s+)?jarvis\s*,?\s*", "", q)

        # Mode switching registry
        mode_map = {
            "drawing": "virtual_drawing_canvas",
            "canvas": "virtual_drawing_canvas",
            "draw": "virtual_drawing_canvas",
            "air painter": "air_painter",
            "painter": "air_painter",
            "paint": "air_painter",
            "finger count": "finger_counter",
            "counter": "finger_counter",
            "count": "finger_counter",
            "rock paper scissors": "rps_ai",
            "rock paper": "rps_ai",
            "rps": "rps_ai",
            "volume controller": "volume_controller",
            "brightness controller": "brightness_controller",
            "virtual mouse": "virtual_mouse",
            "mouse": "virtual_mouse",
            "finger keyboard": "finger_keyboard",
            "keyboard": "finger_keyboard",
            "typing": "finger_keyboard",
            "gesture calculator": "gesture_calculator",
            "calculator": "gesture_calculator",
            "virtual whiteboard": "virtual_whiteboard",
            "whiteboard": "virtual_whiteboard",
            "color tracking": "color_tracking",
            "color": "color_tracking",
            "object measurement": "object_measurement",
            "measurement": "object_measurement",
            "ruler": "object_measurement",
            "face filter": "face_filter",
            "filter": "face_filter",
            "mask": "face_filter",
            "image viewer": "image_viewer",
            "gallery": "image_viewer",
            "image": "image_viewer",
            "music player": "music_player",
            "music": "music_player",
            "hand animation": "hand_animation",
            "animation": "hand_animation",
            "hand fx": "hand_animation",
            "gesture game": "gesture_games",
            "game": "gesture_games",
            "balloon": "gesture_games",
            "finger magic": "finger_magic",
            "magic": "finger_magic",
            "sparks": "finger_magic",
            "emoji detector": "emoji_detector",
            "emoji": "emoji_detector",
            "performance hud": "performance_hud",
            "telemetry hud": "performance_hud",
            "hud": "performance_hud",
            "gesture snake": "gesture_snake",
            "snake game": "gesture_snake",
            "snake": "gesture_snake",
            "air drums": "air_drums",
            "drums": "air_drums",
            "drum": "air_drums",
            "air piano": "air_piano",
            "piano": "air_piano",
            "slide controller": "slide_controller",
            "slide": "slide_controller",
            "slides": "slide_controller",
            "presentation": "slide_controller",
            "theremin": "theremin",
            "air guitar": "air_guitar",
            "guitar": "air_guitar",
            "rock": "air_guitar",
            "magic wand": "magic_wand",
            "wand": "magic_wand",
            "magnifier": "magnifier",
            "zoom": "magnifier",
            "macro pad": "macro_pad",
            "macro": "macro_pad",
            "air signature": "air_signature",
            "signature": "air_signature",
            "iron man": "ironman_jarvis",
            "repulsor": "ironman_jarvis",
            "suit": "ironman_jarvis",
            "mark 85": "ironman_jarvis",
            "mark eighty-five": "ironman_jarvis",
            "arc reactor": "ironman_jarvis",
        }

        # 1. Canvas / Buffer manipulations (Clear, Undo)
        if any(w in q for w in ["clear", "wipe", "purge", "reset canvas"]):
            return "clear", None, "Workspace buffer purged, Sir."

        if any(w in q for w in ["undo", "revert"]):
            return "undo", None, "Reverting previous stroke, Sir."

        # 2. Screenshots & Recording
        if any(w in q for w in ["screenshot", "snapshot", "capture frame", "take photo", "take picture"]):
            return "screenshot", None, "Tactical snapshot captured and archived, Sir."

        if any(w in q for w in ["start record", "record video", "begin recording", "start recording"]):
            return "record_start", None, "Flight recorder engaged, Sir."

        if any(w in q for w in ["stop record", "halt recording", "end recording", "stop recording"]):
            return "record_stop", None, "Recording halted and secured, Sir."

        # 3. Tactical weapon / repulsor discharge
        if any(w in q for w in ["unibeam", "chest laser", "chest blast", "full power unibeam"]):
            return "unibeam", None, "Unibeam capacitors locked and engaged, Sir."

        if any(w in q for w in ["shield", "defense", "barrier", "shields up", "deflect"]):
            return "shield", None, "Nanotech shield barrier online, Sir."

        if any(w in q for w in ["fire", "blast", "discharge", "shoot", "repulsor blast", "open fire"]):
            return "blast", None, "Repulsor discharged, Sir."

        # 4. Vision scan / analysis
        if any(w in q for w in ["scan", "analyze", "what do you see", "describe scene", "look at this"]):
            return "scan", None, "Initiating multi-spectral visual scan, Sir."

        # 5. Audio / Screen controls
        if any(w in q for w in ["unmute", "sound on", "restore sound"]):
            return "unmute", None, "Audio acoustics restored, Sir."

        if any(w in q for w in ["mute", "silence", "sound off", "be quiet"]):
            return "mute", None, "Audio acoustics muted, Sir."

        if any(w in q for w in ["volume up", "increase volume", "louder"]):
            return "volume_up", None, "Increasing acoustic gain, Sir."

        if any(w in q for w in ["volume down", "decrease volume", "quieter", "quiet"]):
            return "volume_down", None, "Decreasing acoustic gain, Sir."

        if any(w in q for w in ["brightness up", "increase brightness", "brighter"]):
            return "brightness_up", None, "HUD ocular luminance increased, Sir."

        if any(w in q for w in ["brightness down", "decrease brightness", "dimmer"]):
            return "brightness_down", None, "HUD ocular luminance dimmed, Sir."

        # 6. System Diagnostics
        if any(w in q for w in ["status", "diagnostics", "report", "system check", "power level"]):
            try:
                import psutil  # type: ignore

                cpu = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory().percent
                return "status", None, f"Mark LXXXV diagnostics nominal, Sir. Core CPU at {cpu:.0f}%, memory at {ram:.0f}%, Arc Reactor at maximum output."
            except Exception:
                return "status", None, "Mark LXXXV diagnostics nominal, Sir. Arc Reactor at 100% capacity."

        # 7. Quit / Power Down
        if any(w in q for w in ["quit", "exit", "power down", "shut down suit", "sleep mode"]):
            return "quit", None, "Powering down Mark LXXXV systems. Good day, Sir."

        # 8. Mode switching
        if any(w in q for w in ["switch", "mode", "open", "launch", "activate", "change to", "go to"]) or any(k in q for k in ["iron man", "repulsor", "guitar", "piano", "drums", "snake", "drawing", "canvas", "whiteboard"]):
            sorted_keys = sorted(mode_map.keys(), key=len, reverse=True)
            for key in sorted_keys:
                if key in q:
                    mode_id = mode_map[key]
                    nice_name = mode_id.replace("_", " ").title()
                    return "switch_mode", mode_id, f"Switching to {nice_name} mode, Sir."

        return None, None, ""

    def _extract_action(self, text: str) -> tuple[str | None, str | None]:
        """Extract [ACTION:CMD:ARG] tag from Gemini response."""

        match = re.search(r"\[ACTION:([A-Z_]+)(?::([a-zA-Z0-9_]+))?\]", text)
        if not match:
            return None, None
        cmd = match.group(1).lower()
        arg = match.group(2)
        if cmd == "switch" and arg:
            return "switch_mode", arg
        return cmd, arg

    def _offline_conversation(self, query: str) -> str:
        """In-character conversational fallback when offline or no API key."""

        q = query.lower().strip()

        if any(w in q for w in ["who are you", "what are you"]):
            return "I am J.A.R.V.I.S., your artificial intelligence. Assisting with suit diagnostics, vision tracking, and tactical defense, Sir."

        if any(w in q for w in ["hello", "hi", "hey", "greetings", "good morning", "good evening"]):
            return "Good day, Sir. All Mark LXXXV subsystems are primed and ready."

        if any(w in q for w in ["thank you", "thanks"]):
            return "Always a pleasure to assist, Sir."

        if any(w in q for w in ["repulsor", "blast", "power"]):
            return "Repulsor capacitors are at 100% capacity. Raise an open palm to discharge, Sir."

        if any(w in q for w in ["how are you", "how are you doing"]):
            return "Operating at peak theoretical efficiency, Sir. Standing by for your command."

        if "help" in q or "shortcuts" in q:
            return "Press 'H' for full shortcuts list, 'J' to speak with me, or raise your palm for repulsor target acquisition, Sir."

        templates = [
            "Telemetry noted, Sir. To unlock deep vision reasoning, add your GEMINI_API_KEY in default_config.json.",
            "Understood, Sir. Suit sensors are scanning continuously.",
            "All telemetry streams nominal, Sir. Awaiting your tactical vector.",
        ]
        return random.choice(templates)
