"""The editing area: Scintilla (QScintilla), the engine Notepad2 is built on, in the Paragon colours.

Colours come from the family palette only (pink / red / orange hues, pearl and onyx greys), and are
given by a style's *role* (comment, keyword, string ...), so every language gets the same scheme.
"""

from __future__ import annotations

import os

from PyQt6.Qsci import QsciScintilla
from PyQt6.QtGui import QColor, QFont

from . import theme

# Syntax colours (all within the family's hues ~318 deg -> 0 -> 42 deg, or greys).
SYNTAX = {
    "default": (theme.TEXT, False, False),
    "comment": ("#9A8F96", False, True),
    "keyword": ("#FF6B3D", True, False),     # orange-red
    "keyword2": ("#FF9A2E", False, False),   # orange: builtins, secondary keywords
    "string": ("#FFB3C8", False, False),     # pale pink
    "char": ("#FFC29A", False, False),       # peach: chars, regexes
    "number": ("#FFB22E", False, False),     # amber-orange
    "class": ("#FF4FA8", True, False),       # magenta-pink
    "function": ("#FF6F91", False, False),   # rose
    "decorator": ("#FF8A5C", False, False),  # coral: decorators, preprocessor
    "operator": ("#D9C9CF", False, False),   # pearl grey
    "tag": ("#FF5D6C", False, False),        # markup tags
    "attribute": ("#FF9A2E", False, False),
    "heading": ("#FF6B3D", True, False),
    "error": ("#FFFFFF", False, False),
}

PAPER = "#08060A"           # editor background (a shade above the window's onyx)
MARGIN = "#0B090C"
MARGIN_TEXT = "#6B6569"
CARET_LINE = "#120E13"
SELECTION = theme.ACCENT_DIM
BRACE = "#FF7A1A"


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


def style_lexer(lexer, font: QFont) -> None:
    """Paint a QScintilla lexer in the family colours, style by style, from each style's role."""
    lexer.setDefaultPaper(QColor(PAPER))
    lexer.setDefaultColor(QColor(theme.TEXT))
    lexer.setPaper(QColor(PAPER), -1)
    lexer.setFont(font, -1)
    for style in range(128):
        desc = lexer.description(style)
        if not desc:
            continue
        colour, bold, italic = SYNTAX[role_of(desc)]
        lexer.setColor(QColor(colour), style)
        f = QFont(font)
        f.setBold(bold)
        f.setItalic(italic)
        lexer.setFont(f, style)
        if role_of(desc) == "error":
            lexer.setPaper(QColor(theme.ACCENT_DIM), style)
        if hasattr(lexer, "setEolFill"):
            lexer.setEolFill(False, style)


class Editor(QsciScintilla):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.base_font = editor_font()
        self.setUtf8(True)
        self.setFont(self.base_font)
        self.setPaper(QColor(PAPER))
        self.setColor(QColor(theme.TEXT))
        # margins: line numbers, bookmarks, folding
        self.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.setMarginsFont(self.base_font)
        self.setMarginsBackgroundColor(QColor(MARGIN))
        self.setMarginsForegroundColor(QColor(MARGIN_TEXT))
        self.setMarginWidth(1, 14)
        self.setMarginSensitivity(1, True)
        self.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle, 2)
        self.setFoldMarginColors(QColor(MARGIN), QColor(MARGIN))
        self._fold_colours()
        self.bookmark = self.markerDefine(QsciScintilla.MarkerSymbol.Bookmark, 24)
        self.setMarkerBackgroundColor(QColor(theme.ACCENT), self.bookmark)
        # caret, current line, selection, braces, guides
        self.setCaretForegroundColor(QColor(theme.ACCENT))
        self.setCaretWidth(2)
        self.setCaretLineVisible(True)
        self.setCaretLineBackgroundColor(QColor(CARET_LINE))
        self.setSelectionBackgroundColor(QColor(SELECTION))
        self.setSelectionForegroundColor(QColor("#FFFFFF"))
        self.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)
        self.setMatchedBraceForegroundColor(QColor(BRACE))
        self.setMatchedBraceBackgroundColor(QColor("#2A1408"))
        self.setUnmatchedBraceForegroundColor(QColor("#FFFFFF"))
        self.setUnmatchedBraceBackgroundColor(QColor(theme.ACCENT_DIM))
        self.setIndentationGuides(True)
        self.setIndentationGuidesBackgroundColor(QColor(PAPER))
        self.setIndentationGuidesForegroundColor(QColor(theme.PANEL_EDGE))
        self.setWhitespaceForegroundColor(QColor("#3A3036"))
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

    def _fold_colours(self):
        """Fold boxes and lines as dim grey outlines on the margin (Scintilla's default is white boxes).
        For the folding markers (25-31) 'fore' is the box fill and 'back' the outline and lines."""
        for n in range(25, 32):
            self.SendScintilla(QsciScintilla.SCI_MARKERSETFORE, n, QColor(MARGIN))
            self.SendScintilla(QsciScintilla.SCI_MARKERSETBACK, n, QColor(theme.TEXT_DIM))

    def _fit_numbers(self):
        if not getattr(self, "_numbers_on", True):
            self.setMarginWidth(0, 0)
            return
        digits = max(3, len(str(self.lines())))
        self.setMarginWidth(0, "9" * (digits + 1))

    def set_lexer(self, lexer):
        if lexer is not None:
            style_lexer(lexer, self.base_font)
        self.setLexer(lexer)
        if lexer is None:  # plain text: the editor's own colours
            self.setPaper(QColor(PAPER))
            self.setColor(QColor(theme.TEXT))
            self.setFont(self.base_font)
        self.setFoldMarginColors(QColor(MARGIN), QColor(MARGIN))
        self.setMarginsBackgroundColor(QColor(MARGIN))
        self.setMarginsForegroundColor(QColor(MARGIN_TEXT))
        self._fold_colours()

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
        self.setFoldMarginColors(QColor(MARGIN), QColor(MARGIN))
        self._fold_colours()
