import os
import re
from pathlib import Path
from datetime import datetime
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLineEdit, QInputDialog,
                             QTreeView, QSplitter, QPushButton, QLabel, QGroupBox, QTabWidget,
                             QTableWidget, QTableWidgetItem, QCheckBox, QMessageBox, QApplication, QMenu, QToolButton,
                             QColorDialog, QComboBox, QSpinBox, QHeaderView, QAbstractSpinBox,
                             QGridLayout, QSizePolicy, QStackedWidget, QListWidget, QListWidgetItem)
from PySide6.QtGui import QStandardItemModel, QStandardItem, QColor, QDesktopServices, QAction, QIcon, QPixmap
from PySide6.QtCore import Qt, QSortFilterProxyModel, QThread, Signal, QUrl, QTimer, QFileSystemWatcher, QSize

from ui.widgets.footprint_widget import FootprintWidget
from ui.widgets.model_preview import ModelPreviewWidget
from ui.widgets.symbol_widget import SymbolWidget
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.empty_state import EmptyState
from ui.resources.icons import Icons
from ui.core.warning_center import warning_center

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


class SymbolFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._library = "All Libraries"
        self._orphans_only = False
        self._has_fp = False
        self._has_ds = False
        self._min_pins = 0

    def setTextFilter(self, text):
        self._text = (text or "").lower()
        self.invalidateFilter()

    def setLibraryFilter(self, lib):
        self._library = lib or "All Libraries"
        self.invalidateFilter()

    def setShowOrphans(self, value):
        self._orphans_only = bool(value)
        self.invalidateFilter()

    def setRequireFootprint(self, value):
        self._has_fp = bool(value)
        self.invalidateFilter()

    def setRequireDatasheet(self, value):
        self._has_ds = bool(value)
        self.invalidateFilter()

    def setMinPins(self, value):
        self._min_pins = int(value or 0)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        idx_lib = model.index(source_row, 0, source_parent)
        idx_name = model.index(source_row, 1, source_parent)
        idx_pins = model.index(source_row, 2, source_parent)
        idx_usage = model.index(source_row, 3, source_parent)

        lib = (idx_lib.data() or "")
        name = (idx_name.data() or "")
        pins = idx_pins.data()
        usage = idx_usage.data()

        if self._library and self._library != "All Libraries" and lib != self._library:
            return False

        if self._text:
            hay = f"{lib} {name}".lower()
            if self._text not in hay:
                return False

        if self._orphans_only and usage not in (0, "0"):
            return False

        if self._min_pins and isinstance(pins, int) and pins < self._min_pins:
            return False

        data = idx_name.data(Qt.UserRole) or {}
        props = data.get("properties", {}) if isinstance(data, dict) else {}
        if self._has_fp:
            fp = (props.get("Footprint") or "").strip()
            if not fp or fp == "~":
                return False
        if self._has_ds:
            ds = (props.get("Datasheet") or "").strip()
            if not ds or ds == "~":
                return False

        return True


class FootprintFilterProxy(QSortFilterProxyModel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._text = ""
        self._library = "All Libraries"
        self._has_3d = False
        self._min_pads = 0

    def setTextFilter(self, text):
        self._text = (text or "").lower()
        self.invalidateFilter()

    def setLibraryFilter(self, lib):
        self._library = lib or "All Libraries"
        self.invalidateFilter()

    def setRequire3D(self, value):
        self._has_3d = bool(value)
        self.invalidateFilter()

    def setMinPads(self, value):
        self._min_pads = int(value or 0)
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        idx_lib = model.index(source_row, 0, source_parent)
        idx_name = model.index(source_row, 1, source_parent)
        idx_pads = model.index(source_row, 2, source_parent)
        idx_model = model.index(source_row, 3, source_parent)

        lib = (idx_lib.data() or "")
        name = (idx_name.data() or "")
        pads = idx_pads.data()
        has_model = (idx_model.data() or "")

        if self._library and self._library != "All Libraries" and lib != self._library:
            return False

        if self._text:
            hay = f"{lib} {name}".lower()
            if self._text not in hay:
                return False

        if self._min_pads and isinstance(pads, int) and pads < self._min_pads:
            return False

        if self._has_3d and has_model != "Yes":
            return False

        return True

class ExplorerTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.fp_view = FootprintWidget()
        self.current_datasheet = None
        self.current_filepath = None
        self._scan_in_progress = False
        self._auto_scan_timer = QTimer(self)
        self._auto_scan_timer.setSingleShot(True)
        self._auto_scan_timer.timeout.connect(self._trigger_auto_scan)
        self.fs_watcher = QFileSystemWatcher(self)
        self.fs_watcher.directoryChanged.connect(self.on_fs_change)
        self.fs_watcher.fileChanged.connect(self.on_fs_change)
        self.setup_ui()
        # Try to load existing data on startup
        if self.logic.data_store:
            self.refresh_data()
        elif self.logic.settings.get("symbol_path"):
            # Auto-run scan if path is configured but no data loaded
            self.run_scan()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        apply_layout(layout, margin=PAGE_PADDING, spacing="sm")
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        preview_accent = "#6366F1"
        if theme == "Dark":
            preview_btn_bg = "#1F232B"
            preview_btn_border = "#3B424D"
            preview_btn_hover = "#2C3240"
            preview_btn_checked = "#32394F"
            preview_btn_text = "#F4F6F9"
            preview_icon_hover = "#272D38"
        else:
            preview_btn_bg = "#F7F8FA"
            preview_btn_border = "#D5D9E3"
            preview_btn_hover = "#ECEFF4"
            preview_btn_checked = "#E2E3FF"
            preview_btn_text = "#111827"
            preview_icon_hover = "#E4E7F0"

        ctrl_bg = "#181B23" if theme == "Dark" else "#FFFFFF"
        ctrl_border = "#2B3140" if theme == "Dark" else "#D5D9E3"
        ctrl_hover = "#242B3B" if theme == "Dark" else "#F5F7FA"
        ctrl_checked = "#2C2F42" if theme == "Dark" else "#E8EBFF"
        ctrl_text = "#F4F6F9" if theme == "Dark" else "#111827"
        icon_bg = "#0F172A" if theme == "Dark" else "#F1F5F9"
        icon_border = "#3A3F4E" if theme == "Dark" else "#E2E8F0"

        preview_button_styles = f"""
            QPushButton#fpPreviewButton, QToolButton#fpPreviewButton {{
                background-color: {preview_btn_bg};
                border: 1px solid {preview_btn_border};
                border-radius: 10px;
                padding: 4px 14px;
                color: {preview_btn_text};
                min-height: 32px;
                font-weight: 600;
            }}
            QPushButton#fpPreviewButton:hover, QToolButton#fpPreviewButton:hover {{
                background-color: {preview_btn_hover};
            }}
            QPushButton#fpPreviewButton:checked, QToolButton#fpPreviewButton:checked {{
                border-color: {preview_accent};
                background-color: {preview_btn_checked};
                color: {preview_accent};
            }}
            QPushButton#fpPreviewIconButton {{
                background-color: {preview_btn_bg};
                border: 1px solid {preview_btn_border};
                border-radius: 10px;
                min-width: 36px;
                min-height: 36px;
                max-width: 36px;
                max-height: 36px;
                padding: 0px;
            }}
            QPushButton#fpPreviewIconButton:hover {{
                background-color: {preview_icon_hover};
                border-color: {preview_accent};
            }}
            QPushButton#fpPreviewIconButton:pressed {{
                background-color: {preview_btn_hover};
            }}
            QPushButton#fpCtrlButton, QToolButton#fpCtrlButton {{
                background-color: {ctrl_bg};
                border: 1px solid {ctrl_border};
                border-radius: 12px;
                padding: 6px 14px;
                color: {ctrl_text};
                min-height: 34px;
                font-weight: 600;
                text-transform: none;
            }}
            QPushButton#fpCtrlButton:hover, QToolButton#fpCtrlButton:hover {{
                background-color: {ctrl_hover};
                border-color: {preview_accent};
            }}
            QPushButton#fpCtrlButton:checked, QToolButton#fpCtrlButton:checked {{
                background-color: {ctrl_checked};
                border-color: {preview_accent};
                color: {preview_accent};
            }}
            QPushButton#fpIconButton {{
                background-color: {icon_bg};
                border: 1px solid {icon_border};
                border-radius: 10px;
                min-width: 34px;
                min-height: 34px;
                max-width: 34px;
                max-height: 34px;
                padding: 0px;
            }}
            QPushButton#fpIconButton:hover {{
                border-color: {preview_accent};
            }}
            QPushButton#fpIconButton:pressed {{
                background-color: {ctrl_hover};
            }}
            QToolButton#fpPreviewButton::menu-indicator {{
                margin-left: 6px;
            }}
        """
        
        top_bar = QHBoxLayout()
        layout.addLayout(top_bar)

        self.search_main = QLineEdit()
        self.search_main.setPlaceholderText("Search across symbols and footprints...")
        self.search_main.setClearButtonEnabled(True)
        self.search_main.setMinimumHeight(32)
        self.search_main.textChanged.connect(self.apply_filters)
        top_bar.addWidget(self.search_main, 1)

        self.chk_auto_rescan = QCheckBox("Auto-rescan")
        self.chk_auto_rescan.toggled.connect(self.toggle_auto_rescan)
        top_bar.addWidget(self.chk_auto_rescan)

        self.lbl_scan_status = QLabel("Last scan: -")
        self.lbl_scan_status.setStyleSheet("color: #667085;")
        top_bar.addWidget(self.lbl_scan_status)

        top_bar.addStretch(1)

        self.btn_scan = QPushButton("Rescan Libraries")
        self.btn_scan.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        self.btn_scan.setObjectName("btnPrimary")
        self.btn_scan.setMinimumHeight(32)
        self.btn_scan.clicked.connect(self.run_scan)
        top_bar.addWidget(self.btn_scan)
        
        # --- Splitter ---
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        splitter.setHandleWidth(6)
        
        # Left: Tabs (Symbols / Footprints)
        self.left_tabs = QTabWidget()
        self.left_tabs.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.left_tabs.setTabPosition(QTabWidget.North)
        self.left_tabs.setMovable(False)
        self.left_tabs.setIconSize(QSize(20, 20))
        self.left_tabs.setDocumentMode(True)
        self.left_tabs.setProperty("stretchTabs", True)
        self.left_tabs.tabBar().setExpanding(True)

        # Symbols Tree
        self.model = QStandardItemModel()
        self.model.setHorizontalHeaderLabels(["Library", "Part", "Pins", "Projects"])
        
        self.proxy = SymbolFilterProxy()
        self.proxy.setSourceModel(self.model)
        
        self.tree = QTreeView()
        self.tree.setModel(self.proxy)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSortingEnabled(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setStyleSheet("QTreeView::item { padding: 4px 6px; }")
        sym_header = self.tree.header()
        sym_header.setStretchLastSection(False)
        sym_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        sym_header.setSectionResizeMode(1, QHeaderView.Stretch)
        sym_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        sym_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.selectionModel().selectionChanged.connect(self.on_select)

        sym_tab = QWidget()
        sym_layout = QVBoxLayout(sym_tab)
        sym_layout.setContentsMargins(0, 0, 0, 0)
        sym_layout.setSpacing(6)

        sym_header = QHBoxLayout()
        sym_title = QLabel("Symbol Library")
        sym_title.setStyleSheet("font-weight: 600;")
        self.sym_count_label = QLabel("0 / 0")
        self.sym_count_label.setStyleSheet("color: #6B7280;")
        self.sym_filter_toggle = QToolButton()
        self.sym_filter_toggle.setText("Filters")
        self.sym_filter_toggle.setCheckable(True)
        self.sym_filter_toggle.setChecked(False)
        self.sym_filter_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        sym_header.addWidget(sym_title)
        sym_header.addStretch()
        sym_header.addWidget(self.sym_count_label)
        sym_header.addWidget(self.sym_filter_toggle)
        sym_layout.addLayout(sym_header)

        sym_filter_panel = QWidget()
        sym_filter_layout = QGridLayout(sym_filter_panel)
        sym_filter_layout.setContentsMargins(0, 0, 0, 0)
        sym_filter_layout.setHorizontalSpacing(12)
        sym_filter_layout.setVerticalSpacing(6)

        self.sym_lib_combo = QComboBox()
        self.sym_lib_combo.setMinimumWidth(180)
        self.sym_lib_combo.currentTextChanged.connect(self.apply_filters)

        self.filter_orphan = QCheckBox("Orphans only")
        self.filter_orphan.toggled.connect(self.apply_filters)
        self.chk_has_fp = QCheckBox("Has footprint")
        self.chk_has_fp.toggled.connect(self.apply_filters)
        self.chk_has_ds = QCheckBox("Has datasheet")
        self.chk_has_ds.toggled.connect(self.apply_filters)

        self.spin_min_pins = QSpinBox()
        self.spin_min_pins.setRange(0, 9999)
        self.spin_min_pins.valueChanged.connect(self.apply_filters)
        self.spin_min_pins.setFixedWidth(70)
        self.spin_min_pins.setButtonSymbols(QAbstractSpinBox.PlusMinus)
        self.spin_min_pins.setStyleSheet(
            "QSpinBox { padding-right: 18px; }"
            "QSpinBox::up-button, QSpinBox::down-button { width: 18px; }"
        )

        sym_filter_layout.addWidget(QLabel("Library"), 0, 0)
        sym_filter_layout.addWidget(self.sym_lib_combo, 0, 1)
        sym_filter_layout.addWidget(QLabel("Min pins"), 0, 2)
        sym_filter_layout.addWidget(self.spin_min_pins, 0, 3)
        sym_filter_layout.addWidget(self.filter_orphan, 1, 0)
        sym_filter_layout.addWidget(self.chk_has_fp, 1, 1)
        sym_filter_layout.addWidget(self.chk_has_ds, 1, 2)
        sym_filter_layout.setColumnStretch(1, 1)
        sym_filter_layout.setColumnStretch(3, 0)

        self.sym_filter_toggle.toggled.connect(sym_filter_panel.setVisible)
        sym_filter_panel.setVisible(False)
        sym_layout.addWidget(sym_filter_panel)
        self.sym_stack = QStackedWidget()
        self.sym_stack.addWidget(self.tree)
        self.sym_empty = EmptyState(
            "No symbols found",
            "Rescan libraries or update your symbol paths.",
            Icons.CHIP,
            "Rescan Libraries",
            self.run_scan,
            icon_color,
        )
        self.sym_stack.addWidget(self.sym_empty)
        sym_layout.addWidget(self.sym_stack)
        self.left_tabs.addTab(sym_tab, Icons.get_icon(Icons.CHIP, icon_color), "Symbols")

        # Footprints Tree
        self.fp_model = QStandardItemModel()
        self.fp_model.setHorizontalHeaderLabels(["Library", "Footprint", "Pads", "3D", "Usage"])
        
        self.fp_proxy = FootprintFilterProxy()
        self.fp_proxy.setSourceModel(self.fp_model)

        self.fp_tree = QTreeView()
        self.fp_tree.setModel(self.fp_proxy)
        self.fp_tree.setAlternatingRowColors(True)
        self.fp_tree.setSortingEnabled(True)
        self.fp_tree.setUniformRowHeights(True)
        self.fp_tree.setStyleSheet("QTreeView::item { padding: 4px 6px; }")
        fp_header = self.fp_tree.header()
        fp_header.setStretchLastSection(False)
        fp_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        fp_header.setSectionResizeMode(1, QHeaderView.Interactive)
        fp_header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        fp_header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        fp_header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        self.fp_tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.fp_tree.customContextMenuRequested.connect(self.show_fp_context_menu)
        self.fp_tree.selectionModel().selectionChanged.connect(self.on_select_footprint)

        fp_tab = QWidget()
        fp_layout = QVBoxLayout(fp_tab)
        fp_layout.setContentsMargins(0, 0, 0, 0)
        fp_layout.setSpacing(6)

        fp_header = QHBoxLayout()
        fp_title = QLabel("Footprint Library")
        fp_title.setStyleSheet("font-weight: 600;")
        self.fp_count_label = QLabel("0 / 0")
        self.fp_count_label.setStyleSheet("color: #6B7280;")
        self.fp_filter_toggle = QToolButton()
        self.fp_filter_toggle.setText("Filters")
        self.fp_filter_toggle.setCheckable(True)
        self.fp_filter_toggle.setChecked(False)
        self.fp_filter_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        fp_header.addWidget(fp_title)
        fp_header.addStretch()
        fp_header.addWidget(self.fp_count_label)
        fp_header.addWidget(self.fp_filter_toggle)
        fp_layout.addLayout(fp_header)

        fp_filter_panel = QWidget()
        fp_filter_layout = QGridLayout(fp_filter_panel)
        fp_filter_layout.setContentsMargins(0, 0, 0, 0)
        fp_filter_layout.setHorizontalSpacing(12)
        fp_filter_layout.setVerticalSpacing(6)

        self.fp_lib_combo = QComboBox()
        self.fp_lib_combo.setMinimumWidth(180)
        self.fp_lib_combo.currentTextChanged.connect(self.apply_filters)
        self.chk_fp_3d = QCheckBox("Has 3D model")
        self.chk_fp_3d.toggled.connect(self.apply_filters)

        self.spin_min_pads = QSpinBox()
        self.spin_min_pads.setRange(0, 9999)
        self.spin_min_pads.valueChanged.connect(self.apply_filters)
        self.spin_min_pads.setFixedWidth(70)

        fp_filter_layout.addWidget(QLabel("Library"), 0, 0)
        fp_filter_layout.addWidget(self.fp_lib_combo, 0, 1)
        fp_filter_layout.addWidget(QLabel("Min pads"), 0, 2)
        fp_filter_layout.addWidget(self.spin_min_pads, 0, 3)
        fp_filter_layout.addWidget(self.chk_fp_3d, 1, 0)
        fp_filter_layout.setColumnStretch(1, 1)
        fp_filter_layout.setColumnStretch(3, 0)

        self.fp_filter_toggle.toggled.connect(fp_filter_panel.setVisible)
        fp_filter_panel.setVisible(False)
        fp_layout.addWidget(fp_filter_panel)
        self.fp_stack = QStackedWidget()
        self.fp_stack.addWidget(self.fp_tree)
        self.fp_empty = EmptyState(
            "No footprints found",
            "Rescan libraries or update your footprint paths.",
            Icons.TOOL,
            "Rescan Libraries",
            self.run_scan,
            icon_color,
        )
        self.fp_stack.addWidget(self.fp_empty)
        fp_layout.addWidget(self.fp_stack)
        self.left_tabs.addTab(fp_tab, Icons.get_icon(Icons.TOOL, icon_color), "Footprints")

        splitter.addWidget(self.left_tabs)
        
        # Right: Details
        right_panel = QWidget()
        right_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        r_layout = QVBoxLayout(right_panel)
        r_layout.setContentsMargins(0, 0, 0, 0)
        r_layout.setSpacing(10)
        
        selection_panel = QWidget()
        selection_panel.setObjectName("selectionPanel")
        selection_layout = QVBoxLayout(selection_panel)
        selection_layout.setContentsMargins(12, 8, 12, 8)
        selection_layout.setSpacing(4)

        header_row = QHBoxLayout()
        self.lbl_part = QLabel("Select a part to view details")
        self.lbl_part.setStyleSheet("font-size: 12pt; font-weight: 600;")
        header_row.addWidget(self.lbl_part, 1)

        self.btn_datasheet = QPushButton("Datasheet")
        self.btn_datasheet.setIcon(Icons.get_icon(Icons.DOC, icon_color))
        self.btn_datasheet.clicked.connect(self.open_datasheet)
        self.btn_file = QPushButton("Source File")
        self.btn_file.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        self.btn_file.clicked.connect(self.open_symbol_file)
        header_row.addWidget(self.btn_datasheet)
        header_row.addWidget(self.btn_file)
        selection_layout.addLayout(header_row)

        meta_row = QHBoxLayout()
        meta_row.setSpacing(10)
        self.lbl_file_path = QLabel("File: -")
        self.lbl_ds_path = QLabel("Datasheet: -")
        meta_row.addWidget(self.lbl_file_path, 1)
        meta_row.addWidget(self.lbl_ds_path, 1)
        selection_layout.addLayout(meta_row)

        proj_row = QHBoxLayout()
        proj_row.setSpacing(8)
        self.lbl_projects = QLabel("Projects")
        self.lbl_projects.setMinimumWidth(60)
        self.projects_list = QListWidget()
        self.projects_list.setMaximumHeight(90)
        self.projects_list.setFrameShape(QListWidget.NoFrame)
        self.projects_list.setFocusPolicy(Qt.NoFocus)
        self.projects_list.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.projects_list.setStyleSheet(
            "QListWidget { background: transparent; border: 1px solid rgba(151, 151, 151, 0.4); border-radius: 6px; padding: 4px; }"
            "QListWidget::item { padding: 2px 4px; }"
        )
        proj_row.addWidget(self.lbl_projects)
        proj_row.addWidget(self.projects_list, 1)
        selection_layout.addLayout(proj_row)

        panel_bg = "#FFFFFF" if theme == "Light" else "#23262B"
        panel_border = "#E1E6EC" if theme == "Light" else "#353A42"
        muted = "#6B7280" if theme == "Light" else "#9CA3AF"
        selection_panel.setStyleSheet(
            f"QWidget#selectionPanel {{ background: {panel_bg}; border: 1px solid {panel_border}; border-radius: 10px; }}"
        )
        chip_bg = "#F3F4F6" if theme == "Light" else "#2A2F36"
        chip_border = "#D0D5DD" if theme == "Light" else "#3B424D"
        for lbl in (self.lbl_file_path, self.lbl_ds_path):
            lbl.setStyleSheet(
                f"color: {muted}; font-size: 11px; background: {chip_bg}; border: 1px solid {chip_border}; "
                "border-radius: 7px; padding: 2px 6px;"
            )
            lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        if hasattr(self, "lbl_projects"):
            self.lbl_projects.setStyleSheet(f"color: {muted}; font-size: 11px; font-weight: 600;")
        heatmap_group = QGroupBox("Usage Heatmap")
        heatmap_layout = QVBoxLayout(heatmap_group)
        heatmap_layout.setContentsMargins(6, 4, 6, 6)
        heatmap_layout.setSpacing(4)
        self.usage_heatmap = QTableWidget(0, 3)
        self.usage_heatmap.setHorizontalHeaderLabels(["Project", "Uses", "Last Touched"])
        self.usage_heatmap.verticalHeader().setVisible(False)
        header = self.usage_heatmap.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.usage_heatmap.setEditTriggers(QTableWidget.NoEditTriggers)
        self.usage_heatmap.setSelectionMode(QTableWidget.NoSelection)
        self.usage_heatmap.setFocusPolicy(Qt.NoFocus)
        self.usage_heatmap.setWordWrap(False)
        self.usage_heatmap.setAlternatingRowColors(True)
        heatmap_layout.addWidget(self.usage_heatmap)
        selection_layout.addWidget(heatmap_group)
        selection_panel.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        selection_panel.setMaximumHeight(360)
        r_layout.addWidget(selection_panel)
        self._populate_project_usage([])
        self.update_usage_heatmap(None)
        
        # Visualizers Container
        preview_group = QGroupBox()
        preview_group.setObjectName("previewGroup")
        preview_group.setTitle("")
        preview_layout = QVBoxLayout(preview_group)
        preview_border = "#D6DCE5" if theme == "Light" else "#343B45"
        preview_group.setStyleSheet(
            f"QGroupBox#previewGroup {{ border: 1px solid {preview_border}; border-radius: 10px; margin-top: 0px; }}"
            "QGroupBox#previewGroup::title { subcontrol-origin: margin; subcontrol-position: top left; padding: 0px; }"
        )
        preview_group.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        preview_header = QHBoxLayout()
        preview_label = QLabel("Preview")
        preview_label.setStyleSheet("font-weight: 600;")
        preview_header.addWidget(preview_label)
        preview_header.addStretch()
        preview_layout.addLayout(preview_header)

        # Footprint Viewer Tab
        self.fp_tab_widget = QWidget()
        self.fp_tab_widget.setStyleSheet(preview_button_styles)
        fp_layout = QVBoxLayout(self.fp_tab_widget)
        fp_layout.setContentsMargins(0, 0, 0, 0)
        fp_layout.setSpacing(6)

        fp_ctrl = QHBoxLayout()
        fp_ctrl.addWidget(QLabel("Footprint"))

        self.btn_layers = QToolButton()
        self.btn_layers.setText("Layers v")
        self.btn_layers.setPopupMode(QToolButton.InstantPopup)
        self.layer_menu = QMenu(self.btn_layers)
        self.btn_layers.setMenu(self.layer_menu)
        self.btn_layers.setObjectName("fpCtrlButton")

        self.fp_view = getattr(self, "fp_view", FootprintWidget())

        self.layer_actions = {}
        self.layer_menus = {}

        act_show_all = self.layer_menu.addAction("Show All Layers")
        act_show_all.triggered.connect(self.show_all_layers)
        act_hide_all = self.layer_menu.addAction("Hide All Layers")
        act_hide_all.triggered.connect(self.hide_all_layers)
        act_reset_view = self.layer_menu.addAction("Reset View")
        act_reset_view.triggered.connect(lambda: self.fp_view.reset_view())
        act_reset_colors = self.layer_menu.addAction("Reset Layer Colors")
        act_reset_colors.triggered.connect(self.reset_layer_colors)
        self.layer_menu.addSeparator()

        for layer in self.fp_view.layer_colors.keys():
            sub = QMenu(layer, self.layer_menu)
            act_visible = QAction("Visible", self)
            act_visible.setCheckable(True)
            act_visible.setChecked(True)
            act_visible.triggered.connect(lambda checked, l=layer: self._toggle_layer_visible(l, checked))
            act_color = QAction("Set Color...", self)
            act_color.triggered.connect(lambda checked=False, l=layer: self.pick_layer_color(l))
            act_reset = QAction("Reset Color", self)
            act_reset.triggered.connect(lambda checked=False, l=layer: self.reset_layer_color(l))

            sub.addAction(act_visible)
            sub.addSeparator()
            sub.addAction(act_color)
            sub.addAction(act_reset)

            icon = self._layer_color_icon(self.fp_view.get_layer_color(layer))
            sub.setIcon(icon)
            act_visible.setIcon(icon)

            self.layer_menu.addMenu(sub)
            self.layer_actions[layer] = act_visible
            self.layer_menus[layer] = sub

        fp_ctrl.addWidget(self.btn_layers)

        btn_nums = QPushButton("123")
        btn_nums.setCheckable(True)
        btn_nums.setFixedWidth(35)
        btn_nums.setToolTip("Toggle Pad Numbers")
        btn_nums.toggled.connect(lambda c: self.fp_view.toggle_pad_numbers(c))
        btn_nums.setObjectName("fpCtrlButton")

        btn_fp_zin = QPushButton(); btn_fp_zin.setFixedWidth(28)
        btn_fp_zin.setIcon(Icons.get_icon(Icons.ZOOM_IN, icon_color))
        btn_fp_zin.setToolTip("Zoom In")
        btn_fp_zin.setObjectName("fpIconButton")
        btn_fp_zout = QPushButton(); btn_fp_zout.setFixedWidth(28)
        btn_fp_zout.setIcon(Icons.get_icon(Icons.ZOOM_OUT, icon_color))
        btn_fp_zout.setToolTip("Zoom Out")
        btn_fp_zout.setObjectName("fpIconButton")
        btn_fp_zout.clicked.connect(lambda: self.fp_view.zoom(0.8))
        btn_fp_rst = QPushButton(); btn_fp_rst.setFixedWidth(34)
        btn_fp_rst.setIcon(Icons.get_icon(Icons.RESET, icon_color))
        btn_fp_rst.setToolTip("Reset View")
        btn_fp_rst.setObjectName("fpIconButton")
        btn_measure = QPushButton("Measure"); btn_measure.setCheckable(True)
        btn_measure.setIcon(Icons.get_icon(Icons.MEASURE, icon_color))
        btn_measure.setObjectName("fpCtrlButton")
        fp_ctrl.addStretch()
        fp_ctrl.addWidget(btn_nums)
        fp_ctrl.addWidget(btn_measure)
        fp_ctrl.addWidget(btn_fp_zin)
        fp_ctrl.addWidget(btn_fp_zout)
        fp_ctrl.addWidget(btn_fp_rst)
        fp_layout.addLayout(fp_ctrl)

        btn_fp_zin.clicked.connect(lambda: self.fp_view.zoom(1.2))
        btn_fp_rst.clicked.connect(lambda: self.fp_view.reset_view())
        btn_measure.toggled.connect(self.fp_view.toggle_measure_mode)
        fp_layout.addWidget(self.fp_view, 1)

        self.sym_tab_widget = QWidget()
        sym_layout = QVBoxLayout(self.sym_tab_widget)
        sym_layout.setContentsMargins(0, 0, 0, 0)
        sym_layout.setSpacing(6)

        sym_ctrl = QHBoxLayout()
        sym_ctrl.addWidget(QLabel("Symbol"))
        btn_sym_zin = QPushButton()
        btn_sym_zin.setToolTip("Zoom In")
        btn_sym_zin.setFixedWidth(28)
        btn_sym_zin.setIcon(Icons.get_icon(Icons.ZOOM_IN, icon_color))
        btn_sym_zout = QPushButton()
        btn_sym_zout.setToolTip("Zoom Out")
        btn_sym_zout.setFixedWidth(28)
        btn_sym_zout.setIcon(Icons.get_icon(Icons.ZOOM_OUT, icon_color))
        btn_sym_rst = QPushButton()
        btn_sym_rst.setToolTip("Reset View")
        btn_sym_rst.setFixedWidth(34)
        btn_sym_rst.setIcon(Icons.get_icon(Icons.RESET, icon_color))
        sym_ctrl.addStretch()
        sym_ctrl.addWidget(btn_sym_zin)
        sym_ctrl.addWidget(btn_sym_zout)
        sym_ctrl.addWidget(btn_sym_rst)
        sym_layout.addLayout(sym_ctrl)

        self.sym_view = SymbolWidget()
        btn_sym_zin.clicked.connect(lambda: self.sym_view.zoom(1.2))
        btn_sym_zout.clicked.connect(lambda: self.sym_view.zoom(0.8))
        btn_sym_rst.clicked.connect(lambda: self.sym_view.reset_view())
        sym_layout.addWidget(self.sym_view, 1)

        self.model_preview = None
        self.model_tab_widget = QWidget()
        model_layout = QVBoxLayout(self.model_tab_widget)
        model_layout.setContentsMargins(0, 0, 0, 0)
        model_layout.setSpacing(6)
        model_header = QHBoxLayout()
        model_label = QLabel("3D Preview")
        model_label.setStyleSheet("font-weight: 600;")
        model_header.addWidget(model_label)
        model_header.addStretch()
        model_layout.addLayout(model_header)
        self.model_preview_container = QWidget()
        self.model_preview_container_layout = QVBoxLayout(self.model_preview_container)
        self.model_preview_container_layout.setContentsMargins(0, 0, 0, 0)
        self.model_preview_container_layout.setSpacing(0)
        self.model_preview_stack = QStackedWidget()
        self.model_preview_placeholder = QLabel("Select a component with a 3D model to preview it here.")
        self.model_preview_placeholder.setAlignment(Qt.AlignCenter)
        self.model_preview_placeholder.setStyleSheet(
            "color: #6B7280; font-style: italic; padding: 12px;"
        )
        self.model_preview_stack.addWidget(self.model_preview_placeholder)
        self.model_preview_container_layout.addWidget(self.model_preview_stack, 1)
        model_layout.addWidget(self.model_preview_container, 1)

        self.preview_tabs = QTabWidget()
        self.preview_tabs.setDocumentMode(True)
        self.preview_tabs.setTabPosition(QTabWidget.North)
        self.preview_tabs.setIconSize(QSize(20, 20))
        self.preview_tabs.setProperty("stretchTabs", True)
        self.preview_tabs.tabBar().setExpanding(True)
        self.preview_tabs.addTab(self.fp_tab_widget, Icons.get_icon(Icons.TOOL, icon_color), "Footprint")
        self.preview_tabs.addTab(self.sym_tab_widget, Icons.get_icon(Icons.CHIP, icon_color), "Symbol")
        self.preview_tabs.addTab(self.model_tab_widget, Icons.get_icon(Icons.MECHANICAL, icon_color), "3D")

        self.pin_table = QTableWidget(0, 4)
        self.pin_table.setHorizontalHeaderLabels(["Pin", "Name", "Type", "Pad"])
        self.pin_table.horizontalHeader().setStretchLastSection(True)
        self.pin_table.verticalHeader().setVisible(False)
        self.pin_table.setAlternatingRowColors(True)

        pin_panel = QWidget()
        pin_layout = QVBoxLayout(pin_panel)
        pin_layout.setContentsMargins(0, 0, 0, 0)
        pin_layout.setSpacing(4)
        pin_header = QHBoxLayout()
        pin_label = QLabel("Pinout")
        pin_label.setStyleSheet("font-weight: 600;")
        pin_header.addWidget(pin_label)
        pin_header.addStretch()
        pin_layout.addLayout(pin_header)
        pin_layout.addWidget(self.pin_table)

        vis_split = QSplitter(Qt.Vertical)
        vis_split.setChildrenCollapsible(False)
        vis_split.addWidget(self.preview_tabs)
        vis_split.addWidget(pin_panel)
        vis_split.setStretchFactor(0, 3)
        vis_split.setStretchFactor(1, 1)
        vis_split.setSizes([520, 180])
        preview_layout.addWidget(vis_split)
        # Properties
        self.prop_table = QTableWidget(0, 2)
        self.prop_table.setHorizontalHeaderLabels(["Property", "Value"])
        prop_header = self.prop_table.horizontalHeader()
        prop_header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        prop_header.setSectionResizeMode(1, QHeaderView.Stretch)
        prop_header.setStretchLastSection(False)
        self.prop_table.setWordWrap(True)
        self.prop_table.verticalHeader().setVisible(False)
        self.prop_table.setAlternatingRowColors(True)
        self.prop_table.setStyleSheet(
            "QTableWidget::item { padding: 6px 4px; }"
            "QTableWidget::item:selected { background-color: rgba(59, 113, 246, 0.2); }"
        )

        card_bg = "#FFFFFF" if theme == "Light" else "#23262B"
        card_border = "#E1E6EC" if theme == "Light" else "#353A42"

        prop_card = QWidget()
        prop_card.setObjectName("propCard")
        prop_card.setStyleSheet(f"QWidget#propCard {{ background: {card_bg}; border: 1px solid {card_border}; border-radius: 10px; }}")
        prop_layout = QVBoxLayout(prop_card)
        prop_layout.setContentsMargins(10, 8, 10, 10)
        prop_header = QLabel("Properties")
        prop_header.setStyleSheet("font-weight: 600;")
        prop_layout.addWidget(prop_header)
        prop_layout.addWidget(self.prop_table, 1)

        content_split = QSplitter(Qt.Horizontal)
        content_split.setChildrenCollapsible(False)
        content_split.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        content_split.addWidget(preview_group)
        content_split.addWidget(prop_card)
        content_split.setStretchFactor(0, 4)
        content_split.setStretchFactor(1, 1)
        content_split.setSizes([900, 320])

        r_layout.addWidget(content_split, 1)
        
        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([460, 1120])
        layout.addWidget(splitter, 1)

        self.left_tabs.currentChanged.connect(self._on_left_tab_changed)
        self._on_left_tab_changed(self.left_tabs.currentIndex())


    def _report_warning(self, message):
        warning_center.add_warning(message, fix_callback=self._open_symbol_path_settings, fix_label="Open Settings")
        window = self.window()
        if window and hasattr(window, "status_bar"):
            window.status_bar.showMessage(message, 5000)

    def _open_symbol_path_settings(self):
        window = self.window()
        if not window or not hasattr(window, "settings_view"):
            return
        if hasattr(window, "tabs"):
            window.tabs.setCurrentWidget(window.settings_view)
        settings_view = window.settings_view
        if hasattr(settings_view, "tabs") and hasattr(settings_view, "page_general"):
            settings_view.tabs.setCurrentWidget(settings_view.page_general)
            inputs = getattr(settings_view.page_general, "inputs", {})
            edit = inputs.get("symbol_path")
            if edit:
                edit.setFocus()
                edit.selectAll()

    def run_scan(self):
        raw_path = self.logic.settings.get("symbol_path", "")
        roots = self.logic.resolve_path_list(raw_path)
        valid_roots = [str(p) for p in roots if p and os.path.exists(p)]
        if not valid_roots:
            detail = ", ".join(str(p) for p in roots) if roots else raw_path
            msg = "Path error: select a valid Symbol Library Path in Settings."
            if detail:
                msg = f"{msg} (Resolved: {detail})"
            self._report_warning(msg)
            return

        if self._scan_in_progress:
            return
        self._scan_in_progress = True
        self.lbl_scan_status.setText("Status: Scanning...")
        self.btn_scan.setEnabled(False)
        self.btn_scan.setText("Scanning...")
        
        # Start Background Thread
        self.worker = ScanWorker(self.logic, valid_roots, self)
        self.worker.finished.connect(self.on_scan_finished)
        self.worker.error.connect(self.on_scan_error)
        self.worker.start()

    def on_scan_finished(self, count):
        self.refresh_data()
        self._scan_in_progress = False
        self.btn_scan.setEnabled(True)
        self.btn_scan.setText(f"Loaded {count} Libs")
        QTimer.singleShot(3000, lambda: self.btn_scan.setText("Rescan Libraries"))
        self.lbl_scan_status.setText(f"Last scan: {datetime.now().strftime('%H:%M:%S')}")
        if self.chk_auto_rescan.isChecked():
            self.setup_watcher()

    def on_scan_error(self, err):
        self._scan_in_progress = False
        self.btn_scan.setEnabled(True); self.btn_scan.setText("Rescan Libraries")
        self.lbl_scan_status.setText("Status: Error")
        self._report_warning(f"Symbol scan error: {err}")
        QMessageBox.critical(self, "Scan Error", f"An error occurred:\n{err}")

    def toggle_auto_rescan(self, checked):
        if checked:
            self.setup_watcher()
        else:
            self.fs_watcher.removePaths(self.fs_watcher.directories())

    def setup_watcher(self):
        self.fs_watcher.removePaths(self.fs_watcher.directories())
        dirs = set()
        sym_roots = self.logic.resolve_path_list(self.logic.settings.get("symbol_path", ""))
        fp_roots = self.logic.resolve_path_list(self.logic.settings.get("footprint_path", ""))
        for root in sym_roots + fp_roots:
            if not root or not os.path.exists(root):
                continue
            try:
                for dirpath, dirnames, filenames in os.walk(root):
                    dirs.add(dirpath)
            except Exception:
                dirs.add(root)
        if dirs:
            self.fs_watcher.addPaths(sorted(dirs))
            self.lbl_scan_status.setText("Status: Watching for changes")

    def on_fs_change(self, _):
        if not self.chk_auto_rescan.isChecked():
            return
        self._auto_scan_timer.start(1500)

    def _trigger_auto_scan(self):
        if self._scan_in_progress:
            return
        self.run_scan()

    def search_online(self):
        text, ok = QInputDialog.getText(self, "Search Online", "Enter Part Number or Keyword:")
        if ok and text:
            QDesktopServices.openUrl(QUrl(f"https://octopart.com/search?q={text}"))

    def refresh_data(self):
        self.model.removeRows(0, self.model.rowCount())
        libs = []
        for lib, parts in self.logic.data_store.items():
            libs.append(lib)
            for name, data in parts.items():
                if not isinstance(data, dict):
                    continue
                file_path = data.get("file_path", "")
                data["file_path"] = self.logic.resolve_path(file_path)
                data["library"] = lib
                data["name"] = name
                datasheet = data.get("properties", {}).get("Datasheet", "")
                if datasheet and not datasheet.lower().startswith(("http://", "https://")):
                    data.setdefault("properties", {})["Datasheet"] = self.logic.resolve_path(datasheet)
                i_lib = QStandardItem(lib)
                i_name = QStandardItem(name)
                i_pins = QStandardItem(); i_pins.setData(len(data.get("pins", [])), Qt.DisplayRole)
                
                uid = f"{lib}:{name}"
                usage_count = len(self.logic.project_manager.project_index.get(uid, []))
                i_usage = QStandardItem(); i_usage.setData(usage_count, Qt.DisplayRole)
                if usage_count == 0: i_usage.setForeground(QColor("orange")) 
                
                i_name.setData(data, Qt.UserRole)
                self.model.appendRow([i_lib, i_name, i_pins, i_usage])
        self._refresh_symbol_lib_combo(libs)
        self.refresh_footprints()
        self.apply_filters()
        if self.proxy.rowCount() == 0:
            self.sym_stack.setCurrentWidget(self.sym_empty)
        else:
            self.sym_stack.setCurrentWidget(self.tree)

    def refresh_footprints(self):
        self.fp_model.removeRows(0, self.fp_model.rowCount())
        fp_roots = self.logic.resolve_path_list(self.logic.settings.get("footprint_path", ""))
        if not fp_roots or not any(os.path.exists(p) for p in fp_roots):
            self.fp_stack.setCurrentWidget(self.fp_empty)
            return

        self.logic.scan_footprint_libraries()
        fp_lib_map = self.logic.footprint_lib_map or {}
        if isinstance(fp_lib_map, dict) and "libraries" in fp_lib_map and isinstance(fp_lib_map["libraries"], dict):
            fp_lib_map = fp_lib_map["libraries"]
        fp_libs = []
        for lib, lib_path in sorted(fp_lib_map.items()):
            fp_libs.append(lib)
            if not lib_path or not os.path.exists(lib_path):
                continue
            for fp_file in Path(lib_path).rglob("*.kicad_mod"):
                name = fp_file.stem
                pads_count, has_model = self._quick_fp_stats(fp_file)
                i_lib = QStandardItem(lib)
                i_name = QStandardItem(name)
                i_pads = QStandardItem()
                i_pads.setData(pads_count, Qt.DisplayRole)
                i_model = QStandardItem("Yes" if has_model else "No")
                ref = f"{lib}:{name}"
                i_name.setData(
                    {"lib": lib, "name": name, "ref": ref, "file_path": str(fp_file)},
                    Qt.UserRole,
                )
                part_refs = self.logic.project_manager.get_parts_using_footprint(ref)
                if part_refs:
                    preview = ", ".join(part_refs[:3])
                    suffix = "..." if len(part_refs) > 3 else ""
                    usage_text = f"{len(part_refs)} part{'s' if len(part_refs) != 1 else ''} ({preview}{suffix})"
                    tooltip = ", ".join(part_refs)
                else:
                    usage_text = "Unused"
                    tooltip = "No parts found"
                usage_item = QStandardItem(usage_text)
                usage_item.setToolTip(tooltip)
                self.fp_model.appendRow([i_lib, i_name, i_pads, i_model, usage_item])
        self._refresh_fp_lib_combo(fp_libs)
        if self.fp_proxy.rowCount() == 0:
            self.fp_stack.setCurrentWidget(self.fp_empty)
        else:
            self.fp_stack.setCurrentWidget(self.fp_tree)

    def _refresh_symbol_lib_combo(self, libs):
        current = self.sym_lib_combo.currentText() if hasattr(self, "sym_lib_combo") else ""
        self.sym_lib_combo.blockSignals(True)
        self.sym_lib_combo.clear()
        self.sym_lib_combo.addItem("All Libraries")
        for lib in sorted(set(libs)):
            self.sym_lib_combo.addItem(lib)
        if current:
            idx = self.sym_lib_combo.findText(current)
            if idx >= 0:
                self.sym_lib_combo.setCurrentIndex(idx)
        self.sym_lib_combo.blockSignals(False)

    def _refresh_fp_lib_combo(self, libs):
        current = self.fp_lib_combo.currentText() if hasattr(self, "fp_lib_combo") else ""
        self.fp_lib_combo.blockSignals(True)
        self.fp_lib_combo.clear()
        self.fp_lib_combo.addItem("All Libraries")
        for lib in sorted(set(libs)):
            self.fp_lib_combo.addItem(lib)
        if current:
            idx = self.fp_lib_combo.findText(current)
            if idx >= 0:
                self.fp_lib_combo.setCurrentIndex(idx)
        self.fp_lib_combo.blockSignals(False)

    def _populate_project_usage(self, projects):
        self.projects_list.clear()
        if not projects:
            item = QListWidgetItem("Not used in any project")
            item.setFlags(Qt.NoItemFlags)
            self.projects_list.addItem(item)
            return
        for proj in projects:
            self.projects_list.addItem(proj)

    def update_usage_heatmap(self, key):
        self.usage_heatmap.setRowCount(0)
        if not key:
            self._set_heatmap_empty("Select a part to view its usage across projects.")
            return
        stats = self.logic.get_part_usage_stats(key)
        if not stats:
            self._set_heatmap_empty("No projects reuse this component yet.")
            return
        max_count = max(item["count"] for item in stats) or 1
        for row, stat in enumerate(stats):
            self.usage_heatmap.insertRow(row)
            project_item = QTableWidgetItem(stat["project"])
            project_item.setToolTip(stat["path"] or stat["project"])
            count_item = QTableWidgetItem(str(stat["count"]))
            count_item.setTextAlignment(Qt.AlignCenter)
            last = stat["last_touched"] or "Never"
            last_item = QTableWidgetItem(last)
            last_item.setTextAlignment(Qt.AlignCenter)
            self.usage_heatmap.setItem(row, 0, project_item)
            self.usage_heatmap.setItem(row, 1, count_item)
            self.usage_heatmap.setItem(row, 2, last_item)
            intensity = min(1.0, stat["count"] / max_count)
            base = 240 - int(120 * intensity)
            color = QColor(255, base, base)
            for col in range(3):
                item = self.usage_heatmap.item(row, col)
                if item:
                    item.setBackground(color)

    def _set_heatmap_empty(self, message):
        self.usage_heatmap.setRowCount(1)
        colspan = self.usage_heatmap.columnCount()
        placeholder = QTableWidgetItem(message)
        placeholder.setTextAlignment(Qt.AlignCenter)
        placeholder.setFlags(Qt.NoItemFlags)
        self.usage_heatmap.setItem(0, 0, placeholder)
        for col in range(1, colspan):
            self.usage_heatmap.setItem(0, col, QTableWidgetItem())
        self.usage_heatmap.setSpan(0, 0, 1, colspan)

    def _quick_fp_stats(self, fp_file):
        pads_count = 0
        has_model = False
        try:
            with open(fp_file, "r", encoding="utf-8", errors="ignore") as f:
                text = f.read()
            pads_count = len(re.findall(r"\(pad\\s", text))
            has_model = "(model " in text
        except Exception:
            pads_count = 0
            has_model = False
        return pads_count, has_model

    def update_fp_layer_visibility(self):
        """Updates the visible layers in the footprint widget based on checkbox state."""
        visible = {layer for layer, act in self.layer_actions.items() if act.isChecked()}
        self.fp_view.set_visible_layers(visible)

    def _on_left_tab_changed(self, index):
        if not hasattr(self, "preview_tabs"):
            return
        if index == 1:
            self.preview_tabs.setCurrentWidget(self.fp_tab_widget)
        else:
            self.preview_tabs.setCurrentWidget(self.sym_tab_widget)

    def _toggle_layer_visible(self, layer, checked):
        act = self.layer_actions.get(layer)
        if act:
            act.setChecked(checked)
        self.update_fp_layer_visibility()

    def show_all_layers(self):
        for act in self.layer_actions.values():
            act.setChecked(True)
        self.update_fp_layer_visibility()

    def hide_all_layers(self):
        for act in self.layer_actions.values():
            act.setChecked(False)
        self.update_fp_layer_visibility()

    def pick_layer_color(self, layer):
        current = self.fp_view.get_layer_color(layer)
        color = QColorDialog.getColor(current, self, f"Select {layer} Color")
        if color.isValid():
            self.fp_view.set_layer_color(layer, color)
            self._refresh_layer_icons(layer)

    def reset_layer_color(self, layer):
        self.fp_view.reset_layer_colors(layer)
        self._refresh_layer_icons(layer)

    def reset_layer_colors(self):
        self.fp_view.reset_layer_colors()
        self._refresh_layer_icons()

    def _layer_color_icon(self, color):
        pix = QPixmap(16, 16)
        pix.fill(color)
        return QIcon(pix)

    def _refresh_layer_icons(self, layer=None):
        if layer:
            color = self.fp_view.get_layer_color(layer)
            icon = self._layer_color_icon(color)
            if layer in self.layer_actions:
                self.layer_actions[layer].setIcon(icon)
            if layer in self.layer_menus:
                self.layer_menus[layer].setIcon(icon)
            return
        for l in self.layer_actions.keys():
            color = self.fp_view.get_layer_color(l)
            icon = self._layer_color_icon(color)
            self.layer_actions[l].setIcon(icon)
            if l in self.layer_menus:
                self.layer_menus[l].setIcon(icon)

    def apply_filters(self):
        txt = self.search_main.text()
        self.proxy.setTextFilter(txt)
        self.proxy.setLibraryFilter(self.sym_lib_combo.currentText())
        self.proxy.setShowOrphans(self.filter_orphan.isChecked())
        self.proxy.setRequireFootprint(self.chk_has_fp.isChecked())
        self.proxy.setRequireDatasheet(self.chk_has_ds.isChecked())
        self.proxy.setMinPins(self.spin_min_pins.value())

        self.fp_proxy.setTextFilter(txt)
        self.fp_proxy.setLibraryFilter(self.fp_lib_combo.currentText())
        self.fp_proxy.setRequire3D(self.chk_fp_3d.isChecked())
        self.fp_proxy.setMinPads(self.spin_min_pads.value())

        if hasattr(self, "sym_count_label"):
            try:
                self.sym_count_label.setText(f"{self.proxy.rowCount()} / {self.model.rowCount()}")
            except Exception:
                pass
        if hasattr(self, "sym_stack"):
            if self.proxy.rowCount() == 0:
                self.sym_stack.setCurrentWidget(self.sym_empty)
            else:
                self.sym_stack.setCurrentWidget(self.tree)
        if hasattr(self, "fp_count_label"):
            try:
                self.fp_count_label.setText(f"{self.fp_proxy.rowCount()} / {self.fp_model.rowCount()}")
            except Exception:
                pass
        if hasattr(self, "fp_stack"):
            if self.fp_proxy.rowCount() == 0:
                self.fp_stack.setCurrentWidget(self.fp_empty)
            else:
                self.fp_stack.setCurrentWidget(self.fp_tree)

    def on_select(self, selected, deselected):
        idx = selected.indexes()
        if not idx: return
        src_idx = self.proxy.mapToSource(idx[0])
        item = self.model.item(src_idx.row(), 1) 
        data = item.data(Qt.UserRole)
        if not data:
            self.update_usage_heatmap(None)
            return

        self.pin_table.setHorizontalHeaderLabels(["Pin", "Name", "Type", "Pad"])
        
        self.lbl_part.setText(f"{data['library']} : {data['name']}")

        if hasattr(self, "sym_view"):
            self.sym_view.set_data(data)
        if hasattr(self, "preview_tabs") and hasattr(self, "sym_tab_widget"):
            self.preview_tabs.setCurrentWidget(self.sym_tab_widget)

        # Update Actions
        self.current_datasheet = data.get("properties", {}).get("Datasheet", "")
        self.current_filepath = data.get("file_path", "")
        self.btn_datasheet.setEnabled(bool(self.current_datasheet and self.current_datasheet != "~"))
        self.btn_file.setEnabled(bool(self.current_filepath))
        
        # Try to resolve footprint geometry if available
        fp_ref = data.get("properties", {}).get("Footprint", "")
        geom = self.logic.get_footprint_data(fp_ref) or {}
        self.fp_view.set_data(geom)
        self.update_fp_layer_visibility() # Apply current visibility settings
        self._update_model_preview(geom, f"{data['library']}:{data['name']}")
        
        # Populate Pinout Table
        self.pin_table.setRowCount(0)
        pins = data.get("pins", [])
        pads = geom.get("pads", [])
        
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
        self.lbl_file_path.setText(f"File: {os.path.basename(self.current_filepath) or 'None'}")
        self.lbl_file_path.setToolTip(self.current_filepath or "")
        ds_label = self.current_datasheet or "None"
        self.lbl_ds_path.setText(f"Datasheet: {ds_label}")
        self.lbl_ds_path.setToolTip(self.current_datasheet or "")
        uid = f"{data.get('library', '')}:{data.get('name', '')}"
        projects = list(self.logic.project_manager.project_index.get(uid, []))
        self._populate_project_usage(projects)
        self.update_usage_heatmap(uid)

    def on_select_footprint(self, selected, deselected):
        idx = selected.indexes()
        if not idx:
            return
        src_idx = self.fp_proxy.mapToSource(idx[0])
        item = self.fp_model.item(src_idx.row(), 1)
        data = item.data(Qt.UserRole) or {}
        lib = data.get("lib", "")
        name = data.get("name", "")
        ref = data.get("ref", "")

        self.lbl_part.setText(f"Footprint: {lib} : {name}")
        if hasattr(self, "sym_view"):
            self.sym_view.set_data(None)
        if hasattr(self, "preview_tabs"):
            self.preview_tabs.setCurrentWidget(self.fp_tab_widget)

        self.current_datasheet = ""
        self.current_filepath = data.get("file_path", "")
        self.btn_datasheet.setEnabled(False)
        self.btn_file.setEnabled(bool(self.current_filepath))
        projects = self.logic.project_manager.get_projects_using_footprint(ref)
        self._populate_project_usage(projects)
        self.update_usage_heatmap(ref if ref else None)

        geom = self.logic.get_footprint_data(ref)
        self.fp_view.set_data(geom)
        self.update_fp_layer_visibility()
        self._update_model_preview(geom, ref)

        # Update pad table
        self.pin_table.setHorizontalHeaderLabels(["Pad", "Type", "Shape", "Size"])
        self.pin_table.setRowCount(0)
        pads = geom.get("pads", []) if geom else []
        for p in pads:
            row = self.pin_table.rowCount()
            self.pin_table.insertRow(row)
            num = p.get("number", "")
            self.pin_table.setItem(row, 0, QTableWidgetItem(num))
            self.pin_table.setItem(row, 1, QTableWidgetItem(p.get("type", "")))
            self.pin_table.setItem(row, 2, QTableWidgetItem(p.get("shape", "")))
            size = p.get("size", [])
            size_txt = f"{size[0]} x {size[1]}" if size and len(size) >= 2 else ""
            self.pin_table.setItem(row, 3, QTableWidgetItem(size_txt))

        # Properties
        self.prop_table.setRowCount(0)
        if geom:
            props = {
                "Pads": str(len(geom.get("pads", []))),
                "Lines": str(len(geom.get("lines", []))),
                "Model": geom.get("model_file") or geom.get("model_path") or "",
                "File": geom.get("file_path") or self.current_filepath,
            }
            for k, v in props.items():
                r = self.prop_table.rowCount()
                self.prop_table.insertRow(r)
                self.prop_table.setItem(r, 0, QTableWidgetItem(k))
                self.prop_table.setItem(r, 1, QTableWidgetItem(str(v)))
            file_path = data.get("file_path", "")
            file_label = os.path.basename(file_path) or "None"
            self.lbl_file_path.setText(f"Footprint File: {file_label}")
            self.lbl_file_path.setToolTip(file_path or "")
            self.lbl_ds_path.setText("Datasheet: None")
            self.lbl_ds_path.setToolTip("")

            # Update row details in list (pads / 3d)
            pads_item = self.fp_model.item(src_idx.row(), 2)
            model_item = self.fp_model.item(src_idx.row(), 3)
            if pads_item:
                pads_item.setText(str(len(geom.get("pads", []))))
            if model_item:
                model_item.setText("Yes" if geom.get("model_path") else "No")
        else:
            self.lbl_file_path.setText("Footprint File: None")
            self.lbl_file_path.setToolTip("")
            self.lbl_ds_path.setText("Datasheet: None")
            self.lbl_ds_path.setToolTip("")
            self._populate_project_usage([])

    def open_datasheet(self):
        if self.current_datasheet:
            QDesktopServices.openUrl(QUrl(self.current_datasheet))

    def open_symbol_file(self):
        if self.current_filepath and os.path.exists(self.current_filepath):
            QDesktopServices.openUrl(QUrl.fromLocalFile(self.current_filepath))

    def _update_model_preview(self, geom, reference):
        bounds = self.fp_view.get_content_bounds()
        model_path = (geom.get("model_file") or geom.get("model_path")) if geom else ""
        if not model_path:
            if self.model_preview_stack:
                self.model_preview_stack.setCurrentWidget(self.model_preview_placeholder)
            return
        self._ensure_model_preview_widget()
        self.model_preview_stack.setCurrentWidget(self.model_preview)
        self.model_preview.set_model_info(bounds, model_path, reference)

    def _ensure_model_preview_widget(self):
        if self.model_preview is not None:
            return
        self.model_preview = ModelPreviewWidget()
        self.model_preview_stack.addWidget(self.model_preview)
        self.model_preview_stack.setCurrentWidget(self.model_preview)

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

    def show_fp_context_menu(self, pos):
        idx = self.fp_tree.indexAt(pos)
        if not idx.isValid():
            return
        menu = QMenu()
        act_copy = menu.addAction("Copy Reference")
        action = menu.exec(self.fp_tree.viewport().mapToGlobal(pos))
        if action == act_copy:
            src_idx = self.fp_proxy.mapToSource(idx)
            txt = f"{self.fp_model.item(src_idx.row(), 0).text()}:{self.fp_model.item(src_idx.row(), 1).text()}"
            QApplication.clipboard().setText(txt)

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)
