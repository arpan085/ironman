"""Entrypoint for the Futuristic AI Desktop Assistant prototype."""
import sys
import logging
from PySide6.QtWidgets import QApplication
from app import MainWindow
from config import config

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main() -> None:
    logger.info("Starting %s", config.app_name)
    # Request a modern OpenGL context for the AI core (3.3 core profile)
    from PySide6.QtGui import QSurfaceFormat
    fmt = QSurfaceFormat()
    fmt.setRenderableType(QSurfaceFormat.OpenGL)
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.CoreProfile)
    fmt.setDepthBufferSize(24)
    QSurfaceFormat.setDefaultFormat(fmt)

    app = QApplication(sys.argv)
    # High-DPI scaling recommended for crisp rendering
    app.setAttribute(10001, True)  # Qt.AA_EnableHighDpiScaling (value-safe)

    window = MainWindow()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()
