from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame, QSizePolicy
from PySide6.QtCore import Qt
from ui.widgets.spacing import apply_layout_margins, SPACING


class HeaderBar(QFrame):
    def __init__(self, title, subtitle="", parent=None):
        super().__init__(parent)
        self.setObjectName("tabHeader")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setMinimumHeight(56)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        content = QWidget(self)
        content_layout = QHBoxLayout(content)
        apply_layout_margins(
            content_layout,
            SPACING["md"],
            SPACING["sm"],
            SPACING["md"],
            SPACING["sm"],
            spacing="md",
        )

        left = QWidget(content)
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(SPACING["xs"])

        self.title_label = QLabel(title)
        self.title_label.setObjectName("tabHeaderTitle")
        left_layout.addWidget(self.title_label)

        self.subtitle_label = QLabel(subtitle)
        self.subtitle_label.setObjectName("tabHeaderSubtitle")
        self.subtitle_label.setVisible(bool(subtitle))
        left_layout.addWidget(self.subtitle_label)

        self.status_label = QLabel("")
        self.status_label.setObjectName("tabHeaderStatus")
        self.status_label.setVisible(False)
        left_layout.addWidget(self.status_label)

        content_layout.addWidget(left, 0, Qt.AlignVCenter)

        actions = QWidget(content)
        actions.setObjectName("tabHeaderActions")
        self.actions_layout = QHBoxLayout(actions)
        self.actions_layout.setContentsMargins(0, 0, 0, 0)
        self.actions_layout.setSpacing(SPACING["sm"])
        content_layout.addWidget(actions, 1, Qt.AlignRight | Qt.AlignVCenter)

        root.addWidget(content)

        divider = QFrame(self)
        divider.setObjectName("tabHeaderDivider")
        divider.setFixedHeight(1)
        root.addWidget(divider)

    def set_title(self, text):
        self.title_label.setText(text)

    def set_subtitle(self, text):
        self.subtitle_label.setText(text or "")
        self.subtitle_label.setVisible(bool(text))

    def set_status(self, text):
        self.status_label.setText(text or "")
        self.status_label.setVisible(bool(text))

    def add_action(self, widget, stretch=0):
        self.actions_layout.addWidget(widget, stretch)
        return widget
