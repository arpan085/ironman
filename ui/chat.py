from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTextBrowser, QLineEdit, QPushButton, QHBoxLayout, QLabel
)
from PySide6.QtCore import Qt, Signal, QTimer

class ChatPanel(QWidget):
    send_message_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.history = QTextBrowser()
        self.history.setOpenExternalLinks(True)
        layout.addWidget(self.history, 1)

        input_row = QHBoxLayout()
        self.input = QLineEdit()
        self.input.setPlaceholderText("Type a message or press microphone to speak...")
        self.send_btn = QPushButton("Send")
        self.send_btn.clicked.connect(self._on_send)
        input_row.addWidget(self.input)
        input_row.addWidget(self.send_btn)
        layout.addLayout(input_row)

        self._typing_timer = QTimer(self)
        self._typing_timer.setInterval(500)
        self._typing_timer.timeout.connect(self._on_typing)
        self._showing_typing = False

    def _on_send(self):
        text = self.input.text().strip()
        if not text:
            return
        self.append_user_message(text)
        self.input.clear()
        self.send_message_requested.emit(text)

    def append_user_message(self, text: str):
        self.history.append(f"<div style='color:#8be9fd; font-weight:600;'>User:</div>")
        self.history.append(f"<div style='padding:6px; background:rgba(10,20,30,0.6); border-radius:6px;'>{text}</div>")

    def append_ai_typing(self):
        self._showing_typing = True
        self.history.append("<i style='color:#9be9ff;'>AI is typing...</i>")
        self._typing_timer.start()

    def _on_typing(self):
        if self._showing_typing:
            cursor = self.history.textCursor()
            self.history.ensureCursorVisible()
            self._typing_timer.stop()

    def append_ai_message(self, text: str):
        self._showing_typing = False
        self.history.append(f"<div style='color:#7afcff; font-weight:700;'>AI:</div>")
        # simple markdown-ish code block rendering
        safe = text.replace("<", "&lt;").replace(">", "&gt;")
        if '```' in safe:
            parts = safe.split('```')
            for i, p in enumerate(parts):
                if i % 2 == 0:
                    self.history.append(f"<div style='padding:6px;'>{p}</div>")
                else:
                    self.history.append(f"<pre style='background:#041021; padding:8px; border-radius:6px; color:#a8f0ff;'>{p}</pre>")
        else:
            self.history.append(f"<div style='padding:6px;'>{safe}</div>")

    def append_system_message(self, text: str):
        self.history.append(f"<div style='color:#f0b27a;'>{text}</div>")
