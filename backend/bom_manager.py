import os
from pathlib import Path
from typing import Dict, List, Tuple

from backend.parser import KiCadParser


class BOMService:
    """Central service for BOM generation."""

    def __init__(self, logic):
        self.logic = logic

    def generate_bom(self, root_sch_path: str) -> List[Dict[str, object]]:
        if not root_sch_path or not os.path.exists(root_sch_path):
            print(f"Error: Root schematic path not found: {root_sch_path}")
            return []

        print(f"DEBUG: Generating BOM from root: {root_sch_path}")
        bom_data: Dict[Tuple[str, str, str], Dict[str, object]] = {}

        def traverse(file_path: str, hierarchy_chain: List[str], uuid_path: str = "/", recursive: bool = True):
            if file_path in hierarchy_chain or not os.path.exists(file_path):
                return

            try:
                comps, sheets = KiCadParser.parse_schematic(file_path)
                comps = comps or []
                sheets = sheets or []
                sheet_name = Path(file_path).stem

                for comp in comps:
                    ref = self._resolve_reference(comp, uuid_path)
                    self._record_component(bom_data, comp, ref, sheet_name)
            except Exception as err:
                print(f"Error parsing components in {file_path}: {err}")

            if not recursive:
                return

            current_dir = Path(file_path).parent
            for sheet in sheets:
                sub_path = (current_dir / sheet["filename"]).resolve()
                new_uuid = (uuid_path if uuid_path != "/" else "") + "/" + sheet["uuid"]
                traverse(str(sub_path), hierarchy_chain + [file_path], new_uuid)

        traverse(root_sch_path, [])

        if not bom_data:
            project_dir = Path(root_sch_path).parent
            for sch_file in project_dir.rglob("*.kicad_sch"):
                traverse(str(sch_file), [], recursive=False)

        return self._format_result(bom_data)

    def _record_component(
        self,
        bom_data: Dict[Tuple[str, str, str], Dict[str, object]],
        component: Dict[str, object],
        reference: str,
        sheet_name: str,
    ) -> None:
        val = component.get("value", "Unknown Value")
        lib_id = component.get("lib_id", "Unknown Lib")
        footprint = component.get("footprint", "")
        key = (val, lib_id, footprint)

        entry = bom_data.setdefault(key, {
            "value": val,
            "lib_id": lib_id,
            "footprint": footprint,
            "qty": 0,
            "refs": [],
            "dnp_refs": [],
            "excluded_refs": [],
            "sheets": set(),
        })

        if component.get("exclude_from_bom") or component.get("is_power_symbol"):
            entry["excluded_refs"].append(reference)
        elif component.get("dnp"):
            entry["dnp_refs"].append(reference)
        else:
            entry["qty"] += 1
            entry["refs"].append(reference)

        entry["sheets"].add(sheet_name)

    def _resolve_reference(self, component: Dict[str, object], uuid_path: str) -> str:
        ref = component.get("ref", "?")
        instances = component.get("instances")
        if not isinstance(instances, list):
            return ref

        for inst in instances:
            if not isinstance(inst, list) or not inst:
                continue
            if inst[0] != "project":
                continue
            for attr in inst[2:]:
                if not isinstance(attr, list) or attr[0] != "path" or len(attr) < 2:
                    continue
                if attr[1] != uuid_path:
                    continue
                for child in inst:
                    if isinstance(child, list) and child[0] == "reference" and len(child) > 1:
                        ref = child[1]
        return ref

    def _format_result(
        self,
        bom_data: Dict[Tuple[str, str, str], Dict[str, object]],
    ) -> List[Dict[str, object]]:
        result: List[Dict[str, object]] = []
        for entry in bom_data.values():
            all_refs = sorted(entry["refs"] + entry["dnp_refs"] + entry["excluded_refs"])
            result.append({
                "qty": entry["qty"],
                "value": entry["value"],
                "footprint": entry["footprint"],
                "dnp": ", ".join(sorted(entry["dnp_refs"])),
                "excluded": ", ".join(sorted(entry["excluded_refs"])),
                "lib_id": entry["lib_id"],
                "sheet": ", ".join(sorted(entry["sheets"])),
                "refs": ", ".join(all_refs),
            })
        return result
