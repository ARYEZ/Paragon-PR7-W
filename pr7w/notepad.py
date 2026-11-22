"""Replacing Windows Notepad (Notepad2's /z), and being Windows' default text editor.

Windows' "debugger" redirect for notepad.exe (Image File Execution Options) makes anything that starts
notepad.exe start PR7-W instead, as `PR7-W.exe /z C:\\Windows\\System32\\notepad.exe <notepad's args>`.
It's machine-wide, so it needs administrator rights: PR7-W re-runs itself elevated (one UAC prompt).
Both registry views are set (32-bit programs read the other one). Only PR7-W's own value is removed.
"""

from __future__ import annotations

import os


IFEO = r"SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\notepad.exe"


def available() -> bool:
    return os.name == "nt"


def debugger_command() -> str:
    from .shell import launcher
    parts = launcher()
    return " ".join(f'"{p}"' if (" " in p or p.lower().endswith(".exe")) else p for p in parts) + " /z"


def _views():
    import winreg
    return (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY)


def current_debugger() -> str:
    """The notepad.exe redirect now set ('' if none)."""
    if not available():
        return ""
    import winreg
    for view in _views():
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, IFEO, 0, winreg.KEY_READ | view)
            v, _ = winreg.QueryValueEx(k, "Debugger")
            winreg.CloseKey(k)
            if v:
                return v
        except OSError:
            pass
    return ""


def is_ours(value: str) -> bool:
    v = value.lower()
    return " /z" in v and ("pr7-w" in v or "-m pr7w" in v)


def is_replaced() -> bool:
    return is_ours(current_debugger())


def replace() -> None:
    """Set the redirect (needs administrator rights; raises PermissionError otherwise)."""
    import winreg
    for view in _views():
        k = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, IFEO, 0, winreg.KEY_SET_VALUE | view)
        winreg.SetValueEx(k, "Debugger", 0, winreg.REG_SZ, debugger_command())
        winreg.CloseKey(k)


def restore() -> None:
    """Remove the redirect, if it's PR7-W's (another program's is left alone)."""
    import winreg
    for view in _views():
        try:
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, IFEO, 0, winreg.KEY_READ | winreg.KEY_SET_VALUE | view)
        except OSError:
            continue
        try:
            v, _ = winreg.QueryValueEx(k, "Debugger")
            if is_ours(v):
                winreg.DeleteValue(k, "Debugger")
        except OSError:
            pass
        finally:
            winreg.CloseKey(k)


def is_admin() -> bool:
    try:
        import ctypes
        return bool(ctypes.windll.shell32.IsUserAnAdmin())
    except Exception:
        return False


def run_elevated(action: str) -> int:
    """Run `PR7-W --replace-notepad` (or --restore-notepad) as administrator and wait. -1 if declined."""
    import ctypes
    from ctypes import wintypes
    from .shell import launcher

    class SHELLEXECUTEINFOW(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.DWORD), ("fMask", wintypes.ULONG), ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR), ("lpFile", wintypes.LPCWSTR), ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR), ("nShow", ctypes.c_int), ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p), ("lpClass", wintypes.LPCWSTR), ("hkeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD), ("hIcon", wintypes.HANDLE), ("hProcess", wintypes.HANDLE)]

    parts = launcher()
    exe = parts[0]
    params = " ".join(parts[1:] + [action])
    info = SHELLEXECUTEINFOW(cbSize=ctypes.sizeof(SHELLEXECUTEINFOW), fMask=0x00000040,  # NOCLOSEPROCESS
                             lpVerb="runas", lpFile=exe, lpParameters=params, nShow=0)
    if not ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(info)) or not info.hProcess:
        return -1  # the user said no at the UAC prompt
    ctypes.windll.kernel32.WaitForSingleObject(info.hProcess, 60_000)
    code = wintypes.DWORD()
    ctypes.windll.kernel32.GetExitCodeProcess(info.hProcess, ctypes.byref(code))
    ctypes.windll.kernel32.CloseHandle(info.hProcess)
    return code.value


def open_default_apps() -> None:
    """Windows' Default apps page for PR7-W (one 'Set default' click takes all its file types)."""
    from PyQt6.QtCore import QUrl
    from PyQt6.QtGui import QDesktopServices
    from .shell import APP_NAME
    QDesktopServices.openUrl(QUrl(f"ms-settings:defaultapps?registeredAppUser={APP_NAME.replace(' ', '%20')}"))


def run(action: str) -> int:
    if not available():
        print("Replacing Notepad is for Windows.")
        return 1
    try:
        (replace if action == "--replace-notepad" else restore)()
        return 0
    except PermissionError:
        print(f"{action} needs administrator rights.")
        return 5


