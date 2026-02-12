import os
import shutil
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTreeView, QListView,
                             QPushButton, QLabel, QFileSystemModel, QHeaderView,
                             QSplitter, QTextEdit, QMenu, QMessageBox, QInputDialog,
                             QLineEdit, QFrame, QScrollArea, QFileDialog, QComboBox, QToolButton, QAbstractItemView)
from PySide6.QtCore import QUrl, Qt, QSortFilterProxyModel, QFileInfo, QSize, QDir, QPoint
from PySide6.QtGui import QDesktopServices, QPixmap, QAction, QDragEnterEvent, QDropEvent, QIcon
try:
    from .resources.icons import Icons
except ImportError:
    from ui.resources.icons import Icons
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.toast import show_toast

class FileTree(QTreeView):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDragDropMode(QTreeView.DragDrop)
        self.setDefaultDropAction(Qt.CopyAction) # Default to copy for external files
        self.setSelectionMode(QAbstractItemView.ExtendedSelection)

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent):
        if event.mimeData().hasUrls():
            # Handle external file drop
            target_index = self.indexAt(event.position().toPoint())
            if not target_index.isValid():
                # Drop on viewport (root)
                target_path = self.model().rootPath() if hasattr(self.model(), 'rootPath') else ""
                # If proxy
                if isinstance(self.model(), QSortFilterProxyModel):
                    target_path = self.model().sourceModel().rootPath()
            else:
                # Drop on item
                model = self.model()
                if isinstance(model, QSortFilterProxyModel):
                    source_index = model.mapToSource(target_index)
                    fs_model = model.sourceModel()
                    target_path = fs_model.filePath(source_index)
                else:
                    target_path = model.filePath(target_index)
                
                if os.path.isfile(target_path):
                    target_path = os.path.dirname(target_path)

            for url in event.mimeData().urls():
                src_path = url.toLocalFile()
                if os.path.exists(src_path):
                    fname = os.path.basename(src_path)
                    dest_path = os.path.join(target_path, fname)
                    try:
                        if os.path.isdir(src_path):
                            shutil.copytree(src_path, dest_path)
                        else:
                            shutil.copy2(src_path, dest_path)
                    except Exception as e:
                        print(f"Error copying {src_path}: {e}")
            
            event.acceptProposedAction()
        else:
            super().dropEvent(event)

class DocumentManagerTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.logic = logic
        # Default to a 'documents' folder in the app directory
        self.root_path = os.path.join(os.getcwd(), "documents")
        if not os.path.exists(self.root_path):
            os.makedirs(self.root_path)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        apply_layout(layout, margin=PAGE_PADDING, spacing="sm")
        
        # Determine icon color
        theme = self.logic.settings.get("theme", "Light")
        icon_color = "#E0E0E0" if theme in ["Dark"] else "#555555"

        top_bar = QHBoxLayout()
        title = QLabel("Documents")
        title.setStyleSheet("font-weight: 700; font-size: 14px;")
        self.location_label = QLabel(f"Location: {self.root_path}")
        self.location_label.setStyleSheet("color: #6B7280;")
        top_bar.addWidget(title)
        top_bar.addWidget(self.location_label)
        top_bar.addStretch()

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setIcon(Icons.get_icon(Icons.RELOAD, icon_color))
        btn_refresh.clicked.connect(self.refresh_view)
        top_bar.addWidget(btn_refresh)

        btn_open_folder = QPushButton("Open in Explorer")
        btn_open_folder.setIcon(Icons.get_icon(Icons.FOLDER, icon_color))
        btn_open_folder.setObjectName("btnPrimary")
        btn_open_folder.clicked.connect(self.open_root_folder)
        top_bar.addWidget(btn_open_folder)

        layout.addLayout(top_bar)

        # Splitter
        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # File System Model & Proxy
        self.fs_model = QFileSystemModel()
        self.fs_model.setRootPath(self.root_path)
        self.fs_model.setReadOnly(False)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setSourceModel(self.fs_model)
        self.proxy_model.setRecursiveFilteringEnabled(True)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)

        # Tree View
        self.tree = FileTree()
        self.tree.setModel(self.proxy_model)
        
        # Set root index on tree view (mapped through proxy)
        root_idx = self.fs_model.index(self.root_path)
        proxy_root_idx = self.proxy_model.mapFromSource(root_idx)
        self.tree.setRootIndex(proxy_root_idx)
        
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)
        self.tree.setSortingEnabled(True)
        self.tree.setColumnWidth(0, 250)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        
        self.tree.doubleClicked.connect(self.on_double_click)
        self.tree.selectionModel().selectionChanged.connect(self.on_selection_changed)
        
        # Context Menu
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)

        splitter.addWidget(self.tree)

        # Preview Pane
        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_layout.setContentsMargins(0, 0, 0, 0)
        
        self.lbl_preview_title = QLabel("No Selection")
        self.lbl_preview_title.setStyleSheet("font-weight: bold; padding: 5px;")
        self.preview_layout.addWidget(self.lbl_preview_title)
        
        self.preview_area = QScrollArea()
        self.preview_area.setWidgetResizable(True)
        self.preview_content = QLabel("Select a file to preview")
        self.preview_content.setAlignment(Qt.AlignCenter)
        self.preview_area.setWidget(self.preview_content)
        self.preview_layout.addWidget(self.preview_area)
        
        splitter.addWidget(self.preview_container)
        splitter.setStretchFactor(0, 2)
        splitter.setStretchFactor(1, 1)

    def on_search(self, text):
        self.proxy_model.setFilterFixedString(text)

    def get_selected_path(self):
        idx = self.tree.currentIndex()
        if not idx.isValid(): return self.root_path
        src_idx = self.proxy_model.mapToSource(idx)
        return self.fs_model.filePath(src_idx)

    def create_folder(self):
        parent_path = self.get_selected_path()
        if os.path.isfile(parent_path):
            parent_path = os.path.dirname(parent_path)
            
        name, ok = QInputDialog.getText(self, "New Folder", "Folder Name:")
        if ok and name:
            new_path = os.path.join(parent_path, name)
            if not os.path.exists(new_path):
                os.makedirs(new_path)

    def show_context_menu(self, pos):
        idx = self.tree.indexAt(pos)
        menu = QMenu()
        
        act_new_folder = menu.addAction("New Folder")
        menu.addSeparator()
        
        if idx.isValid():
            act_open = menu.addAction("Open")
            act_rename = menu.addAction("Rename")
            act_delete = menu.addAction("Delete")
            menu.addSeparator()
            act_copy_path = menu.addAction("Copy Path")
        
        action = menu.exec(self.tree.viewport().mapToGlobal(pos))
        
        if action == act_new_folder: self.create_folder()
        elif idx.isValid():
            path = self.get_selected_path()
            if action == act_open: self.open_file(path)
            elif action == act_rename: self.rename_item(idx)
            elif action == act_delete: self.delete_item(path)
            elif action == act_copy_path: 
                from PySide6.QtWidgets import QApplication
                QApplication.clipboard().setText(path)

    def rename_item(self, index):
        # QFileSystemModel is read-write, so editing the index triggers rename
        self.tree.edit(index)

    def delete_item(self, path):
        if QMessageBox.question(self, "Confirm Delete", f"Delete '{os.path.basename(path)}'?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

    def on_selection_changed(self, selected, deselected):
        path = self.get_selected_path()
        self.update_preview(path)

    def update_preview(self, path):
        if not os.path.exists(path):
            self.lbl_preview_title.setText("No Selection")
            self.preview_content = QLabel("Select a file to preview")
            self.preview_content.setAlignment(Qt.AlignCenter)
            self.preview_area.setWidget(self.preview_content)
            return

        info = QFileInfo(path)
        self.lbl_preview_title.setText(info.fileName())
        
        if os.path.isdir(path):
            self.preview_content = QLabel(f"Folder: {info.fileName()}")
            self.preview_content.setAlignment(Qt.AlignCenter)
            self.preview_area.setWidget(self.preview_content)
            return

        ext = info.suffix().lower()
        if ext in ['png', 'jpg', 'jpeg', 'bmp', 'gif', 'svg']:
            lbl = QLabel()
            pix = QPixmap(path)
            if not pix.isNull():
                if pix.width() > 400: pix = pix.scaledToWidth(400, Qt.SmoothTransformation)
                lbl.setPixmap(pix)
                lbl.setAlignment(Qt.AlignCenter)
                self.preview_area.setWidget(lbl)
            else:
                self.preview_area.setWidget(QLabel("Invalid Image"))
        elif ext in ['txt', 'md', 'py', 'json', 'xml', 'log', 'csv']:
            text_edit = QTextEdit()
            text_edit.setReadOnly(True)
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    text_edit.setPlainText(f.read(10000)) # Limit preview size
            except:
                text_edit.setPlainText("Error reading file.")
            self.preview_area.setWidget(text_edit)
        else:
            # Generic info
            lbl = QLabel(f"File Type: {ext.upper()}\nSize: {info.size()} bytes\nModified: {info.lastModified().toString()}")
            lbl.setAlignment(Qt.AlignCenter)
            self.preview_area.setWidget(lbl)

    def refresh_view(self):
        # Reset root path to force refresh if needed, though QFileSystemModel watches changes
        self.tree.setRootIndex(self.proxy_model.mapFromSource(self.fs_model.index(self.root_path)))
        show_toast(self, "Documents refreshed", 1500, "info")

    def open_root_folder(self):
        QDesktopServices.openUrl(QUrl.fromLocalFile(self.root_path))

    def on_double_click(self, index):
        path = self.get_selected_path()
        self.open_file(path)

    def open_file(self, path):
        if os.path.isfile(path):
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
