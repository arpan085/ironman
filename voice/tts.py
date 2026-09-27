"""TTS wrapper using pyttsx3 (offline) in a background thread."""
import threading
import pyttsx3
import logging

logger = logging.getLogger(__name__)

class TTSWorker:
    def __init__(self):
        self._engine = None
        self._lock = threading.Lock()
        self._init_engine()

    def _init_engine(self):
        try:
            self._engine = pyttsx3.init()
            # try to set a slightly robotic but clear voice
            rate = 150
            self._engine.setProperty('rate', rate)
            volume = 1.0
            self._engine.setProperty('volume', volume)
        except Exception as e:
            logger.exception("Failed to initialize TTS engine: %s", e)
            self._engine = None

    def speak(self, text: str):
        if not text:
            return
        def _run(text):
            try:
                with self._lock:
                    if not self._engine:
                        self._init_engine()
                    if self._engine:
                        self._engine.say(text)
                        self._engine.runAndWait()
            except Exception as e:
                logger.exception("TTS speak error: %s", e)
        t = threading.Thread(target=_run, args=(text,), daemon=True)
        t.start()
