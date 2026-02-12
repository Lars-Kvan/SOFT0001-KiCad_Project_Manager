from PySide6.QtWidgets import QGraphicsDropShadowEffect
from PySide6.QtGui import QColor


def apply_elevation(widget, theme="Light", blur=18, y=4, alpha_light=35, alpha_dark=70):
    alpha = alpha_dark if theme in ["Dark"] else alpha_light
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(0, y)
    shadow.setColor(QColor(0, 0, 0, alpha))
    widget.setGraphicsEffect(shadow)


_DEPTH_LEVELS = {
    "flat": {"blur": 6, "y": 2, "alpha_light": 18, "alpha_dark": 36},
    "secondary": {"blur": 16, "y": 6, "alpha_light": 24, "alpha_dark": 52},
    "primary": {"blur": 30, "y": 10, "alpha_light": 48, "alpha_dark": 96},
    "hero": {"blur": 40, "y": 14, "alpha_light": 64, "alpha_dark": 110},
}


def apply_layered_elevation(widget, level="secondary", theme="Light"):
    config = _DEPTH_LEVELS.get(level, _DEPTH_LEVELS["secondary"])
    apply_elevation(
        widget,
        theme=theme,
        blur=config["blur"],
        y=config["y"],
        alpha_light=config["alpha_light"],
        alpha_dark=config["alpha_dark"],
    )
