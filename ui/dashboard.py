from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QColor, QPen, QBrush
from PySide6.QtCore import Qt, QTimer, QRectF
import math

class AICoreWidget(QWidget):
    """Animated holographic AI core widget using QPainter.
    Lightweight and CPU-friendly; animates at ~60 FPS using a QTimer.
    Designed as an extensible spot for OpenGL/shader upgrade later.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(400, 400)
        self._t = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(16)  # ~60 FPS

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
        radius = min(w, h) * 0.35

        # Background subtle vignette
        grad = QBrush(QColor(5, 10, 20))
        painter.fillRect(self.rect(), grad)

        # Moving grid / scanlines
        painter.save()
        painter.setOpacity(0.06)
        pen = QPen(QColor(0, 120, 180))
        pen.setWidth(1)
        painter.setPen(pen)
        spacing = 24
        offset = (self._t * 40) % spacing
        for x in range(0, w, spacing):
            painter.drawLine(x + offset, 0, x + offset, h)
        for y in range(0, h, spacing):
            painter.drawLine(0, y + offset, w, y + offset)
        painter.restore()

        # Draw concentric rotating rings
        rings = 5
        for i in range(rings):
            r = radius * (0.4 + i * 0.12)
            alpha = int(80 - i * 10)
            color = QColor(30, 200 - i * 30, 255)
            color.setAlpha(max(alpha, 10))
            pen = QPen(color)
            pen.setWidth(2 if i % 2 == 0 else 1)
            painter.setPen(pen)
            # rotate arc
            start = (self._t * (20 + i * 10) + i * 40) % 360
            span = 280 - i * 30
            rect = QRectF(cx - r, cy - r, r * 2, r * 2)
            painter.drawArc(rect, int(start * 16), int(span * 16))

        # Inner rotating hexagon
        painter.save()
        painter.translate(cx, cy)
        angle = (self._t * 40) % 360
        painter.rotate(angle)
        hex_r = radius * 0.35
        path_color = QColor(100, 220, 255, 200)
        pen = QPen(path_color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(QBrush(QColor(10, 40, 60, 100)))
        points = []
        for k in range(6):
            a = math.radians(60 * k)
            x = math.cos(a) * hex_r
            y = math.sin(a) * hex_r
            points.append((x, y))
        # draw polygon
        for i in range(len(points)):
            x1, y1 = points[i]
            x2, y2 = points[(i + 1) % len(points)]
            painter.drawLine(x1, y1, x2, y2)
        painter.restore()

        # Energy pulse center
        pulse = 0.6 + 0.4 * (0.5 + 0.5 * math.sin(self._t * 4))
        center_r = radius * 0.12 * pulse
        glow_color = QColor(50, 220, 255, 200)
        painter.setBrush(glow_color)
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(cx - center_r, cy - center_r, center_r * 2, center_r * 2)

        # Orbiting particles
        painter.setPen(Qt.NoPen)
        for p in range(8):
            ang = self._t * (50 + p * 7) + p * 45
            pr = radius * (0.6 + 0.15 * math.sin(self._t * (1 + p * 0.1)))
            x = cx + math.cos(math.radians(ang)) * pr
            y = cy + math.sin(math.radians(ang)) * pr
            painter.setBrush(QColor(120, 220, 255, 220))
            painter.drawEllipse(x - 4, y - 4, 8, 8)

        # Radar sweep
        painter.setOpacity(0.08)
        sweep_angle = (self._t * 120) % 360
        painter.setBrush(QColor(0, 150, 200))
        painter.setPen(Qt.NoPen)
        sweep_path_r = radius * 0.9
        painter.drawPie(QRectF(cx - sweep_path_r, cy - sweep_path_r, sweep_path_r * 2, sweep_path_r * 2), int((sweep_angle - 6) * 16), int(12 * 16))

        painter.end()
