"""Stylesheet for cyber / holographic theme.
Provides a lightweight Qt stylesheet to get the cyan/glass aesthetic.
"""

def load_stylesheet() -> str:
    return """
    QWidget { background: #041021; color: #9be9ff; font-family: 'Segoe UI', Arial; }
    QMainWindow { background: transparent; }
    QFrame { background: rgba(5,10,20,0.6); border: 1px solid rgba(60,200,255,0.08); border-radius:8px; }
    QLabel { color: #9be9ff; }
    QPushButton { background: qlineargradient(x1:0 y1:0, x2:1 y2:1, stop:0 rgba(10,40,60,0.6), stop:1 rgba(10,60,90,0.6)); color: #eafcff; border:1px solid rgba(70,200,255,0.12); padding:6px; border-radius:6px; }
    QPushButton:checked { background: rgba(0,140,200,0.9); box-shadow: 0px 0px 12px rgba(40,200,255,0.18); }
    QTextBrowser { background: rgba(2,8,16,0.5); border: 1px solid rgba(40,180,255,0.06); border-radius:6px; padding:8px; }
    QLineEdit { background: rgba(0,0,0,0.3); border:1px solid rgba(40,180,255,0.06); border-radius:6px; padding:6px; color:#bff6ff }
    """
