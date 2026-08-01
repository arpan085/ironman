"""Face filter mode with stickers."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ..core.base_mode import BaseMode
from ..core.model_cache import HAAR_FRONTALFACE_URL, ensure_model


class FaceFilterMode(BaseMode):
    """Applies sunglasses/hat/cartoon effect using a Haar cascade detector."""

    name = "face_filter"
    shortcut = "F3"

    def __init__(self) -> None:
        """Initialize filter style and detector cache."""

        self.style = "sunglasses"
        self._face_cascade = None

    def _detector(self) -> Any:
        """Lazily create the OpenCV Haar face detector from local sources."""

        if self._face_cascade is not None:
            return self._face_cascade
        try:
            import cv2  # type: ignore

            candidates: list[Path] = []
            data_dir = getattr(getattr(cv2, "data", None), "haarcascades", "")
            if data_dir:
                candidates.append(Path(data_dir) / "haarcascade_frontalface_default.xml")
            cached = ensure_model(
                "haarcascade_frontalface_default.xml", HAAR_FRONTALFACE_URL
            )
            if cached is not None:
                candidates.append(cached)

            for candidate in candidates:
                if candidate.exists():
                    cascade = cv2.CascadeClassifier(str(candidate))
                    if not cascade.empty():
                        self._face_cascade = cascade
                        break
        except Exception:
            self._face_cascade = None
        return self._face_cascade

    def toggle_style(self) -> None:
        """Rotate through available face filter styles."""

        styles = ["sunglasses", "hat", "cartoon"]
        self.style = styles[(styles.index(self.style) + 1) % len(styles)]

    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Detect faces and overlay selected filter effect."""

        import cv2  # type: ignore

        detector = self._detector()
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, 1.1, 4) if detector is not None else []
        for (x, y, w, h) in faces:
            if self.style == "sunglasses":
                cv2.rectangle(frame, (x + 8, y + h // 3), (x + w - 8, y + h // 2), (0, 0, 0), -1)
            elif self.style == "hat":
                cv2.rectangle(frame, (x, y - h // 3), (x + w, y), (20, 20, 20), -1)
            else:
                roi = frame[y : y + h, x : x + w]
                frame[y : y + h, x : x + w] = cv2.bilateralFilter(roi, 7, 50, 50)

        cv2.putText(frame, f"F3 Face Filter ({self.style}) | Y Toggle", (18, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        return frame
