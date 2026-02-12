from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QProgressBar,
    QInputDialog,
    QPushButton,
    QMessageBox,
    QFileDialog,
    QLabel,
    QComboBox,
    QScrollArea,
    QFrame,
    QToolButton,
)
from PySide6.QtCore import Qt, QDateTime, Signal
from PySide6.QtGui import QFont
from datetime import datetime
from ui.widgets.spacing import SPACING
from ui.widgets.elevation import apply_layered_elevation

try:
    from ..resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons

STATUS_CHOICES = [
    ("Incomplete", "No"),
    ("Complete", "Yes"),
]


class ChecklistRuleRow(QFrame):
    changed = Signal()
    removed = Signal(object)

    def __init__(self, text, owner, due, status, comment="", icon_color="#f1c40f"):
        super().__init__()
        self.setObjectName("checklistRule")
        self.comment = comment
        self.icon_color = icon_color
        self._build_ui(text, owner, due, status)

    def _build_ui(self, text, owner, due, status):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 4, 6, 4)
        layout.setSpacing(8)
        self.setStyleSheet("""
QFrame#checklistRule {
    background: rgba(255, 255, 255, 0.04);
    border-radius: 12px;
    border: 1px solid rgba(255, 255, 255, 0.08);
}
QFrame#checklistRule:pressed {
    border-color: rgba(255, 255, 255, 0.25);
}
""")

        self.text_edit = QLineEdit(text)
        self.text_edit.setPlaceholderText("Rule")
        self.text_edit.setStyleSheet("border: none; background: transparent; color: #f8fafc; font-size: 12px;")
        self.text_edit.textChanged.connect(self.changed.emit)
        layout.addWidget(self.text_edit, stretch=2)

        self.owner_edit = QLineEdit(owner)
        self.owner_edit.setPlaceholderText("Owner")
        self.owner_edit.setMaximumWidth(120)
        self.owner_edit.textChanged.connect(self.changed.emit)
        layout.addWidget(self.owner_edit)

        self.due_edit = QLineEdit(due)
        self.due_edit.setPlaceholderText("Due")
        self.due_edit.setMaximumWidth(110)
        self.due_edit.textChanged.connect(self.changed.emit)
        self.due_edit.setStyleSheet("font-size: 11px;")
        layout.addWidget(self.due_edit)

        self.status_combo = QComboBox()
        for label, value in STATUS_CHOICES:
            self.status_combo.addItem(label, value)
        self._set_status(status)
        self.status_combo.currentTextChanged.connect(lambda _=None: self.changed.emit())
        layout.addWidget(self.status_combo)

        self.btn_remove = QToolButton()
        self.btn_remove.setIcon(Icons.get_icon(Icons.TRASH, self.icon_color))
        self.btn_remove.setToolTip("Remove rule")
        self.btn_remove.clicked.connect(lambda: self.removed.emit(self))
        layout.addWidget(self.btn_remove)

    def _set_status(self, status):
        normalized = "N/A" if status in ("Not Applicable", "N/A") else status
        idx = self.status_combo.findData(normalized)
        if idx == -1:
            idx = self.status_combo.findText(status)
        self.status_combo.setCurrentIndex(idx if idx >= 0 else 0)

    @property
    def data(self):
        return {
            "text": self.text_edit.text().strip(),
            "owner": self.owner_edit.text().strip(),
            "due": self.due_edit.text().strip(),
            "status": self.status_combo.currentData() or self.status_combo.currentText(),
            "comment": self.comment,
        }

class ChecklistCategoryCard(QFrame):
    def __init__(
        self,
        parent,
        name,
        description,
        rules,
        icon_color,
        on_change,
        on_delete,
        is_template=False,
        theme="Light",
    ):
        super().__init__(parent)
        self.setObjectName("checklistCard")
        self._loading = False
        self._on_change = on_change
        self._on_delete = on_delete
        self._is_template = is_template
        self._icon_color = icon_color
        self.theme = theme
        self._build_ui()
        self.set_data(name, description, rules)
        apply_layered_elevation(self, level="secondary", theme=self.theme)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(6, 6, 6, 6)
        outer.setSpacing(6)

        header_frame = QFrame()
        header_frame.setObjectName("checklistCardHeader")
        header_layout = QHBoxLayout(header_frame)
        header_layout.setContentsMargins(6, 4, 6, 4)
        header_layout.setSpacing(6)
        self.btn_toggle = QToolButton()
        self.btn_toggle.setCheckable(True)
        self.btn_toggle.setChecked(True)
        self.btn_toggle.setToolTip("Collapse category")
        self.btn_toggle.clicked.connect(self._toggle_collapsed)
        header_layout.addWidget(self.btn_toggle)

        self.name_edit = QLineEdit()
        self.name_edit.setObjectName("checklistName")
        self.name_edit.setPlaceholderText("Category")
        name_font = QFont(self.name_edit.font())
        name_font.setBold(True)
        name_font.setPointSize(max(10, name_font.pointSize() + 1))
        self.name_edit.setFont(name_font)
        self.name_edit.editingFinished.connect(self._trigger_change)
        header_layout.addWidget(self.name_edit, stretch=1)

        self.btn_add_rule = QPushButton("Add Rule")
        self.btn_add_rule.setObjectName("checklistAddRuleBtn")
        self.btn_add_rule.setIcon(Icons.get_icon(Icons.PLUS, self._icon_color))
        self.btn_add_rule.clicked.connect(self.add_rule)
        header_layout.addWidget(self.btn_add_rule)

        self.btn_delete_category = QToolButton()
        self.btn_delete_category.setObjectName("checklistDeleteBtn")
        self.btn_delete_category.setIcon(Icons.get_icon(Icons.TRASH, self._icon_color))
        self.btn_delete_category.setToolTip("Delete category")
        self.btn_delete_category.clicked.connect(self._delete_self)
        header_layout.addWidget(self.btn_delete_category)
        outer.addWidget(header_frame)

        self.desc_edit = QLineEdit()
        self.desc_edit.setObjectName("checklistDesc")
        self.desc_edit.setPlaceholderText("Describe this category...")
        self.desc_edit.editingFinished.connect(self._trigger_change)
        self.desc_edit.setFixedHeight(28)
        outer.addWidget(self.desc_edit)

        self.summary_widget = QWidget()
        summary_layout = QHBoxLayout(self.summary_widget)
        summary_layout.setContentsMargins(0, 0, 0, 0)
        summary_layout.setSpacing(8)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(False)
        self.progress.setFixedHeight(8)
        summary_layout.addWidget(self.progress, stretch=1)

        self.summary_label = QLabel("0/0 Verified")
        self.summary_label.setObjectName("checklistSummaryLabel")
        summary_layout.addWidget(self.summary_label)
        outer.addWidget(self.summary_widget)

        self.rules_scroll = QScrollArea()
        self.rules_scroll.setWidgetResizable(True)
        self.rules_scroll.setFrameShape(QFrame.NoFrame)
        self.rules_container = QWidget()
        self.rules_container.setObjectName("checklistRulesContainer")
        self.rule_layout = QVBoxLayout(self.rules_container)
        self.rule_layout.setContentsMargins(0, 0, 0, 0)
        self.rule_layout.setSpacing(8)
        self.rule_layout.addStretch()
        self.rules_scroll.setWidget(self.rules_container)
        outer.addWidget(self.rules_scroll)

        self.rule_rows = []

        if self._is_template:
            self.progress.setVisible(False)
            self.summary_label.setVisible(False)

        self._toggle_collapsed()

    def _toggle_collapsed(self):
        expanded = self.btn_toggle.isChecked()
        self.btn_toggle.setArrowType(Qt.DownArrow if expanded else Qt.RightArrow)
        self.desc_edit.setVisible(expanded)
        self.summary_widget.setVisible(expanded and not self._is_template)
        self.rules_scroll.setVisible(expanded)

    def _delete_self(self):
        if self._on_delete:
            self._on_delete(self)

    def _on_table_item_changed(self, _item):
        self._trigger_change()

    def _trigger_change(self):
        if self._loading:
            return
        self.update_summary()
        if self._on_change:
            self._on_change()

    def set_data(self, name, description, rules):
        self._loading = True
        self.name_edit.setText(name)
        self.desc_edit.setText(description)
        self._clear_rules()
        for rule in rules:
            if isinstance(rule, dict):
                text = rule.get("text", "Rule")
                owner = rule.get("owner", "")
                due = rule.get("due", "")
                status = rule.get("status", "No")
                comment = rule.get("comment", "")
            else:
                text = str(rule)
                owner = ""
                due = ""
                status = "No"
                comment = ""
            self._append_rule(text, owner, due, status, comment)
        self._loading = False
        self.update_summary()

    def _append_rule(self, text, owner, due, status, comment=""):
        row = ChecklistRuleRow(text, owner, due, status, comment, icon_color=self._icon_color)
        row.changed.connect(self._trigger_change)
        row.removed.connect(self._remove_rule_row)
        insert_pos = self.rule_layout.count() - 1
        self.rule_layout.insertWidget(insert_pos, row)
        self.rule_rows.append(row)
        return row

    def _clear_rules(self):
        for row in list(self.rule_rows):
            self._remove_rule_row(row)

    def add_rule(self):
        self._append_rule("New Rule", "", "", "No", "")
        self._trigger_change()

    def _remove_rule_row(self, row):
        if row in self.rule_rows:
            self.rule_rows.remove(row)
            row.setParent(None)
            row.deleteLater()
            self._trigger_change()

    def get_name(self):
        return self.name_edit.text().strip()

    def get_description(self):
        return self.desc_edit.text().strip()

    def get_rules(self):
        return [row.data for row in self.rule_rows]

    def get_stats(self):
        total_rules = len(self.rule_rows)
        checked_rules = sum(1 for row in self.rule_rows if row.data.get("status") == "Yes")
        return total_rules, checked_rules

    def update_summary(self):
        total_rules, checked_rules = self.get_stats()
        percent = int((checked_rules / total_rules) * 100) if total_rules else 0
        self.progress.setValue(percent)
        self.progress.setFormat(f"{percent}%")
        self.summary_label.setText(f"{checked_rules}/{total_rules} verified")


class ChecklistWidget(QWidget):
    def __init__(self, parent_tab, is_template=False):
        super().__init__()
        self.parent_tab = parent_tab
        self.is_template = is_template
        self._loading = False
        self.category_cards = []
        self.fallback_steps = {
            "Schematic": {
                "description": "Schematic checks to ensure electrical correctness before layout.",
                "rules": [
                    "Electrical Rules Check (ERC)",
                    "Netlist Verification",
                    "Bill of Materials (BOM) Review",
                ],
            },
            "Layout": {
                "description": "PCB layout verification for placement, routing, and manufacturability.",
                "rules": [
                    "Design Rules Check (DRC)",
                    "Footprint Verification",
                    "Component Placement Review",
                    "Critical Routing / Impedance",
                    "Silkscreen & Polarity Check",
                    "3D Model Fit Check",
                ],
            },
            "Fabrication": {
                "description": "Outputs and checks required for manufacturing handoff.",
                "rules": [
                    "Gerber Generation & Review",
                    "Drill Files Generated",
                ],
            },
            "Assembly": {
                "description": "Assembly files and checks required for build.",
                "rules": [
                    "Pick & Place File Generated",
                ],
            },
        }
        self.setup_ui()

    def setup_ui(self):
        self.setObjectName("checklistRoot")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(12)

        theme = self.parent_tab.logic.settings.get("theme", "Light") if hasattr(self.parent_tab, "logic") else "Light"
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        self.icon_color = icon_color
        self.theme = theme

        hero_frame = QFrame()
        hero_frame.setObjectName("checklistHero")
        hero_layout = QVBoxLayout(hero_frame)
        hero_layout.setContentsMargins(14, 12, 14, 12)
        hero_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("Checklist")
        title.setObjectName("checklistTitle")
        title_row.addWidget(title)
        title_row.addStretch()
        self.lbl_summary = QLabel("Verified 0/0")
        self.lbl_summary.setObjectName("checklistSummary")
        title_row.addWidget(self.lbl_summary)
        hero_layout.addLayout(title_row)

        subtitle = QLabel("Track every QA step before handing off to manufacturing.")
        subtitle.setObjectName("checklistSummaryDesc")
        hero_layout.addWidget(subtitle)

        self.progress = QProgressBar()
        self.progress.setObjectName("checklistProgress")
        self.progress.setRange(0, 100)
        self.progress.setTextVisible(True)
        self.progress.setFormat("%v% Verified")
        hero_layout.addWidget(self.progress)

        action_row = QHBoxLayout()
        action_row.setSpacing(10)
        btn_add_category = QPushButton("Add Category")
        btn_add_category.setObjectName("checklistHeaderBtn")
        btn_add_category.setIcon(Icons.get_icon(Icons.PLUS, icon_color))
        btn_add_category.clicked.connect(self.add_category)
        action_row.addWidget(btn_add_category)

        btn_export = QPushButton("Export Report")
        btn_export.setObjectName("checklistHeaderBtn")
        btn_export.setIcon(Icons.get_icon(Icons.DOC, icon_color))
        btn_export.clicked.connect(self.export_report)
        action_row.addWidget(btn_export)

        if not self.is_template:
            btn_load = QPushButton("Load Template")
            btn_load.setObjectName("checklistHeaderBtn")
            btn_load.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
            btn_load.clicked.connect(self.open_template_dialog)
            action_row.addWidget(btn_load)

        action_row.addStretch()
        hero_layout.addLayout(action_row)

        layout.addWidget(hero_frame)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        self.scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll.setMinimumHeight(320)

        self.container = QWidget()
        self.card_layout = QVBoxLayout(self.container)
        self.card_layout.setSpacing(6)
        self.card_layout.setContentsMargins(0, 0, 0, 0)
        self.card_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)

    def _clear_categories(self):
        for card in self.category_cards:
            card.setParent(None)
            card.deleteLater()
        self.category_cards = []
        while self.card_layout.count() > 1:
            item = self.card_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()

    def _insert_card(self, card):
        self.category_cards.append(card)
        insert_at = max(0, self.card_layout.count() - 1)
        self.card_layout.insertWidget(insert_at, card)

    def load_data(self, data):
        self._loading = True
        self._clear_categories()

        if not data and not self.is_template:
            if hasattr(self.parent_tab, "logic"):
                templates = self.parent_tab.logic.settings.get("checklist_templates", {})
                data = templates.get("Standard", {})

        if data:
            data = self._normalize_legacy_data(data)
        if not data:
            data = self._build_fallback_data()

        for step, rules in data.items():
            description, rule_list = self._unpack_category(step, rules)
            card = ChecklistCategoryCard(
                self,
                step,
                description,
                rule_list,
                self.icon_color,
                self._on_card_changed,
                self._delete_category,
                is_template=self.is_template,
                theme=self.theme,
            )
            self._insert_card(card)

        self._loading = False
        self.update_progress()

    def get_data(self):
        data = {}
        for idx, card in enumerate(self.category_cards):
            name = card.get_name() or f"Category {idx + 1}"
            data[name] = {
                "description": card.get_description(),
                "rules": card.get_rules(),
            }
        return data

    def add_category(self):
        card = ChecklistCategoryCard(
            self,
            "New Category",
            "",
            [],
            self.icon_color,
            self._on_card_changed,
            self._delete_category,
            is_template=self.is_template,
            theme=self.theme,
        )
        self._insert_card(card)
        card.name_edit.setFocus()
        card.name_edit.selectAll()
        self._on_card_changed()

    def _delete_category(self, card):
        if card not in self.category_cards:
            return
        self.category_cards.remove(card)
        card.setParent(None)
        card.deleteLater()
        self._on_card_changed()

    def _on_card_changed(self):
        if self._loading:
            return
        self.update_progress()
        if hasattr(self.parent_tab, "sync_checklist_from_ui"):
            self.parent_tab.sync_checklist_from_ui()

    def update_progress(self):
        total_rules = 0
        checked_rules = 0

        for card in self.category_cards:
            stats = card.get_stats()
            total_rules += stats[0]
            checked_rules += stats[1]

        val = int((checked_rules / total_rules) * 100) if total_rules else 0
        self.progress.setValue(val)
        self.progress.setFormat(f"{val}%")
        self.progress.setProperty("complete", val == 100)
        self.progress.style().unpolish(self.progress)
        self.progress.style().polish(self.progress)

        summary = f"{checked_rules}/{total_rules} verified"
        self.lbl_summary.setText(summary)

    def export_report(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save Report", "Checklist_Report.txt", "Text Files (*.txt)")
        if not path:
            return

        data = self.get_data()
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"PCB Checklist Report - {QDateTime.currentDateTime().toString()}\n")
            f.write("=" * 50 + "\n\n")

            for category, entry in data.items():
                desc = entry.get("description", "")
                desc_text = f" - {desc}" if desc else ""
                f.write(f"{category}{desc_text}\n")
                for rule in entry.get("rules", []):
                    status = rule.get("status", "No")
                    comment = f" Note: {rule.get('comment', '')}" if rule.get("comment") else ""
                    owner = f" Owner: {rule.get('owner', '')}" if rule.get("owner") else ""
                    due = f" Due: {rule.get('due', '')}" if rule.get("due") else ""
                    f.write(f"    [{status}] {rule.get('text', '')}{comment}{owner}{due}\n")
                f.write("\n")

        QMessageBox.information(self, "Exported", "Checklist report saved.")

    def open_template_dialog(self):
        logic = getattr(self.parent_tab, "logic", None)
        if not logic:
            return

        templates = logic.settings.get("checklist_templates", {})
        if not templates:
            QMessageBox.warning(self, "No Templates", "No templates defined in Settings.")
            return

        name, ok = QInputDialog.getItem(self, "Select Template", "Template:", list(templates.keys()), 0, False)
        if ok and name:
            data = templates[name]
            import copy
            self.load_data(copy.deepcopy(data))
            if hasattr(self.parent_tab, "sync_checklist_from_ui"):
                self.parent_tab.sync_checklist_from_ui()

    def _build_fallback_data(self):
        data = {}
        for category, info in self.fallback_steps.items():
            data[category] = {
                "description": info.get("description", ""),
                "rules": [
                    {"text": r, "owner": "", "due": "", "status": "No", "comment": ""}
                    for r in info.get("rules", [])
                ],
            }
        return data

    def _normalize_legacy_data(self, data):
        if not isinstance(data, dict):
            return data
        has_colon_keys = any(isinstance(k, str) and ":" in k for k in data.keys())
        has_new_format = any(isinstance(v, dict) and "rules" in v for v in data.values())
        if not has_colon_keys or has_new_format:
            return data

        new_data = {}
        for key, rules in data.items():
            if isinstance(rules, bool):
                rules = []
            if isinstance(key, str) and ":" in key:
                category, rule = key.split(":", 1)
                category = category.strip()
                rule = rule.strip()
                entry = new_data.setdefault(category, {"description": "", "rules": []})
                if rules:
                    entry["rules"].extend(rules)
                else:
                    entry["rules"].append(
                        {"text": rule, "owner": "", "due": "", "status": "No"}
                    )
            else:
                if isinstance(rules, dict) and "rules" in rules:
                    new_data[key] = rules
                elif isinstance(rules, list):
                    new_data[key] = {"description": "", "rules": rules}
                else:
                    new_data[key] = {"description": "", "rules": []}
        return new_data

    def _unpack_category(self, _step, rules):
        if isinstance(rules, dict) and "rules" in rules:
            description = rules.get("description", "")
            rule_list = rules.get("rules", []) or []
            return description, rule_list
        if isinstance(rules, list):
            return "", rules
        if isinstance(rules, bool):
            return "", []
        return "", []
