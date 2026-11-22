# PyInstaller build of PR7-W: pyinstaller pr7w.spec  ->  dist/PR7-W/PR7-W.exe  (folder build: starts fast)
from pathlib import Path

root = Path(SPECPATH)
a = Analysis(
    [str(root / "tools" / "launcher.py")],
    pathex=[str(root)],
    datas=[(str(root / "pr7w" / "fonts"), "pr7w/fonts"), (str(root / "pr7w" / "icons"), "pr7w/icons")],
    hiddenimports=["PyQt6.Qsci"],
    excludes=["tkinter", "PyQt6.QtWebEngineCore", "PyQt6.QtWebEngineWidgets", "PyQt6.QtQml", "PyQt6.QtQuick",
              "PyQt6.QtMultimedia", "PyQt6.QtPdf", "PyQt6.Qt3DCore"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="PR7-W", console=False,
          icon=str(root / "pr7w" / "icons" / "app.ico"))
coll = COLLECT(exe, a.binaries, a.datas, name="PR7-W")
