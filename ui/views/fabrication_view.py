import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QListWidgetItem, QPushButton, QLabel, QGroupBox)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons

class FabricationView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.project_path = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        
        # Toolbar
        h = QHBoxLayout()
        self.lbl_status = QLabel("No Project Selected")
        h.addWidget(self.lbl_status)
        h.addStretch()
        
        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        btn_refresh.clicked.connect(self.refresh_list)
        h.addWidget(btn_refresh)
        
        btn_open_folder = QPushButton("Open Fab Folder")
        btn_open_folder.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        btn_open_folder.clicked.connect(self.open_folder)
        h.addWidget(btn_open_folder)
        
        layout.addLayout(h)

        # Gerbers
        gb_gerber = QGroupBox("Gerber Files")
        l_gerber = QVBoxLayout(gb_gerber)
        self.list_gerbers = QListWidget()
        l_gerber.addWidget(self.list_gerbers)
        layout.addWidget(gb_gerber)

        # Drill / Assembly
        gb_assembly = QGroupBox("Drill & Assembly Files")
        l_assembly = QVBoxLayout(gb_assembly)
        self.list_assembly = QListWidget()
        l_assembly.addWidget(self.list_assembly)
        layout.addWidget(gb_assembly)

    def load_data(self, project_name, data):
        self.project_path = self.logic.resolve_path(data["metadata"].get("location", ""))
        self.refresh_list()

    def refresh_list(self):
        self.list_gerbers.clear()
        self.list_assembly.clear()
        
        if not self.project_path or not os.path.exists(self.project_path):
            self.lbl_status.setText("Project path not found.")
            return

        self.lbl_status.setText(f"Scanning: {self.logic.relativize_path(self.project_path)}")
        
        gerber_exts = ['.gbr', '.gbl', '.gtl', '.gbs', '.gts', '.gbo', '.gto', '.gm1', '.gm2', '.gm3', '.gvp']
        drill_exts = ['.drl', '.nc', '.xnc']
        assembly_exts = ['.pos', '.csv', '.rpt']

        # Look for a "Gerber" or "Fabrication" subfolder first, otherwise scan root
        scan_dirs = [self.project_path]
        try:
            for d in os.listdir(self.project_path):
                full = os.path.join(self.project_path, d)
                if os.path.isdir(full) and d.lower() in ["gerber", "gerbers", "fabrication", "fab", "output", "plot", "plots"]:
                    scan_dirs.insert(0, full) # Prioritize specific folders
        except: pass

        found_files = set()

        for d in scan_dirs:
            if not os.path.exists(d): continue
            try:
                for f in os.listdir(d):
                    full_path = os.path.join(d, f)
                    if os.path.isfile(full_path):
                        if full_path in found_files: continue
                        
                        ext = os.path.splitext(f)[1].lower()
                        
                        if ext in gerber_exts:
                            self.add_item(self.list_gerbers, f, full_path)
                            found_files.add(full_path)
                        elif ext in drill_exts:
                            self.add_item(self.list_assembly, f, full_path)
                            found_files.add(full_path)
                        elif ext in assembly_exts and ("pos" in f.lower() or "bom" in f.lower() or "drill" in f.lower() or "loc" in f.lower()):
                            self.add_item(self.list_assembly, f, full_path)
                            found_files.add(full_path)
            except: pass

    def add_item(self, list_widget, name, path):
        item = QListWidgetItem(name)
        item.setData(Qt.UserRole, path)
        item.setToolTip(path)
        list_widget.addItem(item)

    def open_folder(self):
        if self.project_path and os.path.exists(self.project_path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.project_path))
