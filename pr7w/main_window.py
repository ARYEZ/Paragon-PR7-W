"""The window: Notepad2's menus, toolbar, editor and status bar, all working."""

from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtCore import QFileSystemWatcher, QSettings, QSize, Qt, QTimer
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from PyQt6.QtWidgets import QApplication, QFileDialog, QFontDialog, QLabel, QMainWindow, QStatusBar, QVBoxLayout, QWidget

from . import finish
from . import document, notepad, printing, schemes, textops, theme
from .dialogs import (AboutDialog, CustomizeSchemesDialog, FindReplaceDialog, PageSetupDialog, GoToDialog, NumberDialog, SchemeDialog, SortDialog,
                      TwoFieldDialog, ask_save, message)
from .editor import Editor
from .widgets import Header, Toolbar

APP = "PR7-W"
FILTERS = ("All Files (*.*);;Text Files (*.txt *.log *.md *.ini *.cfg);;"
           "Source Code (*.py *.c *.cpp *.h *.cs *.java *.js *.ts *.go *.rs *.lua *.rb *.pl *.sh *.ps1 *.bat);;"
           "Web (*.html *.htm *.css *.xml *.json *.svg)")


class MainWindow(QMainWindow):
    def __init__(self, path: str | None = None, goto: tuple[int, int] | None = None):
        super().__init__()
        self.settings = QSettings(QSettings.defaultFormat(), QSettings.Scope.UserScope, "Paragon", "PR7-W")
        self.path: str | None = None
        self.encoding = document.BY_KEY[self.settings.value("default_encoding", "utf-8")]
        self.eol = "crlf" if os.name == "nt" else "lf"
        self.scheme = schemes.DEFAULT
        self.scheme_override = False
        self.disk_mtime = 0.0
        self.find_dialog: FindReplaceDialog | None = None
        self.printer: printing.PagePrinter | None = None
        self.watcher = QFileSystemWatcher(self)
        self.watcher.fileChanged.connect(self._disk_changed)

        central = QWidget()
        col = QVBoxLayout(central)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(0)
        self.header = Header()
        col.addWidget(self.header)
        self.toolbar = Toolbar()
        self.toolbar.triggered.connect(self._toolbar)
        col.addWidget(self.toolbar)
        self.editor = Editor()
        self.editor.overrides = self._load_overrides().get(theme.FINISH, {})
        col.addWidget(self.editor, 1)
        self.setCentralWidget(central)
        sb = QStatusBar()
        sb.setSizeGripEnabled(False)
        self.st = {k: QLabel() for k in ("pos", "size", "enc", "eol", "ovr", "scheme")}
        for k, lab in self.st.items():
            sb.addWidget(lab, 1 if k == "pos" else 0)
        self.setStatusBar(sb)

        self.editor.cursorPositionChanged.connect(lambda *_: self._status())
        self.editor.selectionChanged.connect(self._status)
        self.editor.modificationChanged.connect(lambda _: self._title())
        self.editor.textChanged.connect(self._text_changed)
        self.editor.SCN_CHARADDED.connect(self._char_added)
        self.setAcceptDrops(True)
        self._actions: dict[str, QAction] = {}
        self._build_menus()
        self._restore()
        if path:
            self.open_path(path)
        else:
            self._apply_scheme(schemes.DEFAULT)
            self._title()
            self._status()
        if goto:
            self.go_to(*goto)

    # ================================================================ settings
    def _restore(self):
        s = self.settings
        self.resize(s.value("size", QSize(1100, 760)))
        font = s.value("font")
        if font:
            self.editor.base_font = font
        self.editor.setTabWidth(int(s.value("tab_width", 4)))
        self.editor.setIndentationsUseTabs(not s.value("tabs_as_spaces", True, type=bool))
        self.editor.zoomTo(int(s.value("zoom", 0)))
        for key, a in self._actions.items():
            if a.isCheckable() and getattr(a, "_setting", False):
                a.setChecked(s.value("view/" + key, a._default, type=bool))
                a.triggered.emit(a.isChecked())
        if s.value("view/topmost", False, type=bool):
            self._set_topmost(True)

    def _save_settings(self):
        s = self.settings
        s.setValue("size", self.size())
        s.setValue("font", self.editor.base_font)
        s.setValue("tab_width", self.editor.tabWidth())
        s.setValue("tabs_as_spaces", not self.editor.indentationsUseTabs())
        s.setValue("zoom", self.editor.SendScintilla(QsciScintilla.SCI_GETZOOM))
        for key, a in self._actions.items():
            if a.isCheckable() and getattr(a, "_setting", False):
                s.setValue("view/" + key, a.isChecked())

    # ================================================================ files
    def new(self):
        if not self._maybe_save():
            return
        self.editor.setText("")
        self.path = None
        self.encoding = document.BY_KEY[self.settings.value("default_encoding", "utf-8")]
        self.eol = "crlf" if os.name == "nt" else "lf"
        self.editor.setEolMode(self._eol_mode())
        self.scheme_override = False
        self._apply_scheme(schemes.DEFAULT)
        self.editor.setModified(False)
        self._unwatch()
        self._title()
        self._status()

    def open_dialog(self):
        start = str(Path(self.path).parent) if self.path else self.settings.value("last_dir", str(Path.home()))
        path, _ = QFileDialog.getOpenFileName(self, "Open", start, FILTERS)
        if path:
            self.open_path(path)

    def open_path(self, path: str, encoding: document.Encoding | None = None, ask: bool = True) -> bool:
        if ask and not self._maybe_save():
            return False
        p = Path(path)
        if not p.exists():
            if message(self, APP, f"The file \"{p}\" doesn't exist.\nCreate it?", ("Yes", "No")) != 0:
                return False
            p.touch()
        try:
            doc = document.load(p, encoding)
        except OSError as e:
            message(self, APP, f"Couldn't open \"{p}\":\n{e}")
            return False
        self.path = str(p.resolve())
        self.encoding, self.eol = doc.encoding, doc.eol
        self.editor.setEolMode(self._eol_mode())
        self.editor.setText(doc.text)
        self.editor.setModified(False)
        self.editor.SendScintilla(QsciScintilla.SCI_EMPTYUNDOBUFFER)
        self.scheme_override = False
        first = doc.text.split("\n", 1)[0][:200]
        self._apply_scheme(schemes.for_file(self.path, first))
        self.editor.setCursorPosition(0, 0)
        self._watch()
        self._add_recent(self.path)
        self.settings.setValue("last_dir", str(p.parent))
        if document.mixed_eols(doc.text):
            self.statusBar().showMessage("This file has mixed line endings (File > Line Endings converts them).", 6000)
        self._title()
        self._status()
        return True

    def revert(self):
        if self.path and (not self.editor.isModified() or
                          message(self, APP, "Discard your changes and reload the file?", ("Yes", "No")) == 0):
            line, col = self.editor.getCursorPosition()
            self.open_path(self.path, self.encoding, ask=False)
            self.editor.setCursorPosition(min(line, self.editor.lines() - 1), col)

    def save(self) -> bool:
        if not self.path:
            return self.save_as()
        return self._write(self.path)

    def save_as(self, copy: bool = False) -> bool:
        start = self.path or str(Path(self.settings.value("last_dir", str(Path.home()))) / "Untitled.txt")
        path, _ = QFileDialog.getSaveFileName(self, "Save Copy" if copy else "Save As", start, FILTERS)
        if not path:
            return False
        if copy:
            return self._write(path, keep_state=True)
        if not self._write(path):
            return False
        self.path = str(Path(path).resolve())
        if not self.scheme_override:
            self._apply_scheme(schemes.for_file(self.path, self.editor.text(0)))
        self._watch()
        self._add_recent(self.path)
        self._title()
        return True

    def _write(self, path: str, keep_state: bool = False) -> bool:
        text = self.editor.text()
        lost = document.unencodable(text, self.encoding)
        if lost and message(self, APP, f"Some characters can't be saved as {self.encoding.label} "
                            f"({''.join(lost[:12])}...). Save as UTF-8 instead?", ("Yes", "Cancel")) != 0:
            return False
        enc = document.BY_KEY["utf-8"] if lost else self.encoding
        self._unwatch()
        try:
            size = document.save(path, text, enc)
        except OSError as e:
            message(self, APP, f"Couldn't save \"{path}\":\n{e}")
            self._watch()
            return False
        if not keep_state:
            self.encoding = enc
            self.editor.setModified(False)
            self.disk_size = size
        self._watch()
        self._status()
        return True

    def _maybe_save(self) -> bool:
        if not self.editor.isModified():
            return True
        ans = ask_save(self, Path(self.path).name if self.path else "Untitled")
        return ans == "discard" or (ans == "save" and self.save())

    def _watch(self):
        self._unwatch()
        if self.path and self._setting("change_notify", True):
            self.watcher.addPath(self.path)
            self.disk_mtime = os.path.getmtime(self.path)

    def _unwatch(self):
        for f in self.watcher.files():
            self.watcher.removePath(f)

    def _disk_changed(self, path: str):
        if not self.path or not os.path.exists(path):
            return
        mtime = os.path.getmtime(path)
        if mtime == self.disk_mtime:
            return
        self.disk_mtime = mtime
        if path not in self.watcher.files():
            self.watcher.addPath(path)
        if self.settings.value("auto_reload", False, type=bool) and not self.editor.isModified():
            self.revert()
            return
        if message(self, APP, f"The file \"{Path(path).name}\" has been modified by another program.\n"
                   "Reload it?", ("Yes", "No")) == 0:
            line, col = self.editor.getCursorPosition()
            self.open_path(self.path, self.encoding, ask=False)
            self.editor.setCursorPosition(min(line, self.editor.lines() - 1), col)

    def _add_recent(self, path: str):
        if not self._setting("remember_recent", True):
            return
        recent = [p for p in (self.settings.value("recent") or []) if p != path]
        self.settings.setValue("recent", ([path] + recent)[:12])
        self._fill_recent()

    def _fill_recent(self):
        m = self.recent_menu
        m.clear()
        recent = self.settings.value("recent") or []
        for i, p in enumerate(recent):
            a = m.addAction(f"&{(i + 1) % 10}  {p}" if i < 10 else p)
            a.triggered.connect(lambda _=False, p=p: self.open_path(p))
        if recent:
            m.addSeparator()
            m.addAction("Clear list", lambda: (self.settings.setValue("recent", []), self._fill_recent()))
        m.setEnabled(bool(recent))

    def set_encoding(self, enc: document.Encoding):
        """Notepad2: the encoding the file is saved in (the text is kept)."""
        self.encoding = enc
        self.editor.setModified(True)
        self._status()

    def recode(self, enc: document.Encoding):
        """Notepad2's Recode: read the file again as `enc` (for files detected wrongly)."""
        if self.path and (not self.editor.isModified() or
                          message(self, APP, "Reloading discards your changes. Continue?", ("Yes", "No")) == 0):
            self.open_path(self.path, enc, ask=False)

    def set_eol(self, eol: str):
        self.eol = eol
        self.editor.setEolMode(self._eol_mode())
        self.editor.convertEols(self._eol_mode())
        self._status()

    def _eol_mode(self):
        return {"crlf": QsciScintilla.EolMode.EolWindows, "lf": QsciScintilla.EolMode.EolUnix,
                "cr": QsciScintilla.EolMode.EolMac}[self.eol]

    # ================================================================ schemes
    def _apply_scheme(self, scheme: schemes.Scheme):
        self.scheme = scheme
        self.editor.set_lexer(schemes.make_lexer(scheme, self.editor), scheme.name)
        self._status()

    def choose_scheme(self):
        d = SchemeDialog(self, self.scheme.name)
        if d.exec() == SchemeDialog.DialogCode.Accepted:
            self.scheme_override = True
            self._apply_scheme(schemes.BY_NAME[d.chosen()])

    def toggle_default_scheme(self):
        """Shift+F12: between the file's scheme and Default Text."""
        if self.scheme is schemes.DEFAULT:
            self._apply_scheme(schemes.for_file(self.path, self.editor.text(0)))
        else:
            self._apply_scheme(schemes.DEFAULT)

    # ================================================================ editing helpers
    def _line_block(self) -> tuple[int, int, int, int]:
        """The selected whole lines as positions (start, end), and their line numbers. A selection
        that ends at the start of a line doesn't include that line (as Notepad2)."""
        e = self.editor
        if e.hasSelectedText():
            l1, _, l2, i2 = e.getSelection()
            if i2 == 0 and l2 > l1:
                l2 -= 1
        else:
            l1 = l2 = e.getCursorPosition()[0]
        start = e.positionFromLineIndex(l1, 0)
        end = e.positionFromLineIndex(l2 + 1, 0) if l2 + 1 < e.lines() else e.length()
        return start, end, l1, l2

    def _replace_range(self, start: int, end: int, text: str, select: bool = True):
        e = self.editor
        e.beginUndoAction()
        e.SendScintilla(QsciScintilla.SCI_SETTARGETRANGE, start, end)
        raw = text.encode("utf-8")
        e.SendScintilla(QsciScintilla.SCI_REPLACETARGET, len(raw), raw)
        e.endUndoAction()
        if select:
            e.SendScintilla(QsciScintilla.SCI_SETSEL, start, start + len(raw))

    def lines_op(self, f):
        start, end, _, _ = self._line_block()
        old = self.editor.text_range(start, end)
        new = f(old)
        if new != old:
            self._replace_range(start, end, new)

    def selection_op(self, f):
        e = self.editor
        if not e.hasSelectedText():
            return
        start, end = e.selection_positions()
        old = e.selectedText()
        new = f(old)
        if new != old:
            self._replace_range(start, end, new)

    def move_lines(self, down: bool):
        e = self.editor
        e.SendScintilla(QsciScintilla.SCI_MOVESELECTEDLINESDOWN if down else QsciScintilla.SCI_MOVESELECTEDLINESUP)

    def line_comment(self):
        self.lines_op(lambda t: textops.toggle_line_comment(t, self.scheme.line_comment))

    def stream_comment(self):
        if self.scheme.block_comment:
            self.selection_op(lambda t: textops.toggle_stream_comment(t, *self.scheme.block_comment))

    def sort_lines(self):
        d = SortDialog(self)
        if d.exec() == SortDialog.DialogCode.Accepted:
            self.lines_op(lambda t: textops.sort_lines(t, **d.options()))

    def modify_lines(self):
        d = TwoFieldDialog(self, "Modify Lines", "Prefix", "Append",
                           "$(L) inserts the line number, $(0L) the zero-padded line number.")
        if d.exec() == TwoFieldDialog.DialogCode.Accepted:
            self.lines_op(lambda t: textops.modify_lines(t, d.a.text(), d.b.text()))

    def enclose_selection(self):
        d = TwoFieldDialog(self, "Enclose Selection", "Insert before", "Insert after")
        if d.exec() == TwoFieldDialog.DialogCode.Accepted:
            self.selection_op(lambda t: textops.enclose(t, d.a.text(), d.b.text()))

    def insert_tag(self):
        d = TwoFieldDialog(self, "Insert HTML/XML Tag", "Tag", "Attributes (optional)")
        d.a.setText("div")
        if d.exec() == TwoFieldDialog.DialogCode.Accepted and d.a.text().strip():
            tag = d.a.text().strip().strip("<>")
            attrs = (" " + d.b.text().strip()) if d.b.text().strip() else ""
            if self.editor.hasSelectedText():
                self.selection_op(lambda t: f"<{tag}{attrs}>{t}</{tag.split()[0]}>")
            else:
                self.editor.insert(f"<{tag}{attrs}></{tag.split()[0]}>")

    def split_lines(self):
        width = int(self.settings.value("long_line", 80))
        self.lines_op(lambda t: textops.split_lines_at(t, width))

    def insert_text(self, text: str):
        self.editor.removeSelectedText()
        self.editor.insert(text)
        line, col = self.editor.getCursorPosition()
        self.editor.setCursorPosition(line, col + len(text))

    def swap_clipboard(self):
        """Edit > Swap (Ctrl+K): the selection and the clipboard trade places."""
        cb = QApplication.clipboard()
        clip = cb.text()
        sel = self.editor.selectedText()
        self.editor.replaceSelectedText(clip)
        cb.setText(sel)

    def copy_all(self):
        QApplication.clipboard().setText(self.editor.text())

    def _char_added(self, ch: int):
        """Auto Close HTML/XML: typing the '>' of an opening tag adds its closing tag."""
        if ch != ord(">") or not self._setting("auto_close_html", False):
            return
        if self.scheme.name not in ("Web Source Code", "XML Document"):
            return
        e = self.editor
        line, col = e.getCursorPosition()
        before = e.text(line)[:col]
        m = re.search(r"<([A-Za-z][\w:.-]*)(?:\s[^<>]*)?>$", before)
        if m and not before.endswith("/>") and m.group(1).lower() not in (
                "br", "hr", "img", "input", "meta", "link", "area", "base", "col", "embed", "source", "wbr"):
            e.insert(f"</{m.group(1)}>")

    # ================================================================ find / replace / go to
    def show_find(self, replace: bool = False):
        if self.find_dialog is None:
            self.find_dialog = FindReplaceDialog(self, replace)
            self.find_dialog.action.connect(self._find_action)
        self.find_dialog.set_replace_mode(replace)
        if self.editor.hasSelectedText() and "\n" not in self.editor.selectedText():
            self.find_dialog.find.setEditText(self.editor.selectedText())
        self.find_dialog.show()
        self.find_dialog.raise_()
        self.find_dialog.find.setFocus()
        self.find_dialog.find.lineEdit().selectAll()

    def _find_action(self, what: str):
        d = self.find_dialog
        d.status.setText("")
        if what == "next":
            self.find_next(True)
        elif what == "previous":
            self.find_next(False)
        elif what == "replace":
            self.replace_one()
        else:
            n = self.replace_all(in_selection=(what == "replace_in_selection"))
            d.status.setText(f"{n} occurrence(s) replaced." if n else "No occurrences found.")
        if d.close_after.isChecked() and what in ("next", "previous"):
            d.hide()

    def find_next(self, forward: bool = True) -> bool:
        d = self.find_dialog
        if d is None or not d.find.currentText():
            self.show_find()
            return False
        pat = d.pattern()
        if pat is None:
            return False
        e = self.editor
        text = e.text()
        start, end = e.selection_positions()
        cur = e.pos_to_char(end if forward else start)
        m = self._search(pat, text, cur, forward)
        if m is None and not d.no_wrap.isChecked():
            m = self._search(pat, text, 0 if forward else len(text), forward)
            if m is not None:
                self.statusBar().showMessage("Wrapped around.", 2000)
        if m is None:
            d.status.setText(f"\"{d.find.currentText()}\" not found.")
            return False
        a, b = e.char_to_pos(m.start()), e.char_to_pos(m.end())
        e.SendScintilla(QsciScintilla.SCI_SETSEL, a, b)
        e.SendScintilla(QsciScintilla.SCI_SCROLLCARET)
        return True

    @staticmethod
    def _search(pat: re.Pattern, text: str, at: int, forward: bool):
        if forward:
            m = pat.search(text, at)
            if m and m.start() == m.end() == at:  # don't stick on an empty match
                m = pat.search(text, at + 1) if at < len(text) else None
            return m
        last = None
        for m in pat.finditer(text, 0, at):
            if m.end() <= at and not (m.start() == m.end() == at):
                last = m
        return last

    def replace_one(self):
        d = self.find_dialog
        pat = d.pattern()
        if pat is None:
            return
        e = self.editor
        sel = e.selectedText()
        if sel and pat.fullmatch(sel):
            start, end = e.selection_positions()
            new = pat.sub(d.replacement(), sel, count=1)
            self._replace_range(start, end, new, select=False)
            e.SendScintilla(QsciScintilla.SCI_SETSEL, start + len(new.encode("utf-8")),
                            start + len(new.encode("utf-8")))
        self.find_next(True)

    def replace_all(self, in_selection: bool = False) -> int:
        d = self.find_dialog
        pat = d.pattern()
        if pat is None:
            return 0
        e = self.editor
        if in_selection and e.hasSelectedText():
            start, end = e.selection_positions()
        else:
            start, end = 0, e.length()
        old = e.text_range(start, end)
        try:
            new, n = pat.subn(d.replacement(), old)
        except (re.error, IndexError) as ex:
            d.status.setText(f"Replace failed: {ex}")
            return 0
        if n:
            line, col = e.getCursorPosition()
            self._replace_range(start, end, new, select=in_selection)
            if not in_selection:
                e.setCursorPosition(min(line, e.lines() - 1), col)
        return n

    def go_to_dialog(self):
        line, col = self.editor.getCursorPosition()
        d = GoToDialog(self, line + 1, col + 1, self.editor.lines())
        if d.exec() == GoToDialog.DialogCode.Accepted:
            self.go_to(d.line.value(), d.col.value())

    def go_to(self, line: int, col: int = 1):
        e = self.editor
        line = max(1, min(line, e.lines()))
        e.setCursorPosition(line - 1, max(0, col - 1))
        e.ensureLineVisible(line - 1)
        e.SendScintilla(QsciScintilla.SCI_SCROLLCARET)
        e.setFocus()

    # ================================================================ view and settings
    def _set_wrap(self, on: bool):
        self.editor.setWrapMode(QsciScintilla.WrapMode.WrapWord if on else QsciScintilla.WrapMode.WrapNone)
        self.toolbar.keys["wrap"].setChecked(on)

    def _set_long_line(self, on: bool):
        e = self.editor
        if on:
            e.setEdgeMode(QsciScintilla.EdgeMode.EdgeLine)
            e.setEdgeColumn(int(self.settings.value("long_line", 80)))
            from PyQt6.QtGui import QColor
            from . import theme
            e.setEdgeColor(QColor(theme.PANEL_EDGE))
        else:
            e.setEdgeMode(QsciScintilla.EdgeMode.EdgeNone)

    def _set_topmost(self, on: bool):
        self.setWindowFlag(Qt.WindowType.WindowStaysOnTopHint, on)
        self.show()

    def font_dialog(self):
        font, ok = QFontDialog.getFont(self.editor.base_font, self, "Font")
        if ok:
            self.editor.base_font = font
            self.editor.setFont(font)
            self.editor.setMarginsFont(font)
            self._apply_scheme(self.scheme)

    def tab_settings(self):
        d = NumberDialog(self, "Tab Settings", [("Tab width", self.editor.tabWidth(), 1, 32),
                                                ("Indentation size", self.editor.indentationWidth() or
                                                 self.editor.tabWidth(), 0, 32)],
                         ("Insert tabs as spaces", not self.editor.indentationsUseTabs()))
        if d.exec() == NumberDialog.DialogCode.Accepted:
            self.editor.setTabWidth(d.spins[0].value())
            self.editor.setIndentationWidth(d.spins[1].value())
            self.editor.setIndentationsUseTabs(not d.check.isChecked())
            self._actions["tabs_as_spaces"].setChecked(d.check.isChecked())

    def long_line_settings(self):
        d = NumberDialog(self, "Long Line Settings", [("Column", int(self.settings.value("long_line", 80)), 1, 4096)])
        if d.exec() == NumberDialog.DialogCode.Accepted:
            self.settings.setValue("long_line", d.spins[0].value())
            self._set_long_line(self._actions["long_line"].isChecked())

    def change_notification_settings(self):
        i = message(self, "File Change Notification", "When the open file is changed by another program:",
                    ("Ask to reload", "Reload automatically", "Do nothing"),
                    0 if not self.settings.value("auto_reload", False, type=bool) else 1)
        if i >= 0:
            self.settings.setValue("auto_reload", i == 1)
            self._actions["change_notify"].setChecked(i != 2)
            self._watch()

    # ================================================================ finish, schemes, printing, Notepad
    def set_finish(self, name: str):
        """OBSIDIAN (dark) or AURORA (light): the whole window and the editor, at once."""
        theme.set_finish(name)
        finish.set(theme.FINISH)                 # every family app follows (finish.py)
        app = QApplication.instance()
        app.setPalette(theme.palette())
        app.setStyleSheet(theme.stylesheet())
        self.settings.setValue("finish", theme.FINISH)
        self.editor.overrides = self._load_overrides().get(theme.FINISH, {})
        self.editor.apply_colours()
        self._set_long_line(self._actions["long_line"].isChecked())
        for w in (self.header, self.toolbar, *self.toolbar.keys.values()):
            w.update()
        self.finish_actions[theme.FINISH].setChecked(True)

    def _load_overrides(self) -> dict:
        try:
            data = json.loads(self.settings.value("style_overrides", "{}") or "{}")
            return data if isinstance(data, dict) else {}
        except (TypeError, ValueError):
            return {}

    def customize_schemes(self):
        work = dict(self.editor.overrides)

        def apply(overrides):
            self.editor.overrides = overrides
            self.editor.apply_colours()

        d = CustomizeSchemesDialog(self, work, apply, self.scheme.name)
        if d.exec() == CustomizeSchemesDialog.DialogCode.Accepted:
            data = self._load_overrides()
            data[theme.FINISH] = work
            self.settings.setValue("style_overrides", json.dumps(data))

    def _make_printer(self) -> printing.PagePrinter:
        if self.printer is None:
            self.printer = printing.PagePrinter()
            layout = self.settings.value("page_margins_mm")
            if layout:
                from PyQt6.QtCore import QMarginsF
                from PyQt6.QtGui import QPageLayout
                left, top, right, bottom = (float(x) for x in layout)
                self.printer.setPageMargins(QMarginsF(left, top, right, bottom), QPageLayout.Unit.Millimeter)
        self.printer.title = printing.doc_title(self.path)
        self.printer.header = self.settings.value("print_header", True, type=bool)
        return self.printer

    def page_setup(self):
        p = self._make_printer()
        d = PageSetupDialog(self, p, self.settings.value("print_mode", "colour"),
                            int(self.settings.value("print_zoom", 0)), p.header)
        if d.exec() == PageSetupDialog.DialogCode.Accepted:
            self.settings.setValue("print_mode", d.chosen_mode())
            self.settings.setValue("print_zoom", d.zoom.value())
            self.settings.setValue("print_header", d.header.isChecked())
            from PyQt6.QtGui import QPageLayout
            m = p.pageLayout().margins(QPageLayout.Unit.Millimeter)
            self.settings.setValue("page_margins_mm", [m.left(), m.top(), m.right(), m.bottom()])

    def print_document(self, printer=None, dialog: bool = True) -> bool:
        """File > Print (Ctrl+P); also Notepad's /p (no dialog, default printer)."""
        p = printer or self._make_printer()
        if printer is not None:
            p.title = printing.doc_title(self.path)
        lines = None
        if dialog:
            from PyQt6.QtPrintSupport import QAbstractPrintDialog, QPrintDialog, QPrinter
            d = QPrintDialog(p, self)
            d.setOption(QAbstractPrintDialog.PrintDialogOption.PrintSelection, self.editor.hasSelectedText())
            if d.exec() != QPrintDialog.DialogCode.Accepted:
                return False
            if p.printRange() == QPrinter.PrintRange.Selection and self.editor.hasSelectedText():
                _, _, l1, l2 = self._line_block()
                lines = (l1, l2)
        ok = printing.print_editor(self.editor, p, self.settings.value("print_mode", "colour"),
                                   int(self.settings.value("print_zoom", 0)), lines, self.editor.overrides)
        if not ok:
            self.statusBar().showMessage("Printing failed.", 5000)
        return ok

    def replace_notepad(self, on: bool):
        """Settings > Replace Windows Notepad (machine-wide: asks for administrator rights)."""
        action = "--replace-notepad" if on else "--restore-notepad"
        if notepad.is_admin():
            notepad.run(action)
        else:
            code = notepad.run_elevated(action)
            if code == -1:
                self.statusBar().showMessage("Not changed: administrator permission wasn't given.", 6000)
        self.notepad_action.setChecked(notepad.is_replaced())

    def default_editor(self):
        """Register with Windows (if not yet) and open its Default apps page for PR7-W."""
        from . import shell
        shell.register_open_with()
        notepad.open_default_apps()

    def _setting(self, key: str, default: bool) -> bool:
        a = self._actions.get(key)
        return a.isChecked() if a is not None else default

    # ================================================================ title and status bar
    def _title(self):
        name = Path(self.path).name if self.path else "Untitled"
        star = "* " if self.editor.isModified() else ""
        self.setWindowTitle(f"{star}{name} - {APP}")
        self.header.set_right(f"{star}{name}")

    def _text_changed(self):
        self._size_timer = getattr(self, "_size_timer", None) or QTimer(self, singleShot=True,
                                                                         timeout=self._status)
        self._size_timer.start(150)

    def _status(self):
        e = self.editor
        line, col = e.getCursorPosition()
        start, end = e.selection_positions()
        sel = e.SendScintilla(QsciScintilla.SCI_COUNTCHARACTERS, start, end)
        if e.SendScintilla(QsciScintilla.SCI_SELECTIONISRECTANGLE):
            sel = sum(abs(e.SendScintilla(QsciScintilla.SCI_GETSELECTIONNEND, i) -
                          e.SendScintilla(QsciScintilla.SCI_GETSELECTIONNSTART, i))
                      for i in range(e.SendScintilla(QsciScintilla.SCI_GETSELECTIONS)))
        visual_col = e.SendScintilla(QsciScintilla.SCI_GETCOLUMN, e.SendScintilla(QsciScintilla.SCI_GETCURRENTPOS))
        self.st["pos"].setText(f"Ln {line + 1} : {e.lines()}   Col {visual_col + 1}   Sel {sel}")
        self.st["size"].setText(document.fmt_size(self._doc_bytes()))
        self.st["enc"].setText(self.encoding.label)
        self.st["eol"].setText(document.EOLS[self.eol][0])
        self.st["ovr"].setText("OVR" if e.overwriteMode() else "INS")
        self.st["scheme"].setText(self.scheme.name)

    def _doc_bytes(self) -> int:
        n = self.editor.length()  # UTF-8 bytes in Scintilla
        if self.encoding.codec.startswith("utf-16"):
            n = len(self.editor.text().encode("utf-16-le"))
        elif self.encoding.codec not in ("utf-8",):
            n = len(self.editor.text())
        return n + len(self.encoding.bom)

    # ================================================================ drag and drop, closing
    def dragEnterEvent(self, ev):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev):
        urls = [u.toLocalFile() for u in ev.mimeData().urls() if u.isLocalFile()]
        if urls:
            self.open_path(urls[0])

    def closeEvent(self, ev):
        if not self._maybe_save():
            ev.ignore()
            return
        if self._setting("save_on_exit", True):
            self._save_settings()
        ev.accept()

    # ================================================================ toolbar and menus
    def _toolbar(self, name: str):
        {"new": self.new, "open": self.open_dialog, "save": self.save, "undo": self.editor.undo,
         "redo": self.editor.redo, "cut": self.editor.cut, "copy": self.editor.copy, "paste": self.editor.paste,
         "find": lambda: self.show_find(False), "replace": lambda: self.show_find(True),
         "wrap": lambda: self._actions["wrap"].trigger(), "zoomin": self.editor.zoomIn,
         "zoomout": self.editor.zoomOut, "scheme": self.choose_scheme}[name]()

    def _act(self, menu, text, slot=None, shortcut=None, key=None, checkable=False, default=False,
             setting=False) -> QAction:
        a = QAction(text, self)
        if shortcut:
            a.setShortcuts([QKeySequence(s) for s in shortcut.split("|")])
            a.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        a.setCheckable(checkable)
        if checkable:
            a.setChecked(default)
            a._default = default
            a._setting = setting
            if slot:
                a.triggered.connect(lambda on, f=slot: f(on))
        elif slot:
            a.triggered.connect(lambda _=False, f=slot: f())
        menu.addAction(a)
        if key:
            self._actions[key] = a
        return a

    def check_updates(self):
        from . import update_ui
        update_ui.check(self)

    def _build_menus(self):
        bar = self.menuBar()
        e = self.editor
        act = self._act

        m = bar.addMenu("&File")
        act(m, "&New", self.new, "Ctrl+N")
        act(m, "&Open...", self.open_dialog, "Ctrl+O")
        act(m, "Re&vert", self.revert, "F5")
        m.addSeparator()
        act(m, "&Save", self.save, "Ctrl+S")
        act(m, "Save &As...", self.save_as, "F6|Ctrl+Shift+S")
        act(m, "Save &Copy...", lambda: self.save_as(copy=True), "Ctrl+F6")
        m.addSeparator()
        enc = m.addMenu("&Encoding")
        group = QActionGroup(self)
        self.encoding_actions = {}
        for en in document.ENCODINGS:
            a = act(enc, en.label, lambda on, en=en: on and self.set_encoding(en), checkable=True)
            group.addAction(a)
            self.encoding_actions[en.key] = a
        other = enc.addMenu("&Other")
        for en in document.OTHER_ENCODINGS:
            a = act(other, en.label, lambda on, en=en: on and self.set_encoding(en), checkable=True)
            group.addAction(a)
            self.encoding_actions[en.key] = a
        enc.addSeparator()
        rec = enc.addMenu("&Recode (reload as)")
        for en in document.ENCODINGS + document.OTHER_ENCODINGS:
            act(rec, en.label, lambda en=en: self.recode(en))
        enc.aboutToShow.connect(lambda: self.encoding_actions[self.encoding.key].setChecked(True))
        eolm = m.addMenu("Line &Endings")
        eol_group = QActionGroup(self)
        self.eol_actions = {}
        for k, (label, _) in document.EOLS.items():
            a = act(eolm, f"&{label}", lambda on, k=k: on and self.set_eol(k), checkable=True)
            eol_group.addAction(a)
            self.eol_actions[k] = a
        eolm.aboutToShow.connect(lambda: self.eol_actions[self.eol].setChecked(True))
        m.addSeparator()
        act(m, "Page Se&tup...", self.page_setup)
        act(m, "&Print...", self.print_document, "Ctrl+P")
        m.addSeparator()
        self.recent_menu = m.addMenu("Open &Recent")
        self._fill_recent()
        m.addSeparator()
        act(m, "E&xit", self.close, "Alt+F4")

        m = bar.addMenu("&Edit")
        act(m, "&Undo", e.undo, "Ctrl+Z")
        act(m, "&Redo", e.redo, "Ctrl+Y")
        m.addSeparator()
        act(m, "Cu&t", e.cut, "Ctrl+X")
        act(m, "&Copy", e.copy, "Ctrl+C")
        act(m, "Copy &All", self.copy_all, "Alt+C")
        act(m, "&Paste", e.paste, "Ctrl+V")
        act(m, "S&wap", self.swap_clipboard, "Ctrl+K")
        act(m, "Clea&r", e.removeSelectedText)
        m.addSeparator()
        act(m, "Select &All", e.selectAll, "Ctrl+A")
        m.addSeparator()
        lm = m.addMenu("&Lines")
        act(lm, "Move &Up", lambda: self.move_lines(False), "Ctrl+Shift+Up")
        act(lm, "Move &Down", lambda: self.move_lines(True), "Ctrl+Shift+Down")
        act(lm, "D&uplicate Line", lambda: self.lines_op(textops.duplicate_lines), "Ctrl+D")
        act(lm, "Cu&t Line", lambda: e.SendScintilla(QsciScintilla.SCI_LINECUT), "Ctrl+Shift+X")
        act(lm, "&Copy Line", lambda: e.SendScintilla(QsciScintilla.SCI_LINECOPY), "Ctrl+Shift+C")
        act(lm, "D&elete Line", lambda: e.SendScintilla(QsciScintilla.SCI_LINEDELETE), "Ctrl+Shift+D")
        lm.addSeparator()
        act(lm, "&Split Lines", self.split_lines, "Ctrl+I")
        act(lm, "&Join Lines", lambda: self.lines_op(textops.join_lines_text), "Ctrl+J")
        act(lm, "Join &Paragraphs", lambda: self.lines_op(textops.join_paragraphs), "Ctrl+Shift+J")
        lm.addSeparator()
        act(lm, "S&ort Lines...", self.sort_lines, "Alt+O")
        bm = m.addMenu("&Block")
        act(bm, "&Indent", lambda: self.lines_op(lambda t: textops.indent(
            t, " " * e.tabWidth() if not e.indentationsUseTabs() else "\t")))
        act(bm, "&Unindent", lambda: self.lines_op(lambda t: textops.unindent(t, e.tabWidth())))
        bm.addSeparator()
        act(bm, "&Enclose Selection...", self.enclose_selection, "Alt+Q")
        act(bm, "&Duplicate Selection", lambda: self.selection_op(lambda t: t + t), "Alt+D")
        bm.addSeparator()
        act(bm, "&Pad With Spaces", lambda: self.lines_op(textops.pad_with_spaces), "Alt+B")
        act(bm, "Strip &First Character", lambda: self.lines_op(textops.strip_first_char), "Alt+Z")
        act(bm, "Strip &Last Character", lambda: self.lines_op(textops.strip_last_char), "Alt+U")
        act(bm, "Strip &Trailing Blanks", lambda: self.lines_op(textops.strip_trailing_blanks), "Alt+W")
        act(bm, "&Compress Whitespace", lambda: self.lines_op(textops.compress_whitespace), "Alt+P")
        act(bm, "&Merge Blank Lines", lambda: self.lines_op(textops.merge_blank_lines), "Alt+Y")
        act(bm, "&Remove Blank Lines", lambda: self.lines_op(textops.remove_blank_lines), "Alt+R")
        bm.addSeparator()
        act(bm, "M&odify Lines...", self.modify_lines, "Alt+M")
        bm.addSeparator()
        act(bm, "Toggle Line &Comment", self.line_comment, "Ctrl+Q")
        act(bm, "Toggle &Stream Comment", self.stream_comment, "Ctrl+Shift+Q")
        cm = m.addMenu("Con&vert")
        for text, f, sc in (("&Uppercase", textops.upper, "Ctrl+Shift+U"), ("&Lowercase", textops.lower, "Ctrl+U"),
                            ("&Invert Case", textops.invert_case, "Ctrl+Alt+U"),
                            ("&Title Case", textops.title_case, "Ctrl+Alt+I"),
                            ("&Sentence Case", textops.sentence_case, "Ctrl+Alt+O")):
            act(cm, text, lambda f=f: self.selection_op(f), sc)
        cm.addSeparator()
        act(cm, "&Tabify Selection", lambda: self.lines_op(lambda t: textops.tabify(t, e.tabWidth())), "Ctrl+Shift+T")
        act(cm, "&Untabify Selection", lambda: self.lines_op(lambda t: textops.untabify(t, e.tabWidth())),
            "Ctrl+Shift+S")
        cm.addSeparator()
        act(cm, "URL &Encode", lambda: self.selection_op(textops.url_encode), "Ctrl+Shift+E")
        act(cm, "URL &Decode", lambda: self.selection_op(textops.url_decode), "Ctrl+Shift+R")
        act(cm, "Escape &C Chars", lambda: self.selection_op(textops.escape_c), "Ctrl+Alt+E")
        act(cm, "U&nescape C Chars", lambda: self.selection_op(textops.unescape_c), "Ctrl+Alt+R")
        act(cm, "Char to &Hex", lambda: self.selection_op(textops.char_to_hex), "Ctrl+Alt+X")
        act(cm, "Hex to Cha&r", lambda: self.selection_op(textops.hex_to_char), "Ctrl+Alt+C")
        im = m.addMenu("&Insert")
        act(im, "&HTML/XML Tag...", self.insert_tag, "Alt+X")
        act(im, "&Date/Time (Short)", lambda: self.insert_text(datetime.now().strftime("%H:%M %d.%m.%Y")),
            "Ctrl+F5")
        act(im, "Date/Time (&Long)", lambda: self.insert_text(datetime.now().strftime("%H:%M:%S %A, %d %B %Y")),
            "Ctrl+Shift+F5")
        act(im, "&Filename", lambda: self.insert_text(Path(self.path).name if self.path else "Untitled"), "Ctrl+F9")
        act(im, "&Path and Filename", lambda: self.insert_text(self.path or "Untitled"), "Ctrl+Shift+F9")
        act(im, "&GUID", lambda: self.insert_text(str(uuid.uuid4()).upper()), "Ctrl+Shift+.")
        m.addSeparator()
        act(m, "&Find...", lambda: self.show_find(False), "Ctrl+F")
        act(m, "Find &Next", lambda: self.find_next(True), "F3")
        act(m, "Find Pre&vious", lambda: self.find_next(False), "Shift+F3")
        act(m, "R&eplace...", lambda: self.show_find(True), "Ctrl+H")
        act(m, "&Go To...", self.go_to_dialog, "Ctrl+G")
        act(m, "Select to Matching &Brace", lambda: e.selectToMatchingBrace(), "Ctrl+B")

        m = bar.addMenu("&View")
        act(m, "&Syntax Scheme...", self.choose_scheme, "F12")
        act(m, "&Default Text Scheme", self.toggle_default_scheme, "Shift+F12")
        act(m, "&Customize Schemes...", self.customize_schemes, "Ctrl+F12")
        fm = m.addMenu("Fi&nish")
        finish_group = QActionGroup(self)
        self.finish_actions = {}
        for key, label in (("obsidian", "&OBSIDIAN (dark)"), ("aurora", "&AURORA (light)")):
            a = act(fm, label, lambda on, k=key: on and self.set_finish(k), checkable=True)
            a.setChecked(theme.FINISH == key)
            finish_group.addAction(a)
            self.finish_actions[key] = a
        m.addSeparator()
        act(m, "&Font...", self.font_dialog, "Alt+F12")
        m.addSeparator()
        act(m, "&Word Wrap", self._set_wrap, "Ctrl+W", key="wrap", checkable=True, setting=True)
        act(m, "Long Line &Marker", self._set_long_line, "Ctrl+Shift+L", key="long_line", checkable=True,
            setting=True)
        act(m, "Indentation &Guides", e.setIndentationGuides, "Ctrl+Shift+G", key="guides", checkable=True,
            default=True, setting=True)
        act(m, "Show &Whitespace", e.setWhitespaceVisibility_bool, "Ctrl+Shift+8", key="whitespace",
            checkable=True, setting=True)
        act(m, "Show Line &Endings", e.setEolVisibility, "Ctrl+Shift+9", key="eols", checkable=True, setting=True)
        act(m, "Show Wrap S&ymbols", e.set_wrap_symbols, "Ctrl+Shift+0", key="wrap_symbols", checkable=True,
            setting=True)
        m.addSeparator()
        act(m, "Visual &Brace Matching", e.set_brace_matching, "Ctrl+Shift+V", key="braces", checkable=True,
            default=True, setting=True)
        act(m, "Highlight C&urrent Line", e.setCaretLineVisible, "Ctrl+Shift+I", key="current_line", checkable=True,
            default=True, setting=True)
        m.addSeparator()
        act(m, "&Line Numbers", e.show_line_numbers, "Ctrl+Shift+N", key="line_numbers", checkable=True,
            default=True, setting=True)
        act(m, "Selection M&argin", e.show_symbol_margin, "Ctrl+Shift+M", key="margin", checkable=True,
            default=True, setting=True)
        act(m, "Code &Folding", e.show_folding, "Ctrl+Alt+Shift+F", key="folding", checkable=True, default=True,
            setting=True)
        m.addSeparator()
        act(m, "&Toolbar", self.toolbar.setVisible, key="toolbar", checkable=True, default=True, setting=True)
        act(m, "&Header", self.header.setVisible, key="header", checkable=True, default=True, setting=True)
        act(m, "Stat&usbar", lambda on: self.statusBar().setVisible(on), key="statusbar", checkable=True,
            default=True, setting=True)
        m.addSeparator()
        act(m, "Zoom &In", e.zoomIn, "Ctrl++|Ctrl+=")
        act(m, "Zoom &Out", e.zoomOut, "Ctrl+-")
        act(m, "&Reset Zoom", lambda: e.zoomTo(0), "Ctrl+0")

        m = bar.addMenu("&Settings")
        act(m, "Insert Tabs as &Spaces", lambda on: e.setIndentationsUseTabs(not on), key="tabs_as_spaces",
            checkable=True, default=True, setting=True)
        act(m, "&Tab Settings...", self.tab_settings, "Ctrl+T")
        act(m, "&Long Line Settings...", self.long_line_settings)
        m.addSeparator()
        act(m, "&Auto Indent", e.setAutoIndent, key="auto_indent", checkable=True, default=True, setting=True)
        act(m, "Auto Close &HTML/XML", None, key="auto_close_html", checkable=True, setting=True)
        m.addSeparator()
        act(m, "Always On &Top", self._set_topmost, "Alt+T", key="topmost", checkable=True, setting=True)
        act(m, "&Transparent Mode", lambda on: self.setWindowOpacity(0.75 if on else 1.0), "Alt+Shift+T",
            key="transparent", checkable=True, setting=True)
        m.addSeparator()
        act(m, "File &Change Notification", lambda on: self._watch() if on else self._unwatch(), key="change_notify",
            checkable=True, default=True, setting=True)
        act(m, "Change Notification Settings...", self.change_notification_settings, "Alt+F5")
        m.addSeparator()
        act(m, "Remember Recent &Files", None, key="remember_recent", checkable=True, default=True, setting=True)
        act(m, "Save Settings On &Exit", None, key="save_on_exit", checkable=True, default=True, setting=True)
        act(m, "&Save Settings Now", self._save_settings, "F7")
        m.addSeparator()
        self.notepad_action = act(m, "&Replace Windows Notepad", self.replace_notepad, checkable=True)
        self.notepad_action.setEnabled(notepad.available())
        m.aboutToShow.connect(lambda: self.notepad_action.setChecked(notepad.is_replaced()))
        act(m, "Default Te&xt Editor...", self.default_editor).setEnabled(notepad.available())

        m = bar.addMenu("&?")
        act(m, "Check for &Updates...", self.check_updates)
        act(m, "&About PR7-W...", lambda: AboutDialog(self).exec())
