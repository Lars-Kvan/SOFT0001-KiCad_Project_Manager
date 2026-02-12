# Repository Codemap (SOFT0001-KiCad_Project_Manager)

- `main.py` - application entry; creates `QApplication`, initializes `AppLogic`, and opens `MainWindow`.
- `logger.py` - crash/exception logging helper used by startup.
- `backend/` - domain and persistence layer.
  - `logic.py` - central orchestration for settings, paths, scans, validation, BOM, backups, and project APIs used by UI.
  - `project_manager.py` - project indexing, project metadata operations, schematic cache lifecycle.
  - `indexers.py` - symbol/footprint indexing and cache writes (`library_cache.json`, `footprint_cache.json`).
  - `bom_manager.py` - BOM generation service.
  - `backup_manager.py` - backup scheduling, zip creation, retention, and restore.
  - `validator.py`, `validation_service.py`, `validation_models.py` - validation pipeline and summaries.
  - `path_utils.py`, `paths_config.py` - centralized path resolution and configured roots.
- `ui/` - presentation layer.
  - `core/main_window.py` - top-level shell and tab wiring.
  - `views/` - main feature tabs and project sub-views (`ui_project.py`, `ui_git.py`, `ui_dashboard.py`, `ui_explorer.py`, and related project views).
  - `widgets/` - reusable components (`kanban_widgets.py`, `checklist_widget.py`, `stats_card.py`, `toast.py`, `paint_utils.py`, etc.).
  - `dialogs/` - action palette, bug report, and feature request dialogs.
  - `resources/` - icon renderer, theme styles, and embedded web viewer assets.
  - `_subprocess_utils.py` - shared subprocess flags for hidden-console execution on Windows.
- `data/` - runtime data store.
  - `data/config/` - `settings.json`, `rules.json`, `projects.json`, `app_settings.json`, `presets.json`, and per-project files under `data/config/projects/`.
  - `data/cache/` - `library_cache.json`, `footprint_cache.json`, `schematic_cache.json`.
  - `data/time/` - `time_tracker.json`, `time_data.json`, `task_library.json`.
- `graphical_elements/Icons/` - SVG icon source files.
- `symbols/`, `footprints/`, `documents/`, `notes/`, `licenses/` - project/library content and references.

## Key Data Flows

- Settings and rules round-trip through `backend/logic.py` to `data/config/*.json`.
- Project registry is persisted in hashed per-project files under `data/config/projects/`, with index metadata in `data/config/projects.json`.
- Library scans run through `backend/indexers.py` and update `data/cache/library_cache.json` and `data/cache/footprint_cache.json`.
- Schematic metadata cache is maintained by `backend/project_manager.py` in `data/cache/schematic_cache.json`.
- Time tracking persists in `data/time/time_tracker.json` and related time files.

## Run / Verify

- Run app: `python main.py`
- Fast syntax check: `python -m compileall -q backend ui main.py logger.py`

## Housekeeping

- Legacy root config/cache duplicates (`settings.json`, `rules.json`, etc. at repo root) are deprecated; active files live under `data/config/` and `data/cache/`.
- Backup/export artifacts (`backups/`, `app_data/`, `symbols_*.zip`, `footprints_*.zip`) are runtime-generated and can be cleaned when not needed.
- When adding a new top-level UI area, wire it in `ui/core/main_window.py`.
