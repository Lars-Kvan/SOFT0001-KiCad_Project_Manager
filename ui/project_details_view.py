import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, 
                             QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, QFileDialog, QProgressBar)
from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QDesktopServices

class StructureScanWorker(QThread):
    finished = Signal(dict, int) # tree_data, total_parts
    error = Signal(str)

    def __init__(self, logic, path, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.path = path

    def run(self):
        try:
            tree_data = self.logic.get_subsheets_hierarchy(self.path)
            
            bom = self.logic.generate_bom(self.path)
            total = sum(item['qty'] for item in bom)
            
            self.finished.emit(tree_data, total)
        except Exception as e:
            self.error.emit(str(e))

class ProjectDetailsView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.current_project = None
        self.main_schematic_path = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Project Details Group
        details_gb = QGroupBox("Project Structure")
        details_layout = QVBoxLayout(details_gb)
        
        # Info Label
        self.lbl_current_sch = QLabel("Main Schematic: None")
        details_layout.addWidget(self.lbl_current_sch)
        
        # Part Count
        self.lbl_part_count = QLabel("Total Parts: -")
        self.lbl_part_count.setStyleSheet("font-weight: bold; color: #2980b9; font-size: 14px;")
        details_layout.addWidget(self.lbl_part_count)

        self.progress = QProgressBar()
        self.progress.setVisible(False)
        details_layout.addWidget(self.progress)

        # Sub-sheets tree
        self.tree_subsheets = QTreeWidget()
        self.tree_subsheets.setHeaderLabels(["Hierarchy", "Parts"])
        self.tree_subsheets.setColumnWidth(0, 300)
        self.tree_subsheets.setAlternatingRowColors(True)
        details_layout.addWidget(QLabel("Detected Sub-sheets:"))
        details_layout.addWidget(self.tree_subsheets)
        
        h_btns = QHBoxLayout()
        btn_scan_sheets = QPushButton("Rescan Structure")
        btn_scan_sheets.clicked.connect(self.scan_structure)
        h_btns.addWidget(btn_scan_sheets)
        
        btn_open = QPushButton("Open in KiCad")
        btn_open.clicked.connect(self.open_selected_sheet)
        h_btns.addWidget(btn_open)
        
        details_layout.addLayout(h_btns)
        
        layout.addWidget(details_gb)
        
        self.btn_save = QPushButton("Save Details")
        self.btn_save.setStyleSheet("font-weight: bold; height: 30px; background-color: #2ecc71; color: white;")
        layout.addWidget(self.btn_save)
        
        layout.addStretch()

    def load_data(self, project_name, data):
        self.current_project = project_name
        meta = data.get("metadata", {})
        structure = data.get("structure", {})
        
        self.main_schematic_path = meta.get("main_schematic", "")
        display_path = self.logic.relativize_path(self.main_schematic_path) if self.main_schematic_path else 'Not Set (Go to Status tab)'
        self.lbl_current_sch.setText(f"Main Schematic: {display_path}")
        
        # Use cached data if available to avoid re-scanning
        if structure and structure.get("tree"):
            self.populate_tree(structure["tree"], self.tree_subsheets)
            self.tree_subsheets.expandAll()
            self.lbl_part_count.setText(f"Total Parts: {structure.get('part_count', '-')}")
        elif self.main_schematic_path:
            self.scan_structure()
        else:
            self.tree_subsheets.clear()
            self.lbl_part_count.setText("Total Parts: -")

    def get_data(self):
        return {}

    def scan_structure(self):
        path = self.main_schematic_path
        self.tree_subsheets.clear()
        self.lbl_part_count.setText("Total Parts: Calculating...")
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        if not path:
            self.lbl_part_count.setText("Total Parts: No main schematic set.")
            self.progress.setVisible(False)
            self.tree_subsheets.clear() # Clear any old data
            return
            
        if not os.path.exists(path):
            self.lbl_part_count.setText(f"Total Parts: Error - Schematic not found at {self.logic.relativize_path(path)}")
            self.progress.setVisible(False)
            self.tree_subsheets.clear() # Clear any old data
            return
            
            if hasattr(self, 'worker') and self.worker.isRunning():
                self.worker.terminate()
                self.worker.wait()
                
            self.worker = StructureScanWorker(self.logic, path, self)
            self.worker.finished.connect(self.on_scan_finished)
            self.worker.error.connect(lambda e: self.lbl_part_count.setText(f"Error: {e}"))
            self.worker.finished.connect(lambda: self.progress.setVisible(False))
            self.worker.start()

    def on_scan_finished(self, tree_data, total):
        if tree_data:
            self.populate_tree(tree_data, self.tree_subsheets)
            self.tree_subsheets.expandAll()
        self.lbl_part_count.setText(f"Total Parts: {total}")
        
        # Cache the results to the registry
        if self.current_project and "project_registry" in self.logic.settings:
            if self.current_project in self.logic.settings["project_registry"]:
                self.logic.settings["project_registry"][self.current_project]["structure"] = {
                    "tree": tree_data,
                    "part_count": total
                }
                self.logic.save_settings()

    def populate_tree(self, node_data, parent):
        item = QTreeWidgetItem(parent)
        item.setText(0, node_data["name"])
        item.setText(1, str(node_data.get("part_count", 0)))
        item.setData(0, Qt.UserRole, node_data["path"])
        
        for child in node_data.get("children", []):
            self.populate_tree(child, item)

    def open_selected_sheet(self):
        item = self.tree_subsheets.currentItem()
        if not item: return
        path = item.data(0, Qt.UserRole)
        if path and os.path.exists(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)