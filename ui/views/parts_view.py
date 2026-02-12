import csv
import uuid

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QLabel,
    QMenu,
    QApplication,
    QStackedWidget,
)
from PySide6.QtCore import Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices

from ui.resources.icons import Icons
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.empty_state import EmptyState
from ui.widgets.toast import show_toast


class PartsView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.parts = []
        self._parts_by_id = {}
        self._loading = False
        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(200)
        self._save_timer.timeout.connect(self._flush_save)
        self._columns = [
            ("mpn", "MPN"),
            ("manufacturer", "Manufacturer"),
            ("description", "Description"),
            ("footprint", "Footprint"),
            ("package", "Package"),
            ("datasheet", "Datasheet"),
            ("notes", "Notes"),
        ]
        self.setup_ui()
        self.load_parts()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        apply_layout(layout, margin=PAGE_PADDING, spacing="md")

        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        self.count_label = QLabel("0 / 0")
        self.count_label.setStyleSheet("color: #6B7280;")

        top = QHBoxLayout()
        lbl_search = QLabel("Search")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by MPN, manufacturer, description...")
        self.search_box.setClearButtonEnabled(True)
        self.search_box.textChanged.connect(self._apply_filter)

        btn_add = QPushButton("New Part")
        btn_add.setIcon(Icons.get_icon(Icons.PLUS, icon_color))
        btn_add.setObjectName("btnPrimary")
        btn_add.clicked.connect(self.add_part)

        btn_del = QPushButton("Delete")
        btn_del.setIcon(Icons.get_icon(Icons.TRASH, icon_color))
        btn_del.setObjectName("btnSecondary")
        btn_del.clicked.connect(self.delete_selected)

        btn_dup = QPushButton("Duplicate")
        btn_dup.setIcon(Icons.get_icon(Icons.EDIT, icon_color))
        btn_dup.setObjectName("btnSecondary")
        btn_dup.clicked.connect(self.duplicate_selected)

        btn_import = QPushButton("Import CSV")
        btn_import.setIcon(Icons.get_icon(Icons.DOC, icon_color))
        btn_import.setObjectName("btnSecondary")
        btn_import.clicked.connect(self.import_csv)

        btn_export = QPushButton("Export CSV")
        btn_export.setIcon(Icons.get_icon(Icons.SAVE, icon_color))
        btn_export.setObjectName("btnSecondary")
        btn_export.clicked.connect(self.export_csv)

        top.addWidget(lbl_search)
        top.addWidget(self.search_box, 1)
        top.addWidget(self.count_label)
        top.addWidget(btn_import)
        top.addWidget(btn_export)
        top.addStretch()
        top.addWidget(btn_dup)
        top.addWidget(btn_del)
        top.addWidget(btn_add)
        layout.addLayout(top)

        self.table = QTableWidget(0, len(self._columns))
        self.table.setHorizontalHeaderLabels([label for _, label in self._columns])
        header_view = self.table.horizontalHeader()
        header_view.setSectionResizeMode(QHeaderView.ResizeToContents)
        header_view.setStretchLastSection(True)
        if len(self._columns) >= 3:
            header_view.setSectionResizeMode(2, QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.setSortingEnabled(True)
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._show_context_menu)
        self.table.cellChanged.connect(self._on_cell_changed)
        self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)
        self.table_stack = QStackedWidget()
        self.table_stack.addWidget(self.table)
        self.empty_state = EmptyState(
            "No parts yet",
            "Add a part to start building a reusable library.",
            Icons.CHIP,
            "New Part",
            self.add_part,
            icon_color,
        )
        self.table_stack.addWidget(self.empty_state)
        layout.addWidget(self.table_stack)

    def load_parts(self):
        self._loading = True
        self.parts = list(self.logic.get_parts_db())
        changed = False
        for part in self.parts:
            if not part.get("id"):
                part["id"] = uuid.uuid4().hex
                changed = True
        if changed:
            self.logic.save_parts_db(self.parts)
        self._rebuild_index()
        self._reload_table()
        self._loading = False
        self._apply_filter()
        self._update_count_label()
        if not self.parts:
            self.table_stack.setCurrentWidget(self.empty_state)
        else:
            self.table_stack.setCurrentWidget(self.table)

    def _reload_table(self):
        self.table.setRowCount(0)
        for part in self.parts:
            self._add_row(part)

    def _add_row(self, part):
        row = self.table.rowCount()
        self.table.insertRow(row)
        part_id = part.get("id")
        for col, (key, _) in enumerate(self._columns):
            val = part.get(key, "")
            item = QTableWidgetItem(val if val is not None else "")
            item.setData(Qt.UserRole, part_id)
            self.table.setItem(row, col, item)

    def _rebuild_index(self):
        self._parts_by_id = {p.get("id"): p for p in self.parts if p.get("id")}

    def _apply_filter(self):
        query = self.search_box.text().strip().lower()
        for row in range(self.table.rowCount()):
            if not query:
                self.table.setRowHidden(row, False)
                continue
            matched = False
            for col in range(self.table.columnCount()):
                item = self.table.item(row, col)
                if item and query in (item.text() or "").lower():
                    matched = True
                    break
            self.table.setRowHidden(row, not matched)
        self._update_count_label()

    def add_part(self):
        part = {"id": uuid.uuid4().hex}
        for key, _ in self._columns:
            part[key] = ""
        self.parts.append(part)
        self._parts_by_id[part["id"]] = part
        self._add_row(part)
        self.logic.save_parts_db(self.parts)
        row = self.table.rowCount() - 1
        self.table.setCurrentCell(row, 0)
        self.table.editItem(self.table.item(row, 0))
        self._update_count_label()

    def delete_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()}, reverse=True)
        if not rows:
            return
        if QMessageBox.question(self, "Confirm Delete", f"Delete {len(rows)} selected part(s)?") != QMessageBox.Yes:
            return
        ids_to_remove = set()
        for row in rows:
            item = self.table.item(row, 0)
            if item:
                part_id = item.data(Qt.UserRole)
                if part_id:
                    ids_to_remove.add(part_id)
            self.table.removeRow(row)
        if ids_to_remove:
            self.parts = [p for p in self.parts if p.get("id") not in ids_to_remove]
            self._rebuild_index()
            self.logic.save_parts_db(self.parts)
        self._update_count_label()

    def duplicate_selected(self):
        rows = sorted({idx.row() for idx in self.table.selectedIndexes()})
        if not rows:
            return
        for row in rows:
            part_id = self.table.item(row, 0).data(Qt.UserRole)
            part = self._parts_by_id.get(part_id)
            if not part:
                continue
            new_part = {"id": uuid.uuid4().hex}
            for key, _ in self._columns:
                new_part[key] = part.get(key, "")
            self.parts.append(new_part)
            self._parts_by_id[new_part["id"]] = new_part
            self._add_row(new_part)
        self.logic.save_parts_db(self.parts)
        self._update_count_label()

    def _on_cell_changed(self, row, col):
        if self._loading:
            return
        item = self.table.item(row, col)
        if not item:
            return
        part_id = item.data(Qt.UserRole)
        if not part_id:
            return
        part = self._parts_by_id.get(part_id)
        if not part:
            return
        key = self._columns[col][0]
        part[key] = item.text()
        self._save_timer.start()

    def _flush_save(self):
        self.logic.save_parts_db(self.parts)

    def import_csv(self):
        path, _ = QFileDialog.getOpenFileName(self, "Import Parts CSV", "", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read CSV: {e}")
            return

        if not rows:
            QMessageBox.information(self, "Import", "CSV file is empty.")
            return

        column_map = {}
        for key, label in self._columns:
            column_map[label.lower()] = key
            column_map[key.lower()] = key

        imported = []
        for row in rows:
            part = {"id": uuid.uuid4().hex}
            for key, _ in self._columns:
                part[key] = ""
            for col_name, value in row.items():
                if col_name is None:
                    continue
                mapped = column_map.get(col_name.strip().lower())
                if mapped:
                    part[mapped] = value.strip() if isinstance(value, str) else (value or "")
            imported.append(part)

        if not imported:
            QMessageBox.information(self, "Import", "No usable columns found in CSV.")
            return

        choice = QMessageBox.question(
            self,
            "Import Parts",
            f"Import {len(imported)} part(s).\n\nYes = Append\nNo = Replace",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        if choice == QMessageBox.Cancel:
            return
        if choice == QMessageBox.No:
            self.parts = imported
        else:
            self.parts.extend(imported)
        self._rebuild_index()
        self.logic.save_parts_db(self.parts)
        self._loading = True
        self._reload_table()
        self._loading = False
        self._apply_filter()
        self._update_count_label()

    def export_csv(self):
        path, _ = QFileDialog.getSaveFileName(self, "Export Parts CSV", "parts.csv", "CSV Files (*.csv)")
        if not path:
            return
        try:
            with open(path, "w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=[label for _, label in self._columns])
                writer.writeheader()
                for part in self.parts:
                    row = {}
                    for key, label in self._columns:
                        row[label] = part.get(key, "")
                    writer.writerow(row)
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export CSV: {e}")
            return

    def _update_count_label(self):
        if not hasattr(self, "count_label"):
            return
        total = self.table.rowCount()
        visible = sum(1 for row in range(total) if not self.table.isRowHidden(row))
        self.count_label.setText(f"{visible} / {total}")
        if hasattr(self, "table_stack"):
            if not self.parts:
                self.table_stack.setCurrentWidget(self.empty_state)
            else:
                self.table_stack.setCurrentWidget(self.table)

    def _show_context_menu(self, pos):
        item = self.table.itemAt(pos)
        if not item:
            return
        row = item.row()
        menu = QMenu(self)
        act_copy = menu.addAction("Copy MPN")
        act_open = menu.addAction("Open Datasheet")
        act_dup = menu.addAction("Duplicate")
        act_del = menu.addAction("Delete")
        act = menu.exec(self.table.viewport().mapToGlobal(pos))
        if act == act_copy:
            mpn = self.table.item(row, 0).text() if self.table.item(row, 0) else ""
            QApplication.clipboard().setText(mpn)
        elif act == act_open:
            self._open_datasheet_for_row(row)
        elif act == act_dup:
            self.table.selectRow(row)
            self.duplicate_selected()
        elif act == act_del:
            self.table.selectRow(row)
            self.delete_selected()

    def _on_cell_double_clicked(self, row, col):
        key = self._columns[col][0]
        if key == "datasheet":
            self._open_datasheet_for_row(row)

    def _open_datasheet_for_row(self, row):
        ds_col = next((i for i, (k, _) in enumerate(self._columns) if k == "datasheet"), None)
        if ds_col is None:
            return
        item = self.table.item(row, ds_col)
        if not item:
            return
        val = (item.text() or "").strip()
        if not val:
            return
        if val.lower().startswith(("http://", "https://")):
            QDesktopServices.openUrl(QUrl(val))
        else:
            QDesktopServices.openUrl(QUrl.fromLocalFile(val))
            QMessageBox.information(self, "Export", "Parts exported.")
            show_toast(self, "Parts exported", 2000, "success")
