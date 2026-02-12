import sys
import os
import traceback

from PySide6.QtWidgets import QApplication, QMessageBox, QSplashScreen, QStyle
from PySide6.QtCore import QLockFile, QDir, Qt, qInstallMessageHandler
from PySide6.QtGui import QPixmap, QPainter, QColor, QFont

from backend.logic import AppLogic
from logger import CrashHandler
from ui.core.main_window import MainWindow
from ui.resources.styles import Styles


def _install_qt_font_warning_trace():
    if os.getenv("QT_DEBUG_FONT_WARN_TRACE", "").lower() not in {"1", "true", "yes", "on"}:
        return

    def _handler(msg_type, context, message):  # pragma: no cover (debug hook)
        text = str(message)
        if "QFont::setPointSize" in text:
            print(text, file=sys.stderr)
            traceback.print_stack(limit=16, file=sys.stderr)

    qInstallMessageHandler(_handler)


def main():
    CrashHandler()
    _install_qt_font_warning_trace()

    app = QApplication(sys.argv)
    # Ensure default font has a valid point size to avoid Qt warnings
    app_font = app.font()
    if app_font.pointSize() <= 0 and app_font.pointSizeF() <= 0:
        app_font.setPointSize(10)
        app.setFont(app_font)
    try:
        from PySide6 import QtWebEngineCore
        profile = QtWebEngineCore.QWebEngineProfile.defaultProfile()
        profile.setHttpCacheType(QtWebEngineCore.QWebEngineProfile.HttpCacheType.MemoryHttpCache)
        profile.setPersistentCookiesPolicy(
            QtWebEngineCore.QWebEngineProfile.PersistentCookiesPolicy.NoPersistentCookies
        )
    except ImportError:
        # Handle case where QtWebEngine is not installed
        pass
    app.setApplicationName("KiCad Project Manager")
    app.setOrganizationName("KiCad")
    
    # Set a default icon (Computer Icon) for the taskbar/window title
    app.setWindowIcon(app.style().standardIcon(QStyle.SP_ComputerIcon))

    # Splash Screen
    splash_pix = QPixmap(400, 250)
    splash_pix.fill(QColor("#18181b"))  # Dark background matching the app theme
    painter = QPainter(splash_pix)
    painter.setPen(QColor("#ffffff"))
    painter.setFont(QFont("Segoe UI", 24, QFont.Bold))
    painter.drawText(splash_pix.rect(), Qt.AlignCenter, "KiCad\nProject Manager")
    painter.end()
    splash = QSplashScreen(splash_pix)
    splash.show()
    app.processEvents()

    # Single Instance Check
    lock_file = QLockFile(QDir.temp().filePath("kicad_project_manager.lock"))
    lock_file.setStaleLockTime(0) # Clear lock if previous instance crashed
    if not lock_file.tryLock(100):
        QMessageBox.warning(None, "Already Running", "The application is already running.")
        sys.exit(1)

    logic = AppLogic()

    theme = logic.settings.get("theme", "Light")
    scale = logic.settings.get("ui_scale", 100)
    font = logic.settings.get("ui_font", None)
    Styles.apply_theme(app, theme, scale, font_family=font)

    window = MainWindow(logic)
    window.show()
    splash.finish(window)
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
