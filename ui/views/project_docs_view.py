import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QPushButton, QLabel, QComboBox)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices, QIcon
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons

class ProjectDocsView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.project_path = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Toolbar
        h = QHBoxLayout()
        self.lbl_path = QLabel("No Project Selected")
        h.addWidget(self.lbl_path)
        
        h.addStretch()
        
        self.combo_filter = QComboBox()
        self.combo_filter.addItems(["All Files", "PDFs (*.pdf)", "Images (*.png *.jpg)", "Text (*.txt *.md)"])
        self.combo_filter.currentTextChanged.connect(self.refresh_list)
        h.addWidget(self.combo_filter)
        
        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.clicked.connect(self.refresh_list)
        h.addWidget(btn_refresh)
        
        btn_open_folder = QPushButton("📂 Open Folder")
        btn_open_folder.clicked.connect(self.open_folder)
        h.addWidget(btn_open_folder)
        
        layout.addLayout(h)
        
        # File List
        self.list_files = QListWidget()
        self.list_files.itemDoubleClicked.connect(self.open_file)
        layout.addWidget(self.list_files)
        
        # Instructions
        lbl_hint = QLabel("Double-click to open file. Files are scanned from the project directory.")
        lbl_hint.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(lbl_hint)

    def load_data(self, project_name, data):
        self.project_path = self.logic.resolve_path(data["metadata"].get("location", ""))
        self.lbl_path.setText(f"Location: {self.logic.relativize_path(self.project_path)}")
        self.refresh_list()

    def refresh_list(self):
        self.list_files.clear()
        if not self.project_path or not os.path.exists(self.project_path):
            return

        ext_filter = self.combo_filter.currentText()
        extensions = []
        if "PDF" in ext_filter: extensions = [".pdf"]
        elif "Images" in ext_filter: extensions = [".png", ".jpg", ".jpeg"]
        elif "Text" in ext_filter: extensions = [".txt", ".md"]
        
        try:
            for root, dirs, files in os.walk(self.project_path):
                # Skip hidden folders and backups
                dirs[:] = [d for d in dirs if not d.startswith('.') and "backup" not in d and "backups" not in d]
                
                for f in files:
                    if extensions and not any(f.lower().endswith(e) for e in extensions):
                        continue
                    
                    # Skip KiCad temporary files
                    if f.endswith(".kicad_prl") or f.endswith(".lck") or f.endswith(".bak") or f.endswith(".kicad_pcb") or f.endswith(".kicad_sch"):
                        continue
                        
                    full_path = os.path.join(root, f)
                    rel_path = os.path.relpath(full_path, self.project_path)
                    
                    item = QListWidgetItem(rel_path)
                    item.setData(Qt.UserRole, full_path)
                    item.setIcon(self._icon_for_file(f, full_path))
                    
                    self.list_files.addItem(item)
        except Exception as e:
            print(f"Error scanning docs: {e}")

    def _icon_for_file(self, filename, full_path):
        ext = os.path.splitext(filename)[1].lower()
        theme = self.logic.settings.get("theme", "Light")
        is_dark = theme in ["Dark"]
        color = "#E0E0E0" if is_dark else "#555555"

        if ext in {".pdf"}:
            return Icons.get_icon(Icons.FILE_PDF, color)
        if ext in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg"}:
            return Icons.get_icon(Icons.FILE_IMAGE, color)
        if ext in {".txt", ".md", ".rtf", ".log"}:
            return Icons.get_icon(Icons.FILE_TEXT, color)
        if ext in {".csv", ".tsv", ".xlsx", ".xls"}:
            return Icons.get_icon(Icons.FILE_SHEET, color)
        if ext in {".zip", ".7z", ".rar", ".tar", ".gz"}:
            return Icons.get_icon(Icons.FILE_ARCHIVE, color)
        if ext in {".kicad_pcb", ".kicad_sch", ".kicad_sym", ".kicad_mod", ".step", ".stp"}:
            return Icons.get_icon(Icons.FILE_CAD, color)
        if ext in {".py", ".js", ".ts", ".json", ".yaml", ".yml", ".ini", ".cfg"}:
            return Icons.get_icon(Icons.FILE_CODE, color)
        return Icons.get_icon(Icons.FILE_GENERIC, color)

    def open_file(self, item):
        path = item.data(Qt.UserRole)
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def open_folder(self):
        if self.project_path and os.path.exists(self.project_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_path))
