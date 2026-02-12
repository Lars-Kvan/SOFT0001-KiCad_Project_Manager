from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QListWidget, 
                             QPushButton, QLabel, QLineEdit, QListWidgetItem,
                             QDialog, QTextEdit, QStyledItemDelegate, QStyle, QComboBox, QSlider, QFrame, QGraphicsDropShadowEffect, QProgressBar)
from PySide6.QtCore import Qt, QRect, QSize, QTimer, QPointF, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QFont, QFontMetrics, QPainterPath, QDrag, QStandardItemModel, QStandardItem, QCursor
from PySide6.QtWidgets import QApplication

class KanbanTaskWidget(QWidget):
    def __init__(self, item, logic, parent_list, project_type="Standard"):
        super().__init__()
        self.item = item
        self.logic = logic
        self.parent_list = parent_list
        self.project_type = project_type
        self.drag_start_pos = None
        self._is_dark_theme = self.logic.settings.get("theme", "Light") in ["Dark"]

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.card = QFrame()
        self.card.setObjectName("kanbanCard")
        self.card.setAttribute(Qt.WA_StyledBackground, True)
        self._apply_shadow()
        self.card_layout = QVBoxLayout(self.card)
        self.card_layout.setContentsMargins(14, 14, 14, 14)
        self.card_layout.setSpacing(10)
        layout.addWidget(self.card)

        header_row = QHBoxLayout()
        header_row.setSpacing(10)
        self.title_edit = QLineEdit(item.text())
        self.title_edit.setObjectName("kanbanTitle")
        self.title_edit.setFrame(False)
        self.title_edit.setPlaceholderText("Task Name")
        self.title_edit.textChanged.connect(self.on_title_changed)
        header_row.addWidget(self.title_edit, 1)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        self.progress_bar.setStyleSheet(
            "QProgressBar { background-color: rgba(255, 255, 255, 0.12); border-radius: 3px; }"
            "QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #34d399, stop:1 #10b981); border-radius: 3px; }"
        )
        header_row.addWidget(self.progress_bar, 0)
        self.card_layout.addLayout(header_row)

        self.desc_edit = QTextEdit(item.data(Qt.UserRole))
        self.desc_edit.setObjectName("kanbanDescription")
        self.desc_edit.setFrameShape(QFrame.NoFrame)
        self.desc_edit.setPlaceholderText("Add description or notes...")
        self.desc_edit.setFixedHeight(70)
        self.desc_edit.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.desc_edit.textChanged.connect(self.on_desc_changed)
        self.card_layout.addWidget(self.desc_edit)

        self.footer = QWidget()
        self.footer.setObjectName("kanbanFooter")
        f_layout = QHBoxLayout(self.footer)
        f_layout.setContentsMargins(0, 0, 0, 0)
        f_layout.setSpacing(12)
        self.combo_prio = QComboBox()
        self.setup_prio_combo()
        f_layout.addWidget(self.combo_prio)
        f_layout.addStretch()

        self.combo_cat = QComboBox()
        cats = list(self.logic.settings.get("kanban_categories", {}).keys())
        restrictions = self.logic.settings.get("category_restrictions", {})
        filtered_cats = [c for c in cats if not restrictions.get(c) or self.project_type in restrictions.get(c)]
        self.combo_cat.addItems(filtered_cats)
        current_cat = item.data(Qt.UserRole + 2)
        if current_cat in cats:
            self.combo_cat.setCurrentText(current_cat)
        self.combo_cat.currentTextChanged.connect(self.on_cat_changed)
        f_layout.addWidget(self.combo_cat)
        self.card_layout.addWidget(self.footer)

        # Initial Style
        self.update_header_style()
        self._update_progress_bar()

        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("KanbanTaskWidget { background-color: transparent; }")
        self._install_drag_filters()

    def _install_drag_filters(self):
        # Ensure drag works from anywhere on the card, not just the outer frame.
        for w in (
            self,
            self.card,
            self.footer,
            self.title_edit,
            self.desc_edit,
            self.combo_prio,
            self.combo_cat,
            self.progress_bar,
        ):
            w.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.MouseButtonPress, QEvent.MouseMove, QEvent.MouseButtonRelease):
            # Forward drag handling to the main widget; don't block normal editing.
            if event.type() == QEvent.MouseButtonPress:
                self._handle_drag_press(event)
            elif event.type() == QEvent.MouseMove:
                self._handle_drag_move(event)
            elif event.type() == QEvent.MouseButtonRelease:
                self._handle_drag_release(event)
        return super().eventFilter(watched, event)

    def _handle_drag_press(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_pos = event.position().toPoint()
            modifiers = event.modifiers()
            if modifiers & Qt.ControlModifier:
                self.item.setSelected(not self.item.isSelected())
                self.parent_list.setCurrentItem(self.item)
                return
            if modifiers & Qt.ShiftModifier:
                current_row = self.parent_list.currentRow()
                this_row = self.parent_list.row(self.item)
                if current_row < 0:
                    self.parent_list.setCurrentItem(self.item)
                    self.item.setSelected(True)
                else:
                    start = min(current_row, this_row)
                    end = max(current_row, this_row)
                    self.parent_list.clearSelection()
                    for row in range(start, end + 1):
                        it = self.parent_list.item(row)
                        if it:
                            it.setSelected(True)
                    self.parent_list.setCurrentRow(this_row)
                return
            if not self.item.isSelected():
                self.parent_list.clearSelection()
                self.item.setSelected(True)
            self.parent_list.setCurrentItem(self.item)

    def _handle_drag_move(self, event):
        if self.drag_start_pos:
            if (event.position().toPoint() - self.drag_start_pos).manhattanLength() >= QApplication.startDragDistance():
                self.start_drag()
                self.drag_start_pos = None

    def _handle_drag_release(self, _event):
        self.drag_start_pos = None

    def _update_progress_bar(self):
        value = int(self.item.data(Qt.UserRole + 1) or 0)
        self.progress_bar.setValue(max(0, min(100, value)))

    def _apply_shadow(self):
        # Subtle shadow; avoid aggressive blur to reduce clipping/glitching during drag/scroll.
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setOffset(0, 2)
        shadow.setColor(QColor(0, 0, 0, 70 if self._is_dark_theme else 45))
        self.card.setGraphicsEffect(shadow)

    def _pill_style(self, bg_color, text_color, border_color):
        return (
            "QComboBox {"
            f" background-color: {bg_color};"
            f" color: {text_color};"
            f" border: 1px solid {border_color};"
            " border-radius: 14px;"
            " padding: 2px 18px 2px 10px;"
            " font-family: 'Segoe UI', 'Roboto', sans-serif;"
            " font-weight: 600;"
            " font-size: 11px;"
            " }"
            "QComboBox::drop-down {"
            " border: 0px;"
            " width: 26px;"
            " background: transparent;"
            " margin-right: 0px;"
            " }"
            "QComboBox::down-arrow {"
            " width: 0;"
            " height: 0;"
            " border-left: 6px solid transparent;"
            " border-right: 6px solid transparent;"
            f" border-top: 6px solid {text_color};"
            " margin-right: 8px;"
            " }"
            "QComboBox QAbstractItemView {"
            f" color: {text_color};"
            " background-color: rgba(18, 23, 30, 0.95);"
            " border-radius: 12px;"
            " border: 1px solid rgba(255, 255, 255, 0.08);"
            " padding: 4px;"
            " selection-background-color: rgba(255, 255, 255, 0.15);"
            " selection-color: #FFFFFF;"
            " }"
            "QComboBox QListView::item {"
            f" color: {text_color};"
            " padding: 6px 10px;"
            " border-radius: 8px;"
            " }"
            "QComboBox QListView::item:selected {"
            " background-color: rgba(255, 255, 255, 0.18);"
            " }"
        )

    def update_header_style(self):
        cat = self.combo_cat.currentText()
        color = self.logic.settings.get("kanban_categories", {}).get(cat, "#95a5a6")
        
        # Calculate contrast for title text
        c = QColor(color)
        lum = 0.299 * c.red() + 0.587 * c.green() + 0.114 * c.blue()
        text_color = "black" if lum > 140 else "white"
        
        self.title_edit.setStyleSheet(
            f"background: transparent; color: {text_color}; font-family: 'Segoe UI', 'Roboto', sans-serif; "
            "font-weight: 700; font-size: 13px;"
        )
        self._update_card_style(color)

    def _update_card_style(self, accent_color=None):
        border = "rgba(255,255,255,0.08)" if self._is_dark_theme else "rgba(15,23,42,0.08)"
        accent = QColor(accent_color or "#95a5a6")
        bg_color = accent.name()
        self.card.setStyleSheet(
            "QFrame#kanbanCard {"
            " border-radius: 16px;"
            " border: 1px solid " + border + ";"
            " background-color: " + bg_color + ";"
            " }"
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
        self.update_prio_style()

    def on_title_changed(self, text):
        self.item.setText(text)
        self.parent_list.trigger_sync()

    def on_desc_changed(self):
        self.item.setData(Qt.UserRole, self.desc_edit.toPlainText())
        self.parent_list.trigger_sync()

    def on_prio_changed(self, index):
        text = self.combo_prio.currentText()
        self.item.setData(Qt.UserRole + 3, text)
        self.update_prio_style()
        self.parent_list.trigger_sync()

    def update_prio_style(self):
        # Update the combobox background to match selection for visibility
        colors = {
            "Low": "#2ecc71",
            "Normal": "#f1c40f",
            "High": "#e67e22",
            "Critical": "#c0392b"
        }
        col = QColor(colors.get(self.combo_prio.currentText(), "#95a5a6"))
        bg = QColor(col)
        bg.setAlpha(70 if self._is_dark_theme else 45)
        text_col = "#F5F5F5" if self._is_dark_theme else "#111111"
        self.combo_prio.setStyleSheet(self._pill_style(bg.name(QColor.HexArgb), text_col, col.name()))
        model = self.combo_prio.model()
        for i in range(model.rowCount()):
            model.setData(model.index(i, 0), QColor(text_col), Qt.ForegroundRole)

    def on_cat_changed(self, text):
        self.item.setData(Qt.UserRole + 2, text)
        self.update_header_style()
        self.update_category_style()
        
        # Update parent tab's memory of last used category
        if hasattr(self.parent_list, 'parent_tab'):
            self.parent_list.parent_tab.last_kanban_category = text
            
        self.parent_list.trigger_sync()

    def update_category_style(self):
        cat = self.combo_cat.currentText()
        color = QColor(self.logic.settings.get("kanban_categories", {}).get(cat, "#95a5a6"))
        bg = QColor(color)
        bg.setAlpha(70 if self._is_dark_theme else 40)
        text_col = color.lighter(160).name() if self._is_dark_theme else color.darker(150).name()
        self.combo_cat.setStyleSheet(self._pill_style(bg.name(QColor.HexArgb), text_col, color.name()))

    def set_compact(self, compact):
        """Toggles visibility of description and footer for compact mode."""
        self.desc_edit.setVisible(not compact)
        self.footer.setVisible(not compact)

    def set_selected(self, selected):
        self.card.setProperty("selected", bool(selected))
        # Refresh style so the selector updates.
        self.card.style().unpolish(self.card)
        self.card.style().polish(self.card)
        self.card.update()

    # --- Drag & Drop Handling ---
    def mousePressEvent(self, event):
        self._handle_drag_press(event)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        self._handle_drag_move(event)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self._handle_drag_release(event)
        super().mouseReleaseEvent(event)

    def start_drag(self):
        drag = QDrag(self)
        # Use the parent list's mimeData method via a public helper
        items = self.parent_list.selectedItems()
        if self.item not in items:
            items.append(self.item)
        mime = self.parent_list.get_mime_data(items)
        drag.setMimeData(mime)
        
        # Create a pixmap of the widget for visual feedback
        pixmap = self.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(self.drag_start_pos)
        
        if drag.exec(Qt.MoveAction) == Qt.MoveAction:
            # Remove all dragged items from the source list to avoid duplication.
            for it in items:
                row = self.parent_list.row(it)
                if row >= 0:
                    self.parent_list.takeItem(row)
            self.parent_list.trigger_sync()

class KanbanList(QListWidget):
    def __init__(self, key, parent_tab):
        super().__init__()
        self.key = key
        self.parent_tab = parent_tab
        self.setSelectionMode(QListWidget.ExtendedSelection)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.MoveAction)
        self.setSpacing(10)
        self.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setViewportMargins(4, 4, 4, 4)
        # Stylesheet moved to styles.py for theming support
        self.itemSelectionChanged.connect(self._refresh_selection_styles)

        self._sync_timer = QTimer(self)
        self._sync_timer.setSingleShot(True)
        self._sync_timer.setInterval(200)
        self._sync_timer.timeout.connect(self.parent_tab.sync_kanban_from_ui)

    def dragEnterEvent(self, event):
        if not self._can_accept_event(event):
            event.ignore()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        if not self._can_accept_event(event):
            event.ignore()
            return
        super().dragMoveEvent(event)

    # Override dropEvent to ensure proper synchronization after drag-and-drop
    # This is crucial because the item is moved from one list to another.
    def dropEvent(self, event):
        if not self._can_accept_event(event):
            event.ignore()
            return
        super().dropEvent(event)
        
        # Restore widgets for dropped items (QListWidget drops create new items without widgets)
        for i in range(self.count()):
            item = self.item(i)
            if not self.itemWidget(item):
                widget = KanbanTaskWidget(item, self.parent_tab.logic, self, self.parent_tab.get_current_project_type())
                item.setSizeHint(widget.sizeHint())
                self.setItemWidget(item, widget)
        self._refresh_selection_styles()
        
        # Sync is now handled in start_drag to ensure source item is removed first

    def trigger_sync(self):
        # Debounce to avoid heavy disk writes on every keystroke.
        self._sync_timer.start()

    def get_mime_data(self, items):
        """Expose protected mimeData for child widgets."""
        return self.mimeData(items)

    def _can_accept_event(self, event):
        try:
            incoming = 1
            source = event.source()
            if isinstance(source, QListWidget):
                if source is self:
                    return True
                incoming = max(1, len(source.selectedItems()))
            return self.parent_tab.can_add_task_to_column(self.key, count=incoming)
        except Exception:
            return True

    def _refresh_selection_styles(self):
        for i in range(self.count()):
            item = self.item(i)
            widget = self.itemWidget(item)
            if widget and hasattr(widget, "set_selected"):
                widget.set_selected(item.isSelected())
