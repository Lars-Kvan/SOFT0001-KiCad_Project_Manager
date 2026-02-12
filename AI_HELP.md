# AI Helper Notes

- Start with `rg` when searching; use `python -m py_compile <file>` for quick syntax sanity checks.
- `main.py` is still the entry point, `backend/logic.py` wires the managers directly (the old manager factory helpers are gone), and `ui/core/main_window.py` builds tabs.
- Central data lives in `data/config/settings.json`, `data/cache/schematic_cache.json`, and `data/cache/library_cache.json`.

## Entry points & flows

- `AppLogic` is the glue: settings, backups, validators, pricing, BOM and project managers all register there.
- `backend/indexers.py` now owns the symbol/footprint cache lifecycle (SymbolIndexer + FootprintIndexer), and `AppLogic` routes `scan_libraries`/`scan_footprint_libraries` through it.
- `backend/project_manager.py` handles registry and caches schematic metadata; it now just proxies BOM generation to `logic.bom_service`.
- UI views (e.g., `ui/views/ui_dashboard.py`, `ui/views/project_details_view.py`) call `logic.generate_bom`, which delegates to `backend/bom_manager.py`.

## BOM & caches

- `backend/bom_manager.py` hosts the new `BOMService`. Use `logic.bom_service.generate_bom(...)` when additional BOMs are needed.
- The library/footprint caches are still stored in `data/cache/library_cache.json` and `data/cache/footprint_cache.json`, but `scan_libraries` delegates to `backend.indexers.SymbolIndexer`/`FootprintIndexer` to manage them (the old `cache_manager` helper was removed).

## Fast-AI workflow notes (relaxed)

- You can skip the older advice about wrapping every `paintEvent` in `with ui.widgets.paint_utils.painting(self)` unless you're modifying a paint-heavy widget; general PySide6 painting practices are sufficient.
- Focus on clear, small diffs that keep ASCII and existing naming conventions (`snake_case`, spaces over tabs). Avoid duplicating helper logic; reuse `ui/widgets` components when possible.
- Console-heavy helpers should call shared utilities (e.g., `ui/_subprocess_utils.py`) only when you need to hide windows; otherwise, keep direct subprocess usage minimal.
- Prioritize quick wins: reorganize shared logic (managers/services) before rewiring UI, and document new shortcuts or helpers you introduce.

## Helpful references

- Notifications/toasts live under `ui/widgets/toast.py` (optional utilities in `ui/widgets` and `ui/resources`).
- Project settings, backup controls, and validation rules are saved in `data/config/settings.json`, `rules.json`, and `app_data`/`backups` folders.
- Keep new helpers centralized; add shared utilities to `ui/widgets/` or `ui/resources/` rather than duplicating per view.
