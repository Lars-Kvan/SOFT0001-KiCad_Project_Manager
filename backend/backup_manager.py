import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from datetime import datetime

class BackupManager:
    def __init__(self, logic):
        self.logic = logic

    def get_backup_size_details(self):
        path_str = self.logic.settings.get("backup", {}).get("path", "backups")
        root = Path(path_str)
        if not root.is_absolute(): root = Path(os.getcwd()) / root
        
        details = {}
        grand_total = 0
        for cat in ["app_data", "symbols", "footprints"]:
            cat_path = root / cat
            size = 0
            if cat_path.exists():
                for p in cat_path.glob("*.zip"):
                    if p.is_file(): size += p.stat().st_size
            details[cat] = self._fmt_size(size)
            grand_total += size
        
        details['total'] = self._fmt_size(grand_total)
        return details

    def _fmt_size(self, size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024: return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"

    def perform_backup(self, force=False):
        """Checks schedules and performs backups for enabled categories."""
        cfg = self.logic.settings.get("backup", {})
        root_path = Path(cfg.get("path", "backups"))
        if not root_path.is_absolute(): root_path = Path(os.getcwd()) / root_path
        
        now = datetime.now()
        
        for key in ["app_data", "symbols", "footprints"]:
            c = cfg.get(key, {})
            if not c.get("enabled", False) and not force:
                continue
            
            last_str = c.get("last_run", "")
            interval = c.get("interval_min", 60)
            
            should_run = False
            if force:
                should_run = True
            elif not last_str:
                should_run = True 
            else:
                try:
                    last = datetime.strptime(last_str, "%Y-%m-%d %H:%M:%S")
                    if (now - last).total_seconds() / 60 >= interval:
                        should_run = True
                except:
                    should_run = True
            
            if should_run:
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                dest_dir = root_path / key
                dest_dir.mkdir(parents=True, exist_ok=True)

                dest_zip = dest_dir / f"{key}_{timestamp}.zip"
                if dest_zip.exists():
                    dest_zip.unlink()
                try:
                    with tempfile.TemporaryDirectory() as tmp_dir:
                        tmp = Path(tmp_dir)
                        if key == "app_data":
                            for fname in self.logic.get_settings_files():
                                if os.path.exists(fname):
                                    dest = tmp / fname
                                    dest.parent.mkdir(parents=True, exist_ok=True)
                                    shutil.copy(fname, dest)
                        elif key == "symbols":
                            roots = self.logic.resolve_path_list(self.logic.settings.get("symbol_path"))
                            for src in roots:
                                if src and os.path.exists(src):
                                    for f in Path(src).rglob("*.kicad_sym"):
                                        shutil.copy(f, tmp / f.name)
                        elif key == "footprints":
                            roots = self.logic.resolve_path_list(self.logic.settings.get("footprint_path"))
                            for src in roots:
                                if src and os.path.exists(src):
                                    for f in Path(src).glob("*.pretty"):
                                        if f.is_dir():
                                            shutil.copytree(f, tmp / f.name, dirs_exist_ok=True)

                        self._write_zip_archive(tmp, dest_zip)

                    # Update State & Retention
                    c["last_run"] = now.strftime("%Y-%m-%d %H:%M:%S")
                    self.logic.save_settings()
                    
                    max_b = c.get("max_backups", 10)
                    if max_b > 0:
                        backups = sorted([x for x in dest_dir.glob("*.zip") if x.is_file()], key=lambda x: x.name)
                        while len(backups) > max_b:
                            oldest = backups.pop(0)
                            oldest.unlink()
                except Exception as e:
                    if dest_zip.exists():
                        dest_zip.unlink(missing_ok=True)
                    print(f"Backup {key} failed: {e}")

    def _write_zip_archive(self, source_dir: Path, destination: Path):
        with zipfile.ZipFile(destination, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path in sorted(source_dir.rglob("*")):
                if path.is_file():
                    archive.write(path, path.relative_to(source_dir))

    def restore_backup(self, timestamp):
        cfg = self.logic.settings.get("backup", {})
        path_str = cfg.get("path", "backups")
        dest = Path(path_str)
        if not dest.is_absolute(): dest = Path(os.getcwd()) / dest
        
        target_zip = dest / "app_data" / f"{timestamp}.zip"
        if not target_zip.exists():
            return False

        restored_settings = False
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            try:
                with zipfile.ZipFile(target_zip, "r") as zf:
                    zf.extractall(tmp_path)
            except Exception:
                return False

            for fname in self.logic.get_settings_files():
                fpath = tmp_path / fname
                if fpath.exists():
                    dest = Path(fname)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy(fpath, dest)
                    restored_settings = True

        if restored_settings:
            self.logic.load_settings()
            self.logic.load_rules()
        return restored_settings
