"""Screenshot and video recording helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass(slots=True)
class Recorder:
    """Encapsulates screenshot and video writer state."""

    output_dir: Path
    writer: Any = None

    def ensure_output_dir(self) -> None:
        """Create output directory if missing."""

        self.output_dir.mkdir(parents=True, exist_ok=True)

    def screenshot(self, frame: Any) -> Path | None:
        """Save a screenshot of the current frame."""

        try:
            import cv2  # type: ignore

            self.ensure_output_dir()
            path = self.output_dir / f"shot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            cv2.imwrite(str(path), frame)
            return path
        except Exception:
            return None

    def start_video(self, width: int, height: int, fps: int) -> Path | None:
        """Start video recording with MP4 codec."""

        if self.writer is not None:
            return None
        try:
            import cv2  # type: ignore

            self.ensure_output_dir()
            path = self.output_dir / f"rec_{datetime.now().strftime('%Y%m%d_%H%M%S')}.mp4"
            fourcc = cv2.VideoWriter_fourcc(*"mp4v")
            self.writer = cv2.VideoWriter(str(path), fourcc, max(1, fps), (width, height))
            return path
        except Exception:
            self.writer = None
            return None

    def write(self, frame: Any) -> None:
        """Write a frame to active video writer."""

        if self.writer is not None:
            self.writer.write(frame)

    def is_recording(self) -> bool:
        """Return whether a video is currently being written."""

        return self.writer is not None

    def stop_video(self) -> None:
        """Close active video writer."""

        if self.writer is not None:
            self.writer.release()
            self.writer = None
