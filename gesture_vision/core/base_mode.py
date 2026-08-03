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

    def on_key(self, key: int) -> bool:
        """Handle a key event before global shortcuts. Return True if consumed."""

        return False

    @abstractmethod
    def process(self, frame: Any, landmarks: dict[str, Any], context: dict[str, Any]) -> Any:
        """Process a frame and return a rendered frame."""
