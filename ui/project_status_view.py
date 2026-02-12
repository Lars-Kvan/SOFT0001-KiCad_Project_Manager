import os
import pathlib
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                             QLineEdit, QComboBox, QTextEdit, QPushButton, QMessageBox, QHBoxLayout, QFileDialog, QLabel)
from PySide6.QtCore import Qt, QThread, Signal
from ._subprocess_utils import hidden_console_kwargs

class GitStatusWorker(QThread):
    finished = Signal(str, str, str) # branch, status_text, color_style

    def __init__(self, path, parent=None):
        super().__init__(parent)
        self.path = path

    def run(self):
        if not self.path or not os.path.exists(self.path):
            self.finished.emit("-", "Invalid Path", "color: gray;")
            return

        try:
            # Check if it's a git repo
            kwargs = hidden_console_kwargs()
            subprocess.check_call(
                ['git', 'rev-parse', '--is-inside-work-tree'],
                cwd=self.path,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                **kwargs,
            )

            branch = subprocess.check_output(
                ['git', 'branch', '--show-current'],
                cwd=self.path,
                **kwargs,
            ).decode().strip()
            status = subprocess.check_output(
                ['git', 'status', '--porcelain'],
                cwd=self.path,
                **kwargs,
            ).decode().strip()
            
            if status:
                self.finished.emit(branch, "Uncommitted Changes", "color: #e74c3c;") # Red
            else:
                self.finished.emit(branch, "Clean", "color: #27ae60;") # Green
                
        except (subprocess.CalledProcessError, FileNotFoundError):
            self.finished.emit("-", "Not a Git Repo", "color: gray;")

class ProjectStatusView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        form_gb = QGroupBox("Engineering Project Metadata")
        form = QFormLayout(form_gb)

        self.edit_proj_name = QLineEdit()
        self.edit_proj_num = QLineEdit()
        self.edit_rev = QLineEdit()
        self.edit_rev.setPlaceholderText("e.g., A.1 or 01")
        
        self.combo_proj_status = QComboBox()
        self.combo_proj_status.addItems([
            "Pre-Design", "Schematic Capture", "PCB Layout", 
            "Prototyping", "Validation", "Released", "Abandoned"
        ])
        
        self.edit_proj_type = QComboBox()
        
        # Location with Browse Button
        loc_widget = QWidget()
        loc_layout = QHBoxLayout(loc_widget); loc_layout.setContentsMargins(0,0,0,0)
        self.edit_file_loc = QLineEdit()
        btn_browse = QPushButton("Browse")
        btn_browse.setToolTip("Select project folder")
        btn_browse.clicked.connect(self.browse_loc)
        loc_layout.addWidget(self.edit_file_loc); loc_layout.addWidget(btn_browse)
        
        self.edit_proj_desc = QTextEdit()
        
        # Main Schematic with Browse Button
        sch_widget = QWidget()
        sch_layout = QHBoxLayout(sch_widget); sch_layout.setContentsMargins(0,0,0,0)
        self.edit_main_sch = QLineEdit()
        btn_browse_sch = QPushButton("Browse")
        btn_browse_sch.setToolTip("Select main schematic")
        btn_browse_sch.clicked.connect(self.browse_sch)
        sch_layout.addWidget(self.edit_main_sch); sch_layout.addWidget(btn_browse_sch)

        form.addRow("Project Name:", self.edit_proj_name)
        form.addRow("Project Number:", self.edit_proj_num)
        form.addRow("Revision:", self.edit_rev)
        form.addRow("Current Status:", self.combo_proj_status)
        form.addRow("Project Type:", self.edit_proj_type)
        form.addRow("File Location:", loc_widget)
        form.addRow("Main Schematic:", sch_widget)
        form.addRow("Description:", self.edit_proj_desc)

        layout.addWidget(form_gb)

        # Git Status Group
        git_gb = QGroupBox("Version Control (Git)")
        git_layout = QHBoxLayout(git_gb)
        
        self.lbl_git_branch = QLabel("Branch: -")
        self.lbl_git_status = QLabel("Status: -")
        self.lbl_git_status.setStyleSheet("font-weight: bold;")
        
        btn_git_refresh = QPushButton("Refresh Status")
        btn_git_refresh.clicked.connect(self.check_git_status)
        
        git_layout.addWidget(self.lbl_git_branch)
        git_layout.addWidget(self.lbl_git_status)
        git_layout.addStretch()
        git_layout.addWidget(btn_git_refresh)
        layout.addWidget(git_gb)
        
        # We assign this to self.btn_save so the parent can disconnect/connect signals if needed
        self.btn_save = QPushButton("Save Project Metadata")
        self.btn_save.setStyleSheet("font-weight: bold; height: 30px; background-color: #2ecc71; color: white;")
        # Default behavior (can be overridden by parent)
        self.btn_save.clicked.connect(self.save_metadata)
        layout.addWidget(self.btn_save)
        layout.addStretch()

    def browse_loc(self):
        start = self.logic.resolve_path(self.edit_file_loc.text())
        d = QFileDialog.getExistingDirectory(self, "Select Project Folder", start)
        if d:
            self.edit_file_loc.setText(self.logic.relativize_path(d))

    def browse_sch(self):
        sch_path = self.logic.resolve_path(self.edit_main_sch.text())
        start_dir = os.path.dirname(sch_path) if sch_path else self.logic.resolve_path(self.edit_file_loc.text())
        f, _ = QFileDialog.getOpenFileName(self, "Select Main Schematic", start_dir, "KiCad Schematic (*.kicad_sch)")
        if f:
            self.edit_main_sch.setText(self.logic.relativize_path(f))

    def load_data(self, meta):
        """Standardized receiver for project-specific metadata."""
        if not meta: return
        
        # Block signals to prevent side effects during programatic update
        self.edit_proj_type.blockSignals(True)
        self.edit_proj_type.clear()
        self.edit_proj_type.addItems(self.logic.settings.get("project_types", ["PCB"]))
        self.edit_proj_type.blockSignals(False)

        self.edit_proj_name.blockSignals(True)
        
        self.edit_proj_name.setText(meta.get("name", ""))
        self.edit_proj_num.setText(meta.get("number", ""))
        self.edit_rev.setText(meta.get("revision", "A"))
        self.combo_proj_status.setCurrentText(meta.get("status", "Pre-Design"))
        self.edit_proj_type.setCurrentText(meta.get("type", ""))
        self.edit_file_loc.setText(self.logic.relativize_path(meta.get("location", "")))
        self.edit_proj_desc.setPlainText(meta.get("description", ""))
        self.edit_main_sch.setText(self.logic.relativize_path(meta.get("main_schematic", "")))
        
        # Auto-detect main schematic if missing
        if not self.edit_main_sch.text() and meta.get("location"):
            root = meta.get("location")
            name = meta.get("name", "")
            if os.path.exists(root):
                # Recursive search for Name.kicad_sch
                candidates = list(pathlib.Path(root).rglob(f"{name}.kicad_sch"))
                if candidates:
                    self.edit_main_sch.setText(self.logic.relativize_path(str(candidates[0])))
                    # Auto-save this discovery to prevent re-scanning later
                    # We don't call save_metadata() here to avoid popup spam, 
                    # but we update the in-memory registry via logic if needed, 
                    # or just let the user click save.
                    pass
        
        self.edit_proj_name.blockSignals(False)
        
        # Auto-check git if location exists
        if meta.get("location"):
            self.check_git_status()

    def get_data(self):
        """Standardized getter to package UI state for the registry saver."""
        return {
            "name": self.edit_proj_name.text(),
            "number": self.edit_proj_num.text(),
            "revision": self.edit_rev.text(),
            "status": self.combo_proj_status.currentText(),
            "type": self.edit_proj_type.currentText(),
            "location": self.logic.resolve_path(self.edit_file_loc.text()),
            "description": self.edit_proj_desc.toPlainText(),
            "main_schematic": self.logic.resolve_path(self.edit_main_sch.text())
        }

    def save_metadata(self):
        """Default save handler (saves to global settings). 
        The parent UI usually overrides this to save to the Project Registry."""
        meta = self.get_data()
        self.logic.settings["project_metadata"] = meta
        self.logic.save_settings()
        QMessageBox.information(self, "Success", "Project metadata saved.")

    def check_git_status(self):
        path = self.logic.resolve_path(self.edit_file_loc.text())
        self.lbl_git_status.setText("Status: Checking...")
        self.lbl_git_status.setStyleSheet("color: orange;")
        
        # Manage active workers to prevent "QThread Destroyed" error on rapid switching
        if not hasattr(self, '_active_git_workers'):
            self._active_git_workers = []
        
        # Cleanup dead workers reference
        self._active_git_workers = [w for w in self._active_git_workers if w.isRunning()]

        worker = GitStatusWorker(path, self)
        worker.finished.connect(lambda b, s, c: self.update_git_ui(b, s, c))
        # Remove from list and delete when done
        worker.finished.connect(lambda: self._active_git_workers.remove(worker) if worker in self._active_git_workers else None)
        worker.finished.connect(worker.deleteLater)
        
        self._active_git_workers.append(worker)
        worker.start()

    def closeEvent(self, event):
        if hasattr(self, '_active_git_workers'):
            for w in self._active_git_workers:
                if w.isRunning():
                    w.wait()
        super().closeEvent(event)

    def update_git_ui(self, branch, status, color):
        self.lbl_git_branch.setText(f"Branch: {branch}")
        self.lbl_git_status.setText(f"Status: {status}")
        self.lbl_git_status.setStyleSheet(color)
