import subprocess
import os
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QLabel, QListWidget, QGroupBox, 
                             QMessageBox, QSplitter, QProgressBar, QStyledItemDelegate,
                             QTableWidget, QTableWidgetItem, QHeaderView)
from PySide6.QtCore import Qt, QThread, Signal, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QPainterPath
try:
    from .icons import Icons
except ImportError:
    from ui.icons import Icons
from ui.widgets.progress_utils import style_progress_bar
from ._subprocess_utils import hidden_console_kwargs

class GitWorker(QThread):
    result = Signal(str, str) # type, output
    
    def __init__(self, cmd, cwd, parent=None):
        super().__init__(parent)
        self.cmd = cmd
        self.cwd = cwd
        
    def run(self):
        try:
            # Use run to capture output
            kwargs = hidden_console_kwargs()
            res = subprocess.run(
                ['git'] + self.cmd,
                cwd=self.cwd,
                capture_output=True,
                text=True,
                check=False,
                **kwargs,
            )
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
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        self.repo_path = ""
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)

        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        # Toolbar
        toolbar = QHBoxLayout()
        
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
        
        btn_push = QPushButton("Push")
        btn_push.setIcon(Icons.get_icon(Icons.PUSH, icon_color))
        btn_push.clicked.connect(self.git_push)
        toolbar.addWidget(btn_push)
        
        layout.addLayout(toolbar)
        
        self.progress = QProgressBar()
        style_progress_bar(
            self.progress,
            accent="#2F6BFF",
            theme=self.logic.settings.get("theme", "Light"),
            min_height=12,
            max_height=16,
        )
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        self.btn_ignore = QPushButton("Create .gitignore")
        self.btn_ignore.clicked.connect(self.create_ignore)
        layout.addWidget(self.btn_ignore)

        # Main Splitter
        splitter = QSplitter(Qt.Vertical)
        layout.addWidget(splitter)

        # Status / Staging
        gb_status = QGroupBox("Changed Files (Status)")
        l_status = QVBoxLayout(gb_status)
        self.list_status = QListWidget()
        l_status.addWidget(self.list_status)
        
        h_stage = QHBoxLayout()
        btn_add = QPushButton("Stage All Changes (git add .)")
        btn_add.clicked.connect(self.git_add_all)
        h_stage.addWidget(btn_add)
        l_status.addLayout(h_stage)
        
        splitter.addWidget(gb_status)

        # Commit Area
        gb_commit = QGroupBox("Commit")
        l_commit = QVBoxLayout(gb_commit)
        self.msg_edit = QTextEdit()
        self.msg_edit.setPlaceholderText("Enter commit message...")
        self.msg_edit.setMaximumHeight(60)
        l_commit.addWidget(self.msg_edit)
        
        btn_commit = QPushButton("Commit")
        btn_commit.setStyleSheet("background-color: #27ae60; color: white; font-weight: bold;")
        btn_commit.clicked.connect(self.git_commit)
        l_commit.addWidget(btn_commit)
        splitter.addWidget(gb_commit)

        # Log Area
        gb_log = QGroupBox("Recent History (Log)")
        l_log = QVBoxLayout(gb_log)
        self.table_log = QTableWidget()
        self.table_log.setColumnCount(4)
        self.table_log.setHorizontalHeaderLabels(["Graph", "Message", "Author", "Date"])
        self.table_log.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.table_log.verticalHeader().setVisible(False)
        self.table_log.setShowGrid(False)
        self.table_log.setItemDelegateForColumn(0, GraphDelegate(self.table_log))
        l_log.addWidget(self.table_log)
        splitter.addWidget(gb_log)

    def set_repo_path(self, path):
        self.repo_path = path
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
        self.run_git_async(['status', '--porcelain'], self.handle_status)
        self.run_git_async(['log', '--all', '--date-order', '--pretty=format:%h|%p|%s|%an|%ar', '-n', '100'], self.handle_log)

    def handle_branch(self, type, output):
        if type == "success":
            self.lbl_branch.setText(f"Branch: {output.strip()}")
            self.btn_init.setVisible(False)
            self.btn_ignore.setVisible(not os.path.exists(os.path.join(self.repo_path, ".gitignore")))
        else:
            self.lbl_branch.setText("Not a Git Repo")
            self.btn_init.setVisible(True)
            self.btn_ignore.setVisible(False)

    def handle_status(self, type, output):
        self.list_status.clear()
        if type != "success": return
        if type == "success" and output.strip():
            [self.list_status.addItem(l) for l in output.split('\n') if l.strip()]
        else:
            self.list_status.addItem("No changes")

    def handle_log(self, type, output):
        self.table_log.setRowCount(0)
        if type == "success":
            lines = [l for l in output.split('\n') if l.strip()]
            self.table_log.setRowCount(len(lines))
            
            lanes = []
            for row, line in enumerate(lines):
                parts = line.split('|')
                if len(parts) < 5: continue
                
                commit_hash = parts[0]
                parents = parts[1].split() if parts[1] else []
                subject = parts[2]
                author = parts[3]
                date = parts[4]
                
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
                self.table_log.setItem(row, 1, QTableWidgetItem(subject))
                self.table_log.setItem(row, 2, QTableWidgetItem(author))
                self.table_log.setItem(row, 3, QTableWidgetItem(date))
            
            self.table_log.resizeColumnToContents(0)

    def git_init(self):
        self.run_git_async(['init'], self.on_op_finish)

    def create_ignore(self):
        if self.logic.create_gitignore(self.repo_path):
            QMessageBox.information(self, "Success", ".gitignore created.")

    def git_add_all(self): 
        self.run_git_async(['add', '.'], lambda t, o: self.refresh_status())
        
    def git_commit(self):
        if not self.msg_edit.toPlainText().strip(): return QMessageBox.warning(self, "Error", "Enter commit message.")
        self.run_git_async(['commit', '-m', self.msg_edit.toPlainText()], self.on_op_finish)
        self.msg_edit.clear()

    def git_pull(self): self.run_git_async(['pull'], self.on_op_finish)
    def git_push(self): self.run_git_async(['push'], self.on_op_finish)

    def on_op_finish(self, type, output):
        if type == "error": QMessageBox.warning(self, "Git Error", output)
        else: QMessageBox.information(self, "Git Success", output)
        self.refresh_status()

    def closeEvent(self, event):
        if hasattr(self, 'worker') and self.worker.isRunning():
            self.worker.wait()
        super().closeEvent(event)
