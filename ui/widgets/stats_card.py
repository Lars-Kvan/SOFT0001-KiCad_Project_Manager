from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy
from PySide6.QtCore import Qt

from .elevation import apply_layered_elevation
from .spacing import apply_layout, SPACING


class StatsCard(QFrame):
    def __init__(self, title, value="-", accent=None, subtitle=None, icon=None, theme="Light", depth="primary"):
        super().__init__()
        self.setObjectName("statsCard")

        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        layout = QVBoxLayout(self)
        apply_layout(layout, margin="md", spacing="sm")

        if accent:
            self.accent_bar = QFrame()
            self.accent_bar.setObjectName("statsCardAccent")
            self.accent_bar.setFixedHeight(4)
            self.accent_bar.setStyleSheet(f"background-color: {accent}; border-radius: 2px;")
            layout.addWidget(self.accent_bar)

        header = QHBoxLayout()
        header.setContentsMargins(0, 0, 0, 0)
        header.setSpacing(SPACING["sm"])

        self.title_label = QLabel(title)
        self.title_label.setObjectName("statsCardTitle")
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        header.addWidget(self.title_label, 1)

        if icon:
            self.icon_label = QLabel()
            self.icon_label.setObjectName("statsCardIcon")
            self.icon_label.setPixmap(icon.pixmap(16, 16))
            self.icon_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            header.addWidget(self.icon_label, 0)
        else:
            self.icon_label = None

        layout.addLayout(header)

        self.value_label = QLabel(str(value))
        self.value_label.setObjectName("statsCardValue")
        self.value_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(self.value_label)

        self.subtitle_label = None
        if subtitle is not None:
            self.subtitle_label = QLabel(str(subtitle))
            self.subtitle_label.setObjectName("statsCardSubtitle")
            self.subtitle_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(self.subtitle_label)

        apply_layered_elevation(self, level=depth, theme=theme)

    def set_value(self, value):
        self.value_label.setText(str(value))

    def set_title(self, title):
        self.title_label.setText(str(title))

    def set_subtitle(self, subtitle):
        if self.subtitle_label is None:
            self.subtitle_label = QLabel("")
            self.subtitle_label.setObjectName("statsCardSubtitle")
            self.subtitle_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.layout().addWidget(self.subtitle_label)
        self.subtitle_label.setText(str(subtitle))
