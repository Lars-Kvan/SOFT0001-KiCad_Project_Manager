from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QLineEdit, QListWidgetItem,
                             QDialog, QTextEdit, QStyledItemDelegate, QStyle, QComboBox, QSlider, QFrame, QSizePolicy)
from PySide6.QtCore import Qt, QRect, QSize, QTimer, QPointF
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics, QPainterPath, QDrag, QStandardItemModel, QStandardItem, QCursor
from PySide6.QtWidgets import QApplication

class KanbanTaskWidget(QWidget):
    PRIORITY_COLOR_MAP = {
        "Low": "#2ecc71",
        "Normal": "#f1c40f",
        "High": "#e74c3c",
        "Critical": "#9b59b6",
    }
    COMBO_STYLE = """
QComboBox {
    background: rgba(255, 255, 255, 0.07);
    color: #f8fafc;
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 10px;
    padding: 3px 9px;
    min-height: 28px;
}
QComboBox::drop-down {
    width: 20px;
    border: none;
}
QComboBox::down-arrow {
    width: 0;
    height: 0;
    border: none;
}
QComboBox QAbstractItemView {
    background: #111827;
    border-radius: 12px;
    padding: 4px;
    outline: none;
}
"""
    def __init__(self, item, logic, parent_list, project_type="Standard"):
        super().__init__()
        self.item = item
        self.logic = logic
        self.parent_list = parent_list
        self.project_type = project_type
        self.drag_start_pos = None
        self._category_color = None
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self.container = QFrame()
        self.container.setObjectName("taskBubble")
        self.container.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Fixed)
        main_layout.addWidget(self.container)

        container_layout = QVBoxLayout(self.container)
        container_layout.setContentsMargins(12, 10, 12, 12)
        container_layout.setSpacing(8)

        theme = self.logic.settings.get("theme", "Light")
        dark_mode = theme in {"Dark", "Teal Sand Dark"}
        bg_color = "#111827" if dark_mode else "#FFFFFF"
        border_color = "#1F2937" if dark_mode else "#E5E7EB"
        text_color = "#F8FAFC" if dark_mode else "#0F172A"
        self.container.setStyleSheet(
            f"QFrame#taskBubble {{ background-color: {bg_color}; border: 1px solid {border_color}; border-radius: 16px; }}"
        )

        self.title_edit = QLineEdit(item.text())
        self.title_edit.setObjectName("taskTitle")
        self.title_edit.setPlaceholderText("Task Name")
        self.title_edit.setStyleSheet(
            "QLineEdit#taskTitle { border: none; background: transparent; font-weight: 700; font-size: 13px; }"
            "QLineEdit#taskTitle:focus { border-bottom: 1px solid rgba(15, 118, 110, 0.5); }"
        )
        self.title_edit.textChanged.connect(self.on_title_changed)
        container_layout.addWidget(self.title_edit)

        self.desc_edit = QTextEdit(item.data(Qt.UserRole))
        self.desc_edit.setObjectName("taskDescription")
        self.desc_edit.setFixedHeight(70)
        self.desc_edit.setStyleSheet(
            f"QTextEdit#taskDescription {{ border: none; background: transparent; color: {text_color}; font-size: 12px; }}"
        )
        self.desc_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        container_layout.addWidget(self.desc_edit)

        self.meta_row = QWidget()
        meta_layout = QHBoxLayout(self.meta_row)
        meta_layout.setContentsMargins(0, 0, 0, 0)
        meta_layout.setSpacing(8)
        self.category_label = QLabel("Category: Task")
        self.category_label.setObjectName("categoryLabel")
        self.category_label.setStyleSheet("font-size: 11px; font-weight: 600; border-radius: 6px; padding: 2px 8px;")
        meta_layout.addWidget(self.category_label)
        self.priority_label = QLabel("Priority: Normal")
        self.priority_label.setObjectName("priorityLabel")
        self.priority_label.setStyleSheet("font-size: 11px; font-weight: 600; border-radius: 6px; padding: 2px 8px;")
        meta_layout.addWidget(self.priority_label)
        meta_layout.addStretch()
        container_layout.addWidget(self.meta_row)

        self.action_row = QWidget()
        action_layout = QHBoxLayout(self.action_row)
        action_layout.setContentsMargins(0, 0, 0, 0)
        action_layout.setSpacing(8)
        self.combo_prio = QComboBox()
        self.combo_prio.setObjectName("prioCombo")
        self.combo_prio.setMinimumWidth(120)
        action_layout.addWidget(self.combo_prio)
        self.combo_cat = QComboBox()
        self.combo_cat.setObjectName("categoryCombo")
        self.combo_cat.setMinimumWidth(140)
        self.combo_cat.setEditable(False)
        action_layout.addWidget(self.combo_cat, 1)
        self.combo_prio.setStyleSheet(self.COMBO_STYLE)
        self.combo_cat.setStyleSheet(self.COMBO_STYLE)
        action_layout.addStretch()
        self.action_row.setVisible(True)
        container_layout.addWidget(self.action_row)

        self.setup_prio_combo()
        cats = list(self.logic.settings.get("kanban_categories", {}).keys()) or ["Task"]
        restrictions = self.logic.settings.get("category_restrictions", {})
        filtered_cats = []
        for c in cats:
            restr = restrictions.get(c, [])
            if not restr or self.project_type in restr:
                filtered_cats.append(c)
        if not filtered_cats:
            filtered_cats = cats
        self.combo_cat.addItems(filtered_cats)
        current_cat = item.data(Qt.UserRole + 2)
        if current_cat in filtered_cats:
            self.combo_cat.setCurrentText(current_cat)
        self.combo_cat.currentTextChanged.connect(self.on_cat_changed)

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("KanbanTaskWidget { background-color: transparent; }")

        self.update_category_badge()
        self.update_priority_badge()

    def update_category_badge(self):
        cat = self.combo_cat.currentText() or "Task"
        color = self.logic.settings.get("kanban_categories", {}).get(cat, "#95a5a6")
        self._category_color = color
        badge_color = QColor(color)
        lum = 0.299 * badge_color.red() + 0.587 * badge_color.green() + 0.114 * badge_color.blue()
        text_color = "#050505" if lum > 150 else "#f8fafc"
        self.category_label.setText(f"Category: {cat}")
        self.category_label.setStyleSheet(
            f"background-color: {color}; color: {text_color}; border-radius: 6px; "
            "font-size: 11px; font-weight: 600; padding: 4px 10px;"
        )
        self.update_header_style()

    def update_priority_badge(self):
        text = self.combo_prio.currentText() or "Normal"
        color = self.PRIORITY_COLOR_MAP.get(text, "#95a5a6")
        badge_color = QColor(color)
        lum = 0.299 * badge_color.red() + 0.587 * badge_color.green() + 0.114 * badge_color.blue()
        text_color = "#050505" if lum > 150 else "#ffffff"
        self.priority_label.setText(f"Priority: {text}")
        self.priority_label.setStyleSheet(
            f"background-color: {color}; color: {text_color}; border-radius: 6px; "
            "font-size: 11px; font-weight: 600; padding: 4px 10px;"
        )

    def setup_prio_combo(self):
        model = QStandardItemModel()
        priorities = [
            ("Low", "#2ecc71"),      # Green
            ("Normal", "#f1c40f"),   # Yellow
            ("High", "#e74c3c"),     # Red
            ("Critical", "#9b59b6")  # Purple
        ]
        for txt, col in priorities:
            item = QStandardItem(txt)
            item.setBackground(QColor(col))
            item.setForeground(QColor("black"))
            model.appendRow(item)
        self.combo_prio.setModel(model)
        
        # Set initial selection
        current = self.item.data(Qt.UserRole + 3) or "Normal"
        idx = self.combo_prio.findText(current)
        if idx >= 0: self.combo_prio.setCurrentIndex(idx)
        
        # Connect signal
        self.combo_prio.currentIndexChanged.connect(self.on_prio_changed)
        self.update_priority_badge()

    def on_title_changed(self, text):
        self.item.setText(text)
        self.parent_list.trigger_sync()

    def on_desc_changed(self):
        self.item.setData(Qt.UserRole, self.desc_edit.toPlainText())
        self.parent_list.trigger_sync()

    def on_prio_changed(self, index):
        text = self.combo_prio.currentText()
        self.item.setData(Qt.UserRole + 3, text)
        self.parent_list.trigger_sync()
        self.update_priority_badge()

    def on_cat_changed(self, text):
        self.item.setData(Qt.UserRole + 2, text)
        self.update_category_badge()
        
        # Update parent tab's memory of last used category
        if hasattr(self.parent_list, 'parent_tab'):
            self.parent_list.parent_tab.last_kanban_category = text
            
        self.parent_list.trigger_sync()

    def set_compact(self, compact):
        """Toggles visibility of description and footer for compact mode."""
        self.desc_edit.setVisible(not compact)
        self.footer.setVisible(not compact)
        self.meta_row.setVisible(not compact)

    # --- Drag & Drop Handling ---
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.pos()
            # Ensure the item is selected in the list when clicked
            self.item.setSelected(True)
            self.parent_list.setCurrentItem(self.item)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.drag_start_pos:
            if (event.pos() - self.drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self.start_drag()
                self.drag_start_pos = None
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.drag_start_pos = None
        super().mouseReleaseEvent(event)

    def start_drag(self):
        drag = QDrag(self)
        # Use the parent list's mimeData method via a public helper
        mime = self.parent_list.get_mime_data([self.item])
        drag.setMimeData(mime)
        
        # Create a pixmap of the widget for visual feedback
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.drag_start_pos)
        
        if drag.exec(Qt.MoveAction) == Qt.MoveAction:
            # Remove the item from the source list (this widget's parent list)
            # This prevents duplication because QListWidget's default dropEvent (via manual drag)
            # creates a copy in the destination but doesn't delete the source automatically.
            self.parent_list.takeItem(self.parent_list.row(self.item))
            # Trigger sync to save changes
            self.parent_list.trigger_sync()

class KanbanList(QListWidget):
    def __init__(self, key, parent_tab):
        super().__init__()
        self.key = key
        self.parent_tab = parent_tab
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSpacing(8)
        # Stylesheet moved to styles.py for theming support

    # Override dropEvent to ensure proper synchronization after drag-and-drop
    # This is crucial because the item is moved from one list to another.
    def dropEvent(self, event):
        super().dropEvent(event)
        
        # Restore widgets for dropped items (QListWidget drops create new items without widgets)
        for i in range(self.count()):
            item = self.item(i)
            if not self.itemWidget(item):
                widget = KanbanTaskWidget(item, self.parent_tab.logic, self, self.parent_tab.get_current_project_type())
                item.setSizeHint(widget.sizeHint())
                self.setItemWidget(item, widget)
        
        # Sync is now handled in start_drag to ensure source item is removed first

    def trigger_sync(self):
        self.parent_tab.sync_kanban_from_ui()

    def get_mime_data(self, items):
        """Expose protected mimeData for child widgets."""
        return self.mimeData(items)
