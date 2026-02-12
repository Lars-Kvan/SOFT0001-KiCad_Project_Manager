import json
from datetime import datetime, timedelta, date, time
from pathlib import Path
from copy import deepcopy

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QLineEdit, QDateEdit, QTimeEdit, QScrollArea,
    QFrame, QGraphicsDropShadowEffect, QSizePolicy, QDialog, QTextEdit,
    QProgressBar, QMessageBox, QTabWidget, QSplitter, QListWidget,
    QListWidgetItem, QDoubleSpinBox, QColorDialog, QAbstractItemView,
    QFormLayout
)
from PySide6.QtCore import Qt, QDate, QTime, Signal, QRect, QRectF, QTimer, QMimeData, QEvent
from PySide6.QtGui import QColor, QPainter, QPen, QDrag, QPainterPath, QLinearGradient, QFont
from ui.widgets.spacing import apply_layout, PAGE_PADDING
from ui.widgets.progress_utils import style_progress_bar

# --- Config ---
SLOT_H = 60
BG_COLOR = "#09090b"      # Very dark background
BOX_BG = "#18181b"        # Day box background
BORDER_COLOR = "#27272a"  # Subtle border
WEEKEND_HIGHLIGHT = "#0f172a"
ACCENT = "#6366f1"

COLORS = [
    "#7c3aed", "#ea580c", "#0ea5e9", "#22c55e",
    "#e11d48", "#f97316", "#6366f1", "#14b8a6"
]
TEXT_COLOR = "#0f172a"
SUBTEXT_COLOR = "#1f2937"
GLOW = "rgba(15,23,42,0.15)"

def readable_text_color(bg_hex):
    col = QColor(bg_hex)
    lum = (0.299 * col.red()) + (0.587 * col.green()) + (0.114 * col.blue())
    return "#05060a" if lum > 150 else "#f8fafc"

STYLE = f"""
    QMainWindow, QWidget {{ background-color: {BG_COLOR}; color: #e4e4e7; font-family: 'Segoe UI', sans-serif; }}
    #tabHeader {{
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #18181b, stop:1 #121215);
    }}
    #tabHeaderTitle {{ color: #f8fafc; font-weight: 800; font-size: 14px; }}
    #tabHeaderSubtitle {{ color: #a1a1aa; font-size: 12px; }}
    #tabHeaderStatus {{
        color: #E2E8F0;
        background: #111827;
        border: 1px solid #1F2937;
        border-radius: 999px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 700;
        max-width: 220px;
    }}
    #tabHeaderDivider {{ background: #27272a; }}
    
    /* Day Box Container */
    QWidget#dayBox {{
        background-color: {BOX_BG};
        border: 1px solid {BORDER_COLOR};
        border-radius: 12px;
    }}

    /* Inputs */
    QLineEdit, QComboBox, QDateEdit, QTimeEdit {{
        background-color: {BOX_BG}; border: 1px solid {BORDER_COLOR}; border-radius: 6px;
        padding: 5px 10px; color: #fff; font-size: 12px;
    }}
    
    /* Buttons */
    QPushButton {{
        background-color: {BOX_BG}; border: 1px solid {BORDER_COLOR}; border-radius: 6px;
        color: #fff; padding: 6px 12px; font-weight: 600; font-size: 12px;
    }}
    QPushButton:hover {{ background-color: #27272a; }}
    QPushButton#actionBtn {{ background-color: {ACCENT}; border: none; }}
    QPushButton#actionBtn:hover {{ background-color: #4f46e5; }}
    QPushButton#deleteBtn {{ color: #f87171; background: transparent; border: 1px solid #f87171; }}
    QPushButton#deleteBtn:hover {{ background: #f87171; color: #000; }}

    QLabel#weekRangeBubble {{
        background-color: #171923;
        border: 1px solid #3f475f;
        border-radius: 18px;
        padding: 6px 18px;
        font-weight: 600;
        font-size: 13px;
        color: #f8fafc;
        min-width: 220px;
    }}

    /* Scroll */
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ width: 8px; background: {BG_COLOR}; }}
    QScrollBar::handle:vertical {{ background: #3f3f46; border-radius: 4px; }}
"""

# --- Logic ---
class DataStore:
    def __init__(self, logic):
        self.logic = logic
        self.entries = []
        self.projects = ["Engineering", "Admin", "Research", "Deep Work"]
        self.task_library = {}
        self.load()

    def load(self):
        self.entries = list(self.logic.get_time_entries())
        projects = sorted({e.get("project", "") for e in self.entries if e.get("project")})
        if projects:
            self.projects = projects
        self._load_task_library()

    def _load_task_library(self):
        self.task_library = deepcopy(self.logic.get_time_task_library())

    def reload_task_library(self):
        self._load_task_library()

    def save_task_library(self, library):
        self.logic.save_time_task_library(library)
        self._load_task_library()

    def save(self):
        self.logic.save_time_entries(self.entries)

# --- Visual Components ---

class TaskDialog(QDialog):
    def __init__(self, entry, projects, library=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Entry")
        self.resize(420, 580)
        self.entry = entry
        self.delete_requested = False
        self.library = deepcopy(library) if library else {"categories": [], "tasks": []}
        self._template_update_block = False
        
        # Styling
        self.setStyleSheet(f"""
            QDialog {{ background-color: {BG_COLOR}; }}
            QLabel {{ color: #a1a1aa; font-size: 12px; font-weight: 600; }}
            QLineEdit, QComboBox, QTimeEdit, QTextEdit {{
                background-color: {BOX_BG}; 
                border: 1px solid {BORDER_COLOR}; 
                border-radius: 8px;
                padding: 10px;
                color: #e4e4e7;
                font-size: 12px;
            }}
            QComboBox::drop-down {{ border: none; }}
            QComboBox::down-arrow {{ 
                image: none; border: none; 
                border-left: 5px solid transparent; 
                border-right: 5px solid transparent; 
                border-top: 5px solid #71717a; 
                margin-right: 10px; 
            }}
            QTextEdit {{ padding: 10px; }}
            QPushButton {{
                background-color: {BOX_BG}; border: 1px solid {BORDER_COLOR}; border-radius: 8px;
                color: #e4e4e7; padding: 10px 20px; font-weight: 600; font-size: 12px;
            }}
            QPushButton:hover {{ background-color: #27272a; border-color: #3f3f46; }}
            QPushButton#deleteBtn {{ 
                background-color: transparent; 
                border: 1px solid #ef4444; 
                color: #ef4444; 
            }}
            QPushButton#deleteBtn:hover {{ 
                background-color: #ef4444; 
                color: white; 
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)
        
        # Header
        lbl_title = QLabel("Edit Entry")
        lbl_title.setStyleSheet("font-size: 20px; font-weight: 800; color: white; margin-bottom: 8px;")
        layout.addWidget(lbl_title)
        
        # Time Row
        time_layout = QHBoxLayout()
        time_layout.setSpacing(16)
        
        v_start = QVBoxLayout(); v_start.setSpacing(6)
        v_start.addWidget(QLabel("Start Time"))
        self.in_start = QTimeEdit()
        self.in_start.setDisplayFormat("HH:mm")
        v_start.addWidget(self.in_start)
        
        v_end = QVBoxLayout(); v_end.setSpacing(6)
        v_end.addWidget(QLabel("End Time"))
        self.in_end = QTimeEdit()
        self.in_end.setDisplayFormat("HH:mm")
        v_end.addWidget(self.in_end)
        
        time_layout.addLayout(v_start)
        time_layout.addLayout(v_end)
        layout.addLayout(time_layout)
        
        # Project
        layout.addWidget(QLabel("Project"))
        self.in_proj = QComboBox()
        self.in_proj.setEditable(True)
        self.in_proj.addItems(projects)
        self.in_proj.lineEdit().setPlaceholderText("Select or type project...")
        layout.addWidget(self.in_proj)

        layout.addWidget(QLabel("Category"))
        self.in_category = QComboBox()
        self.in_category.setEditable(True)
        self.in_category.addItems([c.get("name", "") for c in self.library.get("categories", []) if c.get("name")])
        self.in_category.lineEdit().setPlaceholderText("Select or type category...")
        layout.addWidget(self.in_category)
        
        # Task
        layout.addWidget(QLabel("Task"))
        self.in_task = QComboBox()
        self.in_task.setEditable(True)
        self.task_templates = [t for t in self.library.get("tasks", []) if t.get("name")]
        for template in self.task_templates:
            self.in_task.addItem(template["name"], template)
        self.in_task.lineEdit().setPlaceholderText("What are you working on?")
        self.in_task.currentIndexChanged.connect(self._on_task_template_change)
        layout.addWidget(self.in_task)
        
        # Subtask
        layout.addWidget(QLabel("Subtask"))
        self.in_subtask = QComboBox()
        self.in_subtask.setEditable(True)
        self.in_subtask.lineEdit().setPlaceholderText("Optional context...")
        layout.addWidget(self.in_subtask)

        layout.addWidget(QLabel("Tags"))
        self.in_tags = QLineEdit()
        self.in_tags.setPlaceholderText("Comma-separated tags")
        layout.addWidget(self.in_tags)

        duration_layout = QHBoxLayout()
        duration_layout.addWidget(QLabel("Template Duration (hrs)"))
        self.duration_spin = QDoubleSpinBox()
        self.duration_spin.setRange(0.0, 24.0)
        self.duration_spin.setSingleStep(0.25)
        self.duration_spin.setDecimals(2)
        duration_layout.addWidget(self.duration_spin)
        btn_duration = QPushButton("Apply duration")
        btn_duration.clicked.connect(self._apply_duration_to_end)
        duration_layout.addWidget(btn_duration)
        layout.addLayout(duration_layout)
        
        # Description
        layout.addWidget(QLabel("Description"))
        self.in_desc = QTextEdit()
        self.in_desc.setPlaceholderText("Add details, notes, or links...")
        self.in_desc.setFixedHeight(120)
        layout.addWidget(self.in_desc)
        
        layout.addStretch()
        
        # Footer
        footer = QHBoxLayout()
        btn_del = QPushButton("Delete Entry")
        btn_del.setObjectName("deleteBtn")
        btn_del.clicked.connect(self._on_delete)
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_save = QPushButton("Save")
        btn_save.setObjectName("actionBtn")
        btn_save.clicked.connect(self.accept)

        footer.addWidget(btn_del)
        footer.addWidget(btn_cancel)
        footer.addStretch()
        footer.addWidget(btn_save)
        layout.addLayout(footer)
        
        # Populate
        s = datetime.strptime(entry["start"], "%Y-%m-%d %H:%M:%S")
        e = datetime.strptime(entry["end"], "%Y-%m-%d %H:%M:%S")
        self.in_start.setTime(s.time())
        self.in_end.setTime(e.time())
        self.in_proj.setCurrentText(entry.get("project", ""))
        self.in_category.setCurrentText(entry.get("category", ""))
        self._template_update_block = True
        self.in_task.setCurrentText(entry.get("task", ""))
        self._template_update_block = False
        template = self._current_task_template()
        if template:
            self._apply_template(template)
        if entry.get("category"):
            self.in_category.setCurrentText(entry["category"])
        tags = entry.get("tags", "")
        if isinstance(tags, list):
            tags = ", ".join(t for t in tags if t)
        self.in_tags.setText(tags or "")
        self.in_subtask.setCurrentText(entry.get("subtask", ""))
        description = entry.get("description", "")
        if description:
            self.in_desc.setPlainText(description)
        self.setWindowFlag(Qt.FramelessWindowHint, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(42)
        shadow.setOffset(0, 14)
        shadow.setColor(QColor(0, 0, 0, 160))
        self.setGraphicsEffect(shadow)

    def _on_delete(self):
        self.delete_requested = True
        self.accept()

    def update_entry_data(self):
        s_old = datetime.strptime(self.entry["start"], "%Y-%m-%d %H:%M:%S")
        e_old = datetime.strptime(self.entry["end"], "%Y-%m-%d %H:%M:%S")
        
        qt_s = self.in_start.time()
        qt_e = self.in_end.time()
        
        new_s = datetime.combine(s_old.date(), time(qt_s.hour(), qt_s.minute(), qt_s.second()))
        new_e = datetime.combine(e_old.date(), time(qt_e.hour(), qt_e.minute(), qt_e.second()))

        if new_e <= new_s:
            new_e += timedelta(days=1)

        self.entry["start"] = new_s.strftime("%Y-%m-%d %H:%M:%S")
        self.entry["end"] = new_e.strftime("%Y-%m-%d %H:%M:%S")
        self.entry["project"] = self.in_proj.currentText()
        self.entry["category"] = self.in_category.currentText()
        self.entry["task"] = self.in_task.currentText()
        self.entry["subtask"] = self.in_subtask.currentText()
        self.entry["description"] = self.in_desc.toPlainText()
        tags = [t.strip() for t in self.in_tags.text().split(",") if t.strip()]
        self.entry["tags"] = tags

    def _current_task_template(self):
        data = self.in_task.itemData(self.in_task.currentIndex())
        return data if isinstance(data, dict) else None

    def _on_task_template_change(self, index):
        if self._template_update_block:
            return
        template = self._current_task_template()
        if template:
            self._apply_template(template)

    def _apply_template(self, template, force=False):
        category = template.get("category", "")
        if category:
            self.in_category.setCurrentText(category)
        duration = template.get("default_duration")
        if duration is not None:
            self.duration_spin.setValue(float(duration))
        tags = template.get("tags", [])
        if isinstance(tags, list) and tags:
            self.in_tags.setText(", ".join(tags))
        description = template.get("description", "")
        if description and (force or not self.in_desc.toPlainText().strip()):
            self.in_desc.setPlainText(description)
        self._refresh_subtask_options(template.get("subtasks", []))

    def _refresh_subtask_options(self, subtasks):
        current = self.in_subtask.currentText()
        self.in_subtask.blockSignals(True)
        self.in_subtask.clear()
        for sub in subtasks or []:
            title = sub.get("title") if isinstance(sub, dict) else str(sub)
            if title:
                self.in_subtask.addItem(title)
        self.in_subtask.setCurrentText(current)
        self.in_subtask.blockSignals(False)

    def _apply_duration_to_end(self):
        duration = self.duration_spin.value()
        if duration <= 0:
            return
        start_qt = self.in_start.time()
        start_dt = datetime.combine(date.today(), time(start_qt.hour(), start_qt.minute(), start_qt.second()))
        end_dt = start_dt + timedelta(hours=duration)
        self.in_end.setTime(QTime(end_dt.hour, end_dt.minute, end_dt.second))

class Bubble(QFrame):
    """The colored event chip."""
    clicked = Signal(object)
    double_clicked = Signal(object)
    changed = Signal()
    delete_requested = Signal(object)

    def __init__(self, entry, color, parent=None):
        super().__init__(parent)
        self.entry = entry
        self.color = color
        self._is_selected = False
        self.setCursor(Qt.PointingHandCursor)
        self.setMouseTracking(True)
        
        self.m_drag_active = False
        self.m_drag_start_y = 0
        self.m_original_height = 0
        self.m_move_start_pos = None
        self.m_drag_start_y_local = 0

        # Enable hover for repaint
        self.setAttribute(Qt.WA_Hover)
        
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(10)
        shadow.setColor(QColor(0,0,0, 60))
        shadow.setOffset(0, 3)
        self.setGraphicsEffect(shadow)

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        
        rect = self.rect()
        
        # Background Color
        bg_col = QColor(self.color)
        if self.underMouse() or self.m_drag_active:
            bg_col = bg_col.lighter(110)
            
        # Rounded Box
        path = QPainterPath()
        path.addRoundedRect(QRectF(rect).adjusted(1, 1, -1, -1), 6, 6)
        
        # Gradient Fill
        grad = QLinearGradient(rect.topLeft(), rect.bottomLeft())
        grad.setColorAt(0, bg_col)
        grad.setColorAt(1, bg_col.darker(115))
        p.fillPath(path, grad)
        
        # Border
        if self._is_selected:
            p.setPen(QPen(QColor("white"), 2))
        else:
            p.setPen(QPen(QColor(255, 255, 255, 40), 1))
        p.drawPath(path)
        
        # Accent Strip (Left)
        p.setClipPath(path)
        p.fillRect(QRect(0, 0, 6, rect.height()), bg_col.darker(140))
        p.setClipping(False)
        
        # Text
        text_col = QColor(readable_text_color(bg_col.name()))
        p.setPen(text_col)
        
        # Project (Small, Bold, Uppercase)
        font = p.font()
        font.setBold(True); font.setPointSize(7); font.setLetterSpacing(QFont.AbsoluteSpacing, 1)
        p.setFont(font)
        p.drawText(QRect(10, 4, rect.width()-14, 12), Qt.AlignLeft, self.entry.get("project", "").upper())
        
        # Task (Main Text)
        font.setBold(True); font.setPointSize(9); font.setLetterSpacing(QFont.PercentageSpacing, 100)
        p.setFont(font)
        fm = p.fontMetrics()
        task_text = self.entry.get("task", "Untitled")
        elided_task = fm.elidedText(task_text, Qt.ElideRight, rect.width()-14)
        p.drawText(QRect(10, 18, rect.width()-14, 16), Qt.AlignLeft, elided_task)
        
        # Calculate available vertical space for description
        y_desc_start = 36
        y_desc_end = rect.height() - 4

        # Time (Bottom, Faint)
        if rect.height() > 36:
            font.setBold(False); font.setPointSize(8)
            p.setFont(font)
            p.setPen(QColor(text_col.red(), text_col.green(), text_col.blue(), 180))
            s = datetime.strptime(self.entry["start"], "%Y-%m-%d %H:%M:%S")
            e = datetime.strptime(self.entry["end"], "%Y-%m-%d %H:%M:%S")
            p.drawText(QRect(10, rect.height()-16, rect.width()-14, 12), Qt.AlignLeft, f"{s.strftime('%H:%M')} - {e.strftime('%H:%M')}")
            y_desc_end = rect.height() - 18

        # Description (Middle)
        desc = self.entry.get("description", "")
        if desc and (y_desc_end - y_desc_start) > 10:
            font.setBold(False); font.setPointSize(8); font.setItalic(True)
            p.setFont(font)
            p.setPen(QColor(text_col.red(), text_col.green(), text_col.blue(), 160))
            p.drawText(QRectF(10, y_desc_start, rect.width()-14, y_desc_end - y_desc_start), Qt.AlignLeft | Qt.AlignTop | Qt.TextWordWrap, desc)

    def set_selected(self, selected):
        self._is_selected = selected
        self.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            # Check for "fresh creation" double click simulation
            # If this bubble was just created (via slot click), treat immediate click as double click
            created_ts = self.entry.get("_created_at", 0)
            if created_ts and (datetime.now().timestamp() - created_ts) < 0.5:
                self.double_clicked.emit(self.entry)
                e.accept()
                return

            if self.cursor().shape() == Qt.SizeVerCursor:
                self.m_drag_active = True
                self.m_drag_start_y = e.globalPosition().y()
                self.m_original_height = self.height()
                e.accept()
            else:
                self.m_move_start_pos = e.position().toPoint()
                self.m_drag_start_y_local = e.position().y()
                self.clicked.emit(self.entry)
        elif e.button() == Qt.RightButton:
            self.delete_requested.emit(self.entry)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.double_clicked.emit(self.entry)
            e.accept()
        else:
            super().mouseDoubleClickEvent(e)

    def mouseMoveEvent(self, e):
        if self.m_drag_active:
            delta = e.globalPosition().y() - self.m_drag_start_y
            # Calculate theoretical time-based height (including padding)
            raw_time_h = (self.m_original_height + 4) + delta
            # Snap to 15 min (15px) grid
            snapped_time_h = round(raw_time_h / 15.0) * 15
            # Convert back to visual height (subtract padding)
            new_h = max(11, snapped_time_h - 4)
            self.resize(self.width(), int(new_h))
            e.accept()
        else:
            if e.buttons() & Qt.LeftButton and self.m_move_start_pos:
                if (e.position().toPoint() - self.m_move_start_pos).manhattanLength() > QApplication.startDragDistance():
                    self._start_drag()
                    return

            if e.position().y() >= self.height() - 10:
                self.setCursor(Qt.SizeVerCursor)
            else:
                self.setCursor(Qt.PointingHandCursor)
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        if self.m_drag_active and e.button() == Qt.LeftButton:
            self.m_drag_active = False
            time_h = self.height() + 4
            minutes = time_h * (60.0 / SLOT_H)
            s = datetime.strptime(self.entry["start"], "%Y-%m-%d %H:%M:%S")
            new_end = s + timedelta(minutes=minutes)
            self.entry["end"] = new_end.strftime("%Y-%m-%d %H:%M:%S")
            self.changed.emit()
            e.accept()
        else:
            super().mouseReleaseEvent(e)

    def _start_drag(self):
        drag = QDrag(self)
        mime = QMimeData()
        mime.setData("application/x-clanker-entry", b"")
        drag.setMimeData(mime)
        drag.setPixmap(self.grab())
        drag.setHotSpot(self.m_move_start_pos)
        drag.exec(Qt.MoveAction)

class DayBox(QWidget):
    """A distinct box representing a single day column."""
    slot_clicked = Signal(int)
    bubble_clicked = Signal(object)
    bubble_double_clicked = Signal(object)
    bubble_delete = Signal(object)
    entry_changed = Signal()

    def __init__(self, date_obj, entries, parent=None):
        super().__init__(parent)
        self.date_obj = date_obj
        self.entries = entries
        self.selected_entry = None
        self.setObjectName("dayBox")
        self.setMinimumHeight(24 * SLOT_H)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.setAcceptDrops(True)
        self._now_timer = QTimer(self)
        self._now_timer.timeout.connect(self.update)
        self._now_timer.start(60 * 1000)
        self._ghost_rect = None
        self._lanes = []
        self._lane_map = {}
        self._lane_width = self.width()

    def paintEvent(self, e):
        # Draw internal grid lines
        p = QPainter(self)
        p.setPen(QPen(QColor(BORDER_COLOR), 1, Qt.DotLine))

        w = self.width()
        if self.date_obj.weekday() >= 5:
            p.fillRect(self.rect(), QColor(WEEKEND_HIGHLIGHT))
        else:
            p.fillRect(self.rect(), QColor(BOX_BG))

        # Draw horizontal lines for hours
        p.setPen(QPen(QColor(BORDER_COLOR), 1, Qt.DotLine))
        for h in range(1, 24):
            y = h * SLOT_H
            p.drawLine(1, y, w-1, y) # Stay inside border
        
        # Draw "now" indicator when this column matches today
        today = date.today()
        if self.date_obj == today:
            now = datetime.now()
            minutes_since = (now - datetime.combine(today, time(0, 0))).total_seconds() / 60.0
            y = minutes_since * (SLOT_H / 60.0)
            if 0 <= y <= 24 * SLOT_H:
                pen = QPen(QColor("#ef4444"), 2, Qt.SolidLine)
                pen.setCapStyle(Qt.RoundCap)
                p.setPen(pen)
                p.drawLine(2, int(y), w-2, int(y))

        if self._ghost_rect:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(Qt.NoPen)
            painter.setBrush(QColor(255, 255, 255, 80))
            painter.drawRoundedRect(self._ghost_rect, 8, 8)

    def mousePressEvent(self, e):
        hour = int(e.position().y() // SLOT_H)
        if 0 <= hour < 24:
            self.slot_clicked.emit(hour)

    def resizeEvent(self, e):
        self._render_bubbles()

    def dragEnterEvent(self, e):
        if e.source() and isinstance(e.source(), Bubble):
            e.accept()
            self._set_ghost_from_event(e)
        else:
            e.ignore()

    def dragMoveEvent(self, e):
        if e.source() and isinstance(e.source(), Bubble):
            e.accept()
            self._set_ghost_from_event(e)
        else:
            e.ignore()

    def dragLeaveEvent(self, e):
        self._clear_ghost()

    def dropEvent(self, e):
        source = e.source()
        if isinstance(source, Bubble):
            drop_y = e.position().y()
            if hasattr(source, 'm_drag_start_y_local'):
                drop_y -= source.m_drag_start_y_local
            
            snapped_y = max(0, round(drop_y / 15.0) * 15)
            hours = snapped_y / float(SLOT_H)
            
            s_old = datetime.strptime(source.entry["start"], "%Y-%m-%d %H:%M:%S")
            e_old = datetime.strptime(source.entry["end"], "%Y-%m-%d %H:%M:%S")
            duration = e_old - s_old
            
            new_start = datetime.combine(self.date_obj, time(0,0)) + timedelta(hours=hours)
            new_end = new_start + duration
            
            source.entry["start"] = new_start.strftime("%Y-%m-%d %H:%M:%S")
            source.entry["end"] = new_end.strftime("%Y-%m-%d %H:%M:%S")
            self.entry_changed.emit()
            e.accept()
            self._clear_ghost()

    def set_selection(self, entry):
        self.selected_entry = entry
        for c in self.children():
            if isinstance(c, Bubble):
                c.set_selected(c.entry is entry)

    def _render_bubbles(self):
        for c in self.children():
            if isinstance(c, Bubble):
                c.deleteLater()

        events = []
        for entry in self.entries:
            try:
                s = datetime.strptime(entry["start"], "%Y-%m-%d %H:%M:%S")
                e = datetime.strptime(entry["end"], "%Y-%m-%d %H:%M:%S")
            except:
                continue
            events.append((s, e, entry))

        # Sort events by start time
        events.sort(key=lambda x: x[0])

        lanes = []
        for start, end, entry in events:
            placed = False
            for lane in lanes:
                if start >= lane[-1][1]:
                    lane.append((start, end, entry))
                    placed = True
                    break
            if not placed:
                lanes.append([(start, end, entry)])

        total_lanes = max(1, len(lanes))
        lane_width = int((self.width() - 8) / total_lanes)

        self._lanes = lanes
        self._lane_map = {}

        for lane_index, lane in enumerate(lanes):
            x_offset = 4 + lane_index * lane_width
            for start, end, entry in lane:
                day_start = datetime.combine(self.date_obj, time(0, 0))
                start_hours = (start - day_start).total_seconds() / 3600.0
                end_hours = (end - day_start).total_seconds() / 3600.0
                y = int(start_hours * SLOT_H)
                h = int((end_hours - start_hours) * SLOT_H)
                h = max(h, 28)
                c_idx = sum(ord(x) for x in entry.get("project", "")) % len(COLORS)

                bubble = Bubble(entry, COLORS[c_idx], self)
                if entry is self.selected_entry:
                    bubble.set_selected(True)
                bubble.clicked.connect(self.bubble_clicked.emit)
                bubble.double_clicked.connect(self.bubble_double_clicked.emit)
                bubble.delete_requested.connect(self.bubble_delete.emit)
                bubble.changed.connect(self.entry_changed.emit)
                bubble.move(x_offset, y + 2)
                bubble.resize(lane_width - 4, max(24, h - 4))
                bubble.show()
                self._lane_map[id(entry)] = lane_index
        self._lane_width = lane_width

    def _ghost_lane_width(self):
        if self._lane_width > 0:
            return self._lane_width
        total_lanes = max(1, len(self._lanes))
        return max(32, int((self.width() - 8) / total_lanes))

    def _set_ghost_from_event(self, e):
        source = e.source()
        if not source or not isinstance(source, Bubble):
            return
        drop_y = e.position().y()
        if hasattr(source, "m_drag_start_y_local"):
            drop_y -= source.m_drag_start_y_local
        self._set_ghost_rect(drop_y, source.entry)

    def _set_ghost_rect(self, y_pos, entry):
        if entry is None:
            return
        try:
            s = datetime.strptime(entry["start"], "%Y-%m-%d %H:%M:%S")
            e = datetime.strptime(entry["end"], "%Y-%m-%d %H:%M:%S")
        except:
            return
        duration_hours = max(0.25, (e - s).total_seconds() / 3600.0)
        height = int(duration_hours * SLOT_H)
        height = max(28, height)
        snapped_y = max(0, round(y_pos / 15.0) * 15)
        lane_index = self._lane_map.get(id(entry), 0)
        lane_width = self._ghost_lane_width()
        x_offset = 4 + lane_index * lane_width
        self._ghost_rect = QRect(x_offset, int(snapped_y) + 2, max(28, lane_width - 4), max(24, height - 4))
        self.update()

    def _clear_ghost(self):
        if self._ghost_rect:
            self._ghost_rect = None
            self.update()

class TimeAxis(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedWidth(50)
        self.setMinimumHeight(24 * SLOT_H)
    
    def paintEvent(self, e):
        p = QPainter(self)
        p.setPen(QColor("#71717a"))
        font = p.font(); font.setPixelSize(11); font.setBold(True); p.setFont(font)
        for h in range(1, 24):
            y = h * SLOT_H
            p.drawText(QRect(0, y-10, 40, 20), Qt.AlignRight | Qt.AlignVCenter, f"{h:02}")

class WeekSummary(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(220)
        self.setStyleSheet(f"background-color: {BOX_BG}; border-radius: 12px; border: 1px solid {BORDER_COLOR};")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(15, 15, 15, 15)
        self.layout.setSpacing(10)
        
        self.lbl_title = QLabel("Week Summary")
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 16px; color: white; border: none;")
        self.layout.addWidget(self.lbl_title)
        
        self.stats_layout = QVBoxLayout()
        self.stats_layout.setSpacing(8)
        self.layout.addLayout(self.stats_layout)
        self.layout.addStretch()

    def update_stats(self, entries):
        while self.stats_layout.count():
            child = self.stats_layout.takeAt(0)
            if child.widget(): child.widget().deleteLater()
        
        totals = {}
        grand_total = 0
        for e in entries:
            s = datetime.strptime(e["start"], "%Y-%m-%d %H:%M:%S")
            end = datetime.strptime(e["end"], "%Y-%m-%d %H:%M:%S")
            dur = (end - s).total_seconds() / 3600.0
            p = e.get("project", "Unknown")
            totals[p] = totals.get(p, 0) + dur
            grand_total += dur
            
        self.lbl_title.setText(f"Total: {grand_total:.1f}h")
        
        for p, hours in sorted(totals.items(), key=lambda x: x[1], reverse=True):
            lbl = QLabel(f"{p}")
            lbl.setStyleSheet("color: #a1a1aa; font-size: 12px; font-weight: 600; border: none;")
            self.stats_layout.addWidget(lbl)
            
            h_layout = QHBoxLayout()
            h_layout.setSpacing(8)
            
            pb = QProgressBar()
            c_idx = sum(ord(x) for x in p) % len(COLORS)
            col = COLORS[c_idx]
            style_progress_bar(pb, accent=col, theme="Dark", show_text=False, min_height=6, max_height=6)
            pb.setRange(0, 100)
            pct = (hours / grand_total) * 100 if grand_total else 0
            pb.setValue(int(pct))
            
            lbl_val = QLabel(f"{hours:.1f}h")
            lbl_val.setStyleSheet("color: white; font-size: 12px; font-weight: bold; border: none;")
            
            h_layout.addWidget(pb, 1)
            h_layout.addWidget(lbl_val)
            self.stats_layout.addLayout(h_layout)

# --- Main App ---

class TimeTrackerTab(QWidget):
    def __init__(self, logic):
        super().__init__()
        self.setStyleSheet(STYLE)
        self.logic = logic
        self.store = DataStore(logic)
        self.week_start = date.today() - timedelta(days=date.today().weekday())
        self.boxes = []
        self.selected_entry = None

        layout = QVBoxLayout(self)
        apply_layout(layout, margin=PAGE_PADDING, spacing="lg")

        self.lbl_range = QLabel()
        self.lbl_range.setObjectName("weekRangeBubble")
        self.lbl_range.setAlignment(Qt.AlignCenter)
        self.lbl_range.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)
        self.lbl_range.setFixedHeight(34)

        btn_prev = QPushButton("<")
        btn_prev.clicked.connect(lambda: self._nav(-1))
        btn_prev.setFixedWidth(40)
        btn_today = QPushButton("Today")
        btn_today.setObjectName("btnPrimary")
        btn_today.clicked.connect(self._go_today)
        btn_next = QPushButton(">")
        btn_next.clicked.connect(lambda: self._nav(1))
        btn_next.setFixedWidth(40)

        top_bar = QHBoxLayout()
        top_bar.addWidget(self.lbl_range)
        top_bar.addStretch()
        top_bar.addWidget(btn_prev)
        top_bar.addWidget(btn_today)
        top_bar.addWidget(btn_next)
        layout.addLayout(top_bar)

        self.header_scroll = QScrollArea()
        self.header_scroll.setWidgetResizable(True)
        self.header_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.header_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.header_scroll.setFixedHeight(50)
        self.header_container = QWidget()
        self.header_layout = QHBoxLayout(self.header_container)
        self.header_layout.setContentsMargins(0, 0, 8, 0)
        self.header_layout.setSpacing(10)
        self.header_scroll.setWidget(self.header_container)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none;")
        scroll.installEventFilter(self)
        scroll.horizontalScrollBar().valueChanged.connect(
            self.header_scroll.horizontalScrollBar().setValue
        )

        grid_container = QWidget()
        self.grid_layout = QHBoxLayout(grid_container)
        self.grid_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_layout.setSpacing(0)
        self.grid_layout.addWidget(TimeAxis())

        self.cols_layout = QHBoxLayout()
        self.cols_layout.setContentsMargins(0, 0, 0, 0)
        self.cols_layout.setSpacing(10)
        self.grid_layout.addLayout(self.cols_layout)

        scroll.setWidget(grid_container)

        timeline_tab = QWidget()
        timeline_layout = QVBoxLayout(timeline_tab)
        timeline_layout.setContentsMargins(0, 0, 0, 0)
        timeline_layout.setSpacing(4)
        timeline_layout.addWidget(self.header_scroll)
        timeline_layout.addWidget(scroll, 1)

        self.summary_panel = WeekSummary()
        summary_tab = QWidget()
        summary_layout = QVBoxLayout(summary_tab)
        summary_layout.setContentsMargins(15, 15, 15, 15)
        summary_layout.addWidget(self.summary_panel)
        summary_layout.addStretch()

        self.tab_widget = QTabWidget()
        self.tab_widget.setProperty("stretchTabs", True)
        self.tab_widget.tabBar().setExpanding(True)
        self.tab_widget.addTab(timeline_tab, "Timeline")
        self.tab_widget.addTab(summary_tab, "Summary")
        self.library_tab = TaskLibraryTab(self.store)
        self.library_tab.library_changed.connect(self._on_library_changed)
        self.tab_widget.addTab(self.library_tab, "Task Library")
        layout.addWidget(self.tab_widget)

        QTimer.singleShot(0, lambda: scroll.verticalScrollBar().setValue(6 * SLOT_H))
        self._refresh()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel and event.modifiers() & Qt.ControlModifier:
            self._zoom_slots(event.angleDelta().y())
            return True
        return super().eventFilter(obj, event)

    def _zoom_slots(self, delta):
        global SLOT_H
        step = delta / 120
        new_height = SLOT_H + step * 5
        SLOT_H = int(max(30, min(120, new_height)))
        self._refresh()

    def _refresh(self):
        self.store.load()
        while self.header_layout.count():
            item = self.header_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.header_layout.addSpacing(40)

        while self.cols_layout.count():
            self.cols_layout.takeAt(0).widget().deleteLater()

        self.boxes.clear()
        dates = [self.week_start + timedelta(days=i) for i in range(7)]
        self.lbl_range.setText(f"{dates[0].strftime('%b %d')} — {dates[-1].strftime('%b %d')}")

        week_entries = []

        for d in dates:
            day_entries = [e for e in self.store.entries if e["start"].startswith(d.strftime("%Y-%m-%d"))]
            week_entries.extend(day_entries)

            day_total = 0
            for e in day_entries:
                s = datetime.strptime(e["start"], "%Y-%m-%d %H:%M:%S")
                end = datetime.strptime(e["end"], "%Y-%m-%d %H:%M:%S")
                day_total += (end - s).total_seconds() / 3600.0

            hl = QLabel(f"{d.strftime('%a %d')}\n{day_total:.1f}h")
            hl.setAlignment(Qt.AlignCenter)
            hl.setFixedHeight(40)

            if d == date.today():
                bg = ACCENT
                fg = "#ffffff"
            elif d.weekday() >= 5:
                bg = WEEKEND_HIGHLIGHT
                fg = "#f1f5f9"
            else:
                bg = "#3f3f46"
                fg = "#e4e4e7"

            hl.setStyleSheet(f"background-color: {bg}; color: {fg}; border-radius: 8px; font-weight: bold;")
            self.header_layout.addWidget(hl, 1)

            box = DayBox(d, day_entries)
            box.selected_entry = self.selected_entry
            box.slot_clicked.connect(lambda h, day=d: self._slot_click(day, h))
            box.bubble_clicked.connect(self._bubble_click)
            box.bubble_double_clicked.connect(self._open_task_dialog)
            box.bubble_delete.connect(self._on_bubble_delete)
            box.entry_changed.connect(self._on_entry_changed)
            self.cols_layout.addWidget(box, 1)
            self.boxes.append(box)

        self.summary_panel.update_stats(week_entries)

    def _slot_click(self, d, h):
        start = QTime(h, 0)
        end = start.addSecs(3600)
        py_start = time(start.hour(), start.minute(), start.second())
        py_end = time(end.hour(), end.minute(), end.second())

        dt_s = datetime.combine(d, py_start)
        dt_e = datetime.combine(d, py_end)
        if end <= start:
            dt_e += timedelta(days=1)

        default_proj = self.store.projects[0] if self.store.projects else "General"
        entry = {
            "project": default_proj,
            "task": "New Task",
            "start": dt_s.strftime("%Y-%m-%d %H:%M:%S"),
            "end": dt_e.strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.store.entries.append(entry)
        self.store.save()

        entry["_created_at"] = datetime.now().timestamp()

        self.selected_entry = entry
        self._refresh()

    def _bubble_click(self, entry):
        self.selected_entry = entry
        for box in self.boxes:
            box.set_selection(entry)

    def _open_task_dialog(self, entry):
        dlg = TaskDialog(entry, self.store.projects, self.store.task_library, self)
        result = dlg.exec()

        if dlg.delete_requested:
            self._delete_entry(entry)
        elif result == QDialog.Accepted:
            dlg.update_entry_data()
            if entry.get("project") and entry["project"] not in self.store.projects:
                self.store.projects.append(entry["project"])

            self.store.save()
            self._refresh()
            self._bubble_click(entry)

    def _on_entry_changed(self):
        self.store.save()
        self._refresh()

    def _delete_entry(self, entry):
        if entry in self.store.entries:
            self.store.entries.remove(entry)
            self.store.save()
            self.selected_entry = None
        self._refresh()

    def _on_bubble_delete(self, entry):
        if QMessageBox.question(self, "Delete Entry", "Delete this entry?", QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self._delete_entry(entry)

    def _on_library_changed(self):
        self.store.reload_task_library()
        self._refresh()

    def _nav(self, offset):
        self.week_start += timedelta(days=7 * offset)
        self._refresh()

    def _go_today(self):
        self.week_start = date.today() - timedelta(days=date.today().weekday())
        self._refresh()


class TaskLibraryTab(QWidget):
    library_changed = Signal()

    def __init__(self, store):
        super().__init__()
        self.store = store
        self.library = deepcopy(self.store.task_library)
        self.current_category_index = None
        self.current_task_index = None
        self.current_task = None
        self.current_subtask_index = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(self._build_category_panel())
        splitter.addWidget(self._build_task_panel())
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter)

        footer = QHBoxLayout()
        footer.addStretch()
        reset_btn = QPushButton("Reset library to defaults")
        reset_btn.clicked.connect(self._reset_library)
        footer.addWidget(reset_btn)
        layout.addLayout(footer)

        self._refresh_category_list()
        self._refresh_task_list()

    def _build_category_panel(self):
        panel = QWidget()
        panel.setMinimumWidth(260)
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(8)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Categories")
        header.setStyleSheet("font-weight: 700; font-size: 13px;")
        panel_layout.addWidget(header)

        self.cat_list = QListWidget()
        self.cat_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.cat_list.currentItemChanged.connect(self._on_category_selected)
        panel_layout.addWidget(self.cat_list, 1)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add")
        btn_add.clicked.connect(self._add_category)
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self._delete_category)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_delete)
        panel_layout.addLayout(btn_layout)

        panel_layout.addWidget(QLabel("Name"))
        self.cat_name_input = QLineEdit()
        panel_layout.addWidget(self.cat_name_input)

        panel_layout.addWidget(QLabel("Color"))
        color_row = QHBoxLayout()
        self.cat_color_input = QLineEdit()
        color_row.addWidget(self.cat_color_input, 1)
        self.cat_color_preview = QLabel()
        self.cat_color_preview.setFixedSize(24, 24)
        self.cat_color_preview.setStyleSheet("border: 1px solid #27272a; border-radius: 4px;")
        color_row.addWidget(self.cat_color_preview)
        btn_color = QPushButton("Pick")
        btn_color.clicked.connect(self._pick_category_color)
        color_row.addWidget(btn_color)
        panel_layout.addLayout(color_row)
        self.cat_color_input.textChanged.connect(self._update_category_color_preview)

        panel_layout.addWidget(QLabel("Description"))
        self.cat_desc_input = QTextEdit()
        self.cat_desc_input.setFixedHeight(80)
        panel_layout.addWidget(self.cat_desc_input)

        self.cat_save_btn = QPushButton("Save Category")
        self.cat_save_btn.clicked.connect(self._save_category)
        panel_layout.addWidget(self.cat_save_btn)

        return panel

    def _build_task_panel(self):
        panel = QWidget()
        panel_layout = QVBoxLayout(panel)
        panel_layout.setSpacing(8)
        panel_layout.setContentsMargins(0, 0, 0, 0)

        header = QLabel("Task Library")
        header.setStyleSheet("font-weight: 700; font-size: 13px;")
        panel_layout.addWidget(header)

        self.task_list = QListWidget()
        self.task_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.task_list.currentItemChanged.connect(self._on_task_selected)
        panel_layout.addWidget(self.task_list, 1)

        btn_layout = QHBoxLayout()
        btn_add = QPushButton("Add Task")
        btn_add.clicked.connect(self._add_task)
        btn_duplicate = QPushButton("Duplicate")
        btn_duplicate.clicked.connect(self._duplicate_task)
        btn_delete = QPushButton("Delete")
        btn_delete.clicked.connect(self._delete_task)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_duplicate)
        btn_layout.addWidget(btn_delete)
        panel_layout.addLayout(btn_layout)

        tabs = QTabWidget()
        tabs.setDocumentMode(True)
        tabs.setTabPosition(QTabWidget.North)
        tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        tabs.setStyleSheet("QTabWidget::pane { border: none; } QTabBar::tab { padding: 4px 10px; font-weight: 600; }")

        # Build task detail tab
        detail_tab = QWidget()
        detail_layout = QVBoxLayout(detail_tab)
        detail_layout.setContentsMargins(0, 0, 0, 0)
        detail_layout.setSpacing(12)

        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignLeft)
        form_layout.setFormAlignment(Qt.AlignLeft | Qt.AlignTop)
        form_layout.setHorizontalSpacing(10)
        form_layout.setVerticalSpacing(6)

        self.task_name_input = QLineEdit()
        form_layout.addRow("Name", self.task_name_input)

        self.task_category_combo = QComboBox()
        self.task_category_combo.setEditable(True)
        form_layout.addRow("Category", self.task_category_combo)

        color_widget = QWidget()
        color_widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)
        color_widget_layout = QHBoxLayout(color_widget)
        color_widget_layout.setContentsMargins(0, 0, 0, 0)
        color_widget_layout.setSpacing(6)
        self.task_color_input = QLineEdit()
        color_widget_layout.addWidget(self.task_color_input, 1)
        self.task_color_preview = QLabel()
        self.task_color_preview.setFixedSize(24, 24)
        self.task_color_preview.setStyleSheet("border: 1px solid #27272a; border-radius: 4px;")
        color_widget_layout.addWidget(self.task_color_preview)
        btn_task_color = QPushButton("Pick")
        btn_task_color.clicked.connect(self._pick_task_color)
        color_widget_layout.addWidget(btn_task_color)
        self.task_color_input.textChanged.connect(self._update_task_color_preview)
        form_layout.addRow("Color", color_widget)

        self.task_tags_input = QLineEdit()
        self.task_tags_input.setPlaceholderText("Comma-separated tags")
        form_layout.addRow("Tags", self.task_tags_input)

        self.task_duration_spin = QDoubleSpinBox()
        self.task_duration_spin.setRange(0.0, 24.0)
        self.task_duration_spin.setSingleStep(0.25)
        form_layout.addRow("Default duration (h)", self.task_duration_spin)

        self.task_desc_input = QTextEdit()
        self.task_desc_input.setFixedHeight(90)
        detail_layout.addLayout(form_layout)
        detail_layout.addWidget(QLabel("Description"))
        detail_layout.addWidget(self.task_desc_input)
        self.task_preview = QLabel("Select a task to preview metadata.")
        self.task_preview.setWordWrap(True)
        self.task_preview.setStyleSheet("padding: 8px; border: 1px solid #2d2d2d; border-radius: 8px; background: #111; color: #fff;")
        detail_layout.addWidget(QLabel("Preview"))
        detail_layout.addWidget(self.task_preview)
        detail_layout.addStretch()
        tabs.addTab(detail_tab, "Details")

        # Build subtasks tab
        subtask_tab = QWidget()
        subtask_layout = QVBoxLayout(subtask_tab)
        subtask_layout.setContentsMargins(0, 0, 0, 0)
        subtask_layout.setSpacing(8)

        self.subtask_list = QListWidget()
        self.subtask_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.subtask_list.currentItemChanged.connect(self._on_subtask_selected)
        subtask_layout.addWidget(self.subtask_list, 1)

        subtask_row = QHBoxLayout()
        self.subtask_title_input = QLineEdit()
        self.subtask_title_input.setPlaceholderText("Title")
        subtask_row.addWidget(self.subtask_title_input, 2)
        self.subtask_estimate_input = QDoubleSpinBox()
        self.subtask_estimate_input.setRange(0.1, 12.0)
        self.subtask_estimate_input.setSingleStep(0.25)
        self.subtask_estimate_input.setSuffix(" h")
        subtask_row.addWidget(self.subtask_estimate_input, 1)
        subtask_layout.addLayout(subtask_row)

        subtask_btns = QHBoxLayout()
        btn_sub_add = QPushButton("Add Subtask")
        btn_sub_add.clicked.connect(self._add_subtask)
        btn_sub_update = QPushButton("Update")
        btn_sub_update.clicked.connect(self._update_subtask)
        btn_sub_remove = QPushButton("Remove")
        btn_sub_remove.clicked.connect(self._remove_subtask)
        subtask_btns.addWidget(btn_sub_add)
        subtask_btns.addWidget(btn_sub_update)
        subtask_btns.addWidget(btn_sub_remove)
        subtask_layout.addLayout(subtask_btns)
        subtask_layout.addStretch()
        tabs.addTab(subtask_tab, "Subtasks")

        panel_layout.addWidget(tabs, 2)

        self.task_save_btn = QPushButton("Save Task")
        self.task_save_btn.clicked.connect(self._save_task)
        panel_layout.addWidget(self.task_save_btn)

        return panel

    def _refresh_category_list(self):
        categories = self.library.get("categories", [])
        self.cat_list.blockSignals(True)
        self.cat_list.clear()
        for category in categories:
            name = category.get("name", "Unnamed")
            item = QListWidgetItem(name)
            color = QColor(category.get("color", "#ffffff"))
            item.setForeground(color)
            item.setData(Qt.UserRole, category)
            self.cat_list.addItem(item)
        self.cat_list.blockSignals(False)
        if categories:
            idx = min(self.current_category_index or 0, len(categories) - 1)
            self.cat_list.setCurrentRow(idx)
        self._update_category_options()

    def _refresh_task_list(self):
        tasks = self.library.get("tasks", [])
        self.task_list.blockSignals(True)
        self.task_list.clear()
        for task in tasks:
            label = task.get("name", "Unnamed Task")
            category = task.get("category", "")
            display = f"{label} [{category}]" if category else label
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, task)
            self.task_list.addItem(item)
        self.task_list.blockSignals(False)
        if tasks:
            idx = min(self.current_task_index or 0, len(tasks) - 1)
            self.task_list.setCurrentRow(idx)

    def _update_category_options(self):
        if not hasattr(self, "task_category_combo"):
            return
        current = self.task_category_combo.currentText()
        self.task_category_combo.blockSignals(True)
        self.task_category_combo.clear()
        for category in self.library.get("categories", []):
            name = category.get("name")
            if name:
                self.task_category_combo.addItem(name)
        self.task_category_combo.setCurrentText(current)
        self.task_category_combo.blockSignals(False)

    def _on_category_selected(self, current, previous):
        if current is None:
            self.current_category_index = None
            self.cat_name_input.clear()
            self.cat_color_input.clear()
            self.cat_desc_input.clear()
            return
        self.current_category_index = self.cat_list.row(current)
        category = current.data(Qt.UserRole)
        if not category:
            return
        self.cat_name_input.setText(category.get("name", ""))
        self.cat_color_input.setText(category.get("color", "#ffffff"))
        self.cat_desc_input.setPlainText(category.get("description", ""))
        self._update_category_color_preview()

    def _update_category_color_preview(self, *_):
        color = self.cat_color_input.text().strip() or "#ffffff"
        self.cat_color_preview.setStyleSheet(
            f"background-color: {color}; border: 1px solid #27272a; border-radius: 4px;"
        )

    def _pick_category_color(self):
        initial = QColor(self.cat_color_input.text() or "#ffffff")
        picked = QColorDialog.getColor(initial, self, "Pick category color")
        if picked.isValid():
            self.cat_color_input.setText(picked.name())
            self._update_category_color_preview()

    def _add_category(self):
        names = {c.get("name") for c in self.library.get("categories", []) if c.get("name")}
        name = self._unique_name("New Category", names)
        entry = {"name": name, "color": "#a855f7", "description": ""}
        self.library.setdefault("categories", []).append(entry)
        self.current_category_index = len(self.library["categories"]) - 1
        self._refresh_category_list()
        self._persist_library()

    def _delete_category(self):
        if self.current_category_index is None:
            return
        category = self.library["categories"].pop(self.current_category_index)
        removed = category.get("name", "")
        for task in self.library.get("tasks", []):
            if task.get("category") == removed:
                task["category"] = ""
        self.current_category_index = None
        self._refresh_category_list()
        self._refresh_task_list()
        self._persist_library()

    def _save_category(self):
        if self.current_category_index is None:
            return
        name = self.cat_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Please enter a name for the category.")
            return
        color = self.cat_color_input.text().strip() or "#a855f7"
        description = self.cat_desc_input.toPlainText()
        category = self.library["categories"][self.current_category_index]
        old_name = category.get("name", "")
        category.update({"name": name, "color": color, "description": description})
        if old_name and old_name != name:
            for task in self.library.get("tasks", []):
                if task.get("category") == old_name:
                    task["category"] = name
        self._refresh_category_list()
        self._refresh_task_list()
        self._persist_library()

    def _on_task_selected(self, current, previous):
        if current is None:
            self.current_task_index = None
            self.current_task = None
            self._populate_task_form(None)
            return
        self.current_task_index = self.task_list.row(current)
        self.current_task = current.data(Qt.UserRole)
        self._populate_task_form(self.current_task)

    def _populate_task_form(self, task):
        if not task:
            self.task_name_input.clear()
            self.task_category_combo.setCurrentText("")
            self.task_color_input.clear()
            self._update_task_color_preview()
            self.task_desc_input.clear()
            self.task_tags_input.clear()
            self.task_duration_spin.setValue(0.0)
            self._refresh_subtask_list([])
            self.task_preview.setText("Select a task to preview metadata.")
            return
        self.task_name_input.setText(task.get("name", ""))
        self.task_category_combo.setCurrentText(task.get("category", ""))
        self.task_color_input.setText(task.get("color", "#7c3aed"))
        self._update_task_color_preview()
        self.task_desc_input.setPlainText(task.get("description", ""))
        tags = task.get("tags", [])
        self.task_tags_input.setText(", ".join(tags) if isinstance(tags, list) else str(tags))
        self.task_duration_spin.setValue(task.get("default_duration", 1.0))
        self._refresh_subtask_list(task.get("subtasks", []))
        self._update_task_preview(task)

    def _update_task_color_preview(self):
        color = self.task_color_input.text().strip() or "#7c3aed"
        self.task_color_preview.setStyleSheet(
            f"background-color: {color}; border: 1px solid #27272a; border-radius: 4px;"
        )

    def _pick_task_color(self):
        initial = QColor(self.task_color_input.text() or "#7c3aed")
        picked = QColorDialog.getColor(initial, self, "Pick task color")
        if picked.isValid():
            self.task_color_input.setText(picked.name())
            self._update_task_color_preview()

    def _refresh_subtask_list(self, subtasks):
        self.subtask_list.blockSignals(True)
        self.subtask_list.clear()
        for sub in subtasks or []:
            title = sub.get("title", "")
            estimate = sub.get("estimate", 0)
            text = f"{title} — {estimate:.2f}h"
            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, sub)
            self.subtask_list.addItem(item)
        self.subtask_list.blockSignals(False)
        self.current_subtask_index = None

    def _on_subtask_selected(self, current, previous):
        if not current or not self.current_task:
            self.current_subtask_index = None
            return
        self.current_subtask_index = self.subtask_list.row(current)
        sub = current.data(Qt.UserRole)
        if not sub:
            return
        self.subtask_title_input.setText(sub.get("title", ""))
        self.subtask_estimate_input.setValue(sub.get("estimate", 0.25))

    def _add_subtask(self):
        if not self.current_task:
            return
        title = self.subtask_title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing title", "Enter a title for the subtask.")
            return
        estimate = self.subtask_estimate_input.value()
        sub = {"title": title, "estimate": estimate}
        self.current_task.setdefault("subtasks", []).append(sub)
        self._refresh_subtask_list(self.current_task["subtasks"])
        self.subtask_title_input.clear()
        self.subtask_estimate_input.setValue(0.25)
        self._update_task_preview(self.current_task)
        self._persist_library()

    def _update_subtask(self):
        if self.current_task is None or self.current_subtask_index is None:
            return
        title = self.subtask_title_input.text().strip()
        if not title:
            QMessageBox.warning(self, "Missing title", "Enter a title for the subtask.")
            return
        estimate = self.subtask_estimate_input.value()
        sub = self.current_task["subtasks"][self.current_subtask_index]
        sub["title"] = title
        sub["estimate"] = estimate
        self._refresh_subtask_list(self.current_task["subtasks"])
        self.subtask_list.setCurrentRow(self.current_subtask_index)
        self._update_task_preview(self.current_task)
        self._persist_library()

    def _remove_subtask(self):
        if self.current_task is None or self.current_subtask_index is None:
            return
        self.current_task["subtasks"].pop(self.current_subtask_index)
        self.current_subtask_index = None
        self._refresh_subtask_list(self.current_task["subtasks"])
        self._update_task_preview(self.current_task)
        self._persist_library()

    def _add_task(self):
        names = {t.get("name") for t in self.library.get("tasks", []) if t.get("name")}
        name = self._unique_name("New Task", names)
        category = ""
        if self.library.get("categories"):
            category = self.library["categories"][0].get("name", "")
        task = {
            "name": name,
            "category": category,
            "color": "#7c3aed",
            "description": "",
            "default_duration": 1.0,
            "tags": [],
            "subtasks": [],
        }
        self.library.setdefault("tasks", []).append(task)
        self.current_task_index = len(self.library["tasks"]) - 1
        self._refresh_task_list()
        self._persist_library()

    def _duplicate_task(self):
        if not self.current_task:
            return
        new_task = deepcopy(self.current_task)
        names = {t.get("name") for t in self.library.get("tasks", []) if t.get("name")}
        new_task["name"] = self._unique_name(f"{new_task.get('name','Task')} Copy", names)
        self.library.setdefault("tasks", []).append(new_task)
        self.current_task_index = len(self.library["tasks"]) - 1
        self._refresh_task_list()
        self._persist_library()

    def _delete_task(self):
        if self.current_task_index is None:
            return
        self.library["tasks"].pop(self.current_task_index)
        self.current_task_index = None
        self.current_task = None
        self._refresh_task_list()
        self._populate_task_form(None)
        self._persist_library()

    def _save_task(self):
        if not self.current_task:
            return
        name = self.task_name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Missing name", "Task needs a name.")
            return
        self.current_task["name"] = name
        self.current_task["category"] = self.task_category_combo.currentText()
        color = self.task_color_input.text().strip() or "#7c3aed"
        self.current_task["color"] = color
        self.current_task["description"] = self.task_desc_input.toPlainText()
        tags = [
            tag.strip()
            for tag in self.task_tags_input.text().split(",")
            if tag.strip()
        ]
        self.current_task["tags"] = tags
        self.current_task["default_duration"] = self.task_duration_spin.value()
        self._refresh_task_list()
        if self.current_task_index is not None:
            self.task_list.setCurrentRow(self.current_task_index)
        self._update_task_preview(self.current_task)
        self._persist_library()

    def _update_task_preview(self, task):
        if not task:
            self.task_preview.setText("Select a task to preview metadata.")
            return
        tags = ", ".join(task.get("tags", [])) if task.get("tags") else "no tags"
        subtasks = task.get("subtasks", [])
        total = sum(s.get("estimate", 0) for s in subtasks)
        self.task_preview.setText(
            f"Category: {task.get('category','(none)')} | Duration: {task.get('default_duration',0):.2f}h\n"
            f"Tags: {tags}\nSubtasks: {len(subtasks)} ({total:.2f}h)"
        )

    def _persist_library(self):
        self.store.save_task_library(self.library)
        self.library_changed.emit()

    def _reset_library(self):
        if QMessageBox.question(
            self,
            "Reset Task Library",
            "Reset the task library to the default templates?",
            QMessageBox.Yes | QMessageBox.No,
        ) != QMessageBox.Yes:
            return
        self.store.logic.reset_time_task_library()
        self.store.reload_task_library()
        self.library = deepcopy(self.store.task_library)
        self.current_category_index = None
        self.current_task_index = None
        self.current_task = None
        self.current_subtask_index = None
        self._refresh_category_list()
        self._refresh_task_list()
        self.library_changed.emit()

    def _unique_name(self, base, existing):
        base = base.strip() or "Item"
        candidate = base
        counter = 1
        while candidate in existing:
            candidate = f"{base} {counter}"
            counter += 1
        return candidate
