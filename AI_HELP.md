# AI Helper Notes

- Use `rg` first for code search and `rg --files` for inventory.
- Quick syntax check: `python -m compileall -q backend ui main.py logger.py`.
- `main.py` is the entry point.
- `backend/logic.py` is the integration hub for managers/services.
- `ui/core/main_window.py` owns top-level tab composition.

## Current Architecture

- Core orchestration: `backend/logic.py`
- Project operations/indexing: `backend/project_manager.py`
- Library/footprint indexing and cache writes: `backend/indexers.py`
- BOM service: `backend/bom_manager.py`
- Validation stack: `backend/validator.py`, `backend/validation_service.py`, `backend/validation_models.py`
- Backups: `backend/backup_manager.py`
- Path plumbing: `backend/path_utils.py`, `backend/paths_config.py`
- UI tabs/views: `ui/views/*.py`
- Shared UI components: `ui/widgets/*.py`
- Shared theme/icon resources: `ui/resources/styles.py`, `ui/resources/icons.py`

## Active Data Locations

- Settings and rules: `data/config/settings.json`, `data/config/rules.json`
- Project index/registry: `data/config/projects.json` and `data/config/projects/proj_*.json`
- Optional app presets/config: `data/config/app_settings.json`, `data/config/presets.json`, `data/config/kicad_standards.json`
- Caches: `data/cache/library_cache.json`, `data/cache/footprint_cache.json`, `data/cache/schematic_cache.json`
- Time tracking: `data/time/time_tracker.json`, `data/time/time_data.json`, `data/time/task_library.json`

## Practical Edit Guidance

- Prefer editing `ui/views/*` and `ui/widgets/*`; legacy duplicate wrappers under `ui/*.py` were removed.
- Keep shared UI helpers centralized in `ui/widgets/` and `ui/resources/` instead of duplicating code in a single view.
- For subprocess calls that should hide Windows consoles, use `ui/_subprocess_utils.py`.
- When changing project-level behavior, patch `backend/logic.py` plus the owning manager/service, not only UI handlers.

## Runtime Artifacts

- Backup/export artifacts (`backups/`, `app_data/`, `symbols_*.zip`, `footprints_*.zip`) are generated at runtime and can be cleaned when stale.
- Root-level config/cache duplicates (`settings.json`, `rules.json`, `library_cache.json`, etc.) are legacy and should not be reintroduced.
