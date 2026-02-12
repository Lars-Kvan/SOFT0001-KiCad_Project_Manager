import re
import os
from collections import defaultdict
from pathlib import Path
from backend.parser import KiCadParser

class Validator:
    FOOTPRINT_RULES = (
        "Library path missing",
        "Failed to parse footprint",
        "No pads defined",
        "Unnumbered pads present",
        "Pad has zero size",
        "Pad drill larger than pad",
    )
    def __init__(self, logic):
        self.logic = logic

    def _lib_matches(self, lib, scope, target_lib):
        if scope != "selected":
            return True
        if isinstance(target_lib, (list, tuple, set)):
            return lib in target_lib
        return lib == target_lib

    def validate_and_get_stats(self, scope="all", target_lib=None):
        failures = []
        stats = {
            "total_checked": 0,
            "total_fails": 0,
            "fails_by_lib": defaultdict(int)
        }

        # Helper to run checks
        def run_checks(is_shadow=False):
            res_list = []
            for lib, parts in self.logic.data_store.items():
                if not self._lib_matches(lib, scope, target_lib):
                    continue

                lib_exemptions = self.logic.exemptions['libraries'].get(lib, [])
                
                for name, data in parts.items():
                    if not is_shadow: stats["total_checked"] += 1
                    uid = f"{lib}:{name}"
                    part_exemptions = self.logic.exemptions['parts'].get(uid, [])
                    props = data.get("properties", {})

                    # 1. Global Rules
                    for rule_name, rule_regex in self.logic.global_rules.items():
                        is_exempt = rule_name in lib_exemptions or rule_name in part_exemptions
                        
                        if is_shadow != is_exempt: continue # Skip if mode doesn't match exemption status

                        if rule_name not in props:
                            res_list.append((lib, name, f"Missing Global Property: '{rule_name}'"))
                            if not is_shadow: 
                                stats["total_fails"] += 1
                                stats["fails_by_lib"][lib] += 1
                        elif rule_regex:
                            val = props[rule_name]
                            if not re.fullmatch(rule_regex, val):
                                res_list.append((lib, name, f"Invalid '{rule_name}': '{val}' (Regex: {rule_regex})"))
                                if not is_shadow:
                                    stats["total_fails"] += 1
                                    stats["fails_by_lib"][lib] += 1

                    # 2. Library Rules
                    if lib in self.logic.library_rules:
                        for rule_name in self.logic.library_rules[lib]:
                            is_exempt = rule_name in lib_exemptions or rule_name in part_exemptions
                            if is_shadow != is_exempt: continue

                            if rule_name not in props:
                                res_list.append((lib, name, f"Missing Library Rule: '{rule_name}'"))
                                if not is_shadow:
                                    stats["total_fails"] += 1
                                    stats["fails_by_lib"][lib] += 1
            return res_list

        failures = run_checks(is_shadow=False)
        return failures, stats

    def get_exempted_failures(self, scope="all", target_lib=None):
        # Re-runs logic but flips the exemption filter
        failures = []
        for lib, parts in self.logic.data_store.items():
            if not self._lib_matches(lib, scope, target_lib):
                continue
            
            lib_exemptions = self.logic.exemptions['libraries'].get(lib, [])
            
            for name, data in parts.items():
                uid = f"{lib}:{name}"
                part_exemptions = self.logic.exemptions['parts'].get(uid, [])
                props = data.get("properties", {})

                # Check Global
                for rule_name, rule_regex in self.logic.global_rules.items():
                    if rule_name in lib_exemptions or rule_name in part_exemptions:
                        # Check if it actually fails
                        if rule_name not in props or (rule_regex and not re.fullmatch(rule_regex, props[rule_name])):
                            failures.append((lib, name, f"[Exempt] '{rule_name}'"))

                # Check Library
                if lib in self.logic.library_rules:
                    for rule_name in self.logic.library_rules[lib]:
                        if rule_name in lib_exemptions or rule_name in part_exemptions:
                            if rule_name not in props:
                                failures.append((lib, name, f"[Exempt] '{rule_name}'"))
        return failures

    def check_duplicate_mpns(self):
        mpn_map = defaultdict(list)
        for lib, parts in self.logic.data_store.items():
            for name, data in parts.items():
                props = data.get("properties", {})
                # Try common keys for MPN
                mpn = None
                for k in ["MPN", "MFR_PART", "MANUFACTURER_PART_NUMBER", "Part Number"]:
                    if k in props:
                        mpn = props[k]
                        break
                
                if mpn and mpn != "~" and mpn.lower() != "n/a":
                    mpn_map[mpn].append(f"{lib}:{name}")
        
        return {k: v for k, v in mpn_map.items() if len(v) > 1}

    def check_footprint_integrity(self):
        """Checks if symbol pins match footprint pads."""
        issues = []
        fp_cache = {} # Cache parsed footprints to speed up check

        for lib, parts in self.logic.data_store.items():
            for name, data in parts.items():
                fp_ref = data.get("properties", {}).get("Footprint")
                if not fp_ref: continue # Skip parts without footprints (e.g. logos)
                
                if fp_ref not in fp_cache:
                    fp_cache[fp_ref] = self.logic.get_footprint_data(fp_ref)
                
                fp_data = fp_cache[fp_ref]
                if not fp_data:
                    issues.append((lib, name, f"Footprint file not found: {fp_ref}"))
                    continue
                
                # Compare Pins vs Pads
                sym_pins = set(p["number"] for p in data.get("pins", []))
                fp_pads = set(p["number"] for p in fp_data.get("pads", []))
                
                missing_on_fp = sym_pins - fp_pads
                if missing_on_fp:
                    issues.append((lib, name, f"Pins missing on footprint: {', '.join(sorted(missing_on_fp))}"))
        return issues

    def get_footprint_rules(self):
        return list(self.FOOTPRINT_RULES)

    def _fp_is_exempt(self, lib, fp_name, rule_name):
        fp_ex = self.logic.exemptions.get("footprints", {}).get(f"{lib}:{fp_name}", [])
        lib_ex = self.logic.exemptions.get("fp_libraries", {}).get(lib, [])
        return rule_name in fp_ex or rule_name in lib_ex

    def validate_symbols(self, scope="all", target_lib=None):
        """Runs structural symbol checks."""
        issues = []
        for lib, parts in self.logic.data_store.items():
            if not self._lib_matches(lib, scope, target_lib):
                continue
            for name, data in parts.items():
                props = data.get("properties", {})
                pins = data.get("pins", []) or []

                if "Reference" not in props:
                    issues.append((lib, name, "Missing Reference property"))
                if "Value" not in props:
                    issues.append((lib, name, "Missing Value property"))
                if not pins:
                    issues.append((lib, name, "No pins defined"))

                # Pin number checks (warn-level)
                pin_nums = [str(p.get("number", "")).strip() for p in pins]
                empty_pins = [n for n in pin_nums if not n or n == "~"]
                if pins and empty_pins:
                    issues.append((lib, name, "Pin(s) with empty number"))

                nums = [n for n in pin_nums if n and n != "~"]
                dupes = sorted({n for n in nums if nums.count(n) > 1})
                if dupes:
                    issues.append((lib, name, f"Duplicate pin numbers (check if intentional): {', '.join(dupes)}"))

                # Footprint property only required when pins exist
                if pins and not props.get("Footprint"):
                    issues.append((lib, name, "Missing Footprint property"))

        return issues

    def validate_footprints(self, scope="all", target_lib=None):
        """Runs structural footprint checks on all footprint libraries."""
        issues = []

        if not getattr(self.logic, "footprint_lib_map", {}):
            self.logic.scan_footprint_libraries()

        for lib, lib_path in (self.logic.footprint_lib_map or {}).items():
            if not self._lib_matches(lib, scope, target_lib):
                continue
            if not lib_path or not os.path.exists(lib_path):
                rule = "Library path missing"
                if not self._fp_is_exempt(lib, "-", rule):
                    issues.append((lib, "-", rule))
                continue

            for fp_file in Path(lib_path).rglob("*.kicad_mod"):
                fp_name = fp_file.stem
                fp = KiCadParser.parse_footprint_full(fp_file)
                if not fp:
                    rule = "Failed to parse footprint"
                    if not self._fp_is_exempt(lib, fp_name, rule):
                        issues.append((lib, fp_name, rule))
                    continue

                pads = fp.get("pads", []) or []
                if not pads:
                    rule = "No pads defined"
                    if not self._fp_is_exempt(lib, fp_name, rule):
                        issues.append((lib, fp_name, rule))
                    continue

                pad_nums = [str(p.get("number", "")).strip() for p in pads]
                has_numbered = any(n and n != "~" for n in pad_nums)
                has_empty = any((not n) or n == "~" for n in pad_nums)
                if has_numbered and has_empty:
                    rule = "Unnumbered pads present"
                    if not self._fp_is_exempt(lib, fp_name, rule):
                        issues.append((lib, fp_name, rule))

                for pad in pads:
                    num = str(pad.get("number", "")).strip() or "?"
                    size = pad.get("size", [])
                    if not size or len(size) < 2 or size[0] <= 0 or size[1] <= 0:
                        rule = "Pad has zero size"
                        if not self._fp_is_exempt(lib, fp_name, rule):
                            issues.append((lib, fp_name, f"{rule}: Pad {num}"))

                    drill = pad.get("drill")
                    if isinstance(drill, dict):
                        dsize = drill.get("size", [])
                        if dsize:
                            drill_max = max(dsize)
                            pad_min = min(size) if size and len(size) >= 2 else 0
                            if pad_min > 0 and drill_max > pad_min:
                                rule = "Pad drill larger than pad"
                                if not self._fp_is_exempt(lib, fp_name, rule):
                                    issues.append((lib, fp_name, f"{rule}: Pad {num}"))

        return issues

    def bulk_edit_property(self, lib, name, key, new_val):
        """Updates a property in the actual .kicad_sym file."""
        if lib not in self.logic.data_store or name not in self.logic.data_store[lib]:
            return False, "Part not found in memory."
        
        data = self.logic.data_store[lib][name]
        file_path = data.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            return False, "Source file not found."

        success, msg = KiCadParser.update_symbol_property(file_path, name, key, new_val)
        if success:
            # Update memory
            if "properties" not in self.logic.data_store[lib][name]:
                self.logic.data_store[lib][name]["properties"] = {}
            self.logic.data_store[lib][name]["properties"][key] = new_val
            return True, "Property updated successfully."
        return False, msg
