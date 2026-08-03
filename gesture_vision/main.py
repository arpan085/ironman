"""CLI entrypoint for running the gesture suite."""

from __future__ import annotations

import argparse

from .app import GestureVisionApp


def main() -> None:
    """Build and run the application."""

    parser = argparse.ArgumentParser(description="Run the Ironman Gesture Vision Suite.")
    parser.add_argument("--no-splash", action="store_true", help="Skip startup splash screen.")
    args = parser.parse_args()
    app = GestureVisionApp(show_splash_override=not args.no_splash)
    app.run()


if __name__ == "__main__":
    main()
