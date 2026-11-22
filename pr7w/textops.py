"""Notepad2's Edit > Lines / Block / Convert commands, as plain functions on text.

Line commands take the text of whole lines (with their line endings) and return the new text; the
window applies them to the selected lines (or the whole document) as one undo step.
"""

from __future__ import annotations

import random
import re
import urllib.parse

_EOL = re.compile(r"(\r\n|\r|\n)")


def split_lines(text: str) -> tuple[list[str], list[str]]:
    """Lines and the ending after each ('' for a last line without one)."""
    parts = _EOL.split(text)
    lines, ends = parts[0::2], parts[1::2] + [""]
    if lines and lines[-1] == "" and ends[-1] == "" and len(lines) > 1:
        lines.pop()
        ends.pop()
    return lines, ends


def _map_lines(text: str, f) -> str:
    lines, ends = split_lines(text)
    return "".join(f(ln) + ends[i] for i, ln in enumerate(lines))


def _uniform_eol(ends: list[str]) -> str:
    return next((e for e in ends if e), "\n")


# ----------------------------------------------------------------------------- Lines
def _natural_key(s: str):
    return [int(t) if t.isdigit() else t for t in re.split(r"(\d+)", s)]


def sort_lines(text: str, descending=False, ignore_case=True, logical=True, shuffle=False,
               remove_duplicates=False, remove_unique=False) -> str:
    """Notepad2's Sort Lines dialog. 'Logical' compares numbers as numbers (file2 before file10)."""
    lines, ends = split_lines(text)
    eol, last_end = _uniform_eol(ends), ends[-1] if ends else ""
    if shuffle:
        random.shuffle(lines)
    else:
        def key(s):
            k = s.casefold() if ignore_case else s
            return _natural_key(k) if logical else k
        lines.sort(key=key, reverse=descending)
    if remove_duplicates or remove_unique:
        norm = (lambda s: s.casefold()) if ignore_case else (lambda s: s)
        counts: dict = {}
        for ln in lines:
            counts[norm(ln)] = counts.get(norm(ln), 0) + 1
        seen = set()
        kept = []
        for ln in lines:
            n = norm(ln)
            if remove_unique and counts[n] == 1:
                continue
            if remove_duplicates:
                if n in seen:
                    continue
                seen.add(n)
            kept.append(ln)
        lines = kept
    return eol.join(lines) + last_end


def duplicate_lines(text: str) -> str:
    """Duplicate Line (Ctrl+D): the lines again, right below."""
    _, ends = split_lines(text)
    return text + text if ends[-1] else text + _uniform_eol(ends) + text


def join_lines_text(text: str) -> str:
    """Join Lines (Ctrl+J): the selected lines into one, separated by single spaces."""
    lines, ends = split_lines(text)
    return " ".join(ln.strip() for ln in lines if ln.strip()) + ends[-1]


def join_paragraphs(text: str) -> str:
    """Join Paragraphs: lines within each paragraph joined; blank lines between them kept."""
    lines, ends = split_lines(text)
    eol = _uniform_eol(ends)
    paras, cur = [], []
    for ln in lines:
        if ln.strip():
            cur.append(ln.strip())
        else:
            if cur:
                paras.append(" ".join(cur))
                cur = []
            paras.append("")
    if cur:
        paras.append(" ".join(cur))
    return eol.join(paras) + ends[-1]


def split_lines_at(text: str, width: int) -> str:
    """Split Lines (Ctrl+I): rewrap each paragraph to `width` columns at spaces."""
    import textwrap
    lines, ends = split_lines(text)
    eol = _uniform_eol(ends)
    out = []
    for ln in lines:
        out += textwrap.wrap(ln, width, break_long_words=False, break_on_hyphens=False) or [""]
    return eol.join(out) + ends[-1]


# ----------------------------------------------------------------------------- Block
def indent(text: str, unit: str = "    ") -> str:
    return _map_lines(text, lambda ln: unit + ln if ln.strip() else ln)


def unindent(text: str, tab_width: int = 4) -> str:
    def f(ln):
        if ln.startswith("\t"):
            return ln[1:]
        n = len(ln) - len(ln.lstrip(" "))
        return ln[min(n, tab_width):]
    return _map_lines(text, f)


def pad_with_spaces(text: str) -> str:
    lines, ends = split_lines(text)
    w = max((len(ln) for ln in lines), default=0)
    return "".join(ln.ljust(w) + ends[i] for i, ln in enumerate(lines))


def strip_first_char(text: str) -> str:
    return _map_lines(text, lambda ln: ln[1:])


def strip_last_char(text: str) -> str:
    return _map_lines(text, lambda ln: ln[:-1])


def strip_trailing_blanks(text: str) -> str:
    return _map_lines(text, lambda ln: ln.rstrip(" \t"))


def compress_whitespace(text: str) -> str:
    return _map_lines(text, lambda ln: re.sub(r"[ \t]+", " ", ln).strip(" "))


def merge_blank_lines(text: str) -> str:
    lines, ends = split_lines(text)
    out_l, out_e = [], []
    for ln, e in zip(lines, ends):
        if not ln.strip() and out_l and not out_l[-1].strip():
            continue
        out_l.append(ln)
        out_e.append(e)
    return "".join(a + b for a, b in zip(out_l, out_e))


def remove_blank_lines(text: str) -> str:
    lines, ends = split_lines(text)
    return "".join(ln + e for ln, e in zip(lines, ends) if ln.strip())


def modify_lines(text: str, prefix: str = "", suffix: str = "") -> str:
    """Modify Lines (Alt+M): text added before and after every line. $(L) is the line number
    (1-based) and $(0L) the same zero-padded, as in Notepad2."""
    lines, ends = split_lines(text)
    width = len(str(len(lines)))

    def fill(s, n):
        return s.replace("$(L)", str(n)).replace("$(0L)", str(n).zfill(width))
    return "".join(fill(prefix, i + 1) + ln + fill(suffix, i + 1) + ends[i] for i, ln in enumerate(lines))


def enclose(text: str, before: str, after: str) -> str:
    return before + text + after


def toggle_line_comment(text: str, token: str) -> str:
    """Toggle Line Comment (Ctrl+Q): if every non-blank line starts with the token (after its
    indentation), remove it; else add it at the lines' common indentation."""
    if not token:
        return text
    lines, ends = split_lines(text)
    body = [ln for ln in lines if ln.strip()]
    tok = token.rstrip()
    if body and all(ln.lstrip().startswith(tok) for ln in body):
        def off(ln):
            if not ln.strip():
                return ln
            lead = ln[:len(ln) - len(ln.lstrip())]
            rest = ln.lstrip()[len(tok):]
            if rest.startswith(" "):  # the space added after the token when commenting
                rest = rest[1:]
            return lead + rest
        return "".join(off(ln) + ends[i] for i, ln in enumerate(lines))
    col = min((len(ln) - len(ln.lstrip()) for ln in body), default=0)
    space = "" if token.endswith(" ") else " "
    return "".join((ln[:col] + token + space + ln[col:] if ln.strip() else ln) + ends[i]
                   for i, ln in enumerate(lines))


def toggle_stream_comment(text: str, start: str, end: str) -> str:
    if not start:
        return text
    s = text.strip()
    if s.startswith(start) and s.endswith(end):
        lead = text[:len(text) - len(text.lstrip())]
        trail = text[len(text.rstrip()):]
        inner = s[len(start):len(s) - len(end)]
        return lead + inner.strip(" ") + trail if inner.startswith(" ") else lead + inner + trail
    return start + " " + text + " " + end


# ----------------------------------------------------------------------------- Convert
def upper(text: str) -> str:
    return text.upper()


def lower(text: str) -> str:
    return text.lower()


def invert_case(text: str) -> str:
    return text.swapcase()


def title_case(text: str) -> str:
    return re.sub(r"[^\W_]+('[^\W_]+)?", lambda m: m.group(0)[:1].upper() + m.group(0)[1:].lower(), text)


def sentence_case(text: str) -> str:
    out, start = [], True
    for ch in text.lower():
        if start and ch.isalpha():
            out.append(ch.upper())
            start = False
        else:
            out.append(ch)
        if ch in ".!?\r\n":
            start = True
    return "".join(out)


def untabify(text: str, tab_width: int = 4) -> str:
    return _map_lines(text, lambda ln: ln.expandtabs(tab_width))


def tabify(text: str, tab_width: int = 4) -> str:
    """Leading and inner runs of spaces that reach a tab stop become tabs."""
    def f(ln):
        out, col, spaces = [], 0, 0
        for ch in ln:
            if ch == " ":
                spaces += 1
                col += 1
                if col % tab_width == 0:
                    out.append("\t" if spaces > 1 else " ")
                    spaces = 0
                continue
            out.append(" " * spaces)
            spaces = 0
            out.append(ch)
            col = col + tab_width - col % tab_width if ch == "\t" else col + 1
        out.append(" " * spaces)
        return "".join(out)
    return _map_lines(text, f)


def url_encode(text: str) -> str:
    return urllib.parse.quote(text, safe="")


def url_decode(text: str) -> str:
    return urllib.parse.unquote(text)


C_ESCAPES = {"\\": "\\\\", "\"": "\\\"", "'": "\\'", "\n": "\\n", "\r": "\\r", "\t": "\\t", "\a": "\\a", "\b": "\\b",
             "\f": "\\f", "\v": "\\v", "\0": "\\0"}


def escape_c(text: str) -> str:
    return "".join(C_ESCAPES.get(ch, ch) for ch in text)


def unescape_c(text: str) -> str:
    rev = {v[1]: k for k, v in C_ESCAPES.items()}
    out, i = [], 0
    while i < len(text):
        if text[i] == "\\" and i + 1 < len(text) and text[i + 1] in rev:
            out.append(rev[text[i + 1]])
            i += 2
        else:
            out.append(text[i])
            i += 1
    return "".join(out)


def char_to_hex(text: str) -> str:
    """Char to Hex: each character as \\xHH (or \\uHHHH beyond 0xFF)."""
    return "".join(f"\\x{ord(c):02x}" if ord(c) < 256 else f"\\u{ord(c):04x}" for c in text)


def hex_to_char(text: str) -> str:
    return re.sub(r"\\x([0-9a-fA-F]{2})|\\u([0-9a-fA-F]{4})",
                  lambda m: chr(int(m.group(1) or m.group(2), 16)), text)
