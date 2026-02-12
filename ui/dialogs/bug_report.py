import platform
import sys
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


class BugReportDialog(QDialog):
    def __init__(self, parent=None, log_path="bugs.txt"):
        super().__init__(parent)
        self._log_path = log_path
        self._text_edit = None

        self.setWindowTitle("Report Bug")
        self.resize(400, 300)
        self._build_ui()
        apply_modal_style(self, title="Report Bug", accent="#DC2626")

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Please describe the issue:"))

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
            QMessageBox.warning(self, "Empty", "Please enter a description.")
            return

        try:
            sys_info = f"System: {platform.system()} {platform.release()}\n"
            sys_info += f"Python: {sys.version}\n"
            sys_info += f"Platform: {platform.platform()}\n"

            with open(self._log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(f"{sys_info}\nUser Report:\n{text}\n{'-' * 50}\n")
            QMessageBox.information(self, "Submitted", "Thank you for your report! Saved to bugs.txt")
            self.accept()
        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Failed to save report: {exc}")
