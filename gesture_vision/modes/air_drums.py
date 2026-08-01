"""Air Drums mode - play a drum kit by tapping virtual pads with your finger."""

from __future__ import annotations

from typing import Any

from ..core.base_mode import BaseMode
from .common import finger_xy


class AirDrumsMode(BaseMode):
    """Four on-screen drum pads triggered by fingertip hits."""

    name = "air_drums"
    shortcut = "F12"

    def __init__(self) -> None:
        """Set up pads and synthesize sounds once."""

        self.pads: list[tuple[int, int, int, int, str, tuple[int, int, int]]] = []
        self.sounds: dict[str, Any] = {}
        self._cooldowns: dict[str, int] = {}
        self._flash = ""
        self._audio_ready = False
        self._try_audio()

    def _try_audio(self) -> None:
        """Load synthesized drum sounds, falling back to silent mode."""

        try:
            from ..core import soundgen

            soundgen.init()
            for kind in ("kick", "snare", "hihat", "tom"):
                self.sounds[kind] = soundgen.drum(kind)
            self._audio_ready = True
        except Exception:
            self._audio_ready = False
        self._cooldowns = {kind: 0 for kind in ("kick", "snare", "hihat", "tom")}

    def _rebuild_pads(self, w: int, h: int) -> None:
        """Recreate the pad layout whenever the frame size changes."""

        pad_w, pad_h = int(w * 0.2), 96
        y = h - pad_h - 30
        gap = int(w * 0.03)
        x = int(w * 0.05)
        specs = [
            ("kick", (255, 110, 110)),
            ("snare", (110, 200, 255)),
            ("hihat", (255, 220, 80)),
            ("tom", (140, 255, 140)),
        ]
        self.pads = []
        for kind, color in specs:
            self.pads.append((x, y, pad_w, pad_h, kind, color))
            x += pad_w + gap

    def _play(self, kind: str) -> None:
        """Play a drum sound and mark the pad as flashing."""

        if self._audio_ready and kind in self.sounds:
            self.sounds[kind].play()
        self._flash = kind

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect hits on pads and render the kit."""

        import cv2  # type: ignore

        h, w = frame.shape[:2]
        if not self.pads or self.pads[0][1] != h - 96 - 30:
            self._rebuild_pads(w, h)

        pt = finger_xy(landmarks, frame.shape)
        if pt is not None:
            for x, y, pw, ph, kind, _ in self.pads:
                if x <= pt[0] <= x + pw and y <= pt[1] <= y + ph and self._cooldowns[kind] <= 0:
                    self._play(kind)
                    self._cooldowns[kind] = 12

        for kind in self._cooldowns:
            if self._cooldowns[kind] > 0:
                self._cooldowns[kind] -= 1

        for x, y, pw, ph, kind, color in self.pads:
            lit = self._flash == kind
            cv2.rectangle(frame, (x, y), (x + pw, y + ph), color, -1 if lit else 2)
            cv2.putText(frame, kind.upper(), (x + 16, y + ph // 2), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 0) if lit else color, 2)

        if self._flash:
            self._flash = ""

        cv2.putText(frame, "F12 Air Drums | tap pads with your index finger", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        if not self._audio_ready:
            cv2.putText(frame, "Audio device unavailable - visual only", (18, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 140, 255), 2)
        return frame
