from datetime import datetime

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QHBoxLayout,
    QPushButton,
    QMessageBox,
)

from ui.widgets.modal_utils import apply_modal_style


class FeatureRequestDialog(QDialog):
    def __init__(self, parent=None, log_path="feature_requests.txt"):
        super().__init__(parent)
        self._log_path = log_path
        self._text_edit = None

        self.setWindowTitle("Request Feature")
        self.resize(400, 320)
        self._build_ui()
        apply_modal_style(self, title="Request Feature", accent="#D97706")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("What would you like to see improved or added?"))

        self._text_edit = QTextEdit()
        layout.addWidget(self._text_edit)

        h_btns = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_submit = QPushButton("Submit")

        btn_submit.clicked.connect(self._submit)
        btn_cancel.clicked.connect(self.reject)

        h_btns.addWidget(btn_cancel)
        h_btns.addStretch()
        h_btns.addWidget(btn_submit)
        layout.addLayout(h_btns)

    def _submit(self):
        text = self._text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Empty", "Describe the feature you are requesting.")
            return

        try:
            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(f"{text}\n{'-' * 50}\n")
            QMessageBox.information(self, "Thanks", "Feature request saved.")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save request: {exc}")
