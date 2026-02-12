from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from PySide6.QtCore import Qt
from ui.resources.icons import Icons


class EmptyState(QWidget):
    def __init__(self, title, body, icon_name=None, action_text=None, action_cb=None, icon_color="#888888", parent=None):
        super().__init__(parent)
        self.setObjectName("emptyState")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(8)

        if icon_name:
            icon = QLabel()
            icon.setObjectName("emptyStateIcon")
            icon.setAlignment(Qt.AlignCenter)
            icon.setPixmap(Icons.get_icon(icon_name, icon_color).pixmap(24, 24))
            layout.addWidget(icon)

        title_lbl = QLabel(title)
        title_lbl.setObjectName("emptyStateTitle")
        title_lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_lbl)

        body_lbl = QLabel(body)
        body_lbl.setObjectName("emptyStateBody")
        body_lbl.setAlignment(Qt.AlignCenter)
        body_lbl.setWordWrap(True)
        layout.addWidget(body_lbl)

        if action_text and action_cb:
            btn = QPushButton(action_text)
            btn.setObjectName("emptyStateAction")
            btn.clicked.connect(action_cb)
            layout.addWidget(btn, alignment=Qt.AlignCenter)
