import os
import re
import re
import re
import re
import shutil
import copy
import json
from datetime import datetime
from pathlib import Path
from collections import defaultdict

from backend.parser import KiCadParser
from kanban_templates import columns_from_templates

class ProjectManager:
    """Manages project-specific data, registry, and actions."""
    def __init__(self, logic):
        self.logic = logic
        self.bom_service = logic.bom_service
        self.project_index = defaultdict(list)
        self.project_usage_counts = defaultdict(lambda: defaultdict(int))
        self.footprint_index = defaultdict(list)
        self.footprint_parts = defaultdict(list)
        self._schematic_cache_path = self.logic.cache_dir / "schematic_cache.json"
        self._schematic_cache = self._load_schematic_cache()

    def get_project_data(self, identifier):
        """
        Retrieves or initializes project-specific data from the project_registry.
        If the project doesn't exist, it creates a new entry with default values
        and populates Kanban 'todo' with a standard template.
        """
        if "project_registry" not in self.logic.settings:
            self.logic.settings["project_registry"] = {}
        
        if identifier not in self.logic.settings["project_registry"]:
            p_type = "PCB"
            templates = self.logic.settings.get("kanban_templates", {})
            raw_tasks = templates.get(p_type, templates.get("Standard", []))

            self.logic.settings["project_registry"][identifier] = {
                "metadata": {
                    "name": identifier,
                    "location": "",
                    "status": "Pre-Design",
                    "revision": "A",
                    "type": p_type,
                    "description": "",
                    "main_schematic": "",
                    "layout_file": "",
                    "tags": []
                },
                "kanban": columns_from_templates(raw_tasks),
                "bom_pricing": {},
                "checklist": {},
                "test_plan": self._default_test_plan()
            }
            self.logic.save_settings()
            
        data = self.logic.settings["project_registry"][identifier]
        
        meta = data.get("metadata", {})
        loc = meta.get("location", "")
        main_sch = meta.get("main_schematic", "")
        layout_file = meta.get("layout_file", "")

        if "test_plan" not in data or not isinstance(data.get("test_plan"), dict):
            data["test_plan"] = self._default_test_plan()
            self.logic.save_settings()

        if loc and os.path.exists(loc):
            if not main_sch or not os.path.exists(main_sch):
                candidates = [
                    Path(loc) / f"{identifier}.kicad_sch",
                    Path(loc) / f"{Path(loc).name}.kicad_sch"
                ]
                
                found = None
                for c in candidates:
                    if c.exists():
                        found = c
                        break
                
                if not found:
                    sch_files = list(Path(loc).glob("*.kicad_sch"))
                    if len(sch_files) == 1:
                        found = sch_files[0]
                    elif len(sch_files) > 1:
                        pro_files = list(Path(loc).glob("*.kicad_pro"))
                        if pro_files:
                            pro_name = pro_files[0].stem
                            for s in sch_files:
                                if s.stem == pro_name:
                                    found = s
                                    break
                
                if found:
                    meta["main_schematic"] = str(found).replace("\\", "/")
                    self.logic.save_settings()

            if not layout_file or not os.path.exists(layout_file):
                pcb_candidates = [
                    Path(loc) / f"{identifier}.kicad_pcb",
                    Path(loc) / f"{Path(loc).name}.kicad_pcb"
                ]
                pcb_found = None
                for c in pcb_candidates:
                    if c.exists():
                        pcb_found = c
                        break

                if not pcb_found:
                    pcb_files = list(Path(loc).glob("*.kicad_pcb"))
                    if len(pcb_files) == 1:
                        pcb_found = pcb_files[0]
                    elif len(pcb_files) > 1:
                        pro_files = list(Path(loc).glob("*.kicad_pro"))
                        if pro_files:
                            pro_name = pro_files[0].stem
                            for p in pcb_files:
                                if p.stem == pro_name:
                                    pcb_found = p
                                    break

                if pcb_found:
                    meta["layout_file"] = str(pcb_found).replace("\\", "/")
                    self.logic.save_settings()

        return data

    def _default_test_plan(self):
        return {
            "cases": [],
            "config": {
                "categories": [
                    "Functional",
                    "Electrical",
                    "Firmware",
                    "Mechanical",
                    "Safety",
                    "Manufacturing",
                    "Regression",
                ],
                "priorities": ["Critical", "High", "Normal", "Low"],
                "types": ["Unit", "Subsystem", "System", "Integration", "Regression", "Validation"],
            },
        }

    def index_projects(self):
        """
        Indexes which symbols are used in which projects.
        Populates self.project_index (lib_id -> [project_names]) and records per-project counts.
        """
        self.project_index.clear()
        self.project_usage_counts.clear()
        self.footprint_index.clear()
        self.footprint_parts.clear()
        registry = self.logic.settings.get("project_registry", {})
        cache_dirty = False
        active_paths = set()
        for proj_name, data in registry.items():
            p_path = data.get("metadata", {}).get("location", "")
            if not p_path or not os.path.exists(p_path):
                continue
            
            proj = proj_name or Path(p_path).stem
            for sch_file in Path(p_path).rglob("*.kicad_sch"):
                try:
                    path_key = self.logic.normalize_path(str(sch_file.resolve()))
                except Exception:
                    continue
                active_paths.add(path_key)
                try:
                    mtime = sch_file.stat().st_mtime
                except Exception:
                    continue
                cache_entry = self._schematic_cache.get(path_key)
                if not cache_entry or cache_entry.get("mtime") != mtime:
                    try:
                        components, _ = KiCadParser.parse_schematic(sch_file)
                    except Exception:
                        continue
                    processed = []
                    for comp in components:
                        processed.append({
                            "lib_id": comp.get("lib_id", ""),
                            "footprint": comp.get("footprint", ""),
                            "ref": comp.get("ref", ""),
                        })
                    cache_entry = {"mtime": mtime, "components": processed}
                    self._schematic_cache[path_key] = cache_entry
                    cache_dirty = True
                for comp in cache_entry.get("components", []):
                    lib_id = comp.get('lib_id', '')
                    if lib_id:
                        if proj not in self.project_index[lib_id]:
                            self.project_index[lib_id].append(proj)
                        self.project_usage_counts[lib_id][proj] += 1
                    footprint_ref = comp.get('footprint', '')
                    ref = comp.get('ref', '')
                    if footprint_ref:
                        if proj not in self.footprint_index[footprint_ref]:
                            self.footprint_index[footprint_ref].append(proj)
                        if ref and ref not in self.footprint_parts[footprint_ref]:
                            self.footprint_parts[footprint_ref].append(ref)
                        self.project_usage_counts[footprint_ref][proj] += 1
                cache_dirty = cache_dirty or (cache_entry.get("mtime") != mtime)
        removed = set(self._schematic_cache.keys()) - active_paths
        if removed:
            cache_dirty = True
            for key in removed:
                self._schematic_cache.pop(key, None)
        if cache_dirty:
            self._save_schematic_cache()

    def get_projects_using_footprint(self, ref):
        return list(self.footprint_index.get(ref, []))

    def get_parts_using_footprint(self, ref):
        return list(self.footprint_parts.get(ref, []))

    def clone_project(self, source_name, new_name):
        """Clones an existing project registry entry to a new name."""
        if source_name in self.logic.settings["project_registry"]:
            data = copy.deepcopy(self.logic.settings["project_registry"][source_name])
            data["metadata"]["name"] = new_name
            data["metadata"]["location"] = ""
            data["metadata"]["status"] = "Pre-Design"
            self.logic.settings["project_registry"][new_name] = data
            if new_name not in self.logic.settings["projects"]:
                self.logic.settings["projects"].append(new_name)
            self.logic.save_settings()
            return True
        return False

    def archive_project(self, name):
        """Sets project status to Archived."""
        if name in self.logic.settings["project_registry"]:
            self.logic.settings["project_registry"][name]["metadata"]["status"] = "Archived"
            self.logic.save_settings()

    def create_gitignore(self, path):
        """Creates a standard KiCad .gitignore file in the specified path."""
        content = "# KiCad\n*.lck\n*.kicad_prl\n*.kicad_pcb-bak\n*.kicad_sch-bak\nfp-info-cache\n*-backups/\n_autosave-*\n*.zip\n*.iso\n"
        try:
            with open(os.path.join(path, ".gitignore"), "w") as f:
                f.write(content)
            return True
        except: return False

    def toggle_pin(self, name):
        """Toggles the pinned status of a project."""
        if name in self.logic.settings["project_registry"]:
            meta = self.logic.settings["project_registry"][name]["metadata"]
            meta["pinned"] = not meta.get("pinned", False)
            self.logic.save_settings()
            return meta["pinned"]
        return False

    def clean_project(self, name):
        """Removes temporary and backup files from the project directory."""
        if name not in self.logic.settings["project_registry"]: return 0
        loc = self.logic.settings["project_registry"][name]["metadata"].get("location", "")
        if not loc or not os.path.exists(loc): return 0
        
        patterns = ["*.bak", "*.kicad_prl", "*.kicad_pcb-bak", "*.kicad_sch-bak", "fp-info-cache", "_autosave-*", "*.bck"]
        count = 0
        for p in patterns:
            for f in Path(loc).rglob(p):
                try:
                    if f.is_file(): os.remove(f)
                    elif f.is_dir(): shutil.rmtree(f)
                    count += 1
                except: pass
        return count

    def _load_schematic_cache(self):
        try:
            if self._schematic_cache_path.exists():
                with open(self._schematic_cache_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    return data
        except Exception:
            pass
        return {}

    def _save_schematic_cache(self):
        try:
            self._schematic_cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._schematic_cache_path, "w", encoding="utf-8") as f:
                json.dump(self._schematic_cache, f, indent=2)
        except Exception:
            pass

    def get_subsheets(self, root_path):
        if not root_path or not os.path.exists(root_path): return []
        
        found_sheets = set()
        to_scan = [str(Path(root_path).resolve())]
        
        while to_scan:
            current = to_scan.pop(0)
            if current in found_sheets: continue
            found_sheets.add(current)
            
            try:
                with open(current, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                sheets = re.findall(r'\(property\s+"Sheet(?:file| file)"\s+"([^"]+)"', content)
                sheets += re.findall(r'\(file\s+"([^"]+)"\)', content)

                for s in sheets:
                    sub_path = (Path(current).parent / s).resolve()
                    if sub_path.exists():
                        to_scan.append(str(sub_path))
            except: pass
            
        return sorted(list(found_sheets))

    def get_subsheets_hierarchy(self, root_path):
        if not root_path or not os.path.exists(root_path): return None
        
        def build_tree(path, visited):
            abs_path = str(Path(path).resolve())
            if abs_path in visited: 
                return {"name": Path(path).name + " (Recursive)", "path": abs_path, "children": [], "part_count": 0}
            
            visited.add(abs_path)
            
            part_count = 0
            try:
                comps, _ = KiCadParser.parse_schematic(path)
                part_count = len(comps)
            except: pass
            
            node = {"name": Path(path).name, "path": abs_path, "children": [], "part_count": part_count}
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                sheets = re.findall(r'\(property\s+"Sheet(?:file| file)"\s+"([^"]+)"', content)
                sheets += re.findall(r'\(file\s+"([^"]+)"\)', content)
                
                for s in sheets:
                    sub_path = (Path(path).parent / s).resolve()
                    if sub_path.exists():
                        child = build_tree(str(sub_path), visited.copy())
                        if child: node["children"].append(child)
            except: pass
            
            node["children"].sort(key=lambda x: x["name"].lower())
            return node

        return build_tree(root_path, set())

    def generate_bom(self, root_sch_path):
        """Proxy to BOMService so callers keep working."""
        return self.bom_service.generate_bom(root_sch_path)
