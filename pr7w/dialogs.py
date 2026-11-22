"""PR7-W's dialogs, matching Notepad2's, in the Paragon look."""

from __future__ import annotations

import re

from PyQt6.QtCore import pyqtSignal
from PyQt6.QtWidgets import (QCheckBox, QComboBox, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                             QListWidget, QPushButton, QRadioButton, QSpinBox, QVBoxLayout, QWidget)

from . import __version__, schemes
from .widgets import Header


def field_label(text: str) -> QLabel:
    lab = QLabel(text.upper())
    lab.setProperty("role", "field")
    return lab


class ParagonDialog(QDialog):
    def __init__(self, title: str, subtitle: str, parent=None, width: int = 520):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setMinimumWidth(width)
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 16)
        root.setSpacing(0)
        root.addWidget(Header(subtitle.upper()))
        body = QWidget()
        self.body = QVBoxLayout(body)
        self.body.setContentsMargins(20, 10, 20, 0)
        self.body.setSpacing(8)
        root.addWidget(body, 1)
        self.buttons = QHBoxLayout()
        self.buttons.setContentsMargins(20, 14, 20, 0)
        self.buttons.addStretch(1)
        root.addLayout(self.buttons)

    def add_button(self, text: str, slot=None, default: bool = False) -> QPushButton:
        b = QPushButton(text)
        b.setMinimumWidth(96)
        b.setDefault(default)
        b.setAutoDefault(default)
        if slot:
            b.clicked.connect(slot)
        self.buttons.addWidget(b)
        return b


def message(parent, title: str, text: str, buttons=("OK",), default: int = 0) -> int:
    d = ParagonDialog(title, title, parent, 440)
    lab = QLabel(text)
    lab.setWordWrap(True)
    d.body.addWidget(lab)
    chosen = {"i": -1}
    for i, b in enumerate(buttons):
        d.add_button(b, lambda _=False, i=i: (chosen.__setitem__("i", i), d.accept()), default=(i == default))
    d.exec()
    return chosen["i"]


def ask_save(parent, name: str) -> str:
    """Notepad2's question on closing a changed file: 'save', 'discard' or 'cancel'."""
    i = message(parent, "PR7-W", f"Save changes to \"{name}\"?", ("Yes", "No", "Cancel"), 0)
    return {0: "save", 1: "discard"}.get(i, "cancel")


# ----------------------------------------------------------------------------- find / replace
class FindReplaceDialog(ParagonDialog):
    """Notepad2's Find / Replace: modeless; emits what to do, the window does it on the editor."""

    action = pyqtSignal(str)  # next | previous | replace | replace_all | replace_in_selection

    def __init__(self, parent=None, replace: bool = False):
        super().__init__("Replace Text" if replace else "Find Text", "REPLACE" if replace else "FIND", parent, 560)
        self.setModal(False)
        self.body.addWidget(field_label("Find what"))
        self.find = QComboBox()
        self.find.setEditable(True)
        self.find.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.body.addWidget(self.find)
        self.replace_label = field_label("Replace with")
        self.replace = QComboBox()
        self.replace.setEditable(True)
        self.replace.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.body.addWidget(self.replace_label)
        self.body.addWidget(self.replace)
        opts = QGroupBox("OPTIONS")
        g = QGridLayout(opts)
        self.match_case = QCheckBox("Match case")
        self.whole_word = QCheckBox("Match whole word only")
        self.regex = QCheckBox("Regular expression search")
        self.backslash = QCheckBox("Transform backslashes")
        self.no_wrap = QCheckBox("Don't wrap around")
        self.close_after = QCheckBox("Close after find")
        for i, c in enumerate((self.match_case, self.whole_word, self.regex, self.backslash, self.no_wrap,
                               self.close_after)):
            g.addWidget(c, i % 3, i // 3)
        self.regex.toggled.connect(lambda on: self.backslash.setEnabled(not on))
        self.body.addWidget(opts)
        self.status = QLabel("")
        self.status.setProperty("role", "dim")
        self.body.addWidget(self.status)
        self.add_button("Find Next", lambda: self._emit("next"), default=True)
        self.add_button("Find Previous", lambda: self._emit("previous"))
        self.b_replace = self.add_button("Replace", lambda: self._emit("replace"))
        self.b_all = self.add_button("Replace All", lambda: self._emit("replace_all"))
        self.b_sel = self.add_button("In Selection", lambda: self._emit("replace_in_selection"))
        self.add_button("Close", self.hide)
        self.set_replace_mode(replace)

    def set_replace_mode(self, on: bool):
        self.replace_mode = on
        for w in (self.replace_label, self.replace, self.b_replace, self.b_all, self.b_sel):
            w.setVisible(on)
        self.setWindowTitle("Replace Text" if on else "Find Text")

    def _remember(self, combo: QComboBox):
        t = combo.currentText()
        if t:
            i = combo.findText(t)
            if i >= 0:
                combo.removeItem(i)
            combo.insertItem(0, t)
            combo.setCurrentIndex(0)

    def _emit(self, what: str):
        self._remember(self.find)
        if self.replace_mode:
            self._remember(self.replace)
        self.action.emit(what)

    def pattern(self) -> re.Pattern | None:
        """The search as a compiled regex (plain text is escaped), or None if it's invalid."""
        text = self.find.currentText()
        if not text:
            return None
        flags = 0 if self.match_case.isChecked() else re.IGNORECASE
        if self.regex.isChecked():
            pat = text
        else:
            if self.backslash.isChecked():
                text = transform_backslashes(text)
            pat = re.escape(text)
        if self.whole_word.isChecked():
            pat = rf"\b(?:{pat})\b"
        try:
            return re.compile(pat, flags | re.MULTILINE)
        except re.error as e:
            self.status.setText(f"Invalid regular expression: {e}")
            return None

    def replacement(self) -> str:
        r = self.replace.currentText()
        if self.regex.isChecked():
            return r  # \1, \g<name>, \n, \t: Python's re handles them
        return transform_backslashes(r) if self.backslash.isChecked() else r


def transform_backslashes(s: str) -> str:
    return re.sub(r"\\([nrt0\\])", lambda m: {"n": "\n", "r": "\r", "t": "\t", "0": "\0", "\\": "\\"}[m.group(1)], s)


# ----------------------------------------------------------------------------- small dialogs
class GoToDialog(ParagonDialog):
    def __init__(self, parent, line: int, col: int, lines: int):
        super().__init__("Go To", "GO TO", parent, 360)
        g = QGridLayout()
        self.line = QSpinBox()
        self.line.setRange(1, max(1, lines))
        self.line.setValue(line)
        self.col = QSpinBox()
        self.col.setRange(1, 1_000_000)
        self.col.setValue(col)
        g.addWidget(field_label("Line"), 0, 0)
        g.addWidget(self.line, 0, 1)
        g.addWidget(field_label("Column"), 1, 0)
        g.addWidget(self.col, 1, 1)
        self.body.addLayout(g)
        self.add_button("OK", self.accept, default=True)
        self.add_button("Cancel", self.reject)
        self.line.selectAll()
        self.line.setFocus()


class SchemeDialog(ParagonDialog):
    def __init__(self, parent, current: str):
        super().__init__("Select Scheme", "SYNTAX SCHEME", parent, 420)
        self.list = QListWidget()
        for s in schemes.SCHEMES:
            self.list.addItem(s.name)
        names = [s.name for s in schemes.SCHEMES]
        self.list.setCurrentRow(names.index(current) if current in names else 0)
        self.list.itemDoubleClicked.connect(lambda _: self.accept())
        self.list.setMinimumHeight(380)
        self.body.addWidget(self.list)
        self.add_button("OK", self.accept, default=True)
        self.add_button("Cancel", self.reject)

    def chosen(self) -> str:
        return self.list.currentItem().text()


class SortDialog(ParagonDialog):
    def __init__(self, parent):
        super().__init__("Sort Lines", "SORT LINES", parent, 380)
        self.asc = QRadioButton("Sort ascending")
        self.desc = QRadioButton("Sort descending")
        self.shuffle = QRadioButton("Shuffle lines")
        self.asc.setChecked(True)
        for w in (self.asc, self.desc, self.shuffle):
            self.body.addWidget(w)
        self.dups = QCheckBox("Remove duplicate lines")
        self.uniq = QCheckBox("Remove unique lines")
        self.case = QCheckBox("Case sensitive")
        self.logical = QCheckBox("Logical number comparison")
        self.logical.setChecked(True)
        for w in (self.dups, self.uniq, self.case, self.logical):
            self.body.addWidget(w)
        self.add_button("OK", self.accept, default=True)
        self.add_button("Cancel", self.reject)

    def options(self) -> dict:
        return dict(descending=self.desc.isChecked(), shuffle=self.shuffle.isChecked(),
                    remove_duplicates=self.dups.isChecked(), remove_unique=self.uniq.isChecked(),
                    ignore_case=not self.case.isChecked(), logical=self.logical.isChecked())


class TwoFieldDialog(ParagonDialog):
    """Modify Lines (prefix / suffix) and Enclose Selection (before / after)."""

    def __init__(self, parent, title: str, first: str, second: str, note: str = ""):
        super().__init__(title, title.upper(), parent, 440)
        self.a, self.b = QLineEdit(), QLineEdit()
        for label, w in ((first, self.a), (second, self.b)):
            self.body.addWidget(field_label(label))
            self.body.addWidget(w)
        if note:
            n = QLabel(note)
            n.setProperty("role", "dim")
            n.setWordWrap(True)
            self.body.addWidget(n)
        self.add_button("OK", self.accept, default=True)
        self.add_button("Cancel", self.reject)


class NumberDialog(ParagonDialog):
    """Tab settings, long-line limit, split width: one or two numbers and a checkbox."""

    def __init__(self, parent, title: str, fields: list[tuple[str, int, int, int]], check: tuple[str, bool] | None = None):
        super().__init__(title, title.upper(), parent, 380)
        g = QGridLayout()
        self.spins = []
        for r, (label, value, lo, hi) in enumerate(fields):
            s = QSpinBox()
            s.setRange(lo, hi)
            s.setValue(value)
            g.addWidget(field_label(label), r, 0)
            g.addWidget(s, r, 1)
            self.spins.append(s)
        self.body.addLayout(g)
        self.check = None
        if check:
            self.check = QCheckBox(check[0])
            self.check.setChecked(check[1])
            self.body.addWidget(self.check)
        self.add_button("OK", self.accept, default=True)
        self.add_button("Cancel", self.reject)


class AboutDialog(ParagonDialog):
    def __init__(self, parent=None):
        super().__init__("About PR7-W", "ABOUT", parent, 480)
        for text, role in ((f"Paragon PR7-W {__version__}", "heading"),
                           ("The Paragon family's text editor, working the way Notepad2 works.", ""),
                           ("Editing engine: Scintilla (QScintilla, Riverbank Computing) under PyQt6.", "dim"),
                           ("Fonts: Inter (SIL Open Font License 1.1).", "dim")):
            lab = QLabel(text)
            lab.setWordWrap(True)
            if role:
                lab.setProperty("role", role)
            self.body.addWidget(lab)
        self.add_button("OK", self.accept, default=True)


