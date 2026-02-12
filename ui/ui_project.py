from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QFrame,
                             QPushButton, QFileDialog, QGroupBox, QTabWidget,
                             QListWidgetItem, QMessageBox, QLabel, QInputDialog, QLineEdit, QComboBox, QProgressBar, QMenu, QToolButton, QCheckBox,
                             QDialog, QFormLayout)
from PySide6.QtCore import Qt, Signal, QUrl
from PySide6.QtGui import QDesktopServices

try:
    from .kanban_widgets import KanbanList, KanbanTaskWidget
    from .project_status_view import ProjectStatusView 
    from .project_details_view import ProjectDetailsView
    from .checklist_widget import ChecklistWidget
    from .requirements_view import RequirementsView
    from .ui_bom import BOMTab
    from .ui_pricing import PricingTab
    from .project_docs_view import ProjectDocsView
    from .project_stats_view import ProjectStatsView
    from .fabrication_view import FabricationView
except ImportError:
    from kanban_widgets import KanbanList, KanbanTaskWidget
    from project_status_view import ProjectStatusView 
    from project_details_view import ProjectDetailsView
    from checklist_widget import ChecklistWidget
    from requirements_view import RequirementsView
    from ui_bom import BOMTab
    from ui_pricing import PricingTab
    from project_docs_view import ProjectDocsView
    from project_stats_view import ProjectStatsView
    from fabrication_view import FabricationView
try:
    from .icons import Icons
except ImportError:
    from ui.icons import Icons

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
        self.setup_ui()

    def setup_ui(self):
        """Sets up the main layout and widgets for the Project Manager tab."""
        main_layout = QHBoxLayout(self)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        self.icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        # 1. Projects Sidebar/Selector (Moved to Left)
        top_panel = QGroupBox("Projects")
        top_panel.setFixedWidth(350)
        top_layout = QVBoxLayout(top_panel)
        
        # Search & Sort
        # Search input field
        self.search_proj = QLineEdit()
        self.search_proj.setPlaceholderText("Search Projects...")
        self.search_proj.textChanged.connect(self.refresh_paths)
        top_layout.addWidget(self.search_proj)

        # Filter by Project Type dropdown
        self.filter_type = QComboBox()
        self.filter_type.addItem("All Types")
        self.filter_type.addItems(self.logic.settings.get("project_types", []))
        self.filter_type.currentIndexChanged.connect(self.refresh_paths)
        top_layout.addWidget(self.filter_type)

        # Sort Projects dropdown
        self.sort_proj = QComboBox()
        self.sort_proj.addItems(["Sort by Name", "Sort by Type", "Sort by Number"])
        self.sort_proj.currentIndexChanged.connect(self.refresh_paths)
        top_layout.addWidget(self.sort_proj)

        # List of Projects
        self.list_paths = QListWidget()
        # Connect item selection to the project switching handler
        self.list_paths.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_paths.customContextMenuRequested.connect(self.show_project_menu)
        self.list_paths.itemSelectionChanged.connect(self.on_project_switch)
        top_layout.addWidget(self.list_paths)
        
        # Buttons for adding/removing projects
        btns = QVBoxLayout()
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

        btns.addWidget(btn_add)
        btns.addWidget(btn_rem)
        btns.addWidget(btn_actions)
        btns.addWidget(btn_open)
        top_layout.addLayout(btns)
        
        main_layout.addWidget(top_panel)

        # 2. Sub-Tabs for Project Details (Right Panel)
        self.sub_tabs = QTabWidget()
        self.sub_tabs.setMovable(True) # Allow users to reorder sub-tabs
        
        # --- Kanban Board Tab ---
        # This tab displays tasks organized in ToDo, In Progress, Done columns.
        self.tab_kanban = QWidget()
        self.setup_kanban_ui(self.tab_kanban)
        self.sub_tabs.addTab(self.tab_kanban, "Kanban")

        # Sub-Tab New: Requirements
        self.req_view = RequirementsView(self.logic)
        self.sub_tabs.addTab(self.req_view, "Requirements")

        # --- Project Status & Metadata Tab ---
        # Displays general project information like name, number, status, location.
        self.status_view = ProjectStatusView(self.logic)
        # Connect status view save button to the registry save logic
        # This ensures changes in the status view are persisted.
        if hasattr(self.status_view, 'btn_save'):
            self.status_view.btn_save.clicked.connect(self.save_project_metadata)
            
        self.sub_tabs.addTab(self.status_view, "Configuration")

        # Sub-Tab New: Project Details
        self.details_view = ProjectDetailsView(self.logic)
        if hasattr(self.details_view, 'btn_save'):
            self.details_view.btn_save.clicked.connect(self.save_project_metadata)
        self.sub_tabs.addTab(self.details_view, "Details")

        # Sub-Tab C: Checklist
        self.checklist_view = ChecklistWidget(self)
        self.sub_tabs.addTab(self.checklist_view, "Checklist")

        # Sub-Tab New: Documents
        self.docs_view = ProjectDocsView(self.logic)
        self.sub_tabs.addTab(self.docs_view, "Documents")

        # Sub-Tab New: Stats
        self.stats_view = ProjectStatsView(self.logic)
        self.sub_tabs.addTab(self.stats_view, "Statistics")

        # Sub-Tab New: Fabrication
        self.fab_view = FabricationView(self.logic)
        self.sub_tabs.addTab(self.fab_view, "Fabrication")

        # Sub-Tab D: BOM
        self.bom_tab = BOMTab(self.logic)
        self.sub_tabs.addTab(self.bom_tab, "Bill of Materials")
        
        # --- Pricing & Stock Tab ---
        # Fetches and displays pricing and availability for BOM items.
        # Sub-Tab E: Pricing
        self.pricing_tab = PricingTab(self.logic)
        self.sub_tabs.addTab(self.pricing_tab, "Pricing & Stock")

        main_layout.addWidget(self.sub_tabs, stretch=1)

        # 3. Final Initialization
        self.refresh_paths()

    def _create_mini_row(self, w1, w2):
        h = QHBoxLayout()
        h.addWidget(w1); h.addWidget(w2)
        return h

    def setup_kanban_ui(self, parent):
        """Sets up the layout and widgets for the Kanban board."""
        main_v = QVBoxLayout(parent)
        
        # Controls Row
        ctrl_h = QHBoxLayout()
        # Overall Progress Bar
        self.proj_progress = QProgressBar()
        self.proj_progress.setFormat("Project Completion: %p%")
        self.proj_progress.setStyleSheet("QProgressBar::chunk { background-color: #27ae60; }")
        ctrl_h.addWidget(self.proj_progress)
        
        chk_compact = QCheckBox("Compact View")
        chk_compact.toggled.connect(self.toggle_kanban_compact)
        ctrl_h.addWidget(chk_compact)
        
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
            col_layout = QVBoxLayout(col_frame)
            col_layout.setContentsMargins(8, 12, 8, 8)
            col_layout.setSpacing(8)
            
            # Header
            lbl = QLabel(f"{title.upper()}")
            lbl.setObjectName("kanbanHeader")
            lbl.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            self.kanban_labels[key] = lbl
            col_layout.addWidget(lbl)
            
            # Custom KanbanList widget for drag-and-drop tasks
            list_w = KanbanList(key, self)
            self.columns[key] = list_w
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
            
        # Fix: Use UserRole to get the real project ID, fallback to text if missing
        name = item.data(Qt.UserRole) or item.text()
        # Retrieve the isolated data from the registry (AppLogic)
        data = self.logic.get_project_data(name)
        p_type = data["metadata"].get("type", "Standard")
        
        # Update Status View
        if hasattr(self.status_view, 'load_data'):
            self.status_view.load_data(data["metadata"])
        elif hasattr(self.status_view, 'load_metadata'):
            self.status_view.load_metadata(data["metadata"])
            
        # Update Details View
        if hasattr(self.details_view, 'load_data'):
            self.details_view.load_data(name, data)
            
        # Update Requirements
        if hasattr(self.req_view, 'load_data'):
            self.req_view.load_data(data.get("requirements", []))
        
        # Update Documents
        if hasattr(self.docs_view, 'load_data'):
            self.docs_view.load_data(name, data)

        # Update Stats
        if hasattr(self.stats_view, 'load_data'):
            self.stats_view.load_data(name, data)

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
            kanban_col = data["kanban"].get(key, [])
            for t in kanban_col:
                it = QListWidgetItem(t["name"])
                it.setData(Qt.UserRole, t["desc"])
                it.setData(Qt.UserRole + 1, t.get("progress", 0)) # Progress
                it.setData(Qt.UserRole + 2, t.get("category", "")) # Category
                it.setData(Qt.UserRole + 3, t.get("priority", "Normal")) # Priority
                list_w.addItem(it)
                
                # Create and set the interactive widget
                widget = KanbanTaskWidget(it, self.logic, list_w, p_type)
                widget.set_compact(self.is_compact_kanban)
                it.setSizeHint(widget.sizeHint())
                list_w.setItemWidget(it, widget)

        # Update Kanban column counts and overall project progress
        self.update_kanban_counts()
        self.calculate_weighted_progress(data["kanban"])
        
        # Update Checklist tab
        self.checklist_view.load_data(data.get("checklist", {}))
        
        # Update Last Accessed
        if "project_registry" in self.logic.settings and name in self.logic.settings["project_registry"]:
            self.logic.settings["project_registry"][name]["metadata"]["last_accessed"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.logic.save_settings()
        
        # Emit signal to update Git Control tab with the project's repository path
        # This decouples GitTab from ProjectManagerTab.
        loc = data["metadata"].get("location", "")
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
        
        filtered_project_data = []
        for p_name, data in all_project_data:
            meta = data["metadata"]
            
            # Apply search filter
            if query:
                if not (query in p_name.lower() or 
                        query in meta.get("description", "").lower() or 
                        query in meta.get("status", "").lower()):
                    continue # Skip if search query doesn't match
            
            # Apply type filter
            if type_filter != "All Types":
                if meta.get("type", "") != type_filter:
                    continue # Skip if type doesn't match
            
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

        for p, data in filtered_project_data:
            # Display Project Number if available
            meta = data["metadata"]
            
            ptype = meta.get("type", "Other")
            code = type_map.get(ptype, "MISC")
            num = meta.get("number", "")
            rev = meta.get("revision", "")
            name = meta.get("name", p)
            status = meta.get("status", "Pre-Design")
            
            label_text = f"{code}{num}{rev} - {name}"
            
            item = QListWidgetItem()
            item.setData(Qt.UserRole, p) # Store the real project key
            self.list_paths.addItem(item)
            
            # Custom Widget for Item
            wid = QWidget()
            wid.setAttribute(Qt.WA_TransparentForMouseEvents) # Pass clicks to list item
            h = QHBoxLayout(wid)
            h.setContentsMargins(5, 2, 5, 2)
            h.setSpacing(10)
            
            if meta.get("pinned"):
                lbl_pin = QLabel()
                lbl_pin.setPixmap(Icons.get_icon(Icons.PIN, self.icon_color).pixmap(16, 16))
                lbl_pin.setStyleSheet("background-color: transparent;")
                h.addWidget(lbl_pin)

            lbl_name = QLabel(label_text)
            lbl_name.setStyleSheet("background-color: transparent;")
            h.addWidget(lbl_name)
            
            h.addStretch()
            
            col = status_colors.get(status, "#7f8c8d")
            lbl_status = QLabel(status)
            lbl_status.setStyleSheet(f"background-color: {col}; color: white; border-radius: 4px; padding: 2px 6px; font-size: 10px; font-weight: bold;")
            lbl_status.setAlignment(Qt.AlignCenter)
            h.addWidget(lbl_status)
            
            item.setSizeHint(wid.sizeHint())
            self.list_paths.setItemWidget(item, wid)
            
            if p == curr_key:
                self.list_paths.setCurrentItem(item)
        
        # Auto-select first project to populate the UI
        if self.list_paths.count() > 0 and not self.list_paths.currentItem():
            self.list_paths.setCurrentRow(0)

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
                
                self.logic.save_settings()
                self.refresh_paths()
            else:
                QMessageBox.warning(self, "Error", f"Project '{name}' already exists.")

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
        QMessageBox.information(self, "Archived", "Project status set to Archived.")

    def get_current_project_type(self):
        item = self.list_paths.currentItem()
        if not item: return "Standard"
        name = item.data(Qt.UserRole) or item.text()
        return self.logic.get_project_data(name)["metadata"].get("type", "Standard")

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
        if not item: return

        from PySide6.QtWidgets import QMenu
        menu = QMenu()
        act_del = menu.addAction(Icons.get_icon(Icons.TRASH, self.icon_color), "Delete Task")
        action = menu.exec(list_w.mapToGlobal(pos))
        
        if action == act_del:
            self.delete_task(key, item)

    def delete_task(self, key, item):
        self.columns[key].takeItem(self.columns[key].row(item))
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
        for key, list_w in self.columns.items():
            count = list_w.count()
            title = self.kanban_titles.get(key, "").upper()
            if key in self.kanban_labels:
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
        prio_weights = {"Critical": 5, "High": 3, "Normal": 1, "Low": 0.5}
        
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
