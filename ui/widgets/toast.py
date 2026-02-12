from PySide6.QtCore import QEasingCurve, QPoint, Qt, QPropertyAnimation, QTimer
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QWidget,
)

from ui.icons import Icons


class Toast(QWidget):
    def __init__(self, parent, text, duration_ms=2500, kind="success"):
        super().__init__(parent)
        self.setObjectName("toast")
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.duration_ms = duration_ms

        self.theme = self._detect_theme(parent)
        self.colors = self._kind_colors(kind)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        card = QFrame()
        card.setObjectName("toastCard")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 10, 16, 10)
        card_layout.setSpacing(12)

        icon_label = QLabel()
        icon_label.setObjectName("toastIcon")
        icon_label.setFixedSize(24, 24)
        icon_pixmap = Icons.get_icon(self.colors["icon"], color=self.colors["accent"]).pixmap(24, 24)
        icon_label.setPixmap(icon_pixmap)
        card_layout.addWidget(icon_label)

        label = QLabel(text)
        label.setObjectName("toastLabel")
        label.setWordWrap(True)
        card_layout.addWidget(label)
        card_layout.addStretch()

        layout.addWidget(card)

        self._apply_card_style(card, label)
        self._apply_shadow(card)

        self.adjustSize()
        self.final_pos = self._calculate_position()
        self.move(self.final_pos + QPoint(48, 0))
        self.setWindowOpacity(0)

        self._animate_in()

    def _detect_theme(self, parent):
        try:
            return parent.logic.settings.get("theme", "Light")
        except Exception:
            return "Light"

    def _kind_colors(self, kind):
        palette = {
            "success": {
                "accent": "#16A34A",
                "text": "#0F172A",
                "bg_light": "rgba(255,255,255,0.95)",
                "bg_dark": "rgba(15,23,42,0.9)",
                "icon": Icons.CHECK,
            },
            "info": {
                "accent": "#0EA5E9",
                "text": "#0F172A",
                "bg_light": "rgba(255,255,255,0.95)",
                "bg_dark": "rgba(15,23,42,0.9)",
                "icon": Icons.INFO,
            },
            "error": {
                "accent": "#EF4444",
                "text": "#0F172A",
                "bg_light": "rgba(255,255,255,0.95)",
                "bg_dark": "rgba(15,23,42,0.9)",
                "icon": Icons.ALERT,
            },
        }
        return palette.get(kind, palette["success"])

    def _apply_card_style(self, card, label):
        bg = self.colors["bg_dark"] if self.theme in ["Dark"] else self.colors["bg_light"]
        text_color = "#F8FAFC" if self.theme in ["Dark"] else self.colors["text"]
        accent = self.colors["accent"]
        card.setStyleSheet(
            f"""
            QFrame#toastCard {{
                background: {bg};
                border-radius: 14px;
                border-left: 4px solid {accent};
                color: {text_color};
            }}
            QLabel#toastLabel {{
                color: {text_color};
                font-weight: 600;
            }}
            """
        )

    def _apply_shadow(self, card):
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 10)
        shadow.setColor(QColor(0, 0, 0, 120 if self.theme in ["Dark"] else 80))
        card.setGraphicsEffect(shadow)

    def _calculate_position(self):
        parent = self.parent()
        if not parent:
            return QPoint(0, 0)
        parent_rect = parent.geometry()
        x = parent_rect.x() + parent_rect.width() - self.width() - 24
        y = parent_rect.y() + parent_rect.height() - self.height() - 32
        return QPoint(x, y)

    def _animate_in(self):
        self.move(self.final_pos + QPoint(48, 0))
        self.anim_pos_in = QPropertyAnimation(self, b"pos", self)
        self.anim_pos_in.setDuration(320)
        self.anim_pos_in.setEasingCurve(QEasingCurve.OutCubic)
        self.anim_pos_in.setStartValue(self.pos())
        self.anim_pos_in.setEndValue(self.final_pos)

        self.anim_opacity_in = QPropertyAnimation(self, b"windowOpacity", self)
        self.anim_opacity_in.setDuration(320)
        self.anim_opacity_in.setStartValue(0)
        self.anim_opacity_in.setEndValue(1.0)

        self.anim_pos_in.start()
        self.anim_opacity_in.start()
        self.anim_opacity_in.finished.connect(self._start_auto_dismiss)

    def _start_auto_dismiss(self):
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.setSingleShot(True)
        self.dismiss_timer.timeout.connect(self._animate_out)
        self.dismiss_timer.start(self.duration_ms)

    def _animate_out(self):
        self.anim_pos_out = QPropertyAnimation(self, b"pos", self)
        self.anim_pos_out.setDuration(260)
        self.anim_pos_out.setEasingCurve(QEasingCurve.InBack)
        self.anim_pos_out.setStartValue(self.pos())
        self.anim_pos_out.setEndValue(self.pos() + QPoint(48, 0))

        self.anim_opacity_out = QPropertyAnimation(self, b"windowOpacity", self)
        self.anim_opacity_out.setDuration(260)
        self.anim_opacity_out.setStartValue(self.windowOpacity())
        self.anim_opacity_out.setEndValue(0.0)

        self.anim_opacity_out.finished.connect(self.close)
        self.anim_pos_out.start()
        self.anim_opacity_out.start()


def show_toast(parent, text, duration_ms=2500, kind="success"):
    try:
        toast = Toast(parent, text, duration_ms, kind)
        toast.show()
    except Exception:
        pass
