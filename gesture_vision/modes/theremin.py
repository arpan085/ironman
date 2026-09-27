"""Virtual Theremin - play pitch with one hand, volume with hand separation."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import hand_distance, hands_of, point_xy

PENTATONIC = [262, 294, 330, 392, 440, 523, 587, 659, 784, 880]


class ThereminMode(BaseMode):
    """Right hand height selects the note; distance between hands sets volume."""

    name = "theremin"
    shortcut = "F15"

    def __init__(self) -> None:
        """Pre-render the note table and connect the audio channel."""

        self.tones: dict[int, Any] = {}
        self._channel: Any = None
        self._audio_ready = False
        self._current_step: int | None = None
        self._try_audio()

    def _try_audio(self) -> None:
        """Build sustained tones and claim a mixer channel."""

        try:
            from ..core import soundgen
            import pygame  # type: ignore

            soundgen.init()
            self.tones = {i: soundgen.tone(f) for i, f in enumerate(PENTATONIC)}
            self._channel = pygame.mixer.find_channel()
            if self._channel is None:
                self._channel = pygame.mixer.Channel(0)
            self._audio_ready = True
        except Exception:
            self._audio_ready = False

    def _set_note(self, step: int) -> None:
        """Retune the looping oscillator to a pentatonic step."""

        if step == self._current_step:
            return
        self._current_step = step
        if self._audio_ready and self._channel is not None and step in self.tones:
            self._channel.stop()
            self._channel.play(self.tones[step], loops=-1)

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Map hand position to pitch/volume and render the stage."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        hands = hands_of(landmarks)
        if hands:
            x, y = point_xy(hands[0], 8, frame.shape)
            step = min(len(PENTATONIC) - 1, max(0, int((1 - (y / h)) * len(PENTATONIC))))
            self._set_note(step)
            cv2.line(frame, (x, y), (x, int(h * 0.12)), (255, 255, 255), 2)
            cv2.circle(frame, (x, y), 14, (255, 200, 80), -1)
        else:
            if self._channel is not None:
                self._channel.stop()
            self._current_step = None

        volume = 0.8
        dist = hand_distance(landmarks, frame.shape)
        if dist is not None:
            max_d = (w * w + h * h) ** 0.5 * 0.45
            volume = max(0.05, min(1.0, dist / max_d))
        if self._audio_ready and self._channel is not None:
            from ..core.soundgen import get_master_volume, is_muted

            eff_vol = 0.0 if is_muted() else volume * get_master_volume()
            self._channel.set_volume(eff_vol)

        bar_w = int(w * 0.4)
        x0 = w // 2 - bar_w // 2
        cv2.putText(frame, "F15 Theremin | height=pitch, hand distance=volume", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        for i, _ in enumerate(PENTATONIC):
            y = int(h * 0.12) + int((h * 0.78) * (i / len(PENTATONIC)))
            cv2.line(frame, (x0, y), (x0 + bar_w, y), (60, 60, 60), 1)
        note_name = f"Step {self._current_step or 0}"
        cv2.rectangle(frame, (x0, 70), (x0 + bar_w, 104), (30, 30, 30), -1)
        cv2.putText(frame, f"Note {note_name} | Volume {volume * 100:3.0f}%", (x0 + 8, 94), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 200), 2)
        if not self._audio_ready:
            cv2.putText(frame, "Audio device unavailable - visual only", (18, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2)
        return frame

    def on_exit(self) -> None:
        """Stop sound channel on mode switch."""

        if self._channel is not None:
            self._channel.stop()
        self._current_step = None
