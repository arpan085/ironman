"""Common utility helpers and Stark HUD rendering tools for all modes."""

from __future__ import annotations

import math
from typing import Any
import numpy as np


def finger_xy(landmarks: dict[str, Any], frame_shape: tuple[int, int, int]) -> tuple[int, int] | None:
    """Convert normalized index finger tip to pixel coordinates."""

    point = landmarks.get("index_tip")
    if point is None:
        return None
    h, w = frame_shape[:2]
    return int(point.x * w), int(point.y * h)


def palm_xy(landmarks: dict[str, Any], frame_shape: tuple[int, int, int]) -> tuple[int, int] | None:
    """Convert normalized palm center to pixel coordinates."""

    point = landmarks.get("palm_center")
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


# =========================================================================
# Stark HUD Graphic Primitives
# =========================================================================

def draw_hud_panel(
    frame: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    bg_color: tuple[int, int, int] = (15, 20, 25),
    border_color: tuple[int, int, int] = (0, 229, 255),
    alpha: float = 0.65,
    title: str = "",
) -> None:
    """Draw a futuristic translucent HUD card with chamfered brackets."""

    import cv2  # type: ignore

    fh, fw = frame.shape[:2]
    x1, y1 = max(0, x), max(0, y)
    x2, y2 = min(fw, x + w), min(fh, y + h)
    if x2 <= x1 or y2 <= y1:
        return

    sub = frame[y1:y2, x1:x2]
    overlay = sub.copy()
    cv2.rectangle(overlay, (0, 0), (x2 - x1, y2 - y1), bg_color, -1)
    frame[y1:y2, x1:x2] = cv2.addWeighted(sub, 1.0 - alpha, overlay, alpha, 0)

    # Tactical corner brackets
    c_len = min(16, w // 4, h // 4)
    thick = 1
    # Top-left
    cv2.line(frame, (x1, y1), (x1 + c_len, y1), border_color, thick)
    cv2.line(frame, (x1, y1), (x1, y1 + c_len), border_color, thick)
    # Top-right
    cv2.line(frame, (x2, y1), (x2 - c_len, y1), border_color, thick)
    cv2.line(frame, (x2, y1), (x2, y1 + c_len), border_color, thick)
    # Bottom-left
    cv2.line(frame, (x1, y2), (x1 + c_len, y2), border_color, thick)
    cv2.line(frame, (x1, y2), (x1, y2 - c_len), border_color, thick)
    # Bottom-right
    cv2.line(frame, (x2, y2), (x2 - c_len, y2), border_color, thick)
    cv2.line(frame, (x2, y2), (x2, y2 - c_len), border_color, thick)

    if title:
        cv2.putText(
            frame,
            title.upper(),
            (x1 + 8, y1 + 16),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.42,
            border_color,
            1,
            cv2.LINE_AA,
        )


def draw_cyber_circle(
    frame: np.ndarray,
    center: tuple[int, int],
    radius: int,
    color: tuple[int, int, int] = (0, 229, 255),
    thickness: int = 2,
    segments: int = 8,
    angle_offset: float = 0.0,
    gap_ratio: float = 0.25,
) -> None:
    """Render a segmented rotating cyber ring."""

    import cv2  # type: ignore

    cx, cy = center
    step = 360.0 / max(1, segments)
    arc_len = step * (1.0 - gap_ratio)
    for i in range(segments):
        start_angle = angle_offset + i * step
        end_angle = start_angle + arc_len
        cv2.ellipse(
            frame,
            (cx, cy),
            (radius, radius),
            0,
            start_angle,
            end_angle,
            color,
            thickness,
            cv2.LINE_AA,
        )


def draw_target_reticle(
    frame: np.ndarray,
    center: tuple[int, int],
    size: int = 36,
    color: tuple[int, int, int] = (0, 229, 255),
    label: str = "",
) -> None:
    """Render a Stark Industries tactical crosshair with corner brackets."""

    import cv2  # type: ignore

    cx, cy = center
    half = size // 2
    arm = max(6, size // 4)

    # Brackets
    cv2.line(frame, (cx - half, cy - half), (cx - half + arm, cy - half), color, 1, cv2.LINE_AA)
    cv2.line(frame, (cx - half, cy - half), (cx - half, cy - half + arm), color, 1, cv2.LINE_AA)

    cv2.line(frame, (cx + half, cy - half), (cx + half - arm, cy - half), color, 1, cv2.LINE_AA)
    cv2.line(frame, (cx + half, cy - half), (cx + half, cy - half + arm), color, 1, cv2.LINE_AA)

    cv2.line(frame, (cx - half, cy + half), (cx - half + arm, cy + half), color, 1, cv2.LINE_AA)
    cv2.line(frame, (cx - half, cy + half), (cx - half, cy + half - arm), color, 1, cv2.LINE_AA)

    cv2.line(frame, (cx + half, cy + half), (cx + half - arm, cy + half), color, 1, cv2.LINE_AA)
    cv2.line(frame, (cx + half, cy + half), (cx + half, cy + half - arm), color, 1, cv2.LINE_AA)

    # Inner dot
    cv2.circle(frame, (cx, cy), 2, color, -1)

    if label:
        cv2.putText(
            frame,
            label,
            (cx - half, cy - half - 6),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.4,
            color,
            1,
            cv2.LINE_AA,
        )


def draw_cyber_hand(
    frame: np.ndarray,
    hand_points: list[Any],
    color: tuple[int, int, int] = (0, 229, 255),
    glow_color: tuple[int, int, int] = (0, 100, 180),
) -> None:
    """Render a Mark LXXXV Nanotech Cybernetic hand skeleton with plasma conduits."""

    import cv2  # type: ignore

    h, w = frame.shape[:2]
    pts = [(int(p.x * w), int(p.y * h)) for p in hand_points]

    # Hand skeletal connections
    connections = [
        # Palm mesh
        (0, 1), (0, 5), (5, 9), (9, 13), (13, 17), (17, 0),
        # Thumb
        (1, 2), (2, 3), (3, 4),
        # Index
        (5, 6), (6, 7), (7, 8),
        # Middle
        (9, 10), (10, 11), (11, 12),
        # Ring
        (13, 14), (14, 15), (15, 16),
        # Pinky
        (17, 18), (18, 19), (19, 20),
    ]

    # 1. Outer glow conduits
    for i1, i2 in connections:
        cv2.line(frame, pts[i1], pts[i2], glow_color, 3, cv2.LINE_AA)

    # 2. Inner high-energy laser conduit core
    for i1, i2 in connections:
        cv2.line(frame, pts[i1], pts[i2], (255, 255, 255), 1, cv2.LINE_AA)

    # 3. Knuckle nodes (micro-bearings)
    for i, pt in enumerate(pts):
        is_tip = i in (4, 8, 12, 16, 20)
        radius = 5 if is_tip else 3
        # Outer ring
        cv2.circle(frame, pt, radius, color, 1, cv2.LINE_AA)
        # Core plasma dot
        cv2.circle(frame, pt, 2, (255, 255, 255), -1, cv2.LINE_AA)
        if is_tip:
            # Small holographic targeting brackets on tips
            t_arm = 4
            px, py = pt
            cv2.line(frame, (px - t_arm, py - t_arm), (px + t_arm, py - t_arm), color, 1)
            cv2.line(frame, (px - t_arm, py + t_arm), (px + t_arm, py + t_arm), color, 1)

    # 4. Palm repulsor core
    if len(pts) > 9:
        p0, p5, p17 = pts[0], pts[5], pts[17]
        palm_cx = (p0[0] + p5[0] + p17[0]) // 3
        palm_cy = (p0[1] + p5[1] + p17[1]) // 3
        cv2.circle(frame, (palm_cx, palm_cy), 12, color, 1, cv2.LINE_AA)
        cv2.circle(frame, (palm_cx, palm_cy), 6, (0, 215, 255), -1, cv2.LINE_AA)
        cv2.circle(frame, (palm_cx, palm_cy), 2, (255, 255, 255), -1, cv2.LINE_AA)


def draw_ecg_monitor(
    frame: np.ndarray,
    x: int,
    y: int,
    w: int,
    h: int,
    phase: float = 0.0,
    color: tuple[int, int, int] = (100, 255, 140),
) -> None:
    """Render a dynamic real-time P-Q-R-S-T biometric cardiac ECG waveform."""

    import cv2  # type: ignore

    fh, fw = frame.shape[:2]
    pts = []
    cy = y + h // 2
    for px in range(w):
        # Normalized sample in 0..1 per pulse cycle
        val = ((px / 75.0) + phase) % 1.0
        # ECG synthesis: P-wave, Q-dip, R-spike, S-dip, T-wave
        dy = 0.0
        if 0.15 < val < 0.25:
            dy = -6.0 * math.sin((val - 0.15) * 10.0 * math.pi)  # P-wave
        elif 0.38 < val < 0.42:
            dy = 5.0 * math.sin((val - 0.38) * 25.0 * math.pi)   # Q-dip
        elif 0.42 <= val < 0.48:
            dy = -28.0 * math.sin((val - 0.42) * 16.6 * math.pi) # R-spike
        elif 0.48 <= val < 0.52:
            dy = 8.0 * math.sin((val - 0.48) * 25.0 * math.pi)   # S-dip
        elif 0.62 < val < 0.76:
            dy = -10.0 * math.sin((val - 0.62) * 7.14 * math.pi) # T-wave
        pts.append((x + px, int(cy + dy)))

    for i in range(len(pts) - 1):
        # Fade older trace
        alpha_pt = 0.4 + 0.6 * (i / len(pts))
        c = (int(color[0] * alpha_pt), int(color[1] * alpha_pt), int(color[2] * alpha_pt))
        cv2.line(frame, pts[i], pts[i + 1], c, 1, cv2.LINE_AA)

    # Lead glowing dot
    if pts:
        cv2.circle(frame, pts[-1], 3, (255, 255, 255), -1, cv2.LINE_AA)


def draw_hex_shield(
    frame: np.ndarray,
    center: tuple[int, int],
    radius: int = 180,
    color: tuple[int, int, int] = (0, 229, 255),
    alpha: float = 0.5,
    phase: float = 0.0,
) -> None:
    """Render a shimmering hexagonal holographic forcefield barrier."""

    import cv2  # type: ignore

    cx, cy = center
    fh, fw = frame.shape[:2]
    overlay = frame.copy()

    # Hexagonal geometry
    hex_size = 28
    cols = int(radius * 2 // (hex_size * 1.5)) + 2
    rows = int(radius * 2 // (hex_size * 1.732)) + 2

    x_start = cx - radius
    y_start = cy - radius

    for r in range(rows):
        for c in range(cols):
            hx = int(x_start + c * hex_size * 1.5)
            hy = int(y_start + r * hex_size * 1.732 + (c % 2) * (hex_size * 0.866))
            dist = math.hypot(hx - cx, hy - cy)
            if dist <= radius:
                # Shimmer intensity
                shimmer = 0.5 + 0.5 * math.sin(phase * 4.0 + dist * 0.08)
                hex_pts = []
                for a in range(6):
                    angle_deg = 60 * a
                    rad = math.radians(angle_deg)
                    px = int(hx + (hex_size * 0.48) * math.cos(rad))
                    py = int(hy + (hex_size * 0.48) * math.sin(rad))
                    hex_pts.append((px, py))
                hex_arr = np.array([hex_pts], dtype=np.int32)
                # Cell fill
                cell_col = (int(color[0] * shimmer * 0.4), int(color[1] * shimmer * 0.4), int(color[2] * shimmer * 0.4))
                cv2.fillPoly(overlay, hex_arr, cell_col)
                # Cell border
                border_col = (int(color[0] * shimmer), int(color[1] * shimmer), int(color[2] * shimmer))
                cv2.polylines(overlay, hex_arr, True, border_col, 1, cv2.LINE_AA)

    # Outer perimeter barrier ring
    cv2.circle(overlay, (cx, cy), radius, color, 2, cv2.LINE_AA)
    frame[:] = cv2.addWeighted(frame, 1.0 - alpha, overlay, alpha, 0)

