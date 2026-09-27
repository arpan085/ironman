"""CLI entrypoint for running the gesture suite.

Works both as a module (``python -m gesture_vision.main``) and when run
directly as a script (``python gesture_vision/main.py``).
"""

from __future__ import annotations

import argparse
import os
import sys


if __package__ in (None, ""):
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from gesture_vision.app import GestureVisionApp
    from gesture_vision.config import load_config
else:
    from .app import GestureVisionApp
    from .config import load_config


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options overriding the config file."""

    parser = argparse.ArgumentParser(prog="ironman", description="Ironman Gesture Vision Suite")
    parser.add_argument("--camera", type=int, help="camera index to use (default from config)")
    parser.add_argument("--fps", type=int, help="target frames per second")
    parser.add_argument("--sidebar", action="store_true", help="enable the Tkinter mode sidebar")
    parser.add_argument("--no-sidebar", action="store_true", help="disable the Tkinter mode sidebar")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> None:
    """Build and run the application."""

    args = _parse_args(argv)
    config = load_config()
    if args.camera is not None:
        config.camera_index = args.camera
    if args.fps is not None:
        config.target_fps = max(1, min(60, args.fps))
    if args.sidebar:
        config.sidebar_enabled = True
    if args.no_sidebar:
        config.sidebar_enabled = False

    try:
        app = GestureVisionApp(config)
        app.run()
    except RuntimeError as exc:
        print(f"\n[Ironman] {exc}", file=sys.stderr)
        sys.exit(1)
    except KeyboardInterrupt:
        print("\n[Ironman] Interrupted by user.")
        sys.exit(0)


if __name__ == "__main__":
    main()
