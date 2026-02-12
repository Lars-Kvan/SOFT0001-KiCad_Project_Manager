from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

__all__ = ["StandardsTab"]


class StandardsTab(QWidget):
    """Lightweight placeholder while the standards/DRC view is under redesign."""

    def __init__(self, logic=None, parent=None):
        super().__init__(parent)
        self.logic = logic
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        label = QLabel("Standards guidance is coming soon.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        layout.addStretch(1)
