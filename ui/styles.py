class Styles:
    LIGHT = """
    /* Linen Light Theme */
    QMainWindow {
        background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #F8F5F0, stop:1 #EEF2F7);
        color: #2C2A27;
        font-family: 'Source Sans 3', 'IBM Plex Sans', 'Segoe UI', sans-serif;
    }
    QWidget {
        background-color: #F7F4EF;
        color: #2C2A27;
        font-family: 'Source Sans 3', 'IBM Plex Sans', 'Segoe UI', sans-serif;
    }
    QMainWindow#mainWindow { border: 1px solid #D7CFC4; }
    
    QGroupBox {
        background-color: #FFFFFF;
        border: 1px solid #E3DBD0;
        border-radius: 12px;
        margin-top: 1.1em;
        padding-top: 14px;
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
        border: 1px solid #D8D0C5;
        border-radius: 8px;
        padding: 6px 12px;
        color: #2C2A27;
        font-weight: 600;
        text-align: left;
    }
    QPushButton:hover { background-color: #F2F7F4; border-color: #0F766E; color: #0B5F57; }
    QPushButton:pressed { background-color: #0F766E; color: #FFFFFF; border-color: #0B5F57; }
    QPushButton:default { background-color: #0F766E; color: #FFFFFF; border-color: #0B5F57; }
    
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
        padding: 5px 6px;
        color: #2C2A27;
        selection-background-color: #C7F0E4;
        selection-color: #0B5F57;
    }
    QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #0F766E;
        background-color: #FFFEFD;
    }
    QPushButton:focus { border-color: #0F766E; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #0F766E; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #0F766E; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #0F766E; }
    
    QListWidget, QTreeWidget, QTableWidget {
        background-color: #FFFFFF;
        border: 1px solid #E2DBD0;
        border-radius: 8px;
        color: #2C2A27;
        alternate-background-color: #FAF7F2;
    }
    QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
        background-color: #DDF1EC;
        color: #0B5F57;
        border: 1px solid #0F766E;
    }
    QListWidget::item:hover, QTreeWidget::item:hover, QTableWidget::item:hover {
        background-color: #F2F7F4;
    }
    
    QHeaderView::section {
        background-color: #F1ECE6;
        padding: 6px;
        border: none;
        border-bottom: 1px solid #D8D0C5;
        font-weight: 600;
        color: #5A544D;
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
    
    QScrollBar:vertical { background: #EEE7DE; width: 8px; margin: 0px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #CBBFB0; min-height: 24px; border-radius: 4px; margin: 2px; border: 1px solid #D8D0C5; }
    QScrollBar::handle:vertical:hover { background: #B8AFA3; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    QLabel#formHelp { color: #6B7280; font-size: 11px; }

    /* Kanban Specific - Light */
    #kanbanColumn {
        background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
            stop:0 #F9F7F3, stop:1 #F1ECE6);
        border: 1px solid #E2DBD0;
        border-radius: 12px;
    }
    #kanbanHeader {
        font-weight: 700;
        color: #5A544D;
        font-size: 12px;
        padding: 6px 8px 4px 8px;
    }
    #taskCard {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E2DBD0;
        border-bottom: 2px solid #D6CEC4;
    }
    #taskCard:hover { border-color: #0F766E; background-color: #FFFEFD; }
    #taskCard[selected="true"] { border: 2px solid #0F766E; background-color: #FFFEFD; }
    #kanbanAddBtn { background-color: #FFFFFF; color: #5A544D; text-align: left; border: 1px dashed #D3CABE; padding: 8px 10px; border-radius: 8px; }
    #kanbanAddBtn:hover { background-color: #F1F7F4; color: #0B5F57; border-color: #0F766E; }
    KanbanList { background-color: transparent; border: none; outline: none; }
    QListWidget#kanbanList::item { border: none; margin: 0px; padding: 0px; }
    QListWidget#kanbanList::item:selected { background: transparent; border: none; }
    QListWidget#kanbanList::item:hover { background: transparent; }
    #emptyStateTitle { color: #2C2A27; font-weight: 700; font-size: 13px; }
    #emptyStateBody { color: #6B7280; font-size: 12px; }
    #emptyStateAction { padding: 6px 12px; }
    QFrame#statsCard { background-color: #FFFFFF; border: 1px solid #E2DBD0; border-radius: 12px; }
    QLabel#statsCardTitle { color: #6B7280; font-size: 11px; letter-spacing: 0.2px; }
    QLabel#statsCardValue { color: #1F2937; font-size: 20px; font-weight: 700; }
    QLabel#statsCardSubtitle { color: #6B7280; font-size: 11px; }
    """

    DARK = """
    /* Modern Dark Theme (VS Code Inspired) */
    QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E1E1E, stop:1 #2C2C2C); color: #D4D4D4; font-family: 'Segoe UI', 'Roboto', sans-serif; }
    QWidget { background-color: #1E1E1E; color: #D4D4D4; font-family: 'Segoe UI', 'Roboto', sans-serif; }
    
    QGroupBox {
        background-color: #252526;
        border: 1px solid #3E3E42;
        border-radius: 12px;
        margin-top: 1em;
        padding-top: 12px;
    }
    QGroupBox::title {
        subcontrol-origin: margin;
        subcontrol-position: top left;
        padding: 0 8px;
        color: #569CD6;
        font-weight: bold;
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
        padding: 5px;
        color: #D4D4D4;
        selection-background-color: #2D4A6B;
        selection-color: #E9EEF7;
    }
    QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus {
        border: 1px solid #569CD6;
        background-color: #2D2D30;
    }
    QPushButton:focus { border-color: #569CD6; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #569CD6; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #569CD6; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #569CD6; }
    
    QListWidget, QTreeWidget, QTableWidget {
        background-color: #252526;
        border: 1px solid #3E3E42;
        border-radius: 6px;
        color: #D4D4D4;
        alternate-background-color: #2D2D30;
    }
    QListWidget::item:selected, QTreeWidget::item:selected, QTableWidget::item:selected {
        background-color: #094771;
        color: #FFFFFF;
        border: none;
    }
    QListWidget::item:hover, QTreeWidget::item:hover { background-color: #2A2D2E; }
    QLabel#formHelp { color: #AEB6C2; font-size: 11px; }
    QFrame#statsCard { background-color: #2B313A; border: 1px solid #3A424D; border-radius: 12px; }
    QLabel#statsCardTitle { color: #AEB6C2; font-size: 11px; letter-spacing: 0.2px; }
    QLabel#statsCardValue { color: #E9EEF7; font-size: 20px; font-weight: 700; }
    QLabel#statsCardSubtitle { color: #AEB6C2; font-size: 11px; }
    
    QHeaderView::section {
        background-color: #252526;
        color: #CCCCCC;
        padding: 6px;
        border: none;
        border-right: 1px solid #3E3E42;
        border-bottom: 1px solid #3E3E42;
        font-weight: bold;
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
        font-weight: bold;
        min-height: 30px;
        min-width: 110px;
        max-width: 180px;
    }
    
    QScrollBar:vertical { background: #1E1E1E; width: 8px; margin: 0px; border-radius: 4px; }
    QScrollBar::handle:vertical { background: #424242; min-height: 24px; border-radius: 4px; margin: 2px; }
    QScrollBar::handle:vertical:hover { background: #686868; }
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
    
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
    #taskCard[selected="true"] { border: 2px solid #569CD6; background-color: #2D3136; }
    #kanbanAddBtn { background-color: transparent; color: #AAAAAA; text-align: left; border: none; padding: 8px; border-radius: 4px; }
    #kanbanAddBtn:hover { background-color: #3E3E42; color: #FFFFFF; }
    KanbanList { background-color: transparent; border: none; outline: none; }
    QListWidget#kanbanList::item { border: none; margin: 0px; padding: 0px; }
    QListWidget#kanbanList::item:selected { background: transparent; border: none; }
    QListWidget#kanbanList::item:hover { background: transparent; }
    #emptyStateTitle { color: #E9EEF7; font-weight: 700; font-size: 13px; }
    #emptyStateBody { color: #AEB6C2; font-size: 12px; }
    #emptyStateAction { padding: 6px 12px; }
    """

    BLUE = """
    QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #eef2f5, stop:1 #E4E8EB); color: #2c3e50; font-family: 'Segoe UI', sans-serif; }
    QWidget { background-color: #eef2f5; color: #2c3e50; font-family: 'Segoe UI', sans-serif; }
    QGroupBox { font-weight: bold; border: 1px solid #bdc3c7; border-radius: 12px; margin-top: 12px; padding-top: 10px; background-color: #fff; }
    QGroupBox::title { color: #2980b9; }
    QPushButton { text-align: left; background-color: #ecf0f1; border: 1px solid #bdc3c7; border-radius: 8px; padding: 6px 12px; color: #2c3e50; }
    QPushButton:hover { background-color: #d5dbdb; }
    QLineEdit, QTextEdit, QPlainTextEdit { background-color: #fff; border: 1px solid #bdc3c7; border-radius: 8px; padding: 4px; color: #2c3e50; }
    QListWidget, QTreeWidget, QTableWidget { background-color: #fff; border: 1px solid #bdc3c7; border-radius: 4px; color: #2c3e50; }
    QHeaderView::section { background-color: #34495e; padding: 4px; border: 1px solid #2c3e50; font-weight: bold; color: #ecf0f1; }
    QTabBar::tab { background: #bdc3c7; border: 1px solid #95a5a6; padding: 8px 12px; color: #2c3e50;  min-width: 110px; max-width: 180px; }
    QTabBar::tab:selected { background: #fff; border-bottom-color: #fff; font-weight: bold; color: #2980b9;  min-width: 110px; max-width: 180px; }
    QPushButton:focus { border-color: #2980b9; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #2980b9; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #2980b9; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #2980b9; }
    QScrollBar:vertical { border: none; background: #eef2f5; width: 8px; margin: 0px; border-radius: 4px; } QScrollBar::handle:vertical { background: #34495e; min-height: 24px; border-radius: 4px; }
    """

    HIGH_CONTRAST = """
    QMainWindow, QWidget { background-color: #000; color: #fff; font-family: 'Segoe UI', sans-serif; }
    QGroupBox { border: 2px solid #fff; background-color: #000; color: #fff; }
    QPushButton { padding: 6px 12px; text-align: left; background-color: #000; border: 2px solid #fff; color: #fff; font-weight: bold; }
    QPushButton:hover { background-color: #333; }
    QLineEdit, QTextEdit { background-color: #000; border: 2px solid #fff; color: #fff; }
    QListWidget, QTreeWidget { background-color: #000; border: 2px solid #fff; color: #fff; }
    QHeaderView::section { background-color: #000; border: 2px solid #fff; color: #fff; }
    QTabBar::tab { background: #000; border: 2px solid #fff; color: #fff;  min-width: 110px; max-width: 180px; }
    QTabBar::tab:selected { background: #fff; color: #000;  min-width: 110px; max-width: 180px; }
    QPushButton:focus { border-color: #FFFFFF; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 2px solid #FFFFFF; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 2px solid #FFFFFF; }
    QAbstractItemView::item:focus { outline: none; border: 2px solid #FFFFFF; }
    """

    SOLARIZED_LIGHT = """
    QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #fdf6e3, stop:1 #F3ECDA); color: #657b83; font-family: 'Segoe UI', sans-serif; }
    QWidget { background-color: #fdf6e3; color: #657b83; font-family: 'Segoe UI', sans-serif; }
    QGroupBox { font-weight: bold; border: 1px solid #93a1a1; border-radius: 12px; margin-top: 12px; padding-top: 10px; background-color: #eee8d5; }
    QGroupBox::title { color: #586e75; }
    QPushButton { text-align: left; background-color: #eee8d5; border: 1px solid #93a1a1; border-radius: 8px; padding: 6px 12px; color: #657b83; }
    QPushButton:hover { background-color: #93a1a1; color: #fdf6e3; }
    QLineEdit, QTextEdit { background-color: #fdf6e3; border: 1px solid #93a1a1; color: #657b83; }
    QListWidget, QTreeWidget, QTableWidget { background-color: #fdf6e3; border: 1px solid #93a1a1; color: #657b83; alternate-background-color: #eee8d5; }
    QHeaderView::section { background-color: #eee8d5; border: 1px solid #93a1a1; color: #586e75; }
    QTabBar::tab { background: #eee8d5; border: 1px solid #93a1a1; color: #586e75; padding: 8px 12px;  min-width: 110px; max-width: 180px; }
    QTabBar::tab:selected { background: #fdf6e3; font-weight: bold;  min-width: 110px; max-width: 180px; }
    QPushButton:focus { border-color: #268bd2; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #268bd2; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #268bd2; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #268bd2; }
    """

    SOLARIZED_DARK = """
    QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #002b36, stop:1 #0F3842); color: #839496; font-family: 'Segoe UI', sans-serif; }
    QWidget { background-color: #002b36; color: #839496; font-family: 'Segoe UI', sans-serif; }
    QGroupBox { font-weight: bold; border: 1px solid #586e75; border-radius: 12px; margin-top: 12px; padding-top: 10px; background-color: #073642; }
    QGroupBox::title { color: #93a1a1; }
    QPushButton { text-align: left; background-color: #073642; border: 1px solid #586e75; border-radius: 8px; padding: 6px 12px; color: #839496; }
    QPushButton:hover { background-color: #586e75; color: #fdf6e3; }
    QLineEdit, QTextEdit { background-color: #002b36; border: 1px solid #586e75; color: #839496; }
    QListWidget, QTreeWidget, QTableWidget { background-color: #002b36; border: 1px solid #586e75; color: #839496; alternate-background-color: #073642; }
    QHeaderView::section { background-color: #073642; border: 1px solid #586e75; color: #93a1a1; }
    QTabBar::tab { background: #073642; border: 1px solid #586e75; color: #586e75; padding: 8px 12px;  min-width: 110px; max-width: 180px; }
    QTabBar::tab:selected { background: #002b36; font-weight: bold; color: #93a1a1;  min-width: 110px; max-width: 180px; }
    QPushButton:focus { border-color: #268bd2; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #268bd2; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #268bd2; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #268bd2; }
    """

    DRACULA = """
    QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #282a36, stop:1 #353742); color: #f8f8f2; font-family: 'Segoe UI', sans-serif; }
    QWidget { background-color: #282a36; color: #f8f8f2; font-family: 'Segoe UI', sans-serif; }
    QGroupBox { font-weight: bold; border: 1px solid #6272a4; border-radius: 12px; margin-top: 12px; padding-top: 10px; background-color: #44475a; }
    QGroupBox::title { color: #bd93f9; }
    QPushButton { text-align: left; background-color: #44475a; border: 1px solid #6272a4; border-radius: 8px; padding: 6px 12px; color: #f8f8f2; }
    QPushButton:hover { background-color: #6272a4; }
    QLineEdit, QTextEdit { background-color: #282a36; border: 1px solid #6272a4; color: #f8f8f2; }
    QListWidget, QTreeWidget, QTableWidget { background-color: #282a36; border: 1px solid #6272a4; color: #f8f8f2; alternate-background-color: #44475a; }
    QHeaderView::section { background-color: #44475a; border: 1px solid #6272a4; color: #8be9fd; }
    QTabBar::tab { background: #44475a; border: 1px solid #6272a4; color: #6272a4; padding: 8px 12px;  min-width: 110px; max-width: 180px; }
    QTabBar::tab:selected { background: #282a36; font-weight: bold; color: #50fa7b;  min-width: 110px; max-width: 180px; }
    QPushButton:focus { border-color: #bd93f9; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #bd93f9; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #bd93f9; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #bd93f9; }
    """

    NORD = """
    QMainWindow { background-color: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2e3440, stop:1 #3B404B); color: #d8dee9; font-family: 'Segoe UI', sans-serif; }
    QWidget { background-color: #2e3440; color: #d8dee9; font-family: 'Segoe UI', sans-serif; }
    QGroupBox { font-weight: bold; border: 1px solid #4c566a; border-radius: 12px; margin-top: 12px; padding-top: 10px; background-color: #3b4252; }
    QGroupBox::title { color: #88c0d0; }
    QPushButton { text-align: left; background-color: #3b4252; border: 1px solid #4c566a; border-radius: 8px; padding: 6px 12px; color: #d8dee9; }
    QPushButton:hover { background-color: #434c5e; }
    QLineEdit, QTextEdit { background-color: #2e3440; border: 1px solid #4c566a; color: #d8dee9; }
    QListWidget, QTreeWidget, QTableWidget { background-color: #2e3440; border: 1px solid #4c566a; color: #d8dee9; alternate-background-color: #3b4252; }
    QHeaderView::section { background-color: #3b4252; border: 1px solid #4c566a; color: #81a1c1; }
    QTabBar::tab { background: #3b4252; border: 1px solid #4c566a; color: #4c566a; padding: 8px 12px;  min-width: 110px; max-width: 180px; }
    QTabBar::tab:selected { background: #2e3440; font-weight: bold; color: #88c0d0;  min-width: 110px; max-width: 180px; }
    QPushButton:focus { border-color: #88c0d0; }
    QLineEdit:focus, QTextEdit:focus, QPlainTextEdit:focus, QSpinBox:focus, QComboBox:focus { border: 1px solid #88c0d0; }
    QListWidget:focus, QTreeWidget:focus, QTreeView:focus, QTableWidget:focus, QTableView:focus { border: 1px solid #88c0d0; }
    QAbstractItemView::item:focus { outline: none; border: 1px solid #88c0d0; }
    """

    TYPOGRAPHY = """
    QWidget, QMainWindow { font-size: 9pt; }
    QLabel { font-size: 9pt; }
    QGroupBox::title { font-size: 9pt; font-weight: 700; }
    QPushButton { padding: 6px 12px; text-align: left; font-size: 9pt; font-weight: 600; }
    QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox, QDateEdit, QTimeEdit { font-size: 9pt; }
    QHeaderView::section { font-size: 8pt; font-weight: 600; }
    /* Use point units so Qt keeps pointSize valid (avoids setPointSize(-1) warnings). */
    QTabBar::tab { font-size: 9pt; font-weight: 600;  min-width: 110px; max-width: 180px; }
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

    NAV_BLOCK = """
    QTabBar#mainTabBar {
        min-width: 96px;
        max-width: 96px;
    }
    QTabBar#mainTabBar::tab {
        border: none;
        margin: 4px 6px;
        padding: 10px 6px;
    }
    """

    BUTTONS_LIGHT = """
    QPushButton#btnPrimary { background-color: #0F766E; color: #FFFFFF; border: 1px solid #0B5F57; font-weight: 700; }
    QPushButton#btnPrimary:hover { background-color: #0B5F57; }
    QPushButton#btnPrimary:focus { border-color: #0B5F57; }
    QPushButton#btnSecondary { background-color: #FFFFFF; color: #2C2A27; border: 1px solid #D8D0C5; font-weight: 600; }
    QPushButton#btnSecondary:hover { background-color: #F2F7F4; border-color: #0F766E; color: #0B5F57; }
    QPushButton#btnSecondary:focus { border-color: #0F766E; }
    QPushButton#btnGhost { background-color: transparent; color: #2C2A27; border: 1px solid transparent; }
    QPushButton#btnGhost:hover { background-color: #F5F1EB; border-color: #E2DBD0; }
    QPushButton#btnGhost:focus { border-color: #0F766E; }
    """

    BUTTONS_DARK = """
    QPushButton#btnPrimary { background-color: #3B74D6; color: #FFFFFF; border: 1px solid #2F5EB0; font-weight: 700; }
    QPushButton#btnPrimary:hover { background-color: #2F5EB0; }
    QPushButton#btnPrimary:focus { border-color: #3B74D6; }
    QPushButton#btnSecondary { background-color: #2B313A; color: #E9EEF7; border: 1px solid #3A424D; font-weight: 600; }
    QPushButton#btnSecondary:hover { background-color: #343B45; border-color: #3B74D6; }
    QPushButton#btnSecondary:focus { border-color: #3B74D6; }
    QPushButton#btnGhost { background-color: transparent; color: #E9EEF7; border: 1px solid transparent; }
    QPushButton#btnGhost:hover { background-color: #232831; border-color: #2B313A; }
    QPushButton#btnGhost:focus { border-color: #3B74D6; }
    """
    
    @staticmethod
    def apply_theme(app, theme_name, scale_percent=100):
        try:
            scale_percent = float(scale_percent)
        except Exception:
            scale_percent = 100.0
        # Guard against invalid imported settings (e.g. -1) that cause Qt font warnings.
        scale_percent = max(50.0, min(300.0, scale_percent))

        if theme_name == "Dark":
            app.setStyleSheet(Styles.DARK + Styles.TYPOGRAPHY + Styles.NAV_BLOCK + Styles.BUTTONS_DARK)
        else:
            app.setStyleSheet(Styles.LIGHT + Styles.TYPOGRAPHY + Styles.NAV_BLOCK + Styles.BUTTONS_LIGHT)
            
        # Apply UI Scale via Font Size
        font = app.font()
        base_size = 9 # Standard base point size
        font.setPointSizeF(base_size * (scale_percent / 100.0))
        app.setFont(font)

