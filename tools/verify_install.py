"""Check a real install of PR7-W-Setup.exe (CI, Windows): python tools/verify_install.py installed|uninstalled"""
import os
import sys
import time
import winreg
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pr7w import shell  # noqa: E402

HKCU = winreg.HKEY_CURRENT_USER
APP = Path(os.environ["LOCALAPPDATA"]) / "Programs" / "PR7-W"
SHORTCUT = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Paragon PR7-W.lnk"
UNINSTALL = r"Software\Microsoft\Windows\CurrentVersion\Uninstall\{D8F51204-6E9E-4CB7-BF2E-58F4908B7937}_is1"


def value(path, name=""):
    try:
        k = winreg.OpenKey(HKCU, path)
    except OSError:
        return None
    try:
        return winreg.QueryValueEx(k, name)[0]
    except OSError:
        return None
    finally:
        winreg.CloseKey(k)


def has_value(path, name):
    """Open with entries are empty REG_NONE values (read as None), so test for existence."""
    try:
        k = winreg.OpenKey(HKCU, path)
    except OSError:
        return False
    try:
        winreg.QueryValueEx(k, name)
        return True
    except OSError:
        return False
    finally:
        winreg.CloseKey(k)


def check(ok, what, p):
    print(("ok    " if ok else "FAIL  ") + what)
    if not ok:
        p.append(what)


def installed():
    p = []
    exe = APP / "PR7-W.exe"
    for f in (exe, APP / "unins000.exe", APP / "_internal" / "pr7w" / "fonts" / "Inter-Regular.ttf"):
        check(f.is_file(), f"file {f}", p)
    check(SHORTCUT.is_file(), "Start menu shortcut", p)
    check(value(UNINSTALL, "DisplayName") == "Paragon PR7-W", "Installed apps entry", p)
    check(value(rf"Software\Classes\*\shell\{shell.VERB}", "MUIVerb") == "Edit with PR7-W", '"Edit with PR7-W" menu', p)
    cmd = value(rf"Software\Classes\*\shell\{shell.VERB}\command") or ""
    check(cmd.lower() == f'"{exe}" "%1"'.lower(), f"the menu runs the installed PR7-W ({cmd})", p)
    check(has_value(r"Software\Classes\.py\OpenWithProgids", shell.PROGID), '"Open with" for .py', p)
    check(has_value(r"Software\Classes\.txt\OpenWithProgids", shell.PROGID), '"Open with" for .txt', p)
    return p


def uninstalled():
    deadline = time.time() + 60
    while True:
        p = []
        check(not (APP / "PR7-W.exe").exists(), "program files removed", p)
        check(not SHORTCUT.exists(), "Start menu shortcut removed", p)
        check(value(UNINSTALL, "DisplayName") is None, "Installed apps entry removed", p)
        check(value(rf"Software\Classes\*\shell\{shell.VERB}", "MUIVerb") is None, "menu removed", p)
        check(not has_value(r"Software\Classes\.txt\OpenWithProgids", shell.PROGID), '"Open with" removed', p)
        if not p or time.time() > deadline:
            return p
        print("... waiting for the uninstaller to finish")
        time.sleep(3)


if __name__ == "__main__":
    problems = {"installed": installed, "uninstalled": uninstalled}[sys.argv[1]]()
    print("\nALL OK" if not problems else f"\n{len(problems)} problem(s)")
    sys.exit(1 if problems else 0)
