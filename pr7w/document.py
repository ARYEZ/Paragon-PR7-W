"""Reading and writing text files the way Notepad2 does: encodings, byte-order marks, line endings.

Pure Python (no Qt), so it's tested directly. The rule: opening a file and saving it unchanged gives
back the very same bytes. Encodings and line endings change only when the user picks new ones.
"""

from __future__ import annotations

import codecs
import os
from dataclasses import dataclass
from pathlib import Path

# ----------------------------------------------------------------------------- encodings
def ansi_codec() -> str:
    """Windows' 'ANSI' code page (cp1252 on Western systems); cp1252 elsewhere."""
    if os.name == "nt":
        try:
            import ctypes
            return f"cp{ctypes.windll.kernel32.GetACP()}"
        except Exception:
            pass
    return "cp1252"


def _keep_bytes_decode(err: UnicodeDecodeError):
    # A byte the code page has no character for (cp1252: 81 8D 8F 90 9D) becomes U+0080..U+00FF ...
    b = err.object[err.start]
    return chr(b), err.start + 1


def _keep_bytes_encode(err: UnicodeEncodeError):
    # ... and goes back as the same byte on save, so such files survive a round trip.
    ch = err.object[err.start]
    if ord(ch) < 256:
        return bytes([ord(ch)]), err.start + 1
    raise err


def _keep_bytes(err):
    return _keep_bytes_decode(err) if isinstance(err, UnicodeDecodeError) else _keep_bytes_encode(err)


codecs.register_error("pr7w-keep", _keep_bytes)


@dataclass(frozen=True)
class Encoding:
    key: str          # our name, stored in settings
    label: str        # what the menu and status bar show (Notepad2's names)
    codec: str        # Python codec ('ansi' = the system code page)
    bom: bytes = b""


ENCODINGS = [
    Encoding("ansi", "ANSI", "ansi"),
    Encoding("utf-16le-bom", "Unicode", "utf-16-le", codecs.BOM_UTF16_LE),
    Encoding("utf-16be-bom", "Unicode Big Endian", "utf-16-be", codecs.BOM_UTF16_BE),
    Encoding("utf-8", "UTF-8", "utf-8"),
    Encoding("utf-8-bom", "UTF-8 with Signature", "utf-8", codecs.BOM_UTF8),
]
OTHER_ENCODINGS = [  # File > Encoding > Other (as Notepad2's Recode list, abridged to common ones)
    Encoding("cp1250", "Central European (Windows-1250)", "cp1250"),
    Encoding("cp1251", "Cyrillic (Windows-1251)", "cp1251"),
    Encoding("cp1252", "Western European (Windows-1252)", "cp1252"),
    Encoding("cp1253", "Greek (Windows-1253)", "cp1253"),
    Encoding("cp1254", "Turkish (Windows-1254)", "cp1254"),
    Encoding("cp1255", "Hebrew (Windows-1255)", "cp1255"),
    Encoding("cp1256", "Arabic (Windows-1256)", "cp1256"),
    Encoding("cp1257", "Baltic (Windows-1257)", "cp1257"),
    Encoding("cp1258", "Vietnamese (Windows-1258)", "cp1258"),
    Encoding("iso8859-1", "Western European (ISO 8859-1)", "iso8859-1"),
    Encoding("iso8859-2", "Central European (ISO 8859-2)", "iso8859-2"),
    Encoding("iso8859-15", "Latin 9 (ISO 8859-15)", "iso8859-15"),
    Encoding("koi8-r", "Cyrillic (KOI8-R)", "koi8-r"),
    Encoding("cp437", "OEM United States (437)", "cp437"),
    Encoding("cp850", "OEM Multilingual Latin 1 (850)", "cp850"),
    Encoding("shift_jis", "Japanese (Shift-JIS)", "shift_jis"),
    Encoding("gbk", "Chinese Simplified (GBK)", "gbk"),
    Encoding("big5", "Chinese Traditional (Big5)", "big5"),
    Encoding("euc-kr", "Korean (EUC-KR)", "euc-kr"),
]
BY_KEY = {e.key: e for e in ENCODINGS + OTHER_ENCODINGS}


def codec_of(enc: Encoding) -> str:
    return ansi_codec() if enc.codec == "ansi" else enc.codec


def detect_encoding(data: bytes) -> Encoding:
    if data.startswith(codecs.BOM_UTF8):
        return BY_KEY["utf-8-bom"]
    if data.startswith(codecs.BOM_UTF16_LE):
        return BY_KEY["utf-16le-bom"]
    if data.startswith(codecs.BOM_UTF16_BE):
        return BY_KEY["utf-16be-bom"]
    try:
        data.decode("utf-8")
        return BY_KEY["utf-8"]
    except UnicodeDecodeError:
        return BY_KEY["ansi"]


def decode(data: bytes, enc: Encoding) -> str:
    body = data[len(enc.bom):] if enc.bom and data.startswith(enc.bom) else data
    return body.decode(codec_of(enc), errors="pr7w-keep" if enc.codec not in ("utf-8", "utf-16-le", "utf-16-be")
                       else "replace")


def encode(text: str, enc: Encoding) -> bytes:
    """Bytes for saving. Raises UnicodeEncodeError for characters the encoding can't hold."""
    errors = "pr7w-keep" if enc.codec not in ("utf-8", "utf-16-le", "utf-16-be") else "strict"
    return enc.bom + text.encode(codec_of(enc), errors=errors)


def unencodable(text: str, enc: Encoding) -> list[str]:
    """The characters that would be lost saving in `enc` (Notepad2 warns before saving)."""
    if enc.codec in ("utf-8", "utf-16-le", "utf-16-be"):
        return []
    bad = []
    for ch in set(text):
        try:
            ch.encode(codec_of(enc), errors="pr7w-keep")
        except UnicodeEncodeError:
            bad.append(ch)
    return sorted(bad)


# ----------------------------------------------------------------------------- line endings
EOLS = {"crlf": ("CR+LF", "\r\n"), "lf": ("LF", "\n"), "cr": ("CR", "\r")}


def detect_eol(text: str, default: str = "crlf") -> str:
    """The most common line ending (CRLF counted before lone CR / LF)."""
    crlf = text.count("\r\n")
    cr = text.count("\r") - crlf
    lf = text.count("\n") - crlf
    counts = {"crlf": crlf, "lf": lf, "cr": cr}
    best = max(counts, key=lambda k: counts[k])
    return best if counts[best] else default


def mixed_eols(text: str) -> bool:
    crlf = text.count("\r\n")
    return sum(1 for n in (crlf, text.count("\r") - crlf, text.count("\n") - crlf) if n) > 1


def convert_eols(text: str, eol: str) -> str:
    return text.replace("\r\n", "\n").replace("\r", "\n").replace("\n", EOLS[eol][1])


# ----------------------------------------------------------------------------- files
@dataclass
class Loaded:
    text: str
    encoding: Encoding
    eol: str
    size: int


def load(path: str | Path, force: Encoding | None = None) -> Loaded:
    data = Path(path).read_bytes()
    enc = force or detect_encoding(data)
    text = decode(data, enc)
    return Loaded(text, enc, detect_eol(text, "crlf" if os.name == "nt" else "lf"), len(data))


def save(path: str | Path, text: str, enc: Encoding) -> int:
    """Write atomically (a temp file, then a rename), so a failed save never leaves a half file."""
    data = encode(text, enc)
    p = Path(path)
    if p.is_symlink():
        p = p.resolve()  # save into the file the link points to, keeping the link
    tmp = p.with_name(f".{p.name}.pr7w-save")
    tmp.write_bytes(data)
    try:
        if p.exists():
            import shutil
            shutil.copymode(p, tmp)
        os.replace(tmp, p)
    except OSError:
        tmp.unlink(missing_ok=True)
        raise
    return len(data)


def fmt_size(n: int) -> str:
    """Notepad2's status bar size: bytes, then KB / MB with two decimals."""
    if n < 1024:
        return f"{n} bytes"
    for unit in ("KB", "MB", "GB"):
        n /= 1024
        if n < 1024 or unit == "GB":
            return f"{n:.2f} {unit}"
    return ""
