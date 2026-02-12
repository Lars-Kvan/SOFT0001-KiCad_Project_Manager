import sys
import traceback
import logging
import os
import platform
from datetime import datetime
from PySide6.QtWidgets import QMessageBox, QApplication

class CrashHandler:
    def __init__(self, log_dir=None, bug_log_path=None):
        # Use user's home directory to avoid permission issues
        home = os.path.expanduser("~")
        base_dir = os.path.join(home, ".kicad_project_manager")
        
        self.log_dir = log_dir if log_dir else os.path.join(base_dir, "logs")
        self.bug_log_path = bug_log_path if bug_log_path else os.path.join(base_dir, "bugs.txt")
        
        os.makedirs(self.log_dir, exist_ok=True)
        
        # Setup logging
        log_file = os.path.join(self.log_dir, f"app_{datetime.now().strftime('%Y%m%d')}.log")
        logging.basicConfig(
            level=logging.DEBUG,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        sys.excepthook = self.handle_exception
        self._rotate_logs()

    def handle_exception(self, exc_type, exc_value, exc_traceback):
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_traceback)
            return

        logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
        
        error_msg = "".join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        print(error_msg) # Ensure it prints to console
        self._write_bug_report(exc_type, exc_value, error_msg)
        
        # Show error dialog if QApplication is running
        if QApplication.instance():
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle("Critical Error")
            msg.setText("An unexpected error occurred.")
            msg.setInformativeText(str(exc_value))
            msg.setDetailedText(error_msg) # Collapsible details
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

    def _write_bug_report(self, exc_type, exc_value, error_msg):
        try:
            sys_info = f"System: {platform.system()} {platform.release()}\n"
            sys_info += f"Python: {sys.version}\n"
            sys_info += f"Platform: {platform.platform()}\n"

            with open(self.bug_log_path, "a", encoding="utf-8") as f:
                f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n")
                f.write(f"{sys_info}\n")
                f.write("Auto Report:\n")
                f.write(f"{exc_type.__name__}: {exc_value}\n\n")
                f.write("Traceback:\n")
                f.write(error_msg)
                f.write(f"\n{'-' * 50}\n")
        except Exception as exc:
            logging.error("Failed to write bug report: %s", exc)

    def _rotate_logs(self, days_to_keep=7):
        """Removes log files older than the specified number of days."""
        try:
            now = datetime.now()
            for filename in os.listdir(self.log_dir):
                if filename.startswith("app_") and filename.endswith(".log"):
                    file_path = os.path.join(self.log_dir, filename)
                    # Get file modification time
                    file_mtime = datetime.fromtimestamp(os.path.getmtime(file_path))
                    if (now - file_mtime).days > days_to_keep:
                        os.remove(file_path)
                        logging.info(f"Deleted old log file: {filename}")
        except Exception as exc:
            logging.error(f"Failed to rotate logs: {exc}")
