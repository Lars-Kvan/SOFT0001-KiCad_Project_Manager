import re
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QGroupBox, QLabel, QPushButton, QComboBox, QLineEdit,
                             QSplitter, QTreeWidget, QTreeWidgetItem, QHeaderView,
                             QMenu, QMessageBox, QInputDialog, QFrame, QAbstractItemView)
from PySide6.QtGui import QColor, QAction
from PySide6.QtCore import Qt
from .ui_configuration import RulesConfigTab, ExemptionsConfigTab
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.elevation import apply_elevation

class ValidationTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.all_current_failures = []
        self.shadow_failures = []
        self.current_filter_lib = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        apply_layout(layout, margin=PAGE_PADDING, spacing="md")

        theme = self.logic.settings.get("theme", "Light")
        is_dark = theme in ["Dark"]
        muted = "#9CA3AF" if is_dark else "#6B7280"

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        self.tabs.setProperty("stretchTabs", True)
        self.tabs.tabBar().setExpanding(True)
        layout.addWidget(self.tabs)

        # --- SUB-TAB 1: Rule Manager ---
        self.tab_rules_config = RulesConfigTab(self.logic)
        self.tabs.addTab(self.tab_rules_config, "Manage Rules")

        # --- SUB-TAB 2: Exemption Manager ---
        self.tab_exempt_config = ExemptionsConfigTab(self.logic)
        self.tabs.addTab(self.tab_exempt_config, "Manage Exemptions")

        # --- SUB-TAB 2: Compliance Checking ---
        self.tab_rules = QWidget()
        self.setup_rules_ui(self.tab_rules)
        self.tabs.addTab(self.tab_rules, "Compliance Log")

        # --- SUB-TAB 3: Duplicate Finder ---
        self.tab_dupes = QWidget()
        self.setup_dupe_ui(self.tab_dupes)
        self.tabs.addTab(self.tab_dupes, "Duplicate MPN Finder")

        # --- SUB-TAB 4: Footprint Verification ---
        self.tab_fp_check = QWidget()
        self.setup_fp_check_ui(self.tab_fp_check)
        self.tabs.addTab(self.tab_fp_check, "Footprint Verification")

        # --- SUB-TAB 4: Exemption Review ---
        self.tab_exempt = QWidget()
        self.setup_exemption_ui(self.tab_exempt)
        self.tabs.addTab(self.tab_exempt, "Exemption Review")

    def setup_rules_ui(self, parent):
        """Builds the compliance checking dashboard."""
        main_layout = QVBoxLayout(parent)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(12)

        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        is_dark = theme in ["Dark"]
        card_bg = "#23262B" if is_dark else "#FFFFFF"
        card_border = "#2F353D" if is_dark else "#EDE6DC"
        muted = "#9CA3AF" if is_dark else "#6B7280"
        
        # Header: Metrics and Controls
        header_layout = QHBoxLayout()
        
        # Metrics Dashboard
        dash_card = QFrame()
        dash_card.setStyleSheet(f"background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px;")
        dash_layout = QHBoxLayout(dash_card)
        dash_layout.setContentsMargins(10, 8, 10, 10)
        dash_layout.setSpacing(10)
        apply_elevation(dash_card, theme)
        self.lbl_checked = self._create_metric(dash_layout, "Checked", "0", "#3498db") # Blue
        self.lbl_fails = self._create_metric(dash_layout, "Issues", "0", "#e74c3c")   # Red
        self.lbl_score = self._create_metric(dash_layout, "Compliance", "-%", "#2ecc71") # Green
        self.lbl_exempt = self._create_metric(dash_layout, "Exemptions", "0", "#9b59b6") # Purple
        self.lbl_libs = self._create_metric(dash_layout, "Libraries", "0", "#e67e22") # Orange
        header_layout.addWidget(dash_card, 3)

        # Action Controls
        ctrl_card = QFrame()
        ctrl_card.setStyleSheet(f"background: {card_bg}; border: 1px solid {card_border}; border-radius: 12px;")
        ctrl_layout = QVBoxLayout(ctrl_card)
        ctrl_layout.setContentsMargins(10, 8, 10, 10)
        ctrl_layout.setSpacing(8)
        apply_elevation(ctrl_card, theme)
        ctrl_title = QLabel("Actions")
        ctrl_title.setStyleSheet(f"font-weight: 600; color: {muted};")
        ctrl_layout.addWidget(ctrl_title)
        
        # Filter Dropdown
        ctrl_layout.addWidget(QLabel("Library filter"))
        self.lib_combo = QComboBox()
        self.lib_combo.setPlaceholderText("Filter by Library (Optional)")
        self.refresh_lib_list() # Populate dropdown
        ctrl_layout.addWidget(self.lib_combo)

        btn_run = QPushButton("RUN VALIDATION")
        btn_run.setIcon(Icons.get_icon(Icons.PLAY, "white"))
        btn_run.setStyleSheet("font-weight: 600; background-color: #1565C0; color: white; height: 32px; border-radius: 8px;")
        btn_run.clicked.connect(lambda checked=False: self.run_validation("all"))
        ctrl_layout.addWidget(btn_run)
        
        # Toggle Exemptions
        self.check_show_exempt = QPushButton("Toggle Exempted in Log")
        self.check_show_exempt.setCheckable(True)
        self.check_show_exempt.toggled.connect(self.refresh_current_view)
        ctrl_layout.addWidget(self.check_show_exempt)

        self.issue_search = QLineEdit()
        self.issue_search.setPlaceholderText("Filter issues (symbol, library, description)")
        self.issue_search.setClearButtonEnabled(True)
        self.issue_search.textChanged.connect(self.refresh_current_view)
        ctrl_layout.addWidget(self.issue_search)

        header_layout.addWidget(ctrl_card, 2)
        main_layout.addLayout(header_layout)

        # Issue Log Tree
        self.tree_valid = QTreeWidget()
        self.tree_valid.setHeaderLabels(["Library", "Symbol", "Issue Description"])
        self.tree_valid.setAlternatingRowColors(True)
        self.tree_valid.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree_valid.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree_valid.setRootIsDecorated(False)
        self.tree_valid.setUniformRowHeights(True)
        self.tree_valid.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree_valid.customContextMenuRequested.connect(self.show_log_menu)
        main_layout.addWidget(self.tree_valid)

    def setup_dupe_ui(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        is_dark = theme in ["Dark"]
        card_border = "#2F353D" if is_dark else "#EDE6DC"
        muted = "#9CA3AF" if is_dark else "#6B7280"
        
        header = QHBoxLayout()
        title = QLabel("Duplicate MPN Finder")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch()
        btn_scan = QPushButton("Scan for Duplicates")
        btn_scan.setIcon(Icons.get_icon(Icons.SEARCH, icon_color))
        btn_scan.setMinimumHeight(32)
        btn_scan.clicked.connect(self.find_duplicates)
        header.addWidget(btn_scan)
        layout.addLayout(header)

        self.tree_dupe = QTreeWidget()
        self.tree_dupe.setHeaderLabels(["MPN", "Count", "Affected Parts"])
        self.tree_dupe.header().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tree_dupe.setAlternatingRowColors(True)
        self.tree_dupe.setRootIsDecorated(False)
        self.tree_dupe.setUniformRowHeights(True)
        self.tree_dupe.setStyleSheet(f"QTreeWidget {{ border: 1px solid {card_border}; border-radius: 12px; }}")
        layout.addWidget(self.tree_dupe)

    def setup_fp_check_ui(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        is_dark = theme in ["Dark"]
        card_border = "#2F353D" if is_dark else "#EDE6DC"
        
        header = QHBoxLayout()
        title = QLabel("Footprint Verification")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch()
        btn_scan = QPushButton("Verify Pinouts")
        btn_scan.setIcon(Icons.get_icon(Icons.SEARCH, icon_color))
        btn_scan.setMinimumHeight(32)
        btn_scan.clicked.connect(self.run_fp_check)
        header.addWidget(btn_scan)
        layout.addLayout(header)

        self.tree_fp = QTreeWidget()
        self.tree_fp.setHeaderLabels(["Library", "Symbol", "Error"])
        self.tree_fp.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree_fp.setAlternatingRowColors(True)
        self.tree_fp.setRootIsDecorated(False)
        self.tree_fp.setUniformRowHeights(True)
        self.tree_fp.setStyleSheet(f"QTreeWidget {{ border: 1px solid {card_border}; border-radius: 12px; }}")
        layout.addWidget(self.tree_fp)

    def setup_exemption_ui(self, parent):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        theme = self.logic.settings.get("theme", "Light")
        is_dark = theme in ["Dark"]
        card_border = "#353A42" if is_dark else "#E1E6EC"

        header = QHBoxLayout()
        title = QLabel("Active Exemptions")
        title.setStyleSheet("font-weight: 600;")
        header.addWidget(title)
        header.addStretch()
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_exemptions)
        header.addWidget(btn_refresh)
        layout.addLayout(header)

        self.tree_exempt = QTreeWidget()
        self.tree_exempt.setHeaderLabels(["Target UID", "Ignored Rule", "Scope"])
        self.tree_exempt.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree_exempt.setAlternatingRowColors(True)
        self.tree_exempt.setRootIsDecorated(False)
        self.tree_exempt.setUniformRowHeights(True)
        self.tree_exempt.setStyleSheet(f"QTreeWidget {{ border: 1px solid {card_border}; border-radius: 10px; }}")
        layout.addWidget(self.tree_exempt)

        self.btn_restore = QPushButton("Restore (Remove Exemption)")
        self.btn_restore.clicked.connect(self.remove_exemption)
        layout.addWidget(self.btn_restore)

    def _create_metric(self, layout, label, value, color="black"):
        theme = self.logic.settings.get("theme", "Light")
        is_dark = theme in ["Dark"]
        card_bg = "#23262B" if is_dark else "#FFFFFF"
        card_border = "#353A42" if is_dark else "#E1E6EC"
        text_main = "#E5E7EB" if is_dark else "#111827"
        text_sub = "#9CA3AF" if is_dark else "#6B7280"

        frame = QFrame()
        frame.setStyleSheet(f"background-color: {card_bg}; border: 1px solid {card_border}; border-radius: 10px;")
        row = QHBoxLayout(frame)
        row.setContentsMargins(8, 6, 8, 6)
        row.setSpacing(8)
        accent = QFrame()
        accent.setFixedWidth(5)
        accent.setStyleSheet(f"background: {color}; border-radius: 3px;")
        row.addWidget(accent)
        col = QVBoxLayout()
        col.setSpacing(1)
        val_lbl = QLabel(value)
        val_lbl.setStyleSheet(f"font-size: 18px; font-weight: 600; color: {text_main};")
        txt_lbl = QLabel(label)
        txt_lbl.setStyleSheet(f"color: {text_sub}; font-size: 11px;")
        col.addWidget(val_lbl)
        col.addWidget(txt_lbl)
        row.addLayout(col)
        layout.addWidget(frame)
        return val_lbl

    # --- LOGIC ---

    def run_validation(self, scope="all"):
        if not hasattr(self.logic, 'validate_and_get_stats'):
            QMessageBox.critical(self, "Error", "Validation logic missing in backend.")
            return

        # Handle "Selected Library" scope from dropdown if needed
        target_lib = self.lib_combo.currentText()
        if target_lib and target_lib != "All Libraries" and scope == "all":
             scope = "selected"

        failures, stats = self.logic.validate_and_get_stats(scope, target_lib)
        self.all_current_failures = failures
        
        # Fetch shadowed (exempted) failures if backend supports it
        if hasattr(self.logic, 'get_exempted_failures'):
            self.shadow_failures = self.logic.get_exempted_failures(scope)
        else:
            self.shadow_failures = []

        # Update Dashboard
        total = stats['total_checked']
        self.lbl_checked.setText(str(total))
        self.lbl_fails.setText(str(stats['total_fails']))
        
        if total > 0:
            unique_failed = len(set(f"{f[0]}:{f[1]}" for f in failures))
            pass_rate = ((total - unique_failed) / total) * 100
            self.lbl_score.setText(f"{pass_rate:.1f}%")
        else:
            self.lbl_score.setText("-%")

        # Update New Metrics
        total_exempt = sum(len(v) for v in self.logic.exemptions.get('libraries', {}).values()) + \
                       sum(len(v) for v in self.logic.exemptions.get('parts', {}).values())
        self.lbl_exempt.setText(str(total_exempt))
        self.lbl_libs.setText(str(len(stats['fails_by_lib'].keys())))

        self.refresh_current_view()

    def refresh_current_view(self):
        self.tree_valid.clear()
        query = ""
        if hasattr(self, "issue_search"):
            query = (self.issue_search.text() or "").strip().lower()
        
        # 1. Normal Failures
        for f in self.all_current_failures:
            if self.current_filter_lib and f[0] != self.current_filter_lib: continue
            if query and query not in f"{f[0]} {f[1]} {f[2]}".lower():
                continue
            QTreeWidgetItem(self.tree_valid, list(f))

        # 2. Exempted (Shadow) Failures
        if self.check_show_exempt.isChecked():
            for f in self.shadow_failures:
                if self.current_filter_lib and f[0] != self.current_filter_lib: continue
                if query and query not in f"{f[0]} {f[1]} {f[2]}".lower():
                    continue
                item = QTreeWidgetItem(self.tree_valid, list(f))
                for i in range(3):
                    item.setForeground(i, QColor("gray"))
                    font = item.font(i)
                    font.setItalic(True)
                    item.setFont(i, font)

    def find_duplicates(self):
        dupes = self.logic.find_duplicates()
        self.tree_dupe.clear()
        for mpn, parts in dupes.items():
            QTreeWidgetItem(self.tree_dupe, [mpn, str(len(parts)), ", ".join(parts)])

    def run_fp_check(self):
        issues = self.logic.check_footprint_integrity()
        self.tree_fp.clear()
        for lib, name, err in issues:
            QTreeWidgetItem(self.tree_fp, [lib, name, err])
        
        if not issues:
            QMessageBox.information(self, "Success", "All symbol pins match their footprint pads.")

    def refresh_exemptions(self):
        self.tree_exempt.clear()
        for lib, rules in self.logic.exemptions.get('libraries', {}).items():
            for r in rules: QTreeWidgetItem(self.tree_exempt, [lib, r, "Library Wide"])
        for uid, rules in self.logic.exemptions.get('parts', {}).items():
            for r in rules: QTreeWidgetItem(self.tree_exempt, [uid, r, "Specific Part"])

    def remove_exemption(self):
        item = self.tree_exempt.currentItem()
        if not item: return
        target, rule, scope = item.text(0), item.text(1), item.text(2)
        
        if "Library" in scope:
            if target in self.logic.exemptions['libraries'] and rule in self.logic.exemptions['libraries'][target]:
                self.logic.exemptions['libraries'][target].remove(rule)
        else:
            if target in self.logic.exemptions['parts'] and rule in self.logic.exemptions['parts'][target]:
                self.logic.exemptions['parts'][target].remove(rule)
        
        self.logic.save_rules()
        self.refresh_exemptions()
        QMessageBox.information(self, "Restored", f"Rule '{rule}' restored for {target}.")

    def show_log_menu(self, pos):
        item = self.tree_valid.itemAt(pos)
        if not item: return
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        items = self.tree_valid.selectedItems()
        if not items or item not in items:
            items = [item]
        
        menu = QMenu()
        count_suffix = f" ({len(items)})" if len(items) > 1 else ""
        act_exempt_part = menu.addAction(f"Exempt PART{count_suffix} from this Rule")
        act_exempt_lib = menu.addAction("Exempt LIBRARY from this Rule")
        menu.addSeparator()
        act_edit = menu.addAction(Icons.get_icon(Icons.EDIT, icon_color), f"Fix Property (Bulk Edit{count_suffix})...")
        
        action = menu.exec(self.tree_valid.viewport().mapToGlobal(pos))
        
        if action == act_exempt_part: 
            for i in items:
                self.exempt_part_rule(i, refresh=False)
            self.run_validation()
        elif action == act_exempt_lib: self.exempt_lib_rule(item)
        elif action == act_edit: self.bulk_edit(items if len(items) > 1 else item)

    def bulk_edit(self, items):
        if not isinstance(items, list): items = [items]
        item = items[0]

        lib, sym, issue = item.text(0), item.text(1), item.text(2)
        # Regex to extract the missing property name from issue text (e.g., "Missing 'MPN'")
        key_match = re.search(r"'(.*?)'", issue)
        key = key_match.group(1) if key_match else "MPN"
        
        target_desc = sym if len(items) == 1 else f"{len(items)} parts"
        val, ok = QInputDialog.getText(self, "Bulk Edit", f"New value for '{key}' in {target_desc}:")
        if ok and val:
            errors = []
            for i in items:
                l, s = i.text(0), i.text(1)
                success, msg = self.logic.bulk_edit_property(l, s, key, val)
                if not success: errors.append(f"{s}: {msg}")
            
            if errors:
                QMessageBox.warning(self, "Errors", "\n".join(errors[:10]))
            self.run_validation()

    def exempt_part_rule(self, item, refresh=True):
        lib, sym, issue = item.text(0), item.text(1), item.text(2)
        rule = re.search(r"'(.*?)'", issue)
        if rule:
            self.logic.add_part_exemption(lib, sym, rule.group(1))
            if refresh: self.run_validation()

    def exempt_lib_rule(self, item):
        lib, issue = item.text(0), item.text(2)
        rule = re.search(r"'(.*?)'", issue)
        if rule:
            self.logic.add_lib_exemption(lib, rule.group(1))
            self.run_validation()

    def refresh_lib_list(self):
        """Populates the library selection dropdown with currently loaded data."""
        self.lib_combo.clear()
        if hasattr(self.logic, 'data_store') and self.logic.data_store:
            # FIX: Use keys() for dictionary iteration
            libs = sorted(self.logic.data_store.keys())
            self.lib_combo.addItem("All Libraries")
            self.lib_combo.addItems(libs)
