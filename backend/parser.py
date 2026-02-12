import re
import shutil
import logging
from pathlib import Path
from datetime import datetime

class KiCadParser:
    # Regex to capture S-expression tokens: parentheses, quoted strings, or plain symbols
    TOKEN_RE = re.compile(r'\(|\)|"(?:\\.|[^"\\])*"|[^\s()]+')

    @staticmethod
    def parse_s_expression(content):
        """Parses KiCad S-Expression strings into a nested list structure."""
        if not content.strip():
            print("DEBUG: [S-Expr] Content is empty.")
            return []

        stack = [[]]
        for match in KiCadParser.TOKEN_RE.finditer(content):
            token = match.group(0)
            if token == '(':
                new_list = []
                stack[-1].append(new_list)
                stack.append(new_list)
            elif token == ')':
                if len(stack) > 1:
                    stack.pop()
                else:
                    print("DEBUG: [S-Expr] Warning: Unbalanced closing parenthesis.")
            elif token.startswith('"'):
                # Strip quotes and handle escaped internal quotes
                stack[-1].append(token[1:-1].replace('\\"', '"'))
            else:
                stack[-1].append(token)

        if len(stack) != 1:
            print(f"DEBUG: [S-Expr] Warning: Unbalanced nesting level ({len(stack)-1}).")

        return stack[0][0] if stack[0] else []

    @staticmethod
    def parse_libraries(root_paths):
        file_cache = {}
        for root in root_paths:
            for lib_file in Path(root).rglob("*.kicad_sym"):
                symbols = KiCadParser.parse_lib_full(lib_file)
                if symbols:
                    file_cache[str(lib_file)] = {"symbols": symbols}
        return file_cache


    @staticmethod
    def parse_lib_full(file_path):
        """Extracts all symbols and properties from a KiCad symbol library (.kicad_sym)."""
        symbols = []
        path = Path(file_path)
        lib_name = path.stem
        print(f"DEBUG: [Library] --- Parsing: {lib_name} ---")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            data = KiCadParser.parse_s_expression(content)
            
            if not data or data[0] != 'kicad_symbol_lib':
                print(f"DEBUG: [Library] Header mismatch in {lib_name}. (Found: {data[0] if data else 'None'})")
                return []

            for item in data[1:]:
                if isinstance(item, list) and item[0] == 'symbol':
                    sym_data = {
                        "library": lib_name,
                        "name": item[1],
                            "extends": None,
                        "file_path": str(file_path),
                        "properties": {},
                        "pins": [],
                        "graphics": [],
                        "show_pin_numbers": None,
                        "show_pin_names": None,
                        "pin_names_offset": None,
                        "visual_properties": []
                    }

                    def recursive_extract(node_list):
                        for node in node_list:
                            if not isinstance(node, list) or not node:
                                continue
                            
                            head = node[0]
                            if head == "property" and len(node) >= 3:
                                sym_data["properties"][node[1]] = node[2]
                                if node[1] in ["Reference", "Value"]:
                                    sym_data["visual_properties"].append(node)
                            elif head == "symbol":
                                recursive_extract(node)
                            elif head == "extends":
                                sym_data["extends"] = node[1]
                            elif head == "pin_numbers":
                                sym_data["show_pin_numbers"] = True
                                for attr in node[1:]:
                                    if attr == "hide" or (isinstance(attr, list) and len(attr) > 0 and attr[0] == "hide"):
                                        sym_data["show_pin_numbers"] = False
                            elif head == "pin_names":
                                sym_data["show_pin_names"] = True
                                for attr in node[1:]:
                                    if attr == "hide" or (isinstance(attr, list) and len(attr) > 0 and attr[0] == "hide"):
                                        sym_data["show_pin_names"] = False
                                    elif isinstance(attr, list) and attr[0] == "offset":
                                        try:
                                            sym_data["pin_names_offset"] = float(attr[1])
                                        except: pass
                            # Inside parser.py -> parse_lib_full -> extract function
                            elif head == "pin":
                                # Initialize with a default length of 2.54mm (100 mils) if not found
                                pin = {"type": node[1], "at": [0,0,0], "number": "?", "name": "", "length": 2.54, "visible": True, "name_visible": True, "num_visible": True, "name_text_size": 1.27, "num_text_size": 1.27, "stroke_width": None}
                                for attr in node:
                                    if attr == "hide" or (isinstance(attr, list) and len(attr) > 0 and attr[0] == "hide"):
                                        pin["visible"] = False
                                    elif isinstance(attr, list):
                                        if attr[0] == "at": 
                                            pin["at"] = [float(x) for x in attr[1:]]
                                        elif attr[0] == "number": 
                                            pin["number"] = attr[1]
                                            for sub in attr[2:]:
                                                if isinstance(sub, list) and sub[0] == "effects":
                                                    for effect in sub[1:]:
                                                        if effect == "hide" or (isinstance(effect, list) and len(effect) > 0 and effect[0] == "hide"):
                                                            pin["num_visible"] = False
                                                        elif isinstance(effect, list) and effect[0] == "font":
                                                            for f in effect[1:]:
                                                                if isinstance(f, list) and f[0] == "size":
                                                                    try:
                                                                        if len(f) > 1: pin["num_text_size"] = float(f[1])
                                                                    except: pass
                                        elif attr[0] == "name":
                                            pin["name"] = attr[1]
                                            for sub in attr[2:]:
                                                if isinstance(sub, list) and sub[0] == "effects":
                                                    for effect in sub[1:]:
                                                        if effect == "hide" or (isinstance(effect, list) and len(effect) > 0 and effect[0] == "hide"):
                                                            pin["name_visible"] = False
                                                        elif isinstance(effect, list) and effect[0] == "font":
                                                            for f in effect[1:]:
                                                                if isinstance(f, list) and f[0] == "size":
                                                                    try:
                                                                        if len(f) > 1: pin["name_text_size"] = float(f[1])
                                                                    except: pass
                                        elif attr[0] == "length":  # Add this check
                                            pin["length"] = float(attr[1])
                                        elif attr[0] == "stroke":
                                            for s_attr in attr[1:]:
                                                if isinstance(s_attr, list) and s_attr[0] == "width" and len(s_attr) > 1:
                                                    try:
                                                        pin["stroke_width"] = float(s_attr[1])
                                                    except: pass
                                        elif attr[0] == "width" and len(attr) > 1:
                                            # Some legacy formats may store width directly
                                            try:
                                                pin["stroke_width"] = float(attr[1])
                                            except: pass
                                sym_data["pins"].append(pin)
                            elif head in ["rectangle", "polyline", "circle", "arc", "text"]:
                                sym_data["graphics"].append(node)

                    recursive_extract(item)
                    symbols.append(sym_data)

            print(f"DEBUG: [Library] {lib_name} parsed. Symbols found: {len(symbols)}")
            
        except Exception as e:
            print(f"DEBUG: [Library] CRITICAL ERROR in {lib_name}: {e}")
        
        return symbols

    @staticmethod
    def parse_footprint_full(file_path):
        """Parses a KiCad footprint (.kicad_mod) for geometry and 3D model paths."""
        path = Path(file_path)
        geom = {"pads": [], "lines": [], "model_path": None, "file_path": str(file_path)}
        print(f"DEBUG: [Footprint] Parsing: {path.name}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            data = KiCadParser.parse_s_expression(content)

            # The top level is ['footprint', 'name', [...sub-elements]]
            # We need to iterate through the sub-elements
            elements = []
            if data and data[0] == 'footprint':
                elements = data[2:] # Skip 'footprint' and the name

            for item in elements:
                if not isinstance(item, list) or not item: continue
                head = item[0]
                if head == 'pad' and len(item) >= 3:
                    pad_shape = item[3] if len(item) > 3 and isinstance(item[3], str) else "rect"
                    pad = {"number": str(item[1]), "type": item[2], "shape": pad_shape, "layers": [], "at": [0.0, 0.0], "size": [0.0, 0.0], "drill": 0.0, "anchor_shape": "rect", "roundrect_rratio": 0.25}
                    for attr in item:
                        if isinstance(attr, list):
                            if attr[0] == 'at': pad['at'] = [float(x) for x in attr[1:]]
                            elif attr[0] == 'size': pad['size'] = [float(attr[1]), float(attr[2])]
                            elif attr[0] == 'layers': 
                                pad['layers'] = attr[1:]
                                # Expand wildcards for easier UI handling
                                if "*.Cu" in pad['layers']:
                                    pad['layers'].extend(["F.Cu", "B.Cu"])
                                if "*.Mask" in pad['layers']:
                                    pad['layers'].extend(["F.Mask", "B.Mask"])
                            elif attr[0] == 'drill':
                                # Handle (drill 0.8) or (drill oval 1.2 0.8)
                                if len(attr) == 2:
                                    try:
                                        d = float(attr[1])
                                        pad['drill'] = {'shape': 'circle', 'size': [d, d]}
                                    except: pass
                                elif len(attr) >= 3 and attr[1] == 'oval':
                                    try:
                                        w = float(attr[2])
                                        h = float(attr[3]) if len(attr) > 3 else w
                                        pad['drill'] = {'shape': 'oval', 'size': [w, h]}
                                    except: pass
                            elif attr[0] == 'roundrect_rratio':
                                try: pad['roundrect_rratio'] = float(attr[1])
                                except: pass
                            elif attr[0] == 'options':
                                for opt in attr[1:]:
                                    if isinstance(opt, list) and opt[0] == 'anchor':
                                        pad['anchor_shape'] = opt[1]
                            elif attr[0] == 'primitives':
                                pad['primitives'] = []
                                for prim in attr[1:]:
                                    if isinstance(prim, list):
                                        prim_data = {'type': prim[0]}
                                        for p_attr in prim:
                                            if isinstance(p_attr, list):
                                                if p_attr[0] == 'pts':
                                                    prim_data['pts'] = [[float(xy[1]), float(xy[2])] for xy in p_attr[1:] if isinstance(xy, list) and xy[0] == 'xy']
                                                elif p_attr[0] == 'width':
                                                    try: prim_data['width'] = float(p_attr[1])
                                                    except: pass
                                                elif p_attr[0] in ['start', 'end', 'center', 'mid']: prim_data[p_attr[0]] = [float(x) for x in p_attr[1:]]
                                                elif p_attr[0] in ['radius', 'angle']: prim_data[p_attr[0]] = float(p_attr[1])
                                        pad['primitives'].append(prim_data)
                    geom['pads'].append(pad)
                elif head in ['fp_line', 'fp_rect', 'fp_circle', 'fp_arc', 'fp_poly', 'zone']:
                    shape = {'type': head, 'layer': 'F.Fab', 'width': 0.15, 'pts': []}
                    for attr in item:
                        if isinstance(attr, list):
                            if attr[0] == 'layer': shape['layer'] = attr[1]
                            elif attr[0] == 'width': shape['width'] = float(attr[1])
                            elif attr[0] == 'start': shape['start'] = [float(x) for x in attr[1:]]
                            elif attr[0] == 'end': shape['end'] = [float(x) for x in attr[1:]]
                            elif attr[0] == 'center': shape['center'] = [float(x) for x in attr[1:]]
                            elif attr[0] == 'angle': shape['angle'] = float(attr[1])
                            elif attr[0] == 'pts':
                                shape['pts'] = [[float(xy[1]), float(xy[2])] for xy in attr[1:] if isinstance(xy, list) and xy[0] == 'xy']
                    geom['lines'].append(shape)
                elif head == 'model' and len(item) >= 2:
                    geom['model_path'] = item[1]

            print(f"DEBUG: [Footprint] {path.name} parsed. Pads: {len(geom['pads'])}, Lines: {len(geom['lines'])}")
            
        except Exception as e:
            print(f"DEBUG: [Footprint] Error parsing {path.name}: {e}")
            
        return geom

    @staticmethod
    def parse_schematic(file_path):
        """Extracts components and sheets from a KiCad schematic (.kicad_sch)."""
        components = []
        sheets = []
        path = Path(file_path)
        print(f"DEBUG: [Schematic] Extracting BOM from: {path.name}")

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            data = KiCadParser.parse_s_expression(content)
            
            for item in data:
                if isinstance(item, list):
                    if item[0] == 'symbol':
                        comp = {"ref": "", "value": "", "lib_id": "", "exclude_from_bom": False, "dnp": False, "is_power_symbol": False, "instances": []}
                        is_power_symbol = False
                        for sub in item:
                            if isinstance(sub, list):
                                if sub[0] == 'lib_id': 
                                    comp['lib_id'] = sub[1]
                                elif sub[0] == 'property' and len(sub) >= 3:
                                    if sub[1] == 'Reference': comp['ref'] = sub[2]
                                    elif sub[1] == 'Value': comp['value'] = sub[2]
                                    elif sub[1] == 'Footprint': comp['footprint'] = sub[2]
                                elif sub[0] == 'attr':
                                    if 'exclude_from_bom' in sub:
                                        comp['exclude_from_bom'] = True
                                    if 'dnp' in sub:
                                        comp['dnp'] = True
                                elif sub[0] == 'dnp':
                                    if len(sub) > 1 and sub[1] == 'yes':
                                        comp['dnp'] = True
                                elif sub[0] == 'in_bom':
                                    if len(sub) > 1 and sub[1] == 'no':
                                        comp['exclude_from_bom'] = True
                                elif sub[0] == 'power':
                                    comp['is_power_symbol'] = True
                                elif sub[0] == 'instances':
                                    comp['instances'] = sub
                        
                        if comp['ref']:
                            components.append(comp)

                    elif item[0] == 'sheet':
                        sheet = {'uuid': '', 'filename': ''}
                        for sub in item:
                            if isinstance(sub, list):
                                if sub[0] == 'uuid': sheet['uuid'] = sub[1]
                                elif sub[0] == 'property' and len(sub) >= 3:
                                    if sub[1] in ["Sheetfile", "Sheet file"]: sheet['filename'] = sub[2]
                                elif sub[0] == 'file':
                                    sheet['filename'] = sub[1]
                        if sheet['filename']:
                            sheets.append(sheet)

            print(f"DEBUG: [Schematic] {path.name} finished. Found {len(components)} symbols.")
            
        except Exception as e:
            print(f"DEBUG: [Schematic] Error parsing {path.name}: {e}")
            
        return components, sheets

    @staticmethod
    def update_symbol_property(file_path, symbol_name, key, new_value):
        """Safely updates a symbol property on disk with an automatic backup."""
        try:
            path = Path(file_path)
            backup_path = path.with_suffix(f".{datetime.now().strftime('%Y%m%d_%H%M%S')}.bak")
            shutil.copy(file_path, backup_path)
            print(f"DEBUG: [Update] Backup created at {backup_path.name}")

            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            new_lines = []
            in_sym = False
            updated = False

            # Pattern to match: (property "Key" "Value")
            prop_pattern = re.compile(r'(\(property\s+"' + re.escape(key) + r'"\s+)"(.*?)"')

            for line in lines:
                stripped = line.strip()
                # Detection of specific symbol block
                if stripped.startswith(f'(symbol "{symbol_name}"'):
                    in_sym = True
                elif in_sym and stripped.startswith('(symbol '):
                    in_sym = False

                if in_sym and stripped.startswith(f'(property "{key}"'):
                    line = prop_pattern.sub(r'\1"' + str(new_value) + '"', line, count=1)
                    updated = True
                
                new_lines.append(line)

            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)

            print(f"DEBUG: [Update] Property '{key}' updated for '{symbol_name}'. Success: {updated}")
            return True, str(backup_path)
            
        except Exception as e:
            print(f"DEBUG: [Update] Error: {e}")
            return False, str(e)
