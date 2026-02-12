from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class CacheMetadata:
    symbol_path: str = ""
    footprint_path: str = ""
    format_version: int = 0
    generated_at: str = ""
    entry_count: int = 0
    cache_hash: str = ""


@dataclass
class CacheDiagnostics:
    metadata: CacheMetadata
    warnings: List[str] = field(default_factory=list)


@dataclass
class IndexResult:
    data_store: Dict[str, Dict] = field(default_factory=dict)
    diagnostics: CacheDiagnostics = field(default_factory=lambda: CacheDiagnostics(CacheMetadata()))
