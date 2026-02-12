import os
import re
import json
import shutil
import copy
import hashlib
from datetime import datetime
from pathlib import Path
from collections import defaultdict

DEFAULT_TIME_TRACKER_CATEGORIES = {
    "Design": "#6366f1",
    "Layout": "#0ea5e9",
    "Review": "#f97316",
    "Support": "#22c55e",
    "Research": "#a855f7",
}

DEFAULT_TIME_TRACKER_TASKS = [
    {
        "name": "Schematic Capture",
        "category": "Design",
        "color": "#7c3aed",
        "description": "Place symbols, wire nets, and annotate the schematic for review.",
        "default_duration": 2.0,
        "tags": ["schematic", "capture"],
        "subtasks": [
            {"title": "Place Components", "estimate": 0.75},
            {"title": "Wire Nets", "estimate": 0.5},
            {"title": "Annotate Standards", "estimate": 0.25},
        ],
    },
    {
        "name": "Footprint Assignment",
        "category": "Layout",
        "color": "#2563eb",
        "description": "Match symbols to vetted footprints and verify variants.",
        "default_duration": 1.5,
        "tags": ["layout", "fp"],
        "subtasks": [
            {"title": "Verify Library", "estimate": 0.25},
            {"title": "Assign Footprints", "estimate": 0.75},
            {"title": "Lock References", "estimate": 0.25},
        ],
    },
    {
        "name": "PCB Routing",
        "category": "Layout",
        "color": "#0ea5e9",
        "description": "Route critical nets, define pours, and clean up traces.",
        "default_duration": 3.0,
        "tags": ["routing", "critical"],
        "subtasks": [
            {"title": "Define Stackup", "estimate": 0.25},
            {"title": "Route Critical Nets", "estimate": 1.5},
            {"title": "Auto-Routing Cleanup", "estimate": 0.75},
        ],
    },
    {
        "name": "Design Review",
        "category": "Review",
        "color": "#f97316",
        "description": "Run cross-team reviews, checklist walk-through, and approvals.",
        "default_duration": 1.0,
        "tags": ["review", "approval"],
        "subtasks": [
            {"title": "Review Checklist", "estimate": 0.5},
            {"title": "Update Notes", "estimate": 0.25},
            {"title": "Document Decisions", "estimate": 0.25},
        ],
    },
    {
        "name": "Documentation Sprint",
        "category": "Support",
        "color": "#22c55e",
        "description": "Capture BOM, notes, and update supporting docs for handoff.",
        "default_duration": 1.25,
        "tags": ["docs", "handoff"],
        "subtasks": [
            {"title": "Update BOM", "estimate": 0.5},
            {"title": "Notes & Learnings", "estimate": 0.35},
            {"title": "Team Sync", "estimate": 0.4},
        ],
    },
    {
        "name": "Research Spike",
        "category": "Research",
        "color": "#a855f7",
        "description": "Experiment with unfamiliar tools or new architectures.",
        "default_duration": 2.0,
        "tags": ["research", "explore"],
        "subtasks": [
            {"title": "Proof of Concept", "estimate": 1.5},
            {"title": "Collect Findings", "estimate": 0.5},
        ],
    },
]


def _build_default_time_task_library():
    return {
        "categories": [
            {"name": name, "color": color, "description": ""}
            for name, color in DEFAULT_TIME_TRACKER_CATEGORIES.items()
        ],
        "tasks": copy.deepcopy(DEFAULT_TIME_TRACKER_TASKS),
    }

try:
    from .parser import KiCadParser
    from .backup_manager import BackupManager
    from .project_manager import ProjectManager
    from .validator import Validator
    from .pricing_manager import PricingManager
    from .bom_manager import BOMService
    from .indexers import SymbolIndexer, FootprintIndexer
except ImportError:
    from parser import KiCadParser
    from backup_manager import BackupManager
    from project_manager import ProjectManager
    from validator import Validator
    from pricing_manager import PricingManager
    from bom_manager import BOMService
    from indexers import SymbolIndexer, FootprintIndexer
try:
    from .path_utils import PathResolver
    from .validation_service import ValidationService
    from .paths_config import PathsConfig
except ImportError:
    from path_utils import PathResolver
    from validation_service import ValidationService
    from paths_config import PathsConfig

class AppLogic:
    """
    Central application logic class. Manages settings, data storage,
    library scanning, and delegates to specialized managers.
    """
    LIB_CACHE_VERSION = 3
    FOOTPRINT_CACHE_VERSION = 1
    LIBRARY_SCAN_WORKERS = 4

    def __init__(
        self,
        parser=None,
        bom_service=None,
        backup_manager=None,
        validator=None,
        project_manager=None,
        pricing_manager=None,
        validation_service=None,
    ):
        # Data roots
        self.data_dir = Path("data")
        self.config_dir = self.data_dir / "config"
        self.cache_dir = self.data_dir / "cache"
        self.time_dir = self.data_dir / "time"
        for d in (self.config_dir, self.cache_dir, self.time_dir):
            d.mkdir(parents=True, exist_ok=True)

        # Core file paths
        self.settings_path = self.config_dir / "settings.json"
        self.rules_path = self.config_dir / "rules.json"
        self.projects_path = self.config_dir / "projects.json"
        self.projects_dir = self.config_dir / "projects"
        self.presets_path = self.config_dir / "presets.json"
        self.kicad_standards_path = self.config_dir / "kicad_standards.json"
        self.app_settings_path = self.config_dir / "app_settings.json"
        self.time_tracker_file = self.time_dir / "time_tracker.json"
        self.time_data_file = self.time_dir / "time_data.json"
        self.task_library_path = self.time_dir / "task_library.json"
        self.library_cache_path = self.cache_dir / "library_cache.json"
        self.footprint_cache_path = self.cache_dir / "footprint_cache.json"
        self.parts_db_path = self.config_dir / "parts_db.json"
        self.data_store = {} # Stores parsed symbol data (library_name -> part_name -> data)
        self.settings = {
            "symbol_path": "", # Path to KiCad symbol libraries
            "footprint_path": "", # Path to KiCad footprint libraries
            "projects": [], # List of project names for ordering (for UI display)
            "path_root": "", # Base directory for path placeholders (e.g., ${BASE_DIR})
            "project_registry": {}, # Stores project-specific data (metadata, kanban, checklist, etc.)
            "project_types": ["PCB", "Firmware", "Mechanical", "Other"],
            "category_restrictions": {}, # Map category -> list of allowed project types
            "theme": "Light",
            "global_notes": "",
            "external_tools": {"editor": "", "kicad": ""},
            "backup": {
                "path": "backups",
                "backup_on_exit": False,
                "app_data": { "enabled": False, "interval_min": 15, "max_backups": 10, "last_run": "" },
                "symbols": { "enabled": False, "interval_min": 60, "max_backups": 3, "last_run": "" },
                "footprints": { "enabled": False, "interval_min": 60, "max_backups": 3, "last_run": "" }
            },
            "checklist_templates": {
                "Standard": {
                "Schematic: Electrical Rules Check (ERC)": [],
                "Schematic: Netlist Verification": [],
                "Schematic: Bill of Materials (BOM) Review": [],
                "Layout: Design Rules Check (DRC)": [],
                "Layout: Footprint Verification": [],
                "Layout: Component Placement Review": [],
                "Layout: Critical Routing / Impedance": [],
                "Layout: Silkscreen & Polarity Check": [],
                "Layout: 3D Model Fit Check": [],
                "Fabrication: Gerber Generation & Review": [],
                "Fabrication: Drill Files Generated": [],
                "Assembly: Pick & Place File Generated": []
                }
            },
            "kanban_templates": {
                "Standard": [
                    {"name": "Create Schematic"},
                    {"name": "Assign Footprints"},
                    {"name": "Run ERC"},
                    {"name": "Generate Netlist"},
                    {"name": "Outline PCB"},
                    {"name": "Place Components"},
                    {"name": "Route Tracks"},
                    {"name": "Run DRC"},
                    {"name": "Generate Gerbers"},
                    {"name": "Order Parts"},
                ]
            },
            "kanban_categories": {
                "Feature": "#3498db",
                "Bug": "#e74c3c",
                "Task": "#95a5a6",
                "Urgent": "#e67e22"
            }
        }
        self.global_rules = {} # Global property validation rules
        self.library_rules = {} # Per-library required properties
        self.exemptions = {"libraries": {}, "parts": {}, "fp_libraries": {}, "footprints": {}} # Rules exempted for specific libraries/parts/footprints
        self.footprint_lib_map = {} # Map lib_name -> path to .pretty folder
        self.path_resolver = PathResolver(lambda: self.settings.get("path_root", "")) # Shared resolver for relative tokens
        self.paths_config = PathsConfig(self.path_resolver, self.settings)
        self.parser = parser or KiCadParser()
        self.symbol_indexer = SymbolIndexer(self.parser, self.path_resolver, self.library_cache_path)
        self.footprint_indexer = FootprintIndexer(self.path_resolver, self.footprint_cache_path)
        self.cache_diagnostics = {
            "library": {"warnings": [], "metadata": {}},
            "footprint": {"warnings": [], "metadata": {}},
        }
        self.load_settings() # Load application settings from file
        self._load_project_registry_store()
        self._save_project_registry_store()  # ensure per-project files exist/migrate legacy

        # Migration: pl_variable -> path_root
        migrated = False
        if not self.settings.get("path_root"):
            legacy_root = self.settings.get("pl_variable", "")
            if legacy_root:
                self.settings["path_root"] = legacy_root
                migrated = True
        if "pl_variable" in self.settings:
            self.settings.pop("pl_variable", None)
            migrated = True
        if migrated:
            self.save_settings()
        
        # Migration: default_checklist -> checklist_templates["Standard"]
        if "default_checklist" in self.settings:
            if "checklist_templates" not in self.settings:
                self.settings["checklist_templates"] = {}
            # Only migrate if Standard doesn't exist or is empty to avoid overwriting if both exist
            if "Standard" not in self.settings["checklist_templates"]:
                self.settings["checklist_templates"]["Standard"] = self.settings["default_checklist"]
            del self.settings["default_checklist"]
            self.save_settings()
            
        # Migration: Backup Settings (Flat -> Nested)
        bk = self.settings.get("backup", {})
        if "app_data" not in bk:
            new_bk = {
                "path": bk.get("path", "backups"),
                "app_data": { 
                    "enabled": bk.get("enabled", False), 
                    "interval_min": bk.get("interval_min", 15), 
                    "max_backups": bk.get("max_backups", 10),
                    "last_run": ""
                },
                "symbols": { "enabled": False, "interval_min": 60, "max_backups": 3, "last_run": "" },
                "footprints": { "enabled": False, "interval_min": 60, "max_backups": 3, "last_run": "" }
            }
            self.settings["backup"] = new_bk
            self.save_settings()

        self.load_rules() # Load validation rules and exemptions
        self.bom_service = bom_service or BOMService(self)
        self.backup_manager = backup_manager or BackupManager(self) # Initialize backup manager
        self.validator = validator or Validator(self) # Initialize validation manager
        self.project_manager = project_manager or ProjectManager(self) # Initialize project manager
        self.pricing_manager = pricing_manager or PricingManager(self) # Initialize pricing manager
        self.validation_service = validation_service or ValidationService(self, self.validator)
        self.time_tracker_data = self._load_time_tracker()
        self.time_task_library = self._load_time_task_library()
        self.parts_db = self._load_parts_db()

    # --- Persistence ---
    def load_settings(self):
        """Loads application settings from data/config/settings.json."""
        if self.settings_path.exists():
            with open(self.settings_path, "r", encoding="utf-8") as f:
                try: self.settings.update(json.load(f))
                except: pass
        else:
            self.save_settings()
        # Ensure base directory is a concrete path (not a token)
        base_dir_changed = False
        if not self.settings.get("path_root") or self.settings.get("path_root") in ("${BASE_DIR}", "${PL_VAR}"):
            self.settings["path_root"] = self.normalize_path(os.getcwd())
            base_dir_changed = True
        # If the saved root no longer matches where the app lives, pick the best available root automatically.
        if self._autodetect_path_root():
            base_dir_changed = True
        # Resolve any ${BASE_DIR} placeholders for runtime use
        self._resolve_settings_paths()
        if base_dir_changed:
            self.save_settings()

    def _autodetect_path_root(self):
        """
        Pick a sensible path_root when the project folder moves.
        Chooses the candidate root that resolves the most known paths.
        Returns True if path_root was changed.
        """
        stored_root = self.normalize_path(self.settings.get("path_root", ""))
        cwd_root = self.normalize_path(os.getcwd())
        repo_root = self.normalize_path(Path(__file__).resolve().parent.parent)

        # Preserve order: saved value first, then cwd, then repo root
        candidates = []
        for label, root in (("stored", stored_root), ("cwd", cwd_root), ("repo", repo_root)):
            if root and root not in (c[1] for c in candidates):
                candidates.append((label, root))

        sample_paths = [
            self.settings.get("symbol_path", ""),
            self.settings.get("footprint_path", ""),
        ]
        backup_cfg = self.settings.get("backup", {}) or {}
        sample_paths.append(backup_cfg.get("path", ""))
        for proj in (self.settings.get("project_registry", {}) or {}).values():
            meta = proj.get("metadata", {}) or {}
            sample_paths.append(meta.get("location", ""))
            sample_paths.append(meta.get("main_schematic", ""))

        def score(root):
            resolver = PathResolver(lambda: root)
            hits = 0
            for p in sample_paths:
                if not p:
                    continue
                target = resolver.resolve(p)
                if target and os.path.exists(target):
                    hits += 1
            return hits

        best_root = stored_root
        best_score = score(stored_root) if stored_root else -1
        for _, root in candidates[1:]:
            s = score(root)
            if s > best_score:
                best_root = root
                best_score = s

        # If nothing resolves anywhere, fall back to cwd
        if best_score <= 0 and cwd_root:
            best_root = cwd_root

        if best_root and best_root != stored_root:
            self.settings["path_root"] = best_root
            return True
        return False

    def save_settings(self):
        """Saves current application settings to data/config/settings.json."""
        settings_dict = copy.deepcopy(self.settings)
        self._relativize_settings_paths(settings_dict)
        with open(self.settings_path, "w", encoding="utf-8") as f:
            json.dump(settings_dict, f, indent=4)
        self._save_project_registry_store()

    def load_rules(self):
        """Loads validation rules and exemptions from data/config/rules.json."""
        if self.rules_path.exists():
            with open(self.rules_path, "r", encoding="utf-8") as f:
                try:
                    d = json.load(f)
                    self.global_rules = d.get("global", {}) # Global regex rules
                    self.library_rules = d.get("library", {}) # Per-library required properties
                    self.exemptions = d.get("exemptions", {"libraries": {}, "parts": {}}) # Exemptions
                    # Ensure footprint exemption keys exist
                    self.exemptions.setdefault("fp_libraries", {})
                    self.exemptions.setdefault("footprints", {})
                except: pass
        else:
            # Ensure footprint exemption keys exist when no file present
            self.exemptions.setdefault("fp_libraries", {})
            self.exemptions.setdefault("footprints", {})

    def save_rules(self):
        """Saves current validation rules and exemptions to data/config/rules.json."""
        with open(self.rules_path, "w", encoding="utf-8") as f:
            json.dump({"global": self.global_rules, "library": self.library_rules, "exemptions": self.exemptions}, f, indent=4)

    # --- Time Tracker ---
    def _load_time_tracker(self):
        path = self.time_tracker_file
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {"entries": []}

    def _load_time_task_library(self):
        default_library = _build_default_time_task_library()
        path = self.task_library_path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    stored = json.load(f)
                categories = stored.get("categories")
                tasks = stored.get("tasks")
                if isinstance(categories, list) and isinstance(tasks, list):
                    return {
                        "categories": copy.deepcopy(categories),
                        "tasks": copy.deepcopy(tasks),
                    }
            except Exception:
                pass
        return default_library

    def get_time_task_library(self):
        return copy.deepcopy(self.time_task_library)

    def save_time_task_library(self, library):
        snapshot = {
            "categories": copy.deepcopy(library.get("categories", [])),
            "tasks": copy.deepcopy(library.get("tasks", [])),
        }
        self.time_task_library = snapshot
        try:
            with open(self.task_library_path, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
        except Exception as e:
            print(f"DEBUG: Failed to save time task library: {e}")

    def reset_time_task_library(self):
        self.save_time_task_library(_build_default_time_task_library())

    def _load_parts_db(self):
        path = self.parts_db_path
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        data.setdefault("parts", [])
                        if isinstance(data.get("parts"), list):
                            return data
            except Exception:
                pass
        return {"parts": []}

    def get_parts_db(self):
        return list(self.parts_db.get("parts", []))

    def save_parts_db(self, parts):
        self.parts_db["parts"] = list(parts)
        try:
            with open(self.parts_db_path, "w", encoding="utf-8") as f:
                json.dump(self.parts_db, f, indent=2)
        except Exception as e:
            print(f"DEBUG: Failed to save parts db: {e}")

    def get_part_usage_stats(self, lib_id):
        counts = self.project_manager.project_usage_counts.get(lib_id, {})
        if not counts:
            return []
        registry = self.settings.get("project_registry", {})
        stats = []
        for project in sorted(counts.keys(), key=lambda k: (-counts[k], k)):
            meta = registry.get(project, {}).get("metadata", {})
            last_touched = meta.get("last_accessed") or meta.get("updated") or ""
            stats.append({
                "project": meta.get("name", project),
                "count": counts[project],
                "last_touched": last_touched,
                "path": meta.get("location", ""),
            })
        return stats

    def get_time_entries(self):
        return list(self.time_tracker_data.get("entries", []))

    def save_time_entries(self, entries):
        self.time_tracker_data["entries"] = list(entries)
        try:
            with open(self.time_tracker_file, "w", encoding="utf-8") as f:
                json.dump(self.time_tracker_data, f, indent=2)
        except Exception as e:
            print(f"DEBUG: Failed to save time tracker data: {e}")

        # --- Parsing & Indexing ---
    def scan_libraries(self, root_path):
        """
        Scans the specified root_path for KiCad symbol library files (.kicad_sym)
        and populates the internal data_store with parsed symbol data.
        """
        roots = self.resolve_path_list(root_path)
        if not roots:
            roots = self.paths_config.symbol_roots()
        if not roots:
            return 0

        sym_path_str = self.resolve_path_list_string(roots)
        if sym_path_str != self.settings.get("symbol_path"):
            self.settings["symbol_path"] = sym_path_str
            self.save_settings()

        result = self.symbol_indexer.scan(roots, max_workers=self.LIBRARY_SCAN_WORKERS)
        self.data_store = result.data_store
        self.cache_diagnostics["library"] = result.diagnostics
        self.project_manager.index_projects()
        return len(self.data_store)

    def scan_footprint_libraries(self, force=False):
        """Recursively scans the footprint path(s) for .pretty folders and indexes them."""
        roots = self._get_footprint_roots()
        if not roots:
            self.footprint_lib_map = {}
            return 0

        new_map, diagnostics = self.footprint_indexer.scan(roots)
        self.footprint_lib_map = new_map or {}
        self.cache_diagnostics["footprint"] = diagnostics
        return len(self.footprint_lib_map)

    def get_footprint_data(self, fp_ref):
        """Retrieves parsed footprint data for a given footprint reference (e.g., 'Resistor_SMD:R_0805_2012Metric')."""
        if not fp_ref: return None
        
        # Ensure index is built if empty
        if not hasattr(self, 'footprint_lib_map') or not self.footprint_lib_map:
            self.scan_footprint_libraries()

        roots = self._get_footprint_roots()
        if not roots:
            return None
        
        if ":" in fp_ref:
            lib, name = fp_ref.rsplit(":", 1)
            lib = lib.strip(); name = name.strip()
        else:
            lib = None; name = fp_ref.strip()

        candidates = []
        
        # 1. Check indexed libraries (Fast & Accurate for subfolders)
        if lib and lib in self.footprint_lib_map:
            candidates.append(Path(self.footprint_lib_map[lib]) / f"{name}.kicad_mod")

        # 2. Standard paths (Fallback)
        for root in roots:
            if lib:
                candidates.append(Path(root) / f"{lib}.pretty" / f"{name}.kicad_mod")
                candidates.append(Path(root) / lib / f"{name}.kicad_mod")
            candidates.append(Path(root) / f"{name}.kicad_mod")

        target = None
        for c in candidates:
            if c.exists():
                target = c
                break
        
        # 3. Deep Search Fallback (Slow, but finds orphans)
        if not target and name:
            for root in roots:
                try:
                    found = list(Path(root).rglob(f"{name}.kicad_mod"))
                    if found:
                        target = found[0]
                        break
                except Exception:
                    pass

        if not target: return None

        geom = KiCadParser.parse_footprint_full(target)
        # Best-effort: resolve model reference to an on-disk file (many footprints store stale/portable paths).
        if isinstance(geom, dict) and geom.get("model_path"):
            geom["model_file"] = self._resolve_3d_model_file(geom.get("model_path"), geom.get("file_path") or str(target))
        return geom

    def _get_footprint_roots(self):
        """Return valid footprint roots with a safe fallback to BASE_DIR/footprints."""
        roots = self.resolve_path_list(self.settings.get("footprint_path", ""))
        valid = [p for p in roots if p and os.path.isdir(p)]
        if valid:
            # If valid roots exist but none contain .pretty libraries, fall back.
            has_pretty = False
            for root in valid:
                try:
                    if any(p.is_dir() for p in Path(root).rglob("*.pretty")):
                        has_pretty = True
                        break
                except Exception:
                    continue
            if has_pretty:
                return valid
        base = self.get_path_root()
        fallback = self.normalize_path(os.path.join(base, "footprints")) if base else ""
        if fallback and os.path.isdir(fallback):
            return [fallback]
        return valid

    def _model_candidate_filenames(self, model_ref):
        """Returns plausible 3D model filenames for a given KiCad model reference."""
        if not model_ref:
            return []
        raw = str(model_ref).strip().strip('"').strip("'").replace("\\", "/")
        name = raw.rsplit("/", 1)[-1].strip()
        if not name:
            return []

        stem, ext = os.path.splitext(name)
        if not stem:
            return [name]

        candidates = [name]
        ext_l = ext.lower()
        # Common STEP extensions in the wild.
        if ext_l in (".stp", ".step", ".wrl", ".wrz"):
            for alt in (".step", ".stp", ".wrl", ".wrz"):
                if alt != ext_l:
                    candidates.append(stem + alt)

        seen = set()
        unique = []
        for c in candidates:
            k = c.lower()
            if k in seen:
                continue
            seen.add(k)
            unique.append(c)
        return unique

    def _resolve_3d_model_file(self, model_ref, footprint_file_path):
        """
        Resolve a KiCad `(model "...")` reference to a real file on disk.

        Many of the local libraries use `${PL}` / `${PL_FOOTPRINT_DIR}` placeholders or contain absolute paths from
        the author's machine. If the resolved path doesn't exist, we fall back to searching near the footprint library.
        """
        if not model_ref:
            return ""

        raw = str(model_ref).strip().strip('"').strip("'")
        raw_norm = raw.replace("\\", "/")

        # 1) Try expanding known placeholders and environment variables.
        expanded = raw_norm
        root = self.get_path_root()
        if root:
            for token in ("${BASE_DIR}", "${PL_VAR}", "${PL}"):
                if token in expanded:
                    expanded = expanded.replace(token, root)

        # `${PL_FOOTPRINT_DIR}` is commonly used to mean the footprint library root.
        fp_root = ""
        fp_roots = self.resolve_path_list(self.settings.get("footprint_path", ""))
        fp_file_norm = self.normalize_path(footprint_file_path) if footprint_file_path else ""
        if fp_file_norm:
            best_len = 0
            for r in fp_roots:
                r_norm = self.normalize_path(r).rstrip("/")
                if r_norm and fp_file_norm.lower().startswith(r_norm.lower() + "/") and len(r_norm) > best_len:
                    fp_root = r_norm
                    best_len = len(r_norm)
        if not fp_root and fp_roots:
            fp_root = self.normalize_path(fp_roots[0]).rstrip("/")
        if fp_root and "${PL_FOOTPRINT_DIR}" in expanded:
            expanded = expanded.replace("${PL_FOOTPRINT_DIR}", fp_root)

        expanded = self.expand_path(expanded)
        candidate = expanded
        if candidate and not self.path_resolver.is_abs_path(candidate):
            candidate = self.resolve_path(candidate)
        candidate = self.normalize_path(os.path.normpath(candidate)) if candidate else ""

        if candidate and os.path.exists(candidate):
            return candidate

        # 2) Fallback: locate the model under the footprint library folder.
        if not footprint_file_path:
            return ""

        try:
            fp_path = Path(os.path.normpath(footprint_file_path))
        except Exception:
            return ""

        pretty_dir = fp_path.parent
        lib_dir = pretty_dir.parent

        names = self._model_candidate_filenames(raw_norm)
        if not names:
            return ""

        search_dirs = [
            pretty_dir,
            lib_dir,
            lib_dir / "3D Model",
            lib_dir / "3D Models",
            lib_dir / "3dmodels",
            lib_dir / "3d_models",
            lib_dir / "3D",
            lib_dir / "models",
            pretty_dir / "3D Model",
            pretty_dir / "3D Models",
        ]
        if pretty_dir.name.lower().endswith(".pretty"):
            search_dirs.append(pretty_dir.with_suffix(".3dshapes"))

        for d in search_dirs:
            try:
                if not d.exists():
                    continue
            except Exception:
                continue
            for name in names:
                p = d / name
                try:
                    if p.exists() and p.is_file():
                        return self.normalize_path(str(p))
                except Exception:
                    continue

        # Last resort: recursive search inside the library directory.
        try:
            if lib_dir.exists():
                for name in names:
                    found = next((p for p in lib_dir.rglob(name) if p.is_file()), None)
                    if found:
                        return self.normalize_path(str(found))
        except Exception:
            pass

        return ""

    # --- Validation Logic ---
    def validate_and_get_stats(self, scope="all", target_lib=None):
        """Delegates to Validator to perform property validation and get statistics."""
        return self.validator.validate_and_get_stats(scope, target_lib)

    def run_validation_summary(self, scope="all", target_lib=None):
        """Runs validation and returns structured summary (cached)."""
        return self.validation_service.run_validation(scope, target_lib)

    def get_cached_validation_summary(self):
        """Returns the last cached validation summary."""
        return self.validation_service.get_cached_summary()

    def get_exempted_failures(self, scope="all", target_lib=None):
        """Delegates to Validator to get a list of exempted failures."""
        return self.validator.get_exempted_failures(scope, target_lib)

    def find_duplicates(self):
        """Aliases check_duplicate_mpns for the UI."""
        return self.validator.check_duplicate_mpns()

    def check_duplicate_mpns(self):
        """Delegates to Validator to find duplicate MPNs."""
        return self.validator.check_duplicate_mpns()

    def check_footprint_integrity(self):
        """Delegates to Validator to check footprint pin integrity."""
        return self.validator.check_footprint_integrity()

    def get_footprint_rules(self):
        """Returns available footprint validation rule names."""
        return self.validator.get_footprint_rules()

    def validate_symbols(self, scope="all", target_lib=None):
        """Delegates to Validator to perform symbol structural checks."""
        return self.validator.validate_symbols(scope, target_lib)

    def validate_footprints(self, scope="all", target_lib=None):
        """Delegates to Validator to perform footprint structural checks."""
        return self.validator.validate_footprints(scope, target_lib)

    def bulk_edit_property(self, lib, name, key, new_val):
        """Delegates to Validator to bulk edit a symbol property."""
        return self.validator.bulk_edit_property(lib, name, key, new_val)

    def add_part_exemption(self, lib, name, rule):
        """Adds an exemption for a specific part from a given rule."""
        uid = f"{lib}:{name}"
        if uid not in self.exemptions['parts']: self.exemptions['parts'][uid] = []
        if rule not in self.exemptions['parts'][uid]: 
            self.exemptions['parts'][uid].append(rule)
            self.save_rules()

    def add_lib_exemption(self, lib, rule):
        """Adds an exemption for an entire library from a given rule."""
        if lib not in self.exemptions['libraries']: self.exemptions['libraries'][lib] = []
        if rule not in self.exemptions['libraries'][lib]:
            self.exemptions['libraries'][lib].append(rule)
            self.save_rules()

    def get_subsheets(self, root_path):
        """
        Recursively finds all sub-schematic files starting from a root schematic path.
        Uses a robust regex to find sheet references within KiCad schematic files.
        """
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
                
                # Robust Regex for KiCad 6/7/8 Sheetfiles
                # Matches: (property "Sheetfile" "sub.kicad_sch")
                # Matches: (property "Sheet file" "sub.kicad_sch")
                # Captures the filename inside the quotes
                sheets = re.findall(r'\(property\s+"Sheet(?:file| file)"\s+"([^"]+)"', content)
                
                # Fallback for older formats or alternative definitions (e.g., (file "sub.kicad_sch"))
                sheets += re.findall(r'\(file\s+"([^"]+)")', content)

                for s in sheets:
                    # Resolve relative path to the current schematic file
                    sub_path = (Path(current).parent / s).resolve()
                    if sub_path.exists():
                        to_scan.append(str(sub_path))
            except: pass
            
        return sorted(list(found_sheets))

    def get_subsheets_hierarchy(self, root_path):
        """
        Recursively builds a hierarchical (tree) structure of schematic files
        starting from a root schematic.
        Each node in the tree includes the sheet name, full path, part count, and children.
        """
        if not root_path or not os.path.exists(root_path): return None
        
        def build_tree(path, visited):
            abs_path = str(Path(path).resolve())
            # Prevent infinite recursion for cyclic sheet references
            if abs_path in visited: 
                return {"name": Path(path).name + " (Recursive)", "path": abs_path, "children": [], "part_count": 0}
            
            visited.add(abs_path)
            
            # Count parts directly within this specific schematic sheet
            part_count = 0
            try:
                comps, _ = KiCadParser.parse_schematic(path)
                part_count = len(comps)
            except: pass
            
            node = {"name": Path(path).name, "path": abs_path, "children": [], "part_count": part_count}
            
            try:
                with open(path, 'r', encoding='utf-8', errors='replace') as f:
                    content = f.read()
                
                # Use the same robust regex to find sub-sheets
                sheets = re.findall(r'\(property\s+"Sheet(?:file| file)"\s+"([^"]+)"', content)
                sheets += re.findall(r'\(file\s+"([^"]+)")', content)
                
                for s in sheets:
                    sub_path = (Path(path).parent / s).resolve()
                    if sub_path.exists():
                        child = build_tree(str(sub_path), visited.copy()) # Recursive call
                        if child: node["children"].append(child)
            except: pass
            
            # Sort children alphabetically
            node["children"].sort(key=lambda x: x["name"].lower())
            
            return node

        return build_tree(root_path, set())

    def generate_bom(self, root_sch_path):
        """Delegates BOM generation to BOMService for consistent caching."""
        return self.bom_service.generate_bom(root_sch_path)

    def get_project_data(self, identifier):
        """Delegates to ProjectManager to get or initialize project data."""
        return self.project_manager.get_project_data(identifier)

    def fetch_supplier_pricing(self, bom_data):
        """Delegates to PricingManager to fetch supplier pricing."""
        return self.pricing_manager.fetch_supplier_pricing(bom_data)
    
    def get_backup_size(self):
        """Delegates to BackupManager to get total backup size."""
        return self.backup_manager.get_backup_size()

    def perform_backup(self, force=False):
        """Delegates to BackupManager to perform scheduled backups."""
        return self.backup_manager.perform_backup(force)

    def restore_backup(self, timestamp):
        """Delegates to BackupManager to restore a backup."""
        return self.backup_manager.restore_backup(timestamp)

    def launch_tool(self, tool_key, file_path):
        """Launches an external tool configured in settings."""
        import subprocess
        exe = self.settings.get("external_tools", {}).get(tool_key, "")
        if exe and os.path.exists(exe) and file_path:
            try:
                subprocess.Popen([exe, file_path])
                return True
            except Exception as e:
                print(f"Error launching {tool_key}: {e}")
        return False

    def clone_project(self, source_name, new_name):
        """Delegates to ProjectManager to clone a project."""
        return self.project_manager.clone_project(source_name, new_name)

    def archive_project(self, name):
        """Delegates to ProjectManager to archive a project."""
        return self.project_manager.archive_project(name)

    def create_gitignore(self, path):
        """Delegates to ProjectManager to create a .gitignore file."""
        return self.project_manager.create_gitignore(path)

    def toggle_pin(self, name):
        """Delegates to ProjectManager to toggle a project's pinned status."""
        return self.project_manager.toggle_pin(name)

    def clean_project(self, name):
        """Delegates to ProjectManager to clean temporary project files."""
        return self.project_manager.clean_project(name)

    def split_path_list(self, raw):
        return self.path_resolver.split_list(raw)

    def resolve_path_list(self, raw):
        return self.path_resolver.resolve_path_list(raw)

    def resolve_path_list_string(self, raw):
        return self.path_resolver.resolve_path_list_string(raw)

    def relativize_path_list_string(self, raw):
        return self.path_resolver.relativize_path_list_string(raw)

    def get_settings_files(self):
        """Returns a list of config filenames that should be backed up with app data."""
        return [
            str(self.settings_path),
            str(self.rules_path),
            str(self.projects_path),
            str(self.projects_dir),
            str(self.presets_path),
            str(self.kicad_standards_path),
            str(self.app_settings_path),
            str(self.time_tracker_file),
            str(self.parts_db_path),
            str(self.library_cache_path),
            str(self.footprint_cache_path),
        ]

    def get_git_repositories(self):
        """
        Returns a list of dicts describing all known repositories (projects, symbol roots, footprint roots, manual entries).
        Each dict contains: name, path, type, source, and optional metadata for project linkage.
        """
        repos = []
        seen = set()

        def _format_project_name(meta, key):
            base = meta.get("name") or key
            parts = []
            if meta.get("number"):
                parts.append(meta["number"])
            if meta.get("type"):
                parts.append(meta["type"])
            parts.append(base)
            return " · ".join(part for part in parts if part)

        def add_repo(entry, allow_missing=False):
            raw_path = entry.get("path", "")
            resolved = self.resolve_path(raw_path)
            missing_path = False
            if not resolved or not os.path.isdir(resolved):
                if not allow_missing:
                    return
                resolved = ""
                norm = None
                missing_path = True
            else:
                norm = self._normalize_path_key(resolved)
                if not norm or norm in seen:
                    return
                seen.add(norm)
            entry_copy = dict(entry)
            entry_copy["path"] = resolved
            entry_copy["normalized_path"] = norm
            entry_copy.setdefault("type", "manual")
            entry_copy.setdefault("source", "manual")
            entry_copy.setdefault("name", os.path.basename(resolved) or "Repository")
            entry_copy["missing_path"] = missing_path
            repos.append(entry_copy)

        registry = self.settings.get("project_registry", {})
        for key, data in registry.items():
            meta = data.get("metadata", {})
            location = meta.get("location", "")
            git_dir = meta.get("git_directory") or ""
            same_as_loc = meta.get("git_same_as_location", True)
            repo_path = git_dir if git_dir and not same_as_loc else location
            add_repo({
                "name": _format_project_name(meta, key),
                "path": repo_path,
                "type": "project",
                "source": "project",
                "project_key": key,
                "project_location": self.resolve_path(location),
                "project_number": meta.get("number"),
                "project_type": meta.get("type"),
            }, allow_missing=True)

        symbol_roots = self.resolve_path_list(self.settings.get("symbol_path", ""))
        for root in symbol_roots:
            if not root:
                continue
            add_repo({
                "name": "Symbol",
                "path": root,
                "type": "symbol",
                "source": "symbol",
            })

        footprint_roots = self.resolve_path_list(self.settings.get("footprint_path", ""))
        for root in footprint_roots:
            if not root:
                continue
            add_repo({
                "name": "Footprint",
                "path": root,
                "type": "footprint",
                "source": "footprint",
            })

        manual_repos = self.settings.get("git_repos", [])
        for repo in manual_repos:
            name = repo.get("name") or repo.get("path")
            add_repo({
                "name": f"{name}",
                "path": repo.get("path", ""),
                "type": repo.get("type", "manual"),
                "source": "manual",
            })

        # Attach quick git status info to each repo
        for repo in repos:
            status = self._probe_git_repo(repo.get("path", ""), missing=repo.get("missing_path", False))
            repo.update(status)

        # Sort for stable UI ordering: type then name
        repos.sort(key=lambda r: (r.get("type", ""), r.get("name", "")))
        return repos

    def _probe_git_repo(self, path, missing=False):
        """
        Lightweight git probe: returns branch, ahead, behind, clean flags.
        If path is not a git repo, returns placeholders.
        """
        if missing or not path or not os.path.isdir(path):
            return {
                "branch": "-",
                "ahead": 0,
                "behind": 0,
                "clean": True,
                "missing_path": missing,
            }
        try:
            import subprocess
            kwargs = {"cwd": path, "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT, "text": True}
            # Verify repo
            check = subprocess.run(["git", "rev-parse", "--is-inside-work-tree"], **kwargs)
            if check.returncode != 0:
                return {"branch": "-", "ahead": 0, "behind": 0, "clean": True}

            res = subprocess.run(
                ["git", "status", "--porcelain=2", "--branch"],
                **kwargs,
            )
            output = res.stdout or ""
            branch = "-"
            ahead = behind = 0
            changes = []
            for line in output.splitlines():
                if line.startswith("# branch.head"):
                    parts = line.split()
                    if len(parts) >= 3:
                        branch = parts[2]
                elif line.startswith("# branch.ab"):
                    for part in line.split():
                        if part.startswith("+"):
                            try:
                                ahead = int(part.lstrip("+"))
                            except ValueError:
                                ahead = 0
                        elif part.startswith("-"):
                            try:
                                behind = int(part.lstrip("-"))
                            except ValueError:
                                behind = 0
                elif not line.startswith("#") and line.strip():
                    changes.append(line)

            clean = len(changes) == 0 and res.returncode == 0
            return {
                "branch": branch or "-",
                "ahead": ahead,
                "behind": behind,
                "clean": clean,
            }
        except Exception:
            return {
                "branch": "-",
                "ahead": 0,
                "behind": 0,
                "clean": True,
            }

    def get_library_git_note_for_path(self, path):
        """Returns any saved library note for the resolved path."""
        resolved = self.resolve_path(path)
        norm_key = self._normalize_path_key(resolved)
        if not norm_key:
            return None
        notes = self.settings.get("library_git_notes", {})
        note = notes.get(norm_key)
        return copy.deepcopy(note) if note else None

    def set_library_git_note_for_path(self, path, note):
        """Stores or updates a note for the given library repository path."""
        resolved = self.resolve_path(path)
        norm_key = self._normalize_path_key(resolved)
        if not resolved or not norm_key:
            return False
        notes = self.settings.setdefault("library_git_notes", {})
        notes[norm_key] = {
            "path": resolved,
            "note": note or "",
            "updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self.save_settings()
        return True

    # --- Library Git roots (primary symbol/footprint repos) ---
    def get_library_git_roots(self):
        """
        Returns a dict with 'symbol' and 'footprint' git roots (resolved paths or '').
        Falls back to the first configured symbol/footprint path if no explicit git root is set.
        """
        roots = self.settings.get("git_library_roots", {})
        symbol = roots.get("symbol") or (self.resolve_path_list(self.settings.get("symbol_path", "")) or [""])[0]
        footprint = roots.get("footprint") or (self.resolve_path_list(self.settings.get("footprint_path", "")) or [""])[0]
        return {
            "symbol": self.resolve_path(symbol) if symbol else "",
            "footprint": self.resolve_path(footprint) if footprint else "",
        }

    def set_library_git_root(self, kind, path):
        """
        Saves a library git root for the given kind ('symbol' or 'footprint').
        """
        if kind not in ("symbol", "footprint"):
            return False
        resolved = self.resolve_path(path)
        if not resolved:
            return False
        cfg = self.settings.setdefault("git_library_roots", {})
        cfg[kind] = self.relativize_path(resolved)
        self.save_settings()
        return True

    def _normalize_path_key(self, path):
        if not path:
            return ""
        try:
            normalized = os.path.normcase(os.path.normpath(path))
            return normalized
        except Exception:
            return ""

    def add_manual_git_repo(self, name, path):
        if not path:
            return False
        resolved = self.resolve_path(path)
        if not resolved or not os.path.isdir(resolved):
            return False
        repo_list = self.settings.setdefault("git_repos", [])
        norm_target = self._normalize_path_key(resolved)
        for entry in repo_list:
            existing = self.resolve_path(entry.get("path", "")) or ""
            if self._normalize_path_key(existing) == norm_target:
                entry["name"] = name or entry.get("name", entry.get("path", "Manual Repo"))
                entry["path"] = self.relativize_path(resolved)
                self.save_settings()
                return True
        repo_list.append(
            {
                "name": name or os.path.basename(resolved) or "Manual Repo",
                "path": self.relativize_path(resolved),
                "type": "manual",
            }
        )
        self.save_settings()
        return True

    def remove_manual_git_repo(self, path):
        if not path:
            return False
        resolved = self.resolve_path(path)
        if not resolved:
            return False
        norm_target = self._normalize_path_key(resolved)
        repo_list = self.settings.get("git_repos", [])
        removed = False
        for entry in list(repo_list):
            existing = self.resolve_path(entry.get("path", "")) or ""
            if self._normalize_path_key(existing) == norm_target:
                repo_list.remove(entry)
                removed = True
        if removed:
            self.save_settings()
        return removed

    # --- Project registry split I/O ---
    def _project_file_for_key(self, key):
        """Return a safe filename for a project key."""
        digest = hashlib.md5(key.encode("utf-8")).hexdigest()
        return self.projects_dir / f"proj_{digest}.json"

    def _load_project_registry_store(self):
        """
        Loads project_registry from per-project files if present.
        Falls back to legacy projects.json and migrates it on first run.
        """
        registry = {}
        if self.projects_dir.exists():
            for fp in self.projects_dir.glob("proj_*.json"):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                    key = payload.get("project_key") or payload.get("key")
                    data = payload.get("project") or payload.get("data") or {}
                    if not key:
                        meta = data.get("metadata", {})
                        key = meta.get("name")
                    if key and isinstance(data, dict):
                        registry[key] = data
                except Exception:
                    continue
        # Legacy fallback: migrate projects.json if no per-project files exist
        if not registry and self.projects_path.exists():
            try:
                with open(self.projects_path, "r", encoding="utf-8") as f:
                    legacy = json.load(f)
                reg = legacy.get("project_registry", {})
                if isinstance(reg, dict) and reg:
                    registry = reg
                    self._save_project_registry_store(registry)
            except Exception:
                pass
        if registry:
            self.settings["project_registry"] = registry

    def _save_project_registry_store(self, registry=None):
        """Persists project_registry into per-project files and keeps a small index."""
        if registry is None:
            registry = self.settings.get("project_registry", {})
        self.projects_dir.mkdir(parents=True, exist_ok=True)
        index = []
        for key, data in registry.items():
            fp = self._project_file_for_key(key)
            payload = {"project_key": key, "project": data}
            try:
                with open(fp, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
                index.append({"project_key": key, "file": fp.name})
            except Exception:
                continue
        # Write compact index/legacy aggregator
        try:
            with open(self.projects_path, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        "project_registry_index": index,
                        "project_count": len(registry),
                    },
                    f,
                    indent=2,
                )
        except Exception:
            pass

    # --- Path Helpers ---
    def normalize_path(self, path):
        return self.path_resolver.normalize(path)

    def expand_path(self, path):
        return self.path_resolver.expand(path)

    def get_path_root(self):
        return self.path_resolver.get_path_root()

    def resolve_path(self, path):
        return self.path_resolver.resolve(path)

    def relativize_path(self, path):
        return self.path_resolver.relativize(path)

    def _resolve_settings_paths(self):
        self.settings["symbol_path"] = self.resolve_path(self.settings.get("symbol_path", ""))
        self.settings["footprint_path"] = self.resolve_path(self.settings.get("footprint_path", ""))
        
        if "backup" in self.settings:
            self.settings["backup"]["path"] = self.resolve_path(self.settings["backup"].get("path", ""))
            
        if "external_tools" in self.settings:
            for k, v in self.settings["external_tools"].items():
                self.settings["external_tools"][k] = self.resolve_path(v)

        if "project_paths" in self.settings:
            self.settings["project_paths"] = [self.resolve_path(p) for p in self.settings.get("project_paths", [])]

        if "project_metadata" in self.settings:
            meta = self.settings.get("project_metadata", {})
            meta["location"] = self.resolve_path(meta.get("location", ""))
            meta["main_schematic"] = self.resolve_path(meta.get("main_schematic", ""))
            self.settings["project_metadata"] = meta

        registry = self.settings.get("project_registry", {})
        for k, v in registry.items():
            if "metadata" in v:
                v["metadata"]["location"] = self.resolve_path(v["metadata"].get("location", ""))
                v["metadata"]["main_schematic"] = self.resolve_path(v["metadata"].get("main_schematic", ""))
            if "structure" in v and "tree" in v["structure"]:
                self._resolve_tree_paths(v["structure"]["tree"])
        self.settings["project_registry"] = registry

    def _resolve_tree_paths(self, node):
        if not node: return
        if "path" in node:
            node["path"] = self.resolve_path(node["path"])
        for child in node.get("children", []):
            self._resolve_tree_paths(child)

    def _relativize_settings_paths(self, settings_dict):
        settings_dict["symbol_path"] = self.relativize_path(settings_dict.get("symbol_path", ""))
        settings_dict["footprint_path"] = self.relativize_path(settings_dict.get("footprint_path", ""))
        
        if "backup" in settings_dict:
            settings_dict["backup"]["path"] = self.relativize_path(settings_dict["backup"].get("path", ""))
            
        if "external_tools" in settings_dict:
            for k, v in settings_dict["external_tools"].items():
                settings_dict["external_tools"][k] = self.relativize_path(v)

        if "project_paths" in settings_dict:
            settings_dict["project_paths"] = [self.relativize_path(p) for p in settings_dict.get("project_paths", [])]

        if "project_metadata" in settings_dict:
            meta = settings_dict.get("project_metadata", {})
            meta["location"] = self.relativize_path(meta.get("location", ""))
            meta["main_schematic"] = self.relativize_path(meta.get("main_schematic", ""))
            settings_dict["project_metadata"] = meta

        registry = settings_dict.get("project_registry", {})
        for k, v in registry.items():
            if "metadata" in v:
                v["metadata"]["location"] = self.relativize_path(v["metadata"].get("location", ""))
                v["metadata"]["main_schematic"] = self.relativize_path(v["metadata"].get("main_schematic", ""))
            if "structure" in v and "tree" in v["structure"]:
                self._relativize_tree_paths(v["structure"]["tree"])
        settings_dict["project_registry"] = registry

    def _relativize_tree_paths(self, node):
        if not node: return
        if "path" in node:
            node["path"] = self.relativize_path(node["path"])
        for child in node.get("children", []):
            self._relativize_tree_paths(child)
