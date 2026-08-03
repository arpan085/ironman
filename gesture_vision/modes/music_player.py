"""Gesture music player mode."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.base_mode import BaseMode
from .common import draw_instruction, resolve_package_path


class MusicPlayerMode(BaseMode):
    """Simple local-track player with gesture-triggered transport controls."""

    name = "music_player"
    shortcut = "F5"

    def __init__(self, music_dir: str | Path | None = None) -> None:
        """Initialize track list and playback state."""

        self.music_dir = Path(music_dir) if music_dir is not None else resolve_package_path("music")
        self.tracks = sorted([p for p in self.music_dir.glob("*.*") if p.suffix.lower() in {".mp3", ".wav", ".ogg"}])
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

    def play_pause(self) -> None:
        """Toggle playback state."""

        if not self._ready or not self.tracks:
            return
        import pygame  # type: ignore

        if self.is_playing:
            pygame.mixer.music.pause()
            self.is_playing = False
        else:
            self._load_current()
            pygame.mixer.music.play()
            self.is_playing = True

    def next_track(self) -> None:
        """Switch to next track and play directly."""

        if self.tracks:
            self.idx = (self.idx + 1) % len(self.tracks)
            self._load_current()
            import pygame  # type: ignore

            pygame.mixer.music.play()
            self.is_playing = True

    def prev_track(self) -> None:
        """Switch to previous track and play directly."""

        if self.tracks:
            self.idx = (self.idx - 1) % len(self.tracks)
            self._load_current()
            import pygame  # type: ignore

            pygame.mixer.music.play()
            self.is_playing = True

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Render current playback info overlay."""

        import cv2  # type: ignore

        name = self.tracks[self.idx].name if self.tracks else "No tracks"
        status = "Playing" if self.is_playing else "Paused"
        draw_instruction(frame, "F5", "music_player", "N next | B back | SPACE play/pause")
        cv2.putText(frame, f"Track: {name}", (18, 62), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (120, 255, 220), 2)
        cv2.putText(frame, f"State: {status}", (18, 92), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (120, 220, 255), 2)
        return frame
