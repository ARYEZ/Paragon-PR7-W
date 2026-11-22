# Paragon PR7-W

The Paragon family's text editor: it works the way **Notepad2** works (menus, toolbar, shortcuts,
status bar, schemes), on the same editing engine (Scintilla, via QScintilla), in the family's OBSIDIAN
look (the PR7 plugins, Paragon Photo, Paragon PR7-Z). Personal use.

## Install (Windows 10/11, x64)

Run **`PR7-W-Setup-<version>.exe`** (repo Releases, or the latest build's *PR7-W-Setup* artifact under
Actions). It installs for your user (no admin rights) into `%LOCALAPPDATA%\Programs\PR7-W`, adds it to
the Start menu and, ticked by default, puts **"Edit with PR7-W"** on Explorer's right-click menu
(Windows 11: under "Show more options") and PR7-W under **"Open with"** for text and source files.
Uninstall from Settings > Apps > Installed apps.

## Use

Notepad2's shortcuts throughout: Ctrl+F / F3 / Shift+F3 find, Ctrl+H replace, Ctrl+G go to, F12 scheme,
Ctrl+W word wrap, Ctrl+Q toggle comment, Ctrl+D duplicate line, Ctrl+Shift+Up/Down move lines, Alt+O
sort lines, Alt+M modify lines, Ctrl+Shift+U / Ctrl+U case, Ctrl+K swap with clipboard, Alt+T always on
top, Alt+Shift+T transparent. `PR7-W.exe file.txt /g 120,8` opens at line 120, column 8.

Syntax colours come from the family palette only (pink / red / orange hues, pearl and onyx greys),
chosen by each style's role so every language gets the same scheme. The editor text is monospaced
(Consolas, as Notepad2): the one exception to the family's Inter-only rule.

## Run from source

```bash
pip install -r requirements.txt
python -m pr7w notes.txt
```

Tests: `pip install -r requirements-dev.txt` then `python -m pytest`. Build: `pyinstaller pr7w.spec`, then
`iscc /DAppVersion=x.y.z installer\pr7w.iss`. CI does both on every push and tests the installer.
