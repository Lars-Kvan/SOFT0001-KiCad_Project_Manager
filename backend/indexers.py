import hashlib
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

from backend.cache_models import CacheDiagnostics, CacheMetadata, IndexResult
from backend.path_utils import PathResolver


class SymbolIndexer:
    FORMAT_VERSION = 3

    def __init__(self, parser, resolver: PathResolver, cache_path: Path):
        self.parser = parser
        self.resolver = resolver
        self.cache_path = Path(cache_path)

    def scan(self, roots: List[str], max_workers: int = 1) -> IndexResult:
        diagnostics = CacheDiagnostics(metadata=CacheMetadata(format_version=self.FORMAT_VERSION))
        if not roots:
            return IndexResult(data_store={}, diagnostics=diagnostics)
        result = IndexResult()
        symbol_paths = list(self._expand_paths(roots))
        symbol_path_strings = [str(p) for p in symbol_paths]
        root_key = ";".join(symbol_path_strings)
        lib_cache, meta, warnings = self._load_cache(root_key, "files", self.FORMAT_VERSION, "symbol_path")
        diagnostics.metadata = meta
        diagnostics.warnings.extend(warnings)
        cache_updated = False
        current_files = {str(p) for p in symbol_paths}
        removed = set(lib_cache.keys()) - current_files
        if removed:
            for key in removed:
                lib_cache.pop(key, None)
            cache_updated = True

        parse_targets = []
        for sym_file in symbol_paths:
            key = str(sym_file)
            entry = lib_cache.get(key)
            mtime = self._file_mtime(sym_file)
            if entry and entry.get("mtime") == mtime and entry.get("symbols"):
                continue
            parse_targets.append((sym_file, key, mtime))

        if parse_targets:
            worker_count = max(1, min(max_workers, len(parse_targets)))
            if worker_count > 1 and len(parse_targets) > 1:
                with ThreadPoolExecutor(max_workers=worker_count) as executor:
                    future_map = {
                        executor.submit(self.parser.parse_lib_full, sym_file): (sym_file, key, mtime)
                        for sym_file, key, mtime in parse_targets
                    }
                    for future in as_completed(future_map):
                        sym_file, key, mtime = future_map[future]
                        try:
                            symbols = future.result()
                        except Exception as exc:
                            diagnostics.warnings.append(f"Failed to parse {key}: {exc}")
                            continue
                        lib_cache[key] = {"mtime": mtime, "symbols": symbols}
                        cache_updated = True
            else:
                for sym_file, key, mtime in parse_targets:
                    try:
                        symbols = self.parser.parse_lib_full(sym_file)
                    except Exception as exc:
                        diagnostics.warnings.append(f"Failed to parse {key}: {exc}")
                        continue
                    lib_cache[key] = {"mtime": mtime, "symbols": symbols}
                    cache_updated = True
        result.data_store = self._build_data_store(lib_cache)
        if cache_updated:
            diagnostics.metadata = self._write_library_cache(lib_cache, root_key)
        else:
            diagnostics.metadata = self._cache_metadata(lib_cache, root_key)
        result.diagnostics = diagnostics
        return result

    def _expand_paths(self, roots: Iterable[str]) -> Iterable[Path]:
        for root in roots:
            try:
                path = Path(root)
                if path.is_dir():
                    yield from path.rglob("*.kicad_sym")
                elif path.suffix == ".kicad_sym" and path.exists():
                    yield path
            except Exception:
                continue

    def _file_mtime(self, path: Path) -> float:
        try:
            return path.stat().st_mtime
        except Exception:
            return 0.0

    def _build_data_store(self, lib_cache: Dict[str, Dict]) -> Dict[str, Dict]:
        data_store = {}
        for file_path, entry in lib_cache.items():
            symbols = entry.get("symbols") or []
            if not isinstance(symbols, list) or not symbols:
                continue
            lib_name = Path(file_path).stem
            lib_dict = data_store.setdefault(lib_name, {})
            for symbol in symbols:
                name = symbol.get("name")
                if not name:
                    continue
                lib_dict[name] = symbol
        return data_store

    def _load_cache(self, root_key, section_key, expected_version, root_field) -> Tuple[Dict, CacheMetadata, List[str]]:
        metadata = CacheMetadata(format_version=expected_version)
        warnings = []
        if not self.cache_path.exists():
            warnings.append("Cache file missing.")
            return {}, metadata, warnings
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as exc:
            warnings.append(f"Failed to read cache: {exc}")
            return {}, metadata, warnings
        meta_payload = payload.get("__meta__", {})
        metadata.format_version = meta_payload.get("format_version", expected_version)
        metadata.generated_at = meta_payload.get("generated_at", "")
        metadata.entry_count = meta_payload.get("entry_count", 0)
        metadata.cache_hash = meta_payload.get("cache_hash", "")
        metadata.symbol_path = meta_payload.get(root_field, "")
        if metadata.format_version != expected_version:
            warnings.append(f"Cache version mismatch (got {metadata.format_version}, expected {expected_version}).")
        if metadata.symbol_path and root_key and metadata.symbol_path != root_key:
            warnings.append(f"Cache root changed: {metadata.symbol_path} -> {root_key}.")
        entries = payload.get(section_key)
        if not isinstance(entries, dict):
            warnings.append(f"Cache section '{section_key}' missing.")
            return {}, metadata, warnings
        return entries, metadata, warnings

    def _write_library_cache(self, lib_cache: Dict[str, Dict], root_key: str) -> CacheMetadata:
        metadata = self._cache_metadata(lib_cache, root_key)
        payload = {"__meta__": asdict(metadata), "files": lib_cache}
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            metadata.warnings = [f"Failed to write cache: {exc}"]
        return metadata

    def _cache_metadata(self, lib_cache: Dict[str, Dict], root_key: str) -> CacheMetadata:
        metadata = CacheMetadata(
            symbol_path=root_key,
            format_version=self.FORMAT_VERSION,
            generated_at=datetime.utcnow().isoformat(),
            entry_count=len(lib_cache),
            cache_hash=self._hash_entries(lib_cache),
        )
        return metadata

    def _hash_entries(self, entries: Dict[str, Dict]) -> str:
        digest = hashlib.sha1()
        for key in sorted(entries.keys()):
            entry = entries[key]
            digest.update(f"{key}:{entry.get('mtime', 0)}".encode("utf-8"))
        return digest.hexdigest()


class FootprintIndexer:
    FORMAT_VERSION = 1

    def __init__(self, resolver: PathResolver, cache_path: Path):
        self.resolver = resolver
        self.cache_path = Path(cache_path)

    def scan(self, roots: List[str]) -> Tuple[Dict[str, str], CacheDiagnostics]:
        diagnostics = CacheDiagnostics(metadata=CacheMetadata(format_version=self.FORMAT_VERSION))
        if not roots:
            return {}, diagnostics
        root_key = ";".join(roots)
        existing, meta, warnings = self._load_cache(root_key, "libraries", self.FORMAT_VERSION, "footprint_path")
        diagnostics.metadata = meta
        diagnostics.warnings.extend(warnings)
        new_map = {}
        for root in roots:
            try:
                for pretty in Path(root).rglob("*.pretty"):
                    if pretty.is_dir():
                        new_map[pretty.stem] = str(pretty)
            except Exception as exc:
                diagnostics.warnings.append(f"Failed to scan footprints in {root}: {exc}")
        if not new_map:
            return {}, diagnostics
        if new_map != existing:
            diagnostics.metadata = self._write_cache(new_map, root_key)
        else:
            diagnostics.metadata = self._cache_metadata(new_map, root_key, root_field="footprint_path")
        return new_map, diagnostics

    def _load_cache(self, root_key, section_key, expected_version, root_field) -> Tuple[Dict[str, str], CacheMetadata, List[str]]:
        metadata = CacheMetadata(format_version=expected_version)
        warnings = []
        if not self.cache_path.exists():
            warnings.append("Cache file missing.")
            return {}, metadata, warnings
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
        except Exception as exc:
            warnings.append(f"Failed to read cache: {exc}")
            return {}, metadata, warnings
        meta_payload = payload.get("__meta__", {})
        metadata.format_version = meta_payload.get("format_version", expected_version)
        metadata.generated_at = meta_payload.get("generated_at", "")
        metadata.entry_count = meta_payload.get("entry_count", 0)
        metadata.cache_hash = meta_payload.get("cache_hash", "")
        metadata.footprint_path = meta_payload.get(root_field, "")
        if metadata.format_version != expected_version:
            warnings.append(f"Footprint cache version mismatch (got {metadata.format_version}).")
        if metadata.footprint_path and root_key and metadata.footprint_path != root_key:
            warnings.append(f"Footprint cache root changed: {metadata.footprint_path} -> {root_key}.")
        entries = payload.get(section_key)
        if not isinstance(entries, dict):
            warnings.append(f"Cache section '{section_key}' missing.")
            return {}, metadata, warnings
        return entries, metadata, warnings

    def _write_cache(self, lib_map: Dict[str, str], root_key: str) -> CacheMetadata:
        metadata = self._cache_metadata(lib_map, root_key, root_field="footprint_path")
        payload = {"__meta__": asdict(metadata), "libraries": lib_map}
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(payload, f)
        except Exception as exc:
            metadata.warnings = [f"Failed to write footprint cache: {exc}"]
        return metadata

    def _cache_metadata(self, lib_map, root_key, root_field):
        return CacheMetadata(
            footprint_path=root_key,
            format_version=self.FORMAT_VERSION,
            generated_at=datetime.utcnow().isoformat(),
            entry_count=len(lib_map),
            cache_hash=self._hash_entries(lib_map),
        )

    def _hash_entries(self, entries: Dict[str, str]) -> str:
        digest = hashlib.sha1()
        for key in sorted(entries.keys()):
            digest.update(f"{key}:{entries[key]}".encode("utf-8"))
        return digest.hexdigest()
