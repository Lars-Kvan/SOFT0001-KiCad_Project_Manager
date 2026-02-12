from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLineEdit, QListWidget, QListWidgetItem

from ui.widgets.modal_utils import apply_modal_style


class ActionPalette(QDialog):
    def __init__(self, parent=None, actions=None):
        super().__init__(parent)
        self.setWindowTitle("Quick Actions")
        self.setModal(True)
        self.setMinimumWidth(400)
        self._actions = actions or []
        self._filtered = []
        self._build_ui()
        apply_modal_style(self, title="Quick Actions", accent="#2F6BFF")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.search = QLineEdit()
        self.search.setPlaceholderText("Type to filter actions...")
        self.search.textChanged.connect(self._apply_filter)
        layout.addWidget(self.search)

        self.list = QListWidget()
        self.list.itemActivated.connect(self._activate_selected)
        layout.addWidget(self.list)

        self._apply_filter()

    def _apply_filter(self):
        text = self.search.text().strip().lower()
        self.list.clear()
        self._filtered = []
        for label, callback in self._actions:
            if text and text not in label.lower():
                continue
            item = QListWidgetItem(label)
            self.list.addItem(item)
            self._filtered.append((label, callback))
        if self.list.count() > 0:
            self.list.setCurrentRow(0)

    def _activate_selected(self):
        row = self.list.currentRow()
        if row < 0 or row >= len(self._filtered):
            return
        _, callback = self._filtered[row]
        if callback:
            callback()
        self.accept()

    def keyPressEvent(self, event):
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._activate_selected()
            return
        super().keyPressEvent(event)
