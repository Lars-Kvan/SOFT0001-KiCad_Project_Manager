from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QLabel,
    QGroupBox,
    QProgressBar,
    QSplitter,
    QFrame,
)
from PySide6.QtCore import Qt
from collections import Counter
import os

from ui.widgets.stats_card import StatsCard
from ui.widgets.progress_utils import style_progress_bar
from ui.widgets.elevation import apply_layered_elevation


class ProjectStatsView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        stats_wrapper = QFrame()
        stats_wrapper.setObjectName("projectStatsWrapper")
        stats_layout = QVBoxLayout(stats_wrapper)
        stats_layout.setContentsMargins(10, 10, 10, 10)
        stats_layout.setSpacing(8)

        self.summary_grid = QGridLayout()
        self.summary_grid.setHorizontalSpacing(12)
        self.summary_grid.setVerticalSpacing(12)
        stats_layout.addLayout(self.summary_grid)

        apply_layered_elevation(stats_wrapper, level="card", theme="Dark" if self.logic.settings.get("theme", "Light") in {"Dark", "Teal Sand Dark"} else "Light")
        layout.addWidget(stats_wrapper)

        theme = self.logic.settings.get("theme", "Light")
        self.stat_parts = StatsCard("Total Parts", accent="#3B74D6", theme=theme)
        self.stat_libs = StatsCard("Unique Libraries", accent="#16A34A", theme=theme)
        self.stat_footprints = StatsCard("Unique Footprints", accent="#9B59B6", theme=theme)
        self.stat_requirements = StatsCard("Requirements", accent="#D97706", theme=theme)
        self.stat_checklist = StatsCard("Checklist Progress", accent="#0F766E", theme=theme)
        self.stat_kanban = StatsCard("Kanban Progress", accent="#E67E22", theme=theme)

        self.summary_grid.addWidget(self.stat_parts, 0, 0)
        self.summary_grid.addWidget(self.stat_libs, 0, 1)
        self.summary_grid.addWidget(self.stat_footprints, 0, 2)
        self.summary_grid.addWidget(self.stat_requirements, 1, 0)
        self.summary_grid.addWidget(self.stat_checklist, 1, 1)
        self.summary_grid.addWidget(self.stat_kanban, 1, 2)

        progress_frame = QFrame()
        progress_frame.setObjectName("projectStatsProgress")
        progress_layout = QHBoxLayout(progress_frame)
        progress_layout.setContentsMargins(0, 0, 0, 0)
        progress_layout.setSpacing(8)

        self.req_summary = QLabel("Requirements — 0 verified")
        self.req_summary.setObjectName("projectStatsMini")
        progress_layout.addWidget(self.req_summary)
        self.kanban_summary = QLabel("Kanban — 0%")
        self.kanban_summary.setObjectName("projectStatsMini")
        progress_layout.addWidget(self.kanban_summary)
        progress_layout.addStretch()
        layout.addWidget(progress_frame)

        splitter = QSplitter(Qt.Horizontal)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)

        bom_gb = QGroupBox("BOM Breakdown")
        bom_layout = QVBoxLayout(bom_gb)
        self.tbl_libs = QTableWidget(0, 3)
        self.tbl_libs.setHorizontalHeaderLabels(["Library", "Qty", "Share"])
        self.tbl_libs.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_libs.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_libs.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_libs.setAlternatingRowColors(True)
        bom_layout.addWidget(self.tbl_libs)
        left_layout.addWidget(bom_gb)

        files_gb = QGroupBox("Project Files")
        files_layout = QVBoxLayout(files_gb)
        self.lbl_files = QLabel("-")
        self.lbl_files.setWordWrap(True)
        files_layout.addWidget(self.lbl_files)
        left_layout.addWidget(files_gb)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        right_layout.setContentsMargins(0, 0, 0, 0)

        req_gb = QGroupBox("Requirements Status")
        req_layout = QVBoxLayout(req_gb)
        self.tbl_requirements = QTableWidget(0, 2)
        self.tbl_requirements.setHorizontalHeaderLabels(["Status", "Count"])
        self.tbl_requirements.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_requirements.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_requirements.setAlternatingRowColors(True)
        req_layout.addWidget(self.tbl_requirements)
        right_layout.addWidget(req_gb)

        checklist_gb = QGroupBox("Checklist Overview")
        checklist_layout = QVBoxLayout(checklist_gb)
        self.chk_progress = QProgressBar()
        theme = self.logic.settings.get("theme", "Light")
        style_progress_bar(self.chk_progress, accent="#D97706", theme=theme, min_height=14, max_height=18)
        self.chk_progress.setRange(0, 100)
        self.chk_progress.setFormat("%v% Verified")
        checklist_layout.addWidget(self.chk_progress)
        self.tbl_checklist = QTableWidget(0, 3)
        self.tbl_checklist.setHorizontalHeaderLabels(["Category", "Verified", "Total"])
        self.tbl_checklist.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tbl_checklist.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.tbl_checklist.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.tbl_checklist.setAlternatingRowColors(True)
        checklist_layout.addWidget(self.tbl_checklist)
        right_layout.addWidget(checklist_gb)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([520, 480])
        layout.addWidget(splitter)

    def load_data(self, project_name, data):
        meta = data.get("metadata", {})
        main_sch = meta.get("main_schematic", "")
        sch = self.logic.resolve_path(main_sch) if hasattr(self.logic, "resolve_path") else main_sch

        bom = []
        if sch and os.path.exists(sch):
            try:
                bom = self.logic.generate_bom(sch)
            except Exception:
                bom = []

        total_parts = sum(item.get("qty", 0) for item in bom)
        lib_counts = Counter()
        footprint_counts = Counter()
        for item in bom:
            lib_id = item.get("lib_id", "")
            lib = lib_id.split(":")[0] if lib_id else "Unknown"
            lib_counts[lib] += item.get("qty", 0)
            fp = item.get("footprint", "") or "Unknown"
            footprint_counts[fp] += item.get("qty", 0)

        self.stat_parts.set_value(total_parts)
        self.stat_libs.set_value(len(lib_counts))
        self.stat_footprints.set_value(len(footprint_counts))

        # Requirements summary
        reqs = data.get("requirements", []) or []
        req_status = Counter([r.get("status", "Draft") for r in reqs])
        verified_req = req_status.get("Verified", 0)
        self.stat_requirements.set_value(f"{verified_req}/{len(reqs)} verified")
        self.req_summary.setText(f"Requirements — {verified_req}/{len(reqs)} verified")

        # Checklist summary
        checklist = data.get("checklist", {}) or {}
        total_rules, verified_rules, na_rules, per_category = self._checklist_counts(checklist)
        chk_pct = int((verified_rules / total_rules) * 100) if total_rules else 0
        self.chk_progress.setValue(chk_pct)
        self.stat_checklist.set_value(f"{chk_pct}%")

        # Kanban summary
        kanban = data.get("kanban", {}) or {}
        kanban_pct = self._kanban_progress(kanban)
        self.stat_kanban.set_value(f"{kanban_pct}%")
        self.kanban_summary.setText(f"Kanban — {kanban_pct}%")

        # Tables
        self._load_lib_table(lib_counts, total_parts)
        self._load_requirements_table(req_status)
        self._load_checklist_table(per_category)
        self._load_file_summary(meta.get("location", ""))

    def _load_lib_table(self, lib_counts, total_parts):
        self.tbl_libs.setRowCount(0)
        for lib, count in lib_counts.most_common():
            row = self.tbl_libs.rowCount()
            self.tbl_libs.insertRow(row)
            self.tbl_libs.setItem(row, 0, QTableWidgetItem(lib))
            self.tbl_libs.setItem(row, 1, QTableWidgetItem(str(count)))
            share = f"{int((count / total_parts) * 100)}%" if total_parts else "-"
            self.tbl_libs.setItem(row, 2, QTableWidgetItem(share))

    def _load_requirements_table(self, req_status):
        self.tbl_requirements.setRowCount(0)
        for status, count in req_status.most_common():
            row = self.tbl_requirements.rowCount()
            self.tbl_requirements.insertRow(row)
            self.tbl_requirements.setItem(row, 0, QTableWidgetItem(status))
            self.tbl_requirements.setItem(row, 1, QTableWidgetItem(str(count)))

    def _load_checklist_table(self, per_category):
        self.tbl_checklist.setRowCount(0)
        for cat, counts in per_category.items():
            verified, total = counts
            row = self.tbl_checklist.rowCount()
            self.tbl_checklist.insertRow(row)
            self.tbl_checklist.setItem(row, 0, QTableWidgetItem(cat))
            self.tbl_checklist.setItem(row, 1, QTableWidgetItem(str(verified)))
            self.tbl_checklist.setItem(row, 2, QTableWidgetItem(str(total)))

    def _load_file_summary(self, location):
        if not location:
            self.lbl_files.setText("-")
            return
        path = self.logic.resolve_path(location) if hasattr(self.logic, "resolve_path") else location
        if not path or not os.path.exists(path):
            self.lbl_files.setText("-")
            return
        counts = Counter()
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if not d.startswith('.') and "backup" not in d and "backups" not in d]
            for f in files:
                ext = os.path.splitext(f)[1].lower()
                if ext in (".kicad_prl", ".lck", ".bak"):
                    continue
                counts[ext] += 1
        parts = []
        for ext in [".kicad_sch", ".kicad_pcb", ".pdf", ".step", ".stp", ".csv", ".md", ".txt"]:
            if counts.get(ext):
                parts.append(f"{ext}: {counts[ext]}")
        total = sum(counts.values())
        summary = ", ".join(parts) if parts else "No files counted"
        self.lbl_files.setText(f"Total files: {total}\n{summary}")

    def _checklist_counts(self, checklist):
        total = 0
        verified = 0
        na = 0
        per_category = {}
        for cat, rules in checklist.items():
            if isinstance(rules, dict) and "rules" in rules:
                rules = rules.get("rules", [])
            if not isinstance(rules, list):
                continue
            c_total = 0
            c_verified = 0
            for rule in rules:
                if not isinstance(rule, dict):
                    continue
                status = rule.get("status", "No")
                if status == "N/A":
                    na += 1
                    continue
                c_total += 1
                total += 1
                if status == "Yes":
                    c_verified += 1
                    verified += 1
            per_category[cat] = (c_verified, c_total)
        return total, verified, na, per_category

    def _kanban_progress(self, kanban):
        total_weight = 0
        weighted_sum = 0
        weights = self.logic.settings.get(
            "kanban_priority_weights",
            {"Critical": 5, "High": 3, "Normal": 1, "Low": 0.5},
        )
        for col in kanban.values():
            for task in col:
                prio = task.get("priority", "Normal")
                w = weights.get(prio, 1)
                total_weight += w
                weighted_sum += (task.get("progress", 0) * w)
        return int(weighted_sum / total_weight) if total_weight else 0
