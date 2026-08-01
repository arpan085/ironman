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


def hands_of(landmarks: dict[str, Any]) -> list[list[Any]]:
    """Return the raw per-hand landmark lists (each 21 points)."""

    return list(landmarks.get("hands") or [])


def hand_by_label(landmarks: dict[str, Any], label: str) -> list[Any] | None:
    """Return the landmark list for the first hand matching a handedness label."""

    for points, name in zip(hands_of(landmarks), landmarks.get("handedness") or []):
        if name == label:
            return points
    return None


def point_xy(points: list[Any], index: int, frame_shape: tuple[int, int, int]) -> tuple[int, int]:
    """Convert a normalized landmark at ``index`` to pixel coordinates."""

    h, w = frame_shape[:2]
    p = points[index]
    return int(p.x * w), int(p.y * h)


def hand_count(landmarks: dict[str, Any], label: str | None = None) -> int:
    """Return the number of raised fingers for a hand (default: first hand)."""

    fingers = list(landmarks.get("fingers") or [])
    labels = list(landmarks.get("handedness") or [])
    if label is None:
        return fingers[0] if fingers else 0
    for name, count in zip(labels, fingers):
        if name == label:
            return count
    return 0


def tip_distance(
    points_a: list[Any],
    points_b: list[Any],
    frame_shape: tuple[int, int, int],
) -> float:
    """Return the pixel distance between two fingertips (indices 8 and 4)."""

    h, w = frame_shape[:2]
    ax, ay = point_xy(points_a, 8, frame_shape)
    bx, by = point_xy(points_b, 4, frame_shape)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5


def hand_distance(
    landmarks: dict[str, Any],
    frame_shape: tuple[int, int, int],
) -> float | None:
    """Return pixel distance between the index tips of two hands, if present."""

    hands = hands_of(landmarks)
    if len(hands) < 2:
        return None
    ax, ay = point_xy(hands[0], 8, frame_shape)
    bx, by = point_xy(hands[1], 8, frame_shape)
    return ((ax - bx) ** 2 + (ay - by) ** 2) ** 0.5
