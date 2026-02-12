import os
from datetime import datetime, timedelta
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QFrame,
                             QPushButton, QFileDialog, QGroupBox, QTabWidget, QGridLayout,
                             QListWidgetItem, QMessageBox, QLabel, QInputDialog, QLineEdit, QComboBox, QProgressBar, QMenu, QToolButton, QCheckBox,
                             QDialog, QFormLayout, QSpinBox, QSplitter, QSizePolicy)
from PySide6.QtCore import Qt, Signal, QUrl, QSize
from PySide6.QtGui import QDesktopServices
import logging

from ui.widgets.kanban_widgets import KanbanList, KanbanTaskWidget
from ui.views.project_status_view import ProjectStatusView 
from ui.views.project_details_view import ProjectDetailsView
from ui.widgets.checklist_widget import ChecklistWidget
from ui.views.requirements_view import RequirementsView
from ui.views.ui_bom import BOMTab
from ui.views.ui_pricing import PricingTab
from ui.views.project_docs_view import ProjectDocsView
from ui.views.project_stats_view import ProjectStatsView
from ui.views.project_test_plan_view import ProjectTestPlanView
from ui.views.project_tasks_view import ProjectTasksView
from ui.views.fabrication_view import FabricationView
from ui.views.ui_git import GitTab
from ui.resources.icons import Icons
from ui.resources.styles import Styles
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.modal_utils import apply_modal_style
from ui.widgets.progress_utils import style_progress_bar
from kanban_templates import columns_from_templates

_DARK_THEMES = {"Dark", "Teal Sand Dark"}
PROJECT_STATUS_DEFAULTS = [
    "Pre-Design",
    "Schematic Capture",
    "PCB Layout",
    "Prototyping",
    "Validation",
    "Released",
    "Abandoned",
]

RECENT_DAYS = 14
KANBAN_DEFAULT_LIMITS = {"todo": 0, "prog": 0, "done": 0}

class ProjectManagerTab(QWidget):
    """Manages project-related views: Kanban, Requirements, Status, Details, Checklist, BOM, Pricing."""
    project_selected = Signal(str)
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.columns = {}
        self.kanban_labels = {}
        self.kanban_titles = {}
        self.is_compact_kanban = False
        self.last_kanban_category = ""
        self.saved_filter_presets = self.logic.settings.get("project_filter_presets", []).copy()
        self.active_filter_preset = None
        self._preset_button_map = {}
        self.setup_ui()

    def setup_ui(self):
        """Sets up the main layout and widgets for the Project Manager tab."""
        root = QVBoxLayout(self)
        apply_layout(root, margin=PAGE_PADDING, spacing="sm")

        main_layout = QHBoxLayout()
        root.addLayout(main_layout, 1)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        self.icon_color = "#E0E0E0" if theme == "Dark" else "#555555"
        self.is_dark_theme = theme == "Dark"
        self.meta_text_color = "#A0A0A0" if self.is_dark_theme else "#666666"

        # 1. Projects Sidebar/Selector (Moved to Left)
        top_panel = QGroupBox("Projects")
        top_panel.setMinimumWidth(320)
        top_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        top_layout = QVBoxLayout(top_panel)
        
        # Search & Sort
        # Search input field
        self.search_proj = QLineEdit()
        self.search_proj.setPlaceholderText("Search Projects...")
        self.search_proj.textChanged.connect(self.refresh_paths)
        search_row = QHBoxLayout()
        lbl_search = QLabel()
        lbl_search.setPixmap(Icons.get_icon(Icons.SEARCH, self.icon_color).pixmap(16, 16))
        lbl_search.setToolTip("Search")
        search_row.addWidget(lbl_search)
        search_row.addWidget(self.search_proj)
        top_layout.addLayout(search_row)

        # Filter by Project Type dropdown
        self.filter_type = QComboBox()
        self.filter_type.addItem("All Types")
        self.filter_type.addItems(self.logic.settings.get("project_types", []))
        self.filter_type.currentIndexChanged.connect(self.refresh_paths)

        # Sort Projects dropdown
        self.sort_proj = QComboBox()
        self.sort_proj.addItems(["Sort by Name", "Sort by Type", "Sort by Number"])
        self.sort_proj.currentIndexChanged.connect(self.refresh_paths)

        filter_row = QHBoxLayout()
        lbl_type = QLabel()
        lbl_type.setPixmap(Icons.get_icon(Icons.PROJECTS, self.icon_color).pixmap(16, 16))
        lbl_type.setToolTip("Filter by type")
        self.filter_status = QComboBox()
        self.filter_status.addItem("All Statuses")
        self.filter_status.addItems(self.logic.settings.get("project_statuses", PROJECT_STATUS_DEFAULTS))
        self.filter_status.currentIndexChanged.connect(self.refresh_paths)
        self.filter_tags = QLineEdit()
        self.filter_tags.setPlaceholderText("Tags (comma-separated)")
        self.filter_tags.textChanged.connect(self.refresh_paths)
        filter_row.addWidget(lbl_type)
        filter_row.addWidget(self.filter_type)
        lbl_status = QLabel("Status:")
        lbl_status.setStyleSheet("font-weight: 600;")
        filter_row.addWidget(lbl_status)
        filter_row.addWidget(self.filter_status)
        lbl_tags = QLabel("Tags:")
        lbl_tags.setStyleSheet("font-weight: 600;")
        filter_row.addWidget(lbl_tags)
        filter_row.addWidget(self.filter_tags, 1)
        lbl_sort = QLabel()
        lbl_sort.setPixmap(Icons.get_icon(Icons.SORT, self.icon_color).pixmap(16, 16))
        lbl_sort.setToolTip("Sort")
        filter_row.addWidget(lbl_sort)
        filter_row.addWidget(self.sort_proj)
        top_layout.addLayout(filter_row)

        # Quick Filter Chips
        chip_row = QHBoxLayout()
        self.chip_pinned = self._make_filter_chip("Pinned", Icons.PIN)
        self.chip_recent = self._make_filter_chip("Recent", Icons.CLOCK)
        self.chip_archived = self._make_filter_chip("Archived", Icons.ARCHIVE)
        chip_row.addWidget(self.chip_pinned)
        chip_row.addWidget(self.chip_recent)
        chip_row.addWidget(self.chip_archived)
        chip_row.addStretch()
        top_layout.addLayout(chip_row)

        saved_row = QHBoxLayout()
        saved_label = QLabel("Saved Views:")
        saved_label.setStyleSheet("font-weight: 600;")
        saved_row.addWidget(saved_label)
        self.saved_filter_panel = QWidget()
        self.saved_filter_layout = QHBoxLayout(self.saved_filter_panel)
        self.saved_filter_layout.setContentsMargins(0, 0, 0, 0)
        self.saved_filter_layout.setSpacing(6)
        saved_row.addWidget(self.saved_filter_panel, 1)
        self.btn_save_filter = QPushButton("Save View")
        self.btn_save_filter.setIcon(Icons.get_icon(Icons.SAVE, self.icon_color))
        self.btn_save_filter.clicked.connect(self._save_current_filter_preset)
        saved_row.addWidget(self.btn_save_filter)
        self.btn_clear_filters = QPushButton("Clear Filters")
        self.btn_clear_filters.clicked.connect(self._clear_filter_preset)
        saved_row.addWidget(self.btn_clear_filters)
        saved_row.addStretch()
        top_layout.addLayout(saved_row)
        self._render_saved_filter_buttons()

        # List of Projects
        self.list_paths = QListWidget()
        self.list_paths.setSpacing(2)
        
        list_bg = "#18181b" if self.is_dark_theme else "#ffffff"
        list_hover = "#27272a" if self.is_dark_theme else "#f4f4f5"
        list_sel = "#3f3f46" if self.is_dark_theme else "#e4e4e7"
        list_border = "#27272a" if self.is_dark_theme else "#d4d4d8"

        self.list_paths.setStyleSheet(f"""
            QListWidget {{
                background-color: {list_bg};
                border: 1px solid {list_border};
                border-radius: 8px;
                outline: none;
            }}
            QListWidget::item {{
                padding: 2px;
                border-radius: 6px;
                margin: 1px;
            }}
            QListWidget::item:hover {{ background-color: {list_hover}; }}
            QListWidget::item:selected {{ background-color: {list_sel}; }}
        """)
        # Connect item selection to the project switching handler
        self.list_paths.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_paths.customContextMenuRequested.connect(self.show_project_menu)
        self.list_paths.itemSelectionChanged.connect(self.on_project_switch)
        top_layout.addWidget(self.list_paths)
        
        # Buttons for adding/removing projects
        btn_add = QPushButton("New Project")
        btn_add.setIcon(Icons.get_icon(Icons.PLUS, self.icon_color))
        btn_add.clicked.connect(self.add_project)
        btn_rem = QPushButton("Delete Project")
        btn_rem.setIcon(Icons.get_icon(Icons.TRASH, self.icon_color))
        btn_rem.clicked.connect(self.rem_project)
        btn_open = QPushButton("Open Folder")
        btn_open.setIcon(Icons.get_icon(Icons.FOLDER, self.icon_color))
        btn_open.clicked.connect(self.open_project_folder)
        # Actions Menu
        btn_actions = QToolButton()
        btn_actions.setText("Project Actions")
        btn_actions.setIcon(Icons.get_icon(Icons.SETTINGS, self.icon_color))
        btn_actions.setPopupMode(QToolButton.InstantPopup)
        act_menu = QMenu()
        act_menu.addAction("Clone Project", self.clone_project)
        act_menu.addAction("Archive Project", self.archive_project)
        act_menu.addAction("Clean Temporary Files", self.clean_project_files)
        btn_actions.setMenu(act_menu)

        btn_grid = QGridLayout()
        btn_grid.setSpacing(6)
        btn_grid.addWidget(btn_add, 0, 0, 1, 2)
        btn_grid.addWidget(btn_open, 1, 0, 1, 2)
        btn_grid.addWidget(btn_rem, 2, 0)
        btn_grid.addWidget(btn_actions, 2, 1)
        top_layout.addLayout(btn_grid)
        
        # 2. Sub-Tabs for Project Details (Right Panel)
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setObjectName("projectSubTabs")
        self.sub_tabs.setProperty("stretchTabs", False)
        self.sub_tabs.setMovable(True) # Allow users to reorder sub-tabs
        # Allow the tab bar to size itself to content and show scroll buttons when necessary.
        self.sub_tabs.setUsesScrollButtons(True)
        self.sub_tabs.tabBar().setExpanding(False)
        self.sub_tabs.tabBar().setElideMode(Qt.ElideNone)
        self.sub_tabs.setStyleSheet("QTabBar::tab { padding: 8px 14px; min-width: 120px; } QTabBar::tab:selected { margin-bottom: -1px; }")
        self.sub_tabs.setIconSize(QSize(20, 20))
        self._ensure_valid_tabbar_font(self.sub_tabs.tabBar())
        
        # --- Kanban Tab ---
        # This tab displays tasks organized in ToDo, In Progress, Done columns.
        self.tab_kanban = QWidget()
        theme = self.logic.settings.get("theme", "Light")
        panel_theme = "Dark" if theme in _DARK_THEMES else "Light"
        self.tab_kanban.setObjectName("projectPanel")
        self.tab_kanban.setProperty("projectTheme", panel_theme)
        self.setup_kanban_ui(self.tab_kanban)
        self.sub_tabs.addTab(self.tab_kanban, Icons.get_icon(Icons.NOTEBOOK, self.icon_color), "Kanban")

        # --- Tasks Tab ---
        # Lightweight task + time entry manager synced to project registry.
        self.tasks_view = ProjectTasksView(self.logic)
        self.sub_tabs.addTab(self.tasks_view, Icons.get_icon(Icons.CHECKLIST, self.icon_color), "Tasks")

        # Sub-Tab New: Requirements
        self.req_view = RequirementsView(self.logic)
        self.sub_tabs.addTab(self.req_view, Icons.get_icon(Icons.REQUIREMENTS, self.icon_color), "Requirements")

        # --- Configuration Tab ---
        # Displays general project information like name, number, status, location.
        self.status_view = ProjectStatusView(self.logic)
        # Connect status view save button to the registry save logic
        # This ensures changes in the status view are persisted.
        if hasattr(self.status_view, 'btn_save'):
            self.status_view.btn_save.clicked.connect(self.save_project_metadata)
            
        self.sub_tabs.addTab(self.status_view, Icons.get_icon(Icons.SETTINGS, self.icon_color), "Configuration")

        # Sub-Tab New: Details
        self.details_view = ProjectDetailsView(self.logic)
        if hasattr(self.details_view, 'btn_save'):
            self.details_view.btn_save.clicked.connect(self.save_project_metadata)
        self.sub_tabs.addTab(self.details_view, Icons.get_icon(Icons.EDIT, self.icon_color), "Details")

        # Sub-Tab C: Checklist
        self.checklist_view = ChecklistWidget(self)
        self.sub_tabs.addTab(self.checklist_view, Icons.get_icon(Icons.CHECKLIST, self.icon_color), "Checklist")

        # Sub-Tab New: Documents
        self.docs_view = ProjectDocsView(self.logic)
        self.sub_tabs.addTab(self.docs_view, Icons.get_icon(Icons.DOCUMENTS, self.icon_color), "Documents")

        # Sub-Tab New: Test Plan
        self.test_plan_view = ProjectTestPlanView(self.logic)
        self.sub_tabs.addTab(self.test_plan_view, Icons.get_icon(Icons.CHECKLIST, self.icon_color), "Test Plan")

        # Sub-Tab New: Stats
        self.stats_view = ProjectStatsView(self.logic)
        self.sub_tabs.addTab(self.stats_view, Icons.get_icon(Icons.STATS, self.icon_color), "Statistics")

        # Sub-Tab New: Git (Project-specific)
        self.project_git_view = GitTab(self.logic, compact=True)
        self.sub_tabs.addTab(self.project_git_view, Icons.get_icon(Icons.GIT, self.icon_color), "Git")

        # Sub-Tab New: Fabrication
        self.fab_view = FabricationView(self.logic)
        self.sub_tabs.addTab(self.fab_view, Icons.get_icon(Icons.FAB, self.icon_color), "Fabrication")

        # Sub-Tab D: BOM
        self.bom_tab = BOMTab(self.logic)
        self.sub_tabs.addTab(self.bom_tab, Icons.get_icon(Icons.BOM, self.icon_color), "Bill of Materials")
        
        # --- Pricing & Stock Tab ---
        # Fetches and displays pricing and availability for BOM items.
        # Sub-Tab E: Pricing
        self.pricing_tab = PricingTab(self.logic)
        self.sub_tabs.addTab(self.pricing_tab, Icons.get_icon(Icons.GLOBE, self.icon_color), "Pricing & Stock")

        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        right_layout.addWidget(self.sub_tabs, 1)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(top_panel)
        splitter.addWidget(right_container)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setCollapsible(0, False)
        splitter.setSizes([360, 940])

        main_layout.addWidget(splitter)

        # 3. Final Initialization
        self.refresh_paths()

    def _ensure_valid_tabbar_font(self, tab_bar):
        font = tab_bar.font()
        if font.pointSizeF() > 0:
            return
        base = self.font()
        base_size = base.pointSizeF()
        if base_size <= 0:
            base_size = 10.0
        font.setPointSizeF(base_size)
        tab_bar.setFont(font)

    def _create_mini_row(self, w1, w2):
        h = QHBoxLayout()
        h.addWidget(w1); h.addWidget(w2)
        return h

    def _make_filter_chip(self, label, icon_name=None):
        btn = QToolButton()
        btn.setText(label)
        btn.setCheckable(True)
        btn.setAutoRaise(True)
        if icon_name:
            btn.setIcon(Icons.get_icon(icon_name, self.icon_color))
            btn.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        else:
            btn.setToolButtonStyle(Qt.ToolButtonTextOnly)
        btn.setStyleSheet(
            "QToolButton { border: 1px solid #bdc3c7; border-radius: 10px; padding: 2px 8px; }"
            "QToolButton:checked { background-color: #3498db; color: white; border-color: #2980b9; }"
        )
        btn.toggled.connect(self.refresh_paths)
        return btn

    def _render_saved_filter_buttons(self):
        while self.saved_filter_layout.count():
            item = self.saved_filter_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        self._preset_button_map.clear()
        for preset in self.saved_filter_presets:
            btn = QToolButton()
            btn.setText(preset["name"])
            btn.setCheckable(True)
            btn.clicked.connect(lambda checked, p=preset: self._apply_saved_filter(p))
            btn.setContextMenuPolicy(Qt.CustomContextMenu)
            btn.customContextMenuRequested.connect(
                lambda pos, b=btn, p=preset: self._show_filter_context_menu(b, p, pos)
            )
            self.saved_filter_layout.addWidget(btn)
            self._preset_button_map[btn] = preset
        self.saved_filter_layout.addStretch()
        self._update_preset_button_states()

    def _update_preset_button_states(self):
        for btn, preset in self._preset_button_map.items():
            btn.setChecked(self.active_filter_preset is not None and preset == self.active_filter_preset)

    def _apply_saved_filter(self, preset):
        self.active_filter_preset = preset
        self.filter_type.blockSignals(True)
        self.filter_status.blockSignals(True)
        self.filter_tags.blockSignals(True)
        target_type = preset.get("type") or "All Types"
        target_status = preset.get("status") or "All Statuses"
        self.filter_type.setCurrentText(target_type)
        self.filter_status.setCurrentText(target_status)
        tags_text = ", ".join(preset.get("tags", []))
        self.filter_tags.setText(tags_text)
        self.filter_type.blockSignals(False)
        self.filter_status.blockSignals(False)
        self.filter_tags.blockSignals(False)
        self._update_preset_button_states()
        self.refresh_paths()

    def _clear_filter_preset(self):
        self.active_filter_preset = None
        self.filter_type.blockSignals(True)
        self.filter_status.blockSignals(True)
        self.filter_tags.blockSignals(True)
        self.filter_type.setCurrentIndex(0)
        self.filter_status.setCurrentIndex(0)
        self.filter_tags.clear()
        self.filter_type.blockSignals(False)
        self.filter_status.blockSignals(False)
        self.filter_tags.blockSignals(False)
        self._update_preset_button_states()
        self.refresh_paths()

    def _save_current_filter_preset(self):
        name, ok = QInputDialog.getText(self, "Save Filter Preset", "Preset name:")
        if not ok or not name.strip():
            return
        preset = {
            "name": name.strip(),
            "type": self.filter_type.currentText() if self.filter_type.currentText() != "All Types" else "",
            "status": self.filter_status.currentText() if self.filter_status.currentText() != "All Statuses" else "",
            "tags": self._normalize_tags(self.filter_tags.text()),
        }
        existing = next((p for p in self.saved_filter_presets if p["name"].lower() == preset["name"].lower()), None)
        if existing:
            existing.update(preset)
            preset = existing
        else:
            self.saved_filter_presets.append(preset)
        self._save_filter_presets()
        self._render_saved_filter_buttons()

    def _show_filter_context_menu(self, button, preset, pos):
        menu = QMenu()
        act_delete = menu.addAction("Remove view")
        action = menu.exec(button.mapToGlobal(pos))
        if action == act_delete:
            self.saved_filter_presets = [p for p in self.saved_filter_presets if p != preset]
            if self.active_filter_preset == preset:
                self.active_filter_preset = None
            self._save_filter_presets()
            self._render_saved_filter_buttons()

    def _save_filter_presets(self):
        self.logic.settings["project_filter_presets"] = self.saved_filter_presets
        self.logic.save_settings()

    def _meta_badge_style(self):
        theme = self.logic.settings.get("theme", "Light")
        if theme in Styles.DARK_THEME_NAMES:
            return "background-color: rgba(255, 255, 255, 0.08); color: #E5E7EB; border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: 600;"
        return "background-color: rgba(15, 118, 110, 0.12); color: #0F766E; border-radius: 8px; padding: 2px 6px; font-size: 10px; font-weight: 600;"

    def _is_recent(self, meta):
        last = meta.get("last_accessed", "")
        if not last:
            return False
        try:
            last_dt = datetime.strptime(last, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            return False
        return datetime.now() - last_dt <= timedelta(days=RECENT_DAYS)

    def _normalize_tags(self, value):
        if isinstance(value, (list, tuple)):
            return [str(t).strip().lower() for t in value if str(t).strip()]
        if isinstance(value, str):
            return [t.strip().lower() for t in value.split(",") if t.strip()]
        return []

    def _add_section_header(self, title):
        item = QListWidgetItem(title)
        item.setFlags(Qt.ItemIsEnabled)
        font = item.font()
        font.setBold(True)
        item.setFont(font)
        item.setForeground(Qt.gray)
        self.list_paths.addItem(item)

    def _add_project_item(self, p, data):
        meta = data["metadata"]
        type_map = {
            "PCB": "PCBA",
            "Mechanical": "MECH",
            "Software": "SOFT",
            "Firmware": "FIRM",
            "Other": "MISC"
        }

        ptype = meta.get("type", "Other")
        code = type_map.get(ptype, "MISC")
        num = meta.get("number", "")
        rev = meta.get("revision", "")
        name = meta.get("name", p)
        status = meta.get("status", "Pre-Design")

        label_text = name

        item = QListWidgetItem()
        item.setData(Qt.UserRole, p)
        self.list_paths.addItem(item)

        wid = QWidget()
        wid.setAttribute(Qt.WA_TransparentForMouseEvents)
        h = QHBoxLayout(wid)
        h.setContentsMargins(6, 4, 6, 4)
        h.setSpacing(8)

        # Type icon
        type_icon = self._icon_for_project_type(ptype)
        type_color = self._color_for_project_type(ptype)
        lbl_type = QLabel()
        lbl_type.setPixmap(Icons.get_icon(type_icon, type_color).pixmap(20, 20))
        lbl_type.setStyleSheet("background-color: transparent;")
        h.addWidget(lbl_type)

        # Name + meta row
        text_col = QVBoxLayout()
        text_col.setSpacing(2)
        lbl_name = QLabel(label_text)
        lbl_name.setStyleSheet("background-color: transparent; font-weight: 600;")
        text_col.addWidget(lbl_name)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(6)
        is_recent = self._is_recent(meta)
        is_archived = status == "Archived"
        is_pinned = meta.get("pinned", False)
        loc = meta.get("location", "")
        resolved_loc = self.logic.resolve_path(loc) if hasattr(self.logic, "resolve_path") else loc
        has_git = False
        if resolved_loc and os.path.isdir(resolved_loc):
            has_git = os.path.isdir(os.path.join(resolved_loc, ".git"))

        if is_pinned:
            meta_row.addWidget(self._make_icon_label(Icons.PIN, self.icon_color, "Pinned"))
        if is_recent:
            meta_row.addWidget(self._make_icon_label(Icons.CLOCK, self.icon_color, "Recent"))
        if is_archived:
            meta_row.addWidget(self._make_icon_label(Icons.ARCHIVE, self.icon_color, "Archived"))
        if resolved_loc:
            meta_row.addWidget(self._make_icon_label(Icons.FOLDER, self.icon_color, "Location set"))
        if has_git:
            meta_row.addWidget(self._make_icon_label(Icons.GIT, self.icon_color, "Git repo"))

        id_text = f"{code}{num}{rev}".strip()
        meta_parts = []
        if id_text:
            meta_parts.append(id_text)
        if ptype:
            meta_parts.append(ptype)
        if meta.get("last_accessed"):
            meta_parts.append(f"Last: {meta.get('last_accessed', '').split(' ')[0]}")
        meta_text = " | ".join(meta_parts)
        meta_label = QLabel(meta_text)
        meta_label.setObjectName("projectMetaBadge")
        meta_label.setStyleSheet(self._meta_badge_style())
        meta_row.addWidget(meta_label)
        meta_row.addStretch()
        text_col.addLayout(meta_row)

        h.addLayout(text_col)
        h.addStretch()

        status_colors = {
            "Pre-Design": "#7f8c8d",
            "Schematic Capture": "#3498db",
            "PCB Layout": "#9b59b6",
            "Prototyping": "#e67e22",
            "Validation": "#1abc9c",
            "Released": "#2ecc71",
            "Abandoned": "#c0392b",
            "Archived": "#34495e",
        }

        col = status_colors.get(status, "#7f8c8d")
        lbl_status = QLabel(status)
        lbl_status.setStyleSheet(
            f"background-color: {col}; color: white; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;"
        )
        lbl_status.setAlignment(Qt.AlignCenter)
        h.addWidget(lbl_status)

        item.setSizeHint(wid.sizeHint())
        self.list_paths.setItemWidget(item, wid)
        return item

    def _make_icon_label(self, icon_name, color, tooltip="", size=12):
        lbl = QLabel()
        lbl.setPixmap(Icons.get_icon(icon_name, color).pixmap(size, size))
        lbl.setStyleSheet("background-color: transparent;")
        if tooltip:
            lbl.setToolTip(tooltip)
        return lbl

    def _icon_for_project_type(self, ptype):
        mapping = {
            "PCB": Icons.CHIP,
            "PCBA": Icons.PCBA,
            "Firmware": Icons.CODE,
            "Software": Icons.CODE,
            "Mechanical": Icons.MECHANICAL,
            "Other": Icons.PROJECTS,
        }
        return mapping.get(ptype, Icons.PROJECTS)

    def _color_for_project_type(self, ptype):
        colors = {
            "PCB": "#2980b9",
            "PCBA": "#2980b9",
            "Firmware": "#8e44ad",
            "Software": "#16a085",
            "Mechanical": "#d35400",
            "Other": "#7f8c8d",
        }
        return colors.get(ptype, self.icon_color)

    def setup_kanban_ui(self, parent):
        """Sets up the layout and widgets for the Kanban board."""
        main_v = QVBoxLayout(parent)
        
        # Controls Row
        ctrl_h = QHBoxLayout()
        # Overall Progress Bar
        self.proj_progress = QProgressBar()
        style_progress_bar(
            self.proj_progress,
            accent="#0F766E",
            theme="Dark" if self.is_dark_theme else "Light",
            min_height=18,
            max_height=22,
        )
        self.proj_progress.setFormat("Project Completion: %p%")
        ctrl_h.addWidget(self.proj_progress)

        chk_compact = QCheckBox("Compact View")
        chk_compact.toggled.connect(self.toggle_kanban_compact)
        ctrl_h.addWidget(chk_compact)

        btn_limits = QPushButton("WIP Limits")
        btn_limits.clicked.connect(self.open_wip_limits)
        ctrl_h.addWidget(btn_limits)

        main_v.addLayout(ctrl_h)
        
        # Horizontal layout for columns
        layout = QHBoxLayout() 
        layout.setSpacing(16)
        layout.setContentsMargins(0, 10, 0, 0)
        main_v.addLayout(layout)
        
        # Create Kanban columns (To Do, In Progress, Done)
        for key, title in [("todo", "To Do"), ("prog", "In Progress"), ("done", "Done")]:
            self.kanban_titles[key] = title
            
            # Column Container (The "Lane")
            col_frame = QFrame()
            col_frame.setObjectName("kanbanColumn")
            col_frame.setProperty("kanbanKey", key)
            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(8, 12, 8, 8)
            col_layout.setSpacing(8)
            
            # Header
            lbl = QLabel(f"{title.upper()}")
            lbl.setObjectName("kanbanHeader")
            lbl.setProperty("kanbanKey", key)
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.kanban_labels[key] = lbl
            col_layout.addWidget(lbl)
            
            # Custom KanbanList widget for drag-and-drop tasks
            list_w = KanbanList(key, self)
            list_w.setObjectName("kanbanList")
            self.columns[key] = list_w
            list_w.setContextMenuPolicy(Qt.CustomContextMenu)
            list_w.customContextMenuRequested.connect(lambda pos, k=key: self.show_kanban_menu(pos, k))
            col_layout.addWidget(list_w)
            
            # Button to add new tasks to this column
            if key == "done":
                btn_clear = QPushButton("Clear All")
                btn_clear.clicked.connect(self.clear_done_tasks)
                col_layout.addWidget(btn_clear)
            else:
                btn = QPushButton(f"Add Task")
                btn.setIcon(Icons.get_icon(Icons.PLUS, self.icon_color))
                btn.setObjectName("kanbanAddBtn")
                btn.setCursor(Qt.PointingHandCursor)
                btn.clicked.connect(lambda checked=False, k=key: self.add_task(k))
                col_layout.addWidget(btn)
            
            layout.addWidget(col_frame)

    # --- Context Management ---

    def on_project_switch(self):
        """Updates all sub-tabs to display data for the newly selected project."""
        item = self.list_paths.currentItem()
        if not item:
            return
            
        name = item.data(Qt.UserRole)
        if not name:
            return

        data = self.logic.get_project_data(name)
        metadata = data.get("metadata") or {}
        loc = metadata.get("location") or ""
        p_type = metadata.get("type", "Standard")
        
        # Update Status View
        if hasattr(self.status_view, 'load_data'):
            self.status_view.load_data(metadata)
        elif hasattr(self.status_view, 'load_metadata'):
            self.status_view.load_metadata(metadata)
            
        # Update Details View
        if hasattr(self.details_view, 'load_data'):
            self.details_view.load_data(name, data)
            
        # Update Requirements
        if hasattr(self.req_view, 'load_data'):
            self.req_view.load_data(data.get("requirements", []))

        # Update Tasks tab (task definitions only, no hours)
        if hasattr(self, "tasks_view") and hasattr(self.tasks_view, "load_data"):
            self.tasks_view.load_data(name, data)
        
        # Update Documents
        if hasattr(self.docs_view, 'load_data'):
            self.docs_view.load_data(name, data)
        if hasattr(self, "test_plan_view") and hasattr(self.test_plan_view, "load_data"):
            self.test_plan_view.load_data(name, data)

        # Update Stats
        if hasattr(self.stats_view, 'load_data'):
            self.stats_view.load_data(name, data)

        # Update Project Git Tab Context
        if hasattr(self, "project_git_view") and loc:
            self.project_git_view.set_repo_path(loc)

        # Update Fabrication
        if hasattr(self.fab_view, 'load_data'):
            self.fab_view.load_data(name, data)

        # Update BOM Tab Context
        if hasattr(self.bom_tab, 'set_current_project'):
            self.bom_tab.set_current_project(name)
            self.bom_tab.generate()
        
        # Update Pricing Tab Context
        if hasattr(self.pricing_tab, 'set_current_project'):
            self.pricing_tab.set_current_project(name)

        # Update Kanban View
        for key, list_w in self.columns.items():
            list_w.clear()
            kanban_col = data.get("kanban", {}).get(key, [])
            for t in kanban_col:
                it = QListWidgetItem(t["name"])
                it.setData(Qt.UserRole, t["desc"])
                it.setData(Qt.UserRole + 1, t.get("progress", 0)) # Progress
                it.setData(Qt.UserRole + 2, t.get("category", "")) # Category
                it.setData(Qt.UserRole + 3, t.get("priority", "Normal")) # Priority
                list_w.addItem(it)
                
                # Create and set the interactive widget
                try:
                    widget = KanbanTaskWidget(it, self.logic, list_w, p_type)
                except Exception as exc:
                    logging.exception("KanbanTaskWidget failed, falling back to simple placeholder.")
                    widget = QLabel(it.text())
                    widget.setStyleSheet("background: #e5e7eb; border-radius: 10px; padding: 8px; color: #111827;")
                widget.set_compact(self.is_compact_kanban)
                it.setSizeHint(widget.sizeHint())
                list_w.setItemWidget(it, widget)

        # Update Kanban column counts and overall project progress
        self.update_kanban_counts()
        self.calculate_weighted_progress(data.get("kanban", {}))
        
        # Update Checklist tab
        self.checklist_view.load_data(data.get("checklist", {}))
        kanban_snapshot = data.get("kanban", {})
        checklist_snapshot = data.get("checklist", {})
        # Update Last Accessed
        if "project_registry" in self.logic.settings and name in self.logic.settings["project_registry"]:
            self.logic.settings["project_registry"][name]["metadata"]["last_accessed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logic.save_settings()
        
        # Emit signal to update Git Control tab with the project's repository path
        # This decouples GitTab from ProjectManagerTab.
        self.project_selected.emit(loc)

    def refresh_paths(self):
        """Reloads the project names from settings."""
        # Refresh filter options in case settings changed
        current_types = ["All Types"] + self.logic.settings.get("project_types", [])
        existing_items = [self.filter_type.itemText(i) for i in range(self.filter_type.count())]
        # Only update if the list of project types has actually changed
        if current_types != existing_items:
             curr = self.filter_type.currentText()
             self.filter_type.blockSignals(True)
             self.filter_type.clear()
             self.filter_type.addItems(current_types)
             self.filter_type.setCurrentText(curr)
             # If the current text is no longer valid, reset to "All Types"
             if self.filter_type.currentIndex() == -1:
                 self.filter_type.setCurrentIndex(0)
             self.filter_type.blockSignals(False)

        # Save current selection to restore it after refresh
        curr_item = self.list_paths.currentItem()
        curr_key = curr_item.data(Qt.UserRole) if curr_item else None

        self.list_paths.clear()
        # Get the raw list of project names from settings
        raw_projs = self.logic.settings.get("projects", [])
        
        # 1. Get all project data and store it with the project name for easier processing
        all_project_data = []
        for p_name in raw_projs:
            data = self.logic.get_project_data(p_name)
            all_project_data.append((p_name, data)) # Store (name, data) tuple

        # --- 2. Filtering ---
        query = self.search_proj.text().lower()
        type_filter = self.filter_type.currentText()
        status_filter = self.filter_status.currentText()
        tags_filter = self._normalize_tags(self.filter_tags.text())
        
        filtered_project_data = []
        for p_name, data in all_project_data:
            meta = data["metadata"]
            
            # Apply search filter
            if query:
                if not (query in p_name.lower() or 
                        query in meta.get("description", "").lower() or 
                        query in meta.get("status", "").lower()):
                    continue # Skip if search query doesn't match
            
            # Apply status filter
            if status_filter != "All Statuses":
                if meta.get("status", "") != status_filter:
                    continue

            # Apply type filter
            if type_filter != "All Types":
                if meta.get("type", "") != type_filter:
                    continue # Skip if type doesn't match

            if tags_filter:
                project_tags = self._normalize_tags(meta.get("tags", []))
                if not all(tag in project_tags for tag in tags_filter):
                    continue
            
            filtered_project_data.append((p_name, data))

        # --- 3. Sorting ---
        def get_sort_key(item_tuple):
            p_name, data = item_tuple
            meta = data["metadata"]
            
            # Primary sort: Pinned status (True comes before False)
            pinned = meta.get("pinned", False)
            
            # Secondary sort: User-selected option
            secondary_key = ""
            if self.sort_proj.currentText() == "Sort by Type":
                secondary_key = meta.get("type", "")
            elif self.sort_proj.currentText() == "Sort by Number":
                secondary_key = meta.get("number", "")
                if not secondary_key: secondary_key = "zzzz" # Put empty at end
            else: # Default: Sort by Name
                secondary_key = p_name.lower() # Case-insensitive name sort

            return (not pinned, secondary_key) # `not pinned` makes True (pinned) sort first

        filtered_project_data.sort(key=get_sort_key)

        # --- 4. Grouping into Sections ---
        pinned = []
        recent = []
        archived = []
        others = []

        filter_pinned = self.chip_pinned.isChecked()
        filter_recent = self.chip_recent.isChecked()
        filter_archived = self.chip_archived.isChecked()
        any_chip = filter_pinned or filter_recent or filter_archived

        seen = set()
        for p, data in filtered_project_data:
            meta = data["metadata"]
            is_pinned = meta.get("pinned", False)
            is_archived = meta.get("status") == "Archived"
            is_recent = self._is_recent(meta)

            if any_chip:
                if filter_pinned and is_pinned and p not in seen:
                    pinned.append((p, data))
                    seen.add(p)
                    continue
                if filter_recent and is_recent and p not in seen:
                    recent.append((p, data))
                    seen.add(p)
                    continue
                if filter_archived and is_archived and p not in seen:
                    archived.append((p, data))
                    seen.add(p)
                continue

            if is_pinned:
                pinned.append((p, data))
            elif is_archived:
                archived.append((p, data))
            elif is_recent:
                recent.append((p, data))
            else:
                others.append((p, data))

        sections = [
            ("Pinned", pinned),
            ("Recent", recent),
            ("Projects", others),
            ("Archived", archived),
        ]

        for title, items in sections:
            if not items:
                continue
            self._add_section_header(title)
            for p, data in items:
                item = self._add_project_item(p, data)
                if p == curr_key:
                    self.list_paths.setCurrentItem(item)

        # Auto-select first project to populate the UI
        if self.list_paths.count() > 0 and not self.list_paths.currentItem():
            for i in range(self.list_paths.count()):
                item = self.list_paths.item(i)
                if item.data(Qt.UserRole):
                    self.list_paths.setCurrentItem(item)
                    break

    def show_project_menu(self, pos):
        item = self.list_paths.itemAt(pos)
        if not item: return
        name = item.data(Qt.UserRole)
        
        menu = QMenu()
        # Check if pinned
        data = self.logic.get_project_data(name)
        is_pinned = data["metadata"].get("pinned", False)
        
        # Pin/Unpin
        act_pin = menu.addAction("Unpin Project" if is_pinned else "Pin Project")
        menu.addSeparator()
        
        # Quick Actions
        act_open = menu.addAction("Open Folder")
        menu.addSeparator()
        act_clone = menu.addAction("Clone Project")
        
        action = menu.exec(self.list_paths.mapToGlobal(pos))
        
        if action == act_pin:
            self.logic.toggle_pin(name)
            self.refresh_paths()
        elif action == act_open: self.open_project_folder()
        elif action == act_clone: self.clone_project()

    def clean_project_files(self):
        item = self.list_paths.currentItem()
        if not item: return
        name = item.data(Qt.UserRole)
        if QMessageBox.question(self, "Confirm Clean", f"Delete temporary files (backups, cache) for '{name}'?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            count = self.logic.clean_project(name)
            QMessageBox.information(self, "Cleaned", f"Removed {count} temporary files.")

    def add_project(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("New Project")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()
        
        edit_name = QLineEdit()
        edit_num = QLineEdit()
        edit_rev = QLineEdit("A")
        combo_type = QComboBox()
        combo_type.addItems(self.logic.settings.get("project_types", ["PCB", "Firmware", "Mechanical", "Other"]))
        
        form.addRow("Project Name:", edit_name)
        form.addRow("Project Number:", edit_num)
        form.addRow("Revision:", edit_rev)
        form.addRow("Type:", combo_type)
        
        layout.addLayout(form)
        
        footer = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_ok = QPushButton("Create Project")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        footer.addWidget(btn_cancel)
        footer.addStretch()
        footer.addWidget(btn_ok)
        layout.addLayout(footer)

        try:
            apply_modal_style(dlg, title="New Project", accent="#2F6BFF")
        except Exception:
            logging.exception("Failed to style 'New Project' dialog; falling back to native frame.")

        if dlg.exec():
            name = edit_name.text().strip()
            if not name:
                QMessageBox.warning(self, "Error", "Project name is required.")
                return

            p_list = self.logic.settings.setdefault("projects", [])
            if name not in p_list:
                p_list.append(name)
                data = self.logic.get_project_data(name) # Initialize registry entry
                
                # Update metadata with new fields
                data["metadata"]["number"] = edit_num.text().strip()
                data["metadata"]["revision"] = edit_rev.text().strip()
                data["metadata"]["type"] = combo_type.currentText()
                self._apply_project_templates(name, combo_type.currentText())
                
                self.logic.save_settings()
                self.refresh_paths()
            else:
                QMessageBox.warning(self, "Error", f"Project '{name}' already exists.")

    def _apply_project_templates(self, name, project_type):
        data = self.logic.get_project_data(name)
        templates = self.logic.settings.get("kanban_templates", {})
        raw_tasks = templates.get(project_type, templates.get("Standard", []))
        if raw_tasks:
            data["kanban"] = columns_from_templates(raw_tasks)

        # Checklist templates
        checklist_templates = self.logic.settings.get("checklist_templates", {})
        if not data.get("checklist"):
            template = checklist_templates.get(project_type, checklist_templates.get("Standard", {}))
            if template:
                import copy
                data["checklist"] = copy.deepcopy(template)

    def rem_project(self):
        item = self.list_paths.currentItem()
        if not item: return
        
        name = item.data(Qt.UserRole)
        if QMessageBox.question(self, "Confirm", f"Remove '{name}' from project list?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if name in self.logic.settings["projects"]:
                self.logic.settings["projects"].remove(name)
                self.logic.save_settings()
                self.refresh_paths()

    def open_project_folder(self):
        item = self.list_paths.currentItem()
        if not item: return
        name = item.data(Qt.UserRole)
        data = self.logic.get_project_data(name)
        loc = data["metadata"].get("location", "")
        if loc:
            QDesktopServices.openUrl(QUrl.fromLocalFile(loc))
            
    def clone_project(self):
        item = self.list_paths.currentItem()
        if not item: return
        src = item.data(Qt.UserRole)
        new_name, ok = QInputDialog.getText(self, "Clone Project", f"Clone '{src}' to:")
        if ok and new_name:
            if self.logic.clone_project(src, new_name):
                self.refresh_paths()
                QMessageBox.information(self, "Success", f"Project cloned to '{new_name}'")

    def archive_project(self):
        item = self.list_paths.currentItem()
        if not item: return
        self.logic.archive_project(item.data(Qt.UserRole))
        self.on_project_switch() # Refresh UI
        self.refresh_paths()
        QMessageBox.information(self, "Archived", "Project status set to Archived.")

    def get_current_project_type(self):
        item = self.list_paths.currentItem()
        if not item: return "Standard"
        name = item.data(Qt.UserRole) or item.text()
        return self.logic.get_project_data(name)["metadata"].get("type", "Standard")

    def get_kanban_limits(self):
        item = self.list_paths.currentItem()
        if not item:
            return dict(KANBAN_DEFAULT_LIMITS)
        name = item.data(Qt.UserRole)
        if not name:
            return dict(KANBAN_DEFAULT_LIMITS)
        data = self.logic.get_project_data(name)
        limits = data.get("kanban_limits", {})
        merged = dict(KANBAN_DEFAULT_LIMITS)
        merged.update(limits)
        return merged

    def set_kanban_limits(self, limits):
        item = self.list_paths.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole)
        if not name:
            return
        data = self.logic.get_project_data(name)
        data["kanban_limits"] = dict(limits)
        self.logic.save_settings()
        self.update_kanban_counts()

    def can_add_task_to_column(self, key, count=1):
        limits = self.get_kanban_limits()
        limit = limits.get(key, 0)
        if limit <= 0:
            return True
        return (self.columns[key].count() + count) <= limit

    def open_wip_limits(self):
        limits = self.get_kanban_limits()
        dlg = QDialog(self)
        dlg.setWindowTitle("Kanban WIP Limits")
        layout = QVBoxLayout(dlg)
        form = QFormLayout()

        spins = {}
        for key, title in [("todo", "To Do"), ("prog", "In Progress"), ("done", "Done")]:
            spin = QSpinBox()
            spin.setRange(0, 999)
            spin.setValue(int(limits.get(key, 0)))
            spin.setToolTip("0 = Unlimited")
            spins[key] = spin
            form.addRow(f"{title} limit:", spin)

        layout.addLayout(form)
        footer = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_ok = QPushButton("Save Limits")
        btn_cancel.clicked.connect(dlg.reject)
        btn_ok.clicked.connect(dlg.accept)
        footer.addWidget(btn_cancel)
        footer.addStretch()
        footer.addWidget(btn_ok)
        layout.addLayout(footer)

        apply_modal_style(dlg, title="Kanban WIP Limits", accent="#16A34A")

        if dlg.exec():
            new_limits = {k: int(spin.value()) for k, spin in spins.items()}
            self.set_kanban_limits(new_limits)

    # --- Kanban Operations ---

    def refresh_kanban_column(self, list_w, tasks):
        """Internal helper to populate a list widget with task objects."""
        list_w.clear()
        for t in tasks:
            name = t.get("name", "New Task")
            desc = t.get("desc", "")
            prog = t.get("progress", 0)
            
            item = QListWidgetItem(name)
            item.setData(Qt.UserRole, desc)        # Index for description
            item.setData(Qt.UserRole + 1, prog)   # Index for progress bar
            list_w.addItem(item)

    def add_task(self, key):
        """Opens dialog to add task and syncs to registry."""
        if not self.list_paths.currentItem():
            QMessageBox.warning(self, "Selection Required", "Please select a project first.")
            return
        if not self.can_add_task_to_column(key, count=1):
            QMessageBox.warning(self, "WIP Limit", f"'{self.kanban_titles.get(key, key)}' is at its WIP limit.")
            return

        # Create a new blank task
        item = QListWidgetItem("New Task")
        item.setData(Qt.UserRole, "") # Description
        item.setData(Qt.UserRole + 1, 0) # Progress
        item.setData(Qt.UserRole + 2, self.last_kanban_category) # Category (Default to last used)
        item.setData(Qt.UserRole + 3, "Normal") # Priority
        
        list_w = self.columns[key]
        list_w.addItem(item)
        
        # Create widget
        widget = KanbanTaskWidget(item, self.logic, list_w, self.get_current_project_type())
        item.setSizeHint(widget.sizeHint())
        list_w.setItemWidget(item, widget)
        
        # Persist
        self.sync_kanban_from_ui()

    def show_kanban_menu(self, pos, key):
        list_w = self.columns[key]
        item = list_w.itemAt(pos)
        from PySide6.QtWidgets import QMenu
        menu = QMenu()

        if item:
            act_move_todo = menu.addAction("Move to To Do")
            act_move_prog = menu.addAction("Move to In Progress")
            act_move_done = menu.addAction("Move to Done")
            menu.addSeparator()
            act_del = menu.addAction(Icons.get_icon(Icons.TRASH, self.icon_color), "Delete Task")
            action = menu.exec(list_w.mapToGlobal(pos))
            if action == act_move_todo:
                self.move_task_to(item, key, "todo")
            elif action == act_move_prog:
                self.move_task_to(item, key, "prog")
            elif action == act_move_done:
                self.move_task_to(item, key, "done")
            elif action == act_del:
                self.delete_task(key, item)
        else:
            menu.exec(list_w.mapToGlobal(pos))

    def delete_task(self, key, item):
        self.columns[key].takeItem(self.columns[key].row(item))
        self.sync_kanban_from_ui()

    def move_task_to(self, item, source_key, target_key):
        if source_key == target_key:
            return
        if not self.can_add_task_to_column(target_key, count=1):
            QMessageBox.warning(self, "WIP Limit", f"'{self.kanban_titles.get(target_key, target_key)}' is at its WIP limit.")
            return
        src = self.columns.get(source_key)
        tgt = self.columns.get(target_key)
        if not src or not tgt:
            return
        src.takeItem(src.row(item))
        tgt.addItem(item)
        widget = KanbanTaskWidget(item, self.logic, tgt, self.get_current_project_type())
        item.setSizeHint(widget.sizeHint())
        tgt.setItemWidget(item, widget)
        self.sync_kanban_from_ui()

    def clear_done_tasks(self):
        if QMessageBox.question(self, "Confirm", "Clear all tasks in 'Done' column?", QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            self.columns["done"].clear()
            self.sync_kanban_from_ui()

    def sync_kanban_from_ui(self):
        """Scrapes the UI state of the Kanban columns and saves it to the Registry."""
        item = self.list_paths.currentItem()
        if not item:
            return
        name = item.data(Qt.UserRole) or item.text()
        
        new_kanban = {}
        for key, list_widget in self.columns.items():
            new_kanban[key] = []
            for i in range(list_widget.count()):
                it = list_widget.item(i)
                # Retrieve all data from the QListWidgetItem
                # Auto-update progress based on column
                prog = it.data(Qt.UserRole + 1)
                if key == "todo": prog = 0 # Tasks moved to ToDo reset progress
                elif key == "done": prog = 100
                it.setData(Qt.UserRole + 1, prog) # Update UI item

                new_kanban[key].append({
                    "name": it.text(),
                    "desc": it.data(Qt.UserRole),
                    "progress": prog,
                    "category": it.data(Qt.UserRole + 2),
                    "priority": it.data(Qt.UserRole + 3)
                })
        
        # Save the updated Kanban data into the project's registry entry
        if "project_registry" in self.logic.settings and name in self.logic.settings["project_registry"]:
            self.logic.settings["project_registry"][name]["kanban"] = new_kanban
            self.logic.save_settings()
        
        # Update visual indicators
        self.update_kanban_counts()
        self.calculate_weighted_progress(new_kanban)

    def update_kanban_counts(self):
        """Updates the task count displayed in each Kanban column header."""
        limits = self.get_kanban_limits()
        for key, list_w in self.columns.items():
            count = list_w.count()
            title = self.kanban_titles.get(key, "").upper()
            limit = limits.get(key, 0)
            if key in self.kanban_labels:
                if limit > 0:
                    self.kanban_labels[key].setText(f"{title} ({count}/{limit})")
                else:
                    self.kanban_labels[key].setText(f"{title} ({count})")

    def highlight_kanban_task(self, task_name):
        self.sub_tabs.setCurrentWidget(self.tab_kanban)
        for list_w in self.columns.values():
            # Find item
            items = list_w.findItems(task_name, Qt.MatchExactly)
            if items:
                list_w.setCurrentItem(items[0])
                list_w.scrollToItem(items[0])
                return

    def toggle_kanban_compact(self, checked):
        self.is_compact_kanban = checked
        for list_w in self.columns.values():
            for i in range(list_w.count()):
                item = list_w.item(i)
                widget = list_w.itemWidget(item)
                if widget:
                    widget.set_compact(checked)
                    item.setSizeHint(widget.sizeHint())

    def calculate_weighted_progress(self, kanban_data):
        """
        Calculates the overall project completion percentage based on Kanban tasks,
        applying weights based on task priority.
        """
        total_weight = 0
        weighted_sum = 0
        prio_weights = self.logic.settings.get(
            "kanban_priority_weights",
            {"Critical": 5, "High": 3, "Normal": 1, "Low": 0.5},
        )
        
        for col in kanban_data.values():
            for task in col:
                prio = task.get("priority", "Normal")
                w = prio_weights.get(prio, 1)
                prog = task.get("progress", 0)
                total_weight += w
                weighted_sum += (prog * w)
        
        final = int(weighted_sum / total_weight) if total_weight > 0 else 0
        self.proj_progress.setValue(final)

    def sync_checklist_from_ui(self):
        """Retrieves checklist data from the UI and saves it to the project's registry."""
        item = self.list_paths.currentItem()
        if not item: return
        name = item.data(Qt.UserRole) or item.text()
        
        data = self.checklist_view.get_data()
        if "project_registry" in self.logic.settings and name in self.logic.settings["project_registry"]:
            self.logic.settings["project_registry"][name]["checklist"] = data
            self.logic.save_settings()

    def save_project_metadata(self):
        """Aggregates data from Status and Details views and saves it to the project's registry."""
        item = self.list_paths.currentItem()
        if not item:
            return
        
        name = item.data(Qt.UserRole) or item.text()
        meta = {}
        
        if hasattr(self.status_view, 'get_data'):
            meta.update(self.status_view.get_data())
            
        if hasattr(self.details_view, 'get_data'):
            meta.update(self.details_view.get_data())
            
        # Save requirements data if the view exists
        if hasattr(self.req_view, 'get_data'):
            self.logic.settings["project_registry"][name]["requirements"] = self.req_view.get_data()

        # Update the project's metadata in the registry
        if "project_registry" in self.logic.settings and name in self.logic.settings["project_registry"]:
            current_meta = self.logic.settings["project_registry"][name]["metadata"]
            current_meta.update(meta)
            self.logic.save_settings()
            QMessageBox.information(self, "Success", "Project metadata saved.")
            self.refresh_paths()

    def closeEvent(self, event):
        """Propagates close event to sub-tabs to ensure proper cleanup of threads/workers."""
        for i in range(self.sub_tabs.count()):
            w = self.sub_tabs.widget(i)
            if hasattr(w, 'closeEvent'):
                w.closeEvent(event)
        super().closeEvent(event)
