"""Speech recognition worker using SpeechRecognition library.
Runs in a background thread and emits signals to the UI.
"""
from PySide6.QtCore import QObject, Signal, Slot, QThread
import speech_recognition as sr
import threading
import time
import logging

logger = logging.getLogger(__name__)

class _ListenThread(threading.Thread):
    def __init__(self, callback, stop_event: threading.Event):
        super().__init__(daemon=True)
        self.callback = callback
        self.stop_event = stop_event
        self.recognizer = sr.Recognizer()
        self.microphone = None
        try:
            self.microphone = sr.Microphone()
        except Exception as e:
            logger.exception("No microphone available: %s", e)

    def run(self):
        if not self.microphone:
            return
        with self.microphone as source:
            self.recognizer.adjust_for_ambient_noise(source, duration=0.6)
            while not self.stop_event.is_set():
                try:
                    audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=8)
                    text = self.recognizer.recognize_google(audio)
                    logger.info("Transcribed: %s", text)
                    self.callback(text)
                except sr.WaitTimeoutError:
                    continue
                except sr.UnknownValueError:
                    logger.debug("Could not understand audio")
                except Exception as e:
                    logger.exception("Speech recognition error: %s", e)
                    self.callback(None, error=str(e))
                    break

class SpeechWorker(QObject):
    transcribed = Signal(str)
    error = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start_listening(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = _ListenThread(self._on_result, self._stop_event)
        self._thread.start()

    def stop_listening(self):
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._thread.join(timeout=1)

    def _on_result(self, text, error: str | None = None):
        if error:
            self.error.emit(error)
        else:
            if text:
                self.transcribed.emit(text)
