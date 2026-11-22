"""Encodings and line endings: opening and saving unchanged gives back the same bytes."""

import codecs
import os

import pytest

from pr7w import document as d

SAMPLES = {
    "ascii crlf": b"hello\r\nworld\r\n",
    "utf-8 lf": "café – 日本\nüber\n".encode("utf-8"),
    "utf-8 bom": codecs.BOM_UTF8 + "naïve\r\n".encode("utf-8"),
    "utf-16 le": codecs.BOM_UTF16_LE + "été\r\nhiver\r\n".encode("utf-16-le"),
    "utf-16 be": codecs.BOM_UTF16_BE + "été\nhiver\n".encode("utf-16-be"),
    "ansi": "café € 5\r\n".encode("cp1252"),
    "ansi undefined bytes": b"a\x81b\x8dc\x8fd\x90e\x9df\r\n",   # bytes cp1252 has no character for
    "mixed eols": b"one\r\ntwo\nthree\rfour",
    "empty": b"",
}


@pytest.mark.parametrize("name", SAMPLES)
def test_round_trip_is_byte_exact(name, tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(SAMPLES[name])
    doc = d.load(p)
    d.save(p, doc.text, doc.encoding)
    assert p.read_bytes() == SAMPLES[name]


def test_detection():
    assert d.detect_encoding(SAMPLES["utf-8 bom"]).label == "UTF-8 with Signature"
    assert d.detect_encoding(SAMPLES["utf-16 le"]).label == "Unicode"
    assert d.detect_encoding(SAMPLES["utf-16 be"]).label == "Unicode Big Endian"
    assert d.detect_encoding(SAMPLES["utf-8 lf"]).label == "UTF-8"
    assert d.detect_encoding(SAMPLES["ansi"]).label == "ANSI"


def test_bom_not_in_text(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(SAMPLES["utf-8 bom"])
    assert d.load(p).text == "naïve\r\n"


def test_eol_detection_and_conversion():
    assert d.detect_eol("a\r\nb\r\nc\n") == "crlf"
    assert d.detect_eol("a\nb\n") == "lf"
    assert d.detect_eol("a\rb\r") == "cr"
    assert d.detect_eol("no newline", default="lf") == "lf"
    assert d.mixed_eols("a\r\nb\n") and not d.mixed_eols("a\nb\n")
    assert d.convert_eols("a\r\nb\nc\rd", "crlf") == "a\r\nb\r\nc\r\nd"
    assert d.convert_eols("a\r\nb\r\n", "lf") == "a\nb\n"


def test_change_encoding_on_save(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes("café\n".encode("utf-8"))
    doc = d.load(p)
    d.save(p, doc.text, d.BY_KEY["utf-16le-bom"])
    assert p.read_bytes() == codecs.BOM_UTF16_LE + "café\n".encode("utf-16-le")
    assert d.load(p).text == "café\n"


def test_unencodable_characters_are_reported():
    assert d.unencodable("café 日", d.BY_KEY["cp1252"]) == ["日"]
    assert d.unencodable("anything 日", d.BY_KEY["utf-8"]) == []
    with pytest.raises(UnicodeEncodeError):
        d.encode("日", d.BY_KEY["cp1252"])


def test_save_keeps_symlink(tmp_path):
    if os.name == "nt":
        pytest.skip("symlinks need privileges on Windows")
    target = tmp_path / "real.txt"
    target.write_text("old")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    d.save(link, "new", d.BY_KEY["utf-8"])
    assert link.is_symlink() and target.read_text() == "new"


def test_failed_save_leaves_the_file(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes(b"original")
    with pytest.raises(UnicodeEncodeError):
        d.save(p, "日", d.BY_KEY["cp1252"])
    assert p.read_bytes() == b"original"
    assert not list(tmp_path.glob(".*pr7w-save"))


def test_force_encoding(tmp_path):
    p = tmp_path / "f.txt"
    p.write_bytes("é".encode("cp1252"))
    assert d.load(p, force=d.BY_KEY["iso8859-1"]).text == "é"


def test_size_text():
    assert d.fmt_size(512) == "512 bytes"
    assert d.fmt_size(1106) == "1.08 KB"
    assert d.fmt_size(5 * 1024 * 1024) == "5.00 MB"
