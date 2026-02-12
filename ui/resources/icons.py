import os
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPixmap, QPainter
from PySide6.QtSvg import QSvgRenderer

class Icons:
    # Filenames
    RELOAD = "reload.svg"
    BUG = "bug.svg"
    THEME = "theme.svg"
    SUN = "sun.svg"
    MOON = "moon.svg"
    FOLDER = "folder.svg"
    TERMINAL = "terminal.svg"
    PLUS = "plus.svg"
    TRASH = "trash.svg"
    SETTINGS = "settings.svg"
    EXTERNAL = "external.svg"
    SEARCH = "search.svg"
    GLOBE = "globe.svg"
    DOC = "doc.svg"
    PULL = "pull.svg"
    PUSH = "push.svg"
    DASHBOARD = "dashboard.svg"
    PROJECTS = "projects.svg"
    PROJECTS_MAIN = "projects_main.svg"
    LIBRARY = "library.svg"
    GIT = "git.svg"
    SAVE = "save.svg"
    EDIT = "edit.svg"
    PLAY = "play.svg"
    PIN = "pin.svg"
    NOTEBOOK = "notebook.svg"
    DOCUMENTS = "documents.svg"
    CHIP = "chip.svg"
    PCBA = "pcba.svg"
    CODE = "code.svg"
    TOOL = "tool.svg"
    MECHANICAL = "mechanical.svg"
    FAB = "fab.svg"
    CLOCK = "clock.svg"
    ARCHIVE = "archive.svg"
    SORT = "sort.svg"
    ZOOM_IN = "zoom_in.svg"
    ZOOM_OUT = "zoom_out.svg"
    RESET = "reset.svg"
    MEASURE = "measure.svg"
    WARNING = "warning.svg"
    ARROW_UP = "arrow_up.svg"
    ARROW_DOWN = "arrow_down.svg"
    ARROW_LEFT = "arrow_left.svg"
    ARROW_RIGHT = "arrow_right.svg"
    REQUIREMENTS = "requirements.svg"
    CHECKLIST = "checklist.svg"
    STATS = "stats.svg"
    BOM = "bom.svg"
    FILE_PDF = "file_pdf.svg"
    FILE_IMAGE = "file_image.svg"
    FILE_TEXT = "file_text.svg"
    FILE_CODE = "file_code.svg"
    FILE_ARCHIVE = "file_archive.svg"
    FILE_SHEET = "file_sheet.svg"
    FILE_CAD = "file_cad.svg"
    FILE_GENERIC = "file_generic.svg"

    _SVG_DATA = {}


    @staticmethod
    def _get_icon_path(svg_name: str) -> str:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.join(base_dir, "..", "..", "graphical_elements", "icons", svg_name)

    @staticmethod
    def get_icon(svg_name, color="#555555"):
        """Load an SVG file from graphical_elements/icons, replace 'currentColor' with the requested color,
        render it to a 24x24 QPixmap and return a QIcon. Returns an empty QIcon on failure.
        """
        icon_path = Icons._get_icon_path(svg_name)

        # Self-repair: Create icon file if missing or empty
        if not os.path.exists(icon_path) or os.path.getsize(icon_path) == 0:
            try:
                os.makedirs(os.path.dirname(icon_path), exist_ok=True)
                if svg_name in Icons._SVG_DATA:
                    with open(icon_path, "w", encoding="utf-8") as f:
                        f.write(Icons._SVG_DATA[svg_name])
            except Exception as e:
                print(f"Error creating icon {svg_name}: {e}")

        if not os.path.exists(icon_path):
            # File not found
            return QIcon()

        try:
            with open(icon_path, "r", encoding="utf-8") as f:
                svg_data = f.read()
        except Exception:
            return QIcon()

        if not svg_data:
            return QIcon()

        # Replace color placeholder if present
        svg_data = svg_data.replace("currentColor", color)

        pixmap = QPixmap(24, 24)
        pixmap.fill(Qt.transparent)

        renderer = QSvgRenderer(QByteArray(svg_data.encode("utf-8")))
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()

        return QIcon(pixmap)
