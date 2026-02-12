from PySide6.QtCore import QObject, Signal
import os
import sys
try:
    import winsound
except Exception:
    winsound = None


class WarningCenter(QObject):
    warnings_changed = Signal(int, str)

    def __init__(self):
        super().__init__()
        self._warnings = []

    def add_warning(self, message, fix_callback=None, fix_label="Fix"):
        msg = (message or "").strip()
        if not msg:
            return
        warning = {
            "message": msg,
            "fix_callback": fix_callback,
            "fix_label": fix_label or "Fix",
        }
        self._warnings.append(warning)
        self._play_alert()
        self.warnings_changed.emit(len(self._warnings), msg)

    def _play_alert(self):
        # Use a Windows notification sound when available.
        if winsound and sys.platform.startswith("win"):
            try:
                winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                return
            except Exception:
                pass
        # Cross-platform fallback: terminal bell (no-op in most GUI contexts).
        try:
            sys.stdout.write("\a")
            sys.stdout.flush()
        except Exception:
            pass

    def clear(self):
        self._warnings.clear()
        self.warnings_changed.emit(0, "")

    def count(self):
        return len(self._warnings)

    def latest(self):
        if not self._warnings:
            return ""
        return self._warnings[-1].get("message", "")

    def all(self):
        return list(self._warnings)


warning_center = WarningCenter()
