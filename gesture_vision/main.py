"""CLI entrypoint for running the gesture suite."""

from __future__ import annotations

from .app import GestureVisionApp


def main() -> None:
    """Build and run the application."""

    app = GestureVisionApp()
    app.run()


if __name__ == "__main__":
    main()
