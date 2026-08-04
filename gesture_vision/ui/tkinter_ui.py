"""Elegant, interactive dark-themed Tkinter sidebar launcher."""

from __future__ import annotations

import threading
import tkinter as tk
from typing import Callable


class SidebarUI:
    """Professional sidebar launcher with interactive shortcuts and smooth interactions."""

    # Refined color palette
    BG_PRIMARY = "#0d0d0d"      # Nearly black, better than #111111
    BG_SECONDARY = "#1a1a1a"    # Subtle elevation
    BG_HOVER = "#242424"        # Interactive states
    FG_PRIMARY = "#ffffff"      # Clean white
    FG_SECONDARY = "#b0b0b0"    # Muted for secondary text
    ACCENT = "#00d9ff"          # Refined cyan
    ACCENT_HOVER = "#00f0ff"    # Brighter on interaction

    def __init__(
        self,
        title: str,
        shortcuts: list[tuple[str, str, Callable[[], None] | None]] | None = None,
        width: int = 360,
        height: int = 560,
        fullscreen: bool = False,
    ) -> None:
        """Initialize sidebar with title, shortcuts, and optional callbacks.

        Args:
            title: Window title and header text
            shortcuts: List of (name, keybind, callback) tuples. Callback is optional.
            width: Window width in pixels
            height: Window height in pixels
        """
        self.title = title
        self.shortcuts = shortcuts or []
        self.width = width
        self.height = height
        self._thread: threading.Thread | None = None
        self._root: tk.Tk | None = None
        self._fullscreen = fullscreen

    def start(self) -> None:
        """Launch the sidebar in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Render the polished dark-themed sidebar."""
        self._root = tk.Tk()
        self._root.title(self.title)
        self._root.configure(bg=self.BG_PRIMARY)
        if self._fullscreen:
            # Use a true fullscreen window; ESC will exit
            self._root.attributes("-fullscreen", True)
        else:
            self._root.geometry(f"{self.width}x{self.height}")
            self._root.resizable(False, False)

        # Header with title
        self._create_header()

        # Shortcuts container
        self._create_shortcuts_frame()

        # Optional: Add footer with subtle info
        self._create_footer()

        self._root.mainloop()

    def _create_header(self) -> None:
        """Build the header section with title and subheading."""
        header = tk.Frame(self._root, bg=self.BG_PRIMARY)
        header.pack(fill="x", padx=0, pady=0)

        # Main title with refined styling
        title_label = tk.Label(
            header,
            text=self.title,
            fg=self.ACCENT,
            bg=self.BG_PRIMARY,
            font=("Segoe UI", 18, "bold"),
            pady=16,
        )
        title_label.pack()

        # Subtle divider
        divider = tk.Frame(header, bg=self.BG_SECONDARY, height=1)
        divider.pack(fill="x", padx=24)

        # Subheading
        subtitle = tk.Label(
            header,
            text="Quick Launch",
            fg=self.FG_SECONDARY,
            bg=self.BG_PRIMARY,
            font=("Segoe UI", 9),
            pady=12,
        )
        subtitle.pack()

    def _create_shortcuts_frame(self) -> None:
        """Build the interactive shortcuts list."""
        container = tk.Frame(self._root, bg=self.BG_PRIMARY)
        container.pack(fill="both", expand=True, padx=16, pady=12)

        for name, keybind, callback in self.shortcuts:
            self._create_shortcut_button(container, name, keybind, callback)

    def _create_shortcut_button(
        self,
        parent: tk.Frame,
        name: str,
        keybind: str,
        callback: Callable[[], None] | None,
    ) -> None:
        """Create an individual interactive shortcut button."""
        button_frame = tk.Frame(
            parent,
            bg=self.BG_SECONDARY,
            highlightthickness=0,
            relief="flat",
        )
        button_frame.pack(fill="x", pady=6)

        # Make the frame clickable
        def on_enter(event: tk.Event) -> None:
            button_frame.configure(bg=self.BG_HOVER)
            name_label.configure(fg=self.FG_PRIMARY)
            keybind_label.configure(fg=self.ACCENT_HOVER)

        def on_leave(event: tk.Event) -> None:
            button_frame.configure(bg=self.BG_SECONDARY)
            name_label.configure(fg=self.FG_PRIMARY)
            keybind_label.configure(fg=self.ACCENT)

        def on_click(event: tk.Event) -> None:
            if callback:
                callback()

        button_frame.bind("<Enter>", on_enter)
        button_frame.bind("<Leave>", on_leave)
        button_frame.bind("<Button-1>", on_click)

        # Left side: shortcut name
        name_label = tk.Label(
            button_frame,
            text=name,
            fg=self.FG_PRIMARY,
            bg=self.BG_SECONDARY,
            font=("Segoe UI", 11),
            anchor="w",
            padx=14,
            pady=10,
        )
        name_label.pack(side="left", fill="x", expand=True)
        name_label.bind("<Enter>", on_enter)
        name_label.bind("<Leave>", on_leave)
        name_label.bind("<Button-1>", on_click)

        # Right side: keybind indicator
        keybind_label = tk.Label(
            button_frame,
            text=keybind,
            fg=self.ACCENT,
            bg=self.BG_SECONDARY,
            font=("Segoe UI", 9, "bold"),
            anchor="e",
            padx=14,
            pady=10,
        )
        keybind_label.pack(side="right")
        keybind_label.bind("<Enter>", on_enter)
        keybind_label.bind("<Leave>", on_leave)
        keybind_label.bind("<Button-1>", on_click)

    def _create_footer(self) -> None:
        """Add a subtle footer with version or info."""
        footer = tk.Frame(self._root, bg=self.BG_PRIMARY)
        footer.pack(fill="x", padx=24, pady=12, side="bottom")

        divider = tk.Frame(footer, bg=self.BG_SECONDARY, height=1)
        divider.pack(fill="x", pady=(0, 8))

        info = tk.Label(
            footer,
            text="Click any shortcut to launch • Press ESC to close",
            fg=self.FG_SECONDARY,
            bg=self.BG_PRIMARY,
            font=("Segoe UI", 8),
        )
        info.pack()

        # Bind ESC to close
        if self._root:
            self._root.bind("<Escape>", lambda e: self._root.quit())


# Example usage
if __name__ == "__main__":
    def launch_editor() -> None:
        print("Launching editor...")

    def launch_terminal() -> None:
        print("Launching terminal...")

    def launch_settings() -> None:
        print("Opening settings...")

    shortcuts = [
        ("New File", "⌘N", lambda: print("New file")),
        ("Open Project", "⌘O", lambda: print("Open project")),
        ("Recent Files", "⌘R", launch_editor),
        ("Terminal", "⌘T", launch_terminal),
        ("Search", "⌘K", lambda: print("Search")),
        ("Settings", "⌘,", launch_settings),
        ("Documentation", "?", lambda: print("Docs")),
        ("About", None, lambda: print("About")),
    ]

    sidebar = SidebarUI("DevBox", shortcuts, width=380, height=580)
    sidebar.start()

    # Keep the main thread alive
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
