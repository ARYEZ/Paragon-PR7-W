"""Notepad2's Lines / Block / Convert commands."""

from pr7w import textops as t


def test_sort():
    assert t.sort_lines("file10\nFile2\nfile1\n") == "file1\nFile2\nfile10\n"            # logical, ignore case
    assert t.sort_lines("b\na\nc", descending=True) == "c\nb\na"
    assert t.sort_lines("b\r\na\r\nb\r\n", remove_duplicates=True) == "a\r\nb\r\n"
    assert t.sort_lines("b\na\nb\n", remove_unique=True) == "b\nb\n"
    assert t.sort_lines("B\na\n", ignore_case=False, logical=False) == "B\na\n"
    assert sorted(t.sort_lines("1\n2\n3\n4\n", shuffle=True).split()) == ["1", "2", "3", "4"]


def test_duplicate_and_join():
    assert t.duplicate_lines("a\n") == "a\na\n"
    assert t.duplicate_lines("a\r\nb") == "a\r\nb\r\na\r\nb"
    assert t.join_lines_text("  one\n two \nthree\n") == "one two three\n"
    assert t.join_paragraphs("a\nb\n\nc\nd\n") == "a b\n\nc d\n"
    assert t.split_lines_at("one two three four", 9) == "one two\nthree\nfour"


def test_block():
    assert t.indent("a\n\nb\n") == "    a\n\n    b\n"
    assert t.unindent("    a\n\tb\n  c\n") == "a\nb\nc\n"
    assert t.pad_with_spaces("ab\na\n") == "ab\na \n"
    assert t.strip_first_char("ab\ncd\n") == "b\nd\n" and t.strip_last_char("ab\ncd\n") == "a\nc\n"
    assert t.strip_trailing_blanks("a  \t\nb \n") == "a\nb\n"
    assert t.compress_whitespace("  a   b\t\tc  \n") == "a b c\n"
    assert t.merge_blank_lines("a\n\n\n\nb\n") == "a\n\nb\n"
    assert t.remove_blank_lines("a\n\n \nb\n") == "a\nb\n"
    assert t.modify_lines("x\ny\n", "$(0L). ", ";") == "1. x;\n2. y;\n"
    assert t.enclose("x", "<b>", "</b>") == "<b>x</b>"


def test_line_comment_toggles_both_ways():
    code = "    if x:\n        y()\n\n    z()\n"
    on = t.toggle_line_comment(code, "#")
    assert on == "    # if x:\n    #     y()\n\n    # z()\n"
    assert t.toggle_line_comment(on, "#") == code
    assert t.toggle_line_comment("a\n", "//") == "// a\n"
    assert t.toggle_line_comment("REM a\r\n", "REM ") == "a\r\n"
    assert t.toggle_line_comment("x\n", "") == "x\n"


def test_stream_comment():
    assert t.toggle_stream_comment("x = 1", "/*", "*/") == "/* x = 1 */"
    assert t.toggle_stream_comment("/* x = 1 */", "/*", "*/") == "x = 1"


def test_convert():
    assert t.upper("aB") == "AB" and t.lower("aB") == "ab" and t.invert_case("aB") == "Ab"
    assert t.title_case("hello WORLD, it's me") == "Hello World, It's Me"
    assert t.sentence_case("HELLO. how ARE you?\nfine") == "Hello. How are you?\nFine"
    assert t.untabify("\ta\tb", 4) == "    a   b"
    assert t.tabify("        x", 4) == "\t\tx"
    assert t.untabify(t.tabify("    a   b", 4), 4) == "    a   b"
    assert t.url_decode(t.url_encode("a b/ü?")) == "a b/ü?" and t.url_encode("a b") == "a%20b"
    assert t.escape_c('a"\n\t\\') == 'a\\"\\n\\t\\\\' and t.unescape_c(t.escape_c('a"\n\t\\')) == 'a"\n\t\\'
    assert t.char_to_hex("A\u00e9\u65e5") == "\\x41\\xe9\\u65e5" and t.hex_to_char("\\x41\\xe9\\u65e5") == "A\u00e9\u65e5"
