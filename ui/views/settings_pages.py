import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QPushButton,
    QGroupBox, QLabel, QComboBox, QFrame, QFileDialog, QMessageBox, QCheckBox,
    QSpinBox, QDoubleSpinBox, QPlainTextEdit, QListWidget, QListWidgetItem, QInputDialog,
    QColorDialog, QTabWidget, QFontComboBox, QMenu, QButtonGroup, QToolButton
)
from PySide6.QtGui import QColor, QIcon, QPixmap, QDesktopServices, QFont
from PySide6.QtCore import Qt, QSize, QUrl, Signal
from ..widgets.spacing import SPACING
from ..widgets.toast import show_toast
from kanban_templates import (
    format_template_entry,
    normalize_template_list,
    parse_template_line,
)

PROJECT_STATUS_DEFAULTS = [
    "Pre-Design",
    "Schematic Capture",
    "PCB Layout",
    "Prototyping",
    "Validation",
    "Released",
    "Abandoned",
]
def _build_template_map(raw_templates):
    normalized = {k: normalize_template_list(v) for k, v in raw_templates.items()}
    normalized.setdefault("Standard", [])
    return normalized


def _template_lines(entries):
    if not entries:
        return ""
    return "\n".join(format_template_entry(entry) for entry in entries if entry.get("name"))


def _parse_template_editor(text):
    entries = []
    for line in text.splitlines():
        parsed = parse_template_line(line)
        if parsed:
            entries.append(parsed)
    return entries
try:
    from ..widgets.checklist_widget import ChecklistWidget
except ImportError:
    from ui.widgets.checklist_widget import ChecklistWidget
try:
    from ..resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons

class GeneralSettingsPage(QWidget):
    theme_changed = Signal()
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.inputs = {}
        self._input_min_w = 320
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        form_fr = QFrame(); form = QFormLayout(form_fr)
        self._apply_form_style(form)
        self.add_row(
            form,
            "Symbol Path:",
            "symbol_path",
            help_text="Semicolon-separated list of KiCad symbol library folders.",
        )
        self.add_row(
            form,
            "Footprint Path:",
            "footprint_path",
            help_text="Semicolon-separated list of KiCad footprint library folders.",
        )
        self.add_row(
            form,
            "Base Directory:",
            "path_root",
            placeholder="Used for ${BASE_DIR} in paths",
            help_text="Root used for placeholder expansion and relative path resolution.",
        )
        layout.addWidget(form_fr)
        
        gb_tools = QGroupBox("External Tools")
        form_tools = QFormLayout(gb_tools)
        self._apply_form_style(form_tools)
        self.add_tool_row(
            form_tools,
            "Text Editor Executable:",
            "editor",
            help_text="Optional. Used by quick-open actions.",
        )
        self.add_tool_row(
            form_tools,
            "KiCad Executable:",
            "kicad",
            help_text="Optional. Used by launch actions.",
        )
        layout.addWidget(gb_tools)

        # API Keys
        gb_api = QGroupBox("Supplier API Keys")
        form_api = QFormLayout(gb_api)
        self._apply_form_style(form_api)
        self.add_row(form_api, "DigiKey Client ID:", "api_digikey_id")
        self.add_row(form_api, "DigiKey Client Secret:", "api_digikey_secret")
        self.add_row(form_api, "Mouser API Key:", "api_mouser_key")
        self.add_row(form_api, "LCSC Customer ID:", "api_lcsc_id")
        self.add_row(form_api, "Arrow API Key:", "api_arrow_key")
        self.add_row(form_api, "TME Token:", "api_tme_token")
        self.add_row(form_api, "Farnell API Key:", "api_farnell_key")
        layout.addWidget(gb_api)

        # Theme Selector
        h_theme = QHBoxLayout()
        h_theme.addWidget(QLabel("Application Theme:"))
        self.combo_theme = QComboBox()
        from ..resources.styles import Styles
        self.combo_theme.addItems(Styles.get_theme_names())
        self.combo_theme.setCurrentText(self.logic.settings.get("theme", "Light"))
        h_theme.addWidget(self.combo_theme)

        h_theme.addWidget(QLabel("UI Font:"))
        self.font_combo = QFontComboBox()
        current_font = self.logic.settings.get("ui_font", None)
        if current_font:
            self.font_combo.setCurrentFont(QFont(current_font))
        h_theme.addWidget(self.font_combo)
        
        h_theme.addWidget(QLabel("UI Scale (%):"))
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(50, 300)
        self.spin_scale.setValue(self.logic.settings.get("ui_scale", 100))
        self.spin_scale.setSingleStep(10)
        h_theme.addWidget(self.spin_scale)
        
        btn_apply = QPushButton("Apply Theme / Font")
        btn_apply.clicked.connect(self.apply_theme)
        h_theme.addWidget(btn_apply)

        btn_reset_theme = QPushButton("Revert to Light Theme")
        btn_reset_theme.clicked.connect(self.reset_default_theme)
        h_theme.addWidget(btn_reset_theme)
        # Live-apply when font changes
        self.font_combo.currentFontChanged.connect(lambda *_: self.apply_theme())
        
        # Maintenance
        gb_maint = QGroupBox("Maintenance")
        h_maint = QHBoxLayout(gb_maint)
        btn_export = QPushButton("Export Settings"); btn_export.clicked.connect(self.export_settings)
        btn_import = QPushButton("Import Settings"); btn_import.clicked.connect(self.import_settings)
        h_maint.addWidget(btn_export); h_maint.addWidget(btn_import)
        layout.addWidget(gb_maint)
        
        layout.addLayout(h_theme)
        layout.addStretch()

    def _apply_form_style(self, form):
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop | Qt.AlignLeft)
        form.setHorizontalSpacing(SPACING["sm"])
        form.setVerticalSpacing(SPACING["xs"])
        try:
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        except Exception:
            pass

    def add_row(self, form, label, key, placeholder="", help_text=None):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
        val = self.logic.settings.get(key, "")
        if key != "path_root":
            if key in ("symbol_path", "footprint_path"):
                val = self.logic.relativize_path_list_string(val)
            else:
                val = self.logic.relativize_path(val)
        edit = QLineEdit(val)
        if placeholder:
            edit.setPlaceholderText(placeholder)
        btn = QPushButton("Browse")
        icon_color = "#E0E0E0" if self.logic.settings.get("theme", "Light") in ["Dark"] else "#555555"
        btn.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        btn.setToolTip("Select folder")
        btn.clicked.connect(lambda: self.browse(edit, key))
        l.addWidget(edit); l.addWidget(btn)
        edit.setMinimumWidth(self._input_min_w)
        form.addRow(label, w); self.inputs[key] = edit
        if help_text:
            help_lbl = QLabel(help_text)
            help_lbl.setObjectName("formHelp")
            help_lbl.setWordWrap(True)
            form.addRow(QLabel(""), help_lbl)

    def add_tool_row(self, form, label, tool_key, help_text=None):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
        val = self.logic.settings.get("external_tools", {}).get(tool_key, "")
        val = self.logic.relativize_path(val)
        edit = QLineEdit(val)
        btn = QPushButton("Browse")
        icon_color = "#E0E0E0" if self.logic.settings.get("theme", "Light") in ["Dark"] else "#555555"
        btn.setIcon(Icons.get_icon(Icons.DOC, icon_color))
        btn.setToolTip("Select executable")
        btn.clicked.connect(lambda: self.browse_file(edit))
        l.addWidget(edit); l.addWidget(btn)
        edit.setMinimumWidth(self._input_min_w)
        form.addRow(label, w); self.inputs[f"tool_{tool_key}"] = edit
        if help_text:
            help_lbl = QLabel(help_text)
            help_lbl.setObjectName("formHelp")
            help_lbl.setWordWrap(True)
            form.addRow(QLabel(""), help_lbl)

    def browse(self, edit, key=None):
        if key == "path_root":
            start_dir = self.logic.expand_path(edit.text())
        else:
            start_dir = self.logic.resolve_path(edit.text())
        d = QFileDialog.getExistingDirectory(self, "Select", start_dir)
        if d:
            if key == "path_root":
                edit.setText(self.logic.normalize_path(d))
            else:
                edit.setText(self.logic.relativize_path(d))

    def browse_file(self, edit):
        start_dir = self.logic.resolve_path(edit.text())
        # If start_dir is a file, get dirname
        if start_dir and os.path.isfile(start_dir):
            start_dir = os.path.dirname(start_dir)
        f, _ = QFileDialog.getOpenFileName(self, "Select Executable", start_dir)
        if f: edit.setText(self.logic.relativize_path(f))

    def apply_theme(self, persist=True):
        theme = self.combo_theme.currentText()
        scale = self.spin_scale.value()
        from PySide6.QtWidgets import QApplication
        from ..resources.styles import Styles
        font_family = self.font_combo.currentFont().family()
        Styles.apply_theme(QApplication.instance(), theme, scale, font_family)
        # persist immediately so restarts keep the choice
        self.logic.settings["theme"] = theme
        self.logic.settings["ui_scale"] = scale
        self.logic.settings["ui_font"] = font_family
        if persist:
            self.logic.save_settings()
        self.theme_changed.emit()

    def reset_default_theme(self):
        self.combo_theme.setCurrentText("Light")
        self.apply_theme()
        show_toast(self, "Reverted to Light theme", 2200, "info")

    def save_settings(self):
        for k, e in self.inputs.items(): 
            if k.startswith("tool_"): continue
            if k == "path_root":
                self.logic.settings[k] = self.logic.normalize_path(e.text())
            else:
                if k in ("symbol_path", "footprint_path"):
                    self.logic.settings[k] = self.logic.resolve_path_list_string(e.text())
                else:
                    self.logic.settings[k] = self.logic.resolve_path(e.text())

        self.logic.settings["theme"] = self.combo_theme.currentText()
        self.logic.settings["ui_scale"] = self.spin_scale.value()
        self.logic.settings["ui_font"] = self.font_combo.currentFont().family()
        
        # Save Tools
        if "external_tools" not in self.logic.settings: self.logic.settings["external_tools"] = {}
        self.logic.settings["external_tools"]["editor"] = self.logic.resolve_path(self.inputs["tool_editor"].text())
        self.logic.settings["external_tools"]["kicad"] = self.logic.resolve_path(self.inputs["tool_kicad"].text())
        
        self.apply_theme(persist=False)

    def export_settings(self):
        f, _ = QFileDialog.getSaveFileName(self, "Export Settings", "settings_backup.json", "JSON (*.json)")
        if f:
            with open(f, 'w') as file:
                json.dump(self.logic.settings, file, indent=4)
            QMessageBox.information(self, "Success", "Settings exported.")
            show_toast(self, "Settings exported", 2000, "success")

    def import_settings(self):
        f, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON (*.json)")
        if f:
            with open(f, 'r') as file:
                self.logic.settings.update(json.load(file))
            self.logic.save_settings()
            QMessageBox.information(self, "Success", "Settings imported. Restart recommended.")
            show_toast(self, "Settings imported", 2500, "info")

class ProjectConfigPage(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def _apply_form_style(self, form):
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop | Qt.AlignLeft)
        form.setHorizontalSpacing(SPACING["sm"])
        form.setVerticalSpacing(SPACING["xs"])
        try:
            form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        except Exception:
            pass

    def setup_ui(self):
        layout = QVBoxLayout(self)
        defaults_group = QGroupBox("Project Metadata Defaults")
        defaults_layout = QFormLayout(defaults_group)
        self._apply_form_style(defaults_layout)
        self.edit_default_revision = QLineEdit()
        self.edit_default_revision.setMinimumWidth(220)
        self.edit_default_revision.setPlaceholderText("A")
        defaults_layout.addRow("Default Revision:", self.edit_default_revision)
        self.edit_default_description = QPlainTextEdit()
        self.edit_default_description.setMinimumWidth(320)
        self.edit_default_description.setPlaceholderText("Template for project descriptions...")
        self.edit_default_description.setFixedHeight(80)
        defaults_layout.addRow("Default Description:", self.edit_default_description)
        layout.addWidget(defaults_group)

        statuses_group = QGroupBox("Status Lifecycle")
        statuses_layout = QVBoxLayout(statuses_group)
        status_entry = QHBoxLayout()
        self.status_input = QLineEdit()
        self.status_input.setPlaceholderText("New status name")
        btn_add_status = QPushButton("Add")
        btn_add_status.clicked.connect(self.add_project_status)
        status_entry.addWidget(self.status_input)
        status_entry.addWidget(btn_add_status)
        statuses_layout.addLayout(status_entry)
        self.list_statuses = QListWidget()
        statuses_layout.addWidget(self.list_statuses)
        status_actions = QHBoxLayout()
        btn_move_up = QPushButton("Move Up")
        btn_move_up.clicked.connect(lambda: self.move_project_status(-1))
        btn_move_down = QPushButton("Move Down")
        btn_move_down.clicked.connect(lambda: self.move_project_status(1))
        btn_remove_status = QPushButton("Remove")
        btn_remove_status.clicked.connect(self.remove_project_status)
        status_actions.addWidget(btn_move_up)
        status_actions.addWidget(btn_move_down)
        status_actions.addWidget(btn_remove_status)
        statuses_layout.addLayout(status_actions)
        layout.addWidget(statuses_group)

        self.inner_tabs = QTabWidget()
        self.inner_tabs.setProperty("stretchTabs", True)
        self.inner_tabs.setTabPosition(QTabWidget.North)
        self.inner_tabs.setUsesScrollButtons(False)
        self.inner_tabs.tabBar().setExpanding(True)
        layout.addWidget(self.inner_tabs)

        # Checklist Templates Tab
        checklist_tab = QWidget()
        checklist_layout = QVBoxLayout(checklist_tab)
        checklist_layout.setContentsMargins(10, 10, 10, 10)
        gb_check = QGroupBox("PCB Checklist Templates")
        l_check = QVBoxLayout(gb_check)
        
        h_tmpl = QHBoxLayout()
        self.combo_templates = QComboBox()
        self.combo_templates.currentTextChanged.connect(self.on_template_change)
        h_tmpl.addWidget(self.combo_templates, stretch=1)
        
        btn_add_t = QPushButton("New"); btn_add_t.clicked.connect(self.add_template)
        h_tmpl.addWidget(btn_add_t)
        btn_del_t = QPushButton("Delete"); btn_del_t.clicked.connect(self.del_template)
        h_tmpl.addWidget(btn_del_t)
        l_check.addLayout(h_tmpl)

        meta_row = QHBoxLayout()
        meta_row.addWidget(QLabel("Version:"))
        self.edit_template_version = QLineEdit()
        self.edit_template_version.setFixedWidth(80)
        self.edit_template_version.textChanged.connect(self.on_template_version_changed)
        meta_row.addWidget(self.edit_template_version)
        self.btn_bump_version = QPushButton("Bump")
        self.btn_bump_version.clicked.connect(self.bump_template_version)
        meta_row.addWidget(self.btn_bump_version)
        self.lbl_template_updated = QLabel("Updated: -")
        meta_row.addWidget(self.lbl_template_updated)
        meta_row.addStretch()
        l_check.addLayout(meta_row)

        self.checklist_editor = ChecklistWidget(self, is_template=True)
        self.refresh_templates()
        l_check.addWidget(self.checklist_editor)
        checklist_layout.addWidget(gb_check)
        checklist_layout.addStretch()
        self.inner_tabs.addTab(checklist_tab, "Checklist Templates")

        # Project Types Tab
        types_tab = QWidget()
        types_layout = QVBoxLayout(types_tab)
        types_layout.setContentsMargins(10, 10, 10, 10)
        gb_types = QGroupBox("Project Types")
        l_types = QVBoxLayout(gb_types)
        h_types = QHBoxLayout()
        self.type_input = QLineEdit(); self.type_input.setPlaceholderText("New Project Type")
        btn_add_type = QPushButton("Add"); btn_add_type.clicked.connect(self.add_project_type)
        h_types.addWidget(self.type_input); h_types.addWidget(btn_add_type)
        l_types.addLayout(h_types)
        
        self.list_types = QListWidget()
        l_types.addWidget(self.list_types)
        btn_del_type = QPushButton("Remove Selected Type"); btn_del_type.clicked.connect(self.del_project_type)
        l_types.addWidget(btn_del_type)
        self.refresh_project_types()
        types_layout.addWidget(gb_types)
        types_layout.addStretch()
        self.inner_tabs.addTab(types_tab, "Project Types")
        self._load_defaults()

    def refresh_templates(self):
        self.combo_templates.blockSignals(True)
        self.combo_templates.clear()
        templates = self.logic.settings.get("checklist_templates", {})
        self.combo_templates.addItems(list(templates.keys()))
        self.combo_templates.blockSignals(False)
        if self.combo_templates.count() > 0:
            self.combo_templates.setCurrentIndex(0)
            self.on_template_change(self.combo_templates.currentText())
        else:
            self.checklist_editor.load_data({})
            self.edit_template_version.setText("")
            self.lbl_template_updated.setText("Updated: -")

    def on_template_change(self, name):
        if not name: return
        templates = self.logic.settings.get("checklist_templates", {})
        data = templates.get(name, {})
        self.checklist_editor.load_data(data)
        meta = self.get_template_meta(name)
        self.edit_template_version.setText(meta.get("version", "1.0"))
        updated = meta.get("updated", "")
        self.lbl_template_updated.setText(f"Updated: {updated}" if updated else "Updated: -")

    def get_template_meta(self, name):
        meta_store = self.logic.settings.setdefault("checklist_template_meta", {})
        if name not in meta_store:
            meta_store[name] = {"version": "1.0", "updated": ""}
        return meta_store[name]

    def on_template_version_changed(self, text):
        name = self.combo_templates.currentText()
        if not name:
            return
        meta = self.get_template_meta(name)
        meta["version"] = text.strip() or "1.0"

    def bump_template_version(self):
        name = self.combo_templates.currentText()
        if not name:
            return
        meta = self.get_template_meta(name)
        current = meta.get("version", "1.0")
        parts = current.split(".")
        bumped = "1"
        try:
            nums = [int(p) for p in parts if p.isdigit() or (p and p.isnumeric())]
            if len(parts) == 1 and nums:
                bumped = str(nums[0] + 1)
            elif nums:
                nums[-1] += 1
                bumped = ".".join(str(n) for n in nums)
            else:
                bumped = "1"
        except Exception:
            bumped = "1"
        meta["version"] = bumped
        meta["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.edit_template_version.setText(bumped)
        self.lbl_template_updated.setText(f"Updated: {meta['updated']}")

    def add_template(self):
        name, ok = QInputDialog.getText(self, "New Template", "Template Name:")
        if ok and name:
            self.logic.settings.setdefault("checklist_templates", {})[name] = {step: [] for step in self.checklist_editor.fallback_steps}
            self.logic.settings.setdefault("checklist_template_meta", {})[name] = {
                "version": "1.0",
                "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self.refresh_templates()
            self.combo_templates.setCurrentText(name)

    def del_template(self):
        name = self.combo_templates.currentText()
        if name and QMessageBox.question(self, "Confirm", f"Delete template '{name}'?") == QMessageBox.Yes:
            del self.logic.settings["checklist_templates"][name]
            if name in self.logic.settings.get("checklist_template_meta", {}):
                del self.logic.settings["checklist_template_meta"][name]
            self.refresh_templates()

    def sync_checklist_from_ui(self):
        name = self.combo_templates.currentText()
        if name:
            self.logic.settings.setdefault("checklist_templates", {})[name] = self.checklist_editor.get_data()
            meta = self.get_template_meta(name)
            meta["updated"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.lbl_template_updated.setText(f"Updated: {meta['updated']}")

    def add_project_type(self):
        t = self.type_input.text().strip()
        if t and t not in self.logic.settings.setdefault("project_types", []):
            self.logic.settings["project_types"].append(t)
            self.refresh_project_types()
            self.type_input.clear()

    def del_project_type(self):
        item = self.list_types.currentItem()
        if item and item.text() in self.logic.settings.get("project_types", []):
            self.logic.settings["project_types"].remove(item.text())
            self.refresh_project_types()

    def refresh_project_types(self):
        self.list_types.clear()
        for t in self.logic.settings.get("project_types", []):
            self.list_types.addItem(t)

    def _load_defaults(self):
        defaults = self.logic.settings.setdefault("project_metadata_defaults", {})
        self.edit_default_revision.setText(defaults.get("default_revision", "A"))
        self.edit_default_description.setPlainText(defaults.get("default_description", ""))
        self.refresh_status_list()

    def refresh_status_list(self):
        statuses = self.logic.settings.get("project_statuses", PROJECT_STATUS_DEFAULTS)
        self.list_statuses.clear()
        for status in statuses:
            self.list_statuses.addItem(status)

    def add_project_status(self):
        text = self.status_input.text().strip()
        if not text:
            return
        existing = [self.list_statuses.item(i).text() for i in range(self.list_statuses.count())]
        if text in existing:
            return
        self.list_statuses.addItem(text)
        self.status_input.clear()

    def remove_project_status(self):
        row = self.list_statuses.currentRow()
        if row >= 0:
            self.list_statuses.takeItem(row)

    def move_project_status(self, shift):
        count = self.list_statuses.count()
        row = self.list_statuses.currentRow()
        if row < 0:
            return
        target = row + shift
        if target < 0 or target >= count:
            return
        item = self.list_statuses.takeItem(row)
        self.list_statuses.insertItem(target, item)
        self.list_statuses.setCurrentRow(target)

    def save_settings(self):
        defaults = self.logic.settings.setdefault("project_metadata_defaults", {})
        defaults["default_revision"] = self.edit_default_revision.text().strip()
        defaults["default_description"] = self.edit_default_description.toPlainText().strip()
        statuses = [self.list_statuses.item(i).text() for i in range(self.list_statuses.count())]
        if statuses:
            self.logic.settings["project_statuses"] = statuses
        else:
            self.logic.settings["project_statuses"] = PROJECT_STATUS_DEFAULTS.copy()

class KanbanSettingsPage(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Categories
        gb_kanban = QGroupBox("Kanban Categories")
        l_kanban = QVBoxLayout(gb_kanban)
        
        h_scope = QHBoxLayout()
        h_scope.addWidget(QLabel("Configuration Scope:"))
        self.scope_combo = QComboBox()
        self.scope_combo.setMinimumWidth(180)
        self.scope_combo.currentTextChanged.connect(self._on_scope_selected)
        h_scope.addWidget(self.scope_combo, 1)
        l_kanban.addLayout(h_scope)

        self._selected_scope = "Global (All Types)"
        self.refresh_scope_options()
        
        h_k_in = QHBoxLayout()
        self.k_cat_name = QLineEdit(); self.k_cat_name.setPlaceholderText("Category Name")
        self.btn_k_color = QPushButton("Pick Color")
        self.btn_k_color.setStyleSheet("background-color: #95a5a6; color: white;")
        self.btn_k_color.clicked.connect(self.pick_kanban_color)
        self.current_k_color = "#95a5a6"
        btn_add_k = QPushButton("Add"); btn_add_k.clicked.connect(self.add_kanban_cat)
        h_k_in.addWidget(self.k_cat_name); h_k_in.addWidget(self.btn_k_color); h_k_in.addWidget(btn_add_k)
        l_kanban.addLayout(h_k_in)
        
        self.list_kanban_cats = QListWidget()
        self.list_kanban_cats.itemSelectionChanged.connect(self.on_kanban_cat_selected)
        l_kanban.addWidget(self.list_kanban_cats)
        
        btn_row = QHBoxLayout()
        btn_update_k = QPushButton("Update Color"); btn_update_k.clicked.connect(self.update_kanban_cat_color)
        btn_del_k = QPushButton("Remove Category"); btn_del_k.clicked.connect(self.del_kanban_cat)
        btn_row.addWidget(btn_update_k)
        btn_row.addWidget(btn_del_k)
        l_kanban.addLayout(btn_row)
        
        self.refresh_kanban_cats()
        layout.addWidget(gb_kanban)

        # Progress Weights
        gb_weights = QGroupBox("Progress Weighting")
        l_weights = QVBoxLayout(gb_weights)
        form_weights = QFormLayout()
        self.weight_spins = {}
        weights = self.logic.settings.get("kanban_priority_weights", {
            "Critical": 5,
            "High": 3,
            "Normal": 1,
            "Low": 0.5,
        })
        for key in ["Critical", "High", "Normal", "Low"]:
            spin = QDoubleSpinBox()
            spin.setRange(0.1, 10.0)
            spin.setSingleStep(0.1)
            spin.setDecimals(2)
            spin.setValue(float(weights.get(key, 1)))
            self.weight_spins[key] = spin
            form_weights.addRow(f"{key} weight:", spin)
        l_weights.addLayout(form_weights)
        lbl_hint = QLabel("Higher values make that priority impact completion more.")
        lbl_hint.setStyleSheet("color: #888; font-size: 11px;")
        l_weights.addWidget(lbl_hint)
        layout.addWidget(gb_weights)

        # Templates
        gb_kt = QGroupBox("Kanban Task Templates")
        l_kt = QVBoxLayout(gb_kt)
        h_type = QHBoxLayout()
        h_type.addWidget(QLabel("Project Type:"))
        self.combo_k_type = QComboBox()
        self.combo_k_type.addItem("Standard")
        self.combo_k_type.addItems(self.logic.settings.get("project_types", []))
        self.combo_k_type.currentTextChanged.connect(self.on_k_type_change)
        h_type.addWidget(self.combo_k_type)
        l_kt.addLayout(h_type)
        self.edit_kt = QPlainTextEdit()
        l_kt.addWidget(self.edit_kt)
        hint = QLabel(
            "Format: Task Name | Category | Priority | Lane | Description (description optional)."
        )
        hint.setStyleSheet("color: #6B7280; font-size: 11px;")
        l_kt.addWidget(hint)
        layout.addWidget(gb_kt)
        
        raw_templates = self.logic.settings.get("kanban_templates", {})
        self.temp_kanban_templates = _build_template_map(raw_templates)
        self.current_k_type = "Standard"
        self.load_k_template("Standard")

    def pick_kanban_color(self):
        c = QColorDialog.getColor()
        if c.isValid():
            self.current_k_color = c.name()
            self.btn_k_color.setStyleSheet(f"background-color: {c.name()}; color: white;")

    def refresh_kanban_cats(self):
        self.list_kanban_cats.clear()
        scope = self._selected_scope
        all_cats = self.logic.settings.get("kanban_categories", {})
        restrictions = self.logic.settings.get("category_restrictions", {})
        
        for name, color in all_cats.items():
            restr = restrictions.get(name, [])
            if scope != "Global (All Types)" and restr and scope not in restr: continue
            
            display = name + (f" [{','.join(restr)}]" if restr else "")
            item = QListWidgetItem(display)
            pixmap = QPixmap(16, 16); pixmap.fill(QColor(color))
            item.setIcon(QIcon(pixmap))
            self.list_kanban_cats.addItem(item)

    def add_kanban_cat(self):
        name = self.k_cat_name.text().strip()
        scope = self._selected_scope
        if name:
            self.logic.settings.setdefault("kanban_categories", {})[name] = self.current_k_color
            if scope != "Global (All Types)":
                self.logic.settings.setdefault("category_restrictions", {})[name] = [scope]
            self.refresh_kanban_cats()
            self.k_cat_name.clear()

    def del_kanban_cat(self):
        item = self.list_kanban_cats.currentItem()
        if item:
            name = item.text().split(" [")[0]
            if name in self.logic.settings.get("kanban_categories", {}):
                del self.logic.settings["kanban_categories"][name]
                self.refresh_kanban_cats()

    def on_kanban_cat_selected(self):
        item = self.list_kanban_cats.currentItem()
        if not item:
            return
        name = item.text().split(" [")[0]
        color = self.logic.settings.get("kanban_categories", {}).get(name)
        if color:
            self.current_k_color = color
            self.btn_k_color.setStyleSheet(f"background-color: {color}; color: white;")

    def update_kanban_cat_color(self):
        item = self.list_kanban_cats.currentItem()
        if not item:
            return
        name = item.text().split(" [")[0]
        if name in self.logic.settings.get("kanban_categories", {}):
            self.logic.settings["kanban_categories"][name] = self.current_k_color
            self.refresh_kanban_cats()

    def on_k_type_change(self, new_type):
        if not new_type:
            return
        self._commit_template_edits()
        self.current_k_type = new_type
        self.load_k_template(new_type)

    def load_k_template(self, type_name):
        tasks = self.temp_kanban_templates.get(type_name, [])
        if not tasks and type_name != "Standard":
            tasks = self.temp_kanban_templates.get("Standard", [])
        self.edit_kt.setPlainText(_template_lines(tasks))

    def save_settings(self):
        self._commit_template_edits()
        self.logic.settings["kanban_templates"] = self.temp_kanban_templates
        if hasattr(self, "weight_spins"):
            self.logic.settings["kanban_priority_weights"] = {
                k: float(spin.value()) for k, spin in self.weight_spins.items()
            }

    def _commit_template_edits(self):
        if not hasattr(self, "current_k_type"):
            return
        entries = _parse_template_editor(self.edit_kt.toPlainText())
        self.temp_kanban_templates[self.current_k_type] = entries

    def refresh_scope_options(self):
        options = ["Global (All Types)"] + self.logic.settings.get("project_types", [])
        self.scope_combo.blockSignals(True)
        self.scope_combo.clear()
        self.scope_combo.addItems(options)

        target = self._selected_scope if self._selected_scope in options else options[0]
        self.scope_combo.setCurrentText(target)
        self._selected_scope = target
        self.scope_combo.blockSignals(False)

    def _on_scope_selected(self, scope):
        if scope and scope != self._selected_scope:
            self._selected_scope = scope
            self.refresh_kanban_cats()

class BackupSettingsPage(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        
        h_path = QHBoxLayout()
        h_path.addWidget(QLabel("Backup Root Folder:"))
        val = self.logic.settings.get("backup", {}).get("path", "backups")
        self.edit_backup_path = QLineEdit(self.logic.relativize_path(val))
        btn_browse = QPushButton("Browse")
        icon_color = "#E0E0E0" if self.logic.settings.get("theme", "Light") in ["Dark"] else "#555555"
        btn_browse.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        btn_browse.setToolTip("Select backup folder")
        btn_browse.clicked.connect(self.browse)
        btn_open_folder = QPushButton("Open Folder")
        btn_open_folder.setIcon(Icons.get_icon(Icons.EXTERNAL, icon_color))
        btn_open_folder.clicked.connect(self.open_backup_folder)
        h_path.addWidget(self.edit_backup_path)
        h_path.addWidget(btn_browse)
        h_path.addWidget(btn_open_folder)
        layout.addLayout(h_path)
        
        self.chk_backup_exit = QCheckBox("Backup Enabled Categories on Exit")
        self.chk_backup_exit.setChecked(self.logic.settings.get("backup", {}).get("backup_on_exit", False))
        layout.addWidget(self.chk_backup_exit)
        
        btn_backup_now = QPushButton("Run Backup Now")
        btn_backup_now.setIcon(Icons.get_icon(Icons.SAVE, icon_color))
        btn_backup_now.clicked.connect(self.run_manual_backup)
        layout.addWidget(btn_backup_now)
        
        self.backup_tabs = QTabWidget()
        self.backup_tabs.setProperty("stretchTabs", True)
        self.backup_tabs.setIconSize(QSize(16, 16))
        self.backup_tabs.setUsesScrollButtons(False)
        self.backup_tabs.tabBar().setExpanding(True)
        self.backup_inputs = {}
        self.backup_category_keys = ["app_data", "symbols", "footprints"]
        for key, label in [("app_data", "App Data"), ("symbols", "Symbols"), ("footprints", "Footprints")]:
            w = QWidget(); fl = QFormLayout(w)
            cfg = self.logic.settings.get("backup", {}).get(key, {})
            chk = QCheckBox("Enable"); chk.setChecked(cfg.get("enabled", False))
            spin_int = QSpinBox(); spin_int.setRange(1, 10080); spin_int.setValue(cfg.get("interval_min", 60))
            spin_max = QSpinBox(); spin_max.setRange(1, 100); spin_max.setValue(cfg.get("max_backups", 5))
            lbl_last = QLabel(cfg.get("last_run", "Never"))
            lbl_next = QLabel("-")
            fl.addRow("Status:", chk)
            fl.addRow("Interval (min):", spin_int)
            fl.addRow("Max Backups:", spin_max)
            fl.addRow("Last Run:", lbl_last)
            fl.addRow("Next Run:", lbl_next)
            self.backup_inputs[key] = (chk, spin_int, spin_max, lbl_last, lbl_next)
            if key == "app_data":
                icon = Icons.get_icon(Icons.DASHBOARD, icon_color)
            elif key == "symbols":
                icon = Icons.get_icon(Icons.CHIP, icon_color)
            else:
                icon = Icons.get_icon(Icons.TOOL, icon_color)
            self.backup_tabs.addTab(w, icon, label)
        layout.addWidget(self.backup_tabs)
        self.backup_tabs.currentChanged.connect(lambda *_: self.refresh_backups())
        
        # Restore Section
        gb_restore = QGroupBox("Restore Settings & Rules")
        l_restore = QVBoxLayout(gb_restore)
        
        self.list_backups = QListWidget()
        self.list_backups.setContextMenuPolicy(Qt.CustomContextMenu)
        self.list_backups.customContextMenuRequested.connect(self.show_backup_context_menu)
        l_restore.addWidget(self.list_backups)
        
        h_res = QHBoxLayout()
        btn_refresh = QPushButton("Refresh List"); btn_refresh.clicked.connect(self.refresh_backups)
        btn_restore = QPushButton("Restore Selected"); btn_restore.clicked.connect(self.restore_selected)
        h_res.addWidget(btn_refresh); h_res.addWidget(btn_restore)
        l_restore.addLayout(h_res)
        layout.addWidget(gb_restore)
        
        self.refresh_backups()
        self.refresh_backup_status()

    def browse(self):
        start_dir = self.logic.resolve_path(self.edit_backup_path.text())
        d = QFileDialog.getExistingDirectory(self, "Select", start_dir)
        if d:
            self.edit_backup_path.setText(self.logic.relativize_path(d))

    def open_backup_folder(self):
        path = self.logic.resolve_path(self.edit_backup_path.text())
        if not path:
            return
        if not os.path.exists(path):
            QMessageBox.warning(self, "Folder Missing", "Backup folder does not exist.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(path))

    def refresh_backups(self):
        self.list_backups.clear()
        cfg = self.logic.settings.get("backup", {})
        root = self._get_backup_root(cfg)
        cat = self._current_backup_category_key()
        cat_dir = root / cat
        if not cat_dir.exists():
            return
        backups = sorted(
            [p for p in cat_dir.glob("*.zip") if p.is_file()],
            key=lambda p: p.name,
            reverse=True
        )
        for b in backups:
            self.list_backups.addItem(b.stem)

    def run_manual_backup(self):
        self.save_settings()
        self.logic.save_settings()
        try:
            self.logic.perform_backup(force=True)
            QMessageBox.information(self, "Backup", "Backup completed.")
            self.refresh_backups()
            self.refresh_backup_status()
        except Exception as e:
            QMessageBox.critical(self, "Backup Error", f"Backup failed: {e}")

    def restore_selected(self):
        item = self.list_backups.currentItem()
        if not item:
            return
        self.restore_backup_item(item)

    def show_backup_context_menu(self, pos):
        item = self.list_backups.itemAt(pos)
        if not item:
            return
        self.list_backups.setCurrentItem(item)
        menu = QMenu(self)
        act_open = menu.addAction("Open in Folder")
        act_restore = menu.addAction("Restore Backup")
        act_delete = menu.addAction("Delete Backup")
        action = menu.exec(self.list_backups.mapToGlobal(pos))
        if action == act_open:
            self.open_backup_in_folder(item)
        elif action == act_restore:
            self.restore_backup_item(item)
        elif action == act_delete:
            self.delete_backup_item(item)

    def _get_backup_root(self, cfg=None):
        if cfg is None:
            cfg = self.logic.settings.get("backup", {})
        root = Path(cfg.get("path", "backups"))
        if not root.is_absolute():
            root = Path(os.getcwd()) / root
        return root

    def _get_backup_zip(self, item):
        if not item:
            return None
        root = self._get_backup_root()
        cat = self._current_backup_category_key()
        return root / cat / f"{item.text()}.zip"

    def _current_backup_category_key(self):
        idx = self.backup_tabs.currentIndex()
        if idx < 0 or idx >= len(self.backup_category_keys):
            return "app_data"
        return self.backup_category_keys[idx]

    def open_backup_in_folder(self, item):
        zip_path = self._get_backup_zip(item)
        if not zip_path or not zip_path.exists():
            QMessageBox.warning(self, "Missing Backup", "Selected backup does not exist.")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(zip_path.parent)))

    def restore_backup_item(self, item):
        if not item:
            return
        if self._current_backup_category_key() != "app_data":
            QMessageBox.information(self, "Restore", "Restore is only available for App Data backups.")
            return
        timestamp = item.text()
        if QMessageBox.question(
            self,
            "Confirm Restore",
            f"Are you sure you want to restore backup '{timestamp}'?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        try:
            self.logic.restore_backup(timestamp)
            QMessageBox.information(self, "Restore", "Restore completed. Restart recommended.")
        except Exception as e:
            QMessageBox.critical(self, "Restore Error", f"Restore failed: {e}")

    def delete_backup_item(self, item):
        if not item:
            return
        timestamp = item.text()
        if QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete backup '{timestamp}'?",
            QMessageBox.Yes | QMessageBox.No
        ) != QMessageBox.Yes:
            return
        zip_path = self._get_backup_zip(item)
        if not zip_path or not zip_path.exists():
            QMessageBox.warning(self, "Missing Backup", "Selected backup does not exist.")
            return
        try:
            zip_path.unlink()
            self.refresh_backups()
        except Exception as e:
            QMessageBox.critical(self, "Delete Error", f"Delete failed: {e}")

    def save_settings(self):
        if "backup" not in self.logic.settings:
            self.logic.settings["backup"] = {}
        cfg = self.logic.settings["backup"]

        cfg["path"] = self.logic.resolve_path(self.edit_backup_path.text())
        cfg["backup_on_exit"] = self.chk_backup_exit.isChecked()

        for key, inputs in self.backup_inputs.items():
            chk, spin_int, spin_max, lbl_last, lbl_next = inputs
            existing = cfg.get(key, {})
            cfg[key] = {
                "enabled": chk.isChecked(),
                "interval_min": int(spin_int.value()),
                "max_backups": int(spin_max.value()),
                "last_run": existing.get("last_run", "")
            }
        self.refresh_backup_status()

    def refresh_backup_status(self):
        cfg = self.logic.settings.get("backup", {})
        for key, inputs in self.backup_inputs.items():
            chk, spin_int, spin_max, lbl_last, lbl_next = inputs
            last_str = cfg.get(key, {}).get("last_run", "")
            lbl_last.setText(last_str or "Never")
            if not chk.isChecked():
                lbl_next.setText("Disabled")
                continue
            if not last_str:
                lbl_next.setText("Pending")
                continue
            try:
                last_dt = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
                next_dt = last_dt + timedelta(minutes=int(spin_int.value()))
                lbl_next.setText(next_dt.strftime("%Y-%m-%d %H:%M:%S"))
            except Exception:
                lbl_next.setText("-")
