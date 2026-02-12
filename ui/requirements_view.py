from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                             QTableWidgetItem, QPushButton, QHeaderView, QComboBox, 
                             QMessageBox, QInputDialog)
from PySide6.QtCore import Qt

class RequirementsView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        h = QHBoxLayout()
        btn_add = QPushButton("Add Requirement")
        btn_add.clicked.connect(self.add_req)
        btn_del = QPushButton("Delete Selected")
        btn_del.clicked.connect(self.del_req)
        h.addWidget(btn_add)
        h.addWidget(btn_del)
        h.addStretch()
        layout.addLayout(h)
        
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["ID", "Requirement", "Status", "Priority"])
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table.itemChanged.connect(self.on_item_changed)
        layout.addWidget(self.table)

    def load_data(self, reqs):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for r in reqs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r.get("id", f"REQ-{row+1:03d}")))
            self.table.setItem(row, 1, QTableWidgetItem(r.get("text", "")))
            
            # Status Combo
            cb_stat = QComboBox()
            cb_stat.addItems(["Draft", "Review", "Approved", "Implemented", "Verified"])
            cb_stat.setCurrentText(r.get("status", "Draft"))
            cb_stat.currentTextChanged.connect(lambda t, row=row: self.save_trigger())
            self.table.setCellWidget(row, 2, cb_stat)
            
            # Priority Combo
            cb_prio = QComboBox()
            cb_prio.addItems(["Low", "Medium", "High", "Critical"])
            cb_prio.setCurrentText(r.get("priority", "Medium"))
            cb_prio.currentTextChanged.connect(lambda t, row=row: self.save_trigger())
            self.table.setCellWidget(row, 3, cb_prio)
            
        self.table.blockSignals(False)

    def get_data(self):
        reqs = []
        for r in range(self.table.rowCount()):
            reqs.append({
                "id": self.table.item(r, 0).text(),
                "text": self.table.item(r, 1).text(),
                "status": self.table.cellWidget(r, 2).currentText(),
                "priority": self.table.cellWidget(r, 3).currentText()
            })
        return reqs

    def add_req(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(f"REQ-{row+1:03d}"))
        self.table.setItem(row, 1, QTableWidgetItem("New Requirement"))
        
        cb_stat = QComboBox(); cb_stat.addItems(["Draft", "Review", "Approved", "Implemented", "Verified"])
        cb_stat.currentTextChanged.connect(lambda: self.save_trigger())
        self.table.setCellWidget(row, 2, cb_stat)
        
        cb_prio = QComboBox(); cb_prio.addItems(["Low", "Medium", "High", "Critical"])
        cb_prio.currentTextChanged.connect(lambda: self.save_trigger())
        self.table.setCellWidget(row, 3, cb_prio)
        
        self.save_trigger()

    def del_req(self):
        r = self.table.currentRow()
        if r >= 0:
            self.table.removeRow(r)
            self.save_trigger()

    def on_item_changed(self, item):
        self.save_trigger()

    def save_trigger(self):
        # Parent handles save via get_data, but we can emit a signal if needed
        # For now, we rely on the main "Save Project Metadata" button in the parent tab
        pass