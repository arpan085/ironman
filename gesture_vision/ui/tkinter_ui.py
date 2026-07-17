"""Optional modern dark themed Tkinter shell."""

from __future__ import annotations

import threading
import tkinter as tk


class SidebarUI:
    """A simple sidebar launcher window for mode shortcuts."""

    def __init__(self, title: str, shortcuts: list[tuple[str, str]]) -> None:
        """Store title and mode shortcuts."""

        self.title = title
        self.shortcuts = shortcuts
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Run Tkinter in a background thread."""

        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        """Create and render the dark themed sidebar UI."""

        root = tk.Tk()
        root.title(self.title)
        root.configure(bg="#111111")
        root.geometry("340x520")
        tk.Label(root, text=self.title, fg="#00e5ff", bg="#111111", font=("Segoe UI", 16, "bold")).pack(pady=14)
        tk.Label(root, text="Shortcuts", fg="#bbbbbb", bg="#111111", font=("Segoe UI", 10)).pack(pady=4)
        frame = tk.Frame(root, bg="#1b1b1b")
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        for name, shortcut in self.shortcuts:
            row = tk.Frame(frame, bg="#1b1b1b")
            row.pack(fill="x", padx=8, pady=4)
            tk.Label(row, text=name, fg="#ffffff", bg="#1b1b1b", anchor="w", width=28).pack(side="left")
            tk.Label(row, text=shortcut, fg="#00e5ff", bg="#1b1b1b", anchor="e", width=7).pack(side="right")

        root.mainloop()
