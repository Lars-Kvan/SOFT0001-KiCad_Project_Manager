import os
import subprocess


def hidden_console_kwargs():
    """Return subprocess keyword args that hide the console window on Windows."""
    kwargs = {}
    if os.name != "nt":
        return kwargs

    creation_flags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    if creation_flags:
        kwargs["creationflags"] = creation_flags

    if hasattr(subprocess, "STARTUPINFO"):
        startup_info = subprocess.STARTUPINFO()
        startup_info.dwFlags |= getattr(subprocess, "STARTF_USESHOWWINDOW", 0)
        startup_info.wShowWindow = getattr(subprocess, "SW_HIDE", 0)
        kwargs["startupinfo"] = startup_info

    return kwargs
