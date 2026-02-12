import json
import os
from pathlib import Path

class SettingsManager:
    def __init__(self, logic):
        self.logic = logic
        self.settings = {}
        self.global_rules = {}
        self.library_rules = {}
        self.exemptions = {}
        self.config_dir = Path("data") / "config"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.settings_path = self.config_dir / "settings.json"
        self.rules_path = self.config_dir / "rules.json"

    def load_settings(self):
        # In a real application, you would load from a file
        self.settings = {
            "theme": "Light",
            "project_types": ["PCB", "Firmware", "Mechanical", "Other"],
            "kanban_templates": {
                "Standard": [
                    {"name": "Task 1"},
                    {"name": "Task 2"},
                ]
            },
            "project_filter_presets": [],
            "checklist_templates": {
                "Standard": {
                    "Schematic": ["Item 1"],
                    "Layout": ["Item 2"]
                }
            },
            "project_statuses": [
                "Pre-Design", "Schematic Capture", "PCB Layout", "Prototyping",
                "Validation", "Released", "Abandoned"
            ],
            "project_metadata_defaults": {
                "default_revision": "A",
                "default_description": ""
            },
            "kanban_categories": {
                "Task": "#3498db",
                "Bug": "#c0392b"
            },
            "kanban_priority_weights": {
                "Critical": 5, "High": 3, "Normal": 1, "Low": 0.5
            },
            "backup": {
                "path": "backups",
                "backup_on_exit": False,
                "app_data": {"enabled": True, "interval_min": 60, "max_backups": 5, "last_run": ""},
                "symbols": {"enabled": False, "interval_min": 120, "max_backups": 3, "last_run": ""},
                "footprints": {"enabled": False, "interval_min": 120, "max_backups": 3, "last_run": ""}
            },
            "external_tools": {
                "editor": "",
                "kicad": ""
            }
        }
        # Load from files if they exist
        if self.settings_path.exists():
            with open(self.settings_path, "r") as f:
                self.settings.update(json.load(f))

    def save_settings(self):
        with open(self.settings_path, "w") as f:
            json.dump(self.settings, f, indent=4)

    def load_rules(self):
        if self.rules_path.exists():
            with open(self.rules_path, "r") as f:
                rules = json.load(f)
                self.global_rules = rules.get("global_rules", {})
                self.library_rules = rules.get("library_rules", {})
                self.exemptions = rules.get("exemptions", {})

    def save_rules(self):
        rules = {
            "global_rules": self.global_rules,
            "library_rules": self.library_rules,
            "exemptions": self.exemptions
        }
        with open(self.rules_path, "w") as f:
            json.dump(rules, f, indent=4)

    def get_settings_files(self):
        return [str(self.settings_path), str(self.rules_path)]

    def add_part_exemption(self, lib, name, rule):
        if lib not in self.exemptions:
            self.exemptions[lib] = {}
        if name not in self.exemptions[lib]:
            self.exemptions[lib][name] = []
        if rule not in self.exemptions[lib][name]:
            self.exemptions[lib][name].append(rule)
        self.save_rules()

    def add_lib_exemption(self, lib, rule):
        if lib not in self.exemptions:
            self.exemptions[lib] = {}
        if "_library_wide" not in self.exemptions[lib]:
            self.exemptions[lib]["_library_wide"] = []
        if rule not in self.exemptions[lib]["_library_wide"]:
            self.exemptions[lib]["_library_wide"].append(rule)
        self.save_rules()
