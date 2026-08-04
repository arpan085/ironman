"""Main application window and layout."""
from typing import Optional
import logging
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton,
    QFrame, QSizePolicy
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
# Prefer the GPU-accelerated OpenGL core when available
try:
    from ui.opengl_core import AICoreGLWidget as AICoreWidget
except Exception:
    from ui.dashboard import AICoreWidget  # fallback to CPU painter-based core

from ui.chat import ChatPanel
from voice.speech import SpeechWorker
from voice.tts import TTSWorker
from ai.assistant import Assistant
from themes.cyber import load_stylesheet

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Futuristic AI Assistant")
        self.resize(1200, 800)

        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(10, 10, 10, 10)
        root_layout.setSpacing(8)

        # Top bar
        top_bar = self._build_top_bar()
        root_layout.addWidget(top_bar)

        # Main content
        main_content = QHBoxLayout()
        main_content.setSpacing(8)
        root_layout.addLayout(main_content, 1)

        # Left panel (system info + diagnostics)
        left_panel = QFrame()
        left_panel.setFrameShape(QFrame.StyledPanel)
        left_panel.setMaximumWidth(320)
        left_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        left_layout = QVBoxLayout(left_panel)
        self.sys_label = QLabel("System\nCPU: --\nRAM: --\nGPU: --", alignment=Qt.AlignTop)
        left_layout.addWidget(self.sys_label)

        # diagnostics panel (OpenGL / shader / FBO info)
        try:
            from ui.diagnostics import DiagnosticsPanel
            self.diagnostics = DiagnosticsPanel()
            left_layout.addWidget(self.diagnostics)
        except Exception:
            self.diagnostics = None

        main_content.addWidget(left_panel)

        # Center AI core
        self.ai_core = AICoreWidget()
        main_content.addWidget(self.ai_core, 2)

        # Right panel (chat)
        self.chat = ChatPanel()
        self.chat.setMaximumWidth(420)
        main_content.addWidget(self.chat, 1)

        # If diagnostics available, populate with current info
        if self.diagnostics and hasattr(self.ai_core, 'get_diagnostics'):
            diag = self.ai_core.get_diagnostics()
            gl_info = diag.get('gl_version', 'GL: unknown')
            fbo_ok = diag.get('fbo_supported', False)
            shader_log = diag.get('shader_log', None)
            self.diagnostics.update_info(gl_info, fbo_ok, shader_log)

        # Bottom bar (voice controls)
        bottom = self._build_bottom_bar()
        root_layout.addWidget(bottom)

        # Assistant and audio workers
        self.assistant = Assistant()
        self.tts = TTSWorker()
        self.speech_worker = SpeechWorker()
        self.speech_worker.transcribed.connect(self._on_transcribed)
        self.speech_worker.error.connect(self._on_listen_error)

        # Connect chat input to assistant
        self.chat.send_message_requested.connect(self._handle_user_message)

        # Apply theme stylesheet
        self.setStyleSheet(load_stylesheet())

        # Show animated launcher on startup
        try:
            from ui.launcher import Launcher
            self._launcher = Launcher(self)
            self._launcher.setGeometry(self._center_launcher_geometry())
            self._launcher.mode_selected.connect(self._on_mode_selected)
            self._launcher.show()
            self._current_mode = None
        except Exception:
            self._launcher = None
            self._current_mode = None

    def _center_launcher_geometry(self):
        # return QRect centered within the main window for the launcher
        w = 760
        h = 420
        geo = self.geometry()
        x = geo.x() + max(20, (geo.width() - w) // 2)
        y = geo.y() + max(40, (geo.height() - h) // 2)
        from PySide6.QtCore import QRect
        return QRect(x, y, w, h)

    def _on_mode_selected(self, mode_key: str):
        # Update UI to reflect selected mode, and provide visual confirmation
        self._current_mode = mode_key
        if mode_key == 'jarvis':
            self.chat.append_system_message("Jarvis awakened. Listening for commands...")
            # optionally start continuous listening
            # self.speech_worker.start_listening()
        else:
            self.chat.append_system_message(f"Mode selected: {mode_key}")
        # reflect selection in left panel system label
        self.sys_label.setText(f"System\nMode: {mode_key}\nCPU: --\nRAM: --\nGPU: --")

    # keyboard shortcuts handling
    def keyPressEvent(self, event):
        key = event.key()
        # numeric keys 1-9
        from PySide6.QtCore import Qt
        if Qt.Key_1 <= key <= Qt.Key_9:
            idx = key - Qt.Key_0
            self._on_mode_selected(str(idx))
            return
        # F1-F12 mapping
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            idx = key - Qt.Key_F1 + 1
            self._on_mode_selected(f"F{idx}")
            return
        super().keyPressEvent(event)

    def _build_top_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(bar)
        layout.addWidget(QLabel("AI: Online"))
        layout.addStretch()
        layout.addWidget(QLabel("Time: --"))
        layout.addWidget(QLabel("Weather: Sunny 25°C"))
        return bar

    def _build_bottom_bar(self) -> QFrame:
        bar = QFrame()
        bar.setFrameShape(QFrame.StyledPanel)
        layout = QHBoxLayout(bar)
        self.mic_btn = QPushButton("🎤 Listen")
        self.mic_btn.setCheckable(True)
        self.mic_btn.clicked.connect(self._toggle_listen)
        layout.addWidget(self.mic_btn)
        layout.addStretch()
        self.speak_btn = QPushButton("🔊 Speak Test")
        self.speak_btn.clicked.connect(self._speak_test)
        layout.addWidget(self.speak_btn)
        return bar

    @Slot()
    def _toggle_listen(self, checked: bool):
        if checked:
            self.mic_btn.setText("🔴 Listening...")
            self.speech_worker.start_listening()
        else:
            self.mic_btn.setText("🎤 Listen")
            self.speech_worker.stop_listening()

    @Slot(str)
    def _on_transcribed(self, text: str):
        # When speech is transcribed, add to chat and request an assistant reply
        self.chat.append_user_message(text)
        self._handle_user_message(text)
        self.mic_btn.setChecked(False)
        self.mic_btn.setText("🎤 Listen")

    @Slot(str)
    def _on_listen_error(self, err: str):
        self.chat.append_system_message(f"[listen error] {err}")
        self.mic_btn.setChecked(False)
        self.mic_btn.setText("🎤 Listen")

    def _handle_user_message(self, text: str):
        # display typing animation
        self.chat.append_ai_typing()
        # ask assistant in background (non-blocking)
        def _ask():
            reply = self.assistant.ask(text)
            return reply

        # Use a timer single-shot to avoid blocking GUI thread (simple approach)
        QTimer.singleShot(100, lambda: self._deliver_reply(self.assistant.ask(text)))

    def _deliver_reply(self, reply: str):
        self.chat.append_ai_message(reply)
        # speak it
        self.tts.speak(reply)

    def _speak_test(self):
        self.tts.speak("Hello. This is a test voice from the Futuristic AI assistant.")
