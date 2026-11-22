"""Custom-painted Paragon widgets for PR7-W: the mark, the header, compact piano-black keys, line icons."""

from __future__ import annotations

from PyQt6.QtCore import QPointF, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient, QRegion, QTransform
from PyQt6.QtWidgets import QAbstractButton, QHBoxLayout, QLabel, QWidget

from . import theme

AA = QPainter.RenderHint.Antialiasing
CENTER = Qt.AlignmentFlag.AlignCenter
VLEFT = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft
VRIGHT = Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight

# --------------------------------------------------------------------------- the PR7-W mark
# The PR7 plugins' Logo.cpp construction: letters 1 unit tall, stems ~0.24, bars 0.2, slanted 0.3,
# two horizontal speed cuts; the 7 in the family gradient with a soft neon halo.
SLANT = 0.3
SPACING = 0.1
WIDTHS = [0.8, 0.84, 0.8, 0.4, 1.0]  # P, R, 7, dash, W
TOTAL_WIDTH = sum(WIDTHS) + 4 * SPACING + SLANT
CUTS = [(0.63, 0.68), (0.79, 0.83)]


def _poly(path: QPainterPath, pts, x: float) -> None:
    path.moveTo(pts[0][0] + x, pts[0][1])
    for px, py in pts[1:]:
        path.lineTo(px + x, py)
    path.closeSubpath()


W_SHAPE = [(0, 0), (.24, 0), (.31, .58), (.4, .22), (.6, .22), (.69, .58), (.76, 0), (1, 0), (.83, 1), (.6, 1),
           (.5, .62), (.4, 1), (.17, 1)]
SEVEN_SHAPE = [(0, 0), (.8, 0), (.8, .2), (.44, 1), (.18, 1), (.5, .2), (0, .2)]


def _lean() -> QTransform:
    return QTransform(1, 0, -SLANT, 1, SLANT, 0)  # x' = x + slant*(1 - y): y is down, the top leans right


def _letters() -> tuple[QPainterPath, QPainterPath]:
    main, seven = QPainterPath(), QPainterPath()
    main.setFillRule(Qt.FillRule.OddEvenFill)  # bowl counters are holes
    bowl = [(0, 0), (.64, 0), (.8, .15), (.8, .45), (.64, .6), (.24, .6), (.24, 1), (0, 1)]
    counter = [(.24, .2), (.56, .2), (.56, .4), (.24, .4)]
    x = 0.0
    _poly(main, bowl, x)
    _poly(main, counter, x)
    x += WIDTHS[0] + SPACING
    _poly(main, bowl, x)
    _poly(main, counter, x)
    _poly(main, [(.4, .6), (.64, .6), (.84, 1), (.6, 1)], x)  # R's leg
    x += WIDTHS[1] + SPACING
    _poly(seven, SEVEN_SHAPE, x)
    x += WIDTHS[2] + SPACING
    _poly(main, [(0, .42), (.4, .42), (.4, .6), (0, .6)], x)  # dash
    x += WIDTHS[3] + SPACING
    _poly(main, W_SHAPE, x)
    return _lean().map(main), _lean().map(seven)


_MAIN, _SEVEN = _letters()


def draw_mark(p: QPainter, area: QRectF, glow: bool = True) -> QRectF:
    h = min(area.height(), area.width() / TOTAL_WIDTH)
    bounds = QRectF(area.x(), area.center().y() - h / 2, TOTAL_WIDTH * h, h)
    place = QTransform().translate(bounds.x(), bounds.y()).scale(h, h)
    main, seven = place.map(_MAIN), place.map(_SEVEN)
    p.save()
    p.setRenderHint(AA)
    if glow:
        for ring in (3, 2, 1):
            c = QColor(theme.GLOW)
            c.setAlphaF(0.1 * (4 - ring))
            p.setPen(QPen(c, h * 0.07 * ring, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap,
                          Qt.PenJoinStyle.RoundJoin))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(seven)
    clip = QRegion(bounds.adjusted(-h, -h, h, h).toAlignedRect())
    for top, bottom in CUTS:
        clip -= QRegion(QRectF(bounds.x() - h, bounds.y() + h * top, bounds.width() + 2 * h,
                               h * (bottom - top)).toAlignedRect())
    p.setClipRegion(clip)
    p.setPen(Qt.PenStyle.NoPen)
    p.fillPath(main, QColor(theme.TEXT))
    p.fillPath(seven, theme.family_gradient(bounds.x(), 0, bounds.right(), 0))
    p.restore()
    return bounds


class Header(QWidget):
    """The family header: PARAGON, the PR7-W mark, a subtitle; the document's name on the right."""

    def __init__(self, subtitle: str = "TEXT EDITOR", parent=None):
        super().__init__(parent)
        self.subtitle = subtitle
        self.right = None  # None: the current finish's name
        self.setFixedHeight(56)

    def set_right(self, text: str):
        self.right = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(AA)
        r = self.rect()
        p.fillRect(r, QColor(theme.BACKGROUND))
        glow = QRadialGradient(QPointF(160, 0), 420)
        c = QColor(theme.GLOW)
        c.setAlphaF(0.07)
        glow.setColorAt(0, c)
        glow.setColorAt(1, QColor(0, 0, 0, 0))
        p.fillRect(r, glow)
        f = QFont("Inter")
        f.setPixelSize(19)
        p.setFont(f)
        p.setPen(QColor(theme.TEXT))
        p.drawText(QRectF(20, 0, 200, r.height()), VLEFT, "PARAGON")
        mark = draw_mark(p, QRectF(126, 16, 220, 24))
        f2 = QFont("Inter")
        f2.setPixelSize(12)
        f2.setWeight(QFont.Weight.DemiBold)
        p.setFont(f2)
        p.setPen(QColor(theme.TEXT_DIM))
        p.drawText(QRectF(mark.right() + 16, 0, 300, r.height()), VLEFT, self.subtitle)
        p.drawText(QRectF(0, 0, r.width() - 20, r.height()), VRIGHT,
                   self.right if self.right is not None else theme.FINISH.upper())
        p.setPen(QPen(QColor(theme.PANEL_EDGE), 1))
        p.drawLine(0, r.height() - 1, r.width(), r.height() - 1)


# --------------------------------------------------------------------------- line icons (24x24)
def _icon_path(name: str) -> QPainterPath:
    p = QPainterPath()
    if name == "new":
        p.moveTo(5, 2.5); p.lineTo(14, 2.5); p.lineTo(19, 7.5); p.lineTo(19, 21.5); p.lineTo(5, 21.5); p.closeSubpath()
        p.moveTo(14, 2.5); p.lineTo(14, 7.5); p.lineTo(19, 7.5)
        p.moveTo(12, 11); p.lineTo(12, 18); p.moveTo(8.5, 14.5); p.lineTo(15.5, 14.5)
    elif name == "open":
        p.moveTo(2.5, 6); p.quadTo(2.5, 4.5, 4, 4.5); p.lineTo(9, 4.5); p.lineTo(11, 7); p.lineTo(18.5, 7)
        p.quadTo(20, 7, 20, 8.5); p.lineTo(20, 10)
        p.moveTo(2.5, 6); p.lineTo(2.5, 19.5); p.lineTo(18, 19.5); p.lineTo(21.5, 10.5); p.lineTo(6, 10.5)
        p.lineTo(2.5, 19.5)
    elif name == "save":
        p.addRoundedRect(QRectF(3.5, 3.5, 17, 17), 2, 2)
        p.moveTo(7.5, 3.5); p.lineTo(7.5, 9); p.lineTo(15.5, 9); p.lineTo(15.5, 3.5)
        p.addRoundedRect(QRectF(7, 13, 10, 7.5), 1, 1)
    elif name == "undo":
        p.moveTo(9, 5); p.lineTo(4.5, 9.5); p.lineTo(9, 14)
        p.moveTo(4.5, 9.5); p.lineTo(14, 9.5); p.cubicTo(18.5, 9.5, 20, 12.5, 20, 14.5)
        p.cubicTo(20, 17, 18, 19.5, 14, 19.5); p.lineTo(10, 19.5)
    elif name == "redo":
        p.moveTo(15, 5); p.lineTo(19.5, 9.5); p.lineTo(15, 14)
        p.moveTo(19.5, 9.5); p.lineTo(10, 9.5); p.cubicTo(5.5, 9.5, 4, 12.5, 4, 14.5)
        p.cubicTo(4, 17, 6, 19.5, 10, 19.5); p.lineTo(14, 19.5)
    elif name == "cut":
        p.addEllipse(QRectF(3.5, 14.5, 6, 6)); p.addEllipse(QRectF(14.5, 14.5, 6, 6))
        p.moveTo(8.5, 15.5); p.lineTo(17.5, 3.5); p.moveTo(15.5, 15.5); p.lineTo(6.5, 3.5)
    elif name == "copy":
        p.addRoundedRect(QRectF(8, 8, 13, 13), 2, 2)
        p.moveTo(16, 5); p.lineTo(16, 4); p.quadTo(16, 3, 15, 3); p.lineTo(4, 3); p.quadTo(3, 3, 3, 4)
        p.lineTo(3, 15); p.quadTo(3, 16, 4, 16); p.lineTo(5, 16)
    elif name == "paste":
        p.addRoundedRect(QRectF(4.5, 4.5, 15, 17), 2, 2)
        p.addRoundedRect(QRectF(8.5, 2.5, 7, 4), 1, 1)
        p.moveTo(8, 11.5); p.lineTo(16, 11.5); p.moveTo(8, 15.5); p.lineTo(14, 15.5)
    elif name == "find":
        p.addEllipse(QRectF(3.5, 3.5, 12, 12)); p.moveTo(14, 14); p.lineTo(20.5, 20.5)
    elif name == "replace":
        p.addEllipse(QRectF(2.5, 2.5, 9, 9)); p.moveTo(10, 10); p.lineTo(13, 13)
        p.moveTo(14, 16); p.lineTo(21, 16); p.moveTo(18.5, 13.5); p.lineTo(21, 16); p.lineTo(18.5, 18.5)
        p.moveTo(21, 20.5); p.lineTo(14, 20.5)
    elif name == "wrap":
        p.moveTo(3, 5.5); p.lineTo(21, 5.5); p.moveTo(3, 11.5); p.lineTo(17, 11.5)
        p.cubicTo(20.5, 11.5, 20.5, 17.5, 17, 17.5); p.lineTo(11, 17.5)
        p.moveTo(13.5, 15); p.lineTo(11, 17.5); p.lineTo(13.5, 20); p.moveTo(3, 17.5); p.lineTo(7, 17.5)
    elif name == "zoomin":
        p.addEllipse(QRectF(3.5, 3.5, 12, 12)); p.moveTo(14, 14); p.lineTo(20.5, 20.5)
        p.moveTo(9.5, 6.5); p.lineTo(9.5, 12.5); p.moveTo(6.5, 9.5); p.lineTo(12.5, 9.5)
    elif name == "zoomout":
        p.addEllipse(QRectF(3.5, 3.5, 12, 12)); p.moveTo(14, 14); p.lineTo(20.5, 20.5)
        p.moveTo(6.5, 9.5); p.lineTo(12.5, 9.5)
    elif name == "scheme":
        p.moveTo(8, 6); p.lineTo(2.5, 12); p.lineTo(8, 18); p.moveTo(16, 6); p.lineTo(21.5, 12); p.lineTo(16, 18)
        p.moveTo(13.5, 4); p.lineTo(10.5, 20)
    return p


def draw_icon(p: QPainter, name: str, rect: QRectF, colour, width: float = 1.7) -> None:
    path = _icon_path(name)
    s = min(rect.width(), rect.height()) / 24.0
    t = QTransform().translate(rect.center().x() - 12 * s, rect.center().y() - 12 * s).scale(s, s)
    p.save()
    p.setRenderHint(AA)
    p.setPen(QPen(colour, width, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.setBrush(Qt.BrushStyle.NoBrush)
    p.drawPath(t.map(path))
    p.restore()


# --------------------------------------------------------------------------- compact piano-black keys
class SmallKey(QAbstractButton):
    """A compact family piano-black key: icon only (tooltip names it). Checkable keys (word wrap)
    show the family gradient bar at their foot when on, as the spec's buttons do."""

    def __init__(self, icon: str, tip: str, checkable: bool = False, parent=None):
        super().__init__(parent)
        self.icon_name = icon
        self.setToolTip(tip)
        self.setCheckable(checkable)
        self.setFixedSize(QSize(38, 34))
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(AA)
        down, hover = self.isDown(), self.underMouse() and self.isEnabled()
        r = QRectF(self.rect()).adjusted(2, 1, -2, -4)
        if down:
            r.translate(0, 1)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QColor(0, 0, 0, 110 if down else 150))
        p.drawRoundedRect(r.translated(0, 2), 5, 5)
        from PyQt6.QtGui import QLinearGradient
        ch = QLinearGradient(r.topLeft(), r.bottomLeft())
        for pos, c in ((0, "#57565C"), (.18, "#2A292E"), (.7, "#111113"), (1, "#020203")):
            ch.setColorAt(pos, QColor(c))
        p.setBrush(ch)
        p.drawRoundedRect(r, 5, 5)
        face = r.adjusted(2, 2, -2, -3)
        tf = QLinearGradient(face.topLeft(), face.bottomLeft())
        tf.setColorAt(0, QColor("#1C1B20"))
        tf.setColorAt(1, QColor("#060607"))
        p.setBrush(tf)
        p.drawRoundedRect(face, 3.5, 3.5)
        p.setPen(QPen(QColor(255, 255, 255, 105), 1))
        p.drawLine(QPointF(face.left() + 3, face.top() + 0.5), QPointF(face.right() - 3, face.top() + 0.5))
        if hover:
            c = QColor(theme.GLOW)
            c.setAlphaF(0.8)
            p.setPen(QPen(c, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(r.adjusted(-0.5, -0.5, 0.5, 0.5), 5.5, 5.5)
        if self.isChecked():
            bar = QRectF(face.left() + 6, face.bottom() - 3, face.width() - 12, 2)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(theme.family_gradient(bar.left(), 0, bar.right(), 0))
            p.drawRoundedRect(bar, 1, 1)
        colour = QColor("#FFFFFF") if (hover or down or self.isChecked()) else QColor(theme.ON_DARK)
        if not self.isEnabled():
            colour = QColor(theme.TEXT_DIM)
        draw_icon(p, self.icon_name, QRectF(face.center().x() - 9, face.center().y() - 9.5, 18, 18), colour, 1.6)


class Toolbar(QWidget):
    """Notepad2's toolbar order: New Open Save | Undo Redo | Cut Copy Paste | Find Replace | Wrap |
    Zoom in, Zoom out | Scheme."""

    triggered = pyqtSignal(str)
    GROUPS = [[("new", "New (Ctrl+N)"), ("open", "Open (Ctrl+O)"), ("save", "Save (Ctrl+S)")],
              [("undo", "Undo (Ctrl+Z)"), ("redo", "Redo (Ctrl+Y)")],
              [("cut", "Cut (Ctrl+X)"), ("copy", "Copy (Ctrl+C)"), ("paste", "Paste (Ctrl+V)")],
              [("find", "Find (Ctrl+F)"), ("replace", "Replace (Ctrl+H)")],
              [("wrap", "Word Wrap (Ctrl+W)")],
              [("zoomin", "Zoom In (Ctrl++)"), ("zoomout", "Zoom Out (Ctrl+-)")],
              [("scheme", "Select Scheme (F12)")]]

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QHBoxLayout(self)
        lay.setContentsMargins(14, 7, 14, 7)
        lay.setSpacing(3)
        self.keys: dict[str, SmallKey] = {}
        for i, group in enumerate(self.GROUPS):
            if i:
                sep = QLabel()
                sep.setFixedSize(1, 24)
                sep.setStyleSheet(f"background: {theme.PANEL_EDGE};")
                lay.addSpacing(6)
                lay.addWidget(sep)
                lay.addSpacing(6)
            for name, tip in group:
                k = SmallKey(name, tip, checkable=(name == "wrap"))
                k.clicked.connect(lambda _=False, n=name: self.triggered.emit(n))
                self.keys[name] = k
                lay.addWidget(k)
        lay.addStretch(1)
        self.setStyleSheet(f"Toolbar {{ border-bottom: 1px solid {theme.PANEL_EDGE}; }}")
