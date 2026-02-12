from PySide6.QtWidgets import (QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QHeaderView, QProgressBar, QMenu, QInputDialog, 
                             QHBoxLayout, QPushButton, QMessageBox, QFileDialog, QTreeWidgetItemIterator, QLabel, QFrame)
from PySide6.QtCore import Qt, QSignalBlocker, QDateTime
from PySide6.QtGui import QAction, QColor, QFont
try:
    from .icons import Icons
    from .widgets.progress_utils import style_progress_bar
except ImportError:
    from ui.icons import Icons
    from ui.widgets.progress_utils import style_progress_bar

class ChecklistWidget(QWidget):
    def __init__(self, parent_tab, is_template=False):
        super().__init__()
        self.parent_tab = parent_tab
        self.is_template = is_template
        self.fallback_steps = [
            "Schematic: Electrical Rules Check (ERC)",
            "Schematic: Netlist Verification",
            "Schematic: Bill of Materials (BOM) Review",
            "Layout: Design Rules Check (DRC)",
            "Layout: Footprint Verification",
            "Layout: Component Placement Review",
            "Layout: Critical Routing / Impedance",
            "Layout: Silkscreen & Polarity Check",
            "Layout: 3D Model Fit Check",
            "Fabrication: Gerber Generation & Review",
            "Fabrication: Drill Files Generated",
            "Assembly: Pick & Place File Generated"
        ]
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(0, 0, 0, 0)

        theme = self.parent_tab.logic.settings.get("theme", "Light") if hasattr(self.parent_tab, 'logic') else "Light"
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        panel_bg = "#0F172A" if theme in ["Dark"] else "#F5F5F5"
        panel_border = "#1F2937" if theme in ["Dark"] else "#E5E7EB"

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        style_progress_bar(self.progress, accent="#10B981", theme=theme, min_height=14, max_height=18)
        self.progress.setFormat("%p% Verified")
        self.progress.setFixedHeight(18)
        if self.is_template:
            self.progress.setVisible(False)

        title_text = "Checklist Template" if self.is_template else "Checklist"

        header_frame = QFrame()
        header_frame.setObjectName("checklistHeader")
        header_frame.setStyleSheet(
            f"QFrame#checklistHeader {{ background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 14px; }}"
        )
        header_layout = QVBoxLayout(header_frame)
        header_layout.setContentsMargins(14, 14, 14, 14)
        header_layout.setSpacing(10)

        title_layout = QHBoxLayout()
        lbl_title = QLabel(title_text)
        lbl_title.setStyleSheet("font-size: 15pt; font-weight: 700;")
        title_layout.addWidget(lbl_title)
        title_layout.addStretch()
        header_layout.addLayout(title_layout)

        header_layout.addWidget(self.progress)

        action_row = QHBoxLayout()
        action_row.addStretch()
        btn_export = QPushButton("Export Report")
        btn_export.setIcon(Icons.get_icon(Icons.DOC, icon_color))
        btn_export.clicked.connect(self.export_report)
        action_row.addWidget(btn_export)
        if not self.is_template:
            btn_load = QPushButton("Load Template")
            btn_load.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
            btn_load.clicked.connect(self.open_template_dialog)
            action_row.addWidget(btn_load)
        header_layout.addLayout(action_row)

        layout.addWidget(header_frame)

        category_frame = QFrame()
        category_frame.setStyleSheet(
            f"QFrame {{ background-color: {panel_bg}; border-radius: 12px; border: 1px solid {panel_border}; }}"
        )
        category_layout = QHBoxLayout(category_frame)
        category_layout.setContentsMargins(12, 8, 12, 8)
        category_layout.setSpacing(10)
        category_layout.addWidget(QLabel("New Category"))
        self.k_cat_name = QLineEdit()
        self.k_cat_name.setPlaceholderText("Category Name")
        category_layout.addWidget(self.k_cat_name, 1)
        self.btn_k_color = QPushButton("Pick Color")
        self.btn_k_color.setStyleSheet(f"background-color: #95a5a6; color: white; border-radius: 8px;")
        self.btn_k_color.setFixedHeight(32)
        self.btn_k_color.clicked.connect(self.pick_kanban_color)
        category_layout.addWidget(self.btn_k_color)
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self.add_category)
        category_layout.addWidget(btn_add)
        layout.addWidget(category_frame)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Verification Step / Rule", "Comment / Status"])
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_menu)
        self.tree.itemChanged.connect(self.on_item_changed)
        self.tree.itemDoubleClicked.connect(self.on_double_click)
        self.tree.setStyleSheet(f"""
            QTreeWidget {{
                background: transparent;
                border: none;
                font-size: 11pt;
            }}
            QTreeWidget::item {{
                padding: 10px 14px;
                border-radius: 10px;
                margin: 3px 0;
                background-color: rgba(255, 255, 255, 0.02);
            }}
            QTreeWidget::item:selected {{
                background-color: rgba(14, 165, 233, 0.15);
                border: 1px solid rgba(59, 130, 246, 0.45);
            }}
        """)

        tree_container = QFrame()
        tree_container.setStyleSheet(
            f"QFrame {{ background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 14px; }}"
        )
        tree_layout = QVBoxLayout(tree_container)
        tree_layout.setContentsMargins(10, 10, 10, 10)
        tree_layout.addWidget(self.tree)
        layout.addWidget(tree_container, 1)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_update_k = QPushButton("Update Color")
        btn_update_k.clicked.connect(self.update_kanban_cat_color)
        btn_row.addWidget(btn_update_k)
        btn_del_k = QPushButton("Remove Category")
        btn_del_k.clicked.connect(self.del_kanban_cat)
        btn_row.addWidget(btn_del_k)
        layout.addLayout(btn_row)

        if self.is_template:
            self.btn_k_color.setVisible(False)
            btn_add.setVisible(False)

        self.refresh_kanban_cats()

    def load_data(self, data):
        # Block signals to prevent save triggering during load
        with QSignalBlocker(self.tree):
            self.tree.clear()
            
            # If no data, load defaults
            if not data and not self.is_template:
                if hasattr(self.parent_tab, 'logic'):
                    templates = self.parent_tab.logic.settings.get("checklist_templates", {})
                    data = templates.get("Standard", {})
            
            if not data: # Fallback if settings empty or template is empty
                data = {step: [] for step in self.fallback_steps}
            
            font_root = QFont()
            font_root.setBold(True)
            font_root.setPointSize(11)

            for step, rules in data.items():
                root = QTreeWidgetItem(self.tree)
                root.setText(0, step)
                root.setFlags(root.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                root.setCheckState(0, Qt.Unchecked)
                root.setFont(0, font_root)
                
                # Migration: Handle old boolean format if present
                if isinstance(rules, bool): 
                    rules = []

                for r in rules:
                    child = QTreeWidgetItem(root)
                    child.setText(0, r.get("text", "Rule"))
                    child.setText(1, r.get("comment", ""))
                    child.setFlags(child.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                    child.setCheckState(0, Qt.Checked if r.get("checked") else Qt.Unchecked)
                
                root.setExpanded(True)
        
        self.update_progress()

    def get_data(self):
        data = {}
        for i in range(self.tree.topLevelItemCount()):
            root = self.tree.topLevelItem(i)
            step = root.text(0)
            rules = []
            for j in range(root.childCount()):
                child = root.child(j)
                rules.append({
                    "text": child.text(0),
                    "comment": child.text(1),
                    "checked": child.checkState(0) == Qt.Checked
                })
            data[step] = rules
        return data

    def on_item_changed(self, item, column):
        # Trigger save and progress update
        self.update_progress()
        self.parent_tab.sync_checklist_from_ui()

    def update_progress(self):
        total_rules = 0
        checked_rules = 0
        
        iterator = QTreeWidgetItemIterator(self.tree)
        while iterator.value():
            item = iterator.value()
            # Count only leaf nodes (rules)
            if item.parent():
                total_rules += 1
                if item.checkState(0) == Qt.Checked:
                    checked_rules += 1
            iterator += 1
        
        if total_rules > 0:
            val = int((checked_rules / total_rules) * 100)
        else:
            val = 0
        self.progress.setValue(val)
        
        # Color change based on progress
        theme = self.parent_tab.logic.settings.get("theme", "Light") if hasattr(self.parent_tab, 'logic') else "Light"
        style_progress_bar(self.progress, accent=("#2ecc71" if val == 100 else "#10B981"), theme=theme, min_height=14, max_height=18)

    def show_menu(self, pos):
        item = self.tree.itemAt(pos)
        
        # Determine icon color
        theme = self.parent_tab.logic.settings.get("theme", "Light") if hasattr(self.parent_tab, 'logic') else "Light"
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        
        menu = QMenu()
        
        if item:
            if not item.parent(): # Root / Category
                menu.addAction(Icons.get_icon(Icons.PLUS, icon_color), "Add Rule", lambda: self.add_rule(item))
                menu.addSeparator()
                menu.addAction(Icons.get_icon(Icons.EDIT, icon_color), "Rename Category", lambda: self.tree.editItem(item, 0))
                menu.addAction(Icons.get_icon(Icons.TRASH, icon_color), "Delete Category", lambda: self.delete_item(item))
            else: # Child / Rule
                menu.addAction(Icons.get_icon(Icons.EDIT, icon_color), "Edit Rule", lambda: self.tree.editItem(item, 0))
                menu.addAction(Icons.get_icon(Icons.EDIT, icon_color), "Edit Comment", lambda: self.tree.editItem(item, 1))
                menu.addAction(Icons.get_icon(Icons.TRASH, icon_color), "Delete Rule", lambda: self.delete_item(item))
        else:
            # Background click
            menu.addAction(Icons.get_icon(Icons.PLUS, icon_color), "Add New Category", self.add_category)
            menu.addSeparator()
            menu.addAction("Collapse All", self.tree.collapseAll)
            menu.addAction("Expand All", self.tree.expandAll)

        menu.exec(self.tree.viewport().mapToGlobal(pos))

    def add_category(self):
        text, ok = QInputDialog.getText(self, "New Category", "Category Name:")
        if ok and text:
            root = QTreeWidgetItem(self.tree)
            root.setText(0, text)
            root.setFlags(root.flags() | Qt.ItemIsAutoTristate | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            root.setCheckState(0, Qt.Unchecked)
            font = QFont(); font.setBold(True); font.setPointSize(11)
            root.setFont(0, font)
            self.parent_tab.sync_checklist_from_ui()

    def add_rule(self, root):
        text, ok = QInputDialog.getText(self, "New Rule", f"Add check for {root.text(0)}:")
        if ok and text:
            child = QTreeWidgetItem(root)
            child.setText(0, text)
            child.setFlags(child.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
            child.setCheckState(0, Qt.Unchecked)
            root.setExpanded(True)
            self.parent_tab.sync_checklist_from_ui()
            self.update_progress()

    def delete_item(self, item):
        if item.parent():
            item.parent().removeChild(item)
        else:
            # Remove top level
            index = self.tree.indexOfTopLevelItem(item)
            self.tree.takeTopLevelItem(index)
        self.parent_tab.sync_checklist_from_ui()
        self.update_progress()

    def on_double_click(self, item, column):
        self.tree.editItem(item, column)

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "Checklist_Report.txt", "Text Files (*.txt)")
        if path:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"PCB Checklist Report - {QDateTime.currentDateTime().toString()}\n")
                f.write("="*50 + "\n\n")
                
                for i in range(self.tree.topLevelItemCount()):
                    root = self.tree.topLevelItem(i)
                    f.write(f"[{'X' if root.checkState(0) == Qt.Checked else ' '}] {root.text(0)}\n")
                    for j in range(root.childCount()):
                        child = root.child(j)
                        status = "[x]" if child.checkState(0) == Qt.Checked else "[ ]"
                        comment = f" - Note: {child.text(1)}" if child.text(1) else ""
                        f.write(f"    {status} {child.text(0)}{comment}\n")
                    f.write("\n")
            QMessageBox.information(self, "Exported", "Checklist report saved.")

    def open_template_dialog(self):
        logic = getattr(self.parent_tab, 'logic', None)
        if not logic: return
        
        templates = logic.settings.get("checklist_templates", {})
        if not templates:
            QMessageBox.warning(self, "No Templates", "No templates defined in Settings.")
            return

        name, ok = QInputDialog.getItem(self, "Select Template", "Template:", list(templates.keys()), 0, False)
        if ok and name:
            data = templates[name]
            import copy
            self.load_data(copy.deepcopy(data))
            self.parent_tab.sync_checklist_from_ui()
