"""Air Guitar - chords with the left hand, strum across a string line."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import hand_by_label, hand_count, point_xy

CHORDS = {
    1: ("C", [262, 330, 392]),
    2: ("G", [196, 247, 294]),
    3: ("Am", [220, 262, 330]),
    4: ("Em", [165, 196, 247]),
    5: ("F", [175, 220, 262]),
}


class AirGuitarMode(BaseMode):
    """Left hand finger count picks a chord; right hand swipes the strings."""

    name = "air_guitar"
    shortcut = "F16"

    def __init__(self) -> None:
        """Synthesize the five chords up front."""

        self.sounds: dict[int, Any] = {}
        self.chord_name = "C"
        self.chord_count = 1
        self._audio_ready = False
        self._prev_y: int | None = None
        self._cooldown = 0
        self._last_strum = ""
        self._try_audio()

    def _try_audio(self) -> None:
        """Pre-build strummed chords; degrade gracefully without audio."""

        try:
            from ..core import soundgen

            soundgen.init()
            self.sounds = {n: soundgen.chord(CHORDS[n][1]) for n in CHORDS}
            self._audio_ready = True
        except Exception:
            self._audio_ready = False

    def _strum(self) -> None:
        """Play the currently selected chord."""

        n = self.chord_count
        if n not in CHORDS:
            return
        self._cooldown = 14
        self._last_strum = CHORDS[n][0]
        if self._audio_ready and n in self.sounds:
            self.sounds[n].play()

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect the chord hand, watch for strums, and render the fretboard."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        if self._cooldown > 0:
            self._cooldown -= 1

        left = hand_by_label(landmarks, "Left")
        right = hand_by_label(landmarks, "Right")
        chord_label = "Left"
        if left is None and right is not None:
            left, right = right, None
            chord_label = "Right"

        if left is not None:
            count = hand_count(landmarks, chord_label)
            self.chord_count = count if count in CHORDS else 1
            self.chord_name = CHORDS[self.chord_count][0]

        if right is not None:
            cx, cy = point_xy(right, 8, frame.shape)
            line_y = int(h * 0.55)
            if self._prev_y is not None and self._cooldown <= 0:
                crossed = (self._prev_y < line_y <= cy) or (self._prev_y > line_y >= cy)
                if crossed and abs(cy - self._prev_y) > 8:
                    self._strum()
            self._prev_y = cy
        else:
            self._prev_y = None

        cv2.putText(frame, "F16 Air Guitar | left=chord (1-5 fingers), right=strum", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(frame, f"Chord: {self.chord_name}  {'STRUM!' if self._last_strum else ''}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 220, 100), 2)

        line_y = int(h * 0.55)
        for i, dx in enumerate(range(-140, 160, 70)):
            x = w // 2 + dx
            color = (200, 60, 60) if self._last_strum and i % 2 == 0 else (120, 120, 140)
            cv2.line(frame, (x, line_y - 90), (x, line_y + 90), color, 3)
        cv2.rectangle(frame, (w // 2 - 190, line_y - 20), (w // 2 + 190, line_y + 20), (255, 200, 60), 2)

        hint_y = line_y + 50
        for n in sorted(CHORDS):
            name = CHORDS[n][0]
            color = (80, 255, 120) if n == self.chord_count else (150, 150, 150)
            cv2.putText(frame, f"{n}:{name}", (w // 2 - 190 + (n - 1) * 95, hint_y), cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
        if not self._audio_ready:
            cv2.putText(frame, "Audio device unavailable - visual only", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2)
        return frame
