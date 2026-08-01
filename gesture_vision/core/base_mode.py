"""Base class for all gesture modes."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class BaseMode(ABC):
    """Defines the interface each mode must implement."""

    name: str = "base"
    shortcut: str = ""

    def on_enter(self) -> None:
        """Run setup when this mode becomes active."""

    def on_exit(self) -> None:
        """Run cleanup when this mode becomes inactive."""

    @abstractmethod
    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Process a frame and return a rendered frame."""

    def on_key(self, key: int, char: str) -> bool:
        """Consume a key event.

        ``key`` is the raw OpenCV key code, ``char`` the lowercase single
        character for printable keys. Return True when handled.
        """

        return False
