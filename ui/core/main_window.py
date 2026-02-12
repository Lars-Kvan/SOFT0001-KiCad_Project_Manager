from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTabBar,
    QTabWidget,
    QStatusBar,
    QFrame,
    QLabel,
    QTextEdit,
    QSizePolicy,
    QDialog,
    QScrollArea,
    QToolButton,
    QGraphicsDropShadowEffect,
)
from PySide6.QtCore import (
    Qt,
    QSize,
    Signal,
    QTimer,
    QEvent,
    QVariantAnimation,
)
from PySide6.QtGui import QKeySequence, QShortcut, QFontMetrics, QIcon, QColor, QPainter, QFont

import platform
import html
import sys
from datetime import datetime

from ui.dialogs.action_palette import ActionPalette
from ui.dialogs.feature_request import FeatureRequestDialog
from ui.resources.styles import Styles
from ui.resources.icons import Icons
from ui.widgets.elevation import apply_layered_elevation
from ui.widgets.modal_utils import apply_modal_style
from ui.core.warning_center import warning_center
from ui.views.ui_project import ProjectManagerTab
from ui.views.ui_explorer import ExplorerTab
from ui.views.ui_settings import SettingsTab
from ui.views.ui_git import GitTab, GitOverviewTab, LibraryGitTab
from ui.views.ui_validation import ValidationTab
from ui.views.ui_dashboard import DashboardTab
from ui.views.ui_notebook import NotebookTab
from ui.views.ui_doc_manager import DocumentManagerTab
from ui.views.time_tracker_tab import TimeTrackerTab
from ui.views.parts_view import PartsView


_DARK_THEMES = {"Dark", "Teal Sand Dark"}
_MAIN_TAB_BASE_COLORS = [
    "#4F46E5",
    "#2563EB",
    "#0EA5E9",
    "#14B8A6",
]
_INDICATOR_WIDTH = 4


def _gradient_for_color(color):
    base = QColor(color)
    start = base.lighter(135).name()
    end = base.darker(115).name()
    return f"qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 {start}, stop:1 {end})"


def icon_color_for_theme(theme: str) -> str:
    return "#E0E0E0" if theme in _DARK_THEMES else "#444444"


def main_tab_icon_color(theme: str = "Light") -> str:
    theme = theme or "Light"
    return "#E6ECF6" if theme in _DARK_THEMES else "#2C2A27"


def _adjust_color(hex_color: str, factor: float) -> str:
    color = QColor(hex_color)
    if factor >= 1.0:
        r = int(color.red() + (255 - color.red()) * (factor - 1.0))
        g = int(color.green() + (255 - color.green()) * (factor - 1.0))
        b = int(color.blue() + (255 - color.blue()) * (factor - 1.0))
    else:
        r = int(color.red() * factor)
        g = int(color.green() * factor)
        b = int(color.blue() * factor)
    r = max(0, min(255, r))
    g = max(0, min(255, g))
    b = max(0, min(255, b))
    return QColor(r, g, b).name()





class ClickableFrame(QFrame):
    clicked = Signal()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)


class MainWindow(QMainWindow):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self._was_maximized = False
        self._shortcuts = []
        self.setObjectName("mainWindow")
        self.setWindowTitle("KiCad Project Manager")
        self.resize(1280, 800)
        self.setup_ui()

    def setup_ui(self):
        self._build_central_widget()
        self._build_section_header()
        self._build_bug_panel()
        self._build_tabs()
        self._build_status_bar()
        self._install_shortcuts()
        self._install_button_hover_effects()

    def _build_central_widget(self):
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)

        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 10, 20, 20)
        self.main_layout.setSpacing(12)



    def _build_bug_panel(self):
        self.bug_panel = QFrame()
        self.bug_panel.setObjectName("bugPanel")
        self.bug_panel.setFrameShape(QFrame.StyledPanel)
        self.bug_panel.setVisible(False)
        self.bug_panel.setStyleSheet("QFrame#bugPanel { border: 1px solid #e0e0e0; border-radius: 8px; }")

        panel_layout = QVBoxLayout(self.bug_panel)
        panel_layout.setContentsMargins(10, 8, 10, 8)
        panel_layout.setSpacing(6)

        lbl_title = QLabel("Report a bug")
        lbl_title.setStyleSheet("font-weight: bold;")
        panel_layout.addWidget(lbl_title)

        self.bug_text = QTextEdit()
        self.bug_text.setPlaceholderText("Describe the issue...")
        self.bug_text.setMinimumHeight(90)
        panel_layout.addWidget(self.bug_text)

        self.bug_status = QLabel("")
        self.bug_status.setStyleSheet("color: #888; font-size: 11px;")
        panel_layout.addWidget(self.bug_status)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        btn_submit = QPushButton("Submit")
        btn_submit.clicked.connect(self.submit_bug_report)
        btn_cancel = QPushButton("Close")
        btn_cancel.clicked.connect(self.hide_bug_panel)
        btn_row.addWidget(btn_submit)
        btn_row.addWidget(btn_cancel)
        panel_layout.addLayout(btn_row)

        self.main_layout.addWidget(self.bug_panel)

    def _build_section_header(self):
        self.section_header = QFrame()
        self.section_header.setObjectName("sectionHeader")
        header_layout = QHBoxLayout(self.section_header)
        header_layout.setContentsMargins(20, 8, 20, 8)
        header_layout.setSpacing(12)

        self.section_icon = QLabel()
        self.section_icon.setObjectName("sectionIcon")
        self.section_icon.setFixedSize(24, 24)
        header_layout.addWidget(self.section_icon, 0, Qt.AlignVCenter)

        info_layout = QVBoxLayout()
        info_layout.setContentsMargins(0, 0, 0, 0)
        info_layout.setSpacing(0)

        self.section_title = QLabel("Overview")
        self.section_title.setObjectName("sectionTitle")
        self.section_title.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        info_layout.addWidget(self.section_title)

        self.section_subtitle = QLabel("Live overview of current workspaces")
        self.section_subtitle.setObjectName("sectionSubtitle")
        self.section_subtitle.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        info_layout.addWidget(self.section_subtitle)

        header_layout.addLayout(info_layout, 1)
        header_layout.addStretch()

        self.btn_bug = QPushButton("Report Bug")
        self.btn_bug.setIcon(Icons.get_icon(Icons.BUG, "#e74c3c"))
        self.btn_bug.setStyleSheet("border: none; background: transparent; padding: 0px; text-align: left;")
        self.btn_bug.clicked.connect(self.toggle_bug_panel)
        header_layout.addWidget(self.btn_bug)

        self.btn_feature = QPushButton("Request Feature")
        self.btn_feature.setIcon(Icons.get_icon(Icons.EDIT, "#27ae60"))
        self.btn_feature.setStyleSheet("border: none; background: transparent; padding: 0px; text-align: left;")
        self.btn_feature.clicked.connect(self.open_feature_request_dialog)
        header_layout.addWidget(self.btn_feature)

        self.main_layout.addWidget(self.section_header)

    def _build_tabs(self):
        self.tabs = QTabWidget()
        self.tabs.setObjectName("mainTabs")
        self.tabs.tabBar().setObjectName("mainTabBar")
        self.tabs.setIconSize(QSize(20, 20))
        self.tabs.setMovable(False)
        self.tabs.setUsesScrollButtons(True)
        self.tabs.tabBar().setExpanding(False)
        self.tabs.tabBar().setElideMode(Qt.ElideRight)
        self.tabs.tabBar().hide()
        self._ensure_valid_tabbar_font(self.tabs.tabBar())
        self.tabs.currentChanged.connect(self._on_main_tab_changed)

        self.nav_frame = QFrame()
        self.nav_frame.setObjectName("mainNav")
        self.nav_frame.setFixedWidth(240)
        self.nav_layout = QVBoxLayout(self.nav_frame)
        self.nav_layout.setContentsMargins(12, 12, 12, 12)
        self.nav_layout.setSpacing(8)
        self.nav_layout.setAlignment(Qt.AlignTop)
        self.nav_layout.addStretch()
        self.nav_buttons = []

        self.tabs_container = QFrame()
        self.tabs_container.setObjectName("tabsContainer")
        tabs_container_layout = QHBoxLayout(self.tabs_container)
        tabs_container_layout.setContentsMargins(0, 0, 0, 0)
        tabs_container_layout.setSpacing(16)
        tabs_container_layout.addWidget(self.nav_frame)
        tabs_container_layout.addWidget(self.tabs, 1)

        self.main_layout.addWidget(self.tabs_container)
        self.create_tabs()
        self._setup_tab_order_guard()
        self._update_nav_buttons()

    def _add_nav_button(self, tab_index):
        button = QToolButton()
        button.setObjectName("navButton")
        button.setProperty("rounded", True)
        button.setCheckable(True)
        button.setAutoExclusive(True)
        button.setCursor(Qt.PointingHandCursor)
        button.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        button.setIconSize(QSize(24, 24))
        button.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        button.setMinimumHeight(64)
        font = button.font()
        font.setPointSize(13)
        font.setWeight(QFont.DemiBold if hasattr(QFont, "DemiBold") else QFont.Bold)
        button.setFont(font)
        button.clicked.connect(lambda _, idx=tab_index: self.tabs.setCurrentIndex(idx))
        insert_index = max(0, self.nav_layout.count() - 1)
        self.nav_layout.insertWidget(insert_index, button)
        self.nav_buttons.append(button)
        return button

    def _update_nav_buttons(self):
        if not hasattr(self, "nav_buttons"):
            return
        current_index = self.tabs.currentIndex()
        for idx, button in enumerate(self.nav_buttons):
            if idx >= self.tabs.count():
                button.hide()
                continue
            button.show()
            button.setIcon(self.tabs.tabIcon(idx))
            button.setText(self.tabs.tabText(idx))
            button.setToolTip(self.tabs.tabToolTip(idx) or "")
            accent = self._tab_accent_color(idx)
            active = idx == current_index
            button.setChecked(active)
            button.setProperty("active", active)
            button.setProperty("accent", accent)
            button.setStyleSheet(self._nav_button_stylesheet(accent, active))
            button.style().unpolish(button)
            button.style().polish(button)

    def _build_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        self._status_error_timer = QTimer(self)
        self._status_error_timer.setSingleShot(True)
        self._status_error_timer.timeout.connect(self._reset_status_style)
        self._build_warning_indicator()

    def _build_warning_indicator(self):
        self.warning_indicator = ClickableFrame()
        self.warning_indicator.setObjectName("warningIndicator")
        layout = QHBoxLayout(self.warning_indicator)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.setSpacing(6)

        self.warning_icon = QLabel()
        self.warning_icon.setObjectName("warningIcon")
        self.warning_text = QLabel("Warnings: 0")
        self.warning_text.setObjectName("warningText")

        layout.addWidget(self.warning_icon)
        layout.addWidget(self.warning_text)

        self.warning_indicator.setVisible(False)
        self.status_bar.addPermanentWidget(self.warning_indicator)

        warning_center.warnings_changed.connect(self._on_warnings_changed)
        self.warning_indicator.clicked.connect(self._show_warning_dialog)
        self.warning_indicator.setCursor(Qt.PointingHandCursor)
        self._update_warning_indicator_theme()
        self._on_warnings_changed(warning_center.count(), warning_center.latest())

    def _warning_palette(self):
        theme = self.logic.settings.get("theme", "Light")
        if theme in _DARK_THEMES:
            return "#6B2D2D", "rgba(231, 76, 60, 60)", "#FFB3B3", "#E67E22", "#E74C3C"
        return "#F3A2A2", "rgba(231, 76, 60, 45)", "#7D1F1F", "#D97706", "#E74C3C"

    def _update_warning_indicator_theme(self):
        if not hasattr(self, "warning_indicator"):
            return
        border, bg, text, icon_color, badge = self._warning_palette()
        self.warning_indicator.setStyleSheet(
            f"QFrame#warningIndicator {{ border: 1px solid {border}; border-radius: 10px; background-color: {bg}; }}"
            f" QLabel#warningText {{ color: {text}; font-weight: 700; background-color: {badge}; padding: 1px 6px; border-radius: 7px; }}"
        )
        self.warning_icon.setPixmap(Icons.get_icon(Icons.WARNING, icon_color).pixmap(16, 16))

    def _on_warnings_changed(self, count, latest):
        if count <= 0:
            self.warning_indicator.setVisible(False)
            self.warning_indicator.setToolTip("No warnings")
            return
        self.warning_indicator.setVisible(True)
        self.warning_text.setText(f"Warnings: {count}")
        if latest:
            self.warning_indicator.setToolTip(latest)
            self._show_status_error(latest, 5000)
        if getattr(self, "_warning_dialog", None) and self._warning_dialog.isVisible():
            self._refresh_warning_dialog()

    def _show_status_error(self, message, timeout=5000):
        self.status_bar.showMessage(message, timeout)
        self.status_bar.setStyleSheet("QStatusBar { color: #E74C3C; font-weight: 600; }")
        if self._status_error_timer:
            self._status_error_timer.start(timeout)

    def _reset_status_style(self):
        self.status_bar.setStyleSheet("")

    def _show_warning_dialog(self):
        if not getattr(self, "_warning_dialog", None) or not getattr(self, "_warning_list_layout", None):
            self._create_warning_dialog()

        refreshed = self._refresh_warning_dialog()
        if not refreshed and not getattr(self, "_warning_dialog", None):
            self._create_warning_dialog()
            refreshed = self._refresh_warning_dialog()
        if not refreshed:
            return

        self._warning_dialog.show()
        self._warning_dialog.raise_()
        self._warning_dialog.activateWindow()

    def _create_warning_dialog(self):
        if getattr(self, "_warning_dialog", None):
            self._warning_dialog.deleteLater()
        self._warning_dialog = QDialog(self)
        self._warning_dialog.setWindowTitle("Warnings")
        self._warning_dialog.setModal(False)
        self._warning_dialog.resize(520, 320)

        layout = QVBoxLayout(self._warning_dialog)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self._warning_list_container = QWidget()
        self._warning_list_layout = QVBoxLayout(self._warning_list_container)
        self._warning_list_layout.setContentsMargins(0, 0, 0, 0)
        self._warning_list_layout.setSpacing(6)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        scroll.setWidget(self._warning_list_container)
        layout.addWidget(scroll)

        btn_row = QHBoxLayout()
        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self._warning_dialog.close)
        self._btn_clear_warnings = QPushButton("Clear Warnings")
        self._btn_clear_warnings.clicked.connect(warning_center.clear)
        self._btn_copy_warnings = QPushButton("Copy Warnings")
        self._btn_copy_warnings.clicked.connect(self._copy_warnings_to_clipboard)
        btn_row.addWidget(btn_close)
        btn_row.addStretch()
        btn_row.addWidget(self._btn_clear_warnings)
        btn_row.addWidget(self._btn_copy_warnings)
        layout.addLayout(btn_row)
        apply_modal_style(self._warning_dialog, title="Warnings", accent="#E74C3C")
        self._warning_dialog.destroyed.connect(self._reset_warning_dialog_refs)

    def _reset_warning_dialog_refs(self, obj=None):
        self._warning_dialog = None
        self._warning_list_layout = None
        self._warning_list_container = None

    def _refresh_warning_dialog(self):
        layout = getattr(self, "_warning_list_layout", None)
        if layout is None:
            return False
        try:
            self._clear_layout(layout)
        except RuntimeError:
            self._reset_warning_dialog_refs()
            return False
        warnings = warning_center.all()
        if not warnings:
            empty = QLabel("No warnings.")
            empty.setStyleSheet("color: #888;")
            self._warning_list_layout.addWidget(empty)
            return True
        for warn in warnings:
            row = QFrame()
            row.setObjectName("warningRow")
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(8, 6, 8, 6)
            row_layout.setSpacing(8)

            message_text = warn.get("message", "")
            msg = QLabel()
            msg.setWordWrap(True)
            msg.setTextInteractionFlags(Qt.TextBrowserInteraction)
            msg.setOpenExternalLinks(False)
            row_layout.addWidget(msg, 1)

            fix_label = warn.get("fix_label") or "Fix"
            fix_btn = QToolButton()
            fix_btn.setText(fix_label)
            fix_btn.setCursor(Qt.PointingHandCursor)
            fix_btn.setAutoRaise(True)
            fix_btn.setStyleSheet(
                "QToolButton { color: #1E6BD6; border: none; text-decoration: underline; }"
                "QToolButton:hover { color: #0F4EA8; }"
            )
            callback = warn.get("fix_callback")
            if callback:
                msg.setText(f'<a href="fix">{html.escape(message_text)}</a>')
                msg.setStyleSheet("color: #1E6BD6;")
                msg.linkActivated.connect(lambda _=None, cb=callback: cb())
                fix_btn.clicked.connect(callback)
            else:
                msg.setText(message_text)
                msg.setTextInteractionFlags(Qt.TextSelectableByMouse)
                fix_btn.setEnabled(False)
            row_layout.addWidget(fix_btn, 0, Qt.AlignRight | Qt.AlignVCenter)

            self._warning_list_layout.addWidget(row)
        self._warning_list_layout.addStretch()
        return True

    def _copy_warnings_to_clipboard(self):
        warnings = warning_center.all()
        if not warnings:
            return
        lines = []
        for warn in warnings:
            msg = warn.get("message", "").strip()
            if msg:
                lines.append(f"- {msg}")
        if not lines:
            return
        text = "\n".join(lines)
        QApplication.clipboard().setText(text)
        self.status_bar.showMessage("Warnings copied to clipboard", 2500)

    @staticmethod
    def _clear_layout(layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                MainWindow._clear_layout(item.layout())

    def _install_shortcuts(self):
        self._shortcuts = [
            QShortcut(
                QKeySequence("Ctrl+Tab"),
                self,
                lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() + 1) % self.tabs.count()),
            ),
            QShortcut(
                QKeySequence("Ctrl+Shift+Tab"),
                self,
                lambda: self.tabs.setCurrentIndex((self.tabs.currentIndex() - 1) % self.tabs.count()),
            ),
            QShortcut(QKeySequence("Ctrl+K"), self, self.show_action_palette),
            QShortcut(QKeySequence("F11"), self, self.toggle_fullscreen),
        ]
        for shortcut in self._shortcuts:
            shortcut.setContext(Qt.ApplicationShortcut)

    def toggle_fullscreen(self):
        state = self.windowState()
        if state & Qt.WindowFullScreen:
            state &= ~Qt.WindowFullScreen
            if self._was_maximized:
                state |= Qt.WindowMaximized
        else:
            self._was_maximized = bool(state & Qt.WindowMaximized)
            state &= ~Qt.WindowMaximized
            state |= Qt.WindowFullScreen
        self.setWindowState(state)
        self.show()

    def create_tabs(self):
        self.dashboard_view = DashboardTab(self.logic)
        self.project_view = ProjectManagerTab(self.logic)
        self.validation_view = ValidationTab(self.logic)
        self.explorer_view = ExplorerTab(self.logic)
        self.git_view = GitOverviewTab(self.logic)
        self.parts_view = PartsView(self.logic)
        self.settings_view = SettingsTab(self.logic)
        self.settings_view.settings_saved.connect(self._on_settings_saved)
        self.notebook_view = NotebookTab(self.logic)
        self.doc_view = DocumentManagerTab(self.logic)
        self.time_view = TimeTrackerTab(self.logic)

        self.dashboard_view.request_project_load.connect(self.load_project_from_dashboard)
        self.dashboard_view.request_new_project.connect(self.initiate_new_project)
        self.project_view.project_selected.connect(self.git_view.set_repo_path)
        self.settings_view.theme_changed.connect(self.on_theme_changed)

        icon_color = main_tab_icon_color(self.logic.settings.get("theme", "Light"))

        dash_idx = self.tabs.addTab(self.dashboard_view, Icons.get_icon(Icons.DASHBOARD, icon_color), "Dashboard")
        self._set_tab_accent(dash_idx, self._main_tab_color(dash_idx))
        self._add_nav_button(dash_idx)
        proj_idx = self.tabs.addTab(self.project_view, Icons.get_icon(Icons.PROJECTS_MAIN, icon_color), "Projects")
        self._set_tab_accent(proj_idx, self._main_tab_color(proj_idx))
        self._add_nav_button(proj_idx)

        self.lib_manager = QWidget()
        l_lib = QVBoxLayout(self.lib_manager)
        l_lib.setContentsMargins(0, 0, 0, 0)
        self.lib_tabs = QTabWidget()
        self.lib_tabs.setIconSize(QSize(20, 20))
        self._ensure_valid_tabbar_font(self.lib_tabs.tabBar())
        lib_icon_color = icon_color_for_theme(self.logic.settings.get("theme", "Light"))
        self.lib_tabs.addTab(self.explorer_view, Icons.get_icon(Icons.SEARCH, lib_icon_color), "Explorer")
        self.lib_tabs.addTab(self.validation_view, Icons.get_icon(Icons.DOC, lib_icon_color), "Validation")
        self.lib_git_view = LibraryGitTab(self.logic)
        self.lib_tabs.addTab(self.lib_git_view, Icons.get_icon(Icons.GIT, lib_icon_color), "Library Git")
        l_lib.addWidget(self.lib_tabs)
        lib_idx = self.tabs.addTab(self.lib_manager, Icons.get_icon(Icons.LIBRARY, icon_color), "Library")
        self._set_tab_accent(lib_idx, self._main_tab_color(lib_idx))
        self._add_nav_button(lib_idx)

        parts_idx = self.tabs.addTab(self.parts_view, Icons.get_icon(Icons.CHIP, icon_color), "Parts")
        self._set_tab_accent(parts_idx, self._main_tab_color(parts_idx))
        self._add_nav_button(parts_idx)

        git_idx = self.tabs.addTab(self.git_view, Icons.get_icon(Icons.GIT, icon_color), "Git")
        self._set_tab_accent(git_idx, self._main_tab_color(git_idx))
        self._add_nav_button(git_idx)
        note_idx = self.tabs.addTab(self.notebook_view, Icons.get_icon(Icons.NOTEBOOK, icon_color), "Notebook")
        self._set_tab_accent(note_idx, self._main_tab_color(note_idx))
        self._add_nav_button(note_idx)
        doc_idx = self.tabs.addTab(self.doc_view, Icons.get_icon(Icons.DOCUMENTS, icon_color), "Documents")
        self._set_tab_accent(doc_idx, self._main_tab_color(doc_idx))
        self._add_nav_button(doc_idx)
        time_idx = self.tabs.addTab(self.time_view, Icons.get_icon(Icons.CLOCK, icon_color), "Time Tracking")
        self._set_tab_accent(time_idx, self._main_tab_color(time_idx))
        self._add_nav_button(time_idx)

        settings_idx = self.tabs.addTab(self.settings_view, Icons.get_icon(Icons.SETTINGS, icon_color), "Settings")
        self._set_tab_accent(settings_idx, self._main_tab_color(settings_idx))
        self._add_nav_button(settings_idx)

        self._refresh_main_tab_icons()

    def _set_tab_accent(self, index, color):
        bar = self.tabs.tabBar()
        if bar is None:
            return
        data = bar.tabData(index)
        if isinstance(data, dict):
            data["accent"] = color
        else:
            data = {"accent": color}
        bar.setTabData(index, data)

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

    def load_project_from_dashboard(self, project_name, task_name=""):
        self.tabs.setCurrentIndex(1)
        list_widget = self.project_view.list_paths
        for i in range(list_widget.count()):
            item = list_widget.item(i)
            if item.data(Qt.UserRole) == project_name:
                list_widget.setCurrentItem(item)
                break

        if task_name:
            self.project_view.highlight_kanban_task(task_name)

    def initiate_new_project(self):
        self.tabs.setCurrentIndex(1)
        self.project_view.add_project()

    def _on_settings_saved(self):
        if hasattr(self.project_view, "status_view"):
            self.project_view.status_view.refresh_status_options()

    def closeEvent(self, event):
        self._shutdown_views(event)
        if self.logic.settings.get("backup", {}).get("backup_on_exit", False):
            self.logic.perform_backup(force=True)
        event.accept()

    def _shutdown_views(self, event):
        views = [
            self.dashboard_view,
            self.project_view,
            self.explorer_view,
            self.validation_view,
            self.parts_view,
            self.git_view,
            self.notebook_view,
            self.doc_view,
            self.time_view,
        ]
        for view in views:
            try:
                if hasattr(view, "closeEvent"):
                    view.closeEvent(event)
                else:
                    view.close()
            except Exception:
                pass

    def toggle_bug_panel(self):
        if self.bug_panel.isVisible():
            self.hide_bug_panel()
        else:
            self.bug_panel.setVisible(True)
            self.bug_text.setFocus()

    def open_feature_request_dialog(self):
        dlg = FeatureRequestDialog(self)
        if dlg.exec():
            self.status_bar.showMessage("Feature request saved.", 4000)

    def hide_bug_panel(self):
        self.bug_panel.setVisible(False)
        self.bug_text.clear()
        self.bug_status.setText("")

    def submit_bug_report(self):
        text = self.bug_text.toPlainText().strip()
        if not text:
            self.bug_status.setText("Please enter a description.")
            self.status_bar.showMessage("Bug report: description required.", 4000)
            return

        try:
            sys_info = f"System: {platform.system()} {platform.release()}\n"
            sys_info += f"Python: {sys.version}\n"
            sys_info += f"Platform: {platform.platform()}\n"

            with open("bugs.txt", "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(f"{sys_info}\nUser Report:\n{text}\n{'-' * 50}\n")

            self.bug_status.setText("Saved to bugs.txt")
            self.status_bar.showMessage("Bug report saved.", 4000)
            self.bug_text.clear()
        except Exception as exc:
            self.bug_status.setText(f"Failed to save: {exc}")
            self.status_bar.showMessage("Bug report failed to save.", 4000)

    def on_theme_changed(self):
        self._refresh_main_tab_icons()
        self._update_warning_indicator_theme()
        self._update_section_header()

    def toggle_theme(self):
        current = self.logic.settings.get("theme", "Light")
        new_theme = "Dark" if current == "Light" else "Light"
        self.logic.settings["theme"] = new_theme
        self.logic.save_settings()
        Styles.apply_theme(
            QApplication.instance(),
            new_theme,
            self.logic.settings.get("ui_scale", 100),
            self.logic.settings.get("ui_font", None),
        )
        self.on_theme_changed()

    def _refresh_main_tab_icons(self):
        if not hasattr(self, "tabs"):
            return
        theme = self.logic.settings.get("theme", "Light")
        icon_color = main_tab_icon_color(theme)
        tabs = [
            (self.dashboard_view, Icons.DASHBOARD, "Dashboard"),
            (self.project_view, Icons.PROJECTS_MAIN, "Projects"),
            (self.lib_manager, Icons.LIBRARY, "Library"),
            (self.parts_view, Icons.CHIP, "Parts"),
            (self.git_view, Icons.GIT, "Git"),
            (self.notebook_view, Icons.NOTEBOOK, "Notebook"),
            (self.doc_view, Icons.DOCUMENTS, "Documents"),
            (self.time_view, Icons.CLOCK, "Time Tracking"),
            (self.settings_view, Icons.SETTINGS, "Settings"),
        ]
        for widget, icon_name, text in tabs:
            idx = self.tabs.indexOf(widget)
            if idx >= 0:
                self.tabs.setTabIcon(idx, Icons.get_icon(icon_name, icon_color))
                self.tabs.setTabText(idx, text)

        self._apply_main_tab_colors()
        self._update_nav_buttons()

    def _apply_main_tab_colors(self):
        # Accent colors are managed through tabData during tab creation.
        return

    def show_action_palette(self):
        actions = [
            ("New Project", self.project_view.add_project),
            ("Refresh Project List", self.project_view.refresh_paths),
            ("Open Requirements", lambda: self._open_project_subtab(self.project_view.req_view)),
            ("Open Kanban", lambda: self._open_project_subtab(self.project_view.tab_kanban)),
            ("Run Validation", self.validation_view.run_validation),
            ("Rescan Libraries", self.explorer_view.run_scan),
            ("Generate BOM", self.project_view.bom_tab.generate),
            ("Backup Now", lambda: self.logic.perform_backup(force=True)),
            ("Open Documents", lambda: self.tabs.setCurrentWidget(self.doc_view)),
            ("Open Time Tracker", lambda: self.tabs.setCurrentWidget(self.time_view)),
            ("Open Git", lambda: self.tabs.setCurrentWidget(self.git_view)),
            ("Open Parts", lambda: self.tabs.setCurrentWidget(self.parts_view)),
            ("Toggle Theme", self.toggle_theme),
            ("Toggle Fullscreen", self.toggle_fullscreen),
        ]
        dlg = ActionPalette(self, actions=actions)
        dlg.exec()

    def _open_project_subtab(self, widget):
        self.tabs.setCurrentWidget(self.project_view)
        if hasattr(self.project_view, "sub_tabs"):
            self.project_view.sub_tabs.setCurrentWidget(widget)

    def _setup_tab_order_guard(self):
        self._tab_move_guard = False
        self._tab_reorder_timer = QTimer(self)
        self._tab_reorder_timer.setSingleShot(True)
        self._tab_reorder_timer.timeout.connect(self._ensure_settings_tab_last)
        self.tabs.tabBar().tabMoved.connect(self._on_tab_moved)
        self._ensure_settings_tab_last()

    def _on_main_tab_changed(self, _index):
        # Force immediate repaint so selected tab highlight updates without lag.
        bar = self.tabs.tabBar()
        bar.update()
        bar.repaint()
        self._update_section_header()
        self._update_nav_buttons()

    def _tab_accent_color(self, index):
        if index < 0:
            return _MAIN_TAB_BASE_COLORS[0] if _MAIN_TAB_BASE_COLORS else "#16A34A"
        bar = self.tabs.tabBar()
        if bar is not None:
            data = bar.tabData(index)
            if isinstance(data, dict):
                accent = data.get("accent")
                if accent:
                    return accent
        return self._main_tab_color(index)
        return "#16A34A"

    def _nav_button_stylesheet(self, accent, active):
        theme = self.logic.settings.get("theme", "Light")
        is_dark = theme in _DARK_THEMES
        accent_color = QColor(accent or _MAIN_TAB_BASE_COLORS[0] if _MAIN_TAB_BASE_COLORS else "#2563EB")

        active_background = _gradient_for_color(accent_color.name())
        active_border = accent_color.darker(125).name()
        active_hover = accent_color.lighter(140).name()

        neutral_bg = "#0F172A" if is_dark else "#F8FAFC"
        neutral_border = "#1F2937" if is_dark else "#E2E8F0"
        neutral_hover = "#171A24" if is_dark else "#F1F5F9"
        inactive_text = "#E2E8F0" if is_dark else "#475569"

        bg_color = active_background if active else neutral_bg
        border_color = active_border if active else neutral_border
        text_color = "#F8FAFC" if active else inactive_text
        hover_color = active_hover if active else neutral_hover

        return (
            "QToolButton#navButton {"
            f" background: {bg_color};"
            f" color: {text_color};"
            f" border: 1px solid {border_color};"
            " border-radius: 16px;"
            " padding: 18px 16px;"
            " text-align: left;"
            " letter-spacing: 0.08em;"
            "}"
            "QToolButton#navButton::menu-indicator {"
            " subcontrol-origin: padding;"
            " subcontrol-position: right center;"
            "}"
            "QToolButton#navButton:hover {"
            f" background: {hover_color};"
            "}"
            f"QToolButton#navButton:!checked {{ color: {inactive_text}; }}"
        )

    def _current_tab_accent_color(self, index):
        return self._tab_accent_color(index)

    def _main_tab_color(self, index):
        if not _MAIN_TAB_BASE_COLORS:
            return "#16A34A"
        return _MAIN_TAB_BASE_COLORS[index % len(_MAIN_TAB_BASE_COLORS)]

    def _section_text_color(self):
        return "#F8FAFC" if self.logic.settings.get("theme", "Light") in _DARK_THEMES else "#0F172A"

    def _update_section_header(self):
        if not hasattr(self, "section_header"):
            return
        idx = self.tabs.currentIndex()
        title = self.tabs.tabToolTip(idx) or self.tabs.tabText(idx) or "Overview"
        accent = self._current_tab_accent_color(idx)

        theme = self.logic.settings.get("theme", "Light")
        is_dark = theme in _DARK_THEMES

        bg_color = QColor("#F8F5F0") if not is_dark else QColor("#1E1E1E")
        header_bg = bg_color.lighter(105 if is_dark else 102).name()
        border_color = bg_color.lighter(115 if is_dark else 108).name()

        text_color = self._section_text_color()
        subtitle_color = QColor(text_color)
        subtitle_color.setAlphaF(0.7)

        subtitle_map = {
            "Dashboard": "Live overview of projects, tasks, and libraries",
            "Projects": "Track your Kanban, metadata, and status",
            "Library Manager": "Browse, validate, and inspect symbols/footprints",
            "Parts": "Search parts, compare versions, and export BOMs",
            "Git": "Stage, commit, and sync project repositories",
            "Notebook": "Capture notes, docs, and rough sketches",
            "Documents": "Store specs, datasheets, and reference files",
            "Time Tracking": "Log work hours, and export timesheets",
            "Settings": "Configure preferences, backups, and integrations",
        }
        subtitle = subtitle_map.get(title, "Navigate your primary workspaces")

        self.section_title.setText(title)
        self.section_subtitle.setText(subtitle)

        self.section_header.setStyleSheet(
            f"""
            QFrame#sectionHeader {{
                background-color: {header_bg};
                border: 1px solid {border_color};
                border-radius: 12px;
            }}"""
        )

        title_font = self.section_title.font()
        title_font.setPointSizeF(12)
        title_font.setWeight(QFont.DemiBold if hasattr(QFont, "DemiBold") else QFont.Bold)
        self.section_title.setFont(title_font)
        self.section_title.setStyleSheet(f"color: {text_color}; letter-spacing: -0.5px;")

        subtitle_font = self.section_subtitle.font()
        subtitle_font.setPointSizeF(9)
        self.section_subtitle.setFont(subtitle_font)
        self.section_subtitle.setStyleSheet(f"color: rgba({subtitle_color.red()}, {subtitle_color.green()}, {subtitle_color.blue()}, {int(subtitle_color.alphaF() * 255)});")

        # Update Icon
        icon_map = {
            "Dashboard": Icons.DASHBOARD,
            "Projects": Icons.PROJECTS_MAIN,
            "Library Manager": Icons.LIBRARY,
            "Parts": Icons.CHIP,
            "Git": Icons.GIT,
            "Notebook": Icons.NOTEBOOK,
            "Documents": Icons.DOCUMENTS,
            "Time Tracking": Icons.CLOCK,
            "Settings": Icons.SETTINGS,
        }
        icon_name = icon_map.get(title, Icons.DASHBOARD)
        if hasattr(self, "section_icon"):
            self.section_icon.setPixmap(Icons.get_icon(icon_name, accent).pixmap(24, 24))

    def _on_tab_moved(self, _from_index, _to_index):
        if hasattr(self, "_tab_reorder_timer"):
            self._tab_reorder_timer.start(75)
        else:
            self._ensure_settings_tab_last()

    def _ensure_settings_tab_last(self):
        if not hasattr(self, "tabs") or not hasattr(self, "settings_view"):
            return
        if self._tab_move_guard:
            return
        self._tab_move_guard = True
        try:
            settings_idx = self.tabs.indexOf(self.settings_view)
            if settings_idx < 0:
                return
            last = self.tabs.count() - 1
            if settings_idx != last:
                self._move_tab_to(self.settings_view, last)
        finally:
            self._tab_move_guard = False

    def _install_button_hover_effects(self):
        for btn in self.findChildren(QPushButton):
            btn.setAttribute(Qt.WA_Hover, True)
            btn.installEventFilter(self)

    def eventFilter(self, obj, event):
        if isinstance(obj, QPushButton):
            if event.type() == QEvent.Enter:
                self._apply_button_hover(obj, entering=True)
            elif event.type() == QEvent.Leave:
                self._apply_button_hover(obj, entering=False)
        return super().eventFilter(obj, event)

    def _apply_button_hover(self, button, entering):
        button.setProperty("hovered", entering)
        if entering:
            effect = QGraphicsDropShadowEffect(button)
            effect.setBlurRadius(16)
            effect.setOffset(0, 8)
            effect.setColor(QColor(15, 118, 110, 120))
            button.setGraphicsEffect(effect)
        else:
            button.setGraphicsEffect(None)
        button.style().unpolish(button)
        button.style().polish(button)

    def _move_tab_to(self, widget, new_index):
        current_index = self.tabs.indexOf(widget)
        if current_index < 0 or current_index == new_index:
            return
        icon = self.tabs.tabIcon(current_index)
        text = self.tabs.tabText(current_index)
        tooltip = self.tabs.tabToolTip(current_index)
        enabled = self.tabs.isTabEnabled(current_index)
        tab_data = None
        if hasattr(self.tabs, "tabBar"):
            tab_data = self.tabs.tabBar().tabData(current_index)
        current_widget = self.tabs.currentWidget()

        # Adjust target index after removal if needed.
        if current_index < new_index:
            new_index -= 1

        self.tabs.removeTab(current_index)
        self.tabs.insertTab(new_index, widget, icon, text)
        self.tabs.setTabToolTip(new_index, tooltip)
        self.tabs.setTabEnabled(new_index, enabled)
        if tab_data is not None:
            self.tabs.tabBar().setTabData(new_index, tab_data)
        if current_widget is widget:
            self.tabs.setCurrentWidget(widget)
