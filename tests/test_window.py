"""The window, driven the way it's used: open, edit, save, find, replace, line tools, encodings."""

import codecs
import os

import pytest
from PyQt6.Qsci import QsciScintilla

from pr7w import document, main_window, textops


@pytest.fixture()
def win(qapp, monkeypatch):
    monkeypatch.setattr(main_window, "message", lambda *a, **k: 0)   # dialogs answer "yes"/first button
    w = main_window.MainWindow()
    yield w
    w.editor.setModified(False)
    w.close()


def act(w, text):
    """Trigger a menu action by its text (ampersands ignored)."""
    for a in w.findChildren(main_window.QAction):
        if a.text().replace("&", "") == text:
            a.trigger()
            return a
    raise KeyError(text)


def test_open_edit_save_round_trip(win, tmp_path):
    p = tmp_path / "notes.txt"
    p.write_bytes(codecs.BOM_UTF8 + "café\r\nline two\r\n".encode("utf-8"))
    assert win.open_path(str(p))
    assert win.st["enc"].text() == "UTF-8 with Signature" and win.st["eol"].text() == "CR+LF"
    assert win.windowTitle() == "notes.txt - PR7-W"
    win.editor.setCursorPosition(1, 0)
    win.editor.insert("new ")
    assert win.windowTitle().startswith("* ")
    assert win.save()
    assert p.read_bytes() == codecs.BOM_UTF8 + "café\r\nnew line two\r\n".encode("utf-8")
    assert win.windowTitle() == "notes.txt - PR7-W"


def test_new_line_uses_the_files_line_ending(win, tmp_path):
    p = tmp_path / "unix.sh"
    p.write_bytes(b"#!/bin/sh\necho hi\n")
    win.open_path(str(p))
    assert win.scheme.name == "Shell Script" and win.st["eol"].text() == "LF"
    win.editor.setCursorPosition(1, 7)
    win.editor.SendScintilla(QsciScintilla.SCI_NEWLINE)
    win.save()
    assert b"\r" not in p.read_bytes()


def test_close_asks_to_save(win, tmp_path, monkeypatch):
    p = tmp_path / "a.txt"
    p.write_text("x")
    win.open_path(str(p))
    win.editor.insert("changed ")
    monkeypatch.setattr(main_window, "ask_save", lambda *a: "cancel")
    assert not win.close()                       # cancelled: the window stays
    monkeypatch.setattr(main_window, "ask_save", lambda *a: "save")
    assert win.close()
    assert p.read_text() == "changed x"


def find(win, text, regex=False, case=False, word=False, replace=None):
    win.show_find(replace is not None)
    d = win.find_dialog
    d.find.setEditText(text)
    d.regex.setChecked(regex)
    d.match_case.setChecked(case)
    d.whole_word.setChecked(word)
    if replace is not None:
        d.replace.setEditText(replace)
    return d


def test_find_next_previous_and_wrap(win):
    win.editor.setText("日本 cat Cat\ncat")
    find(win, "cat")
    win.editor.setCursorPosition(0, 0)
    assert win.find_next(True) and win.editor.selectedText() == "cat"
    assert win.find_next(True) and win.editor.selectedText() == "Cat"       # case-insensitive
    assert win.find_next(True) and win.editor.getSelection()[0] == 1
    assert win.find_next(True) and win.editor.getSelection()[:2] == (0, 3)  # wrapped (after the 2 CJK chars)
    assert win.find_next(False) and win.editor.getSelection()[0] == 1       # backwards wraps to the end
    find(win, "Cat", case=True)
    win.editor.setCursorPosition(0, 0)
    assert win.find_next(True) and win.editor.getSelection()[:2] == (0, 7)


def test_replace_all_regex_is_one_undo(win):
    win.editor.setText("v1.2 and v10.20\nv3.4")
    d = find(win, r"v(\d+)\.(\d+)", regex=True, replace=r"\2.\1")
    n = win.replace_all()
    assert n == 3 and win.editor.text() == "2.1 and 20.10\n4.3"
    win.editor.undo()
    assert win.editor.text() == "v1.2 and v10.20\nv3.4"
    assert d.status.text() == ""


def test_replace_in_selection_and_whole_word(win):
    win.editor.setText("cat catalog cat\ncat")
    win.editor.setSelection(0, 0, 0, 15)
    find(win, "cat", word=True, replace="dog")
    assert win.replace_all(in_selection=True) == 2
    assert win.editor.text() == "dog catalog dog\ncat"


def test_invalid_regex_is_reported(win):
    win.editor.setText("x")
    d = find(win, "(", regex=True)
    assert not win.find_next(True) and "Invalid regular expression" in d.status.text()


def test_line_tools_on_the_selection(win):
    win.editor.setText("pear\nApple\nbanana\nkeep\n")
    win.editor.setSelection(0, 0, 3, 0)          # three lines; the 4th isn't touched
    win.lines_op(textops.sort_lines)             # what Sort Lines' OK does, with the dialog's defaults
    assert win.editor.text() == "Apple\nbanana\npear\nkeep\n"
    win.editor.setSelection(0, 0, 0, 0)
    act(win, "Duplicate Line")
    assert win.editor.text().startswith("Apple\nApple\n")
    win.editor.undo()
    assert win.editor.text() == "Apple\nbanana\npear\nkeep\n"


def test_toggle_comment_uses_the_scheme(win, tmp_path):
    p = tmp_path / "x.py"
    p.write_bytes(b"a = 1\nb = 2\n")   # exact bytes: write_text gives \r\n on Windows
    win.open_path(str(p))
    win.editor.selectAll()
    act(win, "Toggle Line Comment")
    assert win.editor.text() == "# a = 1\n# b = 2\n"
    act(win, "Toggle Line Comment")
    assert win.editor.text() == "a = 1\nb = 2\n"


def test_convert_case_on_selection(win):
    win.editor.setText("hello world")
    win.editor.setSelection(0, 0, 0, 5)
    act(win, "Uppercase")
    assert win.editor.text() == "HELLO world"


def test_change_encoding_and_line_endings(win, tmp_path):
    p = tmp_path / "e.txt"
    p.write_bytes(b"a\r\nb\r\n")
    win.open_path(str(p))
    win.set_encoding(document.BY_KEY["utf-16le-bom"])
    win.set_eol("lf")
    win.save()
    assert p.read_bytes() == codecs.BOM_UTF16_LE + "a\nb\n".encode("utf-16-le")
    assert win.st["enc"].text() == "Unicode" and win.st["eol"].text() == "LF"


def test_unencodable_text_offers_utf8(win, tmp_path):
    p = tmp_path / "w.txt"
    p.write_bytes("café".encode("cp1252"))
    win.open_path(str(p))
    assert win.encoding.label == "ANSI"
    win.editor.append(" 日本")
    assert win.save()                                    # 'Yes' to saving as UTF-8 instead
    assert p.read_bytes() == "café 日本".encode("utf-8") and win.encoding.label == "UTF-8"


def test_reload_when_changed_on_disk(win, tmp_path):
    p = tmp_path / "live.log"
    p.write_bytes(b"one\n")
    win.open_path(str(p))
    p.write_bytes(b"one\ntwo\n")
    os.utime(p, (win.disk_mtime + 5, win.disk_mtime + 5))
    win._disk_changed(str(p))
    assert win.editor.text() == "one\ntwo\n" and not win.editor.isModified()


def test_go_to(win):
    win.editor.setText("\n".join(f"line {i}" for i in range(1, 201)))
    win.go_to(120, 3)
    assert win.editor.getCursorPosition() == (119, 2)
    win.go_to(9999)
    assert win.editor.getCursorPosition()[0] == 199


def test_scheme_follows_save_as(win, tmp_path, monkeypatch):
    win.editor.setText("x = 1\n")
    target = tmp_path / "script.py"
    monkeypatch.setattr(main_window.QFileDialog, "getSaveFileName", staticmethod(lambda *a, **k: (str(target), "")))
    assert win.save_as()
    assert win.scheme.name == "Python Script" and target.read_text() == "x = 1\n"


def test_auto_close_html(win, tmp_path):
    p = tmp_path / "p.html"
    p.write_text("")
    win.open_path(str(p))
    win._actions["auto_close_html"].setChecked(True)
    win.editor.insert('<div class="x">')
    win.editor.setCursorPosition(0, len('<div class="x">'))
    win._char_added(ord(">"))
    assert win.editor.text() == '<div class="x"></div>'
    win.editor.setText("<br>")
    win.editor.setCursorPosition(0, 4)
    win._char_added(ord(">"))
    assert win.editor.text() == "<br>"


def test_view_toggles_persist(qapp, monkeypatch):
    monkeypatch.setattr(main_window, "message", lambda *a, **k: 0)
    w = main_window.MainWindow()
    w._actions["wrap"].trigger()
    assert w.editor.wrapMode() == QsciScintilla.WrapMode.WrapWord
    w.close()
    w2 = main_window.MainWindow()
    assert w2._actions["wrap"].isChecked() and w2.editor.wrapMode() == QsciScintilla.WrapMode.WrapWord
    w2._actions["wrap"].trigger()
    w2.close()


def test_cli_parse():
    from pr7w.app import parse
    assert parse(["notes.txt", "/g", "120,8"]) == (None, "notes.txt", (120, 8))
    assert parse(["-g", "5", "x.py"]) == (None, "x.py", (5, 1))
    assert parse(["--register"])[0] == "--register"
    with pytest.raises(SystemExit):
        parse(["/g", "abc"])


def test_status_counts_characters_not_bytes(win):
    win.editor.setText("日本語")
    win.editor.selectAll()
    win._status()
    assert "Sel 3" in win.st["pos"].text()
