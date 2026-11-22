"""AURORA, printing, Customize Schemes, replacing Notepad."""

import json
import os

import pytest
from PyQt6.QtGui import QColor

from pr7w import main_window, notepad, schemes, theme
from pr7w.app import parse
from pr7w.editor import style_lexer, editor_font


@pytest.fixture()
def win(qapp, monkeypatch):
    monkeypatch.setattr(main_window, "message", lambda *a, **k: 0)
    w = main_window.MainWindow()
    yield w
    w.set_finish("obsidian")
    w.editor.setModified(False)
    w.close()


def drawn_paper(w) -> str:
    """The background Scintilla really draws (paper() ignores it while a lexer is set)."""
    from PyQt6.Qsci import QsciScintilla
    v = w.editor.SendScintilla(QsciScintilla.SCI_STYLEGETBACK, 32)  # STYLE_DEFAULT, as BGR
    return "#%02X%02X%02X" % (v & 255, (v >> 8) & 255, (v >> 16) & 255)


def is_family(colour: str) -> bool:
    """A family colour: a pink / red / orange hue, or a grey / near-black / pearl (almost no chroma).
    Chroma, not HSL saturation: HSL calls near-blacks like #08060A '25% saturated purple'."""
    c = QColor(colour)
    chroma = (max(c.red(), c.green(), c.blue()) - min(c.red(), c.green(), c.blue())) / 255
    return chroma < 0.12 or c.hslHue() >= 318 or c.hslHue() <= 42


def keyword_colour(w):
    lexer = w.editor.lexer()
    style = next(i for i in range(128) if lexer.description(i) == "Keyword")
    return lexer.color(style).name().upper()


# ---------------------------------------------------------------- AURORA
def test_finish_switch_recolours_everything(win, tmp_path):
    p = tmp_path / "a.py"
    p.write_bytes(b"def f():\n    return 1\n")
    win.open_path(str(p))
    assert keyword_colour(win) == theme.SYNTAX_SETS["obsidian"]["keyword"][0]
    win.set_finish("aurora")
    assert keyword_colour(win) == theme.SYNTAX_SETS["aurora"]["keyword"][0]
    assert drawn_paper(win) == theme.EDITOR_SETS["aurora"]["paper"]
    assert theme.BACKGROUND == "#D9D0D4" and "#D9D0D4" in main_window.QApplication.instance().styleSheet()
    assert win.settings.value("finish") == "aurora"
    win.set_finish("obsidian")
    assert keyword_colour(win) == theme.SYNTAX_SETS["obsidian"]["keyword"][0]
    assert theme.BACKGROUND == "#060407"


@pytest.mark.parametrize("finish", ["obsidian", "aurora"])
def test_every_colour_is_a_family_colour(finish):
    """No green, blue, purple, yellow or cyan in either finish's syntax colours or swatches."""
    colours = [c for c, _, _ in theme.SYNTAX_SETS[finish].values()] + theme.SWATCHES[finish] + \
        [v for v in theme.EDITOR_SETS[finish].values()]
    for colour in colours:
        assert is_family(colour), (finish, colour)


# ---------------------------------------------------------------- printing
def pdf(tmp_path, name, header=True):
    from pr7w.printing import PagePrinter
    from PyQt6.QtPrintSupport import QPrinter
    p = PagePrinter(header=header)
    p.setOutputFormat(QPrinter.OutputFormat.PdfFormat)
    p.setOutputFileName(str(tmp_path / name))
    return p


def page_count(path):
    data = path.read_bytes()
    return data.count(b"/Type /Page\n") + data.count(b"/Type /Page\r") + data.count(b"/Type /Page ") + \
        data.count(b"/Type /Page>") + data.count(b"/Type /Page/")


def test_print_to_pdf_with_header_and_selection(win, tmp_path):
    win.editor.setText("\n".join(f"line {i}: the quick brown fox jumps over the lazy dog" for i in range(300)))
    paper_before = drawn_paper(win)
    assert win.print_document(pdf(tmp_path, "plain.pdf", header=False), dialog=False)
    assert win.print_document(pdf(tmp_path, "head.pdf", header=True), dialog=False)
    plain, head = page_count(tmp_path / "plain.pdf"), page_count(tmp_path / "head.pdf")
    assert plain >= 3 and head >= plain   # the header and footer take room on every page
    assert (tmp_path / "head.pdf").read_bytes().startswith(b"%PDF")
    assert drawn_paper(win) == paper_before                          # screen colours restored
    from pr7w import printing
    p = pdf(tmp_path, "sel.pdf")
    assert printing.print_editor(win.editor, p, lines=(0, 20))
    assert page_count(tmp_path / "sel.pdf") < plain


# ---------------------------------------------------------------- Customize Schemes
def test_overrides_role_then_scheme(qapp):
    lexer = schemes.make_lexer(schemes.BY_NAME["Python Script"])
    kw = next(i for i in range(128) if lexer.description(i) == "Keyword")
    cls = next(i for i in range(128) if lexer.description(i) == "Class name")
    style_lexer(lexer, editor_font(), overrides={"role:keyword": {"fore": "#FF5D6C", "underline": True}})
    assert lexer.color(kw).name().upper() == "#FF5D6C" and lexer.font(kw).underline()
    style_lexer(lexer, editor_font(), overrides={"role:keyword": {"fore": "#FF5D6C"},
                                                 f"Python Script:{kw}": {"fore": "#FFB22E", "bold": False}},
                scheme="Python Script")
    assert lexer.color(kw).name().upper() == "#FFB22E" and not lexer.font(kw).bold()
    assert lexer.color(cls).name().upper() == theme.SYNTAX_SETS["obsidian"]["class"][0]   # untouched


def test_customize_dialog_live_cancel_and_save(win, tmp_path, monkeypatch):
    p = tmp_path / "a.py"
    p.write_bytes(b"def f():\n    return 1\n")
    win.open_path(str(p))
    before = keyword_colour(win)
    seen = {}

    def run_dialog(dialog_self):
        dialog_self.schemes.setCurrentRow(0)                       # All schemes (by role)
        row = [k for k, _ in dialog_self.keys].index("role:keyword")
        dialog_self.styles.setCurrentRow(row)
        dialog_self._set("fore", "#FF4FA8")
        seen["live"] = keyword_colour(win)
        return seen.get("answer")

    monkeypatch.setattr(main_window.CustomizeSchemesDialog, "exec",
                        lambda self: (run_dialog(self), self.reject() if seen.get("answer") == 0 else None)[1] or
                        seen.get("answer"))
    seen["answer"] = 0                                             # Cancel
    win.customize_schemes()
    assert seen["live"] == "#FF4FA8" and keyword_colour(win) == before
    monkeypatch.setattr(main_window.CustomizeSchemesDialog, "exec",
                        lambda self: (run_dialog(self), main_window.CustomizeSchemesDialog.DialogCode.Accepted)[1])
    win.customize_schemes()                                        # OK
    assert keyword_colour(win) == "#FF4FA8"
    saved = json.loads(win.settings.value("style_overrides"))
    assert saved["obsidian"]["role:keyword"]["fore"] == "#FF4FA8" and "aurora" not in saved
    win.settings.setValue("style_overrides", "{}")


# ---------------------------------------------------------------- Notepad
def test_notepad_command_lines():
    exe = r"C:\Windows\System32\notepad.exe"
    assert parse(["/z", exe, r"C:\Users\me\My", r"Notes\todo.txt"]) == (None, r"C:\Users\me\My Notes\todo.txt", None)
    assert parse(["/z", exe, '"C:\\a b\\c.txt"']) == (None, r"C:\a b\c.txt", None)
    assert parse(["/z", exe, "/p", r"C:\x.txt"]) == ("--print-file", r"C:\x.txt", None)
    assert parse(["/z", exe, "/pt", r"C:\x.txt", "Printer", "Driver", "Port"])[0] == "--print-file"
    assert parse(["/z", exe]) == (None, None, None)                # just "notepad": an empty window
    assert parse(["--replace-notepad"])[0] == "--replace-notepad"


def test_only_our_redirect_is_ours():
    assert notepad.is_ours(r'"C:\Users\me\AppData\Local\Programs\PR7-W\PR7-W.exe" /z')
    assert notepad.is_ours(r'"C:\Python\pythonw.exe" -m pr7w /z')
    assert not notepad.is_ours(r'"C:\Program Files\Notepad++\notepad++.exe" -notepadStyleCmdline -z')
    assert notepad.debugger_command().endswith(" /z")


@pytest.mark.skipif(os.name != "nt" or not os.environ.get("CI"), reason="machine-wide; Windows CI (admin) only")
def test_replace_and_restore_notepad():
    import winreg
    assert notepad.is_admin()
    notepad.replace()
    try:
        for view in (winreg.KEY_WOW64_64KEY, winreg.KEY_WOW64_32KEY):
            k = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, notepad.IFEO, 0, winreg.KEY_READ | view)
            assert notepad.is_ours(winreg.QueryValueEx(k, "Debugger")[0])
        assert notepad.is_replaced()
    finally:
        notepad.restore()
    assert not notepad.is_replaced() and notepad.current_debugger() == ""
    # someone else's redirect is left alone
    k = winreg.CreateKeyEx(winreg.HKEY_LOCAL_MACHINE, notepad.IFEO, 0, winreg.KEY_SET_VALUE | winreg.KEY_WOW64_64KEY)
    winreg.SetValueEx(k, "Debugger", 0, winreg.REG_SZ, "other.exe -z")
    notepad.restore()
    assert notepad.current_debugger() == "other.exe -z"
    winreg.DeleteValue(k, "Debugger")
