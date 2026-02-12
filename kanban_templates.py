"""Shared helpers for working with Kanban task templates."""

from typing import Any, Dict, List

DEFAULT_CATEGORY = "Task"
DEFAULT_PRIORITY = "Normal"
DEFAULT_LANE = "todo"
DEFAULT_COLUMNS = ["todo", "prog", "done"]

LANE_ALIASES = {
    "todo": "todo",
    "to do": "todo",
    "to-do": "todo",
    "todo list": "todo",
    "in progress": "prog",
    "in-progress": "prog",
    "prog": "prog",
    "progress": "prog",
    "doing": "prog",
    "done": "done",
    "completed": "done",
    "complete": "done",
}


def _shrink_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def normalize_lane(value: Any) -> str:
    """Return a normalized lane key (todo/prog/done) from user input."""
    if value is None:
        return DEFAULT_LANE
    text = str(value).strip().lower()
    if not text:
        return DEFAULT_LANE
    return LANE_ALIASES.get(text, DEFAULT_LANE)


def normalize_template_entry(entry: Any) -> Dict[str, Any]:
    """Convert a template entry (string or dict) into a normalized dictionary."""
    if entry is None:
        return {}

    if isinstance(entry, str):
        name = entry.strip()
        if not name:
            return {}
        normalized = {
            "name": name,
            "category": DEFAULT_CATEGORY,
            "priority": DEFAULT_PRIORITY,
            "description": "",
            "lane": DEFAULT_LANE,
            "progress": 0,
        }
        return normalized

    if isinstance(entry, dict):
        name = _shrink_text(entry.get("name") or entry.get("title"))
        if not name:
            return {}
        category = _shrink_text(entry.get("category") or entry.get("type") or DEFAULT_CATEGORY) or DEFAULT_CATEGORY
        priority = _shrink_text(entry.get("priority") or DEFAULT_PRIORITY) or DEFAULT_PRIORITY
        description = _shrink_text(entry.get("description") or entry.get("desc") or "")
        lane = normalize_lane(entry.get("lane") or entry.get("column") or entry.get("stage"))
        progress = entry.get("progress", 0)
        try:
            progress = float(progress)
        except (TypeError, ValueError):
            progress = 0
        return {
            "name": name,
            "category": category,
            "priority": priority,
            "description": description,
            "lane": lane,
            "progress": progress,
        }

    return {}


def normalize_template_list(entries: Any) -> List[Dict[str, Any]]:
    """Normalize a list (or dict-like) of template entries."""
    normalized = []
    if isinstance(entries, dict):
        entries = list(entries.values())
    if not entries:
        return normalized
    for entry in entries:
        item = normalize_template_entry(entry)
        if item:
            normalized.append(item)
    return normalized


def task_from_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a normalized template entry into the Kanban task data structure."""
    return {
        "name": entry.get("name", ""),
        "desc": entry.get("description", ""),
        "progress": float(entry.get("progress", 0)),
        "category": entry.get("category", DEFAULT_CATEGORY),
        "priority": entry.get("priority", DEFAULT_PRIORITY),
    }


def columns_from_templates(
    raw_entries: Any, columns: List[str] = None
) -> Dict[str, List[Dict[str, Any]]]:
    """Build kanban columns from the provided template entries."""
    normalized = normalize_template_list(raw_entries)
    columns = columns[:] if columns else DEFAULT_COLUMNS[:]
    board = {col: [] for col in columns}
    for entry in normalized:
        lane = entry.get("lane", DEFAULT_LANE)
        if lane not in board:
            board[lane] = []
        board[lane].append(task_from_entry(entry))
    for col in columns:
        board.setdefault(col, [])
    return board


def parse_template_line(line: str) -> Dict[str, Any]:
    """Parse a single template line using the pipe-delimited editor format."""
    if not line:
        return {}
    parts = [part.strip() for part in line.split("|", 4)]
    if not parts or not parts[0]:
        return {}
    entry = {
        "name": parts[0],
        "category": DEFAULT_CATEGORY,
        "priority": DEFAULT_PRIORITY,
        "lane": DEFAULT_LANE,
        "description": "",
        "progress": 0,
    }
    if len(parts) > 1 and parts[1]:
        entry["category"] = parts[1]
    if len(parts) > 2 and parts[2]:
        entry["priority"] = parts[2]
    if len(parts) > 3 and parts[3]:
        entry["lane"] = normalize_lane(parts[3])
    if len(parts) > 4:
        entry["description"] = parts[4]
    return entry


def format_template_entry(entry: Dict[str, Any]) -> str:
    """Render a normalized entry back into the editor text field."""
    if not entry or not entry.get("name"):
        return ""
    name = entry["name"]
    category = entry.get("category", DEFAULT_CATEGORY)
    priority = entry.get("priority", DEFAULT_PRIORITY)
    lane = entry.get("lane", DEFAULT_LANE)
    desc = entry.get("description", "")
    base = f"{name} | {category} | {priority} | {lane}"
    if desc:
        base = f"{base} | {desc}"
    return base
