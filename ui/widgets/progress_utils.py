from PySide6.QtCore import Qt
from PySide6.QtGui import QColor


def _gradient_colors(accent: str):
    base = QColor(accent)
    light = base.lighter(140).name()
    mid = base.name()
    dark = base.darker(130).name()
    return light, mid, dark


def style_progress_bar(
    progress_bar,
    accent: str = "#0F766E",
    *,
    theme: str = "Light",
    show_text: bool = True,
    min_height: int = 12,
    max_height: int = 16,
):
    text_color = "#F8FAFC" if theme in ["Dark"] else "#0F172A"
    container_bg = "rgba(255,255,255,0.04)" if theme in ["Dark"] else "rgba(15,23,42,0.08)"
    border_color = "rgba(255,255,255,0.18)" if theme in ["Dark"] else "rgba(15,23,42,0.25)"
    light, mid, dark = _gradient_colors(accent)

    style = f"""
    QProgressBar {{
        background: {container_bg};
        border-radius: 10px;
        border: 1px solid {border_color};
        min-height: {min_height}px;
        max-height: {max_height}px;
        color: {text_color};
        font-weight: 600;
        font-size: 10pt;
        text-align: center;
    }}
    QProgressBar::chunk {{
        border-radius: 10px;
        margin: 0;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 {light}, stop:0.5 {mid}, stop:1 {dark});
    }}
    """
    progress_bar.setStyleSheet(style)
    progress_bar.setTextVisible(show_text)
    if show_text:
        progress_bar.setFormat(progress_bar.format() or "%p%")
    progress_bar.setAlignment(Qt.AlignCenter)
