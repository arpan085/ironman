"""Tiny wavetable synthesizer for the gesture music modes.

Generates short drum and note samples with numpy and plays them through
pygame. No audio files required.
"""

from __future__ import annotations

import numpy as np

SAMPLE_RATE = 22050


def init(frequency: int = SAMPLE_RATE, channels: int = 1, buffer: int = 512) -> None:
    """Initialize the pygame mixer without crashing when audio is missing."""

    try:
        import pygame  # type: ignore

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=frequency, size=-16, channels=channels, buffer=buffer)
    except Exception:
        pass


def _array_to_sound(wave: np.ndarray):
    """Convert a float wave in [-1, 1] to a playable pygame Sound."""

    import pygame  # type: ignore

    arr = np.asarray(wave, dtype=np.float32)
    arr = np.clip(arr, -1.0, 1.0) * 32767.0
    if arr.ndim == 1:
        arr = arr[:, None]
    info = pygame.mixer.get_init()
    channels = info[2] if info else 1
    if arr.shape[1] == 1 and channels == 2:
        arr = np.repeat(arr, 2, axis=1)
    return pygame.sndarray.make_sound(np.ascontiguousarray(arr.astype(np.int16)))


def drum(kind: str):
    """Return a synthesized percussion sound."""

    sr = SAMPLE_RATE
    if kind == "kick":
        t = np.linspace(0, 0.35, int(sr * 0.35))
        wave = np.sin(2 * np.pi * (50 + 85 * np.exp(-t * 14)) * t) * np.exp(-t * 9)
    elif kind == "snare":
        t = np.linspace(0, 0.25, int(sr * 0.25))
        noise = np.random.uniform(-1, 1, t.size) * np.exp(-t * 18)
        tone = np.sin(2 * np.pi * 185 * t) * np.exp(-t * 22) * 0.5
        wave = noise * 0.8 + tone
    elif kind == "hihat":
        t = np.linspace(0, 0.12, int(sr * 0.12))
        wave = np.random.uniform(-1, 1, t.size) * np.exp(-t * 65)
    else:  # tom
        t = np.linspace(0, 0.3, int(sr * 0.3))
        wave = np.sin(2 * np.pi * (140 + 70 * np.exp(-t * 12)) * t) * np.exp(-t * 12)
    return _array_to_sound(wave)


def note(frequency: float, duration: float = 0.6):
    """Return a synthesized musical note with a soft decay."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    wave = np.sin(2 * np.pi * frequency * t) + 0.35 * np.sin(2 * np.pi * 2 * frequency * t)
    wave *= np.exp(-t * 3.2)
    return _array_to_sound(wave)


def tone(frequency: float, duration: float = 2.0):
    """Return a sustained tone (no decay) suitable for looping oscillators."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    wave = np.sin(2 * np.pi * frequency * t) + 0.25 * np.sin(2 * np.pi * 2 * frequency * t)
    wave *= 0.4
    return _array_to_sound(wave)


def chord(frequencies: list[float], duration: float = 0.9, strum_delay: float = 0.06):
    """Return a strummed chord built from the given frequencies."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    wave = np.zeros(n)
    for i, freq in enumerate(frequencies):
        onset = int(sr * min(strum_delay, duration) * i)
        if onset >= n:
            break
        seg_len = n - onset
        t_seg = np.linspace(0, duration, seg_len)
        tone_wave = np.sin(2 * np.pi * freq * t_seg) + 0.3 * np.sin(2 * np.pi * 2 * freq * t_seg)
        tone_wave *= np.exp(-t_seg * 2.5)
        wave[onset:] += tone_wave
    peak = max(float(np.max(np.abs(wave))), 1e-6)
    wave *= 0.9 / peak
    return _array_to_sound(wave)
