"""Common utility helpers for all modes."""

from __future__ import annotations

from pathlib import Path
from typing import Any


def finger_xy(landmarks: dict[str, Any], frame_shape: tuple[int, int, int]) -> tuple[int, int] | None:
    """Convert normalized index finger tip to pixel coordinates."""

    point = landmarks.get("index_tip")
    if point is None:
        return None
    h, w = frame_shape[:2]
    return int(point.x * w), int(point.y * h)


def resolve_package_path(folder: str) -> Path:
    """Resolve a package-relative asset folder from the gesture_vision package root."""

    return Path(__file__).resolve().parents[1] / folder


def clamp_point(point: tuple[int, int], frame_shape: tuple[int, int, int]) -> tuple[int, int]:
    """Clamp a point inside the frame bounds."""

    h, w = frame_shape[:2]
    x = max(0, min(w - 1, point[0]))
    y = max(0, min(h - 1, point[1]))
    return (x, y)


def draw_instruction(frame: Any, shortcut: str, mode_name: str, hints: str, *, color: tuple[int, int, int] = (255, 255, 255), position: tuple[int, int] = (18, 28), font_scale: float = 0.6) -> None:
    """Draw a standardized instruction banner to the frame."""

    import cv2  # type: ignore

    title = f"{shortcut} {mode_name.replace('_', ' ').title()} | {hints}"
    cv2.putText(frame, title, position, cv2.FONT_HERSHEY_SIMPLEX, font_scale, color, 2)
