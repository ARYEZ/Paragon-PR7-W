"""Screenshots (offscreen): python tools/screenshots.py OUT_DIR"""
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

from PyQt6.QtWidgets import QApplication  # noqa: E402

from pr7w import theme  # noqa: E402
from pr7w.main_window import MainWindow  # noqa: E402

out = Path(sys.argv[1] if len(sys.argv) > 1 else "docs/screenshots")
out.mkdir(parents=True, exist_ok=True)
app = QApplication([])
theme.load_fonts()
app.setPalette(theme.palette())
app.setStyleSheet(theme.stylesheet())
w = MainWindow()
w.show()
e = w.editor
e.setCursorPosition(25, 12)
e.setSelection(28, 22, 28, 31)          # 'splitlines' selected, to show the selection colour
e.markerAdd(13, e.bookmark)             # a bookmark in the margin
app.processEvents()
w.grab().save(str(out / "main_window.png"))
menu = w.menuBar().actions()[2].menu()
menu.popup(w.mapToGlobal(w.menuBar().geometry().bottomLeft()))
app.processEvents()
menu.setActiveAction(menu.actions()[6])
app.processEvents()
menu.grab().save(str(out / "view_menu.png"))
print("ok")
