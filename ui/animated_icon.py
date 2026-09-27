from PySide6.QtWidgets import QWidget
from PySide6.QtCore import QTimer, QSize, QRectF, Qt, Signal
from PySide6.QtGui import QPainter, QColor
from PySide6.QtSvg import QSvgRenderer
import math
import os

class AnimatedSvgIcon(QWidget):
    """Render an SVG file and animate rotation/scale to produce a lively icon.
    Lightweight: renders SVG into the widget each frame using QSvgRenderer.
    """
    def __init__(self, svg_path: str, size: int = 64, parent=None):
        super().__init__(parent)
        self._path = svg_path
        self._renderer = None
        self._size = size
        self.setFixedSize(QSize(size, size))
        if os.path.exists(svg_path):
            try:
                self._renderer = QSvgRenderer(svg_path)
            except Exception:
                self._renderer = None
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)

    def _tick(self):
        self._t += 0.016
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        w = self.width()
        h = self.height()
        cx = w / 2
        cy = h / 2

        # background subtle radial glow
        glow = QColor(10, 150, 200, 25)
        painter.setBrush(glow)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - w * 0.6, cy - h * 0.6, w * 1.2, h * 1.2)

        if not self._renderer:
            # fallback: draw simple placeholder
            painter.setPen(QColor(60, 200, 255))
            painter.drawEllipse(4, 4, w - 8, h - 8)
            return

        # compute animated transform
        rot = math.degrees(self._t * 0.8) % 360
        scale = 0.9 + 0.08 * math.sin(self._t * 3.0)

        painter.translate(cx, cy)
        painter.rotate(rot)
        painter.scale(scale, scale)
        painter.translate(-cx, -cy)

        # render a soft outer glow by rendering the svg slightly scaled and translucent
        painter.save()
        painter.setOpacity(0.22)
        painter.scale(1.08, 1.08)
        target = QRectF((w - w) / 2, (h - h) / 2, w, h)
        self._renderer.render(painter, target)
        painter.restore()

        # render main svg
        painter.save()
        painter.setOpacity(1.0)
        target = QRectF(0, 0, w, h)
        self._renderer.render(painter, target)
        painter.restore()

    def sizeHint(self) -> QSize:
        return QSize(self._size, self._size)

class ModeTile(QWidget):
    clicked = Signal()

    def __init__(self, label: str, svg_path: str, key: str, parent=None):
        super().__init__(parent)
        from PySide6.QtWidgets import QVBoxLayout, QLabel
        self._key = key
        layout = QVBoxLayout(self)
        layout.setSpacing(6)
        layout.setContentsMargins(6,6,6,6)
        self.icon = AnimatedSvgIcon(svg_path, size=72)
        self.title = QLabel(label)
        self.title.setAlignment(Qt.AlignCenter)
        self.title.setStyleSheet('color:#eafcff; font-weight:700;')
        layout.addWidget(self.icon, alignment=Qt.AlignCenter)
        layout.addWidget(self.title)
        self.setStyleSheet('background:transparent;')

    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

    def key(self):
        return self._key
