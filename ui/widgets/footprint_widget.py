import os
import math
from pathlib import Path
from PySide6.QtWidgets import QWidget
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QFontDatabase, QFontMetrics, QFontMetricsF
from PySide6.QtCore import Qt, QPointF, QRectF, QPoint
from .paint_utils import painting

class FootprintWidget(QWidget):
    DEFAULT_LAYER_COLORS = {
        "F.Cu": QColor("#DA4453"), "B.Cu": QColor("#27AE60"),
        "F.Adhes": QColor("#0055E2"), "B.Adhes": QColor("#E25500"),
        "F.Paste": QColor("#999999"), "B.Paste": QColor("#99D4D4"),
        "F.SilkS": QColor("#E0E0E0"), "B.SilkS": QColor("#E0E000"),
        "F.Mask": QColor("#A020F0"), "B.Mask": QColor("#A020F0"),
        "F.CrtYd": QColor("#AAAAAA"), "B.CrtYd": QColor("#AAAA00"),
        "F.Fab": QColor("#CCCCCC"), "B.Fab": QColor("#00CCCC"),
        "Edge.Cuts": QColor("#F1C40F"),
        "Dwgs.User": QColor("#00E0E0"),
        "Cmts.User": QColor("#E000E0"),
    }
    LAYER_COLORS = DEFAULT_LAYER_COLORS

    _kicad_font_family = "Newstroke" # Default fallback to KiCad stroke font
    _font_loaded = False

    def __init__(self):
        super().__init__()
        self.data = None
        self.layer_colors = {k: QColor(v) for k, v in self.DEFAULT_LAYER_COLORS.items()}
        self.visible_layers = set(self.layer_colors.keys())
        self.show_pad_numbers = False
        self.setMinimumHeight(200)
        self.setStyleSheet("background-color: #333; border: 1px solid #555;")
        self._ensure_font_loaded()

        # View Transform
        self.view_scale = 1.0
        self.view_center = QPointF(0, 0)
        self.is_panning = False
        self.last_mouse_pos = QPointF()
        self.content_bounds = QRectF(-5, -5, 10, 10)

        # Measurement Mode
        self.measure_mode = False
        self.measure_points = []
        self.hover_pos = None
        self.setMouseTracking(True)

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
        project_dir = Path(__file__).resolve().parent.parent
        font_file = project_dir / "resources" / "fonts" / "Newstroke_KiCad_font" / "Newstroke.ttf"
        if font_file.exists():
            font_id = QFontDatabase.addApplicationFont(str(font_file))
            if font_id != -1:
                families = QFontDatabase.applicationFontFamilies(font_id)
                if families:
                    cls._kicad_font_family = families[0]
        cls._font_loaded = True

    def set_data(self, data):
        """Sets the footprint data to be displayed and triggers a repaint."""
        self.data = data
        self._calculate_bounds()
        self.reset_view()
        self.update()

    def get_content_bounds(self):
        return QRectF(self.content_bounds)

    def set_visible_layers(self, layers):
        """Sets which layers to draw."""
        self.visible_layers = layers
        self.update()

    def set_layer_color(self, layer, color):
        if layer in self.layer_colors and color:
            self.layer_colors[layer] = QColor(color)
            self.update()

    def get_layer_color(self, layer):
        return self.layer_colors.get(layer, QColor("white"))

    def reset_layer_colors(self, layer=None):
        if layer:
            if layer in self.layer_colors:
                self.layer_colors[layer] = QColor(self.DEFAULT_LAYER_COLORS.get(layer, self.layer_colors[layer]))
        else:
            self.layer_colors = {k: QColor(v) for k, v in self.DEFAULT_LAYER_COLORS.items()}
        self.update()

    def toggle_pad_numbers(self, enabled):
        self.show_pad_numbers = enabled
        self.update()

    def _calculate_bounds(self):
        if not self.data:
            self.content_bounds = QRectF(-5, -5, 10, 10)
            return

        all_x, all_y = [], []
        pads = self.data.get("pads", [])
        lines = self.data.get("lines", [])
        
        for p in pads:
            at = p.get("at", [0,0]); size = p.get("size", [1, 1])
            all_x.extend([at[0] - size[0]/2, at[0] + size[0]/2])
            all_y.extend([at[1] - size[1]/2, at[1] + size[1]/2])
            
            if p.get("shape") == "custom":
                 for prim in p.get("primitives", []):
                     if prim.get("type") == "gr_poly":
                         for pt in prim.get("pts", []):
                             all_x.append(at[0] + pt[0])
                             all_y.append(at[1] + pt[1])
            
        for l in lines:
            if l.get('start'): all_x.append(l['start'][0]); all_y.append(l['start'][1])
            if l.get('end'): all_x.append(l['end'][0]); all_y.append(l['end'][1])
            if l.get('center'): all_x.append(l['center'][0]); all_y.append(l['center'][1])
            if l.get('pts'):
                for pt in l['pts']: all_x.append(pt[0]); all_y.append(pt[1])
        
        if not all_x: 
            self.content_bounds = QRectF(-5, -5, 10, 10)
        else:
            self.content_bounds = QRectF(min(all_x), min(all_y), max(all_x)-min(all_x), max(all_y)-min(all_y))

    def reset_view(self):
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
        self.view_scale *= factor
        self.update()

    def toggle_measure_mode(self, enabled):
        self.measure_mode = enabled
        self.measure_points = []
        self.setCursor(Qt.CrossCursor if enabled else Qt.ArrowCursor)
        self.update()

    def wheelEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            angle = event.angleDelta().y()
            factor = 1.1 if angle > 0 else 0.9
            self.zoom(factor)
            event.accept()
        else: super().wheelEvent(event)

    def keyPressEvent(self, event):
        if self.measure_mode and event.key() == Qt.Key_Escape:
            self.measure_points = []
            self.update()
            event.accept()
        else:
            super().keyPressEvent(event)

    def paintEvent(self, event):
        """Handles the painting of the footprint on the widget."""
        with painting(self) as painter:
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setFont(self._kicad_font())
            self._scale_bar_bottom_reserved = 0
            
            # Fill background explicitly (Dark Grey/Black)
            painter.fillRect(self.rect(), QColor("#333333"))
            
            if not self.data:
                painter.setPen(QColor("white"))
                painter.drawText(self.rect(), Qt.AlignCenter, "No Footprint Data")
                return

            # Extract pads and lines from data
            pads = self.data.get("pads", [])
            lines = self.data.get("lines", [])

            if not pads and not lines:
                painter.setPen(QColor("white"))
                painter.drawText(self.rect(), Qt.AlignCenter, "Empty Footprint")
                return

            # Apply transformations: center and scale
            w, h = self.width(), self.height()
            painter.translate(w/2, h/2)
            painter.scale(self.view_scale, self.view_scale) # KiCad PCB coordinates are Y-down, matching screen Y-down
            painter.translate(-self.view_center)

            # Group items by layer for correct drawing order
            # Order: Bottom -> Top Copper -> Top Doc -> Top Silk -> Other -> THT
            bottom_items = []
            top_copper_items = []
            top_doc_items = []
            top_silk_items = []
            other_items = []
            tht_pads = []

            for p in pads:
                if not self.visible_layers.intersection(p.get("layers", [])):
                    continue
                layers = p.get("layers", [])
                ptype = p.get("type", "")
                
                if "thru_hole" in ptype or "np_thru_hole" in ptype:
                    tht_pads.append(p)
                elif "B.Cu" in layers:
                    bottom_items.append(('pad', p))
                elif "F.Cu" in layers:
                    top_copper_items.append(('pad', p))
                else:
                    other_items.append(('pad', p))

            for l in lines:
                layer = l.get("layer", "")
                if layer not in self.visible_layers:
                    continue
                
                if layer.startswith("B."):
                    bottom_items.append(('line', l))
                elif layer == "F.Cu":
                    top_copper_items.append(('line', l))
                elif layer == "F.SilkS":
                    top_silk_items.append(('line', l))
                elif layer.startswith("F."): # Fab, CrtYd, Mask, Paste
                    top_doc_items.append(('line', l))
                else:
                    other_items.append(('line', l))

            # Draw Bottom Layer
            for type, item in bottom_items:
                if type == 'pad': self._draw_pad(painter, item)
                else: self._draw_graphic(painter, item)

            # Draw Other (Edge.Cuts, User)
            for type, item in other_items:
                if type == 'pad': self._draw_pad(painter, item)
                else: self._draw_graphic(painter, item)

            # Draw Top Doc (Fab, CrtYd, Mask)
            for type, item in top_doc_items:
                if type == 'pad': self._draw_pad(painter, item)
                else: self._draw_graphic(painter, item)
                
            # Draw Top Silk
            for type, item in top_silk_items:
                if type == 'pad': self._draw_pad(painter, item)
                else: self._draw_graphic(painter, item)
                
            # Draw Top Copper (Pads on top of Silk)
            for type, item in top_copper_items:
                if type == 'pad': self._draw_pad(painter, item)
                else: self._draw_graphic(painter, item)
                
            # Draw THT Pads
            for p in tht_pads:
                self._draw_pad(painter, p)
                
            # Draw Pad Numbers (Always on top of everything)
            if self.show_pad_numbers:
                for p in pads:
                    if not self.visible_layers.intersection(p.get("layers", [])):
                        continue
                    self._draw_pad_text(painter, p)

            if self.measure_mode:
                self._draw_measurement_ui(painter)

            # Draw scale bar (screen space)
            self._draw_scale_bar(painter)
            self._draw_vertical_scale(painter)

    def _pick_scale_length(self, max_px):
        candidates = [0.1, 0.2, 0.5, 1, 2, 5, 10, 20, 50, 100]
        length_mm = candidates[0]
        for mm in candidates:
            if mm * self.view_scale <= max_px:
                length_mm = mm
        length_px = int(length_mm * self.view_scale)
        return length_mm, length_px

    def _draw_pad(self, painter, p):
        at = p.get("at", [0, 0])
        size = p.get("size", [1, 1])
        ptype = p.get("type", "smd")
        layers = p.get("layers", [])
        shape = p.get("shape", "rect")
        drill = p.get("drill", 0.0)
        rotation = 0
        if len(at) > 2:
            rotation = at[2]
        
        # Use local coordinates for drawing, then translate/rotate
        # rect centered at 0,0
        rect = QRectF(-size[0]/2, -size[1]/2, size[0], size[1])
        
        # Determine if we draw copper
        draw_copper = True
        if "np_thru_hole" in ptype:
             # NPTH usually has no copper, unless specified in layers
             if not any("Cu" in l for l in layers):
                 draw_copper = False

        if draw_copper:
            color = None
            if "thru_hole" in ptype:
                 color = QColor("#C0C000") # Gold/Yellow for THT
            elif 'F.Cu' in self.visible_layers and ('F.Cu' in layers or '*.Cu' in layers):
                color = self.layer_colors.get("F.Cu")
            elif 'B.Cu' in self.visible_layers and ('B.Cu' in layers or '*.Cu' in layers):
                color = self.layer_colors.get("B.Cu")
            
            if color:
                painter.save()
                painter.translate(at[0], at[1])
                # KiCad rotation is CCW, Qt rotate is CW. So we negate.
                painter.rotate(-rotation)
                
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                
                if shape == "custom":
                    # Draw Anchor Pad first
                    anchor = p.get("anchor_shape", "rect")
                    if anchor == "circle":
                        painter.drawEllipse(rect)
                    elif anchor == "oval":
                        painter.drawRoundedRect(rect, size[0]/2, size[1]/2)
                    elif anchor == "rect":
                        painter.drawRect(rect)
                    
                    for prim in p.get("primitives", []):
                        self._draw_primitive(painter, prim)
                elif shape == "circle":
                    painter.drawEllipse(rect)
                elif shape == "oval":
                    r = min(size[0], size[1]) / 2
                    painter.drawRoundedRect(rect, r, r)
                elif shape == "roundrect":
                    ratio = p.get("roundrect_rratio", 0.25)
                    r = min(size[0], size[1]) * ratio
                    painter.drawRoundedRect(rect, r, r)
                else:
                    painter.drawRect(rect)

                painter.restore()

        # Draw Drill Hole
        if isinstance(drill, dict):
            d_shape = drill.get("shape", "circle")
            d_size = drill.get("size", [0, 0])
            if d_size[0] > 0:
                painter.setBrush(QColor("#222222"))
                painter.setPen(Qt.NoPen)
                d_rect = QRectF(at[0] - d_size[0]/2, at[1] - d_size[1]/2, d_size[0], d_size[1])
                if d_shape == "oval":
                    r = min(d_size[0], d_size[1]) / 2
                    painter.drawRoundedRect(d_rect, r, r)
                else:
                    painter.drawEllipse(d_rect)
        elif isinstance(drill, (int, float)) and drill > 0:
             painter.setBrush(QColor("#222222"))
             painter.setPen(Qt.NoPen)
             painter.drawEllipse(QPointF(at[0], at[1]), drill/2, drill/2)

        elif not draw_copper and drill == 0:
            color = None
            if 'F.Cu' in self.visible_layers and 'F.Cu' in layers:
                color = self.layer_colors.get("F.Cu")
            elif 'B.Cu' in self.visible_layers and 'B.Cu' in layers:
                color = self.layer_colors.get("B.Cu")
            
            if color:
                painter.save()
                painter.translate(at[0], at[1])
                painter.rotate(-rotation)
                
                painter.setBrush(color)
                painter.setPen(Qt.NoPen)
                if shape == "custom":
                    # Draw Anchor Pad first
                    anchor = p.get("anchor_shape", "rect")
                    if anchor == "circle":
                        painter.drawEllipse(rect)
                    elif anchor == "oval":
                        painter.drawRoundedRect(rect, size[0]/2, size[1]/2)
                    elif anchor == "rect":
                        painter.drawRect(rect)
                    
                    for prim in p.get("primitives", []):
                        self._draw_primitive(painter, prim)
                elif shape == "circle":
                    painter.drawEllipse(rect)
                elif shape == "roundrect":
                    ratio = p.get("roundrect_rratio", 0.25)
                    r = min(size[0], size[1]) * ratio
                    painter.drawRoundedRect(rect, r, r)
                else: # rect, oval (oval is just a rounded rect for smd)
                    painter.drawRect(rect)
                
                painter.restore()

    def _draw_pad_text(self, painter, p):
        at = p.get("at", [0, 0])
        size = p.get("size", [1, 1])
        ptype = p.get("type", "smd")
        rotation = 0
        if len(at) > 2:
            rotation = at[2]

        number_text = str(p.get("number", ""))
        if number_text and size[0] > 0 and size[1] > 0:
            min_dim = min(size[0], size[1])
            target_h = min_dim * 0.6
            
            # Check visibility (approx 4 pixels on screen)
            if (target_h * self.view_scale) > 4.0:
                painter.save()
                painter.translate(at[0], at[1])
                painter.rotate(-rotation)

                # Use a fixed reference font size (e.g. 10pt) to avoid creating tiny fonts
                ref_pt_size = 10.0
                font = self._kicad_font(ref_pt_size)
                
                fm = QFontMetricsF(font)
                ref_h = fm.height()
                ref_w = fm.horizontalAdvance(number_text)
                
                if ref_h > 0:
                    # Calculate scale to fit target height
                    scale = target_h / ref_h
                    
                    # Check width fit
                    avail_w = size[0] * 0.9
                    if (ref_w * scale) > avail_w:
                        scale = avail_w / ref_w
                    
                    painter.scale(scale, scale)
                    painter.setFont(font)
                    
                    # Contrast color
                    if "thru_hole" in ptype:
                        painter.setPen(QColor("white"))
                    else:
                        # For SMD, we assume the pad color is the background for the text.
                        # Since we are drawing text separately, we need to know the pad color.
                        # Defaulting to F.Cu color logic for contrast calculation
                        bg = self.layer_colors.get("F.Cu")
                        if "B.Cu" in p.get("layers", []):
                             bg = self.layer_colors.get("B.Cu")
                        
                        lum = 0.2126*bg.red() + 0.7152*bg.green() + 0.0722*bg.blue()
                        painter.setPen(QColor("black") if lum > 128 else QColor("white"))
                    
                    # Draw centered. Since we scaled around 0,0 (pad center), 
                    # we draw text centered at 0,0 in the scaled coordinate system.
                    draw_rect = QRectF(-ref_w, -ref_h, 2*ref_w, 2*ref_h)
                    painter.drawText(draw_rect, Qt.AlignCenter, number_text)
                
                painter.restore()

    def _draw_primitive(self, painter, prim):
        ptype = prim.get('type')
        if ptype == 'gr_poly':
            pts = prim.get('pts', [])
            if pts:
                qpoly = [QPointF(p[0], p[1]) for p in pts]
                painter.drawPolygon(qpoly)
        elif ptype == 'gr_circle':
            center = prim.get('center', [0,0])
            end = prim.get('end', [0,0])
            radius = math.sqrt((end[0]-center[0])**2 + (end[1]-center[1])**2)
            width = prim.get('width', 0)
            if width > 0:
                pen = QPen(painter.brush().color())
                pen.setWidthF(width)
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)
                painter.drawEllipse(QPointF(center[0], center[1]), radius, radius)
                # Restore
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(pen.color()))
            else:
                painter.drawEllipse(QPointF(center[0], center[1]), radius, radius)
        elif ptype == 'gr_line':
            start = prim.get('start', [0,0])
            end = prim.get('end', [0,0])
            width = prim.get('width', 0)
            pen = QPen(painter.brush().color())
            if width > 0: pen.setWidthF(width)
            painter.setPen(pen)
            painter.drawLine(QPointF(start[0], start[1]), QPointF(end[0], end[1]))
            painter.setPen(Qt.NoPen) # Restore
        elif ptype == 'gr_arc':
            start = prim.get('start')
            mid = prim.get('mid')
            end = prim.get('end')
            width = prim.get('width', 0)
            
            if start and mid and end:
                # 3-point arc calculation
                x1, y1 = start[0], start[1]
                x2, y2 = mid[0], mid[1]
                x3, y3 = end[0], end[1]
                
                D = 2 * (x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2))
                if D != 0:
                    Ux = ((x1**2 + y1**2) * (y2 - y3) + (x2**2 + y2**2) * (y3 - y1) + (x3**2 + y3**2) * (y1 - y2)) / D
                    Uy = ((x1**2 + y1**2) * (x3 - x2) + (x2**2 + y2**2) * (x1 - x3) + (x3**2 + y3**2) * (x2 - x1)) / D
                    center = QPointF(Ux, Uy)
                    radius = math.sqrt((x1 - Ux)**2 + (y1 - Uy)**2)
                    
                    # Calculate angles (Y is NOT flipped here because we are in local pad coords which are already transformed or consistent)
                    # Note: In _draw_pad we rotated the painter. The primitive coords are local.
                    # Standard math.atan2(y, x) works for standard Cartesian. 
                    # KiCad Y is down. Qt Y is down.
                    start_angle = math.degrees(math.atan2(y1 - Uy, x1 - Ux))
                    mid_angle = math.degrees(math.atan2(y2 - Uy, x2 - Ux))
                    end_angle = math.degrees(math.atan2(y3 - Uy, x3 - Ux))
                    
                    start_n = start_angle % 360
                    mid_n = mid_angle % 360
                    end_n = end_angle % 360
                    
                    span_end = (end_n - start_n) % 360
                    span_mid = (mid_n - start_n) % 360
                    
                    if span_mid > span_end: # If mid is not between start and end in CCW direction, go CW
                        span_end -= 360
                        
                    pen = QPen(painter.brush().color())
                    if width > 0: pen.setWidthF(width)
                    painter.setPen(pen)
                    painter.setBrush(Qt.NoBrush)
                    painter.drawArc(QRectF(center.x() - radius, center.y() - radius, radius*2, radius*2), int(-start_angle * 16), int(-span_end * 16))
                    
                    # Restore
                    painter.setPen(Qt.NoPen)
                    painter.setBrush(QBrush(pen.color()))

    def _draw_graphic(self, painter, l):
            layer_name = l.get('layer', 'F.Fab')
            color = self.layer_colors.get(layer_name, QColor("white"))
            pen = QPen(color)
            pen.setWidthF(l.get('width', 0.1))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            
            if l.get('type') == 'zone':
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(color, Qt.SolidPattern))
            else:
                painter.setPen(pen)
                painter.setBrush(Qt.NoBrush)

            head = l.get('type')
            if head == "fp_line":
                start = l.get('start')
                end = l.get('end')
                if start and end:
                    painter.drawLine(QPointF(start[0], start[1]), QPointF(end[0], end[1]))
            elif head == "fp_rect":
                start = l.get('start')
                end = l.get('end')
                if start and end:
                    painter.drawRect(QRectF(QPointF(start[0], start[1]), QPointF(end[0], end[1])))
            elif head == "fp_circle":
                center = l.get('center')
                end = l.get('end')
                if center and end:
                    radius = math.sqrt((end[0]-center[0])**2 + (end[1]-center[1])**2)
                    painter.drawEllipse(QPointF(center[0], center[1]), radius, radius)
            elif head == "fp_arc":
                center = l.get('center'); end = l.get('end'); angle = l.get('angle')
                if center and end and angle is not None:
                    radius = math.sqrt((end[0]-center[0])**2 + (end[1]-center[1])**2)
                    start_angle = math.degrees(math.atan2(end[1] - center[1], end[0] - center[0]))
                    span_angle = -angle # KiCad angle is CW, Qt is CCW
                    rect = QRectF(center[0] - radius, center[1] - radius, 2*radius, 2*radius)
                    painter.drawArc(rect, int(start_angle * 16), int(span_angle * 16))
            elif head in ["fp_poly", "zone"]:
                pts = l.get('pts')
                if pts:
                    qpoly = [QPointF(p[0], p[1]) for p in pts]
                    painter.drawPolygon(qpoly)

    def _draw_measurement_ui(self, painter):
        pen = QPen(QColor("#3498db")) # Blue
        pen.setWidthF(0.1) # Use a thin line in logical units
        pen.setStyle(Qt.DashLine)
        painter.setPen(pen)
        
        # Draw snap-to-pad highlight
        if self.hover_pos:
            snap_pos, pad_num = self._snap_to_pad(self.hover_pos)
            if pad_num:
                painter.drawEllipse(snap_pos, 0.5, 0.5)

        # Draw line and text
        if len(self.measure_points) == 2:
            p1, p2 = self.measure_points
            painter.drawLine(p1, p2)
            
            dist = math.sqrt((p2.x() - p1.x())**2 + (p2.y() - p1.y())**2)
            
            painter.save()
            painter.translate((p1 + p2) / 2)
            painter.scale(1 / self.view_scale, 1 / self.view_scale)
            
            text = f"{dist:.3f} mm"
            fm = painter.fontMetrics()
            text_rect = fm.boundingRect(text)
            text_rect.moveCenter(QPoint(0, -10))
            
            painter.setBrush(QColor(51, 51, 51, 200))
            painter.setPen(Qt.NoPen)
            painter.drawRect(text_rect.adjusted(-4, -2, 4, 2))
            
            painter.setPen(QColor("white"))
            painter.drawText(text_rect, Qt.AlignCenter, text)
            painter.restore()
        
        elif len(self.measure_points) == 1 and self.hover_pos:
            painter.drawLine(self.measure_points[0], self.hover_pos)

    def _draw_scale_bar(self, painter):
        if self.view_scale <= 0:
            return
        # Draw in screen coordinates
        painter.save()
        painter.resetTransform()

        # Pick a scale length that fits ~20% of the width
        max_px = int(self.width() * 0.22)
        length_mm, length_px = self._pick_scale_length(max_px)
        if length_px < 20:
            painter.restore()
            return

        margin = 12
        bar_height = 4
        x2 = self.width() - margin
        x1 = x2 - length_px
        y = self.height() - margin

        # Bar background
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.drawRoundedRect(QRectF(x1 - 6, y - 20, length_px + 12, 22), 6, 6)
        self._scale_bar_bottom_reserved = 26

        # Bar
        painter.setBrush(QColor("#E0E0E0"))
        painter.drawRect(QRectF(x1, y - bar_height, length_px, bar_height))

        # End ticks
        pen = QPen(QColor("#E0E0E0"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(QPoint(x1, y - bar_height - 6), QPoint(x1, y + 2))
        painter.drawLine(QPoint(x2, y - bar_height - 6), QPoint(x2, y + 2))

        # Label
        painter.setPen(QColor("#FFFFFF"))
        label = f"{length_mm:g} mm"
        fm = QFontMetrics(painter.font())
        text_w = fm.horizontalAdvance(label)
        painter.drawText(int((x1 + x2) / 2 - text_w / 2), y - 8, label)

        painter.restore()

    def _draw_vertical_scale(self, painter):
        if self.view_scale <= 0:
            return
        painter.save()
        painter.resetTransform()

        max_px = int(self.height() * 0.22)
        length_mm, length_px = self._pick_scale_length(max_px)
        if length_px < 14:
            painter.restore()
            return

        margin = 12
        bottom_reserved = getattr(self, "_scale_bar_bottom_reserved", 0)
        bar_w = 4
        x = self.width() - margin - bar_w
        y2 = self.height() - margin - bottom_reserved
        y1 = y2 - length_px

        label = f"{length_mm:g} mm"
        fm = QFontMetrics(painter.font())
        text_w = fm.horizontalAdvance(label)

        bg_left = x - 6 - text_w - 6
        bg_top = y1 - 8
        bg_right = x + bar_w + 6
        bg_height = length_px + 16

        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(0, 0, 0, 120))
        painter.drawRoundedRect(QRectF(bg_left, bg_top, bg_right - bg_left, bg_height), 6, 6)

        painter.setBrush(QColor("#E0E0E0"))
        painter.drawRect(QRectF(x, y1, bar_w, length_px))

        pen = QPen(QColor("#E0E0E0"))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawLine(QPoint(x, y1), QPoint(x + bar_w, y1))
        painter.drawLine(QPoint(x, y2), QPoint(x + bar_w, y2))
        tick_mid = y1 + length_px / 2
        painter.drawLine(QPoint(x, tick_mid), QPoint(x + bar_w, tick_mid))

        painter.setPen(QColor("#FFFFFF"))
        label_rect = QRectF(x - text_w - 6, y1 - 2, text_w + 4, length_px + 4)
        painter.drawText(label_rect, Qt.AlignVCenter | Qt.AlignRight, label)

        painter.restore()

    def map_screen_to_logical(self, screen_pos):
        w, h = self.width(), self.height()
        if self.view_scale == 0: return QPointF(0,0)
        
        x = screen_pos.x() - w/2
        y = screen_pos.y() - h/2
        
        x /= self.view_scale
        y /= self.view_scale
        
        x += self.view_center.x()
        y += self.view_center.y()
        
        return QPointF(x, y)

    def _snap_to_pad(self, pos):
        if not self.data or not self.data.get("pads"):
            return pos, None
            
        min_dist_sq = float('inf')
        snap_pos = pos
        snap_pad = None
        
        for pad in self.data.get("pads"):
            pad_pos = QPointF(pad['at'][0], pad['at'][1])
            dist_sq = (pos.x() - pad_pos.x())**2 + (pos.y() - pad_pos.y())**2
            if dist_sq < min_dist_sq:
                min_dist_sq = dist_sq
                snap_pos = pad_pos
                snap_pad = pad.get("number")
        
        if math.sqrt(min_dist_sq) < 2.0:
            return snap_pos, snap_pad
        return pos, None

    def mousePressEvent(self, event):
        if self.measure_mode and event.button() == Qt.LeftButton:
            logical_pos = self.map_screen_to_logical(event.position())
            snapped_pos, _ = self._snap_to_pad(logical_pos)
            
            if len(self.measure_points) == 1:
                self.measure_points.append(snapped_pos)
            else:
                self.measure_points = [snapped_pos]
            
            self.update()
            event.accept()
        elif event.button() == Qt.LeftButton or event.button() == Qt.MiddleButton:
            self.is_panning = True
            self.last_mouse_pos = event.position()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()

    def mouseMoveEvent(self, event):
        if self.is_panning:
            delta = event.position() - self.last_mouse_pos
            self.last_mouse_pos = event.position()
            dx = delta.x() / self.view_scale
            dy = delta.y() / self.view_scale
            self.view_center -= QPointF(dx, dy)
            self.update()
            event.accept()
        elif self.measure_mode:
            self.hover_pos = self.map_screen_to_logical(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.is_panning:
            self.is_panning = False
            self.setCursor(Qt.ArrowCursor if not self.measure_mode else Qt.CrossCursor)
            event.accept()
