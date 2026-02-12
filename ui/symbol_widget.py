import os
import re
import math
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QPainterPath, QFont, QFontDatabase, QTextDocument
from PySide6.QtCore import Qt, QPointF, QRectF, QPoint
from ui.widgets.paint_utils import painting

class SymbolWidget(QWidget):
    _kicad_font_family = "Arial" # Default fallback
    _font_loaded = False

    def __init__(self):
        super().__init__()
        self.data = None
        self.setMinimumHeight(200)
        # Force white background regardless of theme, as requested
        self.setStyleSheet("background-color: #FFFFFF; border: 1px solid #ccc; color: black;") # Ensures consistent background (KiCad default white)
        self._ensure_font_loaded()
        
        # View Transform State
        self.view_scale = 1.0
        self.view_center = QPointF(0, 0)
        self.is_panning = False
        self.last_mouse_pos = QPointF()
        self.content_bounds = QRectF(-5, -5, 10, 10)

    def _kicad_font(self, point_size=10.0):
        font = QFont(self._kicad_font_family)
        # Some Qt font paths can carry pointSize == -1; always force a valid size.
        if point_size is not None and point_size > 0:
            font.setPointSizeF(float(point_size))
        elif font.pointSizeF() <= 0:
            font.setPointSizeF(10.0)
        return font

    @classmethod
    def _ensure_font_loaded(cls):
        if cls._font_loaded:
            return
            
        # Attempt to load the KiCad font (newstroke.ttf)
        # Checking common locations relative to the script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # List of possible filenames (including user typo)
        filenames = ["newstroke.ttf", "newstrokge.ttf", "KiCad.ttf", "Newstroke_KiCad_font.ttf", "Newstroke_KiCad_font"]
        
        # List of search directories
        search_dirs = [
            base_dir, # ui/
            os.path.join(base_dir, ".."), # Parts_Checker/
            os.path.join(base_dir, "fonts"),
            os.path.join(base_dir, "..", "resources"),
            os.path.join(base_dir, "..", "fonts"),
            os.path.join(base_dir, "..", "graphical_elements", "fonts"),
            os.path.join(base_dir, "..", "graphical_elements", "fonts", "Newstroke_KiCad_font"),
            # Try to guess KiCad install location relative to script
            os.path.abspath(os.path.join(base_dir, "../../../share/kicad/resources")),
            # Common Windows Install paths
            r"C:\Program Files\KiCad\9.0\share\kicad\resources",
            r"C:\Program Files\KiCad\8.0\share\kicad\resources",
        ]
        
        font_id = -1
        for d in search_dirs:
            if not os.path.exists(d): continue
            for fname in filenames:
                fpath = os.path.join(d, fname)
                if os.path.exists(fpath):
                    font_id = QFontDatabase.addApplicationFont(fpath)
                    if font_id != -1:
                        families = QFontDatabase.applicationFontFamilies(font_id)
                        if families:
                            cls._kicad_font_family = families[0]
                            break
            if font_id != -1: break
            
        # Fallback: Check if installed system-wide
        if font_id == -1:
            db = QFontDatabase()
            if "KiCad" in db.families():
                cls._kicad_font_family = "KiCad"
            elif "NewStroke" in db.families():
                cls._kicad_font_family = "NewStroke"
        
        cls._font_loaded = True

    def set_data(self, data):
        """Sets the symbol data to be displayed and triggers a repaint."""
        self.data = data
        self._calculate_bounds()
        self.reset_view()
        self.update()

    def _calculate_bounds(self):
        """Calculates the bounding box of the symbol content."""
        if not self.data:
            self.content_bounds = QRectF(-5, -5, 10, 10)
            return

        points = []
        # Pins
        for p in self.data.get("pins", []):
            at = p.get("at", [0, 0])
            l = p.get("length", 2.54)
            points.append((at[0], at[1]))
            # Add extents for all directions to be safe
            points.append((at[0] + l, at[1]))
            points.append((at[0] - l, at[1]))
            points.append((at[0], at[1] + l))
            points.append((at[0], at[1] - l))

        # Graphics
        for g in self.data.get("graphics", []):
            if g[0] == "polyline":
                for pt in g[1:]:
                    if isinstance(pt, list) and pt[0] == "pts":
                        for xy in pt[1:]:
                            if isinstance(xy, list) and xy[0] == "xy":
                                points.append((float(xy[1]), float(xy[2])))
            elif g[0] == "rectangle":
                for attr in g[1:]:
                    if attr[0] in ["start", "end"]:
                        points.append((float(attr[1]), float(attr[2])))
            elif g[0] == "arc":
                for attr in g[1:]:
                    if isinstance(attr, list) and attr[0] in ["start", "mid", "end"]:
                        points.append((float(attr[1]), float(attr[2])))
            elif g[0] == "circle":
                 center = [0,0]; radius = 0
                 for attr in g[1:]:
                     if attr[0] == "center": center = [float(attr[1]), float(attr[2])]
                     elif attr[0] == "radius": radius = float(attr[1])
                 points.append((center[0]-radius, center[1]-radius))
                 points.append((center[0]+radius, center[1]+radius))
            elif g[0] == "text":
                for attr in g[2:]:
                    if isinstance(attr, list) and attr[0] == "at":
                        points.append((float(attr[1]), float(attr[2])))
        
        # Visual Properties
        for prop in self.data.get("visual_properties", []):
            for attr in prop[3:]:
                if isinstance(attr, list) and attr[0] == "at":
                    points.append((float(attr[1]), float(attr[2])))

        if points:
            xs = [p[0] for p in points]
            ys = [p[1] for p in points]
            self.content_bounds = QRectF(min(xs), min(ys), max(xs)-min(xs), max(ys)-min(ys))
        else:
            self.content_bounds = QRectF(-5, -5, 10, 10)

    def reset_view(self):
        """Resets zoom and pan to fit content."""
        if self.content_bounds.width() <= 0 or self.content_bounds.height() <= 0:
            self.view_scale = 10.0
            self.view_center = QPointF(0, 0)
        else:
            w, h = self.width(), self.height()
            if w <= 0: w = 200
            if h <= 0: h = 200
            pad = 1.2
            sx = w / (self.content_bounds.width() * pad)
            sy = h / (self.content_bounds.height() * pad)
            self.view_scale = min(sx, sy)
            self.view_center = self.content_bounds.center()
        self.update()

    def zoom(self, factor):
        """Zooms the view by the given factor."""
        self.view_scale *= factor
        self.update()

    def wheelEvent(self, event):
        """Handles zoom via Ctrl + Scroll."""
        if event.modifiers() & Qt.ControlModifier:
            angle = event.angleDelta().y()
            factor = 1.1 if angle > 0 else 0.9
            self.zoom(factor)
            event.accept()
        else:
            super().wheelEvent(event)

    def mousePressEvent(self, event):
        """Starts panning."""
        if event.button() == Qt.LeftButton or event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        """Handles panning."""
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.last_mouse_pos = event.position()
            
            # Convert screen delta to logical delta
            dx = delta.x() / self.view_scale
            dy = -delta.y() / self.view_scale # Flip Y because of scale(1, -1)
            
            self.view_center -= QPointF(dx, dy)
            self.update()
            event.accept()

    def mouseReleaseEvent(self, event):
        """Ends panning."""
        if event.button() == Qt.LeftButton or event.button() == Qt.MiddleButton:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()

    def paintEvent(self, event):
        """Handles the painting of the symbol on the widget."""
        with painting(self) as painter:
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Fill background explicitly (KiCad default white)
            painter.fillRect(self.rect(), QColor("#FFFFFF"))
            
            if not self.data:
                painter.drawText(self.rect(), Qt.AlignCenter, "No Symbol Data")
                return

            # Apply View Transform
            w, h = self.width(), self.height()
            painter.translate(w/2, h/2)
            painter.scale(self.view_scale, -self.view_scale)
            painter.translate(-self.view_center)

            # Draw Content
            pins = self.data.get("pins", [])
            graphics = self.data.get("graphics", [])
            pen = QPen(QColor("#800000")) # KiCad symbol redish
            pen.setWidthF(0.25)
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)

            for g in graphics:
                # Draw Rectangles
                if g[0] == "rectangle":
                    start = [0,0]
                    end = [0,0]
                    for attr in g[1:]:
                        if attr[0] == "start": start = [float(attr[1]), float(attr[2])]
                        if attr[0] == "end": end = [float(attr[1]), float(attr[2])]
                    painter.drawRect(QRectF(QPointF(start[0], start[1]), QPointF(end[0], end[1])))
                
                # Draw Polylines
                elif g[0] == "polyline":
                    path = QPainterPath()
                    first = True
                    for pt in g[1:]:
                        if isinstance(pt, list) and pt[0] == "pts":
                            for xy in pt[1:]:
                                if xy[0] == "xy":
                                    x, y = float(xy[1]), float(xy[2])
                                    if first: path.moveTo(x, y); first = False
                                    else: path.lineTo(x, y)
                    painter.drawPath(path)
                
                # Draw Circles
                elif g[0] == "circle":
                    center = [0,0]
                    rad = 0
                    for attr in g[1:]:
                        if attr[0] == "center": center = [float(attr[1]), float(attr[2])]
                        if attr[0] == "radius": rad = float(attr[1])
                    painter.drawEllipse(QPointF(center[0], center[1]), rad, rad)
                
                # Draw Arcs (using 3-point arc calculation)
                elif g[0] == "arc":
                    pts = []
                    for attr in g[1:]:
                        if isinstance(attr, list) and attr[0] in ["start", "mid", "end"]:
                            pts.append(QPointF(float(attr[1]), float(attr[2])))
                    
                    if len(pts) == 3:
                        # Calculate circle center and radius from 3 points
                        x1, y1 = pts[0].x(), pts[0].y()
                        x2, y2 = pts[1].x(), pts[1].y()
                        x3, y3 = pts[2].x(), pts[2].y()
                        
                        D = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
                        if D != 0:
                            Ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / D
                            Uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / D
                            center = QPointF(Ux, Uy)
                            radius = math.sqrt((x1 - Ux)**2 + (y1 - Uy)**2)
                            
                            # Calculate angles
                            # Negate Y delta because painter uses inverted Y axis (scale(1, -1))
                            start_angle = math.degrees(math.atan2(-(y1 - Uy), x1 - Ux))
                            mid_angle = math.degrees(math.atan2(-(y2 - Uy), x2 - Ux))
                            end_angle = math.degrees(math.atan2(-(y3 - Uy), x3 - Ux))
                            
                            # Normalize angles to 0-360 for comparison
                            start_n = start_angle % 360
                            mid_n = mid_angle % 360
                            end_n = end_angle % 360
                            
                            # Calculate CCW spans
                            span_end = (end_n - start_n) % 360
                            span_mid = (mid_n - start_n) % 360
                            
                            # Determine direction: if mid is within the CCW path to end, then it's CCW
                            if span_mid < span_end:
                                span = span_end
                            else:
                                span = span_end - 360
                            
                            # Draw Arc (startAngle and spanAngle in 1/16th of a degree)
                            painter.drawArc(QRectF(center.x() - radius, center.y() - radius, radius*2, radius*2), int(start_angle * 16), int(span * 16))

                elif g[0] == "text":
                    self._draw_text_element(painter, g[1], g[2:], QColor("#000080"))

            # Draw Visual Properties (Reference, Value)
            for prop in self.data.get("visual_properties", []):
                # prop: ['property', 'Reference', 'U1', ['at', ...], ['effects', ...]]
                # Check visibility
                is_hidden = False
                for attr in prop[3:]:
                    if attr == "hide": is_hidden = True
                    elif isinstance(attr, list) and attr[0] == "effects":
                        if "hide" in attr: is_hidden = True
                        for e in attr[1:]:
                            if e == "hide" or (isinstance(e, list) and e[0] == "hide"):
                                is_hidden = True
                
                if not is_hidden:
                    # Use Teal for Reference/Value, Navy for Others
                    color = QColor("#008080") if prop[1] in ["Reference", "Value"] else QColor("#000080")
                    self._draw_text_element(painter, prop[2], prop[3:], color)

            # Draw Pins
            pin_pen = QPen(QColor("#800000"))
            pin_pen.setWidthF(0.15)
            pin_pen.setCapStyle(Qt.RoundCap)
            pin_pen.setJoinStyle(Qt.RoundJoin)
            painter.setPen(pin_pen)
            # Reusable font object
            p_font = self._kicad_font()
            
            for p in pins:
                if not p.get("visible", True):
                    continue

                # Pin position and length
                at = p.get("at", [0, 0])
                length = p.get("length", 2.54)
                x, y = at[0], at[1]
                
                # Determine pin angle from 'at' attribute (if present)
                angle = 0
                if len(at) > 2: angle = at[2]

                # Calculate end point of the pin line based on angle
                end_x, end_y = x + length, y # Default 0 deg
                if angle == 90: end_x, end_y = x, y + length
                elif angle == 180: end_x, end_y = x - length, y
                elif angle == 270: end_x, end_y = x, y - length

                # Draw pin line and connection point
                painter.drawLine(QPointF(x, y), QPointF(end_x, end_y))
                painter.drawEllipse(QPointF(x, y), 0.1, 0.1) # Connection point
                
                # Draw Pin Number and Name (Consistent Orientation)
                mid_pin = length / 2.0
                dist = 0.8
                offset = self.data.get("pin_names_offset") or 0.6 # Default offset if not specified
                
                num_pos = QPointF(0, 0)
                name_pos = QPointF(0, 0)
                text_rot = 0
                name_align = Qt.AlignVCenter | Qt.AlignLeft
                name_rect_offset = QPointF(0, -1.5)
                
                if angle == 0: # Right
                    num_pos = QPointF(x + mid_pin, y + dist)
                    name_pos = QPointF(x + length + offset, y)
                    text_rot = 0
                    name_align = Qt.AlignVCenter | Qt.AlignLeft
                    name_rect_offset = QPointF(0, -1.5)
                elif angle == 180: # Left
                    num_pos = QPointF(x - mid_pin, y + dist)
                    name_pos = QPointF(x - length - offset, y)
                    text_rot = 0
                    name_align = Qt.AlignVCenter | Qt.AlignRight
                    name_rect_offset = QPointF(-10, -1.5)
                elif angle == 90: # Up
                    num_pos = QPointF(x - dist, y + mid_pin)
                    name_pos = QPointF(x, y + length + offset)
                    text_rot = 90
                    name_align = Qt.AlignVCenter | Qt.AlignLeft
                    name_rect_offset = QPointF(0, -1.5)
                elif angle == 270: # Down
                    num_pos = QPointF(x - dist, y - mid_pin)
                    name_pos = QPointF(x, y - length - offset)
                    text_rot = 90
                    name_align = Qt.AlignVCenter | Qt.AlignRight
                    name_rect_offset = QPointF(-10, -1.5)

                show_nums = self.data.get("show_pin_numbers")
                if show_nums is None: show_nums = True
                
                num_size = p.get("num_text_size", 1.27)
                point_size = num_size
                if show_nums and p.get("num_visible", True) and num_size > 0 and (point_size * self.view_scale) > 4.0:
                        painter.save()
                        painter.translate(num_pos)
                        painter.rotate(text_rot)
                        painter.scale(1, -1)
                        
                        # Use reference size scaling for smooth text
                        ref_size = 48.0
                        scale = point_size / ref_size
                        painter.scale(scale, scale)
                        p_font.setPointSizeF(ref_size)
                        p_font.setHintingPreference(QFont.PreferNoHinting)
                        painter.setFont(p_font)
                        painter.setPen(QColor("#800000"))
                        # Draw in a large enough rect centered at 0,0 (scaled coords)
                        painter.drawText(QRectF(-100, -50, 200, 100), Qt.AlignCenter, str(p.get("number", "")))
                        painter.restore()

                show_names = self.data.get("show_pin_names")
                if show_names is None: show_names = True

                name_text = p.get("name", "")
                name_size = p.get("name_text_size", 1.27)
                point_size = name_size
                if show_names and name_text != "~" and p.get("name_visible", True) and name_size > 0 and (point_size * self.view_scale) > 4.0:
                        painter.save()
                        painter.translate(name_pos)
                        painter.rotate(text_rot)
                        painter.scale(1, -1)
                        
                        # Use reference size scaling
                        ref_size = 48.0
                        scale = point_size / ref_size
                        painter.scale(scale, scale)
                        p_font.setPointSizeF(ref_size)
                        p_font.setHintingPreference(QFont.PreferNoHinting)
                        painter.setFont(p_font)
                        painter.setPen(QColor("#008080"))
                        
                        # Scale the layout rect to match the new coordinate system
                        rect = QRectF(name_rect_offset.x()/scale, name_rect_offset.y()/scale, 10.0/scale, 3.0/scale)
                        painter.drawText(rect, name_align, name_text)
                        painter.restore()

    def _draw_text_element(self, painter, content, attributes, color):
        at = [0, 0, 0]
        size = [1.27, 1.27]
        h_align = Qt.AlignHCenter
        v_align = Qt.AlignVCenter

        for attr in attributes:
            if isinstance(attr, list):
                if attr[0] == "at": at = [float(x) for x in attr[1:]]
                elif attr[0] == "effects":
                    for e in attr[1:]:
                        if isinstance(e, list):
                            if e[0] == "font":
                                for f in e[1:]:
                                    if isinstance(f, list) and f[0] == "size":
                                        size = [float(x) for x in f[1:]]
                            elif e[0] == "justify":
                                for j in e[1:]:
                                    if j == "left": h_align = Qt.AlignLeft
                                    elif j == "right": h_align = Qt.AlignRight
                                    elif j == "top": v_align = Qt.AlignTop
                                    elif j == "bottom": v_align = Qt.AlignBottom
        
        if not size or size[0] <= 0:
            return

        # Ensure size has 2 elements (Height, Width)
        if len(size) < 2:
            size.append(size[0])

        painter.save()
        painter.translate(at[0], at[1]) # Move to text position
        
        # Restore Y-down coordinate system (cancel global flip)
        painter.scale(1, -1)

        # Rotation (KiCad 90deg is Up, Qt -90deg is Up in Y-down system)
        if len(at) > 2:
            painter.rotate(-at[2])

        # Use a large reference font size to ensure good kerning/layout, then scale down
        ref_size = 48.0
        
        # KiCad size is [Height, Width]
        # We scale the painter to match the target dimensions using the reference font size
        scale_x = abs(size[1]) / ref_size
        scale_y = abs(size[0]) / ref_size
        
        # Heuristic to prevent rendering errors with tiny fonts
        if abs(size[0]) * self.view_scale < 4.0:
            painter.restore()
            return

        painter.scale(scale_x, scale_y)

        t_font = self._kicad_font()
        t_font.setPointSizeF(ref_size)
        t_font.setHintingPreference(QFont.PreferNoHinting) # Important for smooth scaling
        t_font.setStyleStrategy(QFont.PreferAntialias)
        
        doc = QTextDocument()
        doc.setDefaultFont(t_font)
        doc.setDocumentMargin(0)
        doc.setUseDesignMetrics(True) # Critical for accurate kerning at small scales
        doc.setDefaultStyleSheet(f"body {{ color: {color.name()}; }}")
        
        html_content = self._format_kicad_text(content)
        doc.setHtml(f"<body>{html_content}</body>")
        
        w = doc.size().width()
        h = doc.size().height()
        
        x_off = 0
        if h_align == Qt.AlignHCenter: x_off = -w / 2
        elif h_align == Qt.AlignRight: x_off = -w
        
        y_off = 0
        if v_align == Qt.AlignTop: y_off = 0
        elif v_align == Qt.AlignBottom: y_off = -h
        elif v_align == Qt.AlignVCenter: y_off = -h / 2.0
        
        painter.translate(x_off, y_off)
        doc.drawContents(painter)
        painter.restore()

    def _format_kicad_text(self, text):
        # 1. Variable Substitution
        if self.data and "properties" in self.data:
            def replace_var(match):
                key = match.group(1)
                return self.data["properties"].get(key, f"${{{key}}}")
            text = re.sub(r'\$\{([^}]+)\}', replace_var, text)

        # 2. HTML Conversion
        text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        text = text.replace("~~", "\x01") # Placeholder for literal tilde

        # Iteratively replace formatting codes: ~{...}, _{...}, ^{...}
        pattern = re.compile(r'([~_^])\{([^{}]+)\}')
        while True:
            def replace_match(m):
                op, content = m.groups()
                if op == '~': return f'<span style="text-decoration: overline">{content}</span>'
                if op == '_': return f'<sub>{content}</sub>'
                if op == '^': return f'<sup>{content}</sup>'
                return m.group(0)
            new_text, n = pattern.subn(replace_match, text)
            if n == 0: break
            text = new_text

        # Legacy Toggles (~)
        parts = text.split('~')
        if len(parts) > 1:
            res = []
            is_over = False
            for i, p in enumerate(parts):
                if i > 0:
                    tag = '</span>' if is_over else '<span style="text-decoration: overline">'
                    res.append(tag)
                    is_over = not is_over
                res.append(p)
            if is_over: res.append('</span>')
            text = "".join(res)

        text = text.replace("\x01", "~")
        text = text.replace("\n", "<br>")
        return text
