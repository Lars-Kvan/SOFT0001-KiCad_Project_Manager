import os
import shutil
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QLabel,
    QLineEdit,
    QComboBox,
    QPlainTextEdit,
    QFormLayout,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QMessageBox,
    QFileDialog,
    QGroupBox,
    QFrame,
)
from PySide6.QtCore import Qt
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons

_DARK_THEMES = {"Dark", "Teal Sand Dark"}


class ProjectTestPlanView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.current_project = ""
        self.project_path = ""
        self.test_plan_dir = ""
        self.test_plan = {"cases": [], "config": self._default_config()}
        self._loading = False
        self._dirty = False
        self._current_case_id = None
        theme = self.logic.settings.get("theme", "Light")
        panel_theme = "Dark" if theme in _DARK_THEMES else "Light"
        self.setObjectName("projectPanel")
        self.setProperty("projectTheme", panel_theme)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        header = QHBoxLayout()
        self.lbl_summary = QLabel("No project selected")
        header.addWidget(self.lbl_summary)
        header.addStretch()

        self.filter_status = QComboBox()
        self.filter_status.addItems(["All Statuses", "Not Run", "Pass", "Fail", "Blocked", "N/A", "In Progress"])
        self.filter_status.currentTextChanged.connect(self._rebuild_case_list)
        header.addWidget(self.filter_status)

        self.filter_category = QComboBox()
        self.filter_category.addItems(["All Categories"])
        self.filter_category.currentTextChanged.connect(self._rebuild_case_list)
        header.addWidget(self.filter_category)

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search cases...")
        self.search_edit.textChanged.connect(self._rebuild_case_list)
        header.addWidget(self.search_edit)

        self.btn_new = QPushButton("New Case")
        self.btn_new.clicked.connect(self.add_case)
        header.addWidget(self.btn_new)

        self.btn_duplicate = QPushButton("Duplicate")
        self.btn_duplicate.clicked.connect(self.duplicate_case)
        header.addWidget(self.btn_duplicate)

        self.btn_remove = QPushButton("Remove")
        self.btn_remove.clicked.connect(self.remove_case)
        header.addWidget(self.btn_remove)

        self.btn_export = QPushButton("Export Plan")
        self.btn_export.clicked.connect(self.export_plan)
        header.addWidget(self.btn_export)

        self.btn_open_folder = QPushButton("Open Test Plan Folder")
        self.btn_open_folder.clicked.connect(self.open_test_plan_folder)
        header.addWidget(self.btn_open_folder)

        layout.addLayout(header)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        # Left: cases list
        left = QGroupBox("Test Cases")
        left.setObjectName("projectPanelSection")
        left_layout = QVBoxLayout(left)
        self.list_cases = QListWidget()
        self.list_cases.itemSelectionChanged.connect(self._on_case_selected)
        left_layout.addWidget(self.list_cases, 1)
        splitter.addWidget(left)

        # Right: details
        right = QFrame()
        right.setObjectName("projectPanelSection")
        right_layout = QVBoxLayout(right)

        self.lbl_case_header = QLabel("Case: -")
        right_layout.addWidget(self.lbl_case_header)

        tabs = QTabWidget()
        tabs.setProperty("stretchTabs", True)
        tabs.tabBar().setExpanding(True)
        right_layout.addWidget(tabs, 1)

        # Details tab
        details_tab = QWidget()
        details_layout = QVBoxLayout(details_tab)

        form = QFormLayout()
        self.edit_id = QLineEdit()
        self.edit_id.setReadOnly(True)
        self.edit_title = QLineEdit()
        self.combo_category = QComboBox()
        self.combo_category.setEditable(True)
        self.combo_priority = QComboBox()
        self.combo_priority.addItems(self.test_plan["config"]["priorities"])
        self.combo_type = QComboBox()
        self.combo_type.addItems(self.test_plan["config"]["types"])
        self.combo_status = QComboBox()
        self.combo_status.addItems(["Not Run", "In Progress", "Pass", "Fail", "Blocked", "N/A"])
        self.edit_owner = QLineEdit()
        self.edit_requirement = QLineEdit()
        self.edit_pre = QPlainTextEdit()
        self.edit_post = QPlainTextEdit()
        self.edit_notes = QPlainTextEdit()
        self.lbl_last_run = QLabel("-")

        form.addRow("ID:", self.edit_id)
        form.addRow("Title:", self.edit_title)
        form.addRow("Category:", self.combo_category)
        form.addRow("Priority:", self.combo_priority)
        form.addRow("Type:", self.combo_type)
        form.addRow("Status:", self.combo_status)
        form.addRow("Owner:", self.edit_owner)
        form.addRow("Requirement Link:", self.edit_requirement)
        form.addRow("Preconditions:", self.edit_pre)
        form.addRow("Postconditions:", self.edit_post)
        form.addRow("Notes:", self.edit_notes)
        form.addRow("Last Run:", self.lbl_last_run)

        details_layout.addLayout(form)

        btn_row = QHBoxLayout()
        self.btn_save_case = QPushButton("Save Case")
        self.btn_save_case.clicked.connect(self._save_current_case)
        btn_row.addWidget(self.btn_save_case)
        self.btn_log_run = QPushButton("Log Run")
        self.btn_log_run.clicked.connect(self.add_run_entry)
        btn_row.addWidget(self.btn_log_run)
        btn_row.addStretch()
        details_layout.addLayout(btn_row)

        tabs.addTab(details_tab, "Details")

        # Steps tab
        steps_tab = QWidget()
        steps_layout = QVBoxLayout(steps_tab)
        self.tbl_steps = QTableWidget(0, 2)
        self.tbl_steps.setHorizontalHeaderLabels(["Action", "Expected Result"])
        self.tbl_steps.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_steps.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tbl_steps.verticalHeader().setVisible(False)
        self.tbl_steps.setAlternatingRowColors(True)
        steps_layout.addWidget(self.tbl_steps, 1)

        steps_btns = QHBoxLayout()
        self.btn_add_step = QPushButton("Add Step")
        self.btn_add_step.clicked.connect(self.add_step)
        self.btn_remove_step = QPushButton("Remove Step")
        self.btn_remove_step.clicked.connect(self.remove_step)
        self.btn_step_up = QPushButton("Move Up")
        self.btn_step_up.clicked.connect(lambda: self.move_step(-1))
        self.btn_step_down = QPushButton("Move Down")
        self.btn_step_down.clicked.connect(lambda: self.move_step(1))
        steps_btns.addWidget(self.btn_add_step)
        steps_btns.addWidget(self.btn_remove_step)
        steps_btns.addWidget(self.btn_step_up)
        steps_btns.addWidget(self.btn_step_down)
        steps_btns.addStretch()
        steps_layout.addLayout(steps_btns)
        tabs.addTab(steps_tab, "Steps")

        # Runs tab
        runs_tab = QWidget()
        runs_layout = QVBoxLayout(runs_tab)
        self.tbl_runs = QTableWidget(0, 4)
        self.tbl_runs.setHorizontalHeaderLabels(["Date", "Result", "Tester", "Notes"])
        self.tbl_runs.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tbl_runs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_runs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_runs.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tbl_runs.verticalHeader().setVisible(False)
        self.tbl_runs.setAlternatingRowColors(True)
        runs_layout.addWidget(self.tbl_runs, 1)

        runs_btns = QHBoxLayout()
        self.btn_add_run = QPushButton("Add Run")
        self.btn_add_run.clicked.connect(self.add_run_entry)
        self.btn_remove_run = QPushButton("Remove Run")
        self.btn_remove_run.clicked.connect(self.remove_run_entry)
        runs_btns.addWidget(self.btn_add_run)
        runs_btns.addWidget(self.btn_remove_run)
        runs_btns.addStretch()
        runs_layout.addLayout(runs_btns)
        tabs.addTab(runs_tab, "Runs")

        # Attachments tab
        att_tab = QWidget()
        att_layout = QVBoxLayout(att_tab)
        self.list_attachments = QListWidget()
        att_layout.addWidget(self.list_attachments, 1)
        att_btns = QHBoxLayout()
        self.btn_add_attach = QPushButton("Add Attachment")
        self.btn_add_attach.clicked.connect(self.add_attachment)
        self.btn_remove_attach = QPushButton("Remove Attachment")
        self.btn_remove_attach.clicked.connect(self.remove_attachment)
        self.btn_open_attach = QPushButton("Open Attachment")
        self.btn_open_attach.clicked.connect(self.open_attachment)
        att_btns.addWidget(self.btn_add_attach)
        att_btns.addWidget(self.btn_remove_attach)
        att_btns.addWidget(self.btn_open_attach)
        att_btns.addStretch()
        att_layout.addLayout(att_btns)
        tabs.addTab(att_tab, "Attachments")

        splitter.addWidget(right)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        self._wire_dirty_signals()

    def _wire_dirty_signals(self):
        for w in (
            self.edit_title,
            self.edit_owner,
            self.edit_requirement,
        ):
            w.textEdited.connect(self._mark_dirty)
        for w in (self.combo_category, self.combo_priority, self.combo_type, self.combo_status):
            w.currentTextChanged.connect(self._mark_dirty)
        for w in (self.edit_pre, self.edit_post, self.edit_notes):
            w.textChanged.connect(self._mark_dirty)
        self.tbl_steps.itemChanged.connect(self._mark_dirty)
        self.tbl_runs.itemChanged.connect(self._mark_dirty)

    def load_data(self, project_name, data):
        self._save_current_case()
        self.current_project = project_name or ""
        meta = (data or {}).get("metadata", {})
        self.project_path = self.logic.resolve_path(meta.get("location", "")) if hasattr(self.logic, "resolve_path") else meta.get("location", "")
        self.test_plan = (data or {}).get("test_plan", {}) or {}
        self._ensure_test_plan_defaults()
        self._ensure_test_plan_dirs()
        self._refresh_filters()
        self._rebuild_case_list()
        self._clear_case_editor()
        self._update_summary()

    def _default_config(self):
        return {
            "categories": [
                "Functional",
                "Electrical",
                "Firmware",
                "Mechanical",
                "Safety",
                "Manufacturing",
                "Regression",
            ],
            "priorities": ["Critical", "High", "Normal", "Low"],
            "types": ["Unit", "Subsystem", "System", "Integration", "Regression", "Validation"],
        }

    def _ensure_test_plan_defaults(self):
        if "cases" not in self.test_plan or not isinstance(self.test_plan.get("cases"), list):
            self.test_plan["cases"] = []
        if "config" not in self.test_plan or not isinstance(self.test_plan.get("config"), dict):
            self.test_plan["config"] = self._default_config()
        else:
            cfg = self.test_plan["config"]
            defaults = self._default_config()
            for k, v in defaults.items():
                if k not in cfg:
                    cfg[k] = v
        if "priorities" not in self.test_plan["config"]:
            self.test_plan["config"]["priorities"] = self._default_config()["priorities"]
        if "types" not in self.test_plan["config"]:
            self.test_plan["config"]["types"] = self._default_config()["types"]

    def _ensure_test_plan_dirs(self):
        self.test_plan_dir = ""
        if not self.project_path or not os.path.isdir(self.project_path):
            return
        base = os.path.join(self.project_path, "Test_Plan")
        attachments = os.path.join(base, "attachments")
        reports = os.path.join(base, "reports")
        procedures = os.path.join(base, "procedures")
        try:
            os.makedirs(attachments, exist_ok=True)
            os.makedirs(reports, exist_ok=True)
            os.makedirs(procedures, exist_ok=True)
            self.test_plan_dir = base
        except Exception:
            self.test_plan_dir = ""

    def _refresh_filters(self):
        self.combo_category.blockSignals(True)
        self.combo_category.clear()
        self.combo_category.addItems(self.test_plan["config"].get("categories", []))
        self.combo_category.blockSignals(False)

        self.filter_category.blockSignals(True)
        self.filter_category.clear()
        self.filter_category.addItem("All Categories")
        self.filter_category.addItems(self.test_plan["config"].get("categories", []))
        self.filter_category.blockSignals(False)

    def _update_summary(self):
        total, passed, failed, blocked, na, not_run, last = self._summary_counts()
        parts = [
            f"Total: {total}",
            f"Pass: {passed}",
            f"Fail: {failed}",
            f"Blocked: {blocked}",
            f"N/A: {na}",
            f"Not Run: {not_run}",
        ]
        if last:
            parts.append(f"Last Run: {last}")
        self.lbl_summary.setText(" | ".join(parts))

    def _summary_counts(self):
        total = len(self.test_plan.get("cases", []))
        passed = failed = blocked = na = not_run = 0
        last_run = ""
        for case in self.test_plan.get("cases", []):
            status = case.get("status", "Not Run")
            if status == "Pass":
                passed += 1
            elif status == "Fail":
                failed += 1
            elif status == "Blocked":
                blocked += 1
            elif status == "N/A":
                na += 1
            elif status == "Not Run":
                not_run += 1
            last = case.get("last_run", "")
            if last and (not last_run or last > last_run):
                last_run = last
        return total, passed, failed, blocked, na, not_run, last_run

    def _rebuild_case_list(self):
        self.list_cases.clear()
        cases = self.test_plan.get("cases", [])
        query = self.search_edit.text().strip().lower()
        status_filter = self.filter_status.currentText()
        cat_filter = self.filter_category.currentText()

        for case in cases:
            if query:
                text = f"{case.get('id','')} {case.get('title','')}".lower()
                if query not in text:
                    continue
            if status_filter != "All Statuses" and case.get("status", "Not Run") != status_filter:
                continue
            if cat_filter != "All Categories" and case.get("category", "") != cat_filter:
                continue
            label = f"[{case.get('status','Not Run')}] {case.get('id','')} - {case.get('title','')}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, case.get("id"))
            self.list_cases.addItem(item)

    def _on_case_selected(self):
        if self._loading:
            return
        self._save_current_case()
        item = self.list_cases.currentItem()
        if not item:
            self._clear_case_editor()
            return
        case_id = item.data(Qt.UserRole)
        self._load_case(case_id)

    def _load_case(self, case_id):
        case = self._get_case(case_id)
        if not case:
            self._clear_case_editor()
            return
        self._loading = True
        self._current_case_id = case_id
        self.lbl_case_header.setText(f"Case: {case.get('id', '-')}")
        self.edit_id.setText(case.get("id", ""))
        self.edit_title.setText(case.get("title", ""))
        self.combo_category.setCurrentText(case.get("category", ""))
        self.combo_priority.setCurrentText(case.get("priority", "Normal"))
        self.combo_type.setCurrentText(case.get("type", "System"))
        self.combo_status.setCurrentText(case.get("status", "Not Run"))
        self.edit_owner.setText(case.get("owner", ""))
        self.edit_requirement.setText(case.get("requirement", ""))
        self.edit_pre.setPlainText(case.get("preconditions", ""))
        self.edit_post.setPlainText(case.get("postconditions", ""))
        self.edit_notes.setPlainText(case.get("notes", ""))
        self.lbl_last_run.setText(case.get("last_run", "-") or "-")
        self._load_steps(case.get("steps", []))
        self._load_runs(case.get("runs", []))
        self._load_attachments(case.get("attachments", []))
        self._dirty = False
        self._loading = False

    def _clear_case_editor(self):
        self._loading = True
        self._current_case_id = None
        self.lbl_case_header.setText("Case: -")
        self.edit_id.clear()
        self.edit_title.clear()
        self.combo_category.setCurrentIndex(-1)
        self.combo_priority.setCurrentIndex(0)
        self.combo_type.setCurrentIndex(0)
        self.combo_status.setCurrentIndex(0)
        self.edit_owner.clear()
        self.edit_requirement.clear()
        self.edit_pre.clear()
        self.edit_post.clear()
        self.edit_notes.clear()
        self.lbl_last_run.setText("-")
        self.tbl_steps.setRowCount(0)
        self.tbl_runs.setRowCount(0)
        self.list_attachments.clear()
        self._dirty = False
        self._loading = False

    def _mark_dirty(self):
        if self._loading:
            return
        self._dirty = True

    def _get_case(self, case_id):
        for case in self.test_plan.get("cases", []):
            if case.get("id") == case_id:
                return case
        return None

    def _save_current_case(self):
        if self._loading or not self._current_case_id:
            return
        if not self._dirty:
            return
        case = self._get_case(self._current_case_id)
        if not case:
            return
        case.update(self._collect_case_data())
        self._dirty = False
        self._persist()
        self._rebuild_case_list()
        self._update_summary()

    def _collect_case_data(self):
        return {
            "id": self.edit_id.text().strip(),
            "title": self.edit_title.text().strip(),
            "category": self.combo_category.currentText().strip(),
            "priority": self.combo_priority.currentText().strip(),
            "type": self.combo_type.currentText().strip(),
            "status": self.combo_status.currentText().strip(),
            "owner": self.edit_owner.text().strip(),
            "requirement": self.edit_requirement.text().strip(),
            "preconditions": self.edit_pre.toPlainText().strip(),
            "postconditions": self.edit_post.toPlainText().strip(),
            "notes": self.edit_notes.toPlainText().strip(),
            "steps": self._collect_steps(),
            "runs": self._collect_runs(),
            "attachments": self._collect_attachments(),
            "last_run": self.lbl_last_run.text().strip() if self.lbl_last_run.text() != "-" else "",
        }

    def _collect_steps(self):
        steps = []
        for r in range(self.tbl_steps.rowCount()):
            action_item = self.tbl_steps.item(r, 0)
            expected_item = self.tbl_steps.item(r, 1)
            steps.append({
                "action": action_item.text() if action_item else "",
                "expected": expected_item.text() if expected_item else "",
            })
        return steps

    def _collect_runs(self):
        runs = []
        for r in range(self.tbl_runs.rowCount()):
            date_item = self.tbl_runs.item(r, 0)
            result_item = self.tbl_runs.item(r, 1)
            tester_item = self.tbl_runs.item(r, 2)
            notes_item = self.tbl_runs.item(r, 3)
            runs.append({
                "date": date_item.text() if date_item else "",
                "result": result_item.text() if result_item else "",
                "tester": tester_item.text() if tester_item else "",
                "notes": notes_item.text() if notes_item else "",
            })
        return runs

    def _collect_attachments(self):
        files = []
        for i in range(self.list_attachments.count()):
            item = self.list_attachments.item(i)
            if item:
                files.append(item.data(Qt.UserRole))
        return files

    def add_case(self):
        if not self.current_project:
            return
        case_id = self._next_case_id()
        new_case = {
            "id": case_id,
            "title": "New Test Case",
            "category": self.test_plan["config"]["categories"][0] if self.test_plan["config"]["categories"] else "General",
            "priority": "Normal",
            "type": "System",
            "status": "Not Run",
            "owner": "",
            "requirement": "",
            "preconditions": "",
            "postconditions": "",
            "notes": "",
            "steps": [],
            "runs": [],
            "attachments": [],
            "last_run": "",
        }
        self.test_plan["cases"].append(new_case)
        self._persist()
        self._rebuild_case_list()
        self._select_case(case_id)

    def duplicate_case(self):
        item = self.list_cases.currentItem()
        if not item:
            return
        case_id = item.data(Qt.UserRole)
        case = self._get_case(case_id)
        if not case:
            return
        new_case = dict(case)
        new_case["id"] = self._next_case_id()
        new_case["title"] = f"{case.get('title', 'Test Case')} (Copy)"
        self.test_plan["cases"].append(new_case)
        self._persist()
        self._rebuild_case_list()
        self._select_case(new_case["id"])

    def remove_case(self):
        item = self.list_cases.currentItem()
        if not item:
            return
        case_id = item.data(Qt.UserRole)
        case = self._get_case(case_id)
        if not case:
            return
        if QMessageBox.question(self, "Remove Case", f"Remove '{case.get('title','')}'?", QMessageBox.Yes | QMessageBox.No) != QMessageBox.Yes:
            return
        self.test_plan["cases"] = [c for c in self.test_plan["cases"] if c.get("id") != case_id]
        self._persist()
        self._rebuild_case_list()
        self._clear_case_editor()
        self._update_summary()

    def _select_case(self, case_id):
        for i in range(self.list_cases.count()):
            item = self.list_cases.item(i)
            if item and item.data(Qt.UserRole) == case_id:
                self.list_cases.setCurrentItem(item)
                return

    def add_step(self):
        row = self.tbl_steps.rowCount()
        self.tbl_steps.insertRow(row)
        self.tbl_steps.setItem(row, 0, QTableWidgetItem(""))
        self.tbl_steps.setItem(row, 1, QTableWidgetItem(""))
        self._mark_dirty()

    def remove_step(self):
        row = self.tbl_steps.currentRow()
        if row < 0:
            return
        self.tbl_steps.removeRow(row)
        self._mark_dirty()

    def move_step(self, direction):
        row = self.tbl_steps.currentRow()
        if row < 0:
            return
        target = row + direction
        if target < 0 or target >= self.tbl_steps.rowCount():
            return
        for col in range(self.tbl_steps.columnCount()):
            src = self.tbl_steps.takeItem(row, col)
            dst = self.tbl_steps.takeItem(target, col)
            self.tbl_steps.setItem(row, col, dst)
            self.tbl_steps.setItem(target, col, src)
        self.tbl_steps.setCurrentCell(target, 0)
        self._mark_dirty()

    def _load_steps(self, steps):
        self.tbl_steps.setRowCount(0)
        for step in steps:
            row = self.tbl_steps.rowCount()
            self.tbl_steps.insertRow(row)
            self.tbl_steps.setItem(row, 0, QTableWidgetItem(step.get("action", "")))
            self.tbl_steps.setItem(row, 1, QTableWidgetItem(step.get("expected", "")))

    def add_run_entry(self):
        if not self._current_case_id:
            return
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        result = self.combo_status.currentText() or "Not Run"
        row = self.tbl_runs.rowCount()
        self.tbl_runs.insertRow(row)
        self.tbl_runs.setItem(row, 0, QTableWidgetItem(now))
        self.tbl_runs.setItem(row, 1, QTableWidgetItem(result))
        self.tbl_runs.setItem(row, 2, QTableWidgetItem(""))
        self.tbl_runs.setItem(row, 3, QTableWidgetItem(""))
        self.lbl_last_run.setText(now)
        self._mark_dirty()
        self._save_current_case()

    def remove_run_entry(self):
        row = self.tbl_runs.currentRow()
        if row < 0:
            return
        self.tbl_runs.removeRow(row)
        self._mark_dirty()

    def _load_runs(self, runs):
        self.tbl_runs.setRowCount(0)
        for entry in runs:
            row = self.tbl_runs.rowCount()
            self.tbl_runs.insertRow(row)
            self.tbl_runs.setItem(row, 0, QTableWidgetItem(entry.get("date", "")))
            self.tbl_runs.setItem(row, 1, QTableWidgetItem(entry.get("result", "")))
            self.tbl_runs.setItem(row, 2, QTableWidgetItem(entry.get("tester", "")))
            self.tbl_runs.setItem(row, 3, QTableWidgetItem(entry.get("notes", "")))

    def add_attachment(self):
        if not self.test_plan_dir:
            QMessageBox.information(self, "Attachments", "Project location not set or test plan folder unavailable.")
            return
        files, _ = QFileDialog.getOpenFileNames(self, "Select Attachments")
        if not files:
            return
        dest_dir = os.path.join(self.test_plan_dir, "attachments")
        os.makedirs(dest_dir, exist_ok=True)
        for f in files:
            try:
                name = os.path.basename(f)
                dest = os.path.join(dest_dir, name)
                shutil.copy2(f, dest)
                rel = os.path.relpath(dest, self.project_path) if self.project_path else dest
                item = QListWidgetItem(rel)
                item.setData(Qt.UserRole, rel)
                self.list_attachments.addItem(item)
            except Exception:
                continue
        self._mark_dirty()

    def remove_attachment(self):
        item = self.list_attachments.currentItem()
        if not item:
            return
        rel = item.data(Qt.UserRole)
        full = os.path.join(self.project_path, rel) if self.project_path and rel else rel
        result = QMessageBox.question(self, "Remove Attachment", "Remove attachment from plan and delete file?", QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel)
        if result == QMessageBox.Cancel:
            return
        if result == QMessageBox.Yes and full and os.path.exists(full):
            try:
                os.remove(full)
            except Exception:
                pass
        self.list_attachments.takeItem(self.list_attachments.row(item))
        self._mark_dirty()

    def open_attachment(self):
        item = self.list_attachments.currentItem()
        if not item:
            return
        rel = item.data(Qt.UserRole)
        full = os.path.join(self.project_path, rel) if self.project_path and rel else rel
        if full and os.path.exists(full):
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(full))

    def _load_attachments(self, files):
        self.list_attachments.clear()
        for rel in files or []:
            item = QListWidgetItem(rel)
            item.setData(Qt.UserRole, rel)
            self.list_attachments.addItem(item)

    def export_plan(self):
        if not self.test_plan_dir:
            QMessageBox.information(self, "Export", "Project location not set or test plan folder unavailable.")
            return
        path = os.path.join(self.test_plan_dir, "test_plan.md")
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# Test Plan\n\n")
                f.write(f"Project: {self.current_project}\n\n")
                total, passed, failed, blocked, na, not_run, last = self._summary_counts()
                f.write(f"Summary: total {total}, pass {passed}, fail {failed}, blocked {blocked}, n/a {na}, not run {not_run}\n")
                if last:
                    f.write(f"Last run: {last}\n")
                f.write("\n---\n")
                for case in self.test_plan.get("cases", []):
                    f.write(f"\n## {case.get('id','')} - {case.get('title','')}\n")
                    f.write(f"- Category: {case.get('category','')}\n")
                    f.write(f"- Priority: {case.get('priority','')}\n")
                    f.write(f"- Type: {case.get('type','')}\n")
                    f.write(f"- Status: {case.get('status','')}\n")
                    if case.get("requirement"):
                        f.write(f"- Requirement: {case.get('requirement','')}\n")
                    if case.get("preconditions"):
                        f.write("\n### Preconditions\n")
                        f.write(case.get("preconditions") + "\n")
                    if case.get("steps"):
                        f.write("\n### Steps\n")
                        for i, step in enumerate(case.get("steps", []), start=1):
                            f.write(f"{i}. {step.get('action','')} -> {step.get('expected','')}\n")
                    if case.get("notes"):
                        f.write("\n### Notes\n")
                        f.write(case.get("notes") + "\n")
            QMessageBox.information(self, "Export", f"Exported to {path}")
        except Exception as e:
            QMessageBox.warning(self, "Export", f"Failed to export: {e}")

    def open_test_plan_folder(self):
        if self.test_plan_dir and os.path.isdir(self.test_plan_dir):
            from PySide6.QtGui import QDesktopServices
            from PySide6.QtCore import QUrl
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.test_plan_dir))
        else:
            QMessageBox.information(self, "Test Plan Folder", "Project location not set or test plan folder unavailable.")

    def _next_case_id(self):
        existing = [c.get("id", "") for c in self.test_plan.get("cases", [])]
        nums = []
        for cid in existing:
            if cid.startswith("TP-"):
                try:
                    nums.append(int(cid.split("-")[1]))
                except Exception:
                    continue
        next_num = max(nums) + 1 if nums else 1
        return f"TP-{next_num:03d}"

    def _persist(self):
        if not self.current_project:
            return
        reg = self.logic.settings.setdefault("project_registry", {})
        if self.current_project not in reg:
            return
        reg[self.current_project]["test_plan"] = self.test_plan
        self.logic.save_settings()
