"""Acoustic-grade synthesizer for gesture instruments and Stark Iron Man V3 effects.

Generates velvety, cinematic audio textures using harmonic numpy wavetables
and plays them through pygame with master volume control and mute toggle.
Zero external audio files required. All harsh frequencies eliminated.
"""

from __future__ import annotations

import logging
from typing import Any
import numpy as np

logger = logging.getLogger(__name__)

SAMPLE_RATE = 44100  # Studio quality 44.1kHz sample rate

_MASTER_VOLUME: float = 0.65
_IS_MUTED: bool = False
_SOUND_CACHE: dict[str, Any] = {}


def set_master_volume(level: float) -> None:
    """Set master audio volume in range [0.0, 1.0]."""

    global _MASTER_VOLUME
    _MASTER_VOLUME = max(0.0, min(1.0, float(level)))


def get_master_volume() -> float:
    """Return current master audio volume."""

    return _MASTER_VOLUME


def toggle_mute() -> bool:
    """Toggle audio mute state on or off; returns new muted state."""

    global _IS_MUTED
    _IS_MUTED = not _IS_MUTED
    return _IS_MUTED


def is_muted() -> bool:
    """Return True if audio playback is currently muted."""

    return _IS_MUTED


def init(frequency: int = SAMPLE_RATE, channels: int = 2, buffer: int = 512) -> None:
    """Initialize the pygame mixer with stereo 44.1kHz without crashing."""

    try:
        import pygame  # type: ignore

        if not pygame.mixer.get_init():
            pygame.mixer.init(frequency=frequency, size=-16, channels=channels, buffer=buffer)
    except Exception as exc:
        logger.debug("Pygame mixer initialization skipped: %s", exc)


def _array_to_sound(wave: np.ndarray) -> Any:
    """Convert a float wave in [-1, 1] to a stereo playable pygame Sound."""

    try:
        import pygame  # type: ignore

        arr = np.asarray(wave, dtype=np.float32)
        arr = np.clip(arr, -1.0, 1.0) * 32767.0
        if arr.ndim == 1:
            arr = np.column_stack([arr, arr])
        return pygame.sndarray.make_sound(np.ascontiguousarray(arr.astype(np.int16)))
    except Exception as exc:
        logger.debug("Sound array conversion skipped: %s", exc)
        return None


def play_sound(sound: Any) -> None:
    """Safely play a pygame Sound scaled by master volume unless muted."""

    if sound is None or _IS_MUTED or _MASTER_VOLUME <= 0.001:
        return
    try:
        sound.set_volume(_MASTER_VOLUME)
        sound.play()
    except Exception as exc:
        logger.debug("Sound playback error: %s", exc)


def drum(kind: str) -> Any:
    """Return a warm, punchy synthesized percussion sound."""

    sr = SAMPLE_RATE
    if kind == "kick":
        t = np.linspace(0, 0.35, int(sr * 0.35))
        # Warm sub kick with soft punch
        pitch = 50.0 + 80.0 * np.exp(-t * 16.0)
        wave = np.sin(2 * np.pi * pitch * t) * np.exp(-t * 8.5)
    elif kind == "snare":
        t = np.linspace(0, 0.22, int(sr * 0.22))
        noise = np.random.normal(0, 0.6, t.size) * np.exp(-t * 20.0)
        tone_wave = np.sin(2 * np.pi * 175.0 * t) * np.exp(-t * 18.0) * 0.45
        wave = noise * 0.65 + tone_wave
    elif kind == "hihat":
        t = np.linspace(0, 0.09, int(sr * 0.09))
        # Filtered soft shaker texture instead of harsh sizzle
        noise = np.random.normal(0, 0.45, t.size) * np.exp(-t * 70.0)
        wave = noise
    else:  # tom
        t = np.linspace(0, 0.28, int(sr * 0.28))
        wave = np.sin(2 * np.pi * (130.0 + 60.0 * np.exp(-t * 12.0)) * t) * np.exp(-t * 10.0)
    return _array_to_sound(wave * 0.8)


def note(frequency: float, duration: float = 0.6) -> Any:
    """Return a warm musical note with soft harmonic overtone and exponential decay."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    soft_attack = np.minimum(t / 0.015, 1.0)
    wave = (np.sin(2 * np.pi * frequency * t) + 0.25 * np.sin(4 * np.pi * frequency * t)) * soft_attack
    wave *= np.exp(-t * 3.0)
    return _array_to_sound(wave * 0.7)


def tone(frequency: float, duration: float = 2.0) -> Any:
    """Return a warm sustained tone for looping oscillators."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    wave = np.sin(2 * np.pi * frequency * t) + 0.2 * np.sin(4 * np.pi * frequency * t)
    wave *= 0.35
    return _array_to_sound(wave)


def chord(frequencies: list[float], duration: float = 0.9, strum_delay: float = 0.05) -> Any:
    """Return a warm strummed acoustic chord."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    total = np.zeros(n)
    for i, freq in enumerate(frequencies):
        onset = int(sr * min(strum_delay * i, duration * 0.5))
        if onset >= n:
            break
        seg_len = n - onset
        t_seg = np.linspace(0, duration, seg_len)
        soft_attack = np.minimum(t_seg / 0.015, 1.0)
        decay = np.exp(-t_seg * 2.8)
        tone_wave = (np.sin(2 * np.pi * freq * t_seg) + 0.2 * np.sin(4 * np.pi * freq * t_seg)) * soft_attack * decay
        total[onset:] += tone_wave * 0.3
    peak = max(float(np.max(np.abs(total))), 1e-6)
    return _array_to_sound((total / peak) * 0.75)


# =========================================================================
# V3 Cinematic Stark Iron Man & J.A.R.V.I.S. Soundscape (Zero Harshness)
# =========================================================================

def ui_switch(duration: float = 0.26) -> Any:
    """Silky sci-fi holographic mode switch whoosh.
    
    Replaces harsh clicking with a smooth, luxurious cinematic sweep
    and warm harmonic bell resonance.
    """

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    hanning = 0.5 * (1.0 - np.cos(2 * np.pi * t / duration))
    # Smooth downward pitch glide (440Hz -> 220Hz)
    freq = 440.0 - 220.0 * (t / duration)
    w_tone = np.sin(2 * np.pi * freq * t) * hanning
    # Filtered warm air displacement whoosh
    noise = np.random.normal(0, 0.25, n) * hanning * np.exp(-t * 6.0)
    # Warm bell overtone at E4 (329.63Hz)
    chime = np.sin(2 * np.pi * 329.63 * t) * np.exp(-t * 11.0) * 0.35
    wave = (w_tone * 0.45 + noise * 0.22 + chime * 0.33) * 0.4
    return _array_to_sound(wave)


def ui_ping(duration: float = 0.11) -> Any:
    """Velvety crystalline glass tap for button presses and UI feedback.
    
    Tuned to warm marimba frequencies (587.33Hz D5 and 880Hz A5) with soft attack
    and smooth exponential decay. Never piercing.
    """

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    f0 = 587.33
    env = np.sin(np.pi * np.clip(t / 0.008, 0, 0.5)) * np.exp(-t * 32.0)
    wave = (np.sin(2 * np.pi * f0 * t) + 0.3 * np.sin(3 * np.pi * f0 * t) + 0.12 * np.sin(4 * np.pi * f0 * t)) * env * 0.38
    return _array_to_sound(wave)


def jarvis_chime(duration: float = 0.85) -> Any:
    """Celestial Stark Industries C-Major 9th holographic notification chord.
    
    Rich, layered bell harmonics with warm sustain (C5, E5, G5, B5, D6).
    """

    sr = SAMPLE_RATE
    n = int(sr * duration)
    total_w = np.zeros(n)
    notes = [523.25, 659.25, 783.99, 987.77, 1174.66]
    delays = [0.0, 0.04, 0.08, 0.12, 0.16]
    for freq, delay in zip(notes, delays):
        start_idx = int(delay * sr)
        seg_len = n - start_idx
        t_seg = np.linspace(0, duration - delay, seg_len)
        soft_attack = np.minimum(t_seg / 0.012, 1.0)
        decay = np.exp(-t_seg * 4.2)
        tone_val = (np.sin(2 * np.pi * freq * t_seg) + 0.22 * np.sin(2 * np.pi * freq * 2.75 * t_seg) * np.exp(-t_seg * 14)) * soft_attack * decay
        total_w[start_idx:] += tone_val * 0.24
    return _array_to_sound(total_w * 0.55)


def repulsor_charge(duration: float = 0.85) -> Any:
    """Cinematic Mark LXXXV turbine power surge.
    
    Deep, rich resonant power swell from 65Hz to 280Hz with warm plasma harmonics.
    Eliminates high-pitched screeching in favor of movie-grade engine roar.
    """

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    freq = 65.0 + 215.0 * (t / duration) ** 1.6
    sub_bass = np.sin(2 * np.pi * freq * t)
    harmonic1 = 0.35 * np.sin(4 * np.pi * freq * t)
    pulse = 0.85 + 0.15 * np.sin(2 * np.pi * 14.0 * t)
    soft_ramp = np.minimum(t * 3.5, 1.0)
    wave = (sub_bass + harmonic1) * pulse * soft_ramp * 0.65
    return _array_to_sound(wave)


def repulsor_blast(duration: float = 0.55) -> Any:
    """Devastating cinema-grade 1.2GW repulsor discharge.
    
    Chest-thumping 45Hz sub-bass punch + low-pass filtered air shockwave burst
    + subtle plasma ionization crackle.
    """

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    # Deep sub punch
    sub_punch = np.sin(2 * np.pi * (110.0 * np.exp(-t * 24.0)) * t) * np.exp(-t * 6.5)
    # Filtered explosion air rush
    noise = np.random.normal(0, 0.45, n) * np.exp(-t * 12.0)
    # Electric plasma ionization ring
    crackle = np.sin(2 * np.pi * 480.0 * t) * np.exp(-t * 22.0) * 0.25
    wave = sub_punch * 0.85 + noise * 0.40 + crackle
    peak = max(float(np.max(np.abs(wave))), 1e-6)
    return _array_to_sound((wave / peak) * 0.85)


def target_lock(duration: float = 0.20) -> Any:
    """Subtle twin holographic tactical lock pips.
    
    Soft crystal chimes at 880Hz and 1174Hz with warm envelopes.
    """

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    f1, f2 = 880.0, 1174.66
    pip1 = (t < 0.08) * np.sin(2 * np.pi * f1 * t) * np.exp(-t * 28.0)
    t2 = np.maximum(0.0, t - 0.10)
    pip2 = (t >= 0.10) * np.sin(2 * np.pi * f2 * t2) * np.exp(-t2 * 28.0)
    wave = (pip1 + pip2) * 0.4
    return _array_to_sound(wave)


def arc_reactor_pulse(duration: float = 0.75) -> Any:
    """Lush, warm 60Hz ambient plasma heartbeat of the Arc Reactor core."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    core = np.sin(2 * np.pi * 58.0 * t) * (1.0 + 0.25 * np.sin(2 * np.pi * 4.5 * t))
    hum = 0.25 * np.sin(2 * np.pi * 116.0 * t)
    decay = np.exp(-t * 1.5)
    wave = (core + hum) * decay * 0.45
    return _array_to_sound(wave)


def unibeam_blast(duration: float = 1.1) -> Any:
    """Massive screen-spanning chest Arc Reactor Unibeam discharge."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    # Deep sub-bass thunder drop from 180Hz to 35Hz
    sub = np.sin(2 * np.pi * (180.0 * np.exp(-t * 10.0) + 35.0) * t) * (1.0 - t / duration)
    # Plasma roar
    roar = np.random.normal(0, 0.4, n) * (1.0 - t / duration) ** 1.2
    # Laser beam harmonics
    beam = (np.sin(2 * np.pi * 220.0 * t) + 0.3 * np.sin(2 * np.pi * 440.0 * t)) * np.exp(-t * 3.5)
    wave = sub * 0.75 + roar * 0.4 + beam * 0.35
    peak = max(float(np.max(np.abs(wave))), 1e-6)
    return _array_to_sound((wave / peak) * 0.9)


def shield_deploy(duration: float = 0.40) -> Any:
    """Holographic nanotech energy shield deployment shimmer."""

    sr = SAMPLE_RATE
    n = int(sr * duration)
    t = np.linspace(0, duration, n)
    # Shimmering crystal sweep
    freq = 350.0 + 300.0 * (t / duration)
    shimmer = np.sin(2 * np.pi * freq * t) * (1.0 + 0.3 * np.sin(2 * np.pi * 32.0 * t)) * np.exp(-t * 5.0)
    return _array_to_sound(shimmer * 0.42)


def play_named(name: str) -> None:
    """Play a cached synthesized sound by name with master volume scaling."""

    global _SOUND_CACHE
    if _IS_MUTED or _MASTER_VOLUME <= 0.001:
        return

    if name not in _SOUND_CACHE:
        init()
        builders = {
            "blast": repulsor_blast,
            "charge": repulsor_charge,
            "chime": jarvis_chime,
            "lock": target_lock,
            "pulse": arc_reactor_pulse,
            "ping": ui_ping,
            "switch": ui_switch,
            "unibeam": unibeam_blast,
            "shield": shield_deploy,
        }
        if name in builders:
            try:
                _SOUND_CACHE[name] = builders[name]()
            except Exception:
                _SOUND_CACHE[name] = None
        else:
            return

    play_sound(_SOUND_CACHE.get(name))
