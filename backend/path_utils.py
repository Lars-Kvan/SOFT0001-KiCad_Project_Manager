import os
import ntpath
import posixpath


class PathResolver:
    """Helper that normalizes, expands, and resolves paths relative to a configurable root."""

    TOKENS = ("${BASE_DIR}", "${PL_VAR}")

    def __init__(self, root_getter=None):
        self._root_getter = root_getter or (lambda: "")
        self._fallback_root = os.getcwd()

    def set_root_getter(self, getter):
        self._root_getter = getter or (lambda: "")

    def _normalize(self, path):
        return str(path).replace("\\", "/") if path else ""

    def normalize(self, path):
        return self._normalize(path)

    def _is_windows_abs_path(self, path):
        if not path:
            return False
        if path.startswith("\\\\") or path.startswith("//"):
            return True
        drive, _ = ntpath.splitdrive(path)
        return bool(drive)

    def _is_abs_path(self, path):
        if not path:
            return False
        return os.path.isabs(path) or self._is_windows_abs_path(path)

    def is_abs_path(self, path):
        return self._is_abs_path(path)

    def _path_module_for(self, path):
        return ntpath if self._is_windows_abs_path(path) else posixpath

    def expand(self, path):
        if not path:
            return ""
        if isinstance(path, (list, tuple, set)):
            path = next(iter(path), "")
        if isinstance(path, os.PathLike):
            path = os.fspath(path)
        if isinstance(path, (list, tuple, set)):
            path = next(iter(path), "")
        if isinstance(path, os.PathLike):
            path = os.fspath(path)
        return self._normalize(os.path.expandvars(os.path.expanduser(path)))

    def get_path_root(self):
        root = self.expand(self._root_getter())
        if not root or root in self.TOKENS:
            root = self._fallback_root
        if not self._is_abs_path(root):
            root = os.path.abspath(root)
        return self._normalize(root)

    def resolve(self, path):
        candidate = self.expand(path)
        if not candidate:
            return ""
        root = self.get_path_root()
        for token in self.TOKENS:
            if token in candidate:
                candidate = candidate.replace(token, root)
        if not root or self._is_abs_path(candidate):
            return self._normalize(candidate)
        return self._normalize(self._path_module_for(root).join(root, candidate))

    def relativize(self, path):
        if not path:
            return ""
        root = self.get_path_root()
        if not root:
            return self._normalize(path)
        norm_path = self._normalize(self.expand(path)).replace("${PL_VAR}", "${BASE_DIR}")
        if "${BASE_DIR}" in norm_path:
            return norm_path
        norm_root = root.rstrip("/")
        root_is_win = self._is_windows_abs_path(norm_root)
        path_is_win = self._is_windows_abs_path(norm_path)
        path_is_posix = norm_path.startswith("/")
        if not path_is_win and not path_is_posix:
            rel = norm_path.lstrip("./")
            return "${BASE_DIR}" if not rel else f"${{BASE_DIR}}/{rel}"
        if root_is_win != path_is_win and (path_is_posix or path_is_win):
            return norm_path
        pmod = ntpath if root_is_win else posixpath
        try:
            rel = pmod.relpath(norm_path, norm_root)
        except Exception:
            return norm_path
        rel = self._normalize(rel)
        if rel in (".", ""):
            return "${BASE_DIR}"
        return "${BASE_DIR}/" + rel

    def split_list(self, raw):
        if isinstance(raw, (list, tuple, set)):
            parts = [str(p) for p in raw]
        else:
            text = "" if raw is None else str(raw)
            parts = []
            for chunk in text.replace("\n", ";").split(";"):
                if chunk:
                    parts.append(chunk)
        return [p.strip() for p in parts if isinstance(p, str) and p.strip()]

    def normalize_path_list(self, raw, resolve=True):
        parts = self.split_list(raw)
        normalized = []
        seen = set()
        for part in parts:
            candidate = self.resolve(part) if resolve else self._normalize(part)
            if not candidate:
                continue
            key = candidate.lower()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(candidate)
        return normalized

    def resolve_path_list(self, raw):
        return self.normalize_path_list(raw, resolve=True)

    def resolve_path_list_string(self, raw):
        paths = self.resolve_path_list(raw)
        return ";".join(p for p in paths if p)

    def relativize_path_list_string(self, raw):
        values = self.split_list(raw)
        if not values:
            return ""
        relativized = [self.relativize(v) for v in values if v]
        return ";".join(relativized)
