"""Windows Explorer: "Edit with PR7-W" on the right-click menu, and PR7-W under "Open with".

Everything is under HKEY_CURRENT_USER (this user only, no admin rights); unregister() removes
exactly what register() wrote. Notepad2's menu entry is one fixed item, so plain registry
verbs do it (no shell extension needed, unlike PR7-Z's).
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from . import schemes

PROGID = "Paragon.PR7W.Text"
APP_NAME = "Paragon PR7-W"                          # its name in Windows' Default apps
CAPABILITIES = r"Software\Paragon\PR7-W\Capabilities"
VERB = "PR7W"
TEXT_EXTS = sorted({e for s in schemes.SCHEMES for e in s.exts if e.isalnum() and len(e) <= 10} |
                   {"txt", "log", "md", "ini", "cfg", "csv", "tsv", "nfo", "srt", "url"})


def available() -> bool:
    return os.name == "nt"


def launcher() -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable]
    py = Path(sys.executable)
    pyw = py.with_name("pythonw.exe")
    return [str(pyw if pyw.exists() else py), "-m", "pr7w"]


def command() -> str:
    return " ".join(f'"{p}"' if (" " in p or p.lower().endswith(".exe")) else p for p in launcher()) + ' "%1"'


def icon() -> str:
    return f"{sys.executable},0" if getattr(sys, "frozen", False) else str(Path(__file__).parent / "icons" / "app.ico")


def _set(path: str, values: dict):
    import winreg
    k = winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_WRITE)
    for name, val in values.items():
        winreg.SetValueEx(k, name, 0, winreg.REG_NONE if val is None else winreg.REG_SZ,
                          b"" if val is None else val)
    winreg.CloseKey(k)


def _delete_tree(path: str):
    import winreg
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, path, 0, winreg.KEY_ALL_ACCESS)
    except FileNotFoundError:
        return
    while True:
        try:
            sub = winreg.EnumKey(k, 0)
        except OSError:
            break
        _delete_tree(f"{path}\\{sub}")
    winreg.CloseKey(k)
    winreg.DeleteKey(winreg.HKEY_CURRENT_USER, path)


def register_menu():
    _set(rf"Software\Classes\*\shell\{VERB}", {"": "Edit with PR7-W", "MUIVerb": "Edit with PR7-W", "Icon": icon()})
    _set(rf"Software\Classes\*\shell\{VERB}\command", {"": command()})
    _notify()


def unregister_menu():
    _delete_tree(rf"Software\Classes\*\shell\{VERB}")
    _notify()


def register_open_with():
    _set(rf"Software\Classes\{PROGID}", {"": "Text Document (PR7-W)"})
    _set(rf"Software\Classes\{PROGID}\DefaultIcon", {"": icon()})
    _set(rf"Software\Classes\{PROGID}\shell\open\command", {"": command()})
    for ext in TEXT_EXTS:
        _set(rf"Software\Classes\.{ext}\OpenWithProgids", {PROGID: None})
    # Registered with Windows as a text editor, so Settings > Default apps lists it with all its types.
    _set(CAPABILITIES, {"ApplicationName": APP_NAME, "ApplicationDescription": "Text editor (works like Notepad2)",
                        "ApplicationIcon": icon()})
    _set(CAPABILITIES + r"\FileAssociations", {f".{ext}": PROGID for ext in TEXT_EXTS})
    _set(r"Software\RegisteredApplications", {APP_NAME: CAPABILITIES})
    _notify()


def unregister_open_with():
    import winreg
    for ext in TEXT_EXTS:
        try:
            k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\.{ext}\OpenWithProgids", 0,
                               winreg.KEY_SET_VALUE)
            winreg.DeleteValue(k, PROGID)
            winreg.CloseKey(k)
        except OSError:
            pass
    _delete_tree(rf"Software\Classes\{PROGID}")
    _delete_tree(CAPABILITIES)
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\RegisteredApplications", 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(k, APP_NAME)
        winreg.CloseKey(k)
    except OSError:
        pass
    _notify()


def menu_registered() -> bool:
    if not available():
        return False
    import winreg
    try:
        winreg.CloseKey(winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\*\shell\{VERB}"))
        return True
    except OSError:
        return False


def _notify():
    try:
        import ctypes
        ctypes.windll.shell32.SHChangeNotify(0x08000000, 0, None, None)  # SHCNE_ASSOCCHANGED
    except Exception:
        pass


def run(action: str) -> int:
    """The installer's and the command line's --register... switches."""
    if action in ("--replace-notepad", "--restore-notepad"):
        from . import notepad
        return notepad.run(action)
    if not available():
        print("Explorer integration is for Windows.")
        return 1
    steps = {"--register": [register_menu, register_open_with], "--unregister": [unregister_menu, unregister_open_with],
             "--register-menu": [register_menu], "--unregister-menu": [unregister_menu],
             "--register-open-with": [register_open_with], "--unregister-open-with": [unregister_open_with]}[action]
    try:
        for s in steps:
            s()
    except OSError as e:
        print(f"{action} failed: {e}")
        return 2
    return 0
