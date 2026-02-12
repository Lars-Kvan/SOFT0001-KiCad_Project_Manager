"""
ui/views/ui_git.py
Modern Git Interface for KiCad Project Manager
"""
import os
import sys
import subprocess
import threading
from datetime import datetime

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QScrollArea, QFrame, QGridLayout, QTextEdit,
    QDialog, QMessageBox, QProgressBar, QMenu, QSizePolicy,
    QGraphicsDropShadowEffect, QToolButton, QLineEdit
)
from PySide6.QtCore import Qt, QSize, Signal, QThread, QTimer, QObject
from PySide6.QtGui import QColor, QAction, QCursor, QFont, QIcon

from ui.resources.icons import Icons

# --- Constants & Styles ---

STYLE_CARD = """
QFrame#repoCard {
    background-color: %BG%;
    border: 1px solid %BORDER%;
    border-radius: 8px;
}
QFrame#repoCard:hover {
    border: 1px solid %ACCENT%;
}
"""

STYLE_BADGE = """
QLabel {
    background-color: %BG%;
    color: %FG%;
    border-radius: 4px;
    padding: 2px 6px;
    font-weight: bold;
    font-size: 11px;
}
"""

class GitWorker(QObject):
    """Worker to run blocking git commands in a separate thread."""
    finished = Signal(bool, str, str)  # success, stdout, stderr

    def __init__(self, command, cwd):
        super().__init__()
        self.command = command
        self.cwd = cwd

    def run(self):
        try:
            # Prevent console window popping up on Windows
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            process = subprocess.Popen(
                self.command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding='utf-8',
                errors='replace',
                startupinfo=startupinfo
            )
            stdout, stderr = process.communicate()
            success = process.returncode == 0
            self.finished.emit(success, stdout, stderr)
        except Exception as e:
            self.finished.emit(False, "", str(e))

class CommitDialog(QDialog):
    def __init__(self, parent, repo_name, staged_files=None):
        super().__init__(parent)
        self.setWindowTitle(f"Commit to {repo_name}")
        self.resize(500, 400)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        lbl = QLabel("Commit Message")
        lbl.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl)

        self.msg_edit = QTextEdit()
        self.msg_edit.setPlaceholderText("Enter commit message...")
        layout.addWidget(self.msg_edit)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        
        self.btn_commit = QPushButton("Commit")
        self.btn_commit.setStyleSheet("background-color: #10B981; color: white; font-weight: bold;")
        self.btn_commit.clicked.connect(self.accept)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_commit)
        layout.addLayout(btn_layout)

    def get_message(self):
        return self.msg_edit.toPlainText().strip()

class RepoCard(QFrame):
    request_refresh = Signal()
    
    def __init__(self, repo_data, logic, parent=None):
        super().__init__(parent)
        self.repo = repo_data
        self.logic = logic
        self.setObjectName("repoCard")
        self.setup_ui()
        self.apply_theme()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header: Icon, Name, Path
        header = QHBoxLayout()
        
        icon_lbl = QLabel()
        icon_color = "#E0E0E0" if self.is_dark_theme() else "#333333"
        icon_lbl.setPixmap(Icons.get_icon(Icons.GIT, icon_color).pixmap(20, 20))
        header.addWidget(icon_lbl)

        name_layout = QVBoxLayout()
        name_layout.setSpacing(2)
        
        self.lbl_name = QLabel(self.repo.get("name", "Unknown"))
        self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.lbl_path = QLabel(self.repo.get("path", ""))
        self.lbl_path.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_path.setWordWrap(True)
        
        name_layout.addWidget(self.lbl_name)
        name_layout.addWidget(self.lbl_path)
        header.addLayout(name_layout, 1)

        # Status Badges
        self.status_container = QHBoxLayout()
        self.status_container.setSpacing(8)
        header.addLayout(self.status_container)

        layout.addLayout(header)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        line.setStyleSheet("background-color: #333;" if self.is_dark_theme() else "background-color: #EEE;")
        line.setFixedHeight(1)
        layout.addWidget(line)

        # Actions Row
        actions = QHBoxLayout()
        actions.setSpacing(10)

        self.btn_pull = QPushButton("Pull")
        self.btn_pull.setIcon(Icons.get_icon(Icons.GLOBE, "#3B82F6"))
        self.btn_pull.clicked.connect(self.do_pull)
        
        self.btn_push = QPushButton("Push")
        self.btn_push.setIcon(Icons.get_icon(Icons.GLOBE, "#8B5CF6"))
        self.btn_push.clicked.connect(self.do_push)
        
        self.btn_commit = QPushButton("Commit")
        self.btn_commit.setIcon(Icons.get_icon(Icons.SAVE, "#10B981"))
        self.btn_commit.clicked.connect(self.do_commit)

        self.btn_term = QToolButton()
        self.btn_term.setText("Terminal")
        self.btn_term.setToolTip("Open in Terminal")
        self.btn_term.clicked.connect(self.open_terminal)

        actions.addWidget(self.btn_pull)
        actions.addWidget(self.btn_push)
        actions.addWidget(self.btn_commit)
        actions.addStretch()
        actions.addWidget(self.btn_term)

        layout.addLayout(actions)

        self.update_status_display()

    def is_dark_theme(self):
        return self.logic.settings.get("theme", "Light") in {"Dark", "Teal Sand Dark"}

    def apply_theme(self):
        is_dark = self.is_dark_theme()
        bg = "#1E1E1E" if is_dark else "#FFFFFF"
        border = "#333333" if is_dark else "#E5E7EB"
        accent = "#3B82F6"
        
        style = STYLE_CARD.replace("%BG%", bg).replace("%BORDER%", border).replace("%ACCENT%", accent)
        self.setStyleSheet(style)
        
        # Shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(15)
        shadow.setOffset(0, 4)
        shadow.setColor(QColor(0, 0, 0, 60 if is_dark else 20))
        self.setGraphicsEffect(shadow)

    def update_status_display(self):
        # Clear old badges
        while self.status_container.count():
            item = self.status_container.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Branch Badge
        branch = self.repo.get("branch", "-")
        self.add_badge(branch, "#374151", "#F3F4F6")

        # Ahead/Behind
        ahead = self.repo.get("ahead", 0)
        behind = self.repo.get("behind", 0)
        
        if ahead > 0:
            self.add_badge(f"Ahead {ahead}", "#EFF6FF", "#1D4ED8")
        if behind > 0:
            self.add_badge(f"Behind {behind}", "#FEF2F2", "#B91C1C")
            
        # Clean/Dirty
        if not self.repo.get("clean", True):
            self.add_badge("Uncommitted Changes", "#FFFBEB", "#B45309")
        else:
            self.add_badge("Clean", "#ECFDF5", "#047857")

    def add_badge(self, text, bg, fg):
        lbl = QLabel(text)
        # Invert colors for dark mode if needed, but these are tailwind-ish presets
        if self.is_dark_theme():
            # Simple inversion for visibility
            bg, fg = fg, bg 
            
        style = STYLE_BADGE.replace("%BG%", bg).replace("%FG%", fg)
        lbl.setStyleSheet(style)
        self.status_container.addWidget(lbl)

    def run_git(self, args, success_msg=None):
        path = self.repo.get("path")
        if not path or not os.path.exists(path):
            QMessageBox.warning(self, "Error", "Repository path does not exist.")
            return

        # Disable buttons
        self.set_buttons_enabled(False)
        
        # Create worker
        cmd = ["git"] + args
        self.worker = GitWorker(cmd, path)
        self.worker_thread = QThread()
        self.worker.moveToThread(self.worker_thread)
        
        self.worker_thread.started.connect(self.worker.run)
        self.worker.finished.connect(lambda s, o, e: self.on_git_finished(s, o, e, success_msg))
        self.worker.finished.connect(self.worker_thread.quit)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        
        self.worker_thread.start()

    def on_git_finished(self, success, stdout, stderr, success_msg):
        self.set_buttons_enabled(True)
        if success:
            if success_msg:
                # Show small toast or status bar message? For now just refresh
                pass
            self.request_refresh.emit()
        else:
            QMessageBox.critical(self, "Git Error", f"Command failed:\n{stderr}\n{stdout}")

    def set_buttons_enabled(self, enabled):
        self.btn_pull.setEnabled(enabled)
        self.btn_push.setEnabled(enabled)
        self.btn_commit.setEnabled(enabled)

    def do_pull(self):
        self.run_git(["pull"], "Pull successful")

    def do_push(self):
        self.run_git(["push"], "Push successful")

    def do_commit(self):
        dlg = CommitDialog(self, self.repo.get("name"))
        if dlg.exec():
            msg = dlg.get_message()
            if msg:
                # Stage all and commit
                # Chain commands: git add . && git commit -m "msg"
                # Subprocess doesn't like chaining easily without shell=True, 
                # so we'll do a composite python method or just two calls.
                # For simplicity in this UI, we'll assume 'add -A' is desired.
                
                path = self.repo.get("path")
                try:
                    subprocess.run(["git", "add", "-A"], cwd=path, check=True)
                    self.run_git(["commit", "-m", msg], "Commit successful")
                except subprocess.CalledProcessError as e:
                    QMessageBox.critical(self, "Error", f"Failed to stage files: {e}")

    def open_terminal(self):
        path = self.repo.get("path")
        if not path: return
        
        if os.name == 'nt':
            subprocess.Popen(['start', 'cmd', '/k', f'cd /d "{path}"'], shell=True)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-a', 'Terminal', path])
        else:
            subprocess.Popen(['x-terminal-emulator', '--working-directory', path])


class GitTab(QWidget):
    """
    Git Tab. 
    If compact=True, displays a single repository view (used in Project Manager).
    If compact=False (default), acts as a base class or empty container.
    """
    def __init__(self, logic, compact=False):
        super().__init__()
        self.logic = logic
        self.compact = compact
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0,0,0,0)
        
        if self.compact:
            self.setup_single_repo_ui()

    def setup_single_repo_ui(self):
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setAlignment(Qt.AlignTop)
        self.container_layout.setContentsMargins(10, 10, 10, 10)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)
        self.current_repo_path = None

    def set_repo_path(self, path):
        if not self.compact:
            return
        self.current_repo_path = path
        self.refresh_repo()

    def refresh_repo(self):
        if not self.compact:
            return
            
        # Clear existing
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.current_repo_path:
            return

        # Use RepoLoader to fetch data (async)
        self.loader_thread = QThread()
        self.loader = RepoLoader(self.logic)
        self.loader.moveToThread(self.loader_thread)
        self.loader_thread.started.connect(self.loader.run)
        self.loader.finished.connect(self.on_repo_loaded)
        self.loader.finished.connect(self.loader_thread.quit)
        self.loader.finished.connect(self.loader.deleteLater)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)
        self.loader_thread.start()

    def on_repo_loaded(self, repos):
        if not self.current_repo_path:
            return
            
        target = None
        norm_target = os.path.normpath(self.current_repo_path).lower()
        
        for r in repos:
            r_path = r.get("path", "")
            if r_path and os.path.normpath(r_path).lower() == norm_target:
                target = r
                break
        
        if target:
            card = RepoCard(target, self.logic)
            card.request_refresh.connect(self.refresh_repo)
            self.container_layout.addWidget(card)
        else:
            lbl = QLabel("No git repository found.")
            lbl.setStyleSheet("color: #888; margin-top: 20px;")
            lbl.setAlignment(Qt.AlignCenter)
            self.container_layout.addWidget(lbl)
            
            btn_init = QPushButton("Initialize Repository")
            btn_init.setFixedWidth(150)
            btn_init.clicked.connect(self.init_repo)
            
            h = QHBoxLayout()
            h.addStretch()
            h.addWidget(btn_init)
            h.addStretch()
            self.container_layout.addLayout(h)

    def init_repo(self):
        if not self.current_repo_path or not os.path.exists(self.current_repo_path):
            return
        try:
            subprocess.run(["git", "init"], cwd=self.current_repo_path, check=True)
            self.refresh_repo()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to init git: {e}")

class GitOverviewTab(GitTab):
    def __init__(self, logic):
        super().__init__(logic)
        self.filter_types = None # All
        self.setup_ui()
        self.refresh_timer = QTimer(self)
        self.refresh_timer.setSingleShot(True)
        self.refresh_timer.timeout.connect(self.refresh_repos)
        
        # Initial load
        QTimer.singleShot(100, self.refresh_repos)

    def setup_ui(self):
        # Toolbar
        toolbar = QFrame()
        toolbar.setObjectName("gitToolbar")
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(20, 10, 20, 10)
        
        lbl_title = QLabel("Repositories")
        lbl_title.setStyleSheet("font-size: 18px; font-weight: bold;")
        tb_layout.addWidget(lbl_title)
        
        tb_layout.addStretch()
        
        self.btn_refresh = QPushButton("Refresh All")
        self.btn_refresh.setIcon(Icons.get_icon(Icons.SEARCH, "#555"))
        self.btn_refresh.clicked.connect(self.refresh_repos)
        tb_layout.addWidget(self.btn_refresh)
        
        self.layout.addWidget(toolbar)

        # Scroll Area
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(20, 0, 20, 20)
        self.container_layout.setSpacing(16)
        self.container_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.container)
        self.layout.addWidget(self.scroll)

    def set_repo_path(self, path):
        """Called by main window to focus on a specific repo."""
        # For now, just refresh. In future, scroll to specific card.
        self.refresh_repos()

    def refresh_repos(self):
        self.btn_refresh.setEnabled(False)
        self.btn_refresh.setText("Loading...")
        
        # Run in thread to avoid freeze
        self.loader_thread = QThread()
        self.loader = RepoLoader(self.logic)
        self.loader.moveToThread(self.loader_thread)
        
        self.loader_thread.started.connect(self.loader.run)
        self.loader.finished.connect(self.on_repos_loaded)
        self.loader.finished.connect(self.loader_thread.quit)
        self.loader.finished.connect(self.loader.deleteLater)
        self.loader_thread.finished.connect(self.loader_thread.deleteLater)
        
        self.loader_thread.start()

    def on_repos_loaded(self, repos):
        self.btn_refresh.setEnabled(True)
        self.btn_refresh.setText("Refresh All")
        
        # Clear existing
        while self.container_layout.count():
            item = self.container_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        # Filter
        if self.filter_types:
            repos = [r for r in repos if r.get("type") in self.filter_types]

        if not repos:
            lbl = QLabel("No git repositories found.")
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet("color: #888; font-size: 14px; margin-top: 40px;")
            self.container_layout.addWidget(lbl)
            return

        # Grouping (Optional, for now just flat list)
        for repo in repos:
            card = RepoCard(repo, self.logic)
            card.request_refresh.connect(self.refresh_repos)
            self.container_layout.addWidget(card)

class LibraryGitTab(GitOverviewTab):
    def __init__(self, logic):
        super().__init__(logic)
        self.filter_types = ["symbol", "footprint"]

class RepoLoader(QObject):
    finished = Signal(list)
    
    def __init__(self, logic):
        super().__init__()
        self.logic = logic

    def run(self):
        # This calls the backend logic which probes git status
        repos = self.logic.get_git_repositories()
        self.finished.emit(repos)