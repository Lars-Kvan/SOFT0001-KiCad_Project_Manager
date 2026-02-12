from copy import deepcopy

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QSizePolicy,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QFrame,
    QHeaderView,
)


STATUS_OPTIONS = ("Draft", "Review", "Approved", "Implemented", "Verified", "Deprecated")
PRIORITY_OPTIONS = ("Low", "Medium", "High", "Critical")
TYPE_OPTIONS = (
    "Functional",
    "Non-Functional",
    "Interface",
    "Safety",
    "Performance",
    "Regulatory",
    "Test",
    "Manufacturing",
    "Usability",
    "Other",
)
CATEGORY_OPTIONS = (
    "General",
    "Schematic",
    "Layout",
    "BOM",
    "Fabrication",
    "Assembly",
    "Firmware",
    "Mechanical",
    "Documentation",
    "Compliance",
    "Other",
)
VERIFICATION_OPTIONS = ("Test", "Analysis", "Inspection", "Demonstration", "Review", "Other")

COL_ID = 0
COL_TEXT = 1
COL_TYPE = 2
COL_CATEGORY = 3
COL_STATUS = 4
COL_PRIORITY = 5
_DARK_THEMES = {"Dark", "Teal Sand Dark"}


class SubRequirementRow(QWidget):
    def __init__(self, sub, status_options, priority_options, on_change, on_delete):
        super().__init__()
        self._on_change = on_change
        self._on_delete = on_delete

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(8)

        self.edit_id = QLineEdit(sub.get("id", ""))
        self.edit_id.setPlaceholderText("ID")
        self.edit_id.setFixedWidth(120)
        layout.addWidget(self.edit_id)

        self.edit_text = QLineEdit(sub.get("text", ""))
        self.edit_text.setPlaceholderText("Sub-requirement")
        self.edit_text.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        layout.addWidget(self.edit_text, stretch=1)

        self.combo_status = QComboBox()
        self.combo_status.addItems(list(status_options))
        self._ensure_value(self.combo_status, sub.get("status", STATUS_OPTIONS[0]))
        self.combo_status.setCurrentText(sub.get("status", STATUS_OPTIONS[0]))
        layout.addWidget(self.combo_status)

        self.combo_priority = QComboBox()
        self.combo_priority.addItems(list(priority_options))
        self._ensure_value(self.combo_priority, sub.get("priority", PRIORITY_OPTIONS[1]))
        self.combo_priority.setCurrentText(sub.get("priority", PRIORITY_OPTIONS[1]))
        layout.addWidget(self.combo_priority)

        self.btn_delete = QToolButton()
        self.btn_delete.setText("Remove")
        self.btn_delete.clicked.connect(self._delete_clicked)
        layout.addWidget(self.btn_delete)

        self.edit_id.editingFinished.connect(self._emit_change)
        self.edit_text.editingFinished.connect(self._emit_change)
        self.combo_status.currentTextChanged.connect(lambda _=None: self._emit_change())
        self.combo_priority.currentTextChanged.connect(lambda _=None: self._emit_change())

    def _ensure_value(self, combo, value):
        if value and combo.findText(value) == -1:
            combo.addItem(value)

    def _emit_change(self):
        if self._on_change:
            self._on_change()

    def _delete_clicked(self):
        if self._on_delete:
            self._on_delete(self)

    def get_data(self):
        return {
            "id": self.edit_id.text().strip(),
            "text": self.edit_text.text().strip(),
            "status": self.combo_status.currentText(),
            "priority": self.combo_priority.currentText(),
        }

class RequirementsView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self._loading = False
        self._detail_loading = False
        self._sub_loading = False
        self._current_row = None
        theme = self.logic.settings.get("theme", "Light")
        panel_theme = "Dark" if theme in _DARK_THEMES else "Light"
        self.setObjectName("projectPanel")
        self.setProperty("projectTheme", panel_theme)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        self.btn_add = QPushButton("Add Requirement")
        self.btn_add.clicked.connect(self.add_req)
        self.btn_del = QPushButton("Delete Selected")
        self.btn_del.clicked.connect(self.del_req)
        self.btn_dup = QPushButton("Duplicate")
        self.btn_dup.clicked.connect(self.duplicate_req)
        self.btn_add_sub = QPushButton("Add Sub-Requirement")
        self.btn_add_sub.clicked.connect(self.add_sub_req)
        toolbar.addWidget(self.btn_add)
        toolbar.addWidget(self.btn_del)
        toolbar.addWidget(self.btn_dup)
        toolbar.addWidget(self.btn_add_sub)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        filter_row = QHBoxLayout()
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("Search requirements...")
        self.search_edit.textChanged.connect(self.apply_filters)
        self.search_edit.setMinimumWidth(240)
        filter_row.addWidget(self.search_edit)

        self.filter_status = self._make_filter_combo("All Statuses", STATUS_OPTIONS)
        self.filter_type = self._make_filter_combo("All Types", TYPE_OPTIONS)
        self.filter_category = self._make_filter_combo("All Categories", CATEGORY_OPTIONS)
        self.filter_priority = self._make_filter_combo("All Priorities", PRIORITY_OPTIONS)
        for combo in (self.filter_status, self.filter_type, self.filter_category, self.filter_priority):
            combo.setMinimumWidth(140)
        filter_row.addWidget(self.filter_status)
        filter_row.addWidget(self.filter_type)
        filter_row.addWidget(self.filter_category)
        filter_row.addWidget(self.filter_priority)
        layout.addLayout(filter_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(self._build_table_panel())
        splitter.addWidget(self._build_detail_panel())
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([700, 520])
        layout.addWidget(splitter)

    def _build_table_panel(self):
        wrapper = QFrame()
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper.setObjectName("projectPanelSection")

        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(
            ["ID", "Requirement", "Type", "Category", "Status", "Priority"]
        )
        self.table.setMinimumWidth(520)
        self.table.setColumnWidth(COL_ID, 90)
        self.table.setColumnWidth(COL_TYPE, 120)
        self.table.setColumnWidth(COL_CATEGORY, 140)
        self.table.setColumnWidth(COL_STATUS, 120)
        self.table.setColumnWidth(COL_PRIORITY, 110)
        self.table.horizontalHeader().setSectionResizeMode(COL_TEXT, QHeaderView.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.verticalHeader().setDefaultSectionSize(36)
        self.table.setWordWrap(True)
        self.table.setAlternatingRowColors(True)
        self.table.setStyleSheet(
            """
            QTableWidget {
                border: 1px solid rgba(15, 23, 42, 0.12);
                border-radius: 12px;
                padding: 4px;
                background-color: rgba(255, 255, 255, 0.92);
            }
            QTableWidget::item {
                padding: 6px 10px;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 rgba(37, 99, 235, 0.35), stop:1 rgba(14, 165, 233, 0.3));
                color: #fff;
            }
            """
        )
        self.table.itemChanged.connect(self.on_item_changed)
        self.table.itemSelectionChanged.connect(self.on_row_selected)
        wrapper_layout.addWidget(self.table)
        return wrapper

    def _build_detail_panel(self):
        self.detail_panel = QFrame()
        self.detail_panel.setObjectName("projectPanelSection")
        layout = QVBoxLayout(self.detail_panel)
        layout.setSpacing(10)

        meta_group = QGroupBox("Requirement Details")
        meta_layout = QFormLayout(meta_group)

        self.id_edit = QLineEdit()
        self.id_edit.editingFinished.connect(self._ensure_current_id)
        self.id_edit.textChanged.connect(lambda text: self._update_selected("id", text))
        meta_layout.addRow("ID", self.id_edit)

        self.text_edit = QLineEdit()
        self.text_edit.textChanged.connect(lambda text: self._update_selected("text", text))
        meta_layout.addRow("Requirement", self.text_edit)

        self.type_combo = self._make_detail_combo(TYPE_OPTIONS, "type")
        meta_layout.addRow("Type", self.type_combo)

        self.category_combo = self._make_detail_combo(CATEGORY_OPTIONS, "category", editable=True)
        meta_layout.addRow("Category", self.category_combo)

        self.status_combo = self._make_detail_combo(STATUS_OPTIONS, "status")
        meta_layout.addRow("Status", self.status_combo)

        self.priority_combo = self._make_detail_combo(PRIORITY_OPTIONS, "priority")
        meta_layout.addRow("Priority", self.priority_combo)

        self.owner_edit = QLineEdit()
        self.owner_edit.textChanged.connect(lambda text: self._update_selected("owner", text))
        meta_layout.addRow("Owner", self.owner_edit)

        self.source_edit = QLineEdit()
        self.source_edit.textChanged.connect(lambda text: self._update_selected("source", text))
        meta_layout.addRow("Source", self.source_edit)

        self.verification_combo = self._make_detail_combo(VERIFICATION_OPTIONS, "verification")
        meta_layout.addRow("Verification", self.verification_combo)

        self.due_edit = QLineEdit()
        self.due_edit.setPlaceholderText("YYYY-MM-DD")
        self.due_edit.textChanged.connect(lambda text: self._update_selected("due", text))
        meta_layout.addRow("Due Date", self.due_edit)

        self.tags_edit = QLineEdit()
        self.tags_edit.setPlaceholderText("comma,separated,tags")
        self.tags_edit.textChanged.connect(lambda text: self._update_selected("tags", text))
        meta_layout.addRow("Tags", self.tags_edit)

        self.notes_edit = QPlainTextEdit()
        self.notes_edit.setMinimumHeight(120)
        self.notes_edit.textChanged.connect(self._on_notes_changed)
        meta_layout.addRow("Notes", self.notes_edit)

        layout.addWidget(meta_group)

        sub_group = QGroupBox("Sub-Requirements")
        sub_layout = QVBoxLayout(sub_group)
        self.sub_summary = QLabel("Sub-requirements: 0")
        sub_layout.addWidget(self.sub_summary)

        self.sub_list = QListWidget()
        self.sub_list.setSpacing(6)
        self.sub_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.sub_list.setMinimumHeight(160)
        sub_layout.addWidget(self.sub_list)

        sub_btns = QHBoxLayout()
        self.btn_sub_add = QPushButton("Add Sub-Requirement")
        self.btn_sub_add.clicked.connect(self.add_sub_req)
        self.btn_sub_del = QPushButton("Delete Sub-Requirement")
        self.btn_sub_del.clicked.connect(self.del_sub_req)
        sub_btns.addWidget(self.btn_sub_add)
        sub_btns.addWidget(self.btn_sub_del)
        sub_btns.addStretch()
        sub_layout.addLayout(sub_btns)

        layout.addWidget(sub_group)
        layout.addStretch()
        self._set_detail_enabled(False)
        return self.detail_panel

    def _make_filter_combo(self, label, options):
        combo = QComboBox()
        combo.addItem(label)
        combo.addItems(list(options))
        combo.currentTextChanged.connect(self.apply_filters)
        return combo

    def _make_detail_combo(self, options, field, editable=False):
        combo = QComboBox()
        combo.addItems(list(options))
        combo.setEditable(editable)
        combo.currentTextChanged.connect(lambda text: self._update_selected(field, text))
        return combo

    def load_data(self, reqs):
        self._loading = True
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for idx, req in enumerate(reqs):
            normalized = self._normalize_requirement(req, fallback_id=f"REQ-{idx + 1:03d}")
            self._add_row(normalized)
        self.table.blockSignals(False)
        self._loading = False
        self.apply_filters()
        if self.table.rowCount() > 0:
            self.table.selectRow(0)

    def get_data(self):
        reqs = []
        existing_ids = set()
        for row in range(self.table.rowCount()):
            req = self._get_row_data(row)
            if not req:
                req = {}

            req["id"] = self._item_text(row, COL_ID)
            req["text"] = self._item_text(row, COL_TEXT)
            req["type"] = self._combo_text(self.table, row, COL_TYPE, TYPE_OPTIONS[0])
            req["category"] = self._combo_text(self.table, row, COL_CATEGORY, CATEGORY_OPTIONS[0])
            req["status"] = self._combo_text(self.table, row, COL_STATUS, STATUS_OPTIONS[0])
            req["priority"] = self._combo_text(self.table, row, COL_PRIORITY, PRIORITY_OPTIONS[1])
            req["tags"] = self._normalize_tags(req.get("tags", []))
            req["sub_requirements"] = self._normalize_sub_list(req.get("sub_requirements", []))

            if not req["id"].strip():
                req["id"] = self._next_requirement_id(existing_ids)

            existing_ids.add(req["id"])
            reqs.append(req)
        return reqs

    def add_req(self):
        next_id = self._next_requirement_id()
        req = self._normalize_requirement(
            {"id": next_id, "text": "New Requirement"},
            fallback_id=next_id,
        )
        row = self._add_row(req)
        self.table.selectRow(row)
        self.save_trigger()

    def del_req(self):
        row = self.table.currentRow()
        if row >= 0:
            self.table.removeRow(row)
            self._current_row = None
            self._set_detail_enabled(False)
            self.save_trigger()

    def duplicate_req(self):
        row = self.table.currentRow()
        if row < 0:
            return
        req = self._get_row_data(row)
        if not req:
            return
        cloned = deepcopy(req)
        cloned["id"] = self._next_requirement_id()
        new_row = self._add_row(cloned)
        self.table.selectRow(new_row)
        self.save_trigger()

    def add_sub_req(self):
        row = self._current_row
        if row is None:
            return
        req = self._get_row_data(row)
        if not req:
            return
        sub_id = self._next_sub_id(req)
        req.setdefault("sub_requirements", []).append(
            {"id": sub_id, "text": "New Sub-Requirement", "status": STATUS_OPTIONS[0], "priority": PRIORITY_OPTIONS[1]}
        )
        self._set_row_data(row, req)
        self._load_sub_requirements(req)
        self.save_trigger()

    def del_sub_req(self):
        row = self.sub_list.currentRow()
        if row < 0:
            return
        self.sub_list.takeItem(row)
        self._sync_sub_requirements()
        self.save_trigger()

    def on_item_changed(self, item):
        if self._loading:
            return
        row = item.row()
        req = self._get_row_data(row)
        if not req:
            return
        if item.column() == COL_ID:
            new_id = item.text().strip()
            if not new_id:
                new_id = self._next_requirement_id()
                self._set_item_text(row, COL_ID, new_id)
            req["id"] = new_id
        elif item.column() == COL_TEXT:
            req["text"] = item.text()
        self._set_row_data(row, req)
        if row == self._current_row:
            self._load_detail(req)
        self.save_trigger()

    def on_row_selected(self):
        row = self.table.currentRow()
        if row < 0:
            self._current_row = None
            self._set_detail_enabled(False)
            return
        self._current_row = row
        req = self._get_row_data(row)
        if not req:
            req = self._normalize_requirement({}, fallback_id=self._item_text(row, COL_ID))
            self._set_row_data(row, req)
        self._set_detail_enabled(True)
        self._load_detail(req)

    def _sync_sub_requirements(self):
        req = self._get_current_req()
        if not req:
            return
        req["sub_requirements"] = self._collect_sub_requirements()
        self._set_row_data(self._current_row, req)
        self._update_sub_summary(req["sub_requirements"])

    def apply_filters(self):
        search = self.search_edit.text().strip().lower()
        status_filter = self.filter_status.currentText()
        type_filter = self.filter_type.currentText()
        category_filter = self.filter_category.currentText()
        priority_filter = self.filter_priority.currentText()

        for row in range(self.table.rowCount()):
            req = self._get_row_data(row) or {}
            status = req.get("status", STATUS_OPTIONS[0])
            req_type = req.get("type", TYPE_OPTIONS[0])
            category = req.get("category", CATEGORY_OPTIONS[0])
            priority = req.get("priority", PRIORITY_OPTIONS[1])

            if status_filter != "All Statuses" and status != status_filter:
                self.table.setRowHidden(row, True)
                continue
            if type_filter != "All Types" and req_type != type_filter:
                self.table.setRowHidden(row, True)
                continue
            if category_filter != "All Categories" and category != category_filter:
                self.table.setRowHidden(row, True)
                continue
            if priority_filter != "All Priorities" and priority != priority_filter:
                self.table.setRowHidden(row, True)
                continue

            if search:
                haystack = " ".join(
                    [
                        str(req.get("id", "")),
                        str(req.get("text", "")),
                        str(req.get("type", "")),
                        str(req.get("category", "")),
                        str(req.get("status", "")),
                        str(req.get("priority", "")),
                        str(req.get("owner", "")),
                        str(req.get("source", "")),
                        str(req.get("verification", "")),
                        str(req.get("due", "")),
                        " ".join(self._normalize_tags(req.get("tags", []))),
                        str(req.get("notes", "")),
                        self._sub_text_blob(req.get("sub_requirements", [])),
                    ]
                ).lower()
                if search not in haystack:
                    self.table.setRowHidden(row, True)
                    continue

            self.table.setRowHidden(row, False)
        self.table.resizeRowsToContents()

    def save_trigger(self):
        if self._loading or self._detail_loading or self._sub_loading:
            return

    def _add_row(self, req):
        row = self.table.rowCount()
        self.table.insertRow(row)

        id_item = QTableWidgetItem(req.get("id", f"REQ-{row + 1:03d}"))
        id_item.setTextAlignment(Qt.AlignCenter)
        id_item.setData(Qt.ToolTipRole, id_item.text())
        id_item.setFlags(id_item.flags() | Qt.ItemIsEditable)
        text_item = QTableWidgetItem(req.get("text", ""))
        text_item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        text_item.setData(Qt.ToolTipRole, req.get("text", ""))
        text_item.setFlags(text_item.flags() | Qt.ItemIsEditable)
        self.table.setItem(row, COL_ID, id_item)
        self.table.setItem(row, COL_TEXT, text_item)

        self.table.setCellWidget(
            row,
            COL_TYPE,
            self._make_table_combo(TYPE_OPTIONS, req.get("type", TYPE_OPTIONS[0]), COL_TYPE),
        )
        self.table.setCellWidget(
            row,
            COL_CATEGORY,
            self._make_table_combo(CATEGORY_OPTIONS, req.get("category", CATEGORY_OPTIONS[0]), COL_CATEGORY, editable=True),
        )
        self.table.setCellWidget(
            row,
            COL_STATUS,
            self._make_table_combo(STATUS_OPTIONS, req.get("status", STATUS_OPTIONS[0]), COL_STATUS),
        )
        self.table.setCellWidget(
            row,
            COL_PRIORITY,
            self._make_table_combo(PRIORITY_OPTIONS, req.get("priority", PRIORITY_OPTIONS[1]), COL_PRIORITY),
        )

        self._set_row_data(row, req)
        self.table.resizeRowToContents(row)
        return row

    def _make_table_combo(self, options, current, column, editable=False):
        combo = QComboBox()
        combo.addItems(list(options))
        combo.setEditable(editable)
        self._ensure_combo_value(combo, current)
        combo.setCurrentText(current)
        combo.currentTextChanged.connect(lambda text, w=combo, c=column: self._on_table_combo_changed(w, c, text))
        return combo

    def _on_table_combo_changed(self, combo, column, text):
        if self._loading:
            return
        row = self._row_for_widget(combo, column)
        if row is None:
            return
        req = self._get_row_data(row)
        if not req:
            return
        if column == COL_TYPE:
            req["type"] = text
        elif column == COL_CATEGORY:
            req["category"] = text
        elif column == COL_STATUS:
            req["status"] = text
        elif column == COL_PRIORITY:
            req["priority"] = text
        self._set_row_data(row, req)
        if row == self._current_row:
            self._load_detail(req)
        self.save_trigger()

    def _row_for_widget(self, widget, column):
        for row in range(self.table.rowCount()):
            if self.table.cellWidget(row, column) is widget:
                return row
        return None

    def _get_row_data(self, row):
        item = self.table.item(row, COL_ID)
        if not item:
            return None
        data = item.data(Qt.UserRole)
        return data or {}

    def _set_row_data(self, row, req):
        item = self.table.item(row, COL_ID)
        if item:
            item.setData(Qt.UserRole, req)

    def _item_text(self, row, column):
        item = self.table.item(row, column)
        return item.text().strip() if item else ""

    def _set_item_text(self, row, column, text):
        item = self.table.item(row, column)
        if item:
            was_loading = self._loading
            self._loading = True
            item.setText(text)
            self._loading = was_loading

    def _combo_text(self, table, row, column, fallback):
        widget = table.cellWidget(row, column)
        if isinstance(widget, QComboBox):
            return widget.currentText()
        return fallback

    def _normalize_requirement(self, req, fallback_id):
        tags = req.get("tags", [])
        if isinstance(tags, str):
            tags = self._split_tags(tags)
        normalized = {
            "id": req.get("id", fallback_id),
            "text": req.get("text", ""),
            "status": req.get("status", STATUS_OPTIONS[0]),
            "priority": req.get("priority", PRIORITY_OPTIONS[1]),
            "type": req.get("type", TYPE_OPTIONS[0]),
            "category": req.get("category", CATEGORY_OPTIONS[0]),
            "owner": req.get("owner", ""),
            "source": req.get("source", ""),
            "verification": req.get("verification", VERIFICATION_OPTIONS[0]),
            "due": req.get("due", ""),
            "tags": tags,
            "notes": req.get("notes", ""),
            "sub_requirements": self._normalize_sub_list(req.get("sub_requirements", [])),
        }
        return normalized

    def _normalize_sub_list(self, subs):
        normalized = []
        for idx, sub in enumerate(subs or []):
            fallback_id = sub.get("id") if isinstance(sub, dict) else ""
            if not fallback_id:
                fallback_id = f"SUB-{idx + 1:03d}"
            normalized.append(self._normalize_sub_requirement(sub, fallback_id))
        return normalized

    def _normalize_sub_requirement(self, sub, fallback_id):
        if not isinstance(sub, dict):
            sub = {}
        return {
            "id": sub.get("id", fallback_id),
            "text": sub.get("text", ""),
            "status": sub.get("status", STATUS_OPTIONS[0]),
            "priority": sub.get("priority", PRIORITY_OPTIONS[1]),
        }

    def _next_requirement_id(self, existing_ids=None):
        ids = existing_ids or {self._item_text(r, COL_ID) for r in range(self.table.rowCount())}
        max_num = 0
        for req_id in ids:
            if req_id.startswith("REQ-"):
                try:
                    num = int(req_id.split("-")[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    continue
        return f"REQ-{max_num + 1:03d}"

    def _next_sub_id(self, req):
        parent_id = req.get("id", "REQ-000")
        prefix = f"{parent_id}."
        max_num = 0
        for sub in req.get("sub_requirements", []):
            sub_id = sub.get("id", "")
            if sub_id.startswith(prefix):
                try:
                    num = int(sub_id.split(prefix)[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    continue
        return f"{prefix}{max_num + 1}"

    def _load_detail(self, req):
        self._detail_loading = True
        self.id_edit.setText(req.get("id", ""))
        self.text_edit.setText(req.get("text", ""))
        self._ensure_combo_value(self.type_combo, req.get("type", TYPE_OPTIONS[0]))
        self._ensure_combo_value(self.category_combo, req.get("category", CATEGORY_OPTIONS[0]))
        self._ensure_combo_value(self.status_combo, req.get("status", STATUS_OPTIONS[0]))
        self._ensure_combo_value(self.priority_combo, req.get("priority", PRIORITY_OPTIONS[1]))
        self._ensure_combo_value(self.verification_combo, req.get("verification", VERIFICATION_OPTIONS[0]))
        self.type_combo.setCurrentText(req.get("type", TYPE_OPTIONS[0]))
        self.category_combo.setCurrentText(req.get("category", CATEGORY_OPTIONS[0]))
        self.status_combo.setCurrentText(req.get("status", STATUS_OPTIONS[0]))
        self.priority_combo.setCurrentText(req.get("priority", PRIORITY_OPTIONS[1]))
        self.owner_edit.setText(req.get("owner", ""))
        self.source_edit.setText(req.get("source", ""))
        self.verification_combo.setCurrentText(req.get("verification", VERIFICATION_OPTIONS[0]))
        self.due_edit.setText(req.get("due", ""))
        self.tags_edit.setText(", ".join(self._normalize_tags(req.get("tags", []))))
        self.notes_edit.setPlainText(req.get("notes", ""))
        self._load_sub_requirements(req)
        self._detail_loading = False

    def _load_sub_requirements(self, req):
        self._sub_loading = True
        self.sub_list.clear()
        for idx, sub in enumerate(req.get("sub_requirements", [])):
            sub_req = self._normalize_sub_requirement(sub, fallback_id=f"SUB-{idx + 1:03d}")
            row_widget = SubRequirementRow(
                sub_req,
                STATUS_OPTIONS,
                PRIORITY_OPTIONS,
                self._on_sub_row_changed,
                self._delete_sub_row,
            )
            item = QListWidgetItem()
            item.setSizeHint(row_widget.sizeHint())
            self.sub_list.addItem(item)
            self.sub_list.setItemWidget(item, row_widget)
        self._update_sub_summary(req.get("sub_requirements", []))
        self._sub_loading = False

    def _on_sub_row_changed(self):
        if self._sub_loading:
            return
        self._sync_sub_requirements()
        self.save_trigger()

    def _delete_sub_row(self, row_widget):
        for row in range(self.sub_list.count()):
            item = self.sub_list.item(row)
            if self.sub_list.itemWidget(item) is row_widget:
                self.sub_list.takeItem(row)
                self._sync_sub_requirements()
                self.save_trigger()
                break

    def _collect_sub_requirements(self):
        subs = []
        for row in range(self.sub_list.count()):
            item = self.sub_list.item(row)
            widget = self.sub_list.itemWidget(item)
            if not isinstance(widget, SubRequirementRow):
                continue
            sub = widget.get_data()
            if not sub["id"].strip():
                sub["id"] = f"SUB-{row + 1:03d}"
            subs.append(sub)
        return subs

    def _update_sub_summary(self, subs):
        total = len(subs)
        verified = len([s for s in subs if s.get("status") == "Verified"])
        self.sub_summary.setText(f"Sub-requirements: {total} (Verified: {verified})")

    def _update_selected(self, field, value):
        if self._detail_loading or self._current_row is None:
            return
        req = self._get_row_data(self._current_row)
        if not req:
            return
        if field == "tags":
            req[field] = self._split_tags(value)
        else:
            req[field] = value
        self._set_row_data(self._current_row, req)

        if field == "id":
            self._set_item_text(self._current_row, COL_ID, value)
        elif field == "text":
            self._set_item_text(self._current_row, COL_TEXT, value)
        elif field == "type":
            self._set_combo_text(self.table, self._current_row, COL_TYPE, value)
        elif field == "category":
            self._set_combo_text(self.table, self._current_row, COL_CATEGORY, value)
        elif field == "status":
            self._set_combo_text(self.table, self._current_row, COL_STATUS, value)
        elif field == "priority":
            self._set_combo_text(self.table, self._current_row, COL_PRIORITY, value)

        self.save_trigger()

    def _set_combo_text(self, table, row, column, value):
        widget = table.cellWidget(row, column)
        if isinstance(widget, QComboBox) and widget.currentText() != value:
            self._ensure_combo_value(widget, value)
            widget.setCurrentText(value)

    def _on_notes_changed(self):
        if self._detail_loading or self._current_row is None:
            return
        req = self._get_row_data(self._current_row)
        if not req:
            return
        req["notes"] = self.notes_edit.toPlainText()
        self._set_row_data(self._current_row, req)
        self.save_trigger()

    def _ensure_current_id(self):
        if self._current_row is None:
            return
        current = self.id_edit.text().strip()
        if not current:
            new_id = self._next_requirement_id()
            self.id_edit.setText(new_id)
            self._set_item_text(self._current_row, COL_ID, new_id)

    def _set_detail_enabled(self, enabled):
        self.detail_panel.setEnabled(enabled)

    def _get_current_req(self):
        if self._current_row is None:
            return None
        return self._get_row_data(self._current_row)

    def _split_tags(self, text):
        if not text:
            return []
        if isinstance(text, list):
            return [t.strip() for t in text if t.strip()]
        return [t.strip() for t in text.split(",") if t.strip()]

    def _normalize_tags(self, tags):
        if isinstance(tags, list):
            return [t.strip() for t in tags if t.strip()]
        if isinstance(tags, str):
            return self._split_tags(tags)
        return []

    def _ensure_combo_value(self, combo, value):
        if not value:
            return
        if combo.findText(value) == -1:
            combo.addItem(value)

    def _sub_text_blob(self, subs):
        parts = []
        for sub in subs or []:
            if isinstance(sub, dict):
                parts.append(sub.get("id", ""))
                parts.append(sub.get("text", ""))
                parts.append(sub.get("status", ""))
        return " ".join(parts)
