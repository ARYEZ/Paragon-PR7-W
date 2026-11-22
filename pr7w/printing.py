"""Printing as Notepad2 does: a header (file name, date) and footer (page number), colour modes, zoom.

The screen's colours are made for a dark (or pearl) background; on paper, text is printed in the darker
shades of the same family hues (AURORA's syntax set) on white, unless "Screen colours" is chosen.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PyQt6.Qsci import QsciPrinter, QsciScintilla
from PyQt6.QtCore import QRect, Qt
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen

from . import theme

COLOUR_MODES = {  # setting -> (label, Scintilla print mode, syntax set or None for the screen's)
    "colour": ("Colour on white", QsciScintilla.SC_PRINT_COLOURONWHITE, "aurora"),
    "black": ("Black on white", QsciScintilla.SC_PRINT_BLACKONWHITE, "aurora"),
    "screen": ("Screen colours", QsciScintilla.SC_PRINT_NORMAL, None),
}


class PagePrinter(QsciPrinter):
    """QsciPrinter with Notepad2's header and footer, in Inter, in ink on white."""

    def __init__(self, title: str = "", header: bool = True):
        super().__init__(QsciPrinter.PrinterMode.HighResolution)
        self.title = title
        self.header = header
        self.date = datetime.now().strftime("%d.%m.%Y %H:%M")
        self.pages = 0

    def formatPage(self, painter: QPainter, drawing: bool, area: QRect, pagenr: int):
        self.pages = max(self.pages, pagenr)
        if not self.header:
            return
        f = QFont("Inter")
        f.setPointSizeF(8.5)
        fm = QFontMetrics(f, painter.device())
        h = fm.height()
        gap = h // 2
        if drawing:
            painter.save()
            painter.setFont(f)
            painter.setPen(QColor("#26252A"))
            top = QRect(area.left(), area.top(), area.width(), h)
            painter.drawText(top, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.title)
            painter.drawText(top, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self.date)
            painter.setPen(QPen(QColor("#A8999F"), max(1, h // 14)))
            painter.drawLine(area.left(), area.top() + h + gap // 2, area.right(), area.top() + h + gap // 2)
            bottom = QRect(area.left(), area.bottom() - h, area.width(), h)
            painter.drawLine(area.left(), bottom.top() - gap // 2, area.right(), bottom.top() - gap // 2)
            painter.setPen(QColor("#26252A"))
            painter.drawText(bottom, Qt.AlignmentFlag.AlignCenter, f"Page {pagenr}")
            painter.restore()
        area.setTop(area.top() + h + gap)
        area.setBottom(area.bottom() - h - gap)


def print_editor(editor, printer: PagePrinter, mode: str = "colour", zoom: int = 0,
                 lines: tuple[int, int] | None = None, overrides: dict | None = None) -> bool:
    """Print the editor (or `lines`, 0-based inclusive) on `printer`; restores the screen colours after."""
    from .editor import style_lexer
    label, sci_mode, syntax_set = COLOUR_MODES.get(mode, COLOUR_MODES["colour"])
    lexer = editor.lexer()
    try:
        if syntax_set:
            syntax = theme.SYNTAX_SETS[syntax_set]
            if lexer is not None:
                style_lexer(lexer, editor.base_font, syntax=syntax, paper="#FFFFFF", overrides=overrides,
                            scheme=editor.scheme_name)
            else:
                editor.setPaper(QColor("#FFFFFF"))
                editor.setColor(QColor(syntax["default"][0]))
        editor.SendScintilla(QsciScintilla.SCI_SETPRINTCOLOURMODE, sci_mode)
        printer.setMagnification(zoom)
        printer.setWrapMode(QsciScintilla.WrapMode.WrapWord)  # long lines continue on the next line
        start, end = lines if lines else (-1, -1)
        return bool(printer.printRange(editor, start, end))
    finally:
        editor.apply_colours()


def doc_title(path: str | None) -> str:
    return Path(path).name if path else "Untitled"
