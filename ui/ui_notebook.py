import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem, 
                             QTextEdit, QPushButton, QInputDialog, QMessageBox, QSplitter, QHeaderView)
from PySide6.QtCore import Qt
try:
    from .icons import Icons
except ImportError:
    from ui.icons import Icons

class NotebookTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        # Store notes in a 'notes' subdirectory
        self.notes_dir = os.path.join(os.getcwd(), "notes")
        if not os.path.exists(self.notes_dir):
            os.makedirs(self.notes_dir)
        self.current_file = None
        self.setup_ui()
        self.refresh_list()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # Left: Page List
        left_widget = QWidget()
        l_layout = QVBoxLayout(left_widget)
        l_layout.setContentsMargins(0,0,0,0)
        
        h_btns = QHBoxLayout()
        btn_add = QPushButton("New Page")
        btn_add.setIcon(Icons.get_icon(Icons.PLUS, icon_color))
        btn_add.clicked.connect(self.new_page)
        h_btns.addWidget(btn_add)
        
        btn_del = QPushButton("Delete")
        btn_del.setIcon(Icons.get_icon(Icons.TRASH, icon_color))
        btn_del.clicked.connect(self.delete_page)
        h_btns.addWidget(btn_del)
        l_layout.addLayout(h_btns)

        self.tree = QTreeWidget()
        self.tree.setHeaderLabel("Pages")
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.itemClicked.connect(self.load_page)
        l_layout.addWidget(self.tree)
        
        splitter.addWidget(left_widget)

        # Right: Editor
        right_widget = QWidget()
        r_layout = QVBoxLayout(right_widget)
        r_layout.setContentsMargins(0,0,0,0)
        
        h_tools = QHBoxLayout()
        btn_save = QPushButton("Save")
        btn_save.setIcon(Icons.get_icon(Icons.SAVE, icon_color))
        btn_save.clicked.connect(self.save_current)
        h_tools.addWidget(btn_save)
        h_tools.addStretch()
        r_layout.addLayout(h_tools)

        self.editor = QTextEdit()
        self.editor.setPlaceholderText("Select or create a page to start writing...")
        self.editor.textChanged.connect(self.auto_save_trigger)
        r_layout.addWidget(self.editor)
        
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(1, 3)

    def refresh_list(self):
        self.tree.clear()
        if os.path.exists(self.notes_dir):
            files = sorted([f for f in os.listdir(self.notes_dir) if f.endswith(".txt") or f.endswith(".md")])
            for f in files:
                item = QTreeWidgetItem(self.tree)
                item.setText(0, os.path.splitext(f)[0])
                item.setData(0, Qt.UserRole, f)

    def new_page(self):
        name, ok = QInputDialog.getText(self, "New Page", "Page Name:")
        if ok and name:
            filename = f"{name}.txt"
            path = os.path.join(self.notes_dir, filename)
            if not os.path.exists(path):
                with open(path, 'w') as f: f.write("")
            self.refresh_list()

    def delete_page(self):
        item = self.tree.currentItem()
        if not item: return
        filename = item.data(0, Qt.UserRole)
        if QMessageBox.question(self, "Confirm", f"Delete '{filename}'?") == QMessageBox.Yes:
            os.remove(os.path.join(self.notes_dir, filename))
            self.refresh_list()
            self.editor.clear()
            self.current_file = None

    def load_page(self, item):
        filename = item.data(0, Qt.UserRole)
        self.current_file = os.path.join(self.notes_dir, filename)
        with open(self.current_file, 'r', encoding='utf-8') as f:
            self.editor.setPlainText(f.read())

    def save_current(self):
        if self.current_file:
            with open(self.current_file, 'w', encoding='utf-8') as f:
                f.write(self.editor.toPlainText())

    def auto_save_trigger(self):
        # Simple auto-save could go here, or just rely on manual save button
        pass