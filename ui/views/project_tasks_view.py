from datetime import datetime
from PySide6.QtCore import Qt, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QGroupBox, QLabel, QLineEdit, QTextEdit,
    QComboBox, QPushButton, QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem,
    QFrame, QProgressBar, QAbstractItemView, QDateEdit, QSizePolicy
)
from PySide6.QtGui import QColor

from ui.widgets.progress_utils import style_progress_bar
from ui.widgets.stats_card import StatsCard

try:
    from ui.resources.icons import Icons
except ImportError:
    from .resources.icons import Icons


DEFAULT_CATEGORIES = ["Backlog", "Specification", "Design", "Layout", "Build", "Test", "Docs", "Other"]
DEFAULT_STATUSES = ["To Do", "In Progress", "Blocked", "Done"]
_DARK_THEMES = {"Dark", "Teal Sand Dark"}
STATUS_COLORS = {
    "To Do": "#5B6B7A",
    "In Progress": "#3A7FF6",
    "Blocked": "#D64545",
    "Done": "#2DA87A",
}
PRIORITIES = ["Low", "Normal", "High", "Critical"]
PRIORITY_COLORS = {
    "Low": "#5E6C84",
    "Normal": "#3498db",
    "High": "#e67e22",
    "Critical": "#e74c3c",
}


class ProjectTasksView(QWidget):
    """
    Task board (no time tracking): tasks + subtasks with status, priority, due date.
    Data persists in logic.settings['project_registry'][project]['tasks'].
    """

    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.current_project = ""
        self.tasks = []
        theme = self.logic.settings.get("theme", "Light")
        panel_theme = "Dark" if theme in _DARK_THEMES else "Light"
        self.setObjectName("projectPanel")
        self.setProperty("projectTheme", panel_theme)
        self._categories = list(DEFAULT_CATEGORIES)
        self._filters = {"status": "All", "category": "All", "priority": "All", "search": ""}
        self._build_ui()

    # ---------- UI ----------
    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Summary row
        self.summary_bar = QHBoxLayout()
        self.cards = {
            "total": self._stat_card("Total", "#3A7FF6"),
            "active": self._stat_card("Active", "#F6C344"),
            "done": self._stat_card("Done", "#2DA87A"),
            "overdue": self._stat_card("Overdue", "#e74c3c"),
        }
        for c in self.cards.values():
            self.summary_bar.addWidget(c["frame"])
        self.summary_bar.addStretch()
        layout.addLayout(self.summary_bar)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter, 1)

        # LEFT: filters + tree
        left_box = QGroupBox("Tasks")
        left_box.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        left_box.setObjectName("projectPanelSection")
        left = QVBoxLayout(left_box)

        btn_row = QHBoxLayout()
        self.btn_new = QPushButton("New")
        self.btn_new.clicked.connect(self.add_task)
        self.btn_delete = QPushButton("Delete")
        self.btn_delete.clicked.connect(self.remove_task)
        self.btn_import = QPushButton("Import from Kanban")
        self.btn_import.clicked.connect(self.import_from_kanban)
        btn_row.addWidget(self.btn_new)
        btn_row.addWidget(self.btn_delete)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_import)
        left.addLayout(btn_row)

        filter_row = QHBoxLayout()
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search tasks…")
        self.search_box.textChanged.connect(self._on_filters_changed)
        self.filter_status = QComboBox()
        self.filter_status.addItems(["All"] + DEFAULT_STATUSES)
        self.filter_status.currentTextChanged.connect(self._on_filters_changed)
        self.filter_category = QComboBox()
        self.filter_category.addItems(["All"] + self._categories)
        self.filter_category.currentTextChanged.connect(self._on_filters_changed)
        self.filter_priority = QComboBox()
        self.filter_priority.addItems(["All"] + PRIORITIES)
        self.filter_priority.currentTextChanged.connect(self._on_filters_changed)
        filter_row.addWidget(self.search_box, 3)
        filter_row.addWidget(self.filter_status, 1)
        filter_row.addWidget(self.filter_category, 1)
        filter_row.addWidget(self.filter_priority, 1)
        left.addLayout(filter_row)

        self.tree = TaskTree(self)
        self.tree.setHeaderHidden(True)
        self.tree.itemSelectionChanged.connect(self._on_tree_selection)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIndentation(14)
        left.addWidget(self.tree, 1)
        splitter.addWidget(left_box)

        # RIGHT: details
        right_box = QGroupBox("Details")
        right = QVBoxLayout(right_box)
        right_box.setObjectName("projectPanelSection")
        splitter.addWidget(right_box)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

        form1 = QHBoxLayout()
        form1.addWidget(QLabel("Title:"))
        self.edit_name = QLineEdit()
        self.edit_name.textEdited.connect(self._on_task_changed)
        form1.addWidget(self.edit_name, 1)
        right.addLayout(form1)

        form2 = QHBoxLayout()
        form2.addWidget(QLabel("Category:"))
        self.combo_category = QComboBox()
        self.combo_category.addItems(self._categories)
        self.combo_category.currentTextChanged.connect(self._on_task_changed)
        add_cat = QPushButton("+")
        add_cat.setFixedWidth(28)
        add_cat.clicked.connect(self._add_category)
        form2.addWidget(self.combo_category, 1)
        form2.addWidget(add_cat)
        form2.addWidget(QLabel("Status:"))
        self.combo_status = QComboBox()
        self.combo_status.addItems(DEFAULT_STATUSES)
        self.combo_status.currentTextChanged.connect(self._on_task_changed)
        form2.addWidget(self.combo_status, 1)
        form2.addWidget(QLabel("Priority:"))
        self.combo_priority = QComboBox()
        self.combo_priority.addItems(PRIORITIES)
        self.combo_priority.currentTextChanged.connect(self._on_task_changed)
        form2.addWidget(self.combo_priority, 1)
        right.addLayout(form2)

        form3 = QHBoxLayout()
        form3.addWidget(QLabel("Due:"))
        self.date_due = QDateEdit()
        self.date_due.setCalendarPopup(True)
        self.date_due.setDisplayFormat("yyyy-MM-dd")
        self.date_due.setDate(QDate.currentDate())
        self.date_due.dateChanged.connect(self._on_task_changed)
        form3.addWidget(self.date_due, 1)
        right.addLayout(form3)

        right.addWidget(QLabel("Notes:"))
        self.edit_notes = QTextEdit()
        self.edit_notes.textChanged.connect(self._on_task_changed)
        self.edit_notes.setPlaceholderText("Short description, acceptance criteria, links…")
        right.addWidget(self.edit_notes, 2)

        # Subtasks box
        sub_box = QGroupBox("Subtasks")
        sub_layout = QVBoxLayout(sub_box)
        sub_box.setObjectName("projectPanelSection")
        sub_btns = QHBoxLayout()
        self.btn_sub_add = QPushButton("Add")
        self.btn_sub_add.clicked.connect(self._add_subtask)
        self.btn_sub_del = QPushButton("Remove")
        self.btn_sub_del.clicked.connect(self._remove_subtask)
        sub_btns.addWidget(self.btn_sub_add)
        sub_btns.addWidget(self.btn_sub_del)
        sub_btns.addStretch()
        sub_layout.addLayout(sub_btns)

        self.list_subtasks = QListWidget()
        self.list_subtasks.setSelectionMode(QListWidget.SingleSelection)
        self.list_subtasks.itemSelectionChanged.connect(self._on_sub_selected)
        self.list_subtasks.itemChanged.connect(self._on_sub_checked)
        sub_layout.addWidget(self.list_subtasks, 1)

        # Subtask detail inline
        sub_form1 = QHBoxLayout()
        sub_form1.addWidget(QLabel("Title:"))
        self.sub_title = QLineEdit()
        self.sub_title.textEdited.connect(self._on_sub_changed)
        sub_form1.addWidget(self.sub_title, 1)
        sub_layout.addLayout(sub_form1)

        sub_form2 = QHBoxLayout()
        sub_form2.addWidget(QLabel("Status:"))
        self.sub_status = QComboBox()
        self.sub_status.addItems(DEFAULT_STATUSES)
        self.sub_status.currentTextChanged.connect(self._on_sub_changed)
        sub_form2.addWidget(self.sub_status, 1)
        sub_form2.addWidget(QLabel("Priority:"))
        self.sub_priority = QComboBox()
        self.sub_priority.addItems(PRIORITIES)
        self.sub_priority.currentTextChanged.connect(self._on_sub_changed)
        sub_form2.addWidget(self.sub_priority, 1)
        sub_form2.addWidget(QLabel("Due:"))
        self.sub_due = QDateEdit()
        self.sub_due.setCalendarPopup(True)
        self.sub_due.setDisplayFormat("yyyy-MM-dd")
        self.sub_due.setDate(QDate.currentDate())
        self.sub_due.dateChanged.connect(self._on_sub_changed)
        sub_form2.addWidget(self.sub_due, 1)
        sub_layout.addLayout(sub_form2)

        sub_layout.addWidget(QLabel("Notes:"))
        self.sub_notes = QTextEdit()
        self.sub_notes.textChanged.connect(self._on_sub_changed)
        self.sub_notes.setPlaceholderText("Details for this subtask…")
        sub_layout.addWidget(self.sub_notes, 1)

        right.addWidget(sub_box, 2)

        # Progress
        self.progress = QProgressBar()
        style_progress_bar(
            self.progress,
            accent="#2F6BFF",
            theme=self.logic.settings.get("theme", "Light"),
            min_height=12,
            max_height=16,
        )
        self.progress.setRange(0, 100)
        self.progress.setFormat("Subtasks: 0/0")
        right.addWidget(self.progress)

    # ---------- Data IO ----------
    def load_data(self, project_name, data):
        self.current_project = project_name or ""
        self.tasks = list((data or {}).get("tasks", []))
        # merge categories
        for t in self.tasks:
            cat = t.get("category")
            if cat and cat not in self._categories:
                self._categories.append(cat)
        self.combo_category.clear()
        self.combo_category.addItems(self._categories)
        self.filter_category.blockSignals(True)
        self.filter_category.clear()
        self.filter_category.addItems(["All"] + self._categories)
        self.filter_category.blockSignals(False)
        self._refresh_tree()
        self._show_task(None)
        self._update_summary()

    def get_data(self):
        return {"tasks": list(self.tasks)}

    # ---------- Actions ----------
    def add_task(self):
        title = self.search_box.text().strip() or "New Task"
        task = {
            "id": self._make_id(title),
            "name": title,
            "category": self.combo_category.currentText() or self._categories[0],
            "status": "To Do",
            "priority": "Normal",
            "due_date": "",
            "notes": "",
            "subtasks": []
        }
        self.tasks.append(task)
        self._persist()
        self._refresh_tree(select_id=task["id"])
        self._update_summary()

    def remove_task(self):
        task = self._current_task()
        if not task:
            return
        self.tasks = [t for t in self.tasks if t.get("id") != task.get("id")]
        self._persist()
        self._refresh_tree()
        self._show_task(None)
        self._update_summary()

    def import_from_kanban(self):
        if not self.current_project:
            return
        reg = self.logic.settings.get("project_registry", {}).get(self.current_project, {})
        kanban = reg.get("kanban", {})
        names = {t["name"] for col in kanban.values() for t in col if t.get("name")}
        existing = {t.get("name") for t in self.tasks}
        added = 0
        for name in sorted(names):
            if name in existing:
                continue
            self.tasks.append({
                "id": self._make_id(name),
                "name": name,
                "category": "Imported",
                "status": "To Do",
                "priority": "Normal",
                "notes": "",
                "due_date": "",
                "subtasks": []
            })
            added += 1
        if added:
            self._persist()
            self._refresh_tree()
            self._update_summary()

    # ---------- UI helpers ----------
    def _refresh_tree(self, select_id=None, select_sub_id=None):
        self.tree.blockSignals(True)
        self.tree.clear()

        sf = self._filters
        for task in self.tasks:
            if not self._task_passes(task, sf):
                continue
            subs = task.get("subtasks", [])
            done = sum(1 for s in subs if s.get("done"))
            total = len(subs)
            badge = f" ({done}/{total})" if total else ""
            due_txt = f" · due {task.get('due_date')}" if task.get("due_date") else ""
            top = QTreeWidgetItem([f"{task.get('name','Task')}{badge}{due_txt}"])
            top.setData(0, Qt.UserRole, task.get("id"))
            top.setForeground(0, QColor(STATUS_COLORS.get(task.get("status","To Do"), "#999")))
            top.setBackground(0, QColor(PRIORITY_COLORS.get(task.get("priority","Normal"), "#34495e")).lighter(170))
            self.tree.addTopLevelItem(top)

            for sub in subs:
                sub_item = QTreeWidgetItem([sub.get("title", "Subtask")])
                sub_item.setData(0, Qt.UserRole, sub.get("id"))
                sub_item.setCheckState(0, Qt.Checked if sub.get("done") else Qt.Unchecked)
                sub_item.setBackground(0, QColor(PRIORITY_COLORS.get(sub.get("priority", task.get("priority","Normal")), "#34495e")).lighter(190))
                top.addChild(sub_item)
            top.setExpanded(True)

        if select_sub_id:
            self._select_item(select_sub_id)
        elif select_id:
            self._select_item(select_id)
        self.tree.blockSignals(False)

    def _task_passes(self, task, f):
        if f["status"] != "All" and task.get("status") != f["status"]:
            return False
        if f["category"] != "All" and task.get("category") != f["category"]:
            return False
        if f["priority"] != "All" and task.get("priority") != f["priority"]:
            return False
        txt = f["search"].lower()
        if txt and txt not in (task.get("name","").lower() + task.get("notes","").lower()):
            return False
        return True

    def _select_item(self, item_id):
        matches = self.tree.findItems("", Qt.MatchContains | Qt.MatchRecursive, 0)
        for it in matches:
            if it.data(0, Qt.UserRole) == item_id:
                self.tree.setCurrentItem(it)
                it.setSelected(True)
                return

    def _stat_card(self, title, color):
        theme = self.logic.settings.get("theme", "Light")
        card = StatsCard(title, "0", accent=color, theme=theme)
        return {"frame": card, "value": card.value_label}

    # ---------- Task selection / editing ----------
    def _on_tree_selection(self):
        sel = self.tree.selectedItems()
        if not sel:
            self._show_task(None)
            return
        item = sel[0]
        if item.parent():  # subtask clicked -> show parent task and sub detail
            parent = item.parent()
            task = self._find_task(parent.data(0, Qt.UserRole))
            sub = self._find_sub(task, item.data(0, Qt.UserRole)) if task else None
            self._show_task(task, select_sub_id=sub.get("id") if sub else None)
            if sub:
                self._show_sub(sub)
        else:
            task = self._find_task(item.data(0, Qt.UserRole))
            self._show_task(task)

    def _show_task(self, task, select_sub_id=None):
        self._block_task_signals(True)
        if not task:
            self.edit_name.setText("")
            self.combo_category.setCurrentIndex(0)
            self.combo_status.setCurrentIndex(0)
            self.combo_priority.setCurrentIndex(PRIORITIES.index("Normal"))
            self.date_due.setDate(QDate.currentDate())
            self.edit_notes.setPlainText("")
            self.list_subtasks.clear()
            self._update_progress(None)
            self._show_sub(None)
        else:
            self.edit_name.setText(task.get("name", ""))
            cat = task.get("category", self._categories[0])
            if cat not in self._categories:
                self._categories.append(cat)
                self.combo_category.addItem(cat)
                self.filter_category.addItem(cat)
            self.combo_category.setCurrentText(cat)
            self.combo_status.setCurrentText(task.get("status", "To Do"))
            self.combo_priority.setCurrentText(task.get("priority", "Normal"))
            if task.get("due_date"):
                self.date_due.setDate(QDate.fromString(task.get("due_date"), "yyyy-MM-dd"))
            else:
                self.date_due.setDate(QDate.currentDate())
            self.edit_notes.setPlainText(task.get("notes", ""))
            self.list_subtasks.clear()
            subs = task.get("subtasks", [])
            for sub in subs:
                it = QListWidgetItem(sub.get("title", "Subtask"))
                it.setFlags(it.flags() | Qt.ItemIsUserCheckable | Qt.ItemIsEditable)
                it.setCheckState(Qt.Checked if sub.get("done") else Qt.Unchecked)
                it.setData(Qt.UserRole, sub.get("id"))
                self.list_subtasks.addItem(it)
            self._update_progress(task)
            if subs:
                target = 0
                if select_sub_id:
                    for idx in range(self.list_subtasks.count()):
                        if self.list_subtasks.item(idx).data(Qt.UserRole) == select_sub_id:
                            target = idx
                            break
                self.list_subtasks.setCurrentRow(target)
                self._show_sub(subs[target])
            else:
                self._show_sub(None)
        self._block_task_signals(False)

    def _on_task_changed(self):
        task = self._current_task()
        if not task:
            return
        task["name"] = self.edit_name.text().strip()
        task["category"] = self.combo_category.currentText()
        task["status"] = self.combo_status.currentText()
        task["priority"] = self.combo_priority.currentText()
        task["notes"] = self.edit_notes.toPlainText().strip()
        due = self.date_due.date()
        task["due_date"] = due.toString("yyyy-MM-dd") if due.isValid() else ""
        self._persist()
        self._refresh_tree(select_id=task["id"])
        self._update_summary()

    # ---------- Subtasks ----------
    def _add_subtask(self):
        task = self._current_task()
        if not task:
            return
        sub = {
            "id": self._make_id("sub"),
            "title": "New subtask",
            "status": "To Do",
            "priority": "Normal",
            "due_date": "",
            "notes": "",
            "done": False
        }
        task.setdefault("subtasks", []).append(sub)
        self._persist()
        self._show_task(task, select_sub_id=sub["id"])
        self._update_summary()

    def _remove_subtask(self):
        task = self._current_task()
        item = self.list_subtasks.currentItem()
        if not task or not item:
            return
        sid = item.data(Qt.UserRole)
        task["subtasks"] = [s for s in task.get("subtasks", []) if s.get("id") != sid]
        self._persist()
        self._show_task(task)
        self._update_summary()

    def _on_sub_selected(self):
        task = self._current_task()
        if not task:
            self._show_sub(None)
            return
        item = self.list_subtasks.currentItem()
        if not item:
            self._show_sub(None)
            return
        sid = item.data(Qt.UserRole)
        sub = self._find_sub(task, sid)
        self._show_sub(sub)

    def _on_sub_checked(self, item):
        task = self._current_task()
        if not task:
            return
        sid = item.data(Qt.UserRole)
        sub = self._find_sub(task, sid)
        if not sub:
            return
        sub["done"] = item.checkState() == Qt.Checked
        if sub["done"]:
            sub["status"] = "Done"
        self._persist()
        self._refresh_tree(select_id=task["id"], select_sub_id=sid)
        self._update_progress(task)
        self._update_summary()

    def _show_sub(self, sub):
        self._block_sub_signals(True)
        if not sub:
            self.sub_title.setText("")
            self.sub_status.setCurrentIndex(0)
            self.sub_priority.setCurrentIndex(PRIORITIES.index("Normal"))
            self.sub_due.setDate(QDate.currentDate())
            self.sub_notes.setPlainText("")
        else:
            self.sub_title.setText(sub.get("title", ""))
            self.sub_status.setCurrentText(sub.get("status", "To Do"))
            self.sub_priority.setCurrentText(sub.get("priority", "Normal"))
            if sub.get("due_date"):
                self.sub_due.setDate(QDate.fromString(sub.get("due_date"), "yyyy-MM-dd"))
            else:
                self.sub_due.setDate(QDate.currentDate())
            self.sub_notes.setPlainText(sub.get("notes", ""))
        self._block_sub_signals(False)

    def _on_sub_changed(self):
        task = self._current_task()
        item = self.list_subtasks.currentItem()
        if not task or not item:
            return
        sid = item.data(Qt.UserRole)
        sub = self._find_sub(task, sid)
        if not sub:
            return
        sub["title"] = self.sub_title.text().strip()
        sub["status"] = self.sub_status.currentText()
        sub["priority"] = self.sub_priority.currentText()
        due = self.sub_due.date()
        sub["due_date"] = due.toString("yyyy-MM-dd") if due.isValid() else ""
        sub["notes"] = self.sub_notes.toPlainText().strip()
        sub["done"] = sub["status"] == "Done"
        item.setText(sub["title"] or "Subtask")
        item.setCheckState(Qt.Checked if sub["done"] else Qt.Unchecked)
        self._persist()
        self._refresh_tree(select_id=task["id"], select_sub_id=sid)
        self._update_progress(task)
        self._update_summary()

    # ---------- Helpers ----------
    def _current_task(self):
        sel = self.tree.selectedItems()
        if not sel:
            return None
        item = sel[0]
        if item.parent():
            item = item.parent()
        return self._find_task(item.data(0, Qt.UserRole))

    def _find_task(self, tid):
        for t in self.tasks:
            if t.get("id") == tid:
                return t
        return None

    def _find_sub(self, task, sid):
        if not task:
            return None
        for s in task.get("subtasks", []):
            if s.get("id") == sid:
                return s
        return None

    def _update_progress(self, task):
        subs = task.get("subtasks", []) if task else []
        total = len(subs)
        done = sum(1 for s in subs if s.get("done"))
        percent = int((done / total) * 100) if total else 0
        self.progress.setValue(percent)
        self.progress.setFormat(f"Subtasks: {done}/{total} ({percent}%)" if total else "Subtasks: 0/0")

    def _update_summary(self):
        total = len(self.tasks)
        done = sum(1 for t in self.tasks if t.get("status") == "Done")
        active = sum(1 for t in self.tasks if t.get("status") in ("To Do", "In Progress"))
        today = QDate.currentDate()
        overdue = 0
        for t in self.tasks:
            if t.get("status") == "Done":
                continue
            due = t.get("due_date")
            if due:
                d = QDate.fromString(due, "yyyy-MM-dd")
                if d.isValid() and d < today:
                    overdue += 1
        for k, v in {"total": total, "active": active, "done": done, "overdue": overdue}.items():
            self.cards[k]["value"].setText(str(v))

    def _make_id(self, name):
        stamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
        slug = "".join(c for c in name.lower() if c.isalnum() or c in ("-", "_")).strip("-_")
        return f"{slug[:24] or 'item'}-{stamp}"

    def _persist(self):
        if not self.current_project:
            return
        reg = self.logic.settings.setdefault("project_registry", {})
        if self.current_project not in reg:
            return
        reg[self.current_project]["tasks"] = list(self.tasks)
        reg[self.current_project]["time_entries"] = []  # clear legacy
        self.logic.save_settings()

    def _on_filters_changed(self):
        self._filters["search"] = self.search_box.text()
        self._filters["status"] = self.filter_status.currentText()
        self._filters["category"] = self.filter_category.currentText()
        self._filters["priority"] = self.filter_priority.currentText()
        self._refresh_tree()
        self._update_summary()

    def _add_category(self):
        name, ok = QInputDialog.getText(self, "New Category", "Name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name not in self._categories:
            self._categories.append(name)
            self.combo_category.addItem(name)
            self.filter_category.addItem(name)
        self.combo_category.setCurrentText(name)
        self._on_task_changed()

    def _block_task_signals(self, block):
        self.edit_name.blockSignals(block)
        self.combo_category.blockSignals(block)
        self.combo_status.blockSignals(block)
        self.combo_priority.blockSignals(block)
        self.edit_notes.blockSignals(block)
        self.date_due.blockSignals(block)
        self.list_subtasks.blockSignals(block)

    def _block_sub_signals(self, block):
        self.sub_title.blockSignals(block)
        self.sub_status.blockSignals(block)
        self.sub_priority.blockSignals(block)
        self.sub_due.blockSignals(block)
        self.sub_notes.blockSignals(block)


class TaskTree(QTreeWidget):
    """
    Drag a task onto another task to make it a subtask. Drag a subtask onto a task to reparent.
    """

    def __init__(self, view: ProjectTasksView):
        super().__init__()
        self.view = view
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDrop)

    def dropEvent(self, event):
        sel = self.selectedItems()
        if not sel:
            event.ignore()
            return
        src = sel[0]
        pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
        target = self.itemAt(pos)
        if not target:
            event.ignore()
            return
        # normalize target to top-level task
        if target.parent():
            target = target.parent()
        if src == target or self._is_descendant(src, target):
            event.ignore()
            return
        src_id = src.data(0, Qt.UserRole)
        target_id = target.data(0, Qt.UserRole)
        target_task = self.view._find_task(target_id)
        if not target_task:
            event.ignore()
            return

        # task onto task -> convert to subtask
        if not src.parent():
            moving_task = self.view._find_task(src_id)
            if not moving_task:
                event.ignore()
                return
            self.view.tasks = [t for t in self.view.tasks if t.get("id") != src_id]
            target_task.setdefault("subtasks", []).append({
                "id": moving_task.get("id"),
                "title": moving_task.get("name"),
                "done": moving_task.get("status") == "Done",
                "status": moving_task.get("status", "To Do"),
                "priority": moving_task.get("priority", "Normal"),
                "due_date": moving_task.get("due_date", ""),
                "notes": moving_task.get("notes", "")
            })
        else:
            # subtask onto task
            parent_task = self.view._find_task(src.parent().data(0, Qt.UserRole))
            sub = self.view._find_sub(parent_task, src_id) if parent_task else None
            if not sub:
                event.ignore()
                return
            parent_task["subtasks"] = [s for s in parent_task.get("subtasks", []) if s.get("id") != src_id]
            target_task.setdefault("subtasks", []).append(sub)

        self.view._persist()
        self.view._refresh_tree(select_sub_id=src_id, select_id=target_id)
        self.view._update_summary()
        event.accept()

    def _is_descendant(self, child, parent):
        it = child.parent()
        while it:
            if it == parent:
                return True
            it = it.parent()
        return False
