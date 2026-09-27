"""System integration utilities for volume, brightness, and cursor."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any


@dataclass(slots=True)
class SystemControlResult:
    """Normalized control feedback for on-screen UI."""

    percentage: int
    raw_distance: float


def distance(p1: Any, p2: Any) -> float:
    """Return euclidean distance for normalized points."""

    return math.hypot(float(p1.x) - float(p2.x), float(p1.y) - float(p2.y))


def normalize_percentage(raw_distance: float, low: float = 0.02, high: float = 0.30) -> int:
    """Map a finger distance to a 0-100 range."""

    clipped = max(low, min(high, raw_distance))
    return int((clipped - low) * 100 / (high - low))


def get_brightness() -> int:
    """Get current monitor brightness, returning 50 on failure."""

    try:
        import screen_brightness_control as sbc  # type: ignore

        cur = sbc.get_brightness()
        if isinstance(cur, list):
            return int(cur[0]) if cur else 50
        return int(cur)
    except Exception:
        return 50


def set_brightness(percent: int) -> None:
    """Set monitor brightness when dependency is available."""

    try:
        import screen_brightness_control as sbc  # type: ignore

        sbc.set_brightness(max(0, min(100, int(percent))))
    except Exception:
        return


def get_volume() -> int:
    """Get current master audio volume percentage on Windows."""

    try:
        from ctypes import POINTER, cast

        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))
        scalar = volume.GetMasterVolumeLevelScalar()
        return int(round(scalar * 100.0))
    except Exception:
        return 50


def set_volume(percent: int) -> None:
    """Set master volume on Windows using pycaw scalar or dB control."""

    try:
        from ctypes import POINTER, cast

        from comtypes import CLSCTX_ALL  # type: ignore
        from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume  # type: ignore

        clamped = max(0, min(100, int(percent)))
        devices = AudioUtilities.GetSpeakers()
        interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
        volume = cast(interface, POINTER(IAudioEndpointVolume))

        try:
            # Preferred scalar method (0.0 to 1.0)
            volume.SetMasterVolumeLevelScalar(clamped / 100.0, None)
        except Exception:
            min_db, max_db, _ = volume.GetVolumeRange()
            value = min_db + (max_db - min_db) * (clamped / 100.0)
            volume.SetMasterVolumeLevel(value, None)
    except Exception:
        return
