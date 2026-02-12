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
    QGraphicsDropShadowEffect, QToolButton, QLineEdit, QApplication,
    QSplitter, QListWidget, QListWidgetItem, QInputDialog, QTabWidget,
    QTableWidget, QTableWidgetItem, QHeaderView, QCheckBox
)
from PySide6.QtCore import Qt, QSize, Signal, QThread, QTimer, QObject, QUrl
from PySide6.QtGui import QColor, QAction, QCursor, QFont, QIcon, QDesktopServices, QSyntaxHighlighter, QTextCharFormat

from ui.resources.icons import Icons

# --- Constants & Styles ---

STYLE_LIST_ITEM = """
QFrame#repoListItem {
    background-color: %BG%;
    border-bottom: 1px solid %BORDER%;
    border-radius: 4px;
}
QFrame#repoListItem:hover {
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

class DiffHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        self.header_fmt = QTextCharFormat()
        self.header_fmt.setForeground(QColor("#2563EB"))
        self.header_fmt.setFontWeight(QFont.Bold)
        
        self.add_fmt = QTextCharFormat()
        self.add_fmt.setForeground(QColor("#10B981"))
        
        self.rem_fmt = QTextCharFormat()
        self.rem_fmt.setForeground(QColor("#EF4444"))
        
        self.chunk_fmt = QTextCharFormat()
        self.chunk_fmt.setForeground(QColor("#8B5CF6"))

    def highlightBlock(self, text):
        if text.startswith("diff ") or text.startswith("index ") or text.startswith("+++") or text.startswith("---"):
            self.setFormat(0, len(text), self.header_fmt)
        elif text.startswith("@@"):
            self.setFormat(0, len(text), self.chunk_fmt)
        elif text.startswith("+"):
            self.setFormat(0, len(text), self.add_fmt)
        elif text.startswith("-"):
            self.setFormat(0, len(text), self.rem_fmt)

class RepoDetailView(QWidget):
    """
    Integrated view for a single repository.
    Contains Tabs: Changes (Status/Diff/Commit), History, Branches, Stash.
    """
    def __init__(self, logic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.repo_path = None
        self.repo_name = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # --- Toolbar ---
        toolbar = QFrame()
        toolbar.setStyleSheet("background-color: #f1f5f9; border-bottom: 1px solid #e2e8f0;")
        if self.logic.settings.get("theme") in {"Dark", "Teal Sand Dark"}:
            toolbar.setStyleSheet("background-color: #1e1e1e; border-bottom: 1px solid #333;")
        
        tb_layout = QHBoxLayout(toolbar)
        tb_layout.setContentsMargins(10, 5, 10, 5)
        
        self.lbl_repo_name = QLabel("No Repository Selected")
        self.lbl_repo_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        tb_layout.addWidget(self.lbl_repo_name)
        
        tb_layout.addStretch()
        
        self.btn_pull = QPushButton("Pull")
        self.btn_pull.setIcon(Icons.get_icon(Icons.GLOBE, "#3B82F6"))
        self.btn_pull.clicked.connect(lambda: self.run_git_command(["pull"], "Pull successful"))
        
        self.btn_push = QPushButton("Push")
        self.btn_push.setIcon(Icons.get_icon(Icons.GLOBE, "#8B5CF6"))
        self.btn_push.clicked.connect(lambda: self.run_git_command(["push"], "Push successful"))
        
        self.btn_fetch = QPushButton("Fetch")
        self.btn_fetch.setIcon(Icons.get_icon(Icons.SEARCH, "#10B981"))
        self.btn_fetch.clicked.connect(lambda: self.run_git_command(["fetch"], "Fetch successful"))

        self.btn_term = QToolButton()
        self.btn_term.setText("Terminal")
        self.btn_term.clicked.connect(self.open_terminal)

        tb_layout.addWidget(self.btn_pull)
        tb_layout.addWidget(self.btn_push)
        tb_layout.addWidget(self.btn_fetch)
        tb_layout.addWidget(self.btn_term)
        
        layout.addWidget(toolbar)

        # --- Tabs ---
        self.tabs = QTabWidget()
        self.tabs.currentChanged.connect(self.on_tab_changed)
        layout.addWidget(self.tabs)

        # 1. Changes Tab (Status + Diff + Commit)
        self.tab_changes = QWidget()
        self.setup_changes_tab(self.tab_changes)
        self.tabs.addTab(self.tab_changes, "Changes")

        # 2. History Tab
        self.tab_history = QWidget()
        self.setup_history_tab(self.tab_history)
        self.tabs.addTab(self.tab_history, "History")

        # 3. Branches Tab
        self.tab_branches = QWidget()
        self.setup_branches_tab(self.tab_branches)
        self.tabs.addTab(self.tab_branches, "Branches")

        # 4. Stash Tab
        self.tab_stash = QWidget()
        self.setup_stash_tab(self.tab_stash)
        self.tabs.addTab(self.tab_stash, "Stash")

        # Disable initially
        self.set_enabled_all(False)

    def setup_changes_tab(self, parent):
        layout = QVBoxLayout(parent)
        
        splitter = QSplitter(Qt.Vertical)
        
        # Top: File List | Diff
        top_splitter = QSplitter(Qt.Horizontal)
        
        # File List
        self.file_list = QListWidget()
        self.file_list.itemChanged.connect(self.on_file_check_changed)
        self.file_list.currentItemChanged.connect(self.on_file_selected)
        top_splitter.addWidget(self.file_list)
        
        # Diff View
        self.diff_view = QTextEdit()
        self.diff_view.setReadOnly(True)
        self.diff_view.setStyleSheet("font-family: Consolas, monospace; font-size: 12px;")
        self.highlighter = DiffHighlighter(self.diff_view.document())
        top_splitter.addWidget(self.diff_view)
        top_splitter.setStretchFactor(1, 3)
        
        splitter.addWidget(top_splitter)
        
        # Bottom: Commit Area
        commit_frame = QFrame()
        commit_layout = QVBoxLayout(commit_frame)
        commit_layout.setContentsMargins(0, 10, 0, 0)
        
        lbl = QLabel("Commit Message")
        lbl.setStyleSheet("font-weight: bold;")
        commit_layout.addWidget(lbl)
        
        self.msg_edit = QTextEdit()
        self.msg_edit.setPlaceholderText("Enter commit message...")
        self.msg_edit.setMaximumHeight(80)
        commit_layout.addWidget(self.msg_edit)
        
        btn_row = QHBoxLayout()
        self.btn_refresh_status = QPushButton("Refresh Status")
        self.btn_refresh_status.clicked.connect(self.refresh_status)
        
        self.btn_commit = QPushButton("Commit")
        self.btn_commit.setStyleSheet("background-color: #10B981; color: white; font-weight: bold; padding: 6px 12px;")
        self.btn_commit.clicked.connect(self.do_commit)
        
        btn_row.addWidget(self.btn_refresh_status)
        btn_row.addStretch()
        btn_row.addWidget(self.btn_commit)
        commit_layout.addLayout(btn_row)
        
        splitter.addWidget(commit_frame)
        splitter.setStretchFactor(0, 4)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)

    def setup_history_tab(self, parent):
        layout = QVBoxLayout(parent)
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(4)
        self.history_table.setHorizontalHeaderLabels(["Hash", "Date", "Author", "Message"])
        self.history_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.history_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.history_table.verticalHeader().setVisible(False)
        layout.addWidget(self.history_table)
        
        btn_refresh = QPushButton("Refresh History")
        btn_refresh.clicked.connect(self.refresh_history)
        layout.addWidget(btn_refresh)

    def setup_branches_tab(self, parent):
        layout = QVBoxLayout(parent)
        self.branch_list = QListWidget()
        self.branch_list.setContextMenuPolicy(Qt.CustomContextMenu)
        self.branch_list.customContextMenuRequested.connect(self.show_branch_menu)
        layout.addWidget(self.branch_list)
        
        btn_row = QHBoxLayout()
        btn_new = QPushButton("New Branch")
        btn_new.clicked.connect(self.create_branch)
        btn_refresh = QPushButton("Refresh Branches")
        btn_refresh.clicked.connect(self.refresh_branches)
        btn_row.addWidget(btn_new)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def setup_stash_tab(self, parent):
        layout = QVBoxLayout(parent)
        self.stash_list = QListWidget()
        layout.addWidget(self.stash_list)
        
        btn_row = QHBoxLayout()
        btn_stash = QPushButton("Stash Changes")
        btn_stash.clicked.connect(self.do_stash)
        btn_pop = QPushButton("Pop Stash")
        btn_pop.clicked.connect(self.pop_stash)
        btn_refresh = QPushButton("Refresh")
        btn_refresh.clicked.connect(self.refresh_stash)
        
        btn_row.addWidget(btn_stash)
        btn_row.addWidget(btn_pop)
        btn_row.addWidget(btn_refresh)
        btn_row.addStretch()
        layout.addLayout(btn_row)

    def set_repo(self, path, name="Repository"):
        self.repo_path = path
        self.repo_name = name
        self.lbl_repo_name.setText(name if name else "No Repository Selected")
        
        if path and os.path.exists(path):
            self.set_enabled_all(True)
            self.refresh_current_tab()
        else:
            self.set_enabled_all(False)

    def set_enabled_all(self, enabled):
        self.tabs.setEnabled(enabled)
        self.btn_pull.setEnabled(enabled)
        self.btn_push.setEnabled(enabled)
        self.btn_fetch.setEnabled(enabled)
        self.btn_term.setEnabled(enabled)

    def on_tab_changed(self, index):
        self.refresh_current_tab()

    def refresh_current_tab(self):
        if not self.repo_path: return
        idx = self.tabs.currentIndex()
        if idx == 0: self.refresh_status()
        elif idx == 1: self.refresh_history()
        elif idx == 2: self.refresh_branches()
        elif idx == 3: self.refresh_stash()

    # --- Git Operations ---

    def run_git_command(self, args, success_msg=None, refresh_after=True):
        if not self.repo_path: return
        
        worker = GitWorker(["git"] + args, self.repo_path)
        thread = QThread()
        worker.moveToThread(thread)
        
        # Store refs to prevent GC
        self._current_worker = worker
        self._current_thread = thread
        
        thread.started.connect(worker.run)
        worker.finished.connect(lambda s, o, e: self.on_git_finished(s, o, e, success_msg, refresh_after))
        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.start()

    def on_git_finished(self, success, stdout, stderr, success_msg, refresh_after):
        if success:
            if success_msg:
                # Could show status bar message
                pass
            if refresh_after:
                self.refresh_current_tab()
        else:
            QMessageBox.critical(self, "Git Error", f"Command failed:\n{stderr}\n{stdout}")

    # --- Status / Changes ---

    def refresh_status(self):
        self.file_list.clear()
        self.diff_view.clear()
        try:
            cmd = ["git", "status", "--porcelain"]
            result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, check=True)
            for line in result.stdout.splitlines():
                if not line.strip(): continue
                status = line[:2]
                filename = line[3:].strip()
                is_staged = status[0] not in (' ', '?')
                item = QListWidgetItem(f"[{status}] {filename}")
                item.setData(Qt.UserRole, filename)
                item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                item.setCheckState(Qt.Checked if is_staged else Qt.Unchecked)
                self.file_list.addItem(item)
        except Exception as e:
            self.diff_view.setText(f"Error: {e}")

    def on_file_check_changed(self, item):
        filename = item.data(Qt.UserRole)
        if item.checkState() == Qt.Checked:
            subprocess.run(["git", "add", filename], cwd=self.repo_path)
        else:
            subprocess.run(["git", "restore", "--staged", filename], cwd=self.repo_path)

    def on_file_selected(self, current, previous):
        if not current: return
        filename = current.data(Qt.UserRole)
        text_label = current.text()
        try:
            if "??" in text_label:
                full_path = os.path.join(self.repo_path, filename)
                if os.path.exists(full_path):
                    with open(full_path, "r", encoding="utf-8", errors="replace") as f:
                        self.diff_view.setText(f.read())
            else:
                cmd = ["git", "diff", "HEAD", "--", filename]
                result = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True)
                self.diff_view.setText(result.stdout if result.stdout else "(No diff output)")
        except Exception as e:
            self.diff_view.setText(f"Error loading diff: {e}")

    def do_commit(self):
        msg = self.msg_edit.toPlainText().strip()
        if not msg:
            QMessageBox.warning(self, "Error", "Commit message cannot be empty.")
            return
        self.run_git_command(["commit", "-m", msg], "Commit successful")
        self.msg_edit.clear()

    # --- History ---

    def refresh_history(self):
        self.history_table.setRowCount(0)
        try:
            cmd = ["git", "log", "--pretty=format:%h|%ad|%an|%s", "--date=short", "-n", "50"]
            res = subprocess.run(cmd, cwd=self.repo_path, capture_output=True, text=True, encoding='utf-8', errors='replace')
            for line in res.stdout.splitlines():
                parts = line.split("|", 3)
                if len(parts) < 4: continue
                row = self.history_table.rowCount()
                self.history_table.insertRow(row)
                for i, txt in enumerate(parts):
                    self.history_table.setItem(row, i, QTableWidgetItem(txt))
        except Exception as e:
            pass

    # --- Branches ---

    def refresh_branches(self):
        self.branch_list.clear()
        try:
            res = subprocess.run(["git", "branch"], cwd=self.repo_path, capture_output=True, text=True)
            for line in res.stdout.splitlines():
                clean = line.strip()
                item = QListWidgetItem(clean)
                if clean.startswith("*"):
                    item.setForeground(QColor("#10B981"))
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.branch_list.addItem(item)
        except: pass

    def create_branch(self):
        name, ok = QInputDialog.getText(self, "New Branch", "Branch Name:")
        if ok and name:
            self.run_git_command(["checkout", "-b", name.strip()], "Branch created")

    def show_branch_menu(self, pos):
        item = self.branch_list.itemAt(pos)
        if not item: return
        name = item.text().replace("* ", "").strip()
        
        menu = QMenu()
        act_co = menu.addAction("Checkout")
        act_del = menu.addAction("Delete")
        
        action = menu.exec(self.branch_list.mapToGlobal(pos))
        if action == act_co:
            self.run_git_command(["checkout", name], f"Switched to {name}")
        elif action == act_del:
            if QMessageBox.question(self, "Confirm", f"Delete branch {name}?") == QMessageBox.Yes:
                self.run_git_command(["branch", "-D", name], "Branch deleted")

    # --- Stash ---

    def refresh_stash(self):
        self.stash_list.clear()
        try:
            res = subprocess.run(["git", "stash", "list"], cwd=self.repo_path, capture_output=True, text=True)
            for line in res.stdout.splitlines():
                self.stash_list.addItem(line)
        except: pass

    def do_stash(self):
        msg, ok = QInputDialog.getText(self, "Stash", "Message (optional):")
        if ok:
            args = ["stash", "push"]
            if msg: args.extend(["-m", msg])
            self.run_git_command(args, "Changes stashed")

    def pop_stash(self):
        if self.stash_list.count() > 0:
            self.run_git_command(["stash", "pop"], "Stash popped")

    def open_terminal(self):
        if not self.repo_path: return
        if os.name == 'nt':
            subprocess.Popen(['start', 'cmd', '/k', f'cd /d "{self.repo_path}"'], shell=True)
        elif sys.platform == 'darwin':
            subprocess.Popen(['open', '-a', 'Terminal', self.repo_path])
        else:
            subprocess.Popen(['x-terminal-emulator', '--working-directory', self.repo_path])

class RepoListItem(QFrame):
    """Compact card for the repository list."""
    selected = Signal(str, str) # path, name
    
    def __init__(self, repo_data, logic, parent=None):
        super().__init__(parent)
        self.repo = repo_data
        self.logic = logic
        self.setObjectName("repoListItem")
        self.setup_ui()
        self.apply_theme()

    def mousePressEvent(self, event):
        self.selected.emit(self.repo.get("path"), self.repo.get("name"))
        super().mousePressEvent(event)

    def setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        icon_lbl = QLabel()
        icon_color = "#E0E0E0" if self.is_dark_theme() else "#333333"
        icon_lbl.setPixmap(Icons.get_icon(Icons.GIT, icon_color).pixmap(20, 20))
        layout.addWidget(icon_lbl)

        name_layout = QVBoxLayout()
        name_layout.setSpacing(2)
        
        self.lbl_name = QLabel(self.repo.get("name", "Unknown"))
        self.lbl_name.setStyleSheet("font-size: 14px; font-weight: bold;")
        
        self.lbl_path = QLabel(self.repo.get("path", ""))
        self.lbl_path.setStyleSheet("color: #888; font-size: 11px;")
        self.lbl_path.setWordWrap(True)

        name_layout.addWidget(self.lbl_name)
        name_layout.addWidget(self.lbl_path)
        layout.addLayout(name_layout, 1)
        
        # Status Pill
        branch = self.repo.get("branch", "-")
        lbl_branch = QLabel(branch)
        lbl_branch.setStyleSheet("background-color: #374151; color: #F3F4F6; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
        if not self.is_dark_theme():
            lbl_branch.setStyleSheet("background-color: #E5E7EB; color: #1F2937; border-radius: 4px; padding: 2px 6px; font-size: 10px;")
        layout.addWidget(lbl_branch)

    def is_dark_theme(self):
        return self.logic.settings.get("theme", "Light") in {"Dark", "Teal Sand Dark"}

    def apply_theme(self):
        is_dark = self.is_dark_theme()
        bg = "#1E1E1E" if is_dark else "#FFFFFF"
        border = "#333333" if is_dark else "#E5E7EB"
        accent = "#3B82F6"
        
        style = STYLE_LIST_ITEM.replace("%BG%", bg).replace("%BORDER%", border).replace("%ACCENT%", accent)
        self.setStyleSheet(style)

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
            self.detail_view = RepoDetailView(self.logic)
            self.layout.addWidget(self.detail_view)
        else:
            # Placeholder for Overview Tab logic
            pass

    def set_repo_path(self, path):
        if not self.compact:
            return
        self.detail_view.set_repo(path, "Project Repository")

    def refresh_repo(self):
        if not self.compact:
            return
        # For compact view, refresh is handled by detail view actions
        pass

    def init_repo(self):
        # Logic moved to detail view or handled externally
        pass

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
        # Splitter: List | Detail
        self.splitter = QSplitter(Qt.Horizontal)
        
        # Left: List
        self.left_panel = QWidget()
        left_layout = QVBoxLayout(self.left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Toolbar for list
        list_toolbar = QHBoxLayout()
        list_toolbar.setContentsMargins(10, 10, 10, 5)
        lbl = QLabel("Repositories")
        lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        btn_refresh = QToolButton()
        btn_refresh.setIcon(Icons.get_icon(Icons.SEARCH, "#555"))
        btn_refresh.clicked.connect(self.refresh_repos)
        list_toolbar.addWidget(lbl)
        list_toolbar.addStretch()
        list_toolbar.addWidget(btn_refresh)
        left_layout.addLayout(list_toolbar)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.NoFrame)
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(10, 0, 10, 10)
        self.container_layout.setSpacing(8)
        self.container_layout.setAlignment(Qt.AlignTop)
        
        self.scroll.setWidget(self.container)
        left_layout.addWidget(self.scroll)
        
        # Right: Detail
        self.detail_view = RepoDetailView(self.logic)
        
        self.splitter.addWidget(self.left_panel)
        self.splitter.addWidget(self.detail_view)
        self.splitter.setStretchFactor(0, 1)
        self.splitter.setStretchFactor(1, 3)
        self.splitter.setCollapsible(0, False)
        
        self.layout.addWidget(self.splitter)

    def set_repo_path(self, path):
        """Called by main window to focus on a specific repo."""
        # Find in list and select
        pass

    def refresh_repos(self):
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

        for repo in repos:
            item = RepoListItem(repo, self.logic)
            item.selected.connect(self.on_repo_selected)
            self.container_layout.addWidget(item)

    def on_repo_selected(self, path, name):
        self.detail_view.set_repo(path, name)

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