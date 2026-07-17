"""Mode registration and switching logic."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .base_mode import BaseMode


@dataclass(slots=True)
class ModeInfo:
    """Metadata describing a mode binding."""

    name: str
    shortcut: str


class ModeManager:
    """Holds all modes and exposes switch operations."""

    def __init__(self, modes: Iterable[BaseMode]) -> None:
        """Initialize with a non-empty mode iterable."""

        mode_list = list(modes)
        if not mode_list:
            raise ValueError("At least one mode is required")
        self._modes = {mode.name: mode for mode in mode_list}
        self._order = [mode.name for mode in mode_list]
        self._active = self._order[0]
        self._modes[self._active].on_enter()

    @property
    def active_mode(self) -> BaseMode:
        """Return the currently active mode instance."""

        return self._modes[self._active]

    def list_modes(self) -> list[ModeInfo]:
        """Return display metadata for sidebar/menu rendering."""

        return [ModeInfo(name=self._modes[name].name, shortcut=self._modes[name].shortcut) for name in self._order]

    def switch(self, name: str) -> BaseMode:
        """Switch active mode by name and return it."""

        if name not in self._modes:
            raise KeyError(f"Unknown mode: {name}")
        if name == self._active:
            return self.active_mode
        self._modes[self._active].on_exit()
        self._active = name
        self._modes[self._active].on_enter()
        return self.active_mode

    def switch_by_shortcut(self, shortcut: str) -> BaseMode | None:
        """Switch active mode by keyboard shortcut if mapped."""

        lowered = shortcut.lower()
        for name in self._order:
            if self._modes[name].shortcut.lower() == lowered:
                return self.switch(name)
        return None
