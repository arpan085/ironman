from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QGridLayout, QHBoxLayout, QSizePolicy
)
from PySide6.QtCore import Qt, Signal, QPropertyAnimation, QEasingCurve, QRect
from PySide6.QtGui import QFont
from ui.animated_icon import ModeTile

class Launcher(QWidget):
    mode_selected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)

        self._init_ui()
        self._animate_in()

    def _init_ui(self):
        self.resize(760, 420)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)

        # Holographic title / logo
        title = QLabel("FUTURISTIC AI CONTROL CENTER")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet('color: #9be9ff; font-weight:800;')
        title.setFont(QFont('Segoe UI', 14))
        layout.addWidget(title)

        sub = QLabel("Select a mode or say 'Jarvis' to wake the assistant")
        sub.setAlignment(Qt.AlignCenter)
        sub.setStyleSheet('color: #bff6ff;')
        layout.addWidget(sub)

        # Mode tiles grid (1-9) using animated SVG icons
        grid = QGridLayout()
        grid.setSpacing(10)
        self._mode_buttons = {}
        # create ModeTile instances with animated icons
        for i in range(1, 10):
            svg_path = f"assets/icons/mode{i}.svg"
            tile = ModeTile(f"Mode {i}", svg_path, key=str(i))
            tile.setObjectName(f"mode_tile_{i}")
            tile.clicked.connect(lambda n=str(i): self._on_mode_clicked(n))
            r = (i - 1) // 3
            c = (i - 1) % 3
            grid.addWidget(tile, r, c)
            self._mode_buttons[str(i)] = tile

        # F-key row (F1-F6 shown for space)
        frow = QHBoxLayout()
        for i in range(1, 7):
            key = f"F{i}"
            svg_path = f"assets/icons/modeF{i}.svg"
            tile = ModeTile(f"{key}", svg_path, key=key)
            tile.clicked.connect(lambda k=key: self._on_mode_clicked(k))
            frow.addWidget(tile)
            self._mode_buttons[key] = tile

        layout.addLayout(grid)
        layout.addLayout(frow)

        # Bottom controls
        bottom = QHBoxLayout()
        self.jarvis_btn = QPushButton("Wake Jarvis")
        self.jarvis_btn.setCheckable(True)
        self.jarvis_btn.setStyleSheet(btn_style)
        self.jarvis_btn.clicked.connect(self._on_jarvis)
        bottom.addWidget(self.jarvis_btn)

        close_btn = QPushButton("Close")
        close_btn.setStyleSheet(btn_style)
        close_btn.clicked.connect(self._animate_out)
        bottom.addWidget(close_btn)

        layout.addLayout(bottom)

        # Outer styling
        self.setStyleSheet("QWidget { background: rgba(4,8,14,0.82); border: 1px solid rgba(50,200,255,0.06); border-radius:16px; }")

    def _on_mode_clicked(self, key):
        # Emit a normalized mode name
        self.mode_selected.emit(str(key))
        self._animate_out()

    def _on_jarvis(self, checked: bool):
        if checked:
            self.mode_selected.emit("jarvis")
        else:
            # toggling off doesn't select a mode
            pass

    def _animate_in(self):
        # Scale from small to full with opacity
        geom = self.geometry()
        start = QRect(geom.center().x(), geom.center().y(), 10, 6)
        end = geom
        self.setWindowOpacity(0.0)
        anim = QPropertyAnimation(self, b"geometry", self)
        anim.setDuration(520)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutBack)
        anim.start()
        op = QPropertyAnimation(self, b"windowOpacity", self)
        op.setDuration(420)
        op.setStartValue(0.0)
        op.setEndValue(1.0)
        op.setEasingCurve(QEasingCurve.InOutQuad)
        op.start()
        # keep references to prevent GC
        self._geom_anim = anim
        self._op_anim = op

    def _animate_out(self):
        # Fade out then close
        op = QPropertyAnimation(self, b"windowOpacity", self)
        op.setDuration(280)
        op.setStartValue(1.0)
        op.setEndValue(0.0)
        op.setEasingCurve(QEasingCurve.InBack)
        op.start()
        op.finished.connect(self.close)
        self._op_anim = op

    # keyboard handling for quick selection
    def keyPressEvent(self, event):
        key = event.key()
        if Qt.Key_1 <= key <= Qt.Key_9:
            idx = key - Qt.Key_0
            self._on_mode_clicked(str(idx))
            return
        if Qt.Key_F1 <= key <= Qt.Key_F12:
            idx = key - Qt.Key_F1 + 1
            self._on_mode_clicked(f"F{idx}")
            return
        super().keyPressEvent(event)
