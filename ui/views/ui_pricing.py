from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt

__all__ = ["PricingTab"]


class PricingTab(QWidget):
    """Minimal placeholder until the pricing integration is restored."""

    def __init__(self, logic=None, parent=None):
        super().__init__(parent)
        self.logic = logic
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignTop)
        label = QLabel("Pricing & supplier data is temporarily unavailable.")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)
        layout.addStretch(1)
