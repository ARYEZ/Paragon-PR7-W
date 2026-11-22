"""The editing area: Scintilla (QScintilla), the engine Notepad2 is built on, in the Paragon colours.

Colours come from the family palette only (pink / red / orange hues, pearl and onyx greys), and are
given by a style's *role* (comment, keyword, string ...), so every language gets the same scheme.
"""

from __future__ import annotations

import os

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QColor, QFont

from . import theme

# Syntax colours by role, per finish, live in theme.SYNTAX_SETS (OBSIDIAN's set kept here for tests).
SYNTAX = theme.SYNTAX_SETS["obsidian"]


def role_of(description: str) -> str:
    """A lexer style's role from its description ('Single-quoted string' -> 'string')."""
    d = description.lower()
    if not d:
        return "default"
    for words, role in ((("unclosed", "bad", "error"), "error"), (("comment", "doc"), "comment"),
                        (("decorator", "preprocessor", "directive", "pragma"), "decorator"),
                        (("class",), "class"), (("function", "method", "def "), "function"),
                        (("keyword set 2", "secondary", "builtin", "keyword2", "global class"), "keyword2"),
                        (("keyword", "reserved", "instruction", "command", "statement"), "keyword"),
                        (("regex", "character", "char ", "escape"), "char"),
                        (("string", "quoted", "literal", "text block", "heredoc", "verbatim"), "string"),
                        (("number", "numeric", "hex", "float", "integer"), "number"),
                        (("tag", "element", "header", "section"), "tag"),
                        (("attribute", "property", "key"), "attribute"),
                        (("heading", "h1", "h2", "h3", "strong", "emphasis"), "heading"),
                        (("operator", "punctuation", "delimiter"), "operator")):
        if any(w in d for w in words):
            return role
    return "default"


def editor_font(size: int = 11) -> QFont:
    for family in ("Consolas", "Cascadia Mono", "DejaVu Sans Mono", "Courier New"):
        f = QFont(family, size)
        if f.exactMatch() or family == "Courier New":
            f.setStyleHint(QFont.StyleHint.Monospace)
            return f
    return QFont("monospace", size)


def style_lexer(lexer, font: QFont, syntax: dict | None = None, paper: str | None = None,
                overrides: dict | None = None, scheme: str = "") -> None:
    """Paint a QScintilla lexer, style by style, from each style's role.

    syntax: role -> (colour, bold, italic); the current finish's set by default (printing passes its own).
    overrides: Customize Schemes' changes, {"role:<role>": attrs, "<scheme>:<style>": attrs} where attrs is
    {"fore": "#rrggbb", "bold": bool, "italic": bool, "underline": bool}; a scheme's own style wins over its role.
    """
    syntax = syntax or theme.syntax()
    paper = paper or theme.editor_colours()["paper"]
    overrides = overrides or {}
    lexer.setDefaultPaper(QColor(paper))
    lexer.setDefaultColor(QColor(syntax["default"][0]))
    lexer.setPaper(QColor(paper), -1)
    lexer.setFont(font, -1)
    for style in range(128):
        desc = lexer.description(style)
        if not desc:
            continue
        role = role_of(desc)
        colour, bold, italic = syntax[role]
        underline = False
        for key in (f"role:{role}", f"{scheme}:{style}"):
            o = overrides.get(key)
            if o:
                colour = o.get("fore", colour)
                bold = o.get("bold", bold)
                italic = o.get("italic", italic)
                underline = o.get("underline", underline)
        lexer.setColor(QColor(colour), style)
        f = QFont(font)
        f.setBold(bold)
        f.setItalic(italic)
        f.setUnderline(underline)
        lexer.setFont(f, style)
        if role == "error":
            lexer.setPaper(QColor(theme.ACCENT_DIM), style)
        if hasattr(lexer, "setEolFill"):
            lexer.setEolFill(False, style)


class Editor(QsciScintilla):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_font = editor_font()
        self.setUtf8(True)
        self.setFont(self.base_font)
        # margins: line numbers, bookmarks, folding
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginsFont(self.base_font)
        self.setMarginWidth(1, 14)
        self.setMarginSensitivity(1, True)
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 2)
        self.bookmark = self.markerDefine(QsciScintilla.MarkerSymbol.Bookmark, 24)
        self.setMarkerBackgroundColor(QColor(theme.ACCENT), self.bookmark)
        # caret, current line, selection, braces, guides
        self.setCaretWidth(2)
        self.setCaretLineVisible(True)
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setIndentationGuides(True)
        self.overrides: dict = {}
        self.scheme_name = ""
        self.apply_colours()
        self.setAutoIndent(True)
        self.setIndentationsUseTabs(False)
        self.setTabWidth(4)
        self.setEolMode(QsciScintilla.EolMode.EolWindows if os.name == "nt" else QsciScintilla.EolMode.EolUnix)
        self.SendScintilla(QsciScintilla.SCI_SETMULTIPLESELECTION, 1)
        self.SendScintilla(QsciScintilla.SCI_SETADDITIONALSELECTIONTYPING, 1)
        self.SendScintilla(QsciScintilla.SCI_SETVIRTUALSPACEOPTIONS, QsciScintilla.SCVS_RECTANGULARSELECTION)
        # Horizontal scrollbar only when a line is wider than the window (Scintilla assumes 2000 px).
        self.SendScintilla(QsciScintilla.SCI_SETSCROLLWIDTH, 1)
        self.SendScintilla(QsciScintilla.SCI_SETSCROLLWIDTHTRACKING, 1)
        self.textChanged.connect(self._fit_numbers)
        self._fit_numbers()

    def apply_colours(self):
        """Every editor colour from the current finish (called again when the finish changes)."""
        c = theme.editor_colours()
        default = theme.syntax()["default"][0]
        self.setPaper(QColor(c["paper"]))
        self.setColor(QColor(default))
        self.setMarginsBackgroundColor(QColor(c["margin"]))
        self.setMarginsForegroundColor(QColor(c["margin_text"]))
        self.setFoldMarginColors(QColor(c["margin"]), QColor(c["margin"]))
        self._fold_colours()
        self.setCaretForegroundColor(QColor(theme.ACCENT))
        self.setCaretLineBackgroundColor(QColor(c["caret_line"]))
        self.setSelectionBackgroundColor(QColor(theme.ACCENT_DIM))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))
        self.setMatchedBraceForegroundColor(QColor(c["brace"]))
        self.setMatchedBraceBackgroundColor(QColor(c["brace_back"]))
        self.setUnmatchedBraceForegroundColor(QColor("#FFFFFF"))
        self.setUnmatchedBraceBackgroundColor(QColor(theme.ACCENT_DIM))
        self.setIndentationGuidesBackgroundColor(QColor(c["paper"]))
        self.setIndentationGuidesForegroundColor(QColor(c["guides"]))
        self.setWhitespaceForegroundColor(QColor(c["whitespace"]))
        if self.lexer() is not None:
            style_lexer(self.lexer(), self.base_font, overrides=self.overrides, scheme=self.scheme_name)
            self.recolor()

    def _fold_colours(self):
        """Fold boxes and lines as dim outlines on the margin (Scintilla's default is white boxes).
        For the folding markers (25-31) 'fore' is the box fill and 'back' the outline and lines."""
        c = theme.editor_colours()
        for n in range(25, 32):
            self.SendScintilla(QsciScintilla.SCI_MARKERSETFORE, n, QColor(c["margin"]))
            self.SendScintilla(QsciScintilla.SCI_MARKERSETBACK, n, QColor(theme.TEXT_DIM))

    def _fit_numbers(self):
        if not getattr(self, "_numbers_on", True):
            self.setMarginWidth(0, 0)
            return
        digits = max(3, len(str(self.lines())))
        self.setMarginWidth(0, "9" * (digits + 1))

    def set_lexer(self, lexer, scheme: str = ""):
        self.scheme_name = scheme
        if lexer is not None:
            style_lexer(lexer, self.base_font, overrides=self.overrides, scheme=scheme)
        self.setLexer(lexer)
        if lexer is None:  # plain text: the editor's own colours
            self.setFont(self.base_font)
        self.apply_colours()

    # ------------------------------------------------------------------ positions
    # Scintilla positions are UTF-8 byte offsets; Python strings count characters. These convert,
    # so a search done with Python's re on text() lands on the right text in the editor.
    def char_to_pos(self, n: int) -> int:
        if n <= 0:
            return 0
        pos = self.SendScintilla(QsciScintilla.SCI_POSITIONRELATIVE, 0, n)
        return pos if pos or n == 0 else self.length()

    def pos_to_char(self, pos: int) -> int:
        return self.SendScintilla(QsciScintilla.SCI_COUNTCHARACTERS, 0, pos)

    def selection_positions(self) -> tuple[int, int]:
        return (self.SendScintilla(QsciScintilla.SCI_GETSELECTIONSTART),
                self.SendScintilla(QsciScintilla.SCI_GETSELECTIONEND))

    def text_range(self, start: int, end: int) -> str:
        return self.text(start, end) if end > start else ""

    # ------------------------------------------------------------------ View menu switches
    def setWhitespaceVisibility_bool(self, on: bool):
        self.setWhitespaceVisibility(QsciScintilla.WhitespaceVisibility.WsVisible if on
                                     else QsciScintilla.WhitespaceVisibility.WsInvisible)

    def set_wrap_symbols(self, on: bool):
        self.setWrapVisualFlags(QsciScintilla.WrapVisualFlag.WrapFlagByText if on
                                else QsciScintilla.WrapVisualFlag.WrapFlagNone)

    def set_brace_matching(self, on: bool):
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch if on else QsciScintilla.BraceMatch.NoBraceMatch)

    def show_line_numbers(self, on: bool):
        self._numbers_on = on
        self._fit_numbers()

    def show_symbol_margin(self, on: bool):
        self.setMarginWidth(1, 14 if on else 0)

    def show_folding(self, on: bool):
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle if on else QsciScintilla.FoldStyle.NoFoldStyle, 2)
        self.apply_colours()
