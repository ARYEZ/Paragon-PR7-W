"""Screenshots of the real app (offscreen): python tools/screenshots.py OUT_DIR"""
import json
import os
import sys
import tempfile
from pathlib import Path

_cfg = Path(tempfile.gettempdir()) / "pr7w_offscreen.json"
_cfg.write_text(json.dumps({"screens": [{"name": "s", "x": 0, "y": 0, "width": 2560, "height": 3200,
                                          "logicalDpi": 96, "logicalBaseDpi": 96, "dpr": 1}]}))
os.environ.setdefault("QT_QPA_PLATFORM", f"offscreen:configfile={_cfg}")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from PyQt6.QtCore import QSettings  # noqa: E402
from PyQt6.QtWidgets import QApplication  # noqa: E402

QSettings.setDefaultFormat(QSettings.Format.IniFormat)  # keep screenshot runs out of the real settings
QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tempfile.mkdtemp())

from pr7w import theme  # noqa: E402
from pr7w.main_window import MainWindow  # noqa: E402

SAMPLE = '''"""Paragon PR7-Z engine: drives the official 7-Zip console (7z.exe)."""

from __future__ import annotations

import re
from dataclasses import dataclass

# Formats 7-Zip can create, in 7-Zip's Add dialog order.
CREATE_FORMATS = ["7z", "tar", "wim", "zip", "gzip", "bzip2", "xz"]
PROGRESS_RE = re.compile(r"^\\s*(\\d{1,3})%(?:\\s+(\\d+))?")


@dataclass
class AddOptions:
    format: str = "7z"
    level: int = 5                 # 0 store ... 9 ultra
    threads: str = ""              # "" = all cores
    password: str = ""


class ProgressParser:
    """Turns 7z's progress output into events."""

    def __init__(self):
        self.total: int | None = None
        self.errors: list[str] = []

    def feed(self, chunk: str) -> list[int]:
        found = []
        for line in chunk.splitlines():
            m = PROGRESS_RE.match(line)
            if m and 0 <= int(m.group(1)) <= 100:
                found.append(int(m.group(1)))
            elif line.startswith("ERROR"):
                self.errors.append(line[7:])
        return found
'''

out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots")
out.mkdir(parents=True, exist_ok=True)
app = QApplication([])
theme.load_fonts()
app.setPalette(theme.palette())
app.setStyleSheet(theme.stylesheet())
sample = Path(tempfile.mkdtemp()) / "engine.py"
sample.write_text(SAMPLE.replace("\n", "\r\n"), encoding="utf-8")
w = MainWindow(str(sample))
w.resize(1280, 800)
w.show()
e = w.editor
e.markerAdd(13, e.bookmark)
e.setSelection(29, 20, 29, 30)
app.processEvents()
w.grab().save(str(out / "main_window.png"))
w.show_find(replace=True)
d = w.find_dialog
d.find.setEditText(r"self\.(\w+)")
d.replace.setEditText(r"self._\1")
d.regex.setChecked(True)
app.processEvents()
d.grab().save(str(out / "replace_dialog.png"))
menu = w.menuBar().actions()[1].menu()
menu.popup(w.mapToGlobal(w.menuBar().geometry().bottomLeft()))
app.processEvents()
menu.grab().save(str(out / "edit_menu.png"))
print("ok")
