import csv
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QCheckBox,
                             QTableWidget, QTableWidgetItem, QHeaderView, QFileDialog, QMessageBox, QLabel)
from PySide6.QtCore import Qt, QThread, Signal
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons

class BOMTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.current_project = None
        self.bom_data = []
        self._bom_worker = None
        self._bom_target_path = ""
        self.lbl_bom_status = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        # Toolbar
        btn_layout = QHBoxLayout()
        
        self.btn_gen = QPushButton("Generate/Refresh BOM")
        self.btn_gen.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        self.btn_gen.clicked.connect(self.generate)
        btn_layout.addWidget(self.btn_gen)

        self.btn_export = QPushButton("Export CSV")
        self.btn_export.setIcon(Icons.get_icon(Icons.SAVE, icon_color))
        self.btn_export.clicked.connect(self.export_csv)
        btn_layout.addWidget(self.btn_export)
        
        self.btn_compare = QPushButton("Compare CSV")
        self.btn_compare.setIcon(Icons.get_icon(Icons.SEARCH, icon_color))
        self.btn_compare.clicked.connect(self.compare_bom)
        btn_layout.addWidget(self.btn_compare)
        
        btn_layout.addStretch()

        self.chk_hide_dnp = QCheckBox("Hide DNP")
        self.chk_hide_dnp.stateChanged.connect(self._update_row_visibility)
        btn_layout.addWidget(self.chk_hide_dnp)

        self.chk_hide_excluded = QCheckBox("Hide Excluded")
        self.chk_hide_excluded.stateChanged.connect(self._update_row_visibility)
        btn_layout.addWidget(self.chk_hide_excluded)

        layout.addLayout(btn_layout)

        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(10)
        self.table.setHorizontalHeaderLabels(["Qty", "DNP", "Excluded", "Value", "Footprint", "Reference", "Library ID", "Sheets", "Unit Price", "Total Price"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.setWordWrap(True)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.Stretch)
        header.setSectionResizeMode(6, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setSortingEnabled(True)
        
        # Set initial column widths
        self.table.setColumnWidth(0, 50)  # Qty
        self.table.setColumnWidth(1, 50)  # DNP
        self.table.setColumnWidth(2, 70)  # Excluded
        self.table.setColumnWidth(3, 150) # Value
        self.table.setColumnWidth(4, 200) # Footprint
        self.table.setColumnWidth(5, 200) # Reference
        self.table.setColumnWidth(6, 200) # Library ID
        self.table.setColumnWidth(8, 80)  # Unit Price
        self.table.setColumnWidth(9, 80)  # Total Price
        
        self.table_vertical_header = self.table.verticalHeader()
        self.table_vertical_header.setVisible(False)
        self.table.setStyleSheet(
            """
            QTableWidget {
                background-color: transparent;
                border: 1px solid rgba(15, 23, 42, 0.08);
                border-radius: 12px;
            }
            QTableWidget::item {
                padding: 6px 10px;
            }
            QTableWidget::item:selected {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(56, 113, 255, 0.35), stop:1 rgba(30, 64, 175, 0.3));
                color: #fff;
            }
            QTableWidget::item:alternate {
                background-color: rgba(59, 114, 255, 0.03);
            }
            """
        )
        
        self.table.itemChanged.connect(self.on_item_changed)
        
        layout.addWidget(self.table)
        
        self.lbl_bom_status = QLabel("")
        self.lbl_bom_status.setStyleSheet("color: #9ca3af; font-size: 12px;")
        layout.addWidget(self.lbl_bom_status)

        self.lbl_total_cost = QLabel("Total BOM Cost: $0.00")
        layout.addWidget(self.lbl_total_cost)

    def set_current_project(self, project_name):
        self.current_project = project_name

    def generate(self):
        if not self.current_project:
            return

        data = self.logic.get_project_data(self.current_project)
        sch_path = data["metadata"].get("main_schematic")
        
        if not sch_path:
            # Silent skip if no schematic path is set
            self.table.setRowCount(0)
            self.bom_data = [] # Clear internal data
            return
        
        if not os.path.exists(sch_path):
            self.table.setRowCount(0)
            self.bom_data = [] # Clear internal data
            QMessageBox.warning(self, "BOM Generation Error", f"Main schematic file not found: {self.logic.relativize_path(sch_path)}")
            return

        self._start_bom_worker(sch_path)

    def populate_table(self):
        self.table.blockSignals(True)
        pricing = {}
        if self.current_project:
            pricing = self.logic.get_project_data(self.current_project).get("bom_pricing", {})

        self.table.setSortingEnabled(False)
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.bom_data))
        
        self.bom_data.sort(key=lambda x: (x['refs'].split(',')[0] if x['refs'] else (x['dnp'].split(',')[0] if x['dnp'] else (x['excluded'].split(',')[0] if x['excluded'] else ""))))

        for row, item in enumerate(self.bom_data):
            qty_item = QTableWidgetItem()
            qty_item.setData(Qt.DisplayRole, int(item['qty']))
            
            self.table.setItem(row, 0, qty_item)
            self.table.setItem(row, 1, QTableWidgetItem(item.get('dnp', '')))
            self.table.setItem(row, 2, QTableWidgetItem(item.get('excluded', '')))
            self.table.setItem(row, 3, QTableWidgetItem(item['value']))
            self.table.setItem(row, 4, QTableWidgetItem(item.get('footprint', '')))
            self.table.setItem(row, 5, QTableWidgetItem(item['refs']))
            self.table.setItem(row, 6, QTableWidgetItem(item['lib_id']))
            self.table.setItem(row, 7, QTableWidgetItem(item['sheet']))
            
            # Pricing
            key = f"{item['value']}|{item.get('footprint','')}"
            unit_price = pricing.get(key, 0.0)
            total_price = unit_price * item['qty']
            
            price_item = QTableWidgetItem(f"{unit_price:.4f}")
            self.table.setItem(row, 8, price_item)
            
            total_item = QTableWidgetItem(f"{total_price:.2f}")
            total_item.setFlags(total_item.flags() ^ Qt.ItemIsEditable) # Read only
            self.table.setItem(row, 9, total_item)
            for col in range(self.table.columnCount()):
                cell = self.table.item(row, col)
                if cell:
                    cell.setToolTip(cell.text())
        
        self.table.setSortingEnabled(True)
        self.table.blockSignals(False)
        self.table.resizeRowsToContents()
        self.update_total_cost()

    def on_item_changed(self, item):
        if item.column() == 8: # Unit Price Changed
            row = item.row()
            try:
                unit_price = float(item.text())
                qty = int(self.table.item(row, 0).text())
                total = unit_price * qty
                self.table.item(row, 9).setText(f"{total:.2f}")
                
                # Save to registry
                val = self.table.item(row, 3).text()
                fp = self.table.item(row, 4).text()
                key = f"{val}|{fp}"
                
                if self.current_project:
                    data = self.logic.get_project_data(self.current_project)
                    if "bom_pricing" not in data: data["bom_pricing"] = {}
                    data["bom_pricing"][key] = unit_price
                    self.logic.save_settings()
                
                self.update_total_cost()
            except ValueError: pass

    def _update_row_visibility(self):
        hide_dnp = self.chk_hide_dnp.isChecked()
        hide_excluded = self.chk_hide_excluded.isChecked()

        # Hide Columns
        self.table.setColumnHidden(1, hide_dnp)  # DNP Column
        self.table.setColumnHidden(2, hide_excluded)  # Excluded Column

        for row in range(self.table.rowCount()):
            dnp_item = self.table.item(row, 1)
            excluded_item = self.table.item(row, 2)
            dnp_text = dnp_item.text().strip() if dnp_item else ""
            excluded_text = excluded_item.text().strip() if excluded_item else ""

            hide_row = False
            if hide_dnp and dnp_text:
                hide_row = True
            if hide_excluded and excluded_text:
                hide_row = True

            self.table.setRowHidden(row, hide_row)

    def _start_bom_worker(self, schematic_path):
        self._bom_target_path = schematic_path
        self._set_bom_loading(True, "Generating BOM…")
        if self._bom_worker and self._bom_worker.isRunning():
            self._bom_worker.terminate()
        self._bom_worker = _BOMWorker(self.logic, schematic_path)
        self._bom_worker.finished.connect(self._on_bom_ready)
        self._bom_worker.failed.connect(self._on_bom_failed)
        self._bom_worker.start()

    def _on_bom_ready(self, bom_data, path):
        self._set_bom_loading(False)
        self._bom_worker = None
        if path != self._bom_target_path:
            return
        self.bom_data = bom_data
        self.populate_table()
        self._update_row_visibility()

    def _on_bom_failed(self, error, path):
        self._set_bom_loading(False, f"Failed to generate BOM: {error}")
        self._bom_worker = None
        if path != self._bom_target_path:
            return
        QMessageBox.critical(self, "BOM Generation Error", f"Failed to generate BOM: {error}")

    def _set_bom_loading(self, busy, message=""):
        self.btn_gen.setEnabled(not busy)
        self.lbl_bom_status.setText(message)

    def update_total_cost(self):
        total = 0.0
        for r in range(self.table.rowCount()):
            if not self.table.isRowHidden(r):
                try: total += float(self.table.item(r, 9).text())
                except: pass
        self.lbl_total_cost.setText(f"Total BOM Cost: ${total:.2f}")

    def export_csv(self):
        if self.table.rowCount() == 0:
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Export BOM", "", "CSV Files (*.csv)")
        if path:
            try:
                with open(path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    # Headers
                    headers = [self.table.horizontalHeaderItem(i).text() for i in range(self.table.columnCount())]
                    writer.writerow(headers)
                    # Data
                    for r in range(self.table.rowCount()):
                        row_data = [self.table.item(r, c).text() if self.table.item(r, c) else "" for c in range(self.table.columnCount())]
                        writer.writerow(row_data)
                QMessageBox.information(self, "Success", "BOM exported successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to export CSV: {e}")

    def compare_bom(self):
        if not self.bom_data: return
        path, _ = QFileDialog.getOpenFileName(self, "Select Old BOM CSV", "", "CSV Files (*.csv)")
        if not path: return
        
        try:
            changes = []
            old_bom = {}
            with open(path, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # Key by Value+Footprint usually
                    key = (row.get("Value", ""), row.get("Footprint", ""))
                    old_bom[key] = row
            
            # Compare
            current_keys = set((x['value'], x['footprint']) for x in self.bom_data)
            all_keys = current_keys.union(old_bom.keys())
            
            for k in all_keys:
                curr = next((x for x in self.bom_data if x['value'] == k[0] and x['footprint'] == k[1]), None)
                old = old_bom.get(k)
                
                if curr and not old:
                    changes.append(f"ADDED: {k[0]} ({k[1]}) - Qty: {curr['qty']}")
                elif old and not curr:
                    changes.append(f"REMOVED: {k[0]} ({k[1]}) - Qty: {old.get('Qty', '?')}")
                else:
                    # Check Qty
                    c_qty = int(curr['qty'])
                    o_qty = int(old.get('Qty', 0))
                    if c_qty != o_qty:
                        changes.append(f"CHANGED: {k[0]} - Qty {o_qty} -> {c_qty}")
            
            if not changes:
                QMessageBox.information(self, "Compare", "No significant changes found (Value/Footprint/Qty).")
            else:
                # Show in dialog
                dlg = QMessageBox(self)
                dlg.setWindowTitle("BOM Comparison")
                dlg.setText("Changes found:\n\n" + "\n".join(changes[:20]) + ("\n..." if len(changes)>20 else ""))
                dlg.exec()
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Comparison failed: {e}")


class _BOMWorker(QThread):
    finished = Signal(list, str)
    failed = Signal(str, str)

    def __init__(self, logic, schematic_path):
        super().__init__()
        self.logic = logic
        self.schematic_path = schematic_path

    def run(self):
        try:
            bom = self.logic.generate_bom(self.schematic_path)
            self.finished.emit(bom, self.schematic_path)
        except Exception as exc:
            self.failed.emit(str(exc), self.schematic_path)
