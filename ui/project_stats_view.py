from PySide6.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QLabel
from collections import Counter

class ProjectStatsView(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.lbl_title = QLabel("Part Distribution by Library")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(self.lbl_title)
        
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels(["Library", "Count"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setAlternatingRowColors(True)
        layout.addWidget(self.table)

    def load_data(self, project_name, data):
        # We need BOM data. We can try to generate it or use cached structure if available.
        sch = self.logic.resolve_path(data["metadata"].get("main_schematic"))
        
        self.table.setRowCount(0)
        if not sch: return
        
        # This might be slow if done on main thread, but BOM generation is usually fast enough for small projects.
        bom = self.logic.generate_bom(sch)
        
        lib_counts = Counter()
        for item in bom:
            lib_counts[item['lib_id'].split(':')[0]] += item['qty']
            
        sorted_libs = sorted(lib_counts.items(), key=lambda x: x[1], reverse=True)
        
        for lib, count in sorted_libs:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(lib))
            self.table.setItem(row, 1, QTableWidgetItem(str(count)))