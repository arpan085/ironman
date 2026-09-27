"""Gesture music player mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.base_mode import BaseMode


class MusicPlayerMode(BaseMode):
    """Simple local-track player with gesture-triggered transport controls."""

    name = "music_player"
    shortcut = "F5"

    def __init__(self, music_dir: str = "music") -> None:
        """Initialize track list and playback state."""

        p = Path(music_dir)
        if not p.is_absolute() and not p.exists():
            root_candidate = Path(__file__).resolve().parents[2] / music_dir
            if root_candidate.exists():
                p = root_candidate
        self.music_dir = p
        self.tracks = sorted([t for t in self.music_dir.glob("*.*") if t.suffix.lower() in {".mp3", ".wav", ".ogg"}]) if self.music_dir.exists() else []
        self.idx = 0
        self.is_playing = False
        self.volume = 0.5
        self._ready = False
        self._init_audio()

    def _init_audio(self) -> None:
        """Initialize pygame mixer with graceful fallback."""

        try:
            import pygame  # type: ignore

            pygame.mixer.init()
            self._ready = True
        except Exception:
            self._ready = False

    def _load_current(self) -> None:
        """Load current track to mixer."""

        if not self._ready or not self.tracks:
            return
        import pygame  # type: ignore

        pygame.mixer.music.load(str(self.tracks[self.idx]))
        pygame.mixer.music.set_volume(self.volume)

    def _play_current(self) -> None:
        """Load the current track and start playback."""

        if not self._ready or not self.tracks:
            return
        import pygame  # type: ignore

        self._load_current()
        pygame.mixer.music.play()
        self.is_playing = True

    def play_pause(self) -> None:
        """Toggle playback state."""

        if not self._ready or not self.tracks:
            return
        import pygame  # type: ignore

        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
        else:
            self._play_current()

    def next_track(self) -> None:
        """Switch to the next track and start playing it."""

        if self.tracks:
            self.idx = (self.idx + 1) % len(self.tracks)
            self._play_current()

    def prev_track(self) -> None:
        """Switch to the previous track and start playing it."""

        if self.tracks:
            self.idx = (self.idx - 1) % len(self.tracks)
            self._play_current()

    def on_key(self, key: int, char: str) -> bool:
        """Handle playback transport keys."""

        if key == ord("n"):
            self.next_track()
            return True
        if key == ord("b"):
            self.prev_track()
            return True
        if key == 32:
            self.play_pause()
            return True
        return False

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render current playback info overlay."""

        import cv2  # type: ignore

        cv2.putText(frame, "F5 Music Player", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        if not self.tracks:
            cv2.putText(frame, "No tracks found - add mp3/wav/ogg files to ./music", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 220), 2)
            return frame
        name = self.tracks[self.idx].name
        status = "Playing" if self.is_playing else "Paused"
        cv2.putText(frame, f"Track: {name}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 220), 2)
        cv2.putText(frame, f"State: {status} | N next | B back | SPACE play/pause", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 220, 255), 2)
        return frame
