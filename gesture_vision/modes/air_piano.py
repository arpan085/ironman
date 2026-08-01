"""Air Piano mode - hover over a key to play synthesized notes."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import finger_xy


class AirPianoMode(BaseMode):
    """A one-octave piano played by moving your fingertip over the keys."""

    name = "air_piano"
    shortcut = "F13"

    SCALE = [
        ("C4", 262), ("D4", 294), ("E4", 330), ("F4", 349),
        ("G4", 392), ("A4", 440), ("B4", 494), ("C5", 523),
    ]

    def __init__(self) -> None:
        """Synthesize the note sounds up front."""

        self.notes: list[tuple[int, int, int, int, str]] = []
        self.sounds: dict[str, Any] = {}
        self._audio_ready = False
        self._cooldowns = {name: 0 for name, _ in self.SCALE}
        self._try_audio()

    def _try_audio(self) -> None:
        """Load synthesized notes; degrade gracefully without audio."""

        try:
            from ..core import soundgen

            soundgen.init()
            for name, freq in self.SCALE:
                self.sounds[name] = soundgen.note(freq)
            self._audio_ready = True
        except Exception:
            self._audio_ready = False

    def _rebuild_keys(self, w: int, h: int) -> None:
        """Layout one octave of white keys along the bottom edge."""

        key_w = w // len(self.SCALE)
        y = h - 150
        self.notes = [(i * key_w, y, key_w, 140, name) for i, (name, _) in enumerate(self.SCALE)]

    def _play(self, name: str) -> None:
        """Play a note and start its cooldown."""

        if self._audio_ready and name in self.sounds:
            self.sounds[name].play()
        self._cooldowns[name] = 10

    def on_key(self, key: int, char: str) -> bool:
        """Let keys 1-8 play notes directly from the keyboard."""

        if char in "12345678":
            name = self.SCALE[int(char) - 1][0]
            if self._cooldowns[name] <= 0:
                self._play(name)
            return True
        return False

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect which key the fingertip hovers over and render the keyboard."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        if not self.notes or self.notes[0][3] != 140:
            self._rebuild_keys(w, h)

        pt = finger_xy(landmarks, frame.shape)
        if pt is not None:
            for x, y, kw, kh, name in self.notes:
                if x <= pt[0] <= x + kw and y <= pt[1] <= y + kh and self._cooldowns[name] <= 0:
                    self._play(name)
                    break

        for name in self._cooldowns:
            if self._cooldowns[name] > 0:
                self._cooldowns[name] -= 1

        for i, (x, y, kw, kh, name) in enumerate(self.notes):
            playing = self._cooldowns[name] > 0
            cv2.rectangle(frame, (x, y), (x + kw, y + kh), (230, 230, 230), -1)
            cv2.rectangle(frame, (x, y), (x + kw, y + kh), (0, 0, 0), 2)
            if playing:
                cv2.rectangle(frame, (x + 2, y + 2), (x + kw - 2, y + kh - 2), (80, 255, 180), -1)
            label, _ = self.SCALE[i]
            cv2.putText(frame, label, (x + kw // 2 - 14, y + 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 0), 2)
            cv2.putText(frame, str(i + 1), (x + kw // 2 - 6, y + kh - 12), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (90, 90, 90), 1)

        cv2.putText(frame, "F13 Air Piano | hover to play; keys 1-8 as backup", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if not self._audio_ready:
            cv2.putText(frame, "Audio device unavailable - visual only", (18, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2)
        return frame
