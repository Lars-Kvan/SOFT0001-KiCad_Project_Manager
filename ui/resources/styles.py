class Styles:
    LIGHT = """
    /* Linen Light Theme */
    QMainWindow {
        background-color: #F8F5F0;
        background-image:
            qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 rgba(248, 245, 240, 1), stop:1 rgba(238, 242, 247, 1)),
            radial-gradient(circle at 15% 20%, rgba(224, 235, 255, 0.25), transparent 45%),
            radial-gradient(circle at 85% 10%, rgba(255, 248, 233, 0.35), transparent 40%),
            radial-gradient(circle at 50% 80%, rgba(212, 200, 182, 0.2), transparent 55%);
        color: #2C2A27;
        font-family: 'Source Sans 3', 'IBM Plex Sans', 'Segoe UI', sans-serif;
    }
    QWidget {
        background-color: rgba(247, 244, 239, 0.95);
        background-image:
            radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.4), transparent 45%),
            radial-gradient(circle at 80% 60%, rgba(224, 229, 241, 0.25), transparent 55%);
        color: #2C2A27;
        font-family: 'Source Sans 3', 'IBM Plex Sans', 'Segoe UI', sans-serif;
    }
    QMainWindow#mainWindow { border: 1px solid #D7CFC4; }
    
    QGroupBox {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:1 #f4f1eb);
        border: none;
        border-radius: 16px;
        margin-top: 1.1em;
        padding: 18px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 3px 10px;
        color: #FDFCFB;
        font-weight: 700;
        background-color: #0F766E;
        border-radius: 12px 12px 0 0;
        border: 1px solid #0B5F57;
        border-bottom: none;
    }
    
    QPushButton {
        background-color: #FFFFFF;
        border: 1px solid rgba(15, 118, 110, 0.35);
        border-radius: 999px;
        padding: 8px 20px;
        color: #0F776E;
        font-weight: 600;
        text-align: center;
        min-width: 106px;
    }
    QPushButton[hovered="true"] {
        background-color: #F3FBFA;
        color: #0F776E;
    }
    QPushButton:hover {
        background-color: #F2F7F4;
    }
    QPushButton:pressed {
        background-color: #0F766E;
        color: #FFFFFF;
    }
    QPushButton:default,
    QPushButton#btnPrimary {
        background-color: #0F766E;
        color: #FFFFFF;
    }
    
    QLineEdit {
        background-color: #FFFFFF;
        border: 1px solid #D8D0C5;
        border-radius: 8px;
        padding: 6px 12px;
        color: #2C2A27;
        selection-background-color: #C7F0E4;
        selection-color: #0B5F57;
    }
    QLineEdit:focus {
        border: 1px solid #0F766E;
        background-color: #E8F6F2;
    }
    QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
        background-color: #FFFFFF;
        border: 1px solid #D8D0C5;
        border-radius: 8px;
        padding: 5px 8px;
        color: #2C2A27;
        selection-background-color: #C7F0E4;
        selection-color: #0B5F57;
    }
    QComboBox {
        padding-right: 28px;
    }
    QComboBox:hover {
        border-color: #0F766E;
        background-color: #FFFEFD;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid #E1D8CC;
        background-color: #F3EFE9;
        border-top-right-radius: 6px;
        border-bottom-right-radius: 6px;
    }
    QComboBox QAbstractItemView {
        background-color: #FFFFFF;
        border: 1px solid #D8D0C5;
        border-radius: 8px;
        padding: 4px;
        selection-background-color: #DDF1EC;
        selection-color: #0B5F57;
        outline: 0px;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px 10px;
        border-radius: 8px;
    }
    QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #0F766E;
        background-color: #FFFEFD;
    }
    QPushButton:focus { border-color: #0F766E; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #0F766E; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #0F766E; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #0F766E; }
    
    QListWidget, QTreeWidget, QTreeView, QTableWidget, QTableView {
        background-color: #FFFFFF;
        border: 1px solid #E2DBD0;
        border-radius: 12px;
        color: #2C2A27;
        alternate-background-color: rgba(16, 118, 110, 0.08);
        padding: 4px;
    }
    QListWidget::item, QTreeWidget::item, QTreeView::item, QTableWidget::item, QTableView::item {
        background: transparent;
        border-radius: 12px;
        padding: 10px 14px;
        min-height: 50px;
        margin: 4px 0;
    }
    QListWidget::item:alternate, QTreeWidget::item:alternate, QTreeView::item:alternate,
    QTableWidget::item:alternate, QTableView::item:alternate {
        background: rgba(16, 118, 110, 0.05);
    }
    QListWidget::item:hover, QTreeWidget::item:hover, QTreeView::item:hover, QTableWidget::item:hover, QTableView::item:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(15, 118, 110, 0.12), stop:1 rgba(15, 118, 110, 0.04));
        border: 1px solid #0F766E;
        color: #0B5F57;
        margin: 0;
    }
    QListWidget::item:selected, QTreeWidget::item:selected, QTreeView::item:selected, QTableWidget::item:selected, QTableView::item:selected {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(14, 116, 82, 0.35), stop:1 rgba(14, 116, 82, 0.15));
        color: #F8FAFC;
        border: none;
        font-weight: 600;
    }
    
    QHeaderView::section {
        background-color: #F1ECE6;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #D8D0C5;
        font-weight: 600;
        color: #5A544D;
    }

    QProgressBar {
        min-height: 12px;
        border-radius: 10px;
        background: rgba(15, 23, 42, 0.07);
        border: 1px solid rgba(17, 24, 39, 0.15);
        color: #0F172A;
        font-weight: 600;
        text-align: center;
    }
    QProgressBar::chunk {
        border-radius: 10px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #16a34a, stop:0.5 #0f766e, stop:1 #059669);
    }
    
    QTabWidget::pane { border: 1px solid #D8D0C5; background-color: #FFFFFF; border-radius: 8px; }
    QTabBar::tab {
        background: #EDE7DE;
        border: 1px solid #D8D0C5;
        padding: 8px 12px;
        margin-right: 4px;
        border-top-left-radius: 8px;
        border-top-right-radius: 8px;
        color: #5A544D;
        min-height: 30px;
        min-width: 110px;
        max-width: 180px;
    }
    QTabBar::tab:selected { background: #FFFFFF; border-bottom-color: #FFFFFF; color: #0F766E; font-weight: 600;  min-width: 110px; max-width: 180px; }
    QTabBar::tab:hover { background: #F5F1EB; color: #0B5F57;  min-width: 110px; max-width: 180px; }

    /* Main Tabs (Top-level) */
    QTabBar#mainTabBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8fafc, stop:1 #e2e8f0);
        border-radius: 18px;
        padding: 6px;
        border: 1px solid rgba(15, 118, 110, 0.2);
        margin-right: 8px;
    }
    QTabWidget#mainTabs::pane {
        border: none;
        background: transparent;
    }
    QTabBar#mainTabBar::tab {
        background: rgba(255, 255, 255, 0.8);
        color: #0f172a;
        border: 1px solid transparent;
        border-radius: 16px;
        padding: 12px 6px 8px;
        margin: 0 5px;
        min-width: 70px;
        min-height: 70px;
        font-weight: 600;
    }
    QTabBar#mainTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22d3ee, stop:1 #0ea5e9);
        color: #ffffff;
        border-color: rgba(14, 165, 233, 0.85);
    }
    QTabBar#mainTabBar::tab:hover {
        background: rgba(14, 165, 233, 0.1);
        color: #0f172a;
    }
    
    QScrollBar:vertical { background: #EEE7DE; width: 8px; margin: 0px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #CBBFB0; min-height: 24px; border-radius: 4px; margin: 2px; border: 1px solid #D8D0C5; }
    QScrollBar::handle:vertical:hover { background: #B8AFA3; }
    QScrollBar::handle:vertical:pressed { background: #A69C90; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal { background: #EEE7DE; height: 8px; margin: 0px; border-radius: 4px; }
    QScrollBar::handle:horizontal { background: #CBBFB0; min-width: 24px; border-radius: 4px; margin: 2px; border: 1px solid #D8D0C5; }
    QScrollBar::handle:horizontal:hover { background: #B8AFA3; }
    QScrollBar::handle:horizontal:pressed { background: #A69C90; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
    QScrollBar::corner { background: transparent; }

    QMenu { background-color: #FFFFFF; border: 1px solid #D8D0C5; color: #2C2A27; }
    QMenu::item:selected { background-color: #DDF1EC; color: #0B5F57; }
    QSplitter::handle { background-color: #D8D0C5; }
    QToolTip { background-color: #FFFEFD; color: #2C2A27; border: 1px solid #D8D0C5; }
    QLabel#formHelp { color: #6B7280; font-size: 11px; }
    #emptyStateTitle { color: #2C2A27; font-weight: 700; font-size: 13px; }
    #emptyStateBody { color: #6B7280; font-size: 12px; }
    #emptyStateAction { padding: 6px 12px; }
    QFrame#statsCard {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:1 #f4f1eb);
        border: none;
        border-radius: 16px;
        padding: 14px;
    }
    QLabel#statsCardTitle { color: #6B7280; font-size: 11px; letter-spacing: 0.2px; }
    QLabel#statsCardValue { color: #1F2937; font-size: 20px; font-weight: 700; }
    QLabel#statsCardSubtitle { color: #6B7280; font-size: 11px; }

    QFrame#heroSummary {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 rgba(255, 255, 255, 0.95), stop:1 rgba(244, 241, 235, 0.95));
        border-radius: 18px;
        border: none;
        padding: 18px;
    }

    QFrame#accentDivider {
        height: 1px;
        margin: 18px 0;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(255, 255, 255, 0), stop:0.5 rgba(255, 255, 255, 0.35), stop:1 rgba(255, 255, 255, 0));
    }

    QFrame#accentDivider {
        height: 1px;
        margin: 18px 0;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(15, 118, 110, 0), stop:0.5 rgba(15, 118, 110, 0.4), stop:1 rgba(15, 118, 110, 0));
    }

    QFrame#accentDivider {
        height: 1px;
        margin: 18px 0;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(15, 118, 110, 0), stop:0.5 rgba(15, 118, 110, 0.4), stop:1 rgba(15, 118, 110, 0));
    }

    QFrame#accentDivider {
        height: 1px;
        margin: 18px 0;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(15, 118, 110, 0), stop:0.5 rgba(15, 118, 110, 0.4), stop:1 rgba(15, 118, 110, 0));
    }
    """

    DARK = """
    /* Modern Dark Theme (VS Code Inspired) */
    QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E1E1E, stop:1 #2C2C2C); color: #D4D4D4; font-family: 'Segoe UI', 'Roboto', sans-serif; }
    QWidget { background-color: #1E1E1E; color: #D4D4D4; font-family: 'Segoe UI', 'Roboto', sans-serif; }
    QFrame, QScrollArea, QSplitter, QStackedWidget, QTabWidget::pane { background-color: #1E1E1E; }
    QMainWindow#mainWindow { border: 1px solid #3E3E42; }
    
    QGroupBox {
        background-color: #252526;
        border: 1px solid #2F353D;
        border-radius: 12px;
        margin-top: 1em;
        padding-top: 12px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 2px 10px;
        color: #f8fafc;
        font-weight: bold;
        background-color: #1e3a8a;
        border-radius: 12px 12px 0 0;
        border: 1px solid #3e3e42;
        border-bottom: none;
    }
    
    QPushButton {
        background-color: #3C3C3C;
        border: 1px solid #3E3E42;
        border-radius: 8px;
        padding: 6px 12px;
        color: #CCCCCC;
        font-weight: 600;
        text-align: left;
    }
    QPushButton:hover { background-color: #505050; border-color: #569CD6; color: #FFFFFF; }
    QPushButton:pressed { background-color: #007ACC; border-color: #007ACC; }
    
    QLineEdit {
        background-color: #3C3C3C;
        border: 1px solid #3E3E42;
        border-radius: 8px;
        padding: 6px 12px;
        color: #D4D4D4;
        selection-background-color: #2D4A6B;
        selection-color: #E9EEF7;
    }
    QLineEdit:focus {
        border: 1px solid #569CD6;
        background-color: #2B3B4D;
    }
    QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
        background-color: #3C3C3C;
        border: 1px solid #3E3E42;
        border-radius: 8px;
        padding: 5px 8px;
        color: #D4D4D4;
        selection-background-color: #2D4A6B;
        selection-color: #E9EEF7;
    }
    QComboBox {
        padding-right: 28px;
    }
    QComboBox:hover {
        border-color: #569CD6;
        background-color: #3A3F45;
    }
    QComboBox::drop-down {
        subcontrol-origin: padding;
        subcontrol-position: top right;
        width: 24px;
        border-left: 1px solid #464B52;
        background-color: #2A2F36;
        border-top-right-radius: 4px;
        border-bottom-right-radius: 4px;
    }
    QComboBox QAbstractItemView {
        background-color: #2B313A;
        border: 1px solid #3E3E42;
        border-radius: 8px;
        padding: 4px;
        selection-background-color: #2D4A6B;
        selection-color: #E9EEF7;
        outline: 0px;
    }
    QComboBox QAbstractItemView::item {
        padding: 6px 10px;
        border-radius: 8px;
    }
    QPushButton:focus { border-color: #569CD6; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #569CD6; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #569CD6; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #569CD6; }
    QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #569CD6;
        background-color: #2D2D30;
    }
    
    QListWidget, QTreeWidget, QTreeView, QTableWidget, QTableView {
        background-color: #252526;
        border: 1px solid #3E3E42;
        border-radius: 12px;
        color: #D4D4D4;
        alternate-background-color: rgba(15, 118, 110, 0.12);
    }
    QListWidget::item, QTreeWidget::item, QTreeView::item, QTableWidget::item, QTableView::item {
        background: transparent;
        border-radius: 12px;
        padding: 12px 14px;
        min-height: 50px;
        margin: 4px 0;
    }
    QListWidget::item:alternate, QTreeWidget::item:alternate, QTreeView::item:alternate,
    QTableWidget::item:alternate, QTableView::item:alternate {
        background: rgba(255, 255, 255, 0.03);
    }
    QListWidget::item:hover, QTreeWidget::item:hover, QTreeView::item:hover, QTableWidget::item:hover, QTableView::item:hover {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(255, 255, 255, 0.08), stop:1 rgba(255, 255, 255, 0.02));
        border: 1px solid rgba(255, 255, 255, 0.12);
        color: #F8FAFC;
        margin: 4px 0;
    }
    QListWidget::item:selected, QTreeWidget::item:selected, QTreeView::item:selected, QTableWidget::item:selected, QTableView::item:selected {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 rgba(14, 116, 82, 0.45), stop:1 rgba(14, 116, 82, 0.2));
        color: #F8FAFC;
        border: none;
        font-weight: 600;
        margin: 4px 0;
    }
    
    QHeaderView::section {
        background-color: #252526;
        color: #CCCCCC;
        padding: 6px;
        border: none;
        border-right: 1px solid #3E3E42;
        border-bottom: 1px solid #3E3E42;
        font-weight: bold;
    }
    QProgressBar {
        min-height: 12px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.2);
        color: #F8FAFC;
        font-weight: 600;
        text-align: center;
    }
    QProgressBar::chunk {
        border-radius: 10px;
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #0ea5e9, stop:0.5 #3b82f6, stop:1 #60a5fa);
    }
    
    QTabWidget::pane { border: 1px solid #3E3E42; background-color: #1E1E1E; border-radius: 6px; }
    QTabBar::tab {
        background-color: #2D2D30;
        color: #999999;
        padding: 8px 12px;
        border-top-left-radius: 6px;
        border-top-right-radius: 6px;
        margin-right: 2px;
        min-height: 30px;
        min-width: 110px;
        max-width: 180px;
    }
    QTabBar::tab:selected {
        background-color: #1E1E1E;
        color: #569CD6;
        border-top: 2px solid #569CD6;
        min-height: 30px;
        min-width: 110px;
        max-width: 180px;
    }

    /* Main Tabs (Top-level) */
    QTabBar#mainTabBar {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f172a, stop:1 #111827);
        border-radius: 18px;
        padding: 6px;
        border: 1px solid rgba(148, 163, 184, 0.25);
        margin-right: 8px;
    }
    QTabWidget#mainTabs::pane {
        border: none;
        background: transparent;
    }
    QTabBar#mainTabBar::tab {
        background: rgba(15, 23, 42, 0.85);
        color: #e2e8f0;
        border: 1px solid transparent;
        border-radius: 16px;
        padding: 12px 6px 8px;
        margin: 0 5px;
        min-width: 70px;
        min-height: 70px;
        font-weight: 600;
    }
    QTabBar#mainTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #22d3ee, stop:1 #0ea5e9);
        color: #ffffff;
        border-color: rgba(59, 130, 246, 0.8);
    }
    QTabBar#mainTabBar::tab:hover {
        background: rgba(59, 130, 246, 0.12);
        color: #f0f4f8;
    }
    
    QScrollBar:vertical { background: #1A1F25; width: 8px; margin: 0px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #3D4A58; min-height: 24px; border-radius: 4px; margin: 2px; border: 1px solid #2B333C; }
    QScrollBar::handle:vertical:hover { background: #4C5C6F; }
    QScrollBar::handle:vertical:pressed { background: #5F7289; }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QScrollBar:horizontal { background: #1A1F25; height: 8px; margin: 0px; border-radius: 4px; }
    QScrollBar::handle:horizontal { background: #3D4A58; min-width: 24px; border-radius: 4px; margin: 2px; border: 1px solid #2B333C; }
    QScrollBar::handle:horizontal:hover { background: #4C5C6F; }
    QScrollBar::handle:horizontal:pressed { background: #5F7289; }
    QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: transparent; }
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
    QScrollBar::corner { background: transparent; }
    
    QMenu { background-color: #252526; border: 1px solid #3E3E42; color: #D4D4D4; }
    QMenu::item:selected { background-color: #094771; }
    QSplitter::handle { background-color: #3E3E42; }

    /* Kanban Specific - Dark */
    #kanbanColumn {
        background-color: #1E1E1E; /* Matches main bg or slightly lighter */
        background-color: #252526;
        border-radius: 12px;
        border: 1px solid #3E3E42;
    }
    #kanbanHeader {
        font-weight: bold;
        color: #E0E0E0;
        font-size: 14px;
        padding: 4px;
    }
    #taskCard {
        background-color: #333333;
        border-radius: 8px;
        border: 1px solid #454545;
        border-bottom: 2px solid #252526;
    }
    #taskCard:hover { border-color: #569CD6; }
    #kanbanAddBtn { background-color: transparent; color: #AAAAAA; text-align: left; border: none; padding: 8px; border-radius: 4px; }
    #kanbanAddBtn:hover { background-color: #3E3E42; color: #FFFFFF; }
    KanbanList { background-color: transparent; border: none; outline: none; }
    """

    TEAL_SAND = """
    /* Teal Sand Theme */
    QMainWindow {
        background-color: #072b36;
        background-image:
            qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #072b36, stop:0.4 #0f5062, stop:1 #f5e8d3),
            radial-gradient(circle at 30% 25%, rgba(255, 255, 255, 0.18), transparent 50%),
            radial-gradient(circle at 70% 15%, rgba(255, 255, 255, 0.12), transparent 45%);
        color: #041c20;
        font-family: 'Source Sans 3', 'Manrope', sans-serif;
    }
    QWidget {
        background-color: rgba(245, 243, 239, 0.9);
        background-image:
            radial-gradient(circle at 70% 20%, rgba(15, 85, 96, 0.15), transparent 45%),
            radial-gradient(circle at 20% 70%, rgba(248, 231, 206, 0.25), transparent 40%);
        color: #041c20;
        font-family: 'Source Sans 3', 'Manrope', sans-serif;
    }
    QMainWindow#mainWindow { border: 1px solid rgba(11, 47, 52, 0.35); }

    QGroupBox {
        background-color: rgba(255, 255, 255, 0.86);
        border: 1px solid rgba(15, 65, 76, 0.25);
        border-radius: 16px;
        margin-top: 1em;
        padding-top: 12px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 4px 12px;
        color: #041c20;
        font-weight: 700;
        background-color: rgba(255, 255, 255, 0.98);
        border-radius: 12px;
        border: 1px solid rgba(11, 47, 52, 0.2);
        border-bottom: none;
    }

    QPushButton {
        background-color: #0f5560;
        color: #f7efe7;
        border: none;
        border-radius: 999px;
        padding: 10px 18px;
        font-weight: 600;
    }
    QPushButton[hovered="true"],
    QPushButton:hover {
        background-color: #198090;
    }
    QPushButton:pressed {
        background-color: #0c3f45;
    }

    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
        background-color: rgba(255, 255, 255, 0.95);
        border: 1px solid rgba(11, 47, 52, 0.25);
        border-radius: 10px;
        padding: 6px 12px;
        color: #041c20;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border-color: #198090;
        background-color: #ffffff;
    }
    QComboBox::drop-down {
        border-left: 1px solid rgba(11, 47, 52, 0.2);
        background-color: rgba(255, 255, 255, 0.8);
    }

    QListWidget, QTreeWidget, QTreeView, QTableWidget, QTableView {
        background-color: rgba(255, 255, 255, 0.85);
        border: 1px solid rgba(11, 47, 52, 0.2);
        border-radius: 12px;
    }
    QListWidget::item:selected, QTreeWidget::item:selected, QTreeView::item:selected,
    QTableWidget::item:selected, QTableView::item:selected {
        background-color: #198090;
        color: #f7efe7;
        border: none;
    }

    QHeaderView::section {
        background-color: rgba(11, 47, 52, 0.2);
        color: #041c20;
        padding: 6px;
        border: 1px solid rgba(11, 47, 52, 0.1);
        font-weight: 700;
    }

    QTabWidget::pane { border: 1px solid rgba(11, 47, 52, 0.2); background-color: rgba(255, 255, 255, 0.92); border-radius: 14px; }
    QTabBar::tab {
        background: rgba(12, 41, 47, 0.1);
        border: 1px solid rgba(11, 47, 52, 0.15);
        padding: 10px 16px;
        margin-right: 4px;
        border-top-left-radius: 10px;
        border-top-right-radius: 10px;
        color: #041c20;
    }
    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0d6b72, stop:1 #0b5c65);
        color: #f7efe7;
        border-color: #0c5360;
        font-weight: 700;
    }
    QTabBar::tab:hover { background: rgba(12, 41, 47, 0.25); }

    QTabBar#mainTabBar {
        background: rgba(13, 42, 50, 0.4);
        border-radius: 18px;
        padding: 6px;
        border: 1px solid rgba(15, 118, 110, 0.3);
        margin-right: 8px;
    }
    QTabWidget#mainTabs::pane {
        border: none;
        background: transparent;
    }
    QTabBar#mainTabBar::tab {
        background: rgba(248, 250, 252, 0.85);
        color: #041c20;
        border: 1px solid transparent;
        border-radius: 16px;
        padding: 12px 8px;
        margin: 0 6px;
        min-width: 80px;
        min-height: 70px;
        font-weight: 600;
    }
    QTabBar#mainTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #14b8a6, stop:1 #0f766e);
        color: #f7efe7;
        border-color: rgba(15, 118, 110, 0.8);
    }
    QTabBar#mainTabBar::tab:hover {
        background: rgba(56, 189, 248, 0.18);
        color: #041c20;
    }

    QScrollBar:vertical { background: transparent; width: 10px; }
    QScrollBar::handle:vertical { background: rgba(12, 41, 47, 0.45); border-radius: 4px; margin: 2px; }
    QScrollBar::handle:vertical:hover { background: rgba(12, 41, 47, 0.65); }
    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
    QScrollBar:horizontal { background: transparent; height: 10px; }
    QScrollBar::handle:horizontal { background: rgba(12, 41, 47, 0.45); border-radius: 4px; margin: 2px; }

    QMenu { background-color: rgba(255, 255, 255, 0.95); border: 1px solid rgba(11, 47, 52, 0.2); color: #041c20; }
    QMenu::item:selected { background-color: rgba(25, 128, 147, 0.25); }
    QSplitter::handle { background-color: rgba(11, 47, 52, 0.2); }
    QToolTip { background-color: rgba(11, 47, 52, 0.9); color: #f7efe7; border-radius: 6px; padding: 6px; }

    #emptyStateTitle { color: #041c20; font-weight: 700; font-size: 13px; }
    #emptyStateBody { color: #1b4b53; font-size: 12px; }
    #emptyStateAction { padding: 6px 12px; }
    QFrame#statsCard { background-color: rgba(255, 255, 255, 0.92); border: none; border-radius: 16px; }
    QLabel#statsCardTitle { color: #1b4b53; font-size: 11px; letter-spacing: 0.4px; }
    QLabel#statsCardValue { color: #0d6b72; font-size: 22px; font-weight: 700; }
    QLabel#statsCardSubtitle { color: #1b4b53; font-size: 11px; }
    """

    TEAL_SAND_DARK = """
    /* Teal Sand Dark */
    QMainWindow {
        background-color: #03121a;
        background-image:
            qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 #03121a, stop:0.35 #08232e, stop:0.8 #12354c),
            radial-gradient(circle at 25% 20%, rgba(15, 118, 110, 0.35), transparent 40%),
            radial-gradient(circle at 75% 35%, rgba(255, 255, 255, 0.1), transparent 45%);
        color: #d6f6ff;
        font-family: 'Source Sans 3', 'Manrope', sans-serif;
    }
    QWidget {
        background-color: rgba(3, 16, 26, 0.95);
        background-image:
            radial-gradient(circle at 80% 15%, rgba(20, 120, 143, 0.2), transparent 40%),
            radial-gradient(circle at 20% 70%, rgba(222, 201, 174, 0.2), transparent 50%);
        color: #d6f6ff;
        font-family: 'Source Sans 3', 'Manrope', sans-serif;
    }
    QFrame, QScrollArea, QSplitter, QStackedWidget, QTabWidget::pane { background-color: rgba(3, 16, 26, 0.95); }
    QMainWindow#mainWindow { border: 1px solid rgba(8, 46, 56, 0.6); }
    QGroupBox {
        background-color: rgba(11, 31, 41, 0.85);
        border: 1px solid rgba(15, 118, 110, 0.3);
        border-radius: 16px;
        margin-top: 1em;
        padding-top: 14px;
    }
    QGroupBox::title {
        color: #d6f6ff;
        padding: 3px 12px;
        font-weight: 700;
        background-color: rgba(9, 32, 42, 0.9);
        border-radius: 12px 12px 0 0;
        border: 1px solid rgba(15, 118, 110, 0.6);
        border-bottom: none;
    }
    QPushButton {
        background-color: rgba(15, 118, 110, 0.15);
        border: 1px solid rgba(78, 162, 194, 0.65);
        border-radius: 999px;
        padding: 8px 18px;
        color: #d6f6ff;
        font-weight: 600;
    }
    QPushButton:hover {
        background-color: rgba(15, 118, 110, 0.35);
    }
    QPushButton:pressed {
    }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {
        background-color: rgba(4, 15, 20, 0.8);
        border: 1px solid rgba(15, 118, 110, 0.5);
        border-radius: 10px;
        padding: 6px 12px;
        color: #E0FFFF;
    }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #22d3ee;
        background-color: rgba(8, 25, 34, 0.95);
    }
    QListWidget, QTreeWidget, QTreeView, QTableWidget, QTableView {
        background-color: rgba(5, 18, 24, 0.95);
        border: 1px solid rgba(15, 118, 110, 0.35);
        border-radius: 12px;
        color: #d6f6ff;
    }
    QHeaderView::section {
        background-color: rgba(8, 28, 38, 0.9);
        border: 1px solid rgba(15, 118, 110, 0.35);
        color: #b8ecff;
        padding: 6px;
        font-weight: 600;
    }
    QTabWidget::pane { border: 1px solid rgba(15, 118, 110, 0.3); background-color: rgba(3, 18, 24, 0.92); border-radius: 14px; }
    QTabBar::tab {
        background: rgba(34, 35, 46, 0.9);
        border: 1px solid rgba(15, 118, 110, 0.45);
        padding: 8px 14px;
        border-radius: 10px;
        color: #d6f6ff;
        font-weight: 600;
    }
    QTabBar::tab:selected {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #0f5c68, stop:1 #0b3942);
        color: #ffffff;
        border-color: rgba(30, 150, 179, 0.8);
    }
    QScrollBar:vertical { background: rgba(0, 0, 0, 0.15); width: 8px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: rgba(15, 118, 110, 0.8); border-radius: 4px; }
    QScrollBar::handle:vertical:hover { background: rgba(59, 130, 246, 0.8); }
    QScrollBar::corner { background: transparent; }
    QMenu { background-color: rgba(3, 18, 24, 0.9); border: 1px solid rgba(15, 118, 110, 0.6); color: #d6f6ff; }
    QToolTip { background-color: rgba(15, 118, 110, 0.9); color: #03121a; border-radius: 6px; padding: 6px; }
    QFrame#statsCard { background: rgba(7, 26, 37, 0.9); border-radius: 18px; border: 1px solid rgba(15, 118, 110, 0.6); }
    QLabel#statsCardTitle { color: #9eeffd; }
    QLabel#statsCardValue { color: #f0f9ff; }
    QLabel#statsCardSubtitle { color: #9eeffd; }
    """

    KANBAN_LIGHT = """
    #kanbanColumn {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #FBFAF7, stop:0.55 #F3EFE9, stop:1 #ECE5DB);
        border: 1px solid #E5DED3;
        border-radius: 12px;
    }
    #kanbanColumn[kanbanKey="todo"] { border-top: 4px solid #0F766E; }
    #kanbanColumn[kanbanKey="prog"] { border-top: 4px solid #D97706; }
    #kanbanColumn[kanbanKey="done"] { border-top: 4px solid #1B8A5A; }
    #kanbanHeader {
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.2px;
        color: #5A544D;
        padding: 8px 10px 6px 10px;
    }
    #kanbanHeader[kanbanKey="todo"] { color: #0B5F57; }
    #kanbanHeader[kanbanKey="prog"] { color: #B45309; }
    #kanbanHeader[kanbanKey="done"] { color: #166B45; }
    #taskCard {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E5DED3;
        border-bottom: 3px solid #D7CEC2;
    }
    #taskCard:hover {
        border-color: #0F766E;
        background-color: #FFFEFD;
    }
    #taskCard[selected="true"] {
        border: 2px solid #0F766E;
        border-bottom: 3px solid #0B5F57;
        background-color: #FFFEFD;
    }
    #kanbanAddBtn { background-color: #FFFFFF; color: #5A544D; text-align: left; border: 1px dashed #D3CABE; padding: 8px 10px; border-radius: 8px; }
    #kanbanAddBtn:hover { background-color: #F1F7F4; color: #0B5F57; border-color: #0F766E; }
    KanbanList, QListWidget#kanbanList { background-color: transparent; border: none; outline: none; padding: 6px; }
    QListWidget#kanbanList::item { border: none; margin: 0px; padding: 0px; color: transparent; }
    QListWidget#kanbanList::item:selected { background: transparent; border: none; color: transparent; }
    QListWidget#kanbanList::item:hover { background: transparent; color: transparent; }
    """

    KANBAN_DARK = """
    #kanbanColumn {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #222831, stop:0.6 #1E242C, stop:1 #1A1F26);
        border: 1px solid #2B313A;
        border-radius: 12px;
    }
    #kanbanColumn[kanbanKey="todo"] { border-top: 4px solid #3B74D6; }
    #kanbanColumn[kanbanKey="prog"] { border-top: 4px solid #E67E22; }
    #kanbanColumn[kanbanKey="done"] { border-top: 4px solid #2E8B57; }
    #kanbanHeader {
        font-size: 11px;
        font-weight: 800;
        letter-spacing: 1.2px;
        color: #AEB6C2;
        padding: 8px 8px 6px 8px;
    }
    #kanbanHeader[kanbanKey="todo"] { color: #8AB4FF; }
    #kanbanHeader[kanbanKey="prog"] { color: #F5A15B; }
    #kanbanHeader[kanbanKey="done"] { color: #7ED2A1; }
    #taskCard {
        background-color: #2B313A;
        border-radius: 12px;
        border: 1px solid #3A424D;
        border-bottom: 3px solid #1B1F26;
    }
    #taskCard:hover { border-color: #3B74D6; background-color: #2E3440; }
    #taskCard[selected="true"] {
        border: 2px solid #3B74D6;
        border-bottom: 3px solid #6CA0FF;
        background-color: #2F3640;
    }
    #kanbanAddBtn { background-color: #232831; color: #AEB6C2; text-align: left; border: 1px dashed #3A424D; padding: 8px 10px; border-radius: 8px; }
    #kanbanAddBtn:hover { background-color: #2B313A; color: #E9EEF7; border-color: #3B74D6; }
    KanbanList, QListWidget#kanbanList { background-color: transparent; border: none; outline: none; padding: 6px; }
    QListWidget#kanbanList::item { border: none; margin: 0px; padding: 0px; color: transparent; }
    QListWidget#kanbanList::item:selected { background: transparent; border: none; color: transparent; }
    QListWidget#kanbanList::item:hover { background: transparent; color: transparent; }
    """

    HEADER_LIGHT = """
    #tabHeader {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #F8F5F0, stop:1 #F1ECE6);
    }
    #tabHeaderTitle { color: #2C2A27; font-weight: 800; font-size: 14px; }
    #tabHeaderSubtitle { color: #6B7280; font-size: 12px; }
    #tabHeaderStatus {
        color: #0B5F57;
        background: #E7F5F1;
        border: 1px solid #C9E8DF;
        border-radius: 8px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 700;
        max-width: 220px;
    }
    #tabHeaderDivider { background: #E5DED3; }
    """

    HEADER_DARK = """
    #tabHeader {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #1E242C, stop:1 #1B2027);
    }
    #tabHeaderTitle { color: #E9EEF7; font-weight: 800; font-size: 14px; }
    #tabHeaderSubtitle { color: #AEB6C2; font-size: 12px; }
    #tabHeaderStatus {
        color: #CDE7FF;
        background: #1E2A36;
        border: 1px solid #2B3A4A;
        border-radius: 8px;
        padding: 2px 8px;
        font-size: 11px;
        font-weight: 700;
        max-width: 220px;
    }
    #tabHeaderDivider { background: #2B313A; }
    """

    CHECKLIST_LIGHT = """
    #checklistRoot {
        background: transparent;
    }
    #checklistHero {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(248,221,176,0.8), stop:1 rgba(255,255,255,0.7));
        border-radius: 18px;
        border: 1px solid #f3e1cf;
        padding: 18px 20px;
    }
    #checklistTitle {
        color: #7c4d17;
        font-weight: 800;
        font-size: 18px;
        letter-spacing: 0.4px;
    }
    #checklistSummary {
        color: #5c4a3b;
        font-weight: 600;
    }
    #checklistSummaryDesc {
        color: #87603f;
        font-size: 12px;
    }
    #checklistProgress {
        background: rgba(251,233,208,0.7);
        border-radius: 10px;
        border: none;
        height: 16px;
    }
    #checklistProgress::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #f97316, stop:1 #facc15);
        border-radius: 8px;
    }
    #checklistHero QPushButton#checklistHeaderBtn {
        background-color: rgba(255,255,255,0.9);
        border: 1px solid #f1d8b3;
        border-radius: 10px;
        padding: 6px 14px;
        color: #7c4d17;
        font-weight: 600;
    }
    #checklistHero QPushButton#checklistHeaderBtn:hover {
        border-color: #f97316;
        background-color: rgba(249,115,22,0.08);
    }
    QFrame#checklistCard {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #ffffff, stop:1 #fdf4e3);
        border: 1px solid #f3e1cf;
        border-radius: 18px;
    }
    QFrame#checklistCardHeader {
        background: rgba(255,255,255,0.8);
        border-bottom: 1px solid #f5dfc3;
        border-top-left-radius: 18px;
        border-top-right-radius: 18px;
    }
    #checklistName {
        background: transparent;
        border: none;
        color: #7c4d17;
        font-weight: 700;
        padding: 4px 2px;
    }
    #checklistDesc {
        background: #fff9f2;
        border: 1px solid #f5dfc3;
        border-radius: 12px;
        padding: 8px 10px;
        color: #5c4a3b;
    }
    #checklistSummaryLabel { color: #837258; font-weight: 600; }
    QToolButton#checklistDeleteBtn { color: #7c4d17; }
    QToolButton#checklistDeleteBtn:hover { color: #ef4444; }
    QTableWidget#checklistTable {
        background: #fffefc;
        border: none;
        border-radius: 16px;
        gridline-color: #f3e1cf;
        color: #42312a;
        alternate-background-color: #fff8ef;
    }
    QTableWidget#checklistTable::item {
        border-bottom: 1px solid #f3e1cf;
        padding: 6px 8px;
    }
    QTableWidget#checklistTable::item:selected {
        background: rgba(249,115,22,0.12);
        color: #7c4d17;
    }
    QHeaderView::section {
        background: #fff6ee;
        border: none;
        padding: 8px 10px;
        color: #7c4d17;
        font-weight: 600;
    }
    """

    CHECKLIST_DARK = """
    #checklistRoot { background: #0c1118; }
    #checklistHero {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
            stop:0 rgba(10, 27, 39, 0.9), stop:1 rgba(14, 52, 68, 0.8));
        border-radius: 18px;
        border: 1px solid rgba(14, 165, 233, 0.35);
        padding: 18px 20px;
    }
    #checklistTitle {
        color: #f4f7fb;
        font-weight: 800;
        font-size: 18px;
        letter-spacing: 0.45px;
    }
    #checklistSummary {
        color: #bbdff6;
        font-weight: 600;
    }
    #checklistSummaryDesc {
        color: #9ac5ea;
        font-size: 12px;
    }
    #checklistProgress {
        background: rgba(255,255,255,0.08);
        border-radius: 10px;
        border: none;
        height: 16px;
    }
    #checklistProgress::chunk {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
            stop:0 #14b8a6, stop:1 #0ea5e9);
        border-radius: 8px;
    }
    #checklistHero QPushButton#checklistHeaderBtn {
        background-color: rgba(255,255,255,0.1);
        border: 1px solid rgba(14, 165, 233, 0.55);
        border-radius: 10px;
        padding: 6px 14px;
        color: #e2f5ff;
        font-weight: 600;
    }
    #checklistHero QPushButton#checklistHeaderBtn:hover {
        border-color: #7dd3fc;
        background-color: rgba(125,211,252,0.15);
        color: #f0fbff;
    }
    QFrame#checklistCard {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #0c1118, stop:1 #05070b);
        border: 1px solid rgba(255,255,255,0.05);
        border-radius: 18px;
    }
    QFrame#checklistCardHeader {
        background: rgba(255,255,255,0.02);
        border-bottom: 1px solid rgba(255,255,255,0.04);
        border-top-left-radius: 18px;
        border-top-right-radius: 18px;
    }
    #checklistName {
        background: transparent;
        border: none;
        color: #f4f7fb;
        font-weight: 700;
        padding: 4px 2px;
    }
    #checklistDesc {
        background: rgba(255,255,255,0.04);
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 12px;
        padding: 8px 10px;
        color: #cbd5ff;
    }
    #checklistSummaryLabel { color: #d1d9e6; font-weight: 600; }
    QToolButton#checklistDeleteBtn { color: #fefefe; }
    QToolButton#checklistDeleteBtn:hover { color: #fccaca; }
    QTableWidget#checklistTable {
        background: #05070b;
        border: 1px solid rgba(255,255,255,0.03);
        border-radius: 16px;
        gridline-color: rgba(255,255,255,0.08);
        color: #f8fafc;
        alternate-background-color: rgba(255,255,255,0.02);
    }
    QTableWidget#checklistTable::item {
        border-bottom: 1px solid rgba(255,255,255,0.04);
        padding: 6px 8px;
        background: transparent;
    }
    QTableWidget#checklistTable::item:selected {
        background: rgba(14,165,233,0.2);
        color: #f0fbff;
    }
    QHeaderView::section {
        background: rgba(5, 7, 11, 0.85);
        border: none;
        padding: 8px 10px;
        color: #94a3b8;
        font-weight: 600;
    }
    """

    TYPOGRAPHY = """
    QWidget, QMainWindow { font-family: 'Source Sans 3', 'Manrope', sans-serif; font-size: 12pt; }
    QLabel, QPushButton, QLineEdit, QTextEdit, QSpinBox, QComboBox, QTableWidget, QTreeView { font-size: 12pt; }
    QLabel#tabHeaderTitle, QLabel#statsCardTitle, QLabel#heroStatus { font-size: 18pt; letter-spacing: 0.4px; font-weight: 700; }
    QLabel#tabHeaderSubtitle { font-size: 14pt; letter-spacing: 0.2px; font-weight: 500; }
    QLabel#tabHeaderStatus { font-size: 12pt; font-weight: 600; letter-spacing: 0.3px; }
    QGroupBox::title { font-size: 14pt; font-weight: 700; letter-spacing: 0.3px; }
    QPushButton { padding: 8px 14px; text-align: left; font-size: 12pt; font-weight: 600; }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit { font-size: 12pt; }
    QHeaderView::section { font-size: 12pt; font-weight: 600; }
    /* Uniform tab font size to follow the scale */
    QTabBar::tab { font-size: 12pt; font-weight: 600; min-width: 110px; max-width: 180px; }
    QTabWidget[stretchTabs="true"] QTabBar {
        min-width: 0px;
        max-width: 16777215px;
    }
    QTabWidget[stretchTabs="true"] QTabBar::tab {
        max-width: 16777215px;
    }
    QTabWidget[stretchTabs="true"] QTabBar::tab:selected {
        max-width: 16777215px;
    }
    QTabWidget[stretchTabs="true"] QTabBar::tab:hover {
        max-width: 16777215px;
    }
    """

    BUTTONS_LIGHT = """
    QPushButton#btnPrimary {
        background-color: #0F766E;
        color: #FFFFFF;
        border-radius: 999px;
        padding: 10px 22px;
    }
    QPushButton#btnPrimary:hover {
        background-color: #0B5F57;
    }
    QPushButton#btnSecondary {
        background-color: rgba(255, 255, 255, 0.9);
        color: #2C2A27;
        border-radius: 999px;
        padding: 8px 18px;
        border: 1px solid rgba(15, 118, 110, 0.25);
    }
    QPushButton#btnSecondary:hover {
        background-color: #F2F7F4;
        color: #0B5F57;
    }
    QPushButton#btnGhost {
        background-color: transparent;
        color: #0F766E;
        border: 1px solid transparent;
    }
    QPushButton#btnGhost:hover {
        background-color: rgba(15, 118, 110, 0.08);
        border-color: rgba(15, 118, 110, 0.35);
        color: #0F766E;
    }
    QPushButton#btnGhost:focus { border-color: #0F766E; }
    """

    BUTTONS_DARK = """
    QPushButton#btnPrimary {
        background-color: #3B74D6;
        color: #FFFFFF;
        border: 1px solid #2F5EB0;
        font-weight: 700;
    }
    QPushButton#btnPrimary:hover { background-color: #2F5EB0; }
    QPushButton#btnPrimary:focus { border-color: #3B74D6; }
    QPushButton#btnSecondary {
        background-color: #2B313A;
        color: #E9EEF7;
        border: 1px solid #3A424D;
        font-weight: 600;
    }
    QPushButton#btnSecondary:hover { background-color: #343B45; border-color: #3B74D6; }
    QPushButton#btnSecondary:focus { border-color: #3B74D6; }
    QPushButton#btnGhost {
        background-color: transparent;
        color: #E9EEF7;
        border: 1px solid transparent;
    }
    QPushButton#btnGhost:hover { background-color: #232831; border-color: #2B313A; }
    QPushButton#btnGhost:focus { border-color: #3B74D6; }
    """

    PROJECT_PANELS = """
    QWidget#projectPanel[projectTheme="Dark"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #0b1220, stop:1 #1b2435);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        padding: 20px;
        margin: 16px 0;
    }
    QWidget#projectPanel[projectTheme="Light"] {
        background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #f4f6fb, stop:1 #ffffff);
        border-radius: 24px;
        border: 1px solid rgba(15, 23, 42, 0.12);
        padding: 20px;
        margin: 16px 0;
    }
    QWidget#projectPanel QSplitter::handle {
        background: rgba(255, 255, 255, 0.18);
        width: 8px;
        border-radius: 4px;
        margin: 0 10px;
    }
    QWidget#projectPanel[projectTheme="Dark"] QFrame#projectPanelSection,
    QWidget#projectPanel[projectTheme="Dark"] QGroupBox#projectPanelSection {
        background: rgba(16, 24, 35, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 14px;
        padding: 14px;
    }
    QWidget#projectPanel[projectTheme="Light"] QFrame#projectPanelSection,
    QWidget#projectPanel[projectTheme="Light"] QGroupBox#projectPanelSection {
        background: rgba(255, 255, 255, 0.9);
        border: 1px solid rgba(15, 23, 42, 0.1);
        border-radius: 14px;
        padding: 14px;
    }
    QWidget#projectPanelSection QTableWidget, QWidget#projectPanelSection QTableView {
        background: transparent;
        border: none;
    }
    """

    NAV_BLOCK = """
    QTabBar#mainTabBar {
        min-width: 72px;
        max-width: 72px;
    }
    QTabBar#mainTabBar::tab {
        border: none;
        margin: 4px 6px;
        padding: 10px 6px;
    }
    """

    THEMES = {
        "Light": LIGHT,
        "Dark": DARK,
        "Teal Sand": TEAL_SAND,
        "Teal Sand Dark": TEAL_SAND_DARK,
    }

    DARK_THEME_NAMES = {"Dark", "Teal Sand Dark"}

    @staticmethod
    def get_theme_names():
        return list(Styles.THEMES.keys())

    @staticmethod
    def apply_theme(app, theme_name, scale_percent=100, font_family=None):
        try:
            scale_percent = float(scale_percent)
        except Exception:
            scale_percent = 100.0
        # Guard against invalid imported settings (e.g. -1) that cause Qt font warnings.
        scale_percent = max(50.0, min(300.0, scale_percent))

        base = Styles.THEMES.get(theme_name, Styles.LIGHT)

        dark = theme_name in Styles.DARK_THEME_NAMES
        kanban = Styles.KANBAN_DARK if dark else Styles.KANBAN_LIGHT
        header = Styles.HEADER_DARK if dark else Styles.HEADER_LIGHT
        checklist = Styles.CHECKLIST_DARK if dark else Styles.CHECKLIST_LIGHT
        typography = Styles.TYPOGRAPHY
        nav_block = Styles.NAV_BLOCK
        project_panels = Styles.PROJECT_PANELS
        buttons = Styles.BUTTONS_DARK if dark else Styles.BUTTONS_LIGHT
        if font_family:
            # Inject chosen font into CSS so style sheets don't override QApplication font
            base = base.replace(
                "font-family: 'Source Sans 3', 'IBM Plex Sans', 'Segoe UI', sans-serif;",
                f"font-family: '{font_family}', 'IBM Plex Sans', 'Segoe UI', sans-serif;"
            )
            base = base.replace("font-family: 'Segoe UI', 'Roboto', sans-serif;", f"font-family: '{font_family}', 'Roboto', sans-serif;")
            base = base.replace("font-family: 'Segoe UI', sans-serif;", f"font-family: '{font_family}', sans-serif;")
            base = base.replace("font-family: 'Segoe UI', sans-serif", f"font-family: '{font_family}', sans-serif")
        app.setStyleSheet(base + typography + nav_block + project_panels + buttons + header + kanban + checklist)
            
        # Apply UI Scale via Font Size and optional font family
        font = app.font()
        if font_family:
            font.setFamily(font_family)
        base_size = 9  # Standard base point size
        font.setPointSizeF(base_size * (scale_percent / 100.0))
        app.setFont(font)

