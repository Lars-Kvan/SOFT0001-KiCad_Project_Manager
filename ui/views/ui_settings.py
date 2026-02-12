from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QListWidget, QListWidgetItem, QStackedWidget, QFrame,
                               QSizePolicy, QLineEdit, QCompleter)
from PySide6.QtCore import Qt, Signal, QTimer, QSize, QStringListModel
try:
    from ..resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons
from .settings_pages import GeneralSettingsPage, ProjectConfigPage, KanbanSettingsPage, BackupSettingsPage
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.toast import show_toast

class SettingsTab(QWidget):
    settings_saved = Signal()
    theme_changed = Signal()
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.inputs = {}
        self.setup_ui()

    def setup_ui(self):
        root = QVBoxLayout(self)
        apply_layout(root, margin=PAGE_PADDING, spacing="sm")

        layout = QHBoxLayout()
        root.addLayout(layout, 1)

        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        is_dark = theme in ["Dark"]

        bg_color = "#18181b" if is_dark else "#f4f4f5"
        item_hover = "#27272a" if is_dark else "#e4e4e7"
        item_selected = "#3f3f46" if is_dark else "#d4d4d8"

        # Left: Navigation
        nav = QFrame()
        nav.setObjectName("settingsNav")
        nav_layout = QVBoxLayout(nav)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)
        nav.setMinimumWidth(280)
        nav.setStyleSheet(
            f"""
            #settingsNav {{
                background-color: {bg_color};
                border-right: 1px solid {item_selected};
            }}
            QWidget#settingsNavItem {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(255, 255, 255, 0.4), stop:1 rgba(255, 255, 255, 0.15));
                border-radius: 18px;
                padding: 12px 14px;
                border: 1px solid rgba(255, 255, 255, 0.25);
                min-height: 68px;
            }}
            QWidget#settingsNavItem[selected="true"] {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #2563EB, stop:1 #1e40af);
                border-color: #1e40af;
            }}
            QWidget#settingsNavItem QLabel {{
                color: #e5e7eb;
            }}
            QWidget#settingsNavItem[selected="true"] QLabel {{
                color: #ffffff;
            }}
            """
        )

        search_row = QHBoxLayout()
        lbl_search = QLabel("Search settings:")
        lbl_search.setStyleSheet("font-weight: 600;")
        search_row.addWidget(lbl_search)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search settings (e.g. kanban templates, git path)")
        self.search_input.setClearButtonEnabled(True)
        self.search_input.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        search_row.addWidget(self.search_input)
        nav_layout.addLayout(search_row)

        self.nav_list = QListWidget()
        self.nav_list.setSpacing(4)
        self.nav_list.setSelectionMode(QListWidget.SingleSelection)
        self.nav_list.currentRowChanged.connect(self._on_nav_changed)
        self.nav_list.setStyleSheet(
            """
            QListWidget { background: transparent; border: none; outline: none; }
            QListWidget::item { padding: 0; margin: 0; }
            QListWidget::item:selected { background: transparent; }
            """
        )
        nav_layout.addWidget(self.nav_list, 1)
        layout.addWidget(nav)
        self.nav_items = []

        # Right: Pages
        right = QVBoxLayout()
        self.pages = QStackedWidget()
        right.addWidget(self.pages, 1)

        save_row = QHBoxLayout()
        btn_save = QPushButton("Save All Settings")
        btn_save.setObjectName("btnPrimary")
        btn_save.clicked.connect(self.save)
        save_row.addStretch()
        save_row.addWidget(btn_save)
        right.addLayout(save_row)

        self.lbl_status = QLabel("")
        self.lbl_status.setStyleSheet("color: #2ecc71; font-weight: 600;")
        self.lbl_status.setAlignment(Qt.AlignLeft)
        right.addWidget(self.lbl_status)

        layout.addLayout(right, 1)

        # Pages
        self.page_general = GeneralSettingsPage(self.logic)
        self.page_proj = ProjectConfigPage(self.logic)
        self.page_kanban = KanbanSettingsPage(self.logic)
        self.page_backup = BackupSettingsPage(self.logic)
        self.pages.addWidget(self.page_general)
        self.pages.addWidget(self.page_proj)
        self.pages.addWidget(self.page_kanban)
        self.pages.addWidget(self.page_backup)

        self.page_general.theme_changed.connect(self.theme_changed)

        self._add_nav_item("General", "Paths, tools, theme, API keys", Icons.SETTINGS, icon_color)
        self._add_nav_item("Project Configuration", "Types, checklists, templates", Icons.PROJECTS, icon_color)
        self._add_nav_item("Kanban Settings", "Columns, categories, weights", Icons.NOTEBOOK, icon_color)
        self._add_nav_item("Auto Backup", "Backup schedule and restores", Icons.SAVE, icon_color)

        self.nav_list.setCurrentRow(0)

    def _add_nav_item(self, title, desc, icon_name, icon_color):
        item = QListWidgetItem()
        widget = QWidget()
        widget.setAttribute(Qt.WA_TransparentForMouseEvents)
        v = QVBoxLayout(widget)
        v.setContentsMargins(8, 6, 8, 6)
        v.setSpacing(2)
        lbl_title = QLabel(title)
        lbl_title.setStyleSheet("font-weight: 600;")
        lbl_title.setWordWrap(True)
        lbl_desc = QLabel(desc)
        lbl_desc.setStyleSheet("color: #888; font-size: 11px;")
        lbl_desc.setWordWrap(True)
        lbl_title.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        lbl_desc.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        v.addWidget(lbl_title)
        v.addWidget(lbl_desc)
        widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        widget.adjustSize()
        widget.setObjectName("settingsNavItem")
        item.setSizeHint(QSize(widget.sizeHint().width(), widget.sizeHint().height() + 4))
        item.setIcon(Icons.get_icon(icon_name, icon_color))
        self.nav_list.addItem(item)
        self.nav_list.setItemWidget(item, widget)
        self.nav_items.append(widget)
        widget.setProperty("selected", False)

    def _on_nav_changed(self, index):
        if index >= 0:
            self.pages.setCurrentIndex(index)
            self._update_nav_selection(index)

    def _update_nav_selection(self, active_index):
        for idx, widget in enumerate(self.nav_items):
            selected = idx == active_index
            widget.setProperty("selected", selected)
            widget.style().unpolish(widget)
            widget.style().polish(widget)

    def save(self):
        self.page_general.save_settings()
        self.page_proj.save_settings()
        self.page_kanban.save_settings()
        self.page_backup.save_settings()
        
        self.logic.save_settings()
        self.lbl_status.setText("Settings saved.")
        show_toast(self, "Settings saved", 2000, "success")
        QTimer.singleShot(4000, lambda: self.lbl_status.setText(""))
        self.settings_saved.emit()
