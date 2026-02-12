from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, 
                             QLineEdit, QPushButton, QLabel, QFileDialog, 
                             QFrame, QMessageBox, QGroupBox, QComboBox, QInputDialog, 
                             QListWidget, QListWidgetItem, QColorDialog, QPlainTextEdit, 
                             QTabWidget, QCheckBox, QSpinBox)
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtCore import Qt
import json
import os
from pathlib import Path
from .checklist_widget import ChecklistWidget
from ui.widgets.spacing import SPACING
from ui.widgets.toast import show_toast
try:
    from .icons import Icons
except ImportError:
    from ui.icons import Icons

from kanban_templates import (
    format_template_entry,
    normalize_template_list,
    parse_template_line,
)

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

class GeneralSettingsPage(QWidget):
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
            "PL Variable:",
            "pl_variable",
            help_text="Base directory used for path placeholders.",
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
        self.combo_theme.addItems(["Light", "Dark"])
        self.combo_theme.setCurrentText(self.logic.settings.get("theme", "Light"))
        h_theme.addWidget(self.combo_theme)
        
        h_theme.addWidget(QLabel("UI Scale (%):"))
        self.spin_scale = QSpinBox()
        self.spin_scale.setRange(50, 300)
        self.spin_scale.setValue(self.logic.settings.get("ui_scale", 100))
        self.spin_scale.setSingleStep(10)
        h_theme.addWidget(self.spin_scale)
        
        btn_apply = QPushButton("Apply Theme")
        btn_apply.clicked.connect(self.apply_theme)
        h_theme.addWidget(btn_apply)
        
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

    def add_row(self, form, label, key, help_text=None):
        w = QWidget(); l = QHBoxLayout(w); l.setContentsMargins(0,0,0,0)
        val = self.logic.settings.get(key, "")
        if key != "pl_variable":
            val = self.logic.relativize_path(val)
        edit = QLineEdit(val)
        btn = QPushButton("Browse")
        icon_color = "#E0E0E0" if self.logic.settings.get("theme", "Light") in ["Dark"] else "#555555"
        btn.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        btn.setToolTip("Select folder")
        btn.clicked.connect(lambda: self.browse(edit))
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

    def browse(self, edit):
        start_dir = self.logic.resolve_path(edit.text())
        d = QFileDialog.getExistingDirectory(self, "Select", start_dir)
        if d: edit.setText(self.logic.relativize_path(d))

    def browse_file(self, edit):
        start_dir = self.logic.resolve_path(edit.text())
        # If start_dir is a file, get dirname
        if start_dir and os.path.isfile(start_dir):
            start_dir = os.path.dirname(start_dir)
        f, _ = QFileDialog.getOpenFileName(self, "Select Executable", start_dir)
        if f: edit.setText(self.logic.relativize_path(f))

    def apply_theme(self):
        theme = self.combo_theme.currentText()
        scale = self.spin_scale.value()
        from PySide6.QtWidgets import QApplication
        from .styles import Styles
        Styles.apply_theme(QApplication.instance(), theme, scale)

    def save_settings(self):
        for k, e in self.inputs.items(): 
            if k.startswith("tool_"): continue
            if k == "pl_variable":
                self.logic.settings[k] = e.text()
            else:
                self.logic.settings[k] = self.logic.resolve_path(e.text())

        self.logic.settings["theme"] = self.combo_theme.currentText()
        self.logic.settings["ui_scale"] = self.spin_scale.value()
        
        # Save Tools
        if "external_tools" not in self.logic.settings: self.logic.settings["external_tools"] = {}
        self.logic.settings["external_tools"]["editor"] = self.logic.resolve_path(self.inputs["tool_editor"].text())
        self.logic.settings["external_tools"]["kicad"] = self.logic.resolve_path(self.inputs["tool_kicad"].text())
        
        self.apply_theme()

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

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Checklist Templates
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

        self.checklist_editor = ChecklistWidget(self, is_template=True)
        self.refresh_templates()
        l_check.addWidget(self.checklist_editor)
        layout.addWidget(gb_check)

        # Project Types
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
        layout.addWidget(gb_types)

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

    def on_template_change(self, name):
        if not name: return
        templates = self.logic.settings.get("checklist_templates", {})
        data = templates.get(name, {})
        self.checklist_editor.load_data(data)

    def add_template(self):
        name, ok = QInputDialog.getText(self, "New Template", "Template Name:")
        if ok and name:
            self.logic.settings.setdefault("checklist_templates", {})[name] = {step: [] for step in self.checklist_editor.fallback_steps}
            self.refresh_templates()
            self.combo_templates.setCurrentText(name)

    def del_template(self):
        name = self.combo_templates.currentText()
        if name and QMessageBox.question(self, "Confirm", f"Delete template '{name}'?") == QMessageBox.Yes:
            del self.logic.settings["checklist_templates"][name]
            self.refresh_templates()

    def sync_checklist_from_ui(self):
        name = self.combo_templates.currentText()
        if name:
            self.logic.settings.setdefault("checklist_templates", {})[name] = self.checklist_editor.get_data()

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

    def save_settings(self):
        pass # Data is updated live or via sync_checklist_from_ui

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
        self.combo_scope = QComboBox()
        self.combo_scope.addItem("Global (All Types)")
        self.combo_scope.addItems(self.logic.settings.get("project_types", []))
        self.combo_scope.currentTextChanged.connect(self.refresh_kanban_cats)
        h_scope.addWidget(self.combo_scope)
        l_kanban.addLayout(h_scope)
        
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
        l_kanban.addWidget(self.list_kanban_cats)
        
        btn_del_k = QPushButton("Remove Category"); btn_del_k.clicked.connect(self.del_kanban_cat)
        l_kanban.addWidget(btn_del_k)
        
        self.refresh_kanban_cats()
        layout.addWidget(gb_kanban)

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
        hint = QLabel("Format: Task Name | Category | Priority | Lane | Description (description optional).")
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
        scope = self.combo_scope.currentText()
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
        scope = self.combo_scope.currentText()
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

    def _commit_template_edits(self):
        if not hasattr(self, "current_k_type"):
            return
        entries = _parse_template_editor(self.edit_kt.toPlainText())
        self.temp_kanban_templates[self.current_k_type] = entries

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
        btn_browse.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        btn_browse.setToolTip("Select backup folder")
        btn_browse.clicked.connect(self.browse)
        h_path.addWidget(self.edit_backup_path); h_path.addWidget(btn_browse)
        layout.addLayout(h_path)
        
        self.chk_backup_exit = QCheckBox("Backup Enabled Categories on Exit")
        self.chk_backup_exit.setChecked(self.logic.settings.get("backup", {}).get("backup_on_exit", False))
        layout.addWidget(self.chk_backup_exit)
        
        btn_backup_now = QPushButton("Run Backup Now")
        btn_backup_now.setIcon(Icons.get_icon(Icons.SAVE, icon_color))
        btn_backup_now.clicked.connect(self.run_manual_backup)
        layout.addWidget(btn_backup_now)
        
        self.backup_tabs = QTabWidget()
        self.backup_inputs = {}
        for key, label in [("app_data", "App Data"), ("symbols", "Symbols"), ("footprints", "Footprints")]:
            w = QWidget(); fl = QFormLayout(w)
            cfg = self.logic.settings.get("backup", {}).get(key, {})
            chk = QCheckBox("Enable"); chk.setChecked(cfg.get("enabled", False))
            spin_int = QSpinBox(); spin_int.setRange(1, 10080); spin_int.setValue(cfg.get("interval_min", 60))
            spin_max = QSpinBox(); spin_max.setRange(1, 100); spin_max.setValue(cfg.get("max_backups", 5))
            fl.addRow("Status:", chk); fl.addRow("Interval (min):", spin_int); fl.addRow("Max Backups:", spin_max)
            self.backup_inputs[key] = (chk, spin_int, spin_max)
            self.backup_tabs.addTab(w, label)
        layout.addWidget(self.backup_tabs)
        
        # Restore Section
        gb_restore = QGroupBox("Restore Settings & Rules")
        l_restore = QVBoxLayout(gb_restore)
        
        self.list_backups = QListWidget()
        l_restore.addWidget(self.list_backups)
        
        h_res = QHBoxLayout()
        btn_refresh = QPushButton("Refresh List"); btn_refresh.clicked.connect(self.refresh_backups)
        btn_restore = QPushButton("Restore Selected"); btn_restore.clicked.connect(self.restore_selected)
        h_res.addWidget(btn_refresh); h_res.addWidget(btn_restore)
        l_restore.addLayout(h_res)
        layout.addWidget(gb_restore)
        
        self.refresh_backups()

    def browse(self):
        start_dir = self.logic.resolve_path(self.edit_backup_path.text())
        d = QFileDialog.getExistingDirectory(self, "Select", start_dir)
        if d: self.edit_backup_path.setText(self.logic.relativize_path(d))

    def run_manual_backup(self):
        self.logic.perform_backup(force=True)
        QMessageBox.information(self, "Backup", "Manual backup completed for enabled categories.")
        self.refresh_backups()

    def refresh_backups(self):
        self.list_backups.clear()
        path_str = self.logic.resolve_path(self.edit_backup_path.text()) or "backups"
        root = Path(path_str)
        if not root.is_absolute(): root = Path(os.getcwd()) / root
        
        app_data_dir = root / "app_data"
        if app_data_dir.exists():
            backups = sorted([d.name for d in app_data_dir.iterdir() if d.is_dir()], reverse=True)
            self.list_backups.addItems(backups)

    def restore_selected(self):
        item = self.list_backups.currentItem()
        if not item: return
        
        ts = item.text()
        if QMessageBox.question(self, "Confirm Restore", f"Restore settings from '{ts}'?\nCurrent settings will be overwritten and app may need restart.", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.logic.restore_backup(ts)
            QMessageBox.information(self, "Success", "Backup restored. Please restart the application.")

    def save_settings(self):
        backup_cfg = {"path": self.logic.resolve_path(self.edit_backup_path.text())}
        backup_cfg["backup_on_exit"] = self.chk_backup_exit.isChecked()
        
        for key, (chk, spin_int, spin_max) in self.backup_inputs.items():
            backup_cfg[key] = {
                "enabled": chk.isChecked(),
                "interval_min": spin_int.value(),
                "max_backups": spin_max.value(),
                "last_run": self.logic.settings.get("backup", {}).get(key, {}).get("last_run", "")
            }
        self.logic.settings["backup"] = backup_cfg
