import json
from dataclasses import asdict
from datetime import datetime

from backend.validator import Validator
from backend.validation_models import ValidationFailure, ValidationSummary


class ValidationService:
    CACHE_NAME = "validation_cache.json"

    def __init__(self, logic, validator=None):
        self.logic = logic
        self.validator = validator or Validator(logic)
        self.cache_path = self.logic.cache_dir / self.CACHE_NAME

    def run_validation(self, scope="all", target_lib=None) -> ValidationSummary:
        failures, stats = self.validator.validate_and_get_stats(scope, target_lib)
        formatted = self._format_failures(failures)
        summary = ValidationSummary(
            timestamp=datetime.utcnow().isoformat() + "Z",
            scope=scope,
            target_lib=target_lib,
            status="error" if stats.get("total_fails", 0) else "ok",
            stats=stats,
            failures=formatted,
            affected=sorted({f"{item.lib}:{item.name}" for item in formatted}),
        )
        self._cache_summary(summary)
        return summary

    def get_cached_summary(self) -> ValidationSummary | dict:
        if not self.cache_path.exists():
            return {}
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            return self._deserialize_summary(payload)
        except Exception:
            return {}

    def _format_failures(self, failures):
        results = []
        for lib, name, message in failures:
            severity = self._infer_severity(message)
            results.append(
                ValidationFailure(
                    lib=lib,
                    name=name,
                    message=message,
                    severity=severity,
                )
            )
        return results

    @staticmethod
    def _infer_severity(message):
        if not message:
            return "warning"
        text = message.lower()
        keywords = ("missing", "failed", "invalid", "duplicate", "error")
        return "error" if any(keyword in text for keyword in keywords) else "warning"

    def _cache_summary(self, summary: ValidationSummary):
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(asdict(summary), f, indent=2)
        except Exception:
            pass

    def _deserialize_summary(self, payload):
        if not isinstance(payload, dict):
            return {}
        failures = payload.get("failures", [])
        deserialized = [
            ValidationFailure(
                lib=f.get("lib", ""),
                name=f.get("name", ""),
                message=f.get("message", ""),
                severity=f.get("severity", "warning"),
            )
            for f in failures
            if isinstance(f, dict)
        ]
        return ValidationSummary(
            timestamp=payload.get("timestamp", ""),
            scope=payload.get("scope", "all"),
            target_lib=payload.get("target_lib"),
            status=payload.get("status", "unknown"),
            stats=payload.get("stats", {}),
            failures=deserialized,
            affected=payload.get("affected", []),
        )
