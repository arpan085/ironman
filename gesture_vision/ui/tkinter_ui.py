"""Stark Tech themed Tkinter sidebar for mode navigation."""

from __future__ import annotations

import threading
import tkinter as tk
from tkinter import ttk


class SidebarUI:
    """A sleek dark Stark Tech sidebar window for mode shortcuts."""

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
        """Create and render the Stark-themed scrollable sidebar UI."""

        root = tk.Tk()
        root.title(f"{self.title} // STARK HUD")
        root.configure(bg="#0c1015")
        root.geometry("380x640")

        # Header
        header_frame = tk.Frame(root, bg="#0c1015")
        header_frame.pack(fill="x", padx=14, pady=12)

        tk.Label(
            header_frame,
            text="STARK INDUSTRIES",
            fg="#00e5ff",
            bg="#0c1015",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            header_frame,
            text="Mark LXXXV Suite // J.A.R.V.I.S. Online",
            fg="#88ccdd",
            bg="#0c1015",
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(fill="x")

        # Scrollable container for modes
        container = tk.Frame(root, bg="#121820", highlightbackground="#00e5ff", highlightthickness=1)
        container.pack(fill="both", expand=True, padx=12, pady=6)

        canvas = tk.Canvas(container, bg="#121820", highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas, bg="#121820")

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all")),
        )
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw", width=340)
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Mousewheel scrolling
        canvas.bind_all("<MouseWheel>", lambda event: canvas.yview_scroll(int(-1 * (event.delta / 120)), "units"))

        # Render each shortcut row
        for name, shortcut in self.shortcuts:
            row = tk.Frame(scrollable_frame, bg="#121820")
            row.pack(fill="x", padx=10, pady=3)

            is_jarvis = "jarvis" in name.lower() or shortcut == "F21"
            text_color = "#00ffff" if is_jarvis else "#ffffff"
            badge_bg = "#003844" if is_jarvis else "#1e2936"

            tk.Label(
                row,
                text=name.replace("_", " ").title(),
                fg=text_color,
                bg="#121820",
                font=("Segoe UI", 9, "bold" if is_jarvis else "normal"),
                anchor="w",
            ).pack(side="left", fill="x", expand=True)

            tk.Label(
                row,
                text=f" {shortcut} ",
                fg="#00e5ff",
                bg=badge_bg,
                font=("Consolas", 9, "bold"),
                relief="flat",
            ).pack(side="right")

        # Footer
        footer = tk.Frame(root, bg="#0c1015")
        footer.pack(fill="x", padx=14, pady=10)
        tk.Label(
            footer,
            text="Press 'J' for J.A.R.V.I.S. Prompt | 'H' for Help Overlay",
            fg="#6699aa",
            bg="#0c1015",
            font=("Segoe UI", 8),
        ).pack()

        root.mainloop()
