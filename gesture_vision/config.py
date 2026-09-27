"""Configuration loading helpers with environment and Stark suite options."""

from __future__ import annotations

from dataclasses import dataclass
import json
import os
from pathlib import Path
from typing import Any


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
    gemini_api_key: str = ""
    jarvis_enabled: bool = True
    jarvis_voice: bool = True
    jarvis_model: str = "gemini-3.8-flash"
    stark_hud: bool = True


def _default_path() -> Path:
    """Return the default JSON config path."""

    return Path(__file__).resolve().parent / "config" / "default_config.json"


def _read_env_file(project_root: Path) -> dict[str, str]:
    """Parse key=value pairs from .env without external dependencies."""

    env_path = project_root / ".env"
    env_vars: dict[str, str] = {}
    if not env_path.exists():
        return env_vars

    try:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            key = key.strip()
            val = val.strip().strip("\"'")
            env_vars[key] = val
    except Exception:
        pass
    return env_vars


def load_config(path: str | Path | None = None) -> AppConfig:
    """Load configuration from JSON and environment with safe fallbacks."""

    raw: dict[str, Any] = {}
    config_path = Path(path) if path else _default_path()
    if config_path.exists():
        try:
            raw = json.loads(config_path.read_text(encoding="utf-8"))
        except Exception:
            raw = {}

    project_root = Path(__file__).resolve().parents[1]
    env_file = _read_env_file(project_root)

    # API key resolution: env var -> .env file -> config json
    gemini_key = (
        os.environ.get("GEMINI_API_KEY")
        or os.environ.get("GOOGLE_API_KEY")
        or os.environ.get("JARVIS_API_KEY")
        or env_file.get("GEMINI_API_KEY")
        or env_file.get("GOOGLE_API_KEY")
        or env_file.get("JARVIS_API_KEY")
        or str(raw.get("gemini_api_key", ""))
    ).strip()

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
        sidebar_enabled=bool(raw.get("sidebar_enabled", False)),
        gemini_api_key=gemini_key,
        jarvis_enabled=bool(raw.get("jarvis_enabled", True)),
        jarvis_voice=bool(raw.get("jarvis_voice", True)),
        jarvis_model=str(raw.get("jarvis_model", "gemini-2.5-flash")),
        stark_hud=bool(raw.get("stark_hud", True)),
    )
