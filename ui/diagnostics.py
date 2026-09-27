from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTextBrowser
from PySide6.QtCore import Qt

class DiagnosticsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        self.setFixedWidth(260)
        self.title = QLabel("Diagnostics")
        self.title.setStyleSheet('font-weight:700; color:#7afcff;')
        layout.addWidget(self.title)
        self.info = QLabel("GL: unknown\nFBO: unknown\nShader: unknown")
        self.info.setAlignment(Qt.AlignTop)
        layout.addWidget(self.info)
        self.log = QTextBrowser()
        self.log.setMaximumHeight(220)
        layout.addWidget(self.log)

    def update_info(self, gl_info: str, fbo_supported: bool, shader_log: str | None = None):
        fbo_text = 'yes' if fbo_supported else 'no'
        self.info.setText(f"{gl_info}\nFBO supported: {fbo_text}")
        if shader_log:
            self.log.setPlainText(shader_log)
