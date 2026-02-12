import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox, 
                             QComboBox, QLabel, QProgressBar, QSpinBox)
from PySide6.QtCore import Qt, QThread, Signal
try:
    from .icons import Icons
except ImportError:
    from ui.icons import Icons
from ui.widgets.progress_utils import style_progress_bar

class PricingWorker(QThread):
    finished = Signal(list)
    
    def __init__(self, logic, bom, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.bom = bom
        
    def run(self):
        results = self.logic.fetch_supplier_pricing(self.bom)
        self.finished.emit(results)

class PricingTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.current_project = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        
        h = QHBoxLayout()
        self.btn_fetch = QPushButton("Fetch Pricing & Availability")
        self.btn_fetch.setIcon(Icons.get_icon(Icons.SEARCH, icon_color))
        self.btn_fetch.clicked.connect(self.start_fetch)
        h.addWidget(self.btn_fetch)
        
        self.combo_vendor = QComboBox()
        self.combo_vendor.addItems(["All Vendors", "DigiKey", "Mouser", "LCSC"])
        h.addWidget(QLabel("Preferred Vendor:"))
        h.addWidget(self.combo_vendor)
        
        h.addSpacing(20)
        h.addWidget(QLabel("Build Qty:"))
        self.spin_qty = QSpinBox()
        self.spin_qty.setRange(1, 10000)
        self.spin_qty.setValue(1)
        self.spin_qty.valueChanged.connect(self.recalc_totals)
        h.addWidget(self.spin_qty)
        
        layout.addLayout(h)
        
        self.progress = QProgressBar()
        style_progress_bar(
            self.progress,
            accent="#0F766E",
            theme=self.logic.settings.get("theme", "Light"),
            min_height=12,
            max_height=16,
        )
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels(["MPN", "Qty", "Vendor", "Stock", "Unit Price", "Total"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

    def set_current_project(self, project_name):
        self.current_project = project_name
        
    def start_fetch(self):
        if not self.current_project:
            QMessageBox.warning(self, "Error", "No project selected.")
            return

        data = self.logic.get_project_data(self.current_project)
        sch_path = data["metadata"].get("main_schematic")

        if not sch_path or not os.path.exists(sch_path):
            QMessageBox.warning(self, "Error", "Main schematic not found for this project.\nPlease set it in the 'Configuration' tab.")
            return
        
        bom = self.logic.generate_bom(sch_path)
        
        self.progress.setVisible(True)
        self.progress.setRange(0, 0) # Indeterminate
        self.btn_fetch.setEnabled(False)
        
        self.worker = PricingWorker(self.logic, bom, self)
        self.worker.finished.connect(self.on_data_ready)
        self.worker.start()
        
    def on_data_ready(self, results):
        self.progress.setVisible(False)
        self.btn_fetch.setEnabled(True)
        self.table.setRowCount(0)
        for r in results:
            qty_per_board = r['qty']
            
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(r['mpn']))
            self.table.setItem(row, 1, QTableWidgetItem(str(qty_per_board)))
            self.table.setItem(row, 2, QTableWidgetItem(r['vendor']))
            self.table.setItem(row, 3, QTableWidgetItem(str(r['stock'])))
            
            price = r['price']
            # Calculate total based on build qty
            total = r['total'] * self.spin_qty.value()
            
            p_str = f"${price:.2f}" if isinstance(price, (int, float)) else str(price)
            t_str = f"${total:.2f}" if isinstance(total, (int, float)) else str(total)
            
            self.table.setItem(row, 4, QTableWidgetItem(p_str))
            self.table.setItem(row, 5, QTableWidgetItem(t_str))

    def recalc_totals(self):
        build_qty = self.spin_qty.value()
        for row in range(self.table.rowCount()):
            try:
                qty_item = self.table.item(row, 1)
                price_item = self.table.item(row, 4)
                if qty_item and price_item:
                    qty = int(qty_item.text())
                    price_str = price_item.text().replace("$", "")
                    price = float(price_str)
                    total = qty * price * build_qty
                    self.table.item(row, 5).setText(f"${total:.2f}")
            except ValueError:
                pass

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)
