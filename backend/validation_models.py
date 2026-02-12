from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ValidationFailure:
    lib: str
    name: str
    message: str
    severity: str


@dataclass
class ValidationSummary:
    timestamp: str
    scope: str
    target_lib: Optional[str]
    status: str
    stats: Dict[str, Any]
    failures: List[ValidationFailure]
    affected: List[str]
