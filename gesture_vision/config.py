"""Configuration loading helpers."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


def _coerce_bool(value: Any, default: bool) -> bool:
    """Convert common truthy/falsy values to booleans."""

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"1", "true", "yes", "on"}:
            return True
        if lowered in {"0", "false", "no", "off", ""}:
            return False
    return default


def _coerce_string_list(value: Any, default: tuple[str, ...]) -> tuple[str, ...]:
    """Convert config values to a non-empty tuple of strings."""

    if isinstance(value, (list, tuple)):
        cleaned = tuple(str(item).strip() for item in value if str(item).strip())
        if cleaned:
            return cleaned
    return default


@dataclass(slots=True)
class AppConfig:
    """Strongly typed runtime configuration."""

    app_name: str = "Ironman Gesture Vision Suite"
    camera_index: int = 0
    target_fps: int = 30
    window_width: int = 1280
    window_height: int = 720
    theme: str = "dark"
    brush_size: int = 10
    draw_color: tuple[int, int, int] = (0, 255, 255)
    eraser_size: int = 40
    smooth_factor: float = 0.35
    record_output_dir: str = "captures"
    sidebar_enabled: bool = False
    show_splash_screen: bool = True
    fullscreen_enabled: bool = True
    assistant_enabled: bool = True
    wake_word: str = "jarvis"
    startup_chime_enabled: bool = True
    shutdown_chime_enabled: bool = True
    cinematic_hud_enabled: bool = True
    suit_status_voice_enabled: bool = True
    command_confirmations: tuple[str, ...] = ("Certainly, sir.", "Engaging now.")


def _default_path() -> Path:
    """Return the default JSON config path."""

    return Path(__file__).resolve().parent / "config" / "default_config.json"


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load configuration from JSON with safe fallbacks."""

    raw: dict[str, Any] = {}
    config_path = Path(path) if path else _default_path()
    if config_path.exists():
        raw = json.loads(config_path.read_text(encoding="utf-8"))

    draw_color = tuple(raw.get("draw_color", [0, 255, 255]))
    if len(draw_color) != 3:
        draw_color = (0, 255, 255)

    return AppConfig(
        app_name=str(raw.get("app_name", "Ironman Gesture Vision Suite")),
        camera_index=int(raw.get("camera_index", 0)),
        target_fps=max(1, int(raw.get("target_fps", 30))),
        window_width=max(320, int(raw.get("window_width", 1280))),
        window_height=max(240, int(raw.get("window_height", 720))),
        theme=str(raw.get("theme", "dark")),
        brush_size=max(1, int(raw.get("brush_size", 10))),
        draw_color=(int(draw_color[0]), int(draw_color[1]), int(draw_color[2])),
        eraser_size=max(1, int(raw.get("eraser_size", 40))),
        smooth_factor=float(raw.get("smooth_factor", 0.35)),
        record_output_dir=str(raw.get("record_output_dir", "captures")),
        sidebar_enabled=_coerce_bool(raw.get("sidebar_enabled", False), False),
        show_splash_screen=_coerce_bool(raw.get("show_splash_screen", True), True),
        fullscreen_enabled=_coerce_bool(raw.get("fullscreen_enabled", True), True),
        assistant_enabled=_coerce_bool(raw.get("assistant_enabled", True), True),
        wake_word=str(raw.get("wake_word", "jarvis")).strip().lower() or "jarvis",
        startup_chime_enabled=_coerce_bool(raw.get("startup_chime_enabled", True), True),
        shutdown_chime_enabled=_coerce_bool(raw.get("shutdown_chime_enabled", True), True),
        cinematic_hud_enabled=_coerce_bool(raw.get("cinematic_hud_enabled", True), True),
        suit_status_voice_enabled=_coerce_bool(raw.get("suit_status_voice_enabled", True), True),
        command_confirmations=_coerce_string_list(raw.get("command_confirmations"), ("Certainly, sir.", "Engaging now.")),
    )
