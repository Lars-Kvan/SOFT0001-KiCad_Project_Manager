from dataclasses import dataclass
from typing import List

from backend.path_utils import PathResolver


@dataclass
class PathsConfig:
    resolver: PathResolver
    settings: dict

    def symbol_roots(self) -> List[str]:
        return self.resolver.resolve_path_list(self.settings.get("symbol_path", ""))

    def footprint_roots(self) -> List[str]:
        return self.resolver.resolve_path_list(self.settings.get("footprint_path", ""))

    def backup_root(self) -> str:
        return self.resolver.resolve_path(self.settings.get("backup", {}).get("path", "backups"))
