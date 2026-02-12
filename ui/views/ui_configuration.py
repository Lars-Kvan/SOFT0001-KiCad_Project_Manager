from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QSplitter, 
                             QGroupBox, QListWidget, QLineEdit, QPushButton, 
                             QLabel, QRadioButton, QButtonGroup, QTreeWidget, 
                             QTreeWidgetItem, QHeaderView, QFrame, QComboBox, QAbstractItemView,
                             QListWidgetItem)
from PySide6.QtCore import Qt, QTimer
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons

class RulesConfigTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()
        self.refresh_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        # --- Top Header / Toolbar ---
        header = QHBoxLayout()
        title = QLabel("Rule Manager")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        header.addWidget(title)
        
        header.addStretch()
        
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #27ae60; font-weight: bold;")
        header.addWidget(self.lbl_status)

        self.btn_reload = QPushButton("Reload Rules")
        self.btn_reload.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        self.btn_reload.setFixedWidth(120)
        # FIX: Changed from self.load_rules_ui to self.refresh_ui
        self.btn_reload.clicked.connect(self.load_rules_ui) 
        header.addWidget(self.btn_reload)
        main_layout.addLayout(header)

        # --- Horizontal Divider ---
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Main Content
        content_container = QWidget()
        top_layout = QHBoxLayout(content_container)
        top_layout.setContentsMargins(0, 5, 0, 5)

        # 1. Global Rules
        group_g = QGroupBox("Global Property Rules (Regex Validation)")
        layout_g = QVBoxLayout(group_g)
        
        input_g = QHBoxLayout()
        self.g_name = QLineEdit()
        self.g_name.setPlaceholderText("Property (e.g. MPN)")
        self.g_regex = QLineEdit()
        self.g_regex.setPlaceholderText("Regex Pattern")
        btn_add_g = QPushButton("+")
        btn_add_g.setFixedWidth(40)
        btn_add_g.clicked.connect(self.add_global_rule)
        
        input_g.addWidget(self.g_name)
        input_g.addWidget(self.g_regex)
        input_g.addWidget(btn_add_g)
        layout_g.addLayout(input_g)

        self.list_global = QListWidget()
        layout_g.addWidget(self.list_global)
        
        self.btn_del_g = QPushButton("Remove Global Rule")
        self.btn_del_g.setIcon(Icons.get_icon(Icons.TRASH, icon_color))
        self.btn_del_g.clicked.connect(self.del_global_rule)
        layout_g.addWidget(self.btn_del_g)
        top_layout.addWidget(group_g)

        # 2. Specific Library Rules
        group_l = QGroupBox("Per-Library Required Properties")
        # Use a horizontal layout to split Libraries (Left) and Rules (Right)
        layout_l = QHBoxLayout(group_l)
        
        # LEFT: Library Selector
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Select Library:"))
        
        self.lib_search = QLineEdit()
        self.lib_search.setPlaceholderText("🔍 Filter Libraries...")
        self.lib_search.textChanged.connect(self.update_lib_list)
        left_layout.addWidget(self.lib_search)
        
        self.list_libs = QListWidget()
        self.list_libs.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.list_libs.itemSelectionChanged.connect(self.on_select_lib)
        left_layout.addWidget(self.list_libs)
        layout_l.addWidget(left_container, stretch=1)
        
        # RIGHT: Rules for Selected Library
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("Required Properties:"))

        input_l = QHBoxLayout()
        self.l_name = QLineEdit()
        self.l_name.setPlaceholderText("New Property Name")
        btn_add_l = QPushButton("+")
        btn_add_l.setFixedWidth(40)
        btn_add_l.clicked.connect(self.add_lib_rule)
        input_l.addWidget(self.l_name)
        input_l.addWidget(btn_add_l)
        right_layout.addLayout(input_l)

        self.list_lib_rules = QListWidget()
        right_layout.addWidget(self.list_lib_rules)
        
        self.btn_del_l = QPushButton("Remove Library Rule")
        self.btn_del_l.setIcon(Icons.get_icon(Icons.TRASH, icon_color))
        self.btn_del_l.clicked.connect(self.del_lib_rule)
        right_layout.addWidget(self.btn_del_l)
        
        layout_l.addWidget(right_container, stretch=1)
        top_layout.addWidget(group_l)

        main_layout.addWidget(content_container)

        # Connections
        self.list_global.itemSelectionChanged.connect(self.update_btn)
        self.list_lib_rules.itemSelectionChanged.connect(self.update_btn)
        self.update_btn()

    def update_btn(self):
        self.btn_del_g.setEnabled(self.list_global.currentItem() is not None)
        self.btn_del_l.setEnabled(self.list_lib_rules.currentItem() is not None)

    def refresh_ui(self):
        self.list_global.clear()
        for r, rx in self.logic.global_rules.items():
            display = f"{r} → {rx}" if rx else r
            self.list_global.addItem(display)
        self.update_lib_list()

    def update_lib_list(self):
        query = self.lib_search.text().lower()
        self.list_libs.clear()
        if hasattr(self.logic, 'data_store') and self.logic.data_store:
            libs = sorted(self.logic.data_store.keys())
            for lib in libs:
                if query in lib.lower():
                    count = len(self.logic.library_rules.get(lib, {}))
                    item = QListWidgetItem(self.list_libs)
                    item.setText(lib)
                    self._set_lib_widget(item, lib, count)

    def _set_lib_widget(self, item, lib, count):
        wid = QWidget()
        wid.setAttribute(Qt.WA_TransparentForMouseEvents)
        h = QHBoxLayout(wid)
        h.setContentsMargins(5, 2, 5, 2)
        
        lbl_name = QLabel(lib)
        lbl_name.setStyleSheet("background-color: transparent;")
        h.addWidget(lbl_name)
        h.addStretch()
        
        if count > 0:
            lbl_count = QLabel(str(count))
            lbl_count.setStyleSheet("background-color: #3498db; color: white; border-radius: 10px; padding: 2px 6px; font-weight: bold; min-width: 14px;")
            lbl_count.setAlignment(Qt.AlignCenter)
            h.addWidget(lbl_count)
            
        item.setSizeHint(wid.sizeHint())
        self.list_libs.setItemWidget(item, wid)

    def on_select_lib(self):
        libs = self.get_sel_libs()
        self.list_lib_rules.clear()
        if not libs: return
        
        # Find intersection of rules across all selected libraries
        common_rules = None
        for lib in libs:
            rules = set(self.logic.library_rules.get(lib, {}).keys())
            if common_rules is None:
                common_rules = rules
            else:
                common_rules &= rules
        
        if common_rules:
            for r in sorted(list(common_rules)):
                self.list_lib_rules.addItem(r)

    def get_sel_libs(self):
        return [item.text() for item in self.list_libs.selectedItems()]

    def trigger_save(self):
        self.logic.save_rules()
        self.lbl_status.setText("✓ Rules Saved")
        QTimer.singleShot(2000, lambda: self.lbl_status.setText(""))

    def add_global_rule(self):
        name, regex = self.g_name.text().strip(), self.g_regex.text().strip()
        if name:
            self.logic.global_rules[name] = regex
            self.g_name.clear(); self.g_regex.clear()
            self.refresh_ui(); self.trigger_save()

    def del_global_rule(self):
        item = self.list_global.currentItem()
        if item:
            key = item.text().split(" → ")[0]
            if key in self.logic.global_rules: 
                del self.logic.global_rules[key]
                self.refresh_ui(); self.trigger_save()

    def add_lib_rule(self):
        libs = self.get_sel_libs()
        name = self.l_name.text().strip()
        if libs and name:
            for lib in libs:
                if lib not in self.logic.library_rules: self.logic.library_rules[lib] = {}
                self.logic.library_rules[lib][name] = ""
                self.update_lib_count(lib)
            self.l_name.clear()
            
            # Update UI directly to preserve selection
            self.on_select_lib()
            self.trigger_save()

    def del_lib_rule(self):
        libs = self.get_sel_libs()
        item = self.list_lib_rules.currentItem()
        if libs and item:
            rule_name = item.text()
            for lib in libs:
                if rule_name in self.logic.library_rules.get(lib, {}):
                    del self.logic.library_rules[lib][rule_name]
                    self.update_lib_count(lib)
            
            self.list_lib_rules.takeItem(self.list_lib_rules.row(item))
            self.trigger_save()

    def update_lib_count(self, lib_name):
        # Updates the [count] text in the library list without losing selection
        items = self.list_libs.findItems(lib_name, Qt.MatchExactly)
        for item in items:
            count = len(self.logic.library_rules.get(lib_name, {}))
            self._set_lib_widget(item, lib_name, count)

    def load_rules_ui(self):
        self.logic.load_rules()
        self.refresh_ui()

class ExemptionsConfigTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()
        self.refresh_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)

        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        header = QHBoxLayout()
        title = QLabel("Exemption Manager")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #333;")
        header.addWidget(title)
        header.addStretch()
        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #27ae60; font-weight: bold;")
        header.addWidget(self.lbl_status)

        self.btn_reload = QPushButton("Reload Rules")
        self.btn_reload.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        self.btn_reload.setFixedWidth(120)
        self.btn_reload.clicked.connect(self.load_rules_ui)
        header.addWidget(self.btn_reload)
        main_layout.addLayout(header)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        bottom_container = QWidget()
        bottom_layout = QHBoxLayout(bottom_container)
        bottom_layout.setContentsMargins(0, 5, 0, 5)

        # 3. Scope Selection
        group_s = QGroupBox("Target Selection (Scope)")
        layout_s = QVBoxLayout(group_s)
        
        self.lib_search = QLineEdit()
        self.lib_search.setPlaceholderText("🔍 Filter Libraries...")
        self.lib_search.textChanged.connect(self.update_lib_list)
        layout_s.addWidget(self.lib_search)

        scope_h = QHBoxLayout()
        self.list_libs = QListWidget()
        self.list_libs.itemSelectionChanged.connect(self.on_select_lib)
        
        self.list_parts = QListWidget()
        self.list_parts.itemSelectionChanged.connect(self.on_part_select)
        
        scope_h.addWidget(self.list_libs)
        scope_h.addWidget(self.list_parts)
        layout_s.addLayout(scope_h)
        bottom_layout.addWidget(group_s)

        # 4. Exemptions Management
        group_ex = QGroupBox("Exemption Logic")
        layout_ex = QVBoxLayout(group_ex)
        
        layout_ex.addWidget(QLabel("Select Rule to Exempt:"))
        self.rule_combo = QComboBox()
        self.rule_combo.currentIndexChanged.connect(self.update_btn)
        layout_ex.addWidget(self.rule_combo)
        
        radio_box = QHBoxLayout()
        self.rb_lib = QRadioButton("Exempt Entire Library")
        self.rb_part = QRadioButton("Exempt Specific Part")
        self.rb_lib.setChecked(True)
        radio_box.addWidget(self.rb_lib)
        radio_box.addWidget(self.rb_part)
        layout_ex.addLayout(radio_box)
        
        self.btn_ex = QPushButton("Add Exemption")
        self.btn_ex.setFixedHeight(40)
        self.btn_ex.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        self.btn_ex.clicked.connect(self.add_exemption)
        layout_ex.addWidget(self.btn_ex)

        self.tree_ex = QTreeWidget()
        self.tree_ex.setHeaderLabels(["Scope", "Target", "Rule"])
        self.tree_ex.setAlternatingRowColors(True)
        self.tree_ex.header().setSectionResizeMode(QHeaderView.Stretch)
        layout_ex.addWidget(self.tree_ex)
        
        btn_del_ex = QPushButton("Delete Selected Exemption")
        btn_del_ex.setIcon(Icons.get_icon(Icons.TRASH, icon_color))
        btn_del_ex.clicked.connect(self.del_exemption)
        layout_ex.addWidget(btn_del_ex)
        bottom_layout.addWidget(group_ex)
        main_layout.addWidget(bottom_container)

    def refresh_ui(self):
        self.update_lib_list()
        self.update_exemptions()
        self.update_rule_combo()

    def update_rule_combo(self):
        self.rule_combo.clear()
        for r in self.logic.global_rules.keys():
            self.rule_combo.addItem(f"Global: {r}")
        lib = self.get_sel_lib()
        if lib and lib in self.logic.library_rules:
            for r in self.logic.library_rules[lib].keys():
                self.rule_combo.addItem(f"Lib: {r}")

    def update_lib_list(self):
        query = self.lib_search.text().lower()
        self.list_libs.clear()
        # FIX: Iterate keys() because data_store is a dict, not a list
        if hasattr(self.logic, 'data_store') and self.logic.data_store:
            libs = sorted(self.logic.data_store.keys())
            for lib in libs:
                if query in lib.lower():
                    count = len(self.logic.library_rules.get(lib, {}))
                    self.list_libs.addItem(f"{lib} [{count}]")

    def on_select_lib(self):
        lib = self.get_sel_lib()
        if not lib: return
        self.list_lib_rules.clear()
        for r in self.logic.library_rules.get(lib, {}).keys():
            self.list_lib_rules.addItem(r)
        self.list_parts.clear()
        
        # FIX: Access dict keys directly
        if lib in self.logic.data_store:
            parts = sorted(self.logic.data_store[lib].keys())
            self.list_parts.addItems(parts)
        
        self.update_btn()

    def get_sel_lib(self):
        item = self.list_libs.currentItem()
        return item.text().split(" [")[0] if item else None

    def get_sel_part(self):
        item = self.list_parts.currentItem()
        return item.text() if item else None

    def on_part_select(self):
        if self.list_parts.currentItem():
            self.rb_part.setChecked(True)
        self.update_btn()

    def update_btn(self):
        lib = self.get_sel_lib()
        part = self.get_sel_part()
        rule = self.rule_combo.currentText()

        if not lib or not rule:
            self.btn_ex.setEnabled(False)
            self.btn_ex.setText("Select Scope and Rule")
            return
        self.btn_ex.setEnabled(True)
        target = part if (self.rb_part.isChecked() and part) else lib
        self.btn_ex.setText(f"Exempt {target} from '{rule}'")

    def trigger_save(self):
        self.logic.save_rules()
        self.lbl_status.setText("✓ Exemptions Saved")
        QTimer.singleShot(2000, lambda: self.lbl_status.setText(""))

    def add_exemption(self):
        lib, part = self.get_sel_lib(), self.get_sel_part()
        rule_text = self.rule_combo.currentText()
        if not lib or not rule_text: return
        
        # Extract rule name from "Global: Rule" or "Lib: Rule"
        rule = rule_text.split(": ", 1)[1] if ": " in rule_text else rule_text

        if self.rb_part.isChecked() and part:
            uid = f"{lib}:{part}"
            self.logic.exemptions['parts'].setdefault(uid, [])
            if rule not in self.logic.exemptions['parts'][uid]: self.logic.exemptions['parts'][uid].append(rule)
        else:
            self.logic.exemptions['libraries'].setdefault(lib, [])
            if rule not in self.logic.exemptions['libraries'][lib]: self.logic.exemptions['libraries'][lib].append(rule)
        self.update_exemptions(); self.trigger_save()

    def update_exemptions(self):
        self.tree_ex.clear()
        for lib, rules in self.logic.exemptions.get('libraries', {}).items():
            for r in rules: QTreeWidgetItem(self.tree_ex, ["Library", lib, r])
        for uid, rules in self.logic.exemptions.get('parts', {}).items():
            for r in rules: QTreeWidgetItem(self.tree_ex, ["Part", uid, r])

    def del_exemption(self):
        item = self.tree_ex.currentItem()
        if not item: return
        scope, target, rule = item.text(0), item.text(1), item.text(2)
        key = 'libraries' if scope == "Library" else 'parts'
        if rule in self.logic.exemptions[key].get(target, []):
            self.logic.exemptions[key][target].remove(rule)
            if not self.logic.exemptions[key][target]: del self.logic.exemptions[key][target]
            self.update_exemptions(); self.trigger_save()

    def load_rules_ui(self):
        self.logic.load_rules()
        self.refresh_ui()

    def del_global_rule(self):
        item = self.list_global.currentItem()
        if item:
            key = item.text().split(" → ")[0]
            if key in self.logic.global_rules: 
                del self.logic.global_rules[key]
                self.refresh_ui(); self.trigger_save()

    def del_lib_rule(self):
        lib, item = self.get_sel_lib(), self.list_lib_rules.currentItem()
        if lib and item:
            if item.text() in self.logic.library_rules.get(lib, {}):
                del self.logic.library_rules[lib][item.text()]
                self.refresh_ui(); self.trigger_save()

    def load_rules_ui(self):
        """Added missing method to fix AttributeError"""
        self.logic.load_rules()
        self.refresh_ui()
