import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                             QGroupBox, QListWidget, QListWidgetItem, QProgressBar, QToolButton,
                             QFrame, QGridLayout, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor, QIcon
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.elevation import apply_elevation
from ui.widgets.empty_state import EmptyState
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
        apply_layout(layout, margin=PAGE_PADDING, spacing="lg")
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        self.icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        # Welcome / Stats Row
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)
        self.stat_total = self.create_stat_card("Total Projects", "0", "#3498db", Icons.PROJECTS)
        self.stat_active = self.create_stat_card("Active Projects", "0", "#2ecc71", Icons.PLAY)
        self.stat_tasks = self.create_stat_card("Pending Tasks", "0", "#e67e22", Icons.NOTEBOOK)
        self.stat_parts = self.create_stat_card("Total Parts", "0", "#9b59b6", Icons.CHIP)
        
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
        btn_new.setObjectName("btnPrimary")
        btn_new.clicked.connect(self.action_new_project)
        btn_new.setMinimumHeight(34)
        
        btn_scan = QPushButton("Rescan Libraries")
        btn_scan.setIcon(Icons.get_icon(Icons.RELOAD, self.icon_color))
        btn_scan.setObjectName("btnSecondary")
        btn_scan.clicked.connect(self.action_rescan)
        btn_scan.setMinimumHeight(34)
        
        btn_settings = QPushButton("Settings")
        btn_settings.setIcon(Icons.get_icon(Icons.SETTINGS, self.icon_color))
        btn_settings.setObjectName("btnSecondary")
        btn_settings.clicked.connect(self.action_settings)
        btn_settings.setMinimumHeight(34)
        
        btn_kicad = QPushButton("Launch KiCad")
        btn_kicad.setIcon(Icons.get_icon(Icons.EXTERNAL, self.icon_color))
        btn_kicad.setObjectName("btnSecondary")
        btn_kicad.clicked.connect(lambda: self.logic.launch_tool("kicad", ""))
        btn_kicad.setMinimumHeight(34)
        
        qa_layout.addWidget(btn_scan)
        qa_layout.addWidget(btn_settings)
        qa_layout.addWidget(btn_kicad)
        qa_layout.addStretch()
        qa_layout.addWidget(btn_new)
        left_col.addWidget(qa_gb)

        # 2. Active Projects Table
        proj_gb = QGroupBox("Recent Projects")
        proj_layout = QVBoxLayout(proj_gb)
        self.table_projects = QTableWidget(0, 3)
        self.table_projects.setHorizontalHeaderLabels(["Project Name", "Status", "Last Opened"])
        self.table_projects.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.table_projects.setColumnWidth(1, 110)
        self.table_projects.setColumnWidth(2, 160)
        self.table_projects.setAlternatingRowColors(True)
        self.table_projects.verticalHeader().setVisible(False)
        self.table_projects.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_projects.setSelectionMode(QTableWidget.SingleSelection)
        self.table_projects.itemDoubleClicked.connect(self.on_project_double_click)
        header = self.table_projects.horizontalHeader()
        header.setDefaultAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.table_projects.setStyleSheet(
            """
            QTableWidget {
                background: transparent;
                border: none;
            }
            QTableWidget::item {
                padding: 8px 10px;
                border-bottom: 1px solid rgba(255, 255, 255, 0.05);
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(59, 114, 255, 0.35),
                    stop:1 rgba(30, 64, 175, 0.25));
                color: #FFFFFF;
            }
            """
        )
        proj_layout.addWidget(self.table_projects)
        self.empty_projects = EmptyState(
            "No projects yet",
            "Create your first project to start tracking tasks and files.",
            Icons.PROJECTS,
            "New Project",
            self.action_new_project,
            self.icon_color,
        )
        self.empty_projects.setVisible(False)
        proj_layout.addWidget(self.empty_projects)
        left_col.addWidget(proj_gb)
        
        content_split.addLayout(left_col, 3)
        
        # RIGHT COLUMN
        right_col = QVBoxLayout()
        
        # 0. System Health
        self.health_gb = QGroupBox("System Health")
        h_health = QHBoxLayout(self.health_gb)
        self.lbl_health = QLabel("Checking...")
        h_health.addWidget(self.lbl_health)
        right_col.addWidget(self.health_gb)

        # 1. High Priority Tasks
        task_gb = QGroupBox("Urgent Tasks")
        task_layout = QVBoxLayout(task_gb)
        self.list_urgent = QListWidget()
        self.list_urgent.setStyleSheet("border: none; background: transparent;")
        self.list_urgent.itemDoubleClicked.connect(self.on_urgent_task_clicked)
        task_layout.addWidget(self.list_urgent)
        self.empty_urgent = EmptyState(
            "No urgent tasks",
            "Looks clear. Keep tasks updated to surface priorities.",
            Icons.NOTEBOOK,
            "Open Projects",
            lambda: self.parent().parent().setCurrentIndex(1),
            self.icon_color,
        )
        self.empty_urgent.setVisible(False)
        task_layout.addWidget(self.empty_urgent)
        right_col.addWidget(task_gb)
        
        # 2. Library Statistics
        lib_gb = QGroupBox("Library Statistics")
        lib_layout = QVBoxLayout(lib_gb)
        self.lbl_lib_stats = QLabel("Loading...")
        self.lbl_lib_stats.setStyleSheet("font-size: 13px;")
        lib_layout.addWidget(self.lbl_lib_stats)
        btn_lib_scan = QPushButton("Rescan Libraries")
        btn_lib_scan.setIcon(Icons.get_icon(Icons.RELOAD, self.icon_color))
        btn_lib_scan.clicked.connect(self.action_rescan)
        btn_lib_scan.setMinimumHeight(32)
        lib_layout.addWidget(btn_lib_scan)
        right_col.addWidget(lib_gb)
        
        content_split.addLayout(right_col, 2)
        layout.addLayout(content_split)

    # --- Actions ---
    def action_new_project(self):
        self.request_new_project.emit()

    def action_rescan(self):
        self.parent().parent().setCurrentIndex(2) # Switch to Library Manager

    def action_settings(self):
        self.parent().parent().setCurrentIndex(4) # Switch to Settings

    def create_stat_card(self, title, value, color, icon_name=None):
        icon = Icons.get_icon(icon_name, color) if icon_name else None
        theme = self.logic.settings.get("theme", "Light")
        card = StatsCard(title, value, accent=color, icon=icon, theme=theme)
        card.val_label = card.value_label  # for compatibility
        return card

    def _project_part_count(self, structure):
        if not isinstance(structure, dict):
            return 0
        total = structure.get("part_count")
        if isinstance(total, (int, float)) and total > 0:
            return int(total)

        def sum_nodes(node):
            if not node or not isinstance(node, dict):
                return 0
            part = int(node.get("part_count") or 0)
            for child in node.get("children", []):
                part += sum_nodes(child)
            return part

        tree = structure.get("tree")
        return sum_nodes(tree) if tree else 0

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
            struct = p_data.get("structure", {}) or {}
            total_parts += self._project_part_count(struct)
            
            # Collect projects for list
            all_projects_list.append(p_data["metadata"])

        # Sort by pinned (desc), then last_accessed (desc)
        all_projects_list.sort(key=lambda x: (x.get("pinned", False), x.get("last_accessed", "")), reverse=True)

        self.stat_total.val_label.setText(str(total_projs))
        self.stat_active.val_label.setText(str(active_projs))
        self.stat_tasks.val_label.setText(str(total_tasks))
        self.stat_parts.val_label.setText(str(total_parts))
        
        self.empty_projects.setVisible(total_projs == 0)
        self.table_projects.setVisible(total_projs != 0)
        self.empty_urgent.setVisible(len(urgent_tasks) == 0)
        self.list_urgent.setVisible(len(urgent_tasks) != 0)
        
        # Health Check
        sym_path = self.logic.settings.get("symbol_path", "")
        fp_path = self.logic.settings.get("footprint_path", "")
        if sym_path and fp_path:
            self.lbl_health.setText("Libraries configured")
            self.lbl_health.setStyleSheet("color: #27ae60; font-weight: 600;")
        else:
            self.lbl_health.setText("Libraries missing (check Settings)")
            self.lbl_health.setStyleSheet("color: #e74c3c; font-weight: 600;")
        
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
            wid = QWidget()
            h = QHBoxLayout(wid)
            h.setContentsMargins(5, 2, 5, 2)
            h.setAlignment(Qt.AlignCenter)
            h.addWidget(lbl_status)
            self.table_projects.setCellWidget(row, 1, wid)

            # Last Opened
            last_item = QTableWidgetItem(p.get("last_accessed", "-"))
            last_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignRight)
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
