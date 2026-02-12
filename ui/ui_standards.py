import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                             QGroupBox, QListWidget, QLineEdit, QPushButton, 
                             QLabel, QTreeWidget, QTreeWidgetItem, QHeaderView, 
                             QMessageBox, QMenu, QTabWidget)
from PySide6.QtGui import QAction, QColor, QFont
from PySide6.QtCore import Qt
try:
    from .icons import Icons
except ImportError:
    from ui.icons import Icons

class StandardsTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()
        self.refresh_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        # --- Toolbar ---
        toolbar = QHBoxLayout()
        btn_save = QPushButton("Save Rules")
        btn_save.setIcon(Icons.get_icon(Icons.SAVE, icon_color))
        btn_save.clicked.connect(self.save_rules_ui)
        toolbar.addWidget(btn_save)

        btn_load = QPushButton("Load Rules")
        btn_load.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        btn_load.clicked.connect(self.load_rules_ui)
        toolbar.addWidget(btn_load)

        toolbar.addStretch()

        btn_val_sel = QPushButton("Validate Selected")
        btn_val_sel.clicked.connect(lambda: self.run_validation("selected"))
        toolbar.addWidget(btn_val_sel)

        btn_val_all = QPushButton("Run Global Validation")
        btn_val_all.setIcon(Icons.get_icon(Icons.PLAY, "white"))
        btn_val_all.setStyleSheet("font-weight: bold; background-color: #1565C0; color: white;")
        btn_val_all.clicked.connect(lambda: self.run_validation("all"))
        toolbar.addWidget(btn_val_all)
        
        layout.addLayout(toolbar)

        # --- Main Splitter ---
        self.main_splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(self.main_splitter)

        # 1. Global Parameters
        group_global = QGroupBox("1. Global Parameters")
        layout_g = QVBoxLayout(group_global)
        
        input_g = QHBoxLayout()
        self.global_input = QLineEdit()
        self.global_input.setPlaceholderText("Add global rule...")
        self.global_input.returnPressed.connect(self.add_global_rule)
        btn_add_g = QPushButton("+")
        btn_add_g.setFixedWidth(30)
        btn_add_g.clicked.connect(self.add_global_rule)
        input_g.addWidget(self.global_input)
        input_g.addWidget(btn_add_g)
        layout_g.addLayout(input_g)

        self.list_global = QListWidget()
        layout_g.addWidget(self.list_global)
        
        btn_del_g = QPushButton("Remove Selected")
        btn_del_g.clicked.connect(self.del_global_rule)
        layout_g.addWidget(btn_del_g)
        self.main_splitter.addWidget(group_global)

        # 2. Library Selection
        group_lib_sel = QGroupBox("2. Select Library")
        layout_lib = QVBoxLayout(group_lib_sel)
        self.list_libs = QListWidget()
        self.list_libs.itemSelectionChanged.connect(self.on_select_lib_rule)
        self.list_libs.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_libs.customContextMenuRequested.connect(self.show_lib_menu)
        layout_lib.addWidget(self.list_libs)
        self.main_splitter.addWidget(group_lib_sel)

        # 3. Library Parameters
        group_lib_rules = QGroupBox("3. Library Params")
        layout_l = QVBoxLayout(group_lib_rules)
        
        input_l = QHBoxLayout()
        self.lib_rule_input = QLineEdit()
        self.lib_rule_input.setPlaceholderText("Add lib rule...")
        self.lib_rule_input.returnPressed.connect(self.add_lib_rule)
        btn_add_l = QPushButton("+")
        btn_add_l.setFixedWidth(30)
        btn_add_l.clicked.connect(self.add_lib_rule)
        input_l.addWidget(self.lib_rule_input)
        input_l.addWidget(btn_add_l)
        layout_l.addLayout(input_l)

        self.list_lib_rules = QListWidget()
        layout_l.addWidget(self.list_lib_rules)
        
        btn_del_l = QPushButton("Remove Selected")
        btn_del_l.clicked.connect(self.del_lib_rule)
        layout_l.addWidget(btn_del_l)
        self.main_splitter.addWidget(group_lib_rules)

        # 4. Results / Failures
        group_res = QGroupBox("4. Validation Results")
        layout_res = QVBoxLayout(group_res)
        
        self.tree_valid = QTreeWidget()
        self.tree_valid.setHeaderLabels(["Library", "Symbol", "Issue Description"])
        self.tree_valid.header().setSectionResizeMode(QHeaderView.Interactive)
        self.tree_valid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_valid.customContextMenuRequested.connect(self.show_res_menu)
        layout_res.addWidget(self.tree_valid)
        self.main_splitter.addWidget(group_res)

        # Adjust initial widths
        self.main_splitter.setStretchFactor(3, 3) # Give Results the most space

    # --- Logic ---
    def refresh_ui(self):
        self.list_global.clear()
        for r in self.logic.global_rules:
            self.list_global.addItem(r)
        self.update_lib_list()

    def update_lib_list(self):
        self.list_libs.clear()
        libs = sorted(list(set(x['library'] for x in self.logic.data_store)))
        for lib in libs:
            item_text = lib
            if lib in self.logic.exempt_libs:
                item_text += " [EXEMPT]"
            self.list_libs.addItem(item_text)

    def add_global_rule(self):
        r = self.global_input.text().strip()
        if r and r not in self.logic.global_rules:
            self.logic.global_rules.append(r)
            self.refresh_ui()
            self.global_input.clear()

    def del_global_rule(self):
        item = self.list_global.currentItem()
        if item:
            self.logic.global_rules.remove(item.text())
            self.refresh_ui()

    def on_select_lib_rule(self):
        item = self.list_libs.currentItem()
        if not item: return
        lib = item.text().replace(" [EXEMPT]", "")
        self.list_lib_rules.clear()
        for r in self.logic.library_rules.get(lib, []):
            self.list_lib_rules.addItem(r)

    def add_lib_rule(self):
        item = self.list_libs.currentItem()
        r = self.lib_rule_input.text().strip()
        if not item or not r: return
        lib = item.text().replace(" [EXEMPT]", "")
        if lib not in self.logic.library_rules: self.logic.library_rules[lib] = []
        if r not in self.logic.library_rules[lib]:
            self.logic.library_rules[lib].append(r)
            self.list_lib_rules.addItem(r)
            self.lib_rule_input.clear()

    def del_lib_rule(self):
        sel_lib = self.list_libs.currentItem()
        sel_rule = self.list_lib_rules.currentItem()
        if not sel_lib or not sel_rule: return
        lib = sel_lib.text().replace(" [EXEMPT]", "")
        rule = sel_rule.text()
        if rule in self.logic.library_rules.get(lib, []):
            self.logic.library_rules[lib].remove(rule)
            self.list_lib_rules.takeItem(self.list_lib_rules.row(sel_rule))

    # --- Validation ---
    def run_validation(self, scope="all"):
        self.tree_valid.clear()
        target = None
        if scope == "selected":
            sel = self.list_libs.currentItem()
            if not sel:
                QMessageBox.warning(self, "Error", "Select a library first.")
                return
            target = sel.text().replace(" [EXEMPT]", "")
        
        failures = self.logic.validate(scope, target)
        for f in failures:
            QTreeWidgetItem(self.tree_valid, [str(f[0]), str(f[1]), str(f[2])])

        if not failures:
            QMessageBox.information(self, "Success", "No issues found.")
        else:
            self.statusBar_msg(f"Found {len(failures)} issues.")

    # --- Menus ---
    def show_lib_menu(self, pos):
        menu = QMenu()
        toggle_act = menu.addAction("Toggle Global Exemption")
        toggle_act.triggered.connect(self.toggle_lib_exemption)
        menu.exec_(self.list_libs.mapToGlobal(pos))

    def show_res_menu(self, pos):
        item = self.tree_valid.itemAt(pos)
        if not item: return
        menu = QMenu()
        exempt_part = menu.addAction("Exempt PART from Global Rules")
        exempt_lib = menu.addAction("Exempt LIBRARY from Global Rules")
        
        action = menu.exec_(self.tree_valid.mapToGlobal(pos))
        if action == exempt_part: self.exempt_selected_part(item)
        elif action == exempt_lib: self.exempt_selected_part_lib(item)

    def toggle_lib_exemption(self):
        item = self.list_libs.currentItem()
        if not item: return
        lib = item.text().replace(" [EXEMPT]", "")
        if lib in self.logic.exempt_libs: self.logic.exempt_libs.remove(lib)
        else: self.logic.exempt_libs.append(lib)
        self.update_lib_list()

    def exempt_selected_part(self, item):
        uid = f"{item.text(0)}:{item.text(1)}"
        if uid not in self.logic.exempt_parts:
            self.logic.exempt_parts.append(uid)
            QMessageBox.information(self, "Exempt", f"Exempted {uid}")

    def exempt_selected_part_lib(self, item):
        lib = item.text(0)
        if lib not in self.logic.exempt_libs:
            self.logic.exempt_libs.append(lib)
            self.update_lib_list()
            QMessageBox.information(self, "Exempt", f"Exempted Library {lib}")

    # --- Persistence ---
    def save_rules_ui(self):
        # Implementation using QFileDialog.getSaveFileName
        pass

    def load_rules_ui(self):
        # Implementation using QFileDialog.getOpenFileName
        pass

    def statusBar_msg(self, msg):
        # Helper to push messages to main window status bar
        window = self.window()
        if hasattr(window, 'statusBar'):
            window.statusBar().showMessage(msg, 5000)