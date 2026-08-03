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
    )
