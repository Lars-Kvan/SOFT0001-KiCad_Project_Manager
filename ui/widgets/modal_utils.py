from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDialog,
    QFrame,
    QGraphicsBlurEffect,
    QGraphicsDropShadowEffect,
    QLabel,
    QLayout,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


_BLUR_STATE: Dict[QWidget, Dict] = {}


def _modal_gradient(accent: str) -> str:
    color = QColor(accent)
    start = color.lighter(150).name()
    end = color.darker(110).name()
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start}, stop:1 {end})"


def _restore_parent_blur(dialog: QDialog):
    try:
        parent = dialog.parentWidget()
    except RuntimeError:
        parent = None
    if not parent:
        return
    state = _BLUR_STATE.get(parent)
    if not state:
        return
    state["count"] -= 1
    if state["count"] <= 0:
        parent.setGraphicsEffect(state["original"])
        del _BLUR_STATE[parent]


def _apply_parent_blur(dialog: QDialog):
    parent = dialog.parentWidget()
    if not parent:
        return
    if parent not in _BLUR_STATE:
        original = parent.graphicsEffect()
        blur = QGraphicsBlurEffect(parent)
        blur.setBlurRadius(14)
        blur.setBlurHints(QGraphicsBlurEffect.QualityHint)
        parent.setGraphicsEffect(blur)
        _BLUR_STATE[parent] = {"count": 1, "original": original}
    else:
        _BLUR_STATE[parent]["count"] += 1


def _collect_layout_items(layout: QLayout):
    items = []
    while layout.count():
        item = layout.takeAt(0)
        if item.widget():
            widget = item.widget()
            widget.setParent(None)
            items.append(("widget", widget))
        elif item.layout():
            inner = item.layout()
            inner.setParent(None)
            items.append(("layout", inner))
        elif item.spacerItem():
            spacer = item.spacerItem()
            items.append(("spacer", spacer))
        else:
            # Some layouts may expose null entries; skip them.
            continue
    return items


def apply_modal_style(dialog: QDialog, title: str = None, accent: str = "#0F766E"):
    if not isinstance(dialog, QDialog) or dialog.property("_modal_styled"):
        return
    title_text = title or dialog.windowTitle() or "Dialog"
    dialog.setWindowTitle("")
    dialog.setProperty("_modal_styled", True)
    dialog.setWindowFlag(Qt.FramelessWindowHint, True)
    dialog.setAttribute(Qt.WA_TranslucentBackground, True)

    old_layout = dialog.layout()
    collected = _collect_layout_items(old_layout) if old_layout else []
    if old_layout:
        old_layout.deleteLater()
        dialog.setLayout(None)

    title_bar = QLabel(title_text)
    title_bar.setObjectName("modalTitleBar")
    title_bar.setAlignment(Qt.AlignCenter)
    title_bar.setFixedHeight(46)

    content_wrapper = QFrame()
    content_wrapper.setObjectName("modalContent")
    content_layout = QVBoxLayout(content_wrapper)
    content_layout.setContentsMargins(24, 24, 24, 24)
    content_layout.setSpacing(16)
    for kind, obj in collected:
        if kind == "widget":
            content_layout.addWidget(obj)
        elif kind == "layout":
            content_layout.addLayout(obj)
        elif kind == "spacer":
            content_layout.addItem(obj)

    if not collected:
        # Ensure the wrapper still stretches if no previous content existed.
        content_layout.addStretch()

    main_layout = QVBoxLayout()
    main_layout.setContentsMargins(0, 0, 0, 0)
    main_layout.setSpacing(0)
    main_layout.addWidget(title_bar)
    main_layout.addWidget(content_wrapper)
    dialog.setLayout(main_layout)

    accent_gradient = _modal_gradient(accent)
    title_bar_styles = (
        "font-weight: 600; font-size: 13pt; color: #F8FAFC;"
        "text-transform: uppercase; letter-spacing: 0.5px;"
    )

    base_sheet = f"""
    QDialog#modalDialog {{
        background-color: rgba(12, 17, 26, 0.96);
        border-radius: 22px;
        border: 1px solid rgba(255,255,255,0.18);
    }}
    QLabel#modalTitleBar {{
        background: {accent_gradient};
        border-top-left-radius: 22px;
        border-top-right-radius: 22px;
        {title_bar_styles}
    }}
    QFrame#modalContent {{
        background-color: rgba(18, 22, 38, 0.94);
        border-bottom-left-radius: 22px;
        border-bottom-right-radius: 22px;
    }}
    """
    previous_sheet = dialog.styleSheet()
    dialog.setStyleSheet(base_sheet + ("\n" + previous_sheet if previous_sheet else ""))
    dialog.setObjectName("modalDialog")

    shadow = QGraphicsDropShadowEffect(dialog)
    shadow.setBlurRadius(48)
    shadow.setOffset(0, 14)
    shadow.setColor(QColor(0, 0, 0, 160))
    dialog.setGraphicsEffect(shadow)

    _apply_parent_blur(dialog)
    if hasattr(dialog, "finished"):
        dialog.finished.connect(lambda *_ , d=dialog: _restore_parent_blur(d))
    dialog.destroyed.connect(lambda *_ , d=dialog: _restore_parent_blur(d))
