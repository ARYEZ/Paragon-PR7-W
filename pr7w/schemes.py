"""Notepad2's syntax schemes, mapped onto QScintilla's lexers, and picking one for a file.

Each scheme carries its comment syntax too (Edit > Block > Toggle Comment uses it). Where
QScintilla has no lexer for a language, the closest one stands in (noted per scheme).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from PyQt6 import Qsci


def _cpp_with(keywords: str) -> Callable:
    """A C-like language on the C/C++ lexer with its own keywords (Go, Rust)."""
    class Lexer(Qsci.QsciLexerCPP):
        def keywords(self, kw_set):
            return keywords if kw_set == 1 else super().keywords(kw_set)
    return Lexer


GO_KEYWORDS = ("break case chan const continue default defer else fallthrough for func go goto if import "
               "interface map package range return select struct switch type var true false nil iota "
               "bool byte complex64 complex128 error float32 float64 int int8 int16 int32 int64 rune string "
               "uint uint8 uint16 uint32 uint64 uintptr any append cap close copy delete len make new panic "
               "print println recover")
RUST_KEYWORDS = ("as async await break const continue crate dyn else enum extern false fn for if impl in let loop "
                 "match mod move mut pub ref return self Self static struct super trait true type unsafe use where "
                 "while bool char str i8 i16 i32 i64 i128 isize u8 u16 u32 u64 u128 usize f32 f64 String Vec "
                 "Option Some None Result Ok Err Box")


@dataclass
class Scheme:
    name: str
    lexer: Callable | None                 # a QsciLexer class, or None for plain text
    exts: tuple = ()
    files: tuple = ()                      # exact file names (lower case)
    line_comment: str = ""
    block_comment: tuple = ()              # (start, end)
    shebang: tuple = ()                    # interpreter names in a #! line
    note: str = ""


SCHEMES = [
    Scheme("Default Text", None, ("txt", "text", "log", "nfo", "diz", "1st"), ("readme", "license", "copying")),
    Scheme("Web Source Code", Qsci.QsciLexerHTML, ("html", "htm", "xhtml", "shtml", "asp", "aspx", "php", "jsp",
                                                   "vue", "svelte"), block_comment=("<!--", "-->")),
    Scheme("XML Document", Qsci.QsciLexerXML, ("xml", "xsl", "xslt", "xsd", "svg", "xaml", "rss", "plist",
                                               "vcxproj", "csproj", "props", "targets", "resx", "wsdl", "kml", "gpx"),
           block_comment=("<!--", "-->")),
    Scheme("CSS Style Sheets", Qsci.QsciLexerCSS, ("css", "scss", "less"), block_comment=("/*", "*/")),
    Scheme("C/C++ Source Code", Qsci.QsciLexerCPP, ("c", "h", "cpp", "cxx", "cc", "hpp", "hxx", "hh", "inl", "ino",
                                                    "m", "mm"), line_comment="//", block_comment=("/*", "*/")),
    Scheme("C# Source Code", Qsci.QsciLexerCSharp, ("cs",), line_comment="//", block_comment=("/*", "*/")),
    Scheme("Java Source Code", Qsci.QsciLexerJava, ("java", "kt", "kts", "groovy", "gradle"), line_comment="//",
           block_comment=("/*", "*/")),
    Scheme("JavaScript", Qsci.QsciLexerJavaScript, ("js", "mjs", "cjs", "jsx", "ts", "tsx"), line_comment="//",
           block_comment=("/*", "*/"), shebang=("node", "deno")),
    Scheme("JSON", Qsci.QsciLexerJSON, ("json", "jsonc", "json5", "geojson", "webmanifest")),
    Scheme("Go Source Code", _cpp_with(GO_KEYWORDS), ("go",), line_comment="//", block_comment=("/*", "*/"),
           note="C/C++ lexer with Go keywords"),
    Scheme("Rust Source Code", _cpp_with(RUST_KEYWORDS), ("rs",), line_comment="//", block_comment=("/*", "*/"),
           note="C/C++ lexer with Rust keywords"),
    Scheme("Python Script", Qsci.QsciLexerPython, ("py", "pyw", "pyi", "pyx", "spec", "bzl"), ("sconstruct",),
           line_comment="#", shebang=("python", "python3", "python2")),
    Scheme("Ruby Script", Qsci.QsciLexerRuby, ("rb", "rbw", "rake", "gemspec"), ("gemfile", "rakefile"),
           line_comment="#", shebang=("ruby",)),
    Scheme("Perl Script", Qsci.QsciLexerPerl, ("pl", "pm", "t", "cgi"), line_comment="#", shebang=("perl",)),
    Scheme("Lua Script", Qsci.QsciLexerLua, ("lua",), line_comment="--", block_comment=("--[[", "]]"),
           shebang=("lua",)),
    Scheme("Tcl Script", Qsci.QsciLexerTCL, ("tcl", "tk"), line_comment="#", shebang=("tclsh", "wish")),
    Scheme("Shell Script", Qsci.QsciLexerBash, ("sh", "bash", "zsh", "ksh", "fish"),
           (".bashrc", ".bash_profile", ".profile", ".zshrc", "pkgbuild"), line_comment="#",
           shebang=("sh", "bash", "zsh", "ksh", "dash")),
    Scheme("PowerShell", Qsci.QsciLexerBash, ("ps1", "psm1", "psd1"), line_comment="#", block_comment=("<#", "#>"),
           shebang=("pwsh",), note="Bash lexer (comments, $variables, strings)"),
    Scheme("Batch Files", Qsci.QsciLexerBatch, ("bat", "cmd", "nt"), line_comment="REM "),
    Scheme("Makefiles", Qsci.QsciLexerMakefile, ("mak", "mk"), ("makefile", "gnumakefile", "bsdmakefile"),
           line_comment="#"),
    Scheme("CMake", Qsci.QsciLexerCMake, ("cmake",), ("cmakelists.txt",), line_comment="#"),
    Scheme("Diff Files", Qsci.QsciLexerDiff, ("diff", "patch", "rej")),
    Scheme("SQL Query", Qsci.QsciLexerSQL, ("sql", "ddl", "dml"), line_comment="--", block_comment=("/*", "*/")),
    Scheme("Pascal Source Code", Qsci.QsciLexerPascal, ("pas", "dpr", "dpk", "pp", "inc", "lpr"), line_comment="//",
           block_comment=("{", "}")),
    Scheme("Assembly Script", Qsci.QsciLexerMASM, ("asm", "s", "masm"), line_comment=";"),
    Scheme("NASM Assembly", Qsci.QsciLexerNASM, ("nasm",), line_comment=";"),
    Scheme("Configuration Files", Qsci.QsciLexerProperties, ("ini", "inf", "cfg", "conf", "properties", "editorconfig",
                                                             "gitconfig", "toml", "desktop"),
           (".gitattributes", ".gitignore", ".gitmodules"), line_comment=";", note="Properties lexer"),
    Scheme("Registry Files", Qsci.QsciLexerProperties, ("reg",), line_comment=";", note="Properties lexer"),
    Scheme("Inno Setup Script", Qsci.QsciLexerProperties, ("iss", "isl"), line_comment=";",
           note="Properties lexer"),
    Scheme("YAML Document", Qsci.QsciLexerYAML, ("yaml", "yml"), line_comment="#"),
    Scheme("Markdown", Qsci.QsciLexerMarkdown, ("md", "markdown", "mdown", "mkd")),
    Scheme("LaTeX Files", Qsci.QsciLexerTeX, ("tex", "sty", "cls", "bib"), line_comment="%"),
    Scheme("Visual Basic", None, ("vb", "vbs", "bas", "frm", "cls_vb", "vba"), line_comment="'",
           note="plain text with VB comments (no VB lexer in QScintilla)"),
    Scheme("D Source Code", Qsci.QsciLexerD, ("d", "di"), line_comment="//", block_comment=("/*", "*/")),
    Scheme("Fortran Source Code", Qsci.QsciLexerFortran, ("f90", "f95", "f03", "f08", "for", "f"), line_comment="!"),
    Scheme("MATLAB", Qsci.QsciLexerMatlab, ("matlab",), line_comment="%"),
    Scheme("Verilog", Qsci.QsciLexerVerilog, ("v", "vh", "sv", "svh"), line_comment="//", block_comment=("/*", "*/")),
    Scheme("VHDL", Qsci.QsciLexerVHDL, ("vhd", "vhdl"), line_comment="--"),
    Scheme("PostScript", Qsci.QsciLexerPostScript, ("ps", "eps"), line_comment="%"),
    Scheme("CoffeeScript", Qsci.QsciLexerCoffeeScript, ("coffee",), line_comment="#"),
    Scheme("Gettext Catalog", Qsci.QsciLexerPO, ("po", "pot"), line_comment="#"),
]
BY_NAME = {s.name: s for s in SCHEMES}
DEFAULT = SCHEMES[0]


def for_file(path: str | None, first_line: str = "") -> Scheme:
    """Notepad2's choice: an exact file name, then the extension, then a #! line, else Default Text."""
    if path:
        name = Path(path).name.lower()
        for s in SCHEMES:
            if name in s.files:
                return s
        ext = name.rsplit(".", 1)[-1] if "." in name.lstrip(".") else ""
        if not ext and name.startswith(".") and name.count(".") == 1:
            ext = name[1:]
        for s in SCHEMES:
            if ext and ext in s.exts:
                return s
    interp = shebang_program(first_line)
    if interp:
        for s in SCHEMES:
            if interp in s.shebang:
                return s
    return DEFAULT


def shebang_program(line: str) -> str:
    """'#!/usr/bin/env python3' -> 'python'; '#! /usr/bin/perl -w' -> 'perl'; else ''."""
    if not line or not line.startswith("#!"):
        return ""
    words = line[2:].split()
    if not words:
        return ""
    prog = words[0].replace("\\", "/").rsplit("/", 1)[-1]
    if prog == "env":
        rest = [w for w in words[1:] if not w.startswith("-") and "=" not in w]
        prog = rest[0] if rest else ""
    return re.sub(r"[\d.]+$", "", prog) or prog


def make_lexer(scheme: Scheme, parent=None):
    return scheme.lexer(parent) if scheme.lexer else None
