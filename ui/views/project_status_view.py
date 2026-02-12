import os
import pathlib
import subprocess
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QFormLayout, 
                              QLineEdit, QComboBox, QTextEdit, QPushButton, QHBoxLayout, QFileDialog, QLabel,
                              QTextBrowser, QToolButton, QStackedWidget, QCheckBox)
from PySide6.QtCore import Qt, QThread, Signal
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons
from ui._subprocess_utils import hidden_console_kwargs

DEFAULT_PROJECT_STATUSES = [
    "Pre-Design",
    "Schematic Capture",
    "PCB Layout",
    "Prototyping",
    "Validation",
    "Released",
    "Abandoned",
]

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
        self._refresh_status_options()
        
        self.edit_proj_type = QComboBox()
        
        # Location with Browse Button
        loc_widget = QWidget()
        loc_layout = QHBoxLayout(loc_widget); loc_layout.setContentsMargins(0,0,0,0)
        self.edit_file_loc = QLineEdit()
        btn_browse = QPushButton("Browse")
        btn_browse.setIcon(Icons.get_icon(Icons.FOLDER, "#555555"))
        btn_browse.setToolTip("Select project folder")
        btn_browse.clicked.connect(self.browse_loc)
        loc_layout.addWidget(self.edit_file_loc); loc_layout.addWidget(btn_browse)
        self.edit_file_loc.textChanged.connect(self._on_location_changed)
        
        self.edit_git_dir = QLineEdit()
        self.btn_browse_git = QPushButton("Browse")
        self.btn_browse_git.setIcon(Icons.get_icon(Icons.GIT, "#555555"))
        self.btn_browse_git.setToolTip("Select Git repository root")
        self.btn_browse_git.clicked.connect(self.browse_git_dir)
        git_dir_widget = QWidget()
        git_dir_layout = QHBoxLayout(git_dir_widget); git_dir_layout.setContentsMargins(0,0,0,0)
        git_dir_layout.addWidget(self.edit_git_dir); git_dir_layout.addWidget(self.btn_browse_git)
        self.chk_git_same_loc = QCheckBox("Same as folder location")
        self.chk_git_same_loc.setToolTip("Keep the Git directory aligned with the selected project folder")
        self.chk_git_same_loc.stateChanged.connect(self._on_git_same_location_toggled)
        
        self.edit_proj_desc = QTextEdit()
        self.edit_proj_desc.setPlaceholderText("Markdown supported... e.g. **bold**, *italic*, - list")
        self.edit_proj_desc.textChanged.connect(self._update_desc_preview)
        
        # Main Schematic with Browse Button
        sch_widget = QWidget()
        sch_layout = QHBoxLayout(sch_widget); sch_layout.setContentsMargins(0,0,0,0)
        self.edit_main_sch = QLineEdit()
        btn_browse_sch = QPushButton("Browse")
        btn_browse_sch.setIcon(Icons.get_icon(Icons.DOC, "#555555"))
        btn_browse_sch.setToolTip("Select main schematic")
        btn_browse_sch.clicked.connect(self.browse_sch)
        sch_layout.addWidget(self.edit_main_sch); sch_layout.addWidget(btn_browse_sch)

        # Layout File with Browse Button
        layout_widget = QWidget()
        layout_layout = QHBoxLayout(layout_widget); layout_layout.setContentsMargins(0,0,0,0)
        self.edit_layout_file = QLineEdit()
        btn_browse_layout = QPushButton("Browse")
        btn_browse_layout.setIcon(Icons.get_icon(Icons.DOC, "#555555"))
        btn_browse_layout.setToolTip("Select layout file")
        btn_browse_layout.clicked.connect(self.browse_layout)
        layout_layout.addWidget(self.edit_layout_file); layout_layout.addWidget(btn_browse_layout)

        form.addRow("Project Name:", self.edit_proj_name)
        form.addRow("Project Number:", self.edit_proj_num)
        form.addRow("Revision:", self.edit_rev)
        form.addRow("Current Status:", self.combo_proj_status)
        form.addRow("Project Type:", self.edit_proj_type)
        form.addRow("Folder Location:", loc_widget)
        git_row = QWidget()
        git_row_layout = QHBoxLayout(git_row)
        git_row_layout.setContentsMargins(0, 0, 0, 0)
        git_row_layout.setSpacing(8)
        git_row_layout.addWidget(git_dir_widget, 1)
        git_row_layout.addWidget(self.chk_git_same_loc)
        git_row_layout.addStretch()
        form.addRow("Git Directory:", git_row)
        form.addRow("Main Schematic:", sch_widget)
        form.addRow("Layout File:", layout_widget)

        desc_tools = QHBoxLayout()
        btn_bold = QToolButton(); btn_bold.setText("B"); btn_bold.setToolTip("Bold"); btn_bold.clicked.connect(lambda: self._wrap_markdown("**"))
        btn_italic = QToolButton(); btn_italic.setText("I"); btn_italic.setToolTip("Italic"); btn_italic.clicked.connect(lambda: self._wrap_markdown("*"))
        btn_h1 = QToolButton(); btn_h1.setText("H1"); btn_h1.setToolTip("Heading 1"); btn_h1.clicked.connect(lambda: self._prefix_lines("# "))
        btn_h2 = QToolButton(); btn_h2.setText("H2"); btn_h2.setToolTip("Heading 2"); btn_h2.clicked.connect(lambda: self._prefix_lines("## "))
        btn_list = QToolButton(); btn_list.setText("•"); btn_list.setToolTip("Bulleted list"); btn_list.clicked.connect(lambda: self._prefix_lines("- "))
        btn_code = QToolButton(); btn_code.setText("</>"); btn_code.setToolTip("Code block"); btn_code.clicked.connect(self._insert_code_block)
        btn_link = QToolButton(); btn_link.setText("Link"); btn_link.setToolTip("Insert link"); btn_link.clicked.connect(self._insert_link)
        self.btn_preview = QToolButton(); self.btn_preview.setText("Preview"); self.btn_preview.setCheckable(True); self.btn_preview.toggled.connect(self._toggle_desc_preview)
        for b in (btn_bold, btn_italic, btn_h1, btn_h2, btn_list, btn_code, btn_link, self.btn_preview):
            desc_tools.addWidget(b)
        desc_tools.addStretch()

        self.desc_preview = QTextBrowser()
        self.desc_preview.setOpenExternalLinks(True)
        self.desc_stack = QStackedWidget()
        self.desc_stack.addWidget(self.edit_proj_desc)
        self.desc_stack.addWidget(self.desc_preview)

        desc_widget = QWidget()
        desc_layout = QVBoxLayout(desc_widget)
        desc_layout.setContentsMargins(0, 0, 0, 0)
        desc_layout.setSpacing(6)
        desc_layout.addLayout(desc_tools)
        desc_layout.addWidget(self.desc_stack)

        form.addRow("Description:", desc_widget)

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

    def browse_layout(self):
        layout_path = self.logic.resolve_path(self.edit_layout_file.text())
        start_dir = os.path.dirname(layout_path) if layout_path else self.logic.resolve_path(self.edit_file_loc.text())
        f, _ = QFileDialog.getOpenFileName(
            self,
            "Select Layout File",
            start_dir,
            "KiCad PCB (*.kicad_pcb)"
        )
        if f:
            self.edit_layout_file.setText(self.logic.relativize_path(f))

    def browse_git_dir(self):
        start = self.logic.resolve_path(self.edit_git_dir.text()) or self.logic.resolve_path(self.edit_file_loc.text())
        d = QFileDialog.getExistingDirectory(self, "Select Git Directory", start)
        if d:
            self.edit_git_dir.setText(self.logic.relativize_path(d))

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
        self._refresh_status_options(meta.get("status", "Pre-Design"))
        self.edit_proj_type.setCurrentText(meta.get("type", ""))
        self.edit_file_loc.setText(self.logic.relativize_path(meta.get("location", "")))
        self.edit_proj_desc.setPlainText(meta.get("description", ""))
        self._update_desc_preview()
        self.edit_main_sch.setText(self.logic.relativize_path(meta.get("main_schematic", "")))
        self.edit_layout_file.setText(self.logic.relativize_path(meta.get("layout_file", "")))
        self.edit_git_dir.setText(self.logic.relativize_path(meta.get("git_directory", meta.get("location", ""))))
        git_same_pref = meta.get("git_same_as_location")
        if git_same_pref is None:
            git_same_pref = self._paths_equivalent(
                meta.get("git_directory", ""), meta.get("location", "")
            )
        self.chk_git_same_loc.setChecked(bool(git_same_pref))
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
        if self.edit_git_dir.text() or meta.get("location"):
            self.check_git_status()

    def _on_location_changed(self):
        if self.chk_git_same_loc.isChecked():
            self._sync_git_to_location()

    def _on_git_same_location_toggled(self, state):
        checked = state == Qt.Checked
        self.edit_git_dir.setDisabled(checked)
        self.btn_browse_git.setDisabled(checked)
        if checked:
            self._sync_git_to_location()

    def _sync_git_to_location(self):
        loc = self.edit_file_loc.text().strip()
        if not loc:
            self.edit_git_dir.blockSignals(True)
            self.edit_git_dir.clear()
            self.edit_git_dir.blockSignals(False)
            return
        resolved = self.logic.resolve_path(loc)
        if not resolved:
            self.edit_git_dir.blockSignals(True)
            self.edit_git_dir.clear()
            self.edit_git_dir.blockSignals(False)
            return
        rel = self.logic.relativize_path(resolved)
        self.edit_git_dir.blockSignals(True)
        self.edit_git_dir.setText(rel)
        self.edit_git_dir.blockSignals(False)

    def _status_options(self):
        return self.logic.settings.get("project_statuses", DEFAULT_PROJECT_STATUSES)

    def _refresh_status_options(self, selection=None):
        current = selection or self.combo_proj_status.currentText()
        self.combo_proj_status.blockSignals(True)
        self.combo_proj_status.clear()
        for status in self._status_options():
            self.combo_proj_status.addItem(status)
        if current:
            idx = self.combo_proj_status.findText(current)
            if idx >= 0:
                self.combo_proj_status.setCurrentIndex(idx)
        self.combo_proj_status.blockSignals(False)

    def refresh_status_options(self):
        self._refresh_status_options()

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
            "main_schematic": self.logic.resolve_path(self.edit_main_sch.text()),
            "layout_file": self.logic.resolve_path(self.edit_layout_file.text()),
            "git_directory": self.logic.resolve_path(self.edit_git_dir.text()),
            "git_same_as_location": self.chk_git_same_loc.isChecked(),
        }

    def _toggle_desc_preview(self, checked):
        if checked:
            self._update_desc_preview()
            self.desc_stack.setCurrentWidget(self.desc_preview)
        else:
            self.desc_stack.setCurrentWidget(self.edit_proj_desc)

    def _update_desc_preview(self):
        if hasattr(self, "desc_preview"):
            self.desc_preview.setMarkdown(self.edit_proj_desc.toPlainText())

    def _wrap_markdown(self, wrapper):
        cursor = self.edit_proj_desc.textCursor()
        selected = cursor.selectedText()
        if not selected:
            cursor.insertText(wrapper + wrapper)
            cursor.movePosition(cursor.Left, cursor.MoveAnchor, len(wrapper))
            self.edit_proj_desc.setTextCursor(cursor)
            return
        cursor.insertText(f"{wrapper}{selected}{wrapper}")

    def _prefix_lines(self, prefix):
        cursor = self.edit_proj_desc.textCursor()
        if not cursor.hasSelection():
            cursor.select(cursor.LineUnderCursor)
        text = cursor.selectedText().replace("\u2029", "\n")
        lines = text.split("\n")
        lines = [prefix + line if line.strip() else line for line in lines]
        cursor.insertText("\n".join(lines))

    def _insert_code_block(self):
        cursor = self.edit_proj_desc.textCursor()
        selected = cursor.selectedText()
        if selected:
            text = selected.replace("\u2029", "\n")
            cursor.insertText(f"```\n{text}\n```")
        else:
            cursor.insertText("```\n\n```")
            cursor.movePosition(cursor.Up)
        self.edit_proj_desc.setTextCursor(cursor)

    def _insert_link(self):
        cursor = self.edit_proj_desc.textCursor()
        selected = cursor.selectedText() or "link text"
        cursor.insertText(f"[{selected}](https://)")

    def _paths_equivalent(self, first, second):
        if not first or not second:
            return False
        resolved_first = self.logic.resolve_path(first)
        resolved_second = self.logic.resolve_path(second)
        if not resolved_first or not resolved_second:
            return False
        norm = lambda p: os.path.normcase(os.path.normpath(p))
        return norm(resolved_first) == norm(resolved_second)

    def save_metadata(self):
        """Default save handler (saves to global settings). 
        The parent UI usually overrides this to save to the Project Registry."""
        meta = self.get_data()
        self.logic.settings["project_metadata"] = meta
        self.logic.save_settings()

    def check_git_status(self):
        git_dir = self.edit_git_dir.text().strip()
        location = self.edit_file_loc.text().strip()
        start_path = git_dir or location
        path = self.logic.resolve_path(start_path)
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
