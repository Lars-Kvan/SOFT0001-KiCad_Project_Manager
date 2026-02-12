import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                             QGroupBox, QListWidget, QListWidgetItem, QProgressBar, QToolButton,
                             QFrame, QGridLayout, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon
try:
    from .icons import Icons
    from .widgets.elevation import apply_layered_elevation
    from .widgets.stats_card import StatsCard
except ImportError:
    from ui.icons import Icons
    from ui.widgets.elevation import apply_layered_elevation
    from ui.widgets.stats_card import StatsCard

class DashboardTab(QWidget):
    request_project_load = Signal(str, str)
    request_new_project = Signal()

    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        self.icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        
        # Welcome / Stats Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(15)
        self.stat_total = StatsCard("Total Projects", "0", accent="#3498db", theme=theme)
        self.stat_active = StatsCard("Active Projects", "0", accent="#2ecc71", theme=theme)
        self.stat_tasks = StatsCard("Pending Tasks", "0", accent="#e67e22", theme=theme)
        self.stat_parts = StatsCard("Total Parts", "0", accent="#9b59b6", theme=theme)
        
        stats_layout.addWidget(self.stat_total, 1)
        stats_layout.addWidget(self.stat_active, 1)
        stats_layout.addWidget(self.stat_tasks, 1)
        stats_layout.addWidget(self.stat_parts, 1)
        layout.addLayout(stats_layout)

        # Main Content Split
        content_split = QHBoxLayout()
        
        # LEFT COLUMN
        left_col = QVBoxLayout()
        
        # 1. Quick Actions
        qa_gb = QGroupBox("Quick Actions")
        qa_layout = QHBoxLayout(qa_gb)
        
        btn_new = QPushButton("New Project")
        btn_new.setIcon(Icons.get_icon(Icons.PLUS, "white"))
        btn_new.clicked.connect(self.action_new_project)
        btn_new.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold; padding: 8px;")
        
        btn_scan = QPushButton("Rescan Libraries")
        btn_scan.setIcon(Icons.get_icon(Icons.RELOAD, self.icon_color))
        btn_scan.clicked.connect(self.action_rescan)
        
        btn_settings = QPushButton("Settings")
        btn_settings.setIcon(Icons.get_icon(Icons.SETTINGS, self.icon_color))
        btn_settings.clicked.connect(self.action_settings)
        
        btn_kicad = QPushButton("Launch KiCad")
        btn_kicad.setIcon(Icons.get_icon(Icons.EXTERNAL, self.icon_color))
        btn_kicad.clicked.connect(lambda: self.logic.launch_tool("kicad", ""))

        qa_layout.addWidget(btn_new)
        qa_layout.addWidget(btn_scan)
        qa_layout.addWidget(btn_settings)
        qa_layout.addWidget(btn_kicad)
        left_col.addWidget(qa_gb)
        apply_layered_elevation(qa_gb, level="secondary", theme=theme)

        # 2. Active Projects Table
        proj_gb = QGroupBox("Recent Projects")
        proj_layout = QVBoxLayout(proj_gb)
        self.table_projects = QTableWidget(0, 3)
        self.table_projects.setHorizontalHeaderLabels(["Project Name", "Status", "Last Opened"])
        self.table_projects.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_projects.setColumnWidth(1, 110)
        self.table_projects.setColumnWidth(2, 160)
        self.table_projects.verticalHeader().setDefaultSectionSize(34)
        self.table_projects.verticalHeader().setVisible(False)
        self.table_projects.setAlternatingRowColors(True)
        self.table_projects.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_projects.setSelectionMode(QTableWidget.SingleSelection)
        self.table_projects.itemDoubleClicked.connect(self.on_project_double_click)
        proj_layout.addWidget(self.table_projects)
        left_col.addWidget(proj_gb)
        apply_layered_elevation(proj_gb, level="secondary", theme=theme)
        
        content_split.addLayout(left_col, 3)
        
        # RIGHT COLUMN
        right_col = QVBoxLayout()
        
        # 0. System Health
        self.health_gb = QGroupBox("System Health")
        h_health = QHBoxLayout(self.health_gb)
        self.lbl_health = QLabel("Checking...")
        h_health.addWidget(self.lbl_health)
        right_col.addWidget(self.health_gb)
        apply_layered_elevation(self.health_gb, level="secondary", theme=theme)

        # 1. High Priority Tasks
        task_gb = QGroupBox("Urgent Tasks")
        task_layout = QVBoxLayout(task_gb)
        self.list_urgent = QListWidget()
        self.list_urgent.setStyleSheet("border: none; background: transparent;")
        self.list_urgent.itemDoubleClicked.connect(self.on_urgent_task_clicked)
        task_layout.addWidget(self.list_urgent)
        right_col.addWidget(task_gb)
        apply_layered_elevation(task_gb, level="secondary", theme=theme)
        
        # 2. Library Statistics
        lib_gb = QGroupBox("Library Statistics")
        lib_layout = QVBoxLayout(lib_gb)
        self.lbl_lib_stats = QLabel("Loading...")
        self.lbl_lib_stats.setStyleSheet("font-size: 13px;")
        lib_layout.addWidget(self.lbl_lib_stats)
        btn_lib_scan = QPushButton("Rescan Libraries")
        btn_lib_scan.setIcon(Icons.get_icon(Icons.RELOAD, self.icon_color))
        btn_lib_scan.clicked.connect(self.action_rescan)
        lib_layout.addWidget(btn_lib_scan)
        right_col.addWidget(lib_gb)
        apply_layered_elevation(lib_gb, level="secondary", theme=theme)
        
        content_split.addLayout(right_col, 2)
        layout.addLayout(content_split)

    # --- Actions ---
    def action_new_project(self):
        self.request_new_project.emit()

    def action_rescan(self):
        self.parent().parent().setCurrentIndex(2) # Switch to Library Manager

    def action_settings(self):
        self.parent().parent().setCurrentIndex(4) # Switch to Settings

    def refresh_data(self):
        registry = self.logic.settings.get("project_registry", {})
        visible_projects = self.logic.settings.get("projects", [])
        
        # Stats
        # Only count projects that are in the 'projects' list (not deleted ones still in registry)
        valid_registry = {k: v for k, v in registry.items() if k in visible_projects}
        
        total_projs = len(valid_registry)
        active_projs = sum(1 for p in valid_registry.values() if p["metadata"].get("status") not in ["Released", "Abandoned"])
        
        total_tasks = 0
        urgent_tasks = []
        total_parts = 0
        all_projects_list = []
        
        for p_name, p_data in valid_registry.items():
            # Count tasks
            kanban = p_data.get("kanban", {})
            for col in ["todo", "prog"]:
                tasks = kanban.get(col, [])
                total_tasks += len(tasks)
                for t in tasks:
                    if t.get("priority") in ["High", "Critical"]:
                        item = QListWidgetItem(f"[{p_data['metadata'].get('name', p_name)}] {t['name']}")
                        item.setData(Qt.UserRole, (p_name, t['name']))
                        urgent_tasks.append(item)
            
            # Count parts (if structure scanned)
            struct = p_data.get("structure", {})
            total_parts += struct.get("part_count", 0)
            
            # Collect projects for list
            all_projects_list.append(p_data["metadata"])

        # Sort by pinned (desc), then last_accessed (desc)
        all_projects_list.sort(key=lambda x: (x.get("pinned", False), x.get("last_accessed", "")), reverse=True)

        self.stat_total.set_value(total_projs)
        self.stat_active.set_value(active_projs)
        self.stat_tasks.set_value(total_tasks)
        self.stat_parts.set_value(total_parts)
        
        # Health Check
        sym_path = self.logic.settings.get("symbol_path", "")
        fp_path = self.logic.settings.get("footprint_path", "")
        if sym_path and fp_path:
            self.lbl_health.setText("✅ Libraries Configured")
            self.lbl_health.setStyleSheet("color: #27ae60; font-weight: bold;")
        else:
            self.lbl_health.setText("❌ Libraries Missing (Check Settings)")
            self.lbl_health.setStyleSheet("color: #e74c3c; font-weight: bold;")
        
        # Update Urgent List
        self.list_urgent.clear()
        for t in urgent_tasks:
            self.list_urgent.addItem(t)
            
        type_map = {
            "PCB": "PCBA",
            "Mechanical": "MECH",
            "Software": "SOFT",
            "Firmware": "FIRM",
            "Other": "MISC"
        }

        status_colors = {
            "Pre-Design": "#7f8c8d",      # Gray
            "Schematic Capture": "#3498db", # Blue
            "PCB Layout": "#9b59b6",      # Purple
            "Prototyping": "#e67e22",     # Orange
            "Validation": "#1abc9c",      # Teal
            "Released": "#2ecc71",        # Green
            "Abandoned": "#c0392b",       # Red
            "Archived": "#34495e"         # Dark Blue/Gray
        }

        # Update Recent Projects Table (Top 15)
        self.table_projects.setRowCount(0)
        for p in all_projects_list[:15]:
            row = self.table_projects.rowCount()
            self.table_projects.insertRow(row)
            
            ptype = p.get("type", "Other")
            code = type_map.get(ptype, "MISC")
            num = p.get("number", "")
            rev = p.get("revision", "")
            name = p.get("name", "Unknown")
            
            display_name = f"{code}{num}{rev} - {name}"
            name_item = QTableWidgetItem(display_name)
            name_item.setData(Qt.UserRole, p.get("name")) # Store ID
            name_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            if p.get("pinned"):
                name_item.setIcon(Icons.get_icon(Icons.PIN, self.icon_color))
            
            self.table_projects.setItem(row, 0, name_item)
            
            # Status Badge
            status_text = p.get("status", "-")
            col = status_colors.get(status_text, "#7f8c8d")
            lbl_status = QLabel(status_text)
            lbl_status.setStyleSheet(f"background-color: {col}; color: white; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            lbl_status.setAlignment(Qt.AlignCenter)
            wid = QWidget(); h = QHBoxLayout(wid); h.setContentsMargins(0, 0, 0, 0); h.setAlignment(Qt.AlignCenter); h.addWidget(lbl_status)
            self.table_projects.setCellWidget(row, 1, wid)

            # Last Opened
            last_item = QTableWidgetItem(p.get("last_accessed", "-"))
            last_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.table_projects.setItem(row, 2, last_item)

    def on_project_double_click(self, item):
        # Get the project name from the first column of the selected row
        row = item.row()
        name_item = self.table_projects.item(row, 0)
        project_name = name_item.data(Qt.UserRole)
        self.request_project_load.emit(project_name, "")

    def on_urgent_task_clicked(self, item):
        data = item.data(Qt.UserRole)
        if data:
            self.request_project_load.emit(data[0], data[1])

    def showEvent(self, event):
        self.refresh_data()
        super().showEvent(event)
