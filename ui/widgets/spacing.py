from PySide6.QtCore import QMargins

SPACING = {
    "xs": 4,
    "sm": 8,
    "md": 12,
    "lg": 16,
    "xl": 24,
}

PAGE_PADDING = SPACING["lg"]


def apply_layout(layout, margin="md", spacing="md"):
    if layout is None:
        return
    m = SPACING[margin] if isinstance(margin, str) else margin
    s = SPACING[spacing] if isinstance(spacing, str) else spacing
    layout.setContentsMargins(m, m, m, m)
    layout.setSpacing(s)


def apply_layout_margins(layout, left, top, right, bottom, spacing=None):
    if layout is None:
        return
    layout.setContentsMargins(left, top, right, bottom)
    if spacing is not None:
        s = SPACING[spacing] if isinstance(spacing, str) else spacing
        layout.setSpacing(s)
