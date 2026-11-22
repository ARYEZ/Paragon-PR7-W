"""Scheme choice by name, extension and #! line; every scheme builds and gets family colours."""

import pytest

from pr7w import schemes
from pr7w.editor import SYNTAX, role_of, style_lexer, editor_font


@pytest.mark.parametrize("path,expected", [
    ("engine.py", "Python Script"), ("C:/x/Makefile", "Makefiles"), ("CMakeLists.txt", "CMake"),
    ("a.CPP", "C/C++ Source Code"), ("index.html", "Web Source Code"), ("pr7z.iss", "Inno Setup Script"),
    ("setup.ps1", "PowerShell"), ("main.go", "Go Source Code"), ("lib.rs", "Rust Source Code"),
    ("notes.md", "Markdown"), (".gitignore", "Configuration Files"), (".bashrc", "Shell Script"),
    ("data.json", "JSON"), ("README", "Default Text"), ("x.unknownext", "Default Text"), ("run.bat", "Batch Files"),
    ("tune.reg", "Registry Files"), ("build.yml", "YAML Document"), ("a.vbs", "Visual Basic"),
])
def test_scheme_for_file(path, expected):
    assert schemes.for_file(path).name == expected


@pytest.mark.parametrize("line,expected", [
    ("#!/usr/bin/env python3", "Python Script"), ("#!/bin/bash", "Shell Script"), ("#! /usr/bin/perl -w", "Perl Script"),
    ("#!/usr/bin/env node", "JavaScript"), ("plain first line", "Default Text"),
])
def test_scheme_from_shebang(line, expected):
    assert schemes.for_file("script", line).name == expected


def test_every_scheme_builds_in_family_colours(qapp):
    from PyQt6.QtGui import QColor
    allowed = {QColor(c).name() for c, _, _ in SYNTAX.values()}
    for s in schemes.SCHEMES:
        lexer = schemes.make_lexer(s)
        if lexer is None:
            continue
        style_lexer(lexer, editor_font())
        for style in range(128):
            if lexer.description(style):
                assert lexer.color(style).name() in allowed, (s.name, style, lexer.description(style))


def test_family_hues_only():
    """No green, blue, purple, yellow or cyan: every syntax colour is a red/pink/orange hue or a grey."""
    from PyQt6.QtGui import QColor
    for name, (colour, _, _) in SYNTAX.items():
        c = QColor(colour)
        h, s = c.hslHue(), c.hslSaturationF()
        assert s < 0.25 or h == -1 or h >= 318 or h <= 42, (name, colour, h, s)


def test_roles():
    assert role_of("Comment") == "comment" and role_of("Double-quoted string") == "string"
    assert role_of("Keyword") == "keyword" and role_of("Class name") == "class"
    assert role_of("Function or method name") == "function" and role_of("Decorator") == "decorator"
    assert role_of("Unclosed string") == "error" and role_of("Number") == "number"
