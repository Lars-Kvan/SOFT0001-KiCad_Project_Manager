import subprocess
import os
from datetime import datetime
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTextEdit,
    QLabel,
    QListWidget,
    QGroupBox,
    QMessageBox,
    QSplitter,
    QProgressBar,
    QStyledItemDelegate,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFrame,
    QLineEdit,
    QComboBox,
    QInputDialog,
    QFileDialog,
    QAbstractItemView,
    QSizePolicy,
    QTabWidget,
)
from PySide6.QtCore import Qt, QThread, Signal, QPointF, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons
from ui.widgets.spacing import apply_layout, PAGE_PADDING

class GitWorker(QThread):
    result = Signal(str, str) # type, output
    
    def __init__(self, cmd, cwd, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.cwd = cwd
        
    def run(self):
        try:
            # Use run to capture output
            res = subprocess.run(['git'] + self.cmd, cwd=self.cwd, capture_output=True, text=True, check=False)
            self.result.emit("success" if res.returncode == 0 else "error", res.stdout + res.stderr)
        except Exception as e:
            self.result.emit("error", str(e))

class GraphDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.colors = [
            QColor("#e74c3c"), QColor("#3498db"), QColor("#2ecc71"), 
            QColor("#f1c40f"), QColor("#9b59b6"), QColor("#1abc9c"),
            QColor("#e67e22"), QColor("#34495e")
        ]
        self.col_width = 15

    def paint(self, painter, option, index):
        if index.column() == 0:
            painter.save()
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Data: {'node_col': int, 'color_idx': int, 'edges': [(start_col, end_col, color_idx), ...]}
            data = index.data(Qt.UserRole)
            if data:
                rect = option.rect
                center_y = rect.y() + rect.height() / 2
                
                # Draw Edges
                for start_col, end_col, color_idx in data.get('edges', []):
                    color = self.colors[color_idx % len(self.colors)]
                    pen = QPen(color, 2)
                    painter.setPen(pen)
                    
                    x1 = rect.x() + start_col * self.col_width + self.col_width / 2
                    y1 = rect.y()
                    x2 = rect.x() + end_col * self.col_width + self.col_width / 2
                    y2 = rect.y() + rect.height()
                    
                    # If connecting to current node, go to center
                    if start_col == data['node_col'] and end_col == data['node_col']:
                        # Pass through
                        painter.drawLine(x1, y1, x2, y2)
                    else:
                        # Complex routing (bezier or straight lines)
                        # Simplified: Draw straight lines for now
                        # To make it look like a graph, we draw from Top to Center, Center to Bottom
                        
                        # We need to know if this edge is incoming (to node) or outgoing (from node) or passthrough
                        # The logic passed from handle_log simplifies this:
                        # edges are simply lines from Top(start_col) to Bottom(end_col)
                        # But we want them to converge at the node if applicable.
                        
                        # Improved rendering logic based on 'type' in edge could be better, 
                        # but let's try direct lines first.
                        
                        # If this is a merge/branch, we might want to curve.
                        path = QPainterPath()
                        path.moveTo(x1, y1)
                        path.cubicTo(x1, y1 + rect.height(), x2, y2 - rect.height(), x2, y2)
                        painter.drawPath(path)

                # Draw Node
                node_col = data.get('node_col')
                if node_col is not None:
                    color = self.colors[data['color_idx'] % len(self.colors)]
                    painter.setBrush(QBrush(color))
                    painter.setPen(Qt.NoPen)
                    
                    cx = rect.x() + node_col * self.col_width + self.col_width / 2
                    r = 4
                    painter.drawEllipse(QPointF(cx, center_y), r, r)

            painter.restore()
        else:
            super().paint(painter, option, index)

class GitTab(QWidget):
    git_status_updated = Signal(dict)

    def __init__(self, logic, compact=False):
        super().__init__()
        self.logic = logic
        self.compact = compact
        self.repo_path = ""
        self.branch_ahead = 0
        self.branch_behind = 0
        self.git_summary = {
            "items": [],
            "branch": "Not a Git Repo",
            "ahead": 0,
            "behind": 0,
            "clean": True,
        }
        self.list_status = QListWidget()
        self.log_rows = []
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        apply_layout(layout, margin=PAGE_PADDING, spacing="md")

        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"
        is_dark = theme in ["Dark"]
        card_border = "#2F353D" if is_dark else "#EDE6DC"
        muted = "#9CA3AF" if is_dark else "#6B7280"

        # Toolbar
        toolbar = QHBoxLayout()
        self.lbl_repo = QLabel("Repo: -")
        self.lbl_repo.setStyleSheet(f"color: {muted};")
        toolbar.addWidget(self.lbl_repo)
        
        self.btn_init = QPushButton("Initialize Repo")
        self.btn_init.clicked.connect(self.git_init)
        self.btn_init.setVisible(False)
        toolbar.addWidget(self.btn_init)
        
        self.lbl_branch = QLabel("Branch: -")
        self.lbl_branch.setStyleSheet("font-weight: bold; font-size: 12px;")
        toolbar.addWidget(self.lbl_branch)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        btn_refresh.clicked.connect(self.refresh_status)
        toolbar.addWidget(btn_refresh)
        
        btn_pull = QPushButton("Pull")
        btn_pull.setIcon(Icons.get_icon(Icons.PULL, icon_color))
        btn_pull.clicked.connect(self.git_pull)
        toolbar.addWidget(btn_pull)

        self.btn_ignore = QPushButton("Create .gitignore")
        self.btn_ignore.clicked.connect(self.create_ignore)
        toolbar.addWidget(self.btn_ignore)

        toolbar.addStretch()
        
        btn_push = QPushButton("Push")
        btn_push.setIcon(Icons.get_icon(Icons.PUSH, icon_color))
        btn_push.setObjectName("btnPrimary")
        btn_push.clicked.connect(self.git_push)
        toolbar.addWidget(btn_push)
        layout.addLayout(toolbar)
        
        self.progress = QProgressBar()
        self.progress.setVisible(False)
        layout.addWidget(self.progress)

        # Main Splitter
        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter)

        # LEFT COLUMN
        left_col = QWidget()
        left_layout = QVBoxLayout(left_col)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)

        gb_status = QGroupBox("Changed Files")
        gb_status.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {card_border}; border-radius: 10px; margin-top: 0.6em; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {muted}; font-weight: 600; }}"
        )
        l_status = QVBoxLayout(gb_status)
        self.list_status.setStyleSheet("border: none; background: transparent;")
        l_status.addWidget(self.list_status)
        
        h_stage = QHBoxLayout()
        btn_add = QPushButton("Stage All Changes (git add .)")
        btn_add.clicked.connect(self.git_add_all)
        h_stage.addWidget(btn_add)
        btn_unstage = QPushButton("Unstage All")
        btn_unstage.clicked.connect(self.git_unstage_all)
        h_stage.addWidget(btn_unstage)
        l_status.addLayout(h_stage)
        left_layout.addWidget(gb_status)

        # Commit Area
        gb_commit = QGroupBox("Commit")
        gb_commit.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {card_border}; border-radius: 10px; margin-top: 0.6em; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {muted}; font-weight: 600; }}"
        )
        l_commit = QVBoxLayout(gb_commit)
        self.msg_edit = QTextEdit()
        self.msg_edit.setPlaceholderText("Enter commit message...")
        self.msg_edit.setMaximumHeight(60)
        l_commit.addWidget(self.msg_edit)
        
        btn_commit = QPushButton("Commit")
        btn_commit.setStyleSheet("background-color: #27ae60; color: white; font-weight: 600; padding: 6px 12px; border-radius: 8px;")
        btn_commit.clicked.connect(self.git_commit)

        btn_commit_signoff = QPushButton("Commit + Signoff")
        btn_commit_signoff.setStyleSheet("background-color: #0ea5e9; color: white; font-weight: 600; padding: 6px 12px; border-radius: 8px;")
        btn_commit_signoff.setToolTip("Runs: git commit -s -m <message>\nAdds a 'Signed-off-by' line using your Git user.name/email.")
        btn_commit_signoff.clicked.connect(self.git_commit_signoff)

        h_commit_btns = QHBoxLayout()
        h_commit_btns.setSpacing(8)
        h_commit_btns.addWidget(btn_commit)
        h_commit_btns.addWidget(btn_commit_signoff)

        l_commit.addLayout(h_commit_btns)
        left_layout.addWidget(gb_commit)
        splitter.addWidget(left_col)

        # Log Area
        gb_log = QGroupBox("Recent History (Log)")
        gb_log.setStyleSheet(
            f"QGroupBox {{ border: 1px solid {card_border}; border-radius: 10px; margin-top: 0.6em; }}"
            f"QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {muted}; font-weight: 600; }}"
        )
        l_log = QVBoxLayout(gb_log)
        self.table_log = QTableWidget()
        self.table_log.setColumnCount(5)
        self.table_log.setHorizontalHeaderLabels(["Graph", "Message", "Author", "When", "Hash"])
        self.table_log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_log.horizontalHeader().setDefaultSectionSize(120)
        self.table_log.verticalHeader().setVisible(False)
        self.table_log.setShowGrid(False)
        self.table_log.setAlternatingRowColors(True)
        self.table_log.setSelectionBehavior(QTableWidget.SelectRows)
        self.table_log.setSelectionMode(QTableWidget.SingleSelection)
        self.table_log.setItemDelegateForColumn(0, GraphDelegate(self.table_log))
        self.table_log.setStyleSheet(
            """
            QTableWidget { background: #0f1624; alternate-background-color: #0b1220; color: #e5e7eb; }
            QHeaderView::section { background: #111827; color: #cbd5e1; padding: 6px 8px; border: none; }
            QTableWidget::item { padding: 6px; }
            QTableWidget::item:selected { background: #1d283a; color: #f8fafc; }
            """
        )
        self.table_log.itemSelectionChanged.connect(self._update_log_detail)
        l_log.addWidget(self.table_log)

        # Commit detail footer
        detail = QFrame()
        detail.setObjectName("commitDetail")
        detail.setStyleSheet(
            "QFrame#commitDetail { border: 1px solid #1f2937; border-radius: 10px; padding: 8px; background: #0b1220; }"
        )
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(8, 6, 8, 6)
        detail_layout.setSpacing(4)
        self.lbl_commit_subject = QLabel("Select a commit to see details")
        self.lbl_commit_subject.setStyleSheet("color: #e5e7eb; font-weight: 700;")
        self.lbl_commit_meta = QLabel("")
        self.lbl_commit_meta.setStyleSheet("color: #9ca3af; font-family: 'JetBrains Mono', 'Consolas', monospace;")
        detail_layout.addWidget(self.lbl_commit_subject)
        detail_layout.addWidget(self.lbl_commit_meta)
        l_log.addWidget(detail)
        splitter.addWidget(gb_log)

    def set_repo_path(self, path):
        self.repo_path = path
        self.lbl_repo.setText(f"Repo: {path or '-'}")
        self.refresh_status()

    def run_git_async(self, args, callback=None):
        if not self.repo_path or not os.path.exists(self.repo_path): return None
        
        self.progress.setVisible(True)
        self.progress.setRange(0, 0)
        
        self.worker = GitWorker(args, self.repo_path, self)
        if callback:
            self.worker.result.connect(callback)
        self.worker.result.connect(lambda t, o: self.progress.setVisible(False))
        self.worker.start()

    def refresh_status(self):
        if not self.repo_path:
            self.lbl_branch.setText("No Project Selected"); return

        self.run_git_async(['branch', '--show-current'], self.handle_branch)
        self.run_git_async(['status', '--porcelain=2', '--branch'], self.handle_status)
        self.run_git_async(['log', '--all', '--date-order', '--pretty=format:%h|%p|%s|%an|%ar', '-n', '100'], self.handle_log)

    def handle_branch(self, type, output):
        if type == "success":
            branch = output.strip()
            self.lbl_branch.setText(f"Branch: {branch}")
            self.btn_init.setVisible(False)
            self.btn_ignore.setVisible(not os.path.exists(os.path.join(self.repo_path, ".gitignore")))
            self.git_summary["branch"] = branch or "Detached"
        else:
            self.lbl_branch.setText("Not a Git Repo")
            self.btn_init.setVisible(True)
            self.btn_ignore.setVisible(False)
            self.git_summary["branch"] = "Not a Git Repo"
        self._emit_git_summary()

    def handle_status(self, type, output):
        self.list_status.clear()
        status_items = []
        self.branch_ahead = 0
        self.branch_behind = 0
        if type != "success":
            self.git_summary.update({
                "items": [],
                "clean": True,
                "ahead": self.branch_ahead,
                "behind": self.branch_behind,
            })
            self._emit_git_summary()
            return

        branch_ab_line = ""
        for line in output.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            if stripped.startswith("#"):
                if stripped.startswith("# branch.ab"):
                    branch_ab_line = stripped
                    parts = stripped.split()
                    for part in parts:
                        if part.startswith("+"):
                            try:
                                self.branch_ahead = int(part.lstrip("+"))
                            except ValueError:
                                self.branch_ahead = 0
                        elif part.startswith("-"):
                            try:
                                self.branch_behind = int(part.lstrip("-"))
                            except ValueError:
                                self.branch_behind = 0
                continue
            status_items.append(stripped)
            self.list_status.addItem(stripped)

        if not status_items:
            self.list_status.addItem("No changes")

        self.git_summary.update({
            "items": status_items,
            "clean": len(status_items) == 0,
            "ahead": self.branch_ahead,
            "behind": self.branch_behind,
        })
        self._emit_git_summary()

    def _emit_git_summary(self):
        self.git_status_updated.emit(dict(self.git_summary))

    def get_git_summary(self):
        return dict(self.git_summary)

    def handle_log(self, type, output):
        self.table_log.setRowCount(0)
        self.log_rows = []
        if type == "success":
            lines = [l for l in output.split('\n') if l.strip()]
            self.table_log.setRowCount(len(lines))
            self.table_log.setSortingEnabled(False)
            
            lanes = []
            for row, line in enumerate(lines):
                parts = line.split('|')
                if len(parts) < 5: continue
                
                commit_hash = parts[0]
                parents = parts[1].split() if parts[1] else []
                subject = parts[2]
                author = parts[3]
                date = parts[4]
                self.log_rows.append({
                    "hash": commit_hash,
                    "parents": parents,
                    "subject": subject,
                    "author": author,
                    "date": date,
                })
                
                if commit_hash in lanes:
                    node_col = lanes.index(commit_hash)
                else:
                    node_col = len(lanes)
                    lanes.append(commit_hash)
                
                graph_data = {
                    'node_col': node_col,
                    'color_idx': node_col,
                    'edges': [] 
                }
                
                next_lanes = list(lanes)
                
                # Pass-throughs
                for i, h in enumerate(lanes):
                    if h is not None and i != node_col:
                        graph_data['edges'].append((i, i, i))
                
                # Edges to parents
                if parents:
                    graph_data['edges'].append((node_col, node_col, node_col))
                    # Update lanes for next row
                    next_lanes[node_col] = parents[0]
                    for p in parents[1:]:
                        if p not in next_lanes:
                            next_lanes.append(p)
                            # Draw edge to new lane
                            target = len(next_lanes) - 1
                            graph_data['edges'].append((node_col, target, target))
                        else:
                            target = next_lanes.index(p)
                            graph_data['edges'].append((node_col, target, target))
                else:
                    next_lanes[node_col] = None
                
                lanes = next_lanes

                item_graph = QTableWidgetItem()
                item_graph.setData(Qt.UserRole, graph_data)
                self.table_log.setItem(row, 0, item_graph)
                
                msg_item = QTableWidgetItem(subject)
                msg_item.setToolTip(f"{subject}\n{commit_hash}")
                self.table_log.setItem(row, 1, msg_item)

                author_item = QTableWidgetItem(author)
                author_item.setToolTip(author)
                self.table_log.setItem(row, 2, author_item)

                date_item = QTableWidgetItem(date)
                date_item.setToolTip(date)
                self.table_log.setItem(row, 3, date_item)

                hash_item = QTableWidgetItem(commit_hash)
                hash_item.setFont(author_item.font())
                hash_item.setToolTip(commit_hash)
                self.table_log.setItem(row, 4, hash_item)
                self.table_log.setRowHeight(row, 42)
            
            self.table_log.resizeColumnToContents(0)
            self.table_log.setSortingEnabled(True)

    def _update_log_detail(self):
        row = self.table_log.currentRow()
        if row < 0 or row >= len(self.log_rows):
            self.lbl_commit_subject.setText("Select a commit to see details")
            self.lbl_commit_meta.setText("")
            return
        data = self.log_rows[row]
        self.lbl_commit_subject.setText(data.get("subject", "-"))
        parents = data.get("parents", [])
        parents_str = " ".join(parents) if parents else "-"
        meta = (
            f"hash {data.get('hash','-')}   |   parents {parents_str}\n"
            f"author {data.get('author','-')}   |   {data.get('date','-')}"
        )
        self.lbl_commit_meta.setText(meta)

    def git_init(self):
        self.run_git_async(['init'], self.on_op_finish)

    def create_ignore(self):
        if self.logic.create_gitignore(self.repo_path):
            QMessageBox.information(self, "Success", ".gitignore created.")

    def git_add_all(self): 
        self.run_git_async(['add', '.'], lambda t, o: self.refresh_status())

    def git_unstage_all(self):
        self.run_git_async(['reset'], lambda t, o: self.refresh_status())
        
    def git_commit(self):
        if not self.msg_edit.toPlainText().strip(): return QMessageBox.warning(self, "Error", "Enter commit message.")
        if not self.repo_path or not os.path.isdir(self.repo_path):
            return QMessageBox.warning(self, "Error", "No repository selected.")
        self._stage_all_quiet()
        self.run_git_async(['commit', '-m', self.msg_edit.toPlainText()], self.on_op_finish)
        self.msg_edit.clear()

    def git_commit_signoff(self):
        """Commit with a signed-off-by trailer (git commit -s)."""
        if not self.msg_edit.toPlainText().strip(): return QMessageBox.warning(self, "Error", "Enter commit message.")
        if not self.repo_path or not os.path.isdir(self.repo_path):
            return QMessageBox.warning(self, "Error", "No repository selected.")
        self._stage_all_quiet()
        self.run_git_async(['commit', '-s', '-m', self.msg_edit.toPlainText()], self.on_op_finish)
        self.msg_edit.clear()

    def git_pull(self): self.run_git_async(['pull'], self.on_op_finish)
    def git_push(self): self.run_git_async(['push'], self.on_op_finish)

    def on_op_finish(self, type, output):
        if type == "error": QMessageBox.warning(self, "Git Error", output)
        self.refresh_status()

    def _stage_all_quiet(self):
        """Stage all changes before committing; ignore errors but keep commit robust."""
        try:
            subprocess.run(['git', 'add', '-A'], cwd=self.repo_path, capture_output=True, text=True, check=False)
        except Exception:
            pass

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)


class GitOverviewList(QWidget):
    def __init__(self, logic, repo_filter=None, allow_manual=True):
        super().__init__()
        self.logic = logic
        self.repo_filter = repo_filter or (lambda repo: True)
        self.allow_manual = allow_manual
        self.selected_repo = None
        self.selected_row = -1
        self.current_repos = []
        self.repo_status_map = {}
        self.stat_labels = {}
        self.git_tab = GitTab(logic, compact=True)
        self.git_tab.git_status_updated.connect(self._on_detail_status_update)
        self._build_ui()
        self.refresh_repos()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        self.root_layout = layout
        apply_layout(layout, margin=PAGE_PADDING, spacing="md")
        header_ext = self._build_header_extension()
        if header_ext:
            layout.addWidget(header_ext)

        # Summary chips
        stats_frame = QFrame()
        stats_frame.setObjectName("gitStatsBar")
        stats_frame.setStyleSheet(
            """
            QFrame#gitStatsBar {
                border: 1px solid #2F353D;
                border-radius: 10px;
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                            stop:0 #111827, stop:1 #0B1220);
                padding: 6px;
            }
            QLabel#statLabel { color: #9CA3AF; font-size: 10px; letter-spacing: 0.08em; }
            QLabel#statValue { color: #E5E7EB; font-weight: 700; font-size: 16px; }
            """
        )
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setContentsMargins(6, 4, 6, 4)
        stats_layout.setSpacing(10)

        def add_stat(name, title, color):
            card = QFrame()
            card.setStyleSheet(
                f"QFrame {{ background: {color}; border-radius: 8px; padding: 6px 10px; }}"
            )
            v = QVBoxLayout(card)
            v.setContentsMargins(6, 4, 6, 4)
            v.setSpacing(0)
            lbl_title = QLabel(title)
            lbl_title.setObjectName("statLabel")
            lbl_value = QLabel("0")
            lbl_value.setObjectName("statValue")
            v.addWidget(lbl_title)
            v.addWidget(lbl_value)
            stats_layout.addWidget(card)
            self.stat_labels[name] = lbl_value

        add_stat("total", "Repos", "#1F2937")
        add_stat("project", "Projects", "#0B7A75")
        add_stat("library", "Libraries", "#6B21A8")
        add_stat("manual", "Manual", "#78350F")
        add_stat("clean", "Clean", "#065F46")
        add_stat("dirty", "Dirty", "#7F1D1D")
        add_stat("ahead", "Ahead", "#1E3A8A")
        add_stat("behind", "Behind", "#B45309")

        layout.addWidget(stats_frame)

        control_row = QHBoxLayout()
        control_row.setSpacing(8)
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Filter repositories...")
        self.filter_input.textChanged.connect(self.refresh_repos)
        control_row.addWidget(self.filter_input, 1)

        self.type_combo = QComboBox()
        self.type_combo.addItem("All Types", "")
        for repo_type in ("project", "symbol", "footprint", "manual"):
            self.type_combo.addItem(repo_type.title(), repo_type)
        self.type_combo.currentIndexChanged.connect(self.refresh_repos)
        control_row.addWidget(self.type_combo)

        btn_refresh = QPushButton("Refresh List")
        btn_refresh.clicked.connect(self.refresh_repos)
        control_row.addWidget(btn_refresh)

        self.btn_add = None
        self.btn_remove = None
        if self.allow_manual:
            self.btn_add = QPushButton("Add Repository")
            self.btn_add.clicked.connect(self._prompt_add_repo)
            control_row.addWidget(self.btn_add)
            self.btn_remove = QPushButton("Remove Selected")
            self.btn_remove.clicked.connect(self._remove_selected_repo)
            self.btn_remove.setEnabled(False)
            control_row.addWidget(self.btn_remove)

        layout.addLayout(control_row)

        splitter = QSplitter(Qt.Horizontal)
        splitter.setChildrenCollapsible(False)
        layout.addWidget(splitter, 1)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(6)

        self.table_repos = QTableWidget(0, 6)
        self.table_repos.setHorizontalHeaderLabels(
            ["Name", "Type", "Path", "Source", "Branch", "Status"]
        )
        header = self.table_repos.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultSectionSize(140)
        for col in range(6):
            if col == 2:  # Path column
                header.setSectionResizeMode(col, QHeaderView.Stretch)
            elif col == 0:
                header.setSectionResizeMode(col, QHeaderView.ResizeToContents)
            else:
                header.setSectionResizeMode(col, QHeaderView.Interactive)
        self.table_repos.verticalHeader().setVisible(False)
        self.table_repos.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_repos.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_repos.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table_repos.setSortingEnabled(True)
        self.table_repos.itemSelectionChanged.connect(self._on_repo_selection_changed)
        self.table_repos.setAlternatingRowColors(True)
        self.table_repos.setStyleSheet(
            """
            QTableWidget { background: #0f1624; alternate-background-color: #0b1220; color: #e5e7eb; gridline-color: #1f2937; }
            QHeaderView::section { background: #111827; color: #cbd5e1; padding: 6px 8px; border: none; }
            QTableWidget::item { padding: 6px; }
            """
        )
        left_layout.addWidget(self.table_repos)
        splitter.addWidget(left_panel)
        left_panel.setMinimumWidth(340)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(8)

        self.repo_header = QLabel("Select a repository to inspect")
        self.repo_header.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(self.repo_header)

        self.repo_path_label = QLabel("")
        self.repo_path_label.setStyleSheet("color: #9CA3AF; font-size: 11px;")
        right_layout.addWidget(self.repo_path_label)

        self.git_tab.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        right_layout.addWidget(self.git_tab, 1)

        self.note_group = QGroupBox("Library Version Note")
        note_layout = QVBoxLayout(self.note_group)
        note_layout.setContentsMargins(8, 8, 8, 8)
        note_layout.setSpacing(6)
        self.library_note_editor = QTextEdit()
        self.library_note_editor.setPlaceholderText("Record library version details or commits used in this push.")
        self.library_note_editor.setFixedHeight(120)
        note_layout.addWidget(self.library_note_editor)

        footer_layout = QHBoxLayout()
        footer_layout.setContentsMargins(0, 0, 0, 0)
        self.note_footer = QLabel("No saved library note.")
        footer_layout.addWidget(self.note_footer)
        footer_layout.addStretch()
        self.btn_save_note = QPushButton("Save Note")
        self.btn_save_note.clicked.connect(self._save_library_note)
        footer_layout.addWidget(self.btn_save_note)
        note_layout.addLayout(footer_layout)

        self.note_group.setVisible(False)
        right_layout.addWidget(self.note_group)

        splitter.addWidget(right_panel)
        splitter.setStretchFactor(1, 1)

    def _build_header_extension(self):
        return None

    def refresh_repos(self):
        filter_text = (self.filter_input.text() or "").strip().lower()
        filter_type = self.type_combo.currentData()
        repos = [
            repo for repo in self.logic.get_git_repositories()
            if self.repo_filter(repo)
        ]

        was_sorting = self.table_repos.isSortingEnabled()
        if was_sorting:
            self.table_repos.setSortingEnabled(False)
        prev_path = self.selected_repo.get("path") if self.selected_repo else None
        self.table_repos.blockSignals(True)
        self.table_repos.setRowCount(0)
        displayed = []
        for repo in repos:
            if filter_type and repo.get("type") != filter_type:
                continue
            haystack = f"{repo.get('name', '')} {repo.get('path', '')}".lower()
            if filter_text and filter_text not in haystack:
                continue
            row = self.table_repos.rowCount()
            self.table_repos.insertRow(row)
            values = [
                repo.get("name") or "-",
                repo.get("type") or "-",
                repo.get("path") or "Not set",
                repo.get("source") or "-",
                str(repo.get("branch") or "-"),
                ("Path missing" if repo.get("missing_path") else ("Clean" if repo.get("clean", True) else "Dirty")),
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setData(Qt.UserRole, repo)
                if col == 5:
                    if value.lower().startswith("path"):
                        fg = QColor("#e74c3c")
                    else:
                        fg = QColor("#27ae60") if value.lower() == "clean" else QColor("#e74c3c")
                    item.setForeground(fg)
                self.table_repos.setItem(row, col, item)
            self.table_repos.setRowHeight(row, 34)
            displayed.append(repo)
        self.table_repos.blockSignals(False)
        self.current_repos = displayed
        self.table_repos.resizeColumnsToContents()
        self.table_repos.horizontalHeader().setStretchLastSection(True)
        if was_sorting:
            self.table_repos.setSortingEnabled(True)
            self.table_repos.sortItems(0)

        if prev_path:
            self._select_repo_by_path(prev_path)
        else:
            self.table_repos.clearSelection()
            self._clear_repo_detail()
        self._update_remove_button_state()
        self._update_stats()

    def set_repo_path(self, path):
        """
        Public hook so other views (e.g., project list) can drive the overview.
        Tries to refresh and select the matching repo by path.
        """
        if not path:
            return
        # Ensure latest repo list before selection
        self.refresh_repos()
        self._select_repo_by_path(path)

    def _select_repo_by_path(self, path):
        if not path:
            return
        for row in range(self.table_repos.rowCount()):
            item = self.table_repos.item(row, 0)
            repo = item.data(Qt.UserRole) if item else None
            if repo and repo.get("path") == path:
                self.table_repos.selectRow(row)
                self.table_repos.scrollToItem(item)
                return
        self.table_repos.clearSelection()
        self._clear_repo_detail()

    def _on_repo_selection_changed(self):
        row = self.table_repos.currentRow()
        if row < 0:
            self.selected_repo = None
            self.selected_row = -1
            self._clear_repo_detail()
            self._update_remove_button_state()
            return
        item = self.table_repos.item(row, 0)
        repo = item.data(Qt.UserRole) if item else None
        if not repo:
            return
        self.selected_repo = repo
        self.selected_row = row
        self._display_repo_detail(repo)
        self._update_remove_button_state()

    def _display_repo_detail(self, repo):
        repo_name = repo.get("name") or "Repository"
        repo_type = repo.get("type", "unknown").title()
        self.repo_header.setText(f"{repo_name} · {repo_type}")
        path = repo.get("path", "")
        source = repo.get("source", "").title() or "Manual"
        if repo.get("missing_path"):
            self.repo_path_label.setText("Not set — configure in Projects")
            self.git_tab.set_repo_path("")
        else:
            self.repo_path_label.setText(path)
            self.git_tab.set_repo_path(path)
        self._update_note_area(repo)

    def _clear_repo_detail(self):
        self.repo_header.setText("Select a repository to inspect")
        self.repo_path_label.setText("")
        self.git_tab.set_repo_path("")
        self.note_group.setVisible(False)

    def _update_note_area(self, repo):
        repo_type = repo.get("type")
        if repo_type in ("symbol", "footprint"):
            note_data = self.logic.get_library_git_note_for_path(repo.get("path", ""))
            self.library_note_editor.blockSignals(True)
            self.library_note_editor.setPlainText(note_data.get("note", "") if note_data else "")
            self.library_note_editor.blockSignals(False)
            timestamp = note_data.get("updated") if note_data else None
            self.note_footer.setText(f"Last saved: {timestamp}" if timestamp else "No saved library note.")
            self.note_group.setTitle(f"Library Version Note · {repo.get('name', 'Library')}")
            self.note_group.setVisible(True)
        else:
            self.note_group.setVisible(False)

    def _save_library_note(self):
        if not (self.selected_repo and self.selected_repo.get("type") in ("symbol", "footprint")):
            return
        note_text = self.library_note_editor.toPlainText().strip()
        saved = self.logic.set_library_git_note_for_path(self.selected_repo["path"], note_text)
        if saved:
            QMessageBox.information(self, "Library Note", "Library note saved.")
            self._update_note_area(self.selected_repo)
        else:
            QMessageBox.warning(self, "Library Note", "Failed to save the library note.")

    def _on_detail_status_update(self, summary):
        if summary is None or self.selected_row < 0:
            return
        branch_item = self.table_repos.item(self.selected_row, 4)
        status_item = self.table_repos.item(self.selected_row, 5)
        if branch_item:
            branch_item.setText(summary.get("branch") or "-")
        if status_item:
            clean = summary.get("clean", True)
            items = summary.get("items", [])
            if clean:
                status_text = "Clean"
            else:
                status_text = f"{len(items)} change{'s' if len(items) != 1 else ''}"
            status_item.setText(status_text)
            color = QColor("#27ae60") if clean else QColor("#e74c3c")
            status_item.setForeground(color)
        # Cache status for summary stats
        path = self.selected_repo.get("path") if self.selected_repo else None
        if path:
            self.repo_status_map[path] = summary
            self._update_stats()

    def _prompt_add_repo(self):
        start = self.logic.get_path_root() or os.getcwd()
        path = QFileDialog.getExistingDirectory(self, "Select Git Repository", start)
        if not path:
            return
        default_name = os.path.basename(path) or path
        name, ok = QInputDialog.getText(self, "Repository Name", "Repository name (for display):", text=default_name)
        if not ok:
            return
        if not self.logic.add_manual_git_repo(name.strip(), path):
            QMessageBox.warning(self, "Add Repository", "Failed to add repository. Verify the path and try again.")
            return
        QMessageBox.information(self, "Add Repository", "Repository added to the overview.")
        self.refresh_repos()

    def _remove_selected_repo(self):
        if not (self.selected_repo and self.selected_repo.get("type") == "manual"):
            return
        path = self.selected_repo.get("path")
        if self.logic.remove_manual_git_repo(path):
            QMessageBox.information(self, "Remove Repository", "Repository removed.")
            self.refresh_repos()
        else:
            QMessageBox.warning(self, "Remove Repository", "Failed to remove the repository.")

    def _update_remove_button_state(self):
        if not self.allow_manual or not hasattr(self, 'btn_remove') or self.btn_remove is None:
            return
        self.btn_remove.setEnabled(bool(self.selected_repo and self.selected_repo.get("type") == "manual"))

    def _update_stats(self):
        total = len(self.current_repos)
        projects = sum(1 for r in self.current_repos if r.get("type") == "project")
        libs = sum(1 for r in self.current_repos if r.get("type") in ("symbol", "footprint"))
        manual = sum(1 for r in self.current_repos if r.get("type") == "manual")
        clean = dirty = ahead = behind = 0
        for repo in self.current_repos:
            path = repo.get("path", "")
            summary = self.repo_status_map.get(path)
            if summary:
                if summary.get("clean", True):
                    clean += 1
                else:
                    dirty += 1
                ahead += summary.get("ahead", 0) or 0
                behind += summary.get("behind", 0) or 0
        self._set_stat("total", total)
        self._set_stat("project", projects)
        self._set_stat("library", libs)
        self._set_stat("manual", manual)
        self._set_stat("clean", clean)
        self._set_stat("dirty", dirty)
        self._set_stat("ahead", ahead)
        self._set_stat("behind", behind)

    def _set_stat(self, name, value):
        lbl = self.stat_labels.get(name)
        if lbl:
            lbl.setText(str(value))


class LibraryGitTab(GitOverviewList):
    def __init__(self, logic):
        super().__init__(
            logic,
            repo_filter=lambda repo: repo.get("type") in ("symbol", "footprint"),
            allow_manual=False,
        )
        self.filter_input.setPlaceholderText("Filter symbol or footprint repos...")
        if hasattr(self, "type_combo"):
            self.type_combo.setVisible(False)

    def _build_header_extension(self):
        panel = QFrame()
        panel.setStyleSheet(
            "QFrame { background: #0f1624; border: 1px solid #1f2937; border-radius: 10px; padding: 10px; }"
        )
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(6)

        def build_row(title, kind):
            row = QHBoxLayout()
            row.setContentsMargins(0, 0, 0, 0)
            row.setSpacing(6)
            label = QLabel(title)
            label.setStyleSheet("color: #cbd5e1; font-weight: 600;")
            edit = QLineEdit()
            edit.setPlaceholderText("Set git root...")
            browse = QPushButton("Browse")
            browse.setIcon(Icons.get_icon(Icons.FOLDER, "#9CA3AF"))
            save_btn = QPushButton("Save")
            save_btn.setIcon(Icons.get_icon(Icons.SAVE, "#10B981"))

            def load_current():
                roots = self.logic.get_library_git_roots()
                path = roots.get(kind, "")
                edit.setText(path or "")

            def browse_clicked():
                start = self.logic.resolve_path(edit.text()) or self.logic.get_path_root() or os.getcwd()
                d = QFileDialog.getExistingDirectory(self, f"Select {title} Git Root", start)
                if d:
                    edit.setText(d)

            def save_clicked():
                path = edit.text().strip()
                if not path:
                    QMessageBox.warning(self, "Save Git Path", f"Please select a {title.lower()} path.")
                    return
                if self.logic.set_library_git_root(kind, path):
                    QMessageBox.information(self, "Saved", f"{title} git root saved.")
                    self.refresh_repos()
                else:
                    QMessageBox.warning(self, "Save Git Path", "Failed to save path. Verify and try again.")

            browse.clicked.connect(browse_clicked)
            save_btn.clicked.connect(save_clicked)
            load_current()

            row.addWidget(label, 0)
            row.addWidget(edit, 1)
            row.addWidget(browse, 0)
            row.addWidget(save_btn, 0)
            return row

        layout.addLayout(build_row("Symbols", "symbol"))
        layout.addLayout(build_row("Footprints", "footprint"))
        return panel


class GitOverviewTab(QWidget):
    """
    Container offering All / Projects / Libraries / Manual views while keeping the original class name.
    """
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        layout = QVBoxLayout(self)
        apply_layout(layout, margin=PAGE_PADDING, spacing="md")

        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setIconSize(QSize(18, 18))

        self.views = {
            "all": GitOverviewList(logic),
            "project": GitOverviewList(logic, repo_filter=lambda r: r.get("type") == "project", allow_manual=False),
            "library": GitOverviewList(logic, repo_filter=lambda r: r.get("type") in ("symbol", "footprint"), allow_manual=False),
            "manual": GitOverviewList(logic, repo_filter=lambda r: r.get("type") == "manual" or r.get("missing_path"), allow_manual=True),
        }

        self.tabs.addTab(self.views["all"], Icons.get_icon(Icons.GIT, "#9CA3AF"), "All")
        self.tabs.addTab(self.views["project"], Icons.get_icon(Icons.PROJECTS_MAIN, "#9CA3AF"), "Projects")
        self.tabs.addTab(self.views["library"], Icons.get_icon(Icons.LIBRARY, "#9CA3AF"), "Libraries")
        self.tabs.addTab(self.views["manual"], Icons.get_icon(Icons.FOLDER, "#9CA3AF"), "Manual/Unset")

        layout.addWidget(self.tabs)

    def set_repo_path(self, path):
        view = self.views.get("all")
        if view:
            view.set_repo_path(path)
