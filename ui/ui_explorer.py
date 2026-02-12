import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QInputDialog,
                             QTreeView, QSplitter, QPushButton, QLabel, QGroupBox,
                             QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox, QApplication, QMenu, QToolButton)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QDesktopServices, QAction
from PySide6.QtCore import Qt, QSortFilterProxyModel, QThread, Signal, QUrl, QTimer

try:
    from .view_widgets import SymbolWidget, FootprintWidget
except ImportError:
    from view_widgets import SymbolWidget, FootprintWidget
try:
    from .icons import Icons
except ImportError:
    from ui.icons import Icons

class ScanWorker(QThread):
    finished = Signal(int)
    error = Signal(str)

    def __init__(self, logic, path, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.path = path

    def run(self):
        try:
            # Run the heavy scanning operation in this background thread
            count = self.logic.scan_libraries(self.path)
            self.finished.emit(count)
        except Exception as e:
            self.error.emit(str(e))

class ExplorerTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.current_datasheet = None
        self.current_filepath = None
        self.setup_ui()
        # Try to load existing data on startup
        if self.logic.data_store:
            self.refresh_data()
        elif self.logic.settings.get("symbol_path"):
            # Auto-run scan if path is configured but no data loaded
            self.run_scan()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        
        # --- Top Bar ---
        top_bar = QHBoxLayout()
        
        # 1. Rescan Button (CRITICAL FIX)
        self.btn_scan = QPushButton("Rescan Libraries")
        self.btn_scan.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        self.btn_scan.setStyleSheet("font-weight: bold; height: 30px;")
        self.btn_scan.clicked.connect(self.run_scan)
        top_bar.addWidget(self.btn_scan)

        # 1.5 Online Search
        btn_online = QPushButton("Search Online")
        btn_online.setIcon(Icons.get_icon(Icons.GLOBE, icon_color))
        btn_online.clicked.connect(self.search_online)
        top_bar.addWidget(btn_online)

        # 2. Search
        self.search_main = QLineEdit()
        self.search_main.setPlaceholderText("Search Library or Part Name...")
        self.search_main.textChanged.connect(self.apply_filters)
        top_bar.addWidget(self.search_main, 3)
        
        # 3. Filter
        self.filter_orphan = QCheckBox("Show Orphans Only")
        self.filter_orphan.toggled.connect(self.apply_filters)
        top_bar.addWidget(self.filter_orphan)
        layout.addLayout(top_bar)
        
        # --- Splitter ---
        splitter = QSplitter(Qt.Horizontal)
        
        # Left: Tree
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Library", "Part", "Pins", "Projects"])
        
        self.proxy = QSortFilterProxyModel()
        self.proxy.setSourceModel(self.model)
        self.proxy.setFilterKeyColumn(-1) 
        
        self.tree = QTreeView()
        self.tree.setModel(self.proxy)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.selectionModel().selectionChanged.connect(self.on_select)
        splitter.addWidget(self.tree)
        
        # Right: Details
        right_panel = QWidget()
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0,0,0,0)
        
        self.lbl_part = QLabel("Select a part to view details")
        self.lbl_part.setStyleSheet("font-size: 12pt; font-weight: bold; padding: 5px;")
        r_layout.addWidget(self.lbl_part)

        # Action Buttons (Datasheet & File)
        btn_layout = QHBoxLayout()
        self.btn_datasheet = QPushButton("Open Datasheet")
        self.btn_datasheet.setIcon(Icons.get_icon(Icons.DOC, icon_color))
        self.btn_datasheet.clicked.connect(self.open_datasheet)
        self.btn_file = QPushButton("Open Source File")
        self.btn_file.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        self.btn_file.clicked.connect(self.open_symbol_file)
        btn_layout.addWidget(self.btn_datasheet)
        btn_layout.addWidget(self.btn_file)
        r_layout.addLayout(btn_layout)
        
        # Visualizers Container
        vis_split = QSplitter(Qt.Vertical)
        
        # View Options
        view_opts = QHBoxLayout()
        self.chk_sym = QCheckBox("Symbol"); self.chk_sym.setChecked(True)
        self.chk_fp = QCheckBox("Footprint"); self.chk_fp.setChecked(True)
        self.chk_pin = QCheckBox("Pinout"); self.chk_pin.setChecked(True)
        
        self.chk_sym.toggled.connect(lambda v: self.sym_view.setVisible(v))
        self.chk_fp.toggled.connect(lambda v: self.fp_view.setVisible(v))
        self.chk_pin.toggled.connect(lambda v: self.pin_table.setVisible(v))
        
        view_opts.addWidget(QLabel("Show:"))
        view_opts.addWidget(self.chk_sym)
        view_opts.addWidget(self.chk_fp)
        view_opts.addWidget(self.chk_pin)
        view_opts.addStretch()
        r_layout.addLayout(view_opts)
        
        # Symbol Viewer Container with Controls
        sym_container = QWidget()
        sym_layout = QVBoxLayout(sym_container)
        sym_layout.setContentsMargins(0,0,0,0)
        sym_layout.setSpacing(2)
        
        sym_ctrl = QHBoxLayout()
        sym_ctrl.addWidget(QLabel("Symbol:"))
        btn_zin = QPushButton("+"); btn_zin.setFixedWidth(25); btn_zin.clicked.connect(lambda: self.sym_view.zoom(1.2))
        btn_zout = QPushButton("-"); btn_zout.setFixedWidth(25); btn_zout.clicked.connect(lambda: self.sym_view.zoom(0.8))
        btn_rst = QPushButton("Reset"); btn_rst.setFixedWidth(45); btn_rst.clicked.connect(lambda: self.sym_view.reset_view())
        sym_ctrl.addStretch(); sym_ctrl.addWidget(btn_zin); sym_ctrl.addWidget(btn_zout); sym_ctrl.addWidget(btn_rst)
        sym_layout.addLayout(sym_ctrl)

        self.sym_view = SymbolWidget()
        sym_layout.addWidget(self.sym_view)

        # Footprint Viewer Container with Controls
        fp_container = QWidget()
        fp_layout = QVBoxLayout(fp_container)
        fp_layout.setContentsMargins(0,0,0,0)
        fp_layout.setSpacing(2)

        fp_ctrl = QHBoxLayout()
        fp_ctrl.addWidget(QLabel("Footprint:"))
        
        # Layer Visibility Dropdown
        self.btn_layers = QToolButton()
        self.btn_layers.setText("Layers ▾")
        self.btn_layers.setPopupMode(QToolButton.InstantPopup)
        self.layer_menu = QMenu(self.btn_layers)
        self.btn_layers.setMenu(self.layer_menu)
        
        self.layer_actions = {}
        for layer in FootprintWidget.LAYER_COLORS.keys():
            action = QAction(layer, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.triggered.connect(self.update_fp_layer_visibility)
            self.layer_menu.addAction(action)
            self.layer_actions[layer] = action
            
        fp_ctrl.addWidget(self.btn_layers)
        
        btn_nums = QPushButton("123")
        btn_nums.setCheckable(True)
        btn_nums.setFixedWidth(35)
        btn_nums.setToolTip("Toggle Pad Numbers")
        btn_nums.toggled.connect(lambda c: self.fp_view.toggle_pad_numbers(c))
        
        btn_fp_zin = QPushButton("+"); btn_fp_zin.setFixedWidth(25)
        btn_fp_zout = QPushButton("-"); btn_fp_zout.setFixedWidth(25)
        btn_fp_rst = QPushButton("Reset"); btn_fp_rst.setFixedWidth(45)
        btn_measure = QPushButton("Measure"); btn_measure.setCheckable(True)
        fp_ctrl.addStretch()
        fp_ctrl.addWidget(btn_nums)
        fp_ctrl.addWidget(btn_measure)
        fp_ctrl.addWidget(btn_fp_zin)
        fp_ctrl.addWidget(btn_fp_zout)
        fp_ctrl.addWidget(btn_fp_rst)
        fp_layout.addLayout(fp_ctrl)

        self.fp_view = FootprintWidget()
        btn_fp_zin.clicked.connect(lambda: self.fp_view.zoom(1.2))
        btn_fp_zout.clicked.connect(lambda: self.fp_view.zoom(0.8))
        btn_fp_rst.clicked.connect(lambda: self.fp_view.reset_view())
        btn_measure.toggled.connect(self.fp_view.toggle_measure_mode)
        fp_layout.addWidget(self.fp_view)

        self.pin_table = QTableWidget(0, 4)
        self.pin_table.setHorizontalHeaderLabels(["Pin", "Name", "Type", "Pad"])
        self.pin_table.horizontalHeader().setStretchLastSection(True)

        vis_split.addWidget(sym_container)
        vis_split.addWidget(fp_container)
        vis_split.addWidget(self.pin_table)
        vis_split.setSizes([200, 200, 150]) 
        r_layout.addWidget(vis_split)
        
        # Properties
        self.prop_table = QTableWidget(0, 2)
        self.prop_table.setHorizontalHeaderLabels(["Property", "Value"])
        self.prop_table.horizontalHeader().setStretchLastSection(True)
        r_layout.addWidget(self.prop_table)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)
        layout.addWidget(splitter)

    def run_scan(self):
        path = self.logic.settings.get("symbol_path", "")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Path Error", "Please go to the Settings tab and select a valid Symbol Library Path.")
            return

        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning...")
        
        # Start Background Thread
        self.worker = ScanWorker(self.logic, path, self)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        self.worker.start()

    def on_scan_finished(self, count):
        self.refresh_data()
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText(f"Loaded {count} Libs")
        QTimer.singleShot(3000, lambda: self.btn_scan.setText("Rescan Libraries"))

    def on_scan_error(self, err):
        self.btn_scan.setEnabled(True); self.btn_scan.setText("Rescan Libraries")
        QMessageBox.critical(self, "Scan Error", f"An error occurred:\n{err}")

    def search_online(self):
        text, ok = QInputDialog.getText(self, "Search Online", "Enter Part Number or Keyword:")
        if ok and text:
            QDesktopServices.openUrl(QUrl(f"https://octopart.com/search?q={text}"))

    def refresh_data(self):
        self.model.removeRows(0, self.model.rowCount())
        for lib, parts in self.logic.data_store.items():
            for name, data in parts.items():
                i_lib = QStandardItem(lib)
                i_name = QStandardItem(name)
                i_pins = QStandardItem(); i_pins.setData(len(data.get("pins", [])), Qt.DisplayRole)
                
                uid = f"{lib}:{name}"
                usage_count = len(self.logic.project_manager.project_index.get(uid, []))
                i_usage = QStandardItem(); i_usage.setData(usage_count, Qt.DisplayRole)
                if usage_count == 0: i_usage.setForeground(QColor("orange")) 
                
                i_name.setData(data, Qt.UserRole)
                self.model.appendRow([i_lib, i_name, i_pins, i_usage])

    def update_fp_layer_visibility(self):
        """Updates the visible layers in the footprint widget based on checkbox state."""
        visible = {layer for layer, act in self.layer_actions.items() if act.isChecked()}
        self.fp_view.set_visible_layers(visible)

    def apply_filters(self):
        txt = self.search_main.text()
        self.proxy.setFilterFixedString(txt)
        # Orphan filter logic could go here by subclassing proxy, 
        # but text filter is safest for now.

    def on_select(self, selected, deselected):
        idx = selected.indexes()
        if not idx: return
        src_idx = self.proxy.mapToSource(idx[0])
        item = self.model.item(src_idx.row(), 1) 
        data = item.data(Qt.UserRole)
        
        self.lbl_part.setText(f"{data['library']} : {data['name']}")
        self.sym_view.set_data(data)

        # Update Actions
        self.current_datasheet = data.get("properties", {}).get("Datasheet", "")
        self.current_filepath = data.get("file_path", "")
        self.btn_datasheet.setEnabled(bool(self.current_datasheet and self.current_datasheet != "~"))
        self.btn_file.setEnabled(bool(self.current_filepath))
        
        # Try to resolve footprint geometry if available
        fp_ref = data.get("properties", {}).get("Footprint", "")
        geom = self.logic.get_footprint_data(fp_ref)
        self.fp_view.set_data(geom)
        self.update_fp_layer_visibility() # Apply current visibility settings
        
        # Populate Pinout Table
        self.pin_table.setRowCount(0)
        pins = data.get("pins", [])
        pads = geom.get("pads", []) if geom else []
        
        # Map pads by number
        pad_map = {p.get("number"): p for p in pads}
        
        for p in pins:
            row = self.pin_table.rowCount()
            self.pin_table.insertRow(row)
            num = p.get("number", "")
            self.pin_table.setItem(row, 0, QTableWidgetItem(num))
            self.pin_table.setItem(row, 1, QTableWidgetItem(p.get("name", "")))
            self.pin_table.setItem(row, 2, QTableWidgetItem(p.get("type", "")))
            
            pad_info = "Found" if num in pad_map else "Missing"
            self.pin_table.setItem(row, 3, QTableWidgetItem(pad_info))

        self.prop_table.setRowCount(0)
        for k, v in data.get("properties", {}).items():
            r = self.prop_table.rowCount()
            self.prop_table.insertRow(r)
            self.prop_table.setItem(r, 0, QTableWidgetItem(k))
            self.prop_table.setItem(r, 1, QTableWidgetItem(v))

    def open_datasheet(self):
        if self.current_datasheet:
            QDesktopServices.openUrl(QUrl(self.current_datasheet))

    def open_symbol_file(self):
        if self.current_filepath and os.path.exists(self.current_filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_filepath))

    def show_context_menu(self, pos):
        idx = self.tree.indexAt(pos)
        if not idx.isValid(): return
        
        menu = QMenu()
        act_copy = menu.addAction("Copy Reference")
        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        
        if action == act_copy:
            src_idx = self.proxy.mapToSource(idx)
            # Assuming column 1 is name, column 0 is lib
            txt = f"{self.model.item(src_idx.row(), 0).text()}:{self.model.item(src_idx.row(), 1).text()}"
            QApplication.clipboard().setText(txt)

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)