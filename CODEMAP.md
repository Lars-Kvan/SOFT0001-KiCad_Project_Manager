# Repository Codemap (Parts_Checker)

- main.py — application entry; constructs QApplication, loads AppLogic, applies theme, opens MainWindow.
- backend/
  - logic.py — core settings load/save, path helpers, manager wiring, and the high-level APIs that each UI view uses.
  - project_manager.py — project registry CRUD, file path resolution, BOM generation.
  - indexers.py — SymbolIndexer/FootprintIndexer now own the library and footprint cache lifecycle.
  - other managers: backup_manager.py, pricing_manager.py, validator.py, etc.
- ui/
  - main_window.py — builds top-level tabs and wiring to logic.
  - views/ — individual tab UIs (Pricing & Standards now render placeholder notices directly here; the legacy `ui/tabs` wrappers were removed during the restructure).
    - time_tracker_tab.py — weekly timesheet (current bubble view, week nav, quick add, CSV export).
    - project_*_view.py, ui_project.py — project manager screens.
  - resources/ — styles and icons.
- backups/ — dated settings/rules backups.
- documents/, graphical_elements/, licenses/, notes/ — assorted assets and reference files.
- settings.json — live app settings and project registry; time_tracker.json — time entries.

## Key Data Flows
- Settings: loaded/saved via backend/logic.py (settings.json).
- Projects: registry stored under settings["project_registry"]; list under settings["projects"].
- Time tracker: persistence in time_tracker.json via logic.get_time_entries/save_time_entries.

## Run
python main.py (PySide6). Themes and UI scale configured in settings.

## Notable UI files
- ui/views/time_tracker_tab.py — weekly bubble board.
- ui/views/ui_settings.py + ui/views/settings_pages.py — settings navigation and pages.
- ui/kanban_widgets.py — kanban task cards.
- ui/views/ui_explorer.py — symbol/footprint browser; model preview now lazy-loads QtWebEngine when a footprint 3D model is requested.
- ui/widgets/paint_utils.py — `painting(QWidget)` context for safe QPainter begin/end; keep paintEvent drawing inside it.

## Testing / checks
- python -m py_compile <file> for quick syntax check.

## Fresh startup behaviors
- Schematics are cached after the first `ProjectManager.index_projects` pass (`data/cache/schematic_cache.json`), so subsequent launches skip re-parsing unchanged `.kicad_sch` files.
- `info/project_manager.py` registers the cache loader/saver and maintains usage/footprint indexes from cached component summaries.

## Housekeeping
- Avoid editing backups/ and logs/ directly; regenerate via app if needed.
- If adding new managers/views, register in main_window.py tab creation.
