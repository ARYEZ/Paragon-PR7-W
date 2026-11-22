# Paragon PR7-W

The Paragon family's text editor: it works the way **Notepad2** works (menus, toolbar, shortcuts,
status bar, schemes), built on the same editing engine, Scintilla (via QScintilla), in the family's
OBSIDIAN look (the PR7 plugins, Paragon Photo, Paragon PR7-Z). Personal use.

**Status: mock-up for approval** (`docs/mockup/`): the real window, nothing wired yet.

Syntax colours come from the family palette only (pink / red / orange hues, pearl and onyx greys) and
are chosen by each style's role, so every language gets the same scheme. The editor text uses a
monospaced font (Consolas, as Notepad2), the one exception to the family's Inter-only rule.

Render screenshots: `QT_SCALE_FACTOR=2 python tools/screenshots.py OUT_DIR`
