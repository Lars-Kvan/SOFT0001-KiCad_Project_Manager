import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QHBoxLayout, 
                              QLineEdit, QPushButton, QLabel, QTreeWidget, QTreeWidgetItem, QFileDialog, QProgressBar,
                              QFormLayout, QToolButton)
from PySide6.QtCore import Qt, QUrl, QThread, Signal
from PySide6.QtGui import QDesktopServices, QColor
from ui.widgets.progress_utils import style_progress_bar

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

        summary_gb = QGroupBox("Project Summary")
        summary_layout = QFormLayout(summary_gb)

        self.lbl_meta_status = QLabel("-")
        self.lbl_meta_type = QLabel("-")
        self.lbl_meta_last = QLabel("-")

        loc_row, self.lbl_meta_location, self.btn_open_location = self._make_path_row("Open Folder", self._open_location)
        sch_row, self.lbl_meta_schematic, self.btn_open_schematic = self._make_path_row("Open File", self._open_schematic)
        lay_row, self.lbl_meta_layout, self.btn_open_layout = self._make_path_row("Open File", self._open_layout)

        self.lbl_meta_requirements = QLabel("-")
        self.lbl_meta_subsheets = QLabel("-")
        self.lbl_meta_parts = QLabel("-")
        self.lbl_meta_libs = QLabel("-")
        self.lbl_meta_checklist = QLabel("-")
        self.lbl_meta_kanban = QLabel("-")
        self.lbl_meta_test_plan = QLabel("-")

        summary_layout.addRow("Status:", self.lbl_meta_status)
        summary_layout.addRow("Type:", self.lbl_meta_type)
        summary_layout.addRow("Last Opened:", self.lbl_meta_last)
        summary_layout.addRow("Location:", loc_row)
        summary_layout.addRow("Main Schematic:", sch_row)
        summary_layout.addRow("Layout File:", lay_row)
        summary_layout.addRow("Requirements:", self.lbl_meta_requirements)
        summary_layout.addRow("Sub-sheets:", self.lbl_meta_subsheets)
        summary_layout.addRow("Parts:", self.lbl_meta_parts)
        summary_layout.addRow("Libraries:", self.lbl_meta_libs)
        summary_layout.addRow("Checklist:", self.lbl_meta_checklist)
        summary_layout.addRow("Kanban:", self.lbl_meta_kanban)
        summary_layout.addRow("Test Plan:", self.lbl_meta_test_plan)

        layout.addWidget(summary_gb)
        
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
        theme = self.logic.settings.get("theme", "Light")
        style_progress_bar(self.progress, accent="#F59E0B", theme=theme, min_height=10, max_height=14)
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

        self._update_summary(meta, data)
        
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

    def _make_path_row(self, button_text, handler):
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel("-")
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        btn = QToolButton()
        btn.setText(button_text)
        btn.clicked.connect(handler)
        row_layout.addWidget(label)
        row_layout.addStretch()
        row_layout.addWidget(btn)
        return row, label, btn

    def _status_color(self, status):
        palette = {
            "Pre-Design": "#64748b",
            "Schematic Capture": "#2563EB",
            "PCB Layout": "#7c3aed",
            "Prototyping": "#f97316",
            "Validation": "#0ea5e9",
            "Released": "#22c55e",
            "Abandoned": "#ef4444",
            "Draft": "#64748b",
            "Review": "#2563EB",
            "Approved": "#0ea5e9",
            "Implemented": "#22c55e",
            "Verified": "#14b8a6",
            "Deprecated": "#ef4444",
        }
        return palette.get(status, "#2563EB")

    def _gradient_style(self, accent):
        color = QColor(accent)
        lighter = color.lighter(150).name()
        darker = color.darker(120).name()
        return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {lighter}, stop:1 {darker})"

    def _set_summary_value(self, label, text, accent="#2563EB"):
        label.setText(text or "-")
        label.setToolTip(text)
        gradient = self._gradient_style(accent)
        label.setStyleSheet(
            f"border-radius: 12px; padding: 4px 10px; font-weight: 600; color: #F8FAFC; "
            f"background: {gradient}; border: 1px solid rgba(0, 0, 0, 0.08);"
        )

    def _set_path_label(self, label, button, path):
        text = self.logic.relativize_path(path) if path else "-"
        label.setText(text)
        label.setToolTip(path or "")
        button.setEnabled(bool(path and os.path.exists(path)))

    def _update_summary(self, meta, data):
        status = meta.get("status", "-") or "-"
        ptype = meta.get("type", "-") or "-"
        last = meta.get("last_accessed", "-") or "-"
        location = meta.get("location", "")
        schematic = meta.get("main_schematic", "")
        layout_file = meta.get("layout_file", "")

        self._set_summary_value(self.lbl_meta_status, status, self._status_color(status))
        self._set_summary_value(self.lbl_meta_type, ptype, "#9d8189")
        self._set_summary_value(self.lbl_meta_last, last, "#64748b")
        self._set_path_label(self.lbl_meta_location, self.btn_open_location, location)
        self._set_path_label(self.lbl_meta_schematic, self.btn_open_schematic, schematic)
        self._set_path_label(self.lbl_meta_layout, self.btn_open_layout, layout_file)

        reqs = data.get("requirements", []) or []
        req_total = len(reqs)
        req_verified = len([r for r in reqs if r.get("status") == "Verified"])
        sub_total = sum(len(r.get("sub_requirements", []) or []) for r in reqs)
        sub_verified = sum(
            len([s for s in (r.get("sub_requirements", []) or []) if s.get("status") == "Verified"])
            for r in reqs
        )
        self._set_summary_value(
            self.lbl_meta_requirements,
            f"{req_total} (Verified: {req_verified}, Sub: {sub_total}, Sub Verified: {sub_verified})",
            "#2563EB",
        )

        structure = data.get("structure", {}) or {}
        tree = structure.get("tree")
        sub_count = self._count_tree_nodes(tree) - 1 if tree else 0
        self._set_summary_value(self.lbl_meta_subsheets, str(max(sub_count, 0)) if tree else "-", "#14b8a6")

        part_count = structure.get("part_count")
        self._set_summary_value(self.lbl_meta_parts, str(part_count) if part_count is not None else "-", "#f97316")

        libs = self._count_unique_libs(meta.get("main_schematic", ""))
        self._set_summary_value(self.lbl_meta_libs, str(libs) if libs is not None else "-", "#8b5cf6")

        checklist = data.get("checklist", {}) or {}
        total_rules, verified_rules, na_rules = self._checklist_counts(checklist)
        if total_rules > 0:
            checklist_text = f"{verified_rules}/{total_rules} verified"
            if na_rules:
                checklist_text += f" (N/A {na_rules})"
        else:
            checklist_text = "-"
        self._set_summary_value(self.lbl_meta_checklist, checklist_text, "#facc15")

        kanban = data.get("kanban", {}) or {}
        todo = len(kanban.get("todo", []) or [])
        prog = len(kanban.get("prog", []) or [])
        done = len(kanban.get("done", []) or [])
        self._set_summary_value(self.lbl_meta_kanban, f"To Do {todo} • In Progress {prog} • Done {done}", "#10b981")

        test_plan = data.get("test_plan", {}) or {}
        t_total, t_pass, t_fail, t_na, t_not_run, t_last = self._test_plan_counts(test_plan)
        if t_total:
            tp_text = f"{t_total} total (Pass {t_pass}, Fail {t_fail}, N/A {t_na}, Not Run {t_not_run})"
            if t_last:
                tp_text += f" | Last {t_last}"
        else:
            tp_text = "-"
        self._set_summary_value(self.lbl_meta_test_plan, tp_text, "#f97316")

    def _checklist_counts(self, checklist):
        total = 0
        verified = 0
        na = 0
        for _, rules in checklist.items():
            if isinstance(rules, dict) and "rules" in rules:
                rules = rules.get("rules", [])
            if not isinstance(rules, list):
                continue
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                status = rule.get("status", "No")
                if status == "N/A":
                    na += 1
                    continue
                total += 1
                if status == "Yes":
                    verified += 1
        return total, verified, na

    def _count_tree_nodes(self, node):
        if not node:
            return 0
        count = 1
        for child in node.get("children", []):
            count += self._count_tree_nodes(child)
        return count

    def _count_unique_libs(self, main_schematic):
        if not main_schematic:
            return None
        path = self.logic.resolve_path(main_schematic) if hasattr(self.logic, "resolve_path") else main_schematic
        if not path or not os.path.exists(path):
            return None
        try:
            bom = self.logic.generate_bom(path)
        except Exception:
            return None
        libs = set()
        for item in bom or []:
            lib_id = item.get("lib_id", "")
            if lib_id:
                libs.add(lib_id.split(":")[0])
        return len(libs)

    def _test_plan_counts(self, test_plan):
        cases = test_plan.get("cases", []) if isinstance(test_plan, dict) else []
        total = len(cases)
        passed = failed = na = not_run = 0
        last = ""
        for case in cases:
            status = case.get("status", "Not Run")
            if status == "Pass":
                passed += 1
            elif status == "Fail":
                failed += 1
            elif status == "N/A":
                na += 1
            elif status == "Not Run":
                not_run += 1
            last_run = case.get("last_run", "")
            if last_run and (not last or last_run > last):
                last = last_run
        return total, passed, failed, na, not_run, last

    def _open_location(self):
        self._open_path(self.lbl_meta_location.text(), expect_dir=True)

    def _open_schematic(self):
        self._open_path(self.lbl_meta_schematic.text())

    def _open_layout(self):
        self._open_path(self.lbl_meta_layout.text())

    def _open_path(self, display_path, expect_dir=False):
        if not display_path or display_path == "-":
            return
        resolved = self.logic.resolve_path(display_path)
        if not resolved:
            return
        if expect_dir and not os.path.isdir(resolved):
            return
        if not expect_dir and not os.path.exists(resolved):
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(resolved))

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
