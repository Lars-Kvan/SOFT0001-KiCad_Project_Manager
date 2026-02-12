from PySide6.QtWidgets import (QWidget, QVBoxLayout, QPushButton, QTabWidget, QMessageBox)
from PySide6.QtCore import Qt, Signal
from .settings_pages import GeneralSettingsPage, ProjectConfigPage, KanbanSettingsPage, BackupSettingsPage

class SettingsTab(QWidget):
    settings_saved = Signal()
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.inputs = {}
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)
        
        # Tab 1: General
        self.page_general = GeneralSettingsPage(self.logic)
        self.tabs.addTab(self.page_general, "General")
        
        # Tab 2: Project Config
        self.page_proj = ProjectConfigPage(self.logic)
        self.tabs.addTab(self.page_proj, "Project Configuration")
        
        # Tab 3: Kanban Settings
        self.page_kanban = KanbanSettingsPage(self.logic)
        self.tabs.addTab(self.page_kanban, "Kanban Settings")
        
        # Tab 4: Auto Backup
        self.page_backup = BackupSettingsPage(self.logic)
        self.tabs.addTab(self.page_backup, "Auto Backup")
        
        layout.addStretch()
        btn_save = QPushButton("Save All Settings")
        btn_save.clicked.connect(self.save)
        layout.addWidget(btn_save)

    def save(self):
        self.page_general.save_settings()
        self.page_proj.save_settings()
        self.page_kanban.save_settings()
        self.page_backup.save_settings()
        
        self.logic.save_settings()
        QMessageBox.information(self, "Saved", "Settings saved.")
        self.settings_saved.emit()