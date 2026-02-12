import hashlib
import json
import os
import shutil
from pathlib import Path

from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QToolButton, QGridLayout
from PySide6.QtCore import Qt, QUrl, QThread, Signal, QSize
from PySide6 import QtCore
from PySide6 import QtWebEngineWidgets, QtWebEngineCore
from ui.resources.icons import Icons


class _ModelConvertWorker(QThread):
    finished = Signal(str, int)
    failed = Signal(str, int)

    def __init__(self, gmsh_cmd, src_path, dst_path, token, parent=None):
        super().__init__(parent)
        self.gmsh_cmd = gmsh_cmd
        self.src_path = src_path
        self.dst_path = dst_path
        self.token = token

    def run(self):
        try:
            import subprocess
            proc = subprocess.run(
                [self.gmsh_cmd, "-3", self.src_path, "-format", "stl", "-o", self.dst_path, "-v", "0"],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0:
                err = proc.stderr.strip() or proc.stdout.strip() or "Gmsh conversion failed."
                self.failed.emit(err, self.token)
                return
            if not os.path.exists(self.dst_path):
                self.failed.emit("Conversion finished but STL was not created.", self.token)
                return
            self.finished.emit(self.dst_path, self.token)
        except Exception as e:
            self.failed.emit(str(e), self.token)


class _StepConvertWorker(QThread):
    finished = Signal(str, int)
    failed = Signal(str, str, int)

    def __init__(self, widget, src_path, token, parent=None):
        super().__init__(parent)
        self.widget = widget
        self.src_path = src_path
        self.token = token

    def run(self):
        try:
            gltf_path = self.widget._cached_gltf_path(self.src_path)
            if self.widget._is_valid_gltf(gltf_path, self.src_path):
                self.finished.emit(gltf_path, self.token)
                return

            self.widget._ocp_error = ""
            self.widget._freecad_error = ""
            ocp_available = self.widget._ensure_ocp()
            ocp_python = None
            freecad_cmd = ""
            converted = False
            if ocp_available:
                converted = self.widget._convert_step_ocp_to_glb(self.src_path, gltf_path)
            else:
                ocp_python = self.widget._get_ocp_python()
                if ocp_python:
                    converted = self.widget._convert_step_external(ocp_python, self.src_path, gltf_path)
                else:
                    freecad_cmd = self.widget._get_freecad_cmd()
                    if freecad_cmd:
                        converted = self.widget._convert_step_freecad(freecad_cmd, self.src_path, gltf_path)

            if converted:
                self.finished.emit(gltf_path, self.token)
                return
            if not ocp_available and not ocp_python and not freecad_cmd:
                message = self.widget._ocp_error or "OCP unavailable"
            elif freecad_cmd:
                message = self.widget._freecad_error or "FreeCAD conversion failed"
            else:
                message = self.widget._ocp_error or "OCP conversion failed"
            self.failed.emit(message, self.src_path, self.token)
        except Exception as exc:
            self.failed.emit(str(exc), self.src_path, self.token)


class ModelPreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.model_path = ""
        self.reference = ""
        self._load_token = 0
        self._gmsh_worker = None
        self._step_worker = None
        self._gmsh_cmd = self._find_gmsh_cmd()
        self._ocp_checked = False
        self._ocp_available = False
        self._ocp_error = ""
        self._ocp_python = ""
        self._ocp_script_path = ""
        self._freecad_cmd = ""
        self._freecad_error = ""
        self._freecad_script_path = ""

        self.web_view = QtWebEngineWidgets.QWebEngineView()
        self.web_view.setMinimumSize(QSize(200, 200))
        settings = self.web_view.settings()
        settings.setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QtWebEngineCore.QWebEngineSettings.WebAttribute.WebGLEnabled, True)
        self._viewer_ready = False
        self._pending_model_url = ""
        self.web_view.loadFinished.connect(self._on_web_loaded)
        viewer_path = Path(__file__).resolve().parent.parent / "resources" / "web" / "viewer.html"
        self.web_view.setUrl(QUrl.fromLocalFile(str(viewer_path)))

        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.web_view, 0, 0)

        self.overlay = QLabel("")
        self.overlay.setAlignment(Qt.AlignCenter)
        self.overlay.setStyleSheet("color: #3C3F44; background: transparent; padding: 6px;")
        self.overlay.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        overlay_row = QHBoxLayout()
        overlay_row.setContentsMargins(0, 0, 0, 0)
        self.nav_pad = QWidget()
        nav_layout = QGridLayout(self.nav_pad)
        nav_layout.setContentsMargins(0, 0, 0, 0)
        nav_layout.setHorizontalSpacing(4)
        nav_layout.setVerticalSpacing(4)

        self.btn_up = QToolButton()
        self.btn_left = QToolButton()
        self.btn_right = QToolButton()
        self.btn_down = QToolButton()
        icon_color = "#1F2937"
        icon_size = QSize(14, 14)
        self.btn_up.setIcon(Icons.get_icon(Icons.ARROW_UP, icon_color))
        self.btn_left.setIcon(Icons.get_icon(Icons.ARROW_LEFT, icon_color))
        self.btn_right.setIcon(Icons.get_icon(Icons.ARROW_RIGHT, icon_color))
        self.btn_down.setIcon(Icons.get_icon(Icons.ARROW_DOWN, icon_color))
        for btn in (self.btn_up, self.btn_left, self.btn_right, self.btn_down):
            btn.setIconSize(icon_size)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(QSize(24, 24))
            btn.setStyleSheet(
                "QToolButton { background: rgba(255,255,255,0.92); border: 1px solid #CBD5E1; "
                "border-radius: 6px; color: #1F2937; font-weight: 700; }"
                "QToolButton:hover { background: #E8F0FA; border-color: #94A3B8; }"
            )

        nav_layout.addWidget(self.btn_up, 0, 1)
        nav_layout.addWidget(self.btn_left, 1, 0)
        nav_layout.addWidget(self.btn_right, 1, 2)
        nav_layout.addWidget(self.btn_down, 2, 1)
        self.reset_btn = QToolButton()
        self.reset_btn.setText("Reset View")
        self.reset_btn.setCursor(Qt.PointingHandCursor)
        self.reset_btn.setStyleSheet(
            "QToolButton { background: rgba(255,255,255,0.9); border: 1px solid #CBD5E1; "
            "border-radius: 10px; padding: 4px 10px; color: #1F2937; }"
            "QToolButton:hover { background: #E8F0FA; border-color: #94A3B8; }"
        )
        self.reset_btn.clicked.connect(self.reset_view)
        overlay_row.addWidget(self.nav_pad, alignment=Qt.AlignLeft)
        overlay_row.addStretch(1)
        overlay_row.addWidget(self.reset_btn, alignment=Qt.AlignRight)

        overlay_panel = QWidget()
        overlay_panel.setStyleSheet("background: transparent;")
        overlay_layout = QGridLayout(overlay_panel)
        overlay_layout.setContentsMargins(8, 8, 8, 8)
        overlay_layout.addWidget(self.nav_pad, 0, 0, alignment=Qt.AlignLeft | Qt.AlignBottom)
        overlay_layout.addWidget(self.reset_btn, 0, 1, alignment=Qt.AlignRight | Qt.AlignBottom)
        overlay_layout.setColumnStretch(0, 1)
        overlay_layout.setColumnStretch(1, 1)
        layout.addWidget(overlay_panel, 0, 0, alignment=Qt.AlignBottom)
        layout.addWidget(self.overlay, 0, 0, alignment=Qt.AlignCenter)

        self.btn_left.clicked.connect(lambda: self._rotate_view(-10.0, 0.0))
        self.btn_right.clicked.connect(lambda: self._rotate_view(10.0, 0.0))
        self.btn_up.clicked.connect(lambda: self._rotate_view(0.0, 10.0))
        self.btn_down.clicked.connect(lambda: self._rotate_view(0.0, -10.0))

    def set_model_info(self, bounds, model_path, reference):
        self.model_path = model_path or ""
        self.reference = reference or ""
        self._load_token += 1
        token = self._load_token
        if not self.model_path or not os.path.exists(self.model_path):
            self._show_message("3D model not available")
            self._load_web_model("")
            return
        self._show_message("Loading 3D model...")
        preview_path = self._prefer_color_variant(self.model_path)
        self._load_model_async(preview_path, token)

    def _load_model_async(self, path, token):
        ext = Path(path).suffix.lower()
        if ext in (".stp", ".step"):
            gltf_path = self._cached_gltf_path(path)
            if self._is_valid_gltf(gltf_path, path):
                self._load_web_model(gltf_path)
                return
            self._show_message("Converting STEP in background...")
            self._start_step_conversion(path, token)
            return
        self._load_web_model(path)

    def _start_step_conversion(self, src_path, token):
        if self._step_worker and self._step_worker.isRunning():
            self._step_worker.terminate()
        self._step_worker = _StepConvertWorker(self, src_path, token, self)
        self._step_worker.finished.connect(self._on_step_conversion_finished)
        self._step_worker.failed.connect(self._on_step_conversion_failed)
        self._step_worker.start()

    def _on_step_conversion_finished(self, model_path, token):
        if token != self._load_token:
            return
        self._load_web_model(model_path)

    def _on_step_conversion_failed(self, message, src_path, token):
        if token != self._load_token:
            return
        self._show_message(f"3D preview conversion failed: {message}")
        if not self._gmsh_cmd:
            return
        stl_path = self._cached_stl_path(src_path)
        if os.path.exists(stl_path) and os.path.getmtime(stl_path) >= os.path.getmtime(src_path):
            self._load_web_model(stl_path)
            return
        self._show_message("Converting STEP to STL...")
        self._start_conversion(src_path, stl_path, token)

    def _on_web_loaded(self, ok):
        self._viewer_ready = bool(ok)
        if not ok:
            self._show_message("3D preview failed to initialize")
            return
        def _after_ready(ready):
            self._viewer_ready = bool(ready)
            if self._pending_model_url and self._viewer_ready:
                self._run_js_load(self._pending_model_url)
        try:
            self.web_view.page().runJavaScript("window.__viewerReady === true", _after_ready)
        except Exception:
            self._viewer_ready = True
            if self._pending_model_url:
                self._run_js_load(self._pending_model_url)

    def _run_js_load(self, url):
        try:
            payload = json.dumps(url)
            self.web_view.page().runJavaScript(f"window.loadModel({payload});")
            self._await_web_loaded()
        except Exception:
            self._show_message("3D preview failed to load model")

    def _load_web_model(self, path):
        if not path or not os.path.exists(path):
            self._pending_model_url = ""
            if self._viewer_ready:
                self.web_view.page().runJavaScript("window.loadModel('');")
            return
        url = QUrl.fromLocalFile(os.path.abspath(path)).toString()
        self._pending_model_url = url
        if self._viewer_ready:
            self._run_js_load(url)
        else:
            self.web_view.page().runJavaScript("window.__viewerReady === true", lambda ready: self._run_js_load(url) if ready else None)

    def _await_web_loaded(self, attempts=0):
        if attempts > 20:
            return
        def _handle(ok):
            if ok:
                self._show_message("")
                return
            QtCore.QTimer.singleShot(250, lambda: self._await_web_loaded(attempts + 1))
        try:
            self.web_view.page().runJavaScript("window.__lastLoadOk === true", _handle)
        except Exception:
            return

    def _show_message(self, text):
        self.overlay.setText(text)

    def reset_view(self):
        if self._viewer_ready:
            self.web_view.page().runJavaScript("window.resetView();")

    def _rotate_view(self, delta_azimuth, delta_elevation):
        if self._viewer_ready:
            try:
                self.web_view.page().runJavaScript(f"window.rotateView({delta_azimuth}, {delta_elevation});")
            except Exception:
                pass

    def _start_conversion(self, src_path, dst_path, token):
        if self._gmsh_worker and self._gmsh_worker.isRunning():
            self._gmsh_worker.terminate()
        self._gmsh_worker = _ModelConvertWorker(self._gmsh_cmd, src_path, dst_path, token, self)
        self._gmsh_worker.finished.connect(self._on_gmsh_conversion_finished)
        self._gmsh_worker.failed.connect(self._on_gmsh_conversion_failed)
        self._gmsh_worker.start()

    def _on_gmsh_conversion_finished(self, model_path, token):
        if token != self._load_token:
            return
        self._load_web_model(model_path)

    def _on_gmsh_conversion_failed(self, message, token):
        if token != self._load_token:
            return
        self._show_message(f"3D preview error: {message}")

    def _cached_stl_path(self, src_path):
        cache_root = Path("data") / "cache" / "3d_cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        stat = os.stat(src_path)
        key = f"{src_path}:{stat.st_mtime}".encode("utf-8")
        digest = hashlib.sha1(key).hexdigest()[:16]
        return str(cache_root / f"{digest}.stl")

    def _cached_gltf_path(self, src_path):
        cache_root = Path("data") / "cache" / "3d_cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        stat = os.stat(src_path)
        key = f"{src_path}:{stat.st_mtime}".encode("utf-8")
        digest = hashlib.sha1(key).hexdigest()[:16]
        return str(cache_root / f"{digest}.gltf")

    def _is_valid_gltf(self, gltf_path, src_path):
        if not os.path.exists(gltf_path):
            return False
        if os.path.getmtime(gltf_path) < os.path.getmtime(src_path):
            return False
        if os.path.getsize(gltf_path) < 512:
            return False
        bin_path = os.path.splitext(gltf_path)[0] + ".bin"
        if os.path.exists(bin_path) and os.path.getsize(bin_path) == 0:
            return False
        return True

    def _find_gmsh_cmd(self):
        env = os.environ.get("GMSH_CMD", "")
        if env and os.path.exists(env):
            return env
        candidates = [
            r"C:\\Program Files\\FreeCAD 1.0\\bin\\gmsh.exe",
            r"C:\\Program Files\\FreeCAD\\bin\\gmsh.exe",
            r"C:\\Program Files\\Gmsh\\gmsh.exe",
        ]
        for cand in candidates:
            if os.path.exists(cand):
                return cand
        return ""

    def _ensure_ocp(self):
        if self._ocp_checked:
            return self._ocp_available
        self._ocp_checked = True
        try:
            import OCP  # noqa: F401
        except Exception as exc:
            self._ocp_error = str(exc)
            self._ocp_available = False
            return False
        self._ocp_available = True
        self._ocp_error = ""
        return True

    def _get_ocp_python(self):
        if self._ocp_python:
            return self._ocp_python
        env = os.environ.get("OCP_PYTHON", "")
        if env and os.path.exists(env):
            self._ocp_python = env
            return env
        candidates = [
            os.path.join(os.getcwd(), ".venv_ocp", "Scripts", "python.exe"),
            os.path.join(os.getcwd(), "data", "ocp_env", "Scripts", "python.exe"),
        ]
        for cand in candidates:
            if os.path.exists(cand):
                self._ocp_python = cand
                return cand
        return ""

    def _ensure_ocp_script(self):
        script_version = "v4"
        if self._ocp_script_path and os.path.exists(self._ocp_script_path):
            try:
                with open(self._ocp_script_path, "r", encoding="utf-8") as f:
                    first_line = f.readline().strip()
                if script_version in first_line:
                    return self._ocp_script_path
            except Exception:
                pass
        cache_root = Path("data") / "cache" / "3d_cache"
        cache_root.mkdir(parents=True, exist_ok=True)
        script_path = cache_root / "ocp_convert_glb.py"
        script = """# Parts_Checker OCP_GLTF_SCRIPT v4
import sys
import os
from OCP.TDocStd import TDocStd_Document
from OCP.XCAFApp import XCAFApp_Application
from OCP.STEPCAFControl import STEPCAFControl_Reader
from OCP.IFSelect import IFSelect_RetDone
from OCP.RWGltf import RWGltf_CafWriter
from OCP.TCollection import TCollection_ExtendedString, TCollection_AsciiString
from OCP.TColStd import TColStd_IndexedDataMapOfStringString
from OCP.TDF import TDF_LabelSequence
from OCP.XCAFDoc import XCAFDoc_DocumentTool
from OCP.BRepMesh import BRepMesh_IncrementalMesh
try:
    from OCP.Message import Message_ProgressRange
except Exception:
    Message_ProgressRange = None


def main():
    args = [a for a in sys.argv[1:] if a]
    if len(args) < 2:
        print("Usage: ocp_convert_glb.py input.step output.glb")
        return 2
    src, dst = args[0], args[1]
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
    app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
    reader = STEPCAFControl_Reader()
    reader.SetColorMode(True)
    reader.SetLayerMode(True)
    reader.SetNameMode(True)
    status = reader.ReadFile(src)
    if status != IFSelect_RetDone:
        print("STEP read failed")
        return 3
    reader.Transfer(doc)
    shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    labels = TDF_LabelSequence()
    shape_tool.GetFreeShapes(labels)
    if labels.Length() == 0:
        shape_tool.GetShapes(labels)
    for idx in range(1, labels.Length() + 1):
        label = labels.Value(idx)
        shape = shape_tool.GetShape_s(label)
        if shape is None or shape.IsNull():
            continue
        BRepMesh_IncrementalMesh(shape, 0.1, False, 0.5, False)
    is_binary = dst.lower().endswith('.glb')
    writer = RWGltf_CafWriter(TCollection_AsciiString(dst), is_binary)
    if hasattr(writer, "SetToEmbedTextures"):
        writer.SetToEmbedTextures(True)
    if not Message_ProgressRange:
        print("Message_ProgressRange unavailable")
        return 4
    file_info = TColStd_IndexedDataMapOfStringString()
    ok = writer.Perform(doc, file_info, Message_ProgressRange())
    if not ok or not os.path.exists(dst) or os.path.getsize(dst) < 512:
        print("glTF export failed")
        return 4
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
"""
        try:
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script)
        except Exception:
            return ""
        self._ocp_script_path = str(script_path)
        return self._ocp_script_path

    def _convert_step_external(self, python_exe, src_path, dst_path):
        script = self._ensure_ocp_script()
        if not script or not os.path.exists(script):
            self._ocp_error = "OCP helper script missing"
            return False
        try:
            import subprocess
            proc = subprocess.run(
                [python_exe, script, src_path, dst_path],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if proc.returncode != 0 or not os.path.exists(dst_path):
                msg = proc.stderr.strip() or proc.stdout.strip() or "OCP conversion failed"
                self._ocp_error = msg
                return False
            if os.path.getsize(dst_path) < 512:
                self._ocp_error = "OCP conversion produced empty geometry"
                return False
        except Exception as exc:
            self._ocp_error = str(exc)
            return False
        return True

    def _get_freecad_cmd(self):
        if self._freecad_cmd:
            return self._freecad_cmd
        env = os.environ.get("FREECAD_CMD", "")
        if env and os.path.exists(env):
            self._freecad_cmd = env
            return env
        which_cmd = shutil.which("FreeCADCmd")
        if which_cmd and os.path.exists(which_cmd):
            self._freecad_cmd = which_cmd
            return which_cmd
        candidates = [
            r"C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe",
            r"C:\Program Files\FreeCAD\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD 1.0\bin\FreeCADCmd.exe",
            r"C:\Program Files (x86)\FreeCAD\bin\FreeCADCmd.exe",
        ]
        for cand in candidates:
            if os.path.exists(cand):
                self._freecad_cmd = cand
                return cand
        return ""

    def _ensure_freecad_script(self):
        if self._freecad_script_path and os.path.exists(self._freecad_script_path):
            return self._freecad_script_path
        project_root = Path(__file__).resolve().parents[2]
        script_path = project_root / "data" / "cache" / "freecad_export_gltf.py"
        if not script_path.exists():
            return ""
        self._freecad_script_path = str(script_path)
        return self._freecad_script_path

    def _convert_step_freecad(self, freecad_cmd, src_path, dst_path):
        script = self._ensure_freecad_script()
        if not script:
            self._freecad_error = "FreeCAD helper script missing"
            return False
        try:
            import subprocess

            proc = subprocess.run(
                [freecad_cmd, script, src_path, dst_path],
                capture_output=True,
                text=True,
                timeout=180,
            )
            if proc.returncode != 0 or not os.path.exists(dst_path):
                msg = proc.stderr.strip() or proc.stdout.strip() or "FreeCAD conversion failed"
                self._freecad_error = msg
                return False
            if os.path.getsize(dst_path) < 512:
                self._freecad_error = "FreeCAD conversion produced empty geometry"
                return False
        except Exception as exc:
            self._freecad_error = str(exc)
            return False
        return True

    def _convert_step_ocp_to_glb(self, src_path, dst_path):
        try:
            from OCP.TDocStd import TDocStd_Document
            from OCP.XCAFApp import XCAFApp_Application
            from OCP.STEPCAFControl import STEPCAFControl_Reader
            from OCP.IFSelect import IFSelect_RetDone
            from OCP.RWGltf import RWGltf_CafWriter
            from OCP.TCollection import TCollection_ExtendedString, TCollection_AsciiString
            from OCP.TColStd import TColStd_IndexedDataMapOfStringString
            from OCP.TDF import TDF_LabelSequence
            from OCP.XCAFDoc import XCAFDoc_DocumentTool
            from OCP.BRepMesh import BRepMesh_IncrementalMesh
            try:
                from OCP.Message import Message_ProgressRange
            except Exception:
                Message_ProgressRange = None
        except Exception as exc:
            self._ocp_error = str(exc)
            return False

        app = XCAFApp_Application.GetApplication_s()
        doc = TDocStd_Document(TCollection_ExtendedString("MDTV-XCAF"))
        app.NewDocument(TCollection_ExtendedString("MDTV-XCAF"), doc)
        reader = STEPCAFControl_Reader()
        reader.SetColorMode(True)
        reader.SetLayerMode(True)
        reader.SetNameMode(True)
        status = reader.ReadFile(src_path)
        if status != IFSelect_RetDone:
            self._ocp_error = "STEP read failed"
            return False
        reader.Transfer(doc)

        shape_tool = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
        labels = TDF_LabelSequence()
        shape_tool.GetFreeShapes(labels)
        if labels.Length() == 0:
            shape_tool.GetShapes(labels)
        for idx in range(1, labels.Length() + 1):
            label = labels.Value(idx)
            shape = shape_tool.GetShape_s(label)
            if shape is None or shape.IsNull():
                continue
            BRepMesh_IncrementalMesh(shape, 0.1, False, 0.5, False)

        is_binary = dst_path.lower().endswith(".glb")
        writer = RWGltf_CafWriter(TCollection_AsciiString(dst_path), is_binary)
        if hasattr(writer, "SetToEmbedTextures"):
            writer.SetToEmbedTextures(True)
        if not Message_ProgressRange:
            self._ocp_error = "OCP Message_ProgressRange unavailable"
            return False
        file_info = TColStd_IndexedDataMapOfStringString()
        ok = writer.Perform(doc, file_info, Message_ProgressRange())
        if not ok:
            self._ocp_error = "glTF export failed"
            return False
        if not os.path.exists(dst_path):
            return False
        if os.path.getsize(dst_path) < 512:
            self._ocp_error = "glTF export produced empty geometry"
            return False
        return True

    def _prefer_color_variant(self, path):
        base = Path(path)
        if not base.exists():
            return path
        stem = base.stem
        folder = base.parent
        preferred_exts = (".gltf", ".obj", ".wrl", ".vrml", ".glb")
        for ext in preferred_exts:
            cand = folder / f"{stem}{ext}"
            if cand.exists():
                return str(cand)
        if base.suffix.lower() in (".stp", ".step"):
            candidates = []
            for ext in preferred_exts:
                candidates.extend(sorted(folder.glob(f"*{ext}")))
            if len(candidates) == 1:
                return str(candidates[0])
        return path
