from contextlib import contextmanager

from PySide6.QtGui import QPainter


@contextmanager
def painting(widget):
    painter = QPainter(widget)
    try:
        yield painter
    finally:
        painter.end()
