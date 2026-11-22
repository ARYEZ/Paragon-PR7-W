"""The window, laid out like Notepad2: menus, toolbar, editor, status bar. (Mock-up stage.)"""

from __future__ import annotations

from PyQt6.Qsci import QsciLexerPython
from PyQt6.QtGui import QAction, QKeySequence
from PyQt6.QtWidgets import QLabel, QMainWindow, QStatusBar, QVBoxLayout, QWidget

from .editor import Editor
from .widgets import Header, Toolbar

MENUS = {
    "&File": ["&New\tCtrl+N", "&Open...\tCtrl+O", "Re&vert\tF5", "-", "&Save\tCtrl+S", "Save &As...\tF6",
              "Save &Copy...\tCtrl+F6", "-", "&Encoding", "Line &Endings", "-", "Page Se&tup...", "&Print...\tCtrl+P",
              "-", "P&roperties...", "Create &Desktop Link", "-", "&Open Recent\tAlt+H", "-", "E&xit\tAlt+F4"],
    "&Edit": ["&Undo\tCtrl+Z", "&Redo\tCtrl+Y", "-", "Cu&t\tCtrl+X", "&Copy\tCtrl+C", "Copy &All\tAlt+C",
              "&Paste\tCtrl+V", "S&wap\tCtrl+K", "Clea&r\tDel", "-", "Select &All\tCtrl+A", "-", "&Lines",
              "&Block", "Con&vert", "&Insert", "Spec&ial", "-", "&Find...\tCtrl+F", "Find &Next\tF3",
              "Find Pre&vious\tShift+F3", "R&eplace...\tCtrl+H", "&Go To...\tCtrl+G"],
    "&View": ["&Syntax Scheme...\tF12", "&2nd Default Scheme\tShift+F12", "&Customize Schemes...\tCtrl+F12",
              "-", "&Font...\tAlt+F12", "-", "&Word Wrap\tCtrl+W", "Long Line &Marker\tCtrl+Shift+L",
              "Indentation &Guides\tCtrl+Shift+G", "Show &Whitespace\tCtrl+Shift+8",
              "Show Line &Endings\tCtrl+Shift+9", "Show Wrap S&ymbols\tCtrl+Shift+0", "-",
              "Visual &Brace Matching\tCtrl+Shift+V", "Highlight C&urrent Line\tCtrl+Shift+I", "-",
              "&Line Numbers\tCtrl+Shift+N", "Selection M&argin\tCtrl+Shift+M", "Code &Folding\tCtrl+Shift+Alt+F",
              "-", "&Toolbar", "Stat&usbar", "-", "Zoom &In\tCtrl++", "Zoom &Out\tCtrl+-",
              "&Reset Zoom\tCtrl+0"],
    "&Settings": ["Insert Tabs as &Spaces", "&Tab Settings...\tCtrl+T", "Word Wrap Setti&ngs...",
                  "&Long Line Settings...", "-", "&Auto Indent", "Auto Close &HTML/XML", "-",
                  "Always On &Top\tAlt+T", "Minimi&ze To Tray", "&Transparent Mode\tAlt+Shift+T", "-",
                  "File &Change Notification...\tAlt+F5", "-", "Remember Recent &Files", "Save Settings On &Exit",
                  "&Save Settings Now\tF7"],
    "&?": ["&About PR7-W..."],
}

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


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("engine.py - PR7-W")
        self.resize(1280, 800)
        self._menus()
        central = QWidget()
        col = QVBoxLayout(central)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.header = Header()
        self.header.set_right("engine.py")  # a file name keeps its case
        col.addWidget(self.header)
        self.toolbar = Toolbar()
        col.addWidget(self.toolbar)
        self.editor = Editor()
        self.editor.set_lexer(QsciLexerPython(self.editor))
        self.editor.setText(SAMPLE)
        col.addWidget(self.editor, 1)
        self.setCentralWidget(central)
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.status = []
        for i, text in enumerate(["Ln 26 : 37   Col 13   Sel 0", "1.08 KB", "UTF-8", "CR+LF", "INS", "Python"]):
            lab = QLabel(text)
            sb.addWidget(lab, 1 if i == 0 else 0)
            self.status.append(lab)
        self.setStatusBar(sb)

    def _menus(self):
        bar = self.menuBar()
        for title, items in MENUS.items():
            m = bar.addMenu(title)
            for it in items:
                if it == "-":
                    m.addSeparator()
                    continue
                text, _, sc = it.partition("\t")
                a = QAction(text, self)
                if sc:
                    a.setShortcut(QKeySequence(sc))
                if text in ("&Word Wrap", "Indentation &Guides", "Visual &Brace Matching", "Highlight C&urrent Line",
                            "&Line Numbers", "Selection M&argin", "Code &Folding", "&Toolbar", "Stat&usbar",
                            "Insert Tabs as &Spaces", "&Auto Indent", "Remember Recent &Files",
                            "Save Settings On &Exit"):
                    a.setCheckable(True)
                    a.setChecked(text != "&Word Wrap")
                m.addAction(a)
