"""Common utility helpers for all modes."""

from __future__ import annotations

from typing import Any


def finger_xy(landmarks: dict[str, Any], frame_shape: tuple[int, int, int]) -> tuple[int, int] | None:
    """Convert normalized index finger tip to pixel coordinates."""

    point = landmarks.get("index_tip")
    if point is None:
        return None
    h, w = frame_shape[:2]
    return int(point.x * w), int(point.y * h)
