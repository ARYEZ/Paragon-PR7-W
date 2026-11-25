# Paragon PR7-W: notes for Claude

**Paragon PR7-W** is the owner's personal text editor: Python (**PyQt6 + QScintilla**) that **works the way
Notepad2 works**, in the Paragon family look (the PR7 plugins, Paragon Photo, Paragon PR7-Z
`ARYEZ/Paragon-PR7-Z`). Windows 10/11 x64 is the target; it runs on Linux for tests. The owner writes
Python; explain the why of changes.

## How it's built

- **PyQt6, not PySide6** (QScintilla exists only for PyQt). The theme is PR7-Z's `theme.py` ported: PyQt6
  needs fully scoped enums (`QPalette.ColorRole.Window`, `Qt.AlignmentFlag.AlignCenter`). Don't load PySide6
  and PyQt6 in one process.
- `pr7w/document.py` (no Qt): encodings (Notepad2's names), BOMs, line endings, atomic saves. **Opening and
  saving unchanged must be byte-exact** (tests cover UTF-8/BOM/UTF-16/ANSI incl. cp1252's undefined bytes via
  the `pr7w-keep` error handler, mixed EOLs). Line endings are only normalised by File > Line Endings.
- `pr7w/schemes.py`: Notepad2's schemes on QScintilla lexers, chosen by file name, extension, `#!` line.
  Missing lexers use the closest one (Go/Rust: the C++ lexer with their keywords; INI/Registry/Inno:
  Properties; PowerShell: Bash) and say so in `note`.
- `pr7w/editor.py`: the Scintilla widget in family colours. `style_lexer` colours every style by its *role*
  (from the lexer's style description) from `SYNTAX`. Positions: Scintilla counts UTF-8 bytes, Python
  characters; use `char_to_pos` / `pos_to_char` (SCI_POSITIONRELATIVE / SCI_COUNTCHARACTERS).
- `pr7w/textops.py` (no Qt): Edit > Lines / Block / Convert as functions on text; the window applies them to
  the selected lines (`lines_op`) or selection (`selection_op`) as one undo step.
- `pr7w/main_window.py`: menus declared with `_act` (text, shortcut, slot, settings key); find/replace runs
  Python's `re` on `text()` and maps offsets, so Find and Replace All agree.
- `pr7w/shell.py`: "Edit with PR7-W" (a registry verb on `*`) and Open with, HKCU only.
- **Finishes:** `theme.set_finish("obsidian"|"aurora")` rebinds the module's colours (FINISHES), and
  `theme.syntax()` / `theme.editor_colours()` give the per-finish sets; things that stay dark in both (keys,
  menus, buttons, tooltips) use `theme.ON_DARK`. `MainWindow.set_finish` re-applies style sheet, palette and
  `Editor.apply_colours()`. With a lexer set, `QsciScintilla.paper()` doesn't report what's drawn: tests read
  `SCI_STYLEGETBACK`. Colour checks use chroma (HSL calls near-blacks saturated).
- `pr7w/printing.py`: `PagePrinter.formatPage` draws header/footer and shrinks the area; prints use AURORA's
  syntax set on white (`COLOUR_MODES`), then `apply_colours()` restores the screen.
- Customize Schemes: overrides `{"role:<role>"|"<scheme>:<style>": {fore, bold, italic, underline}}`, per finish,
  JSON in the `style_overrides` setting; `style_lexer(..., overrides=, scheme=)` applies them.
- `pr7w/notepad.py`: Notepad replacement = HKLM IFEO `notepad.exe` Debugger `"<PR7-W>" /z` in both registry
  views (admin; `run_elevated` re-runs PR7-W with "runas"); only PR7-W's own value is removed. `app._parse_notepad`
  reads Notepad's command line after `/z <notepad path>` (unquoted spaces, /p, /pt). Default apps: Capabilities +
  RegisteredApplications (shell.register_open_with); `ms-settings:defaultapps?registeredAppUser=Paragon%20PR7-W`.
- Installer `installer/pr7w.iss` (Inno Setup 6, per user, AppId {D8F51204-6E9E-4CB7-BF2E-58F4908B7937}
  permanent); CI installs it silently and runs `tools/verify_install.py installed|uninstalled`.

- Updates: `pr7w/updates.py` (no Qt; GitHub's public releases/latest, User-Agent names only the app, installer asset `PR7-W-Setup-*.exe`, run with /SILENT /relaunch=1) and `update_ui.py` (once-a-day check from app.py, the menu's Check for Updates, UpdateDialog; settings updates/auto|last|skip; `notify` for tests). The installer's [Code] Relaunch starts PR7-W again only for /relaunch=1. Same files in every family app (PR7-W's update_ui imports PyQt6): keep them in step. With PR7-U (the family installer) installed, update_ui offers it (`_family_app`, `open_family`; `answer` for tests); every app has the shared family.py with all ten AppIds.

- `pr7w/finish.py` (no Qt): the family's finish (OBSIDIAN / AURORA), one choice for every app: HKCU\Software\Paragon\Family "Finish" (a file elsewhere; PARAGON_FAMILY_FILE in tests, conftest). `finish.start` at start-up, `set_finish` saves it, app.py's 2 s timer `finish.follow`s another app's switch. The same file in every family app: keep them in step.

## The look (family rules)

- Colours: the family's only (hues ~318 -> 0 -> 42 deg, pearl and onyx greys), syntax colours included
  (`tests/test_schemes.py` checks every lexer style). Inter for the UI; the editor's monospaced font is the
  one exception. Labels UPPER CASE; file names keep their case.
- The PR7-W mark uses the PR7 `Logo.cpp` letter geometry plus a W (`widgets.W_SHAPE`); icon by
  `tools/make_icon.py`, wizard art by `tools/make_installer_art.py`. Check visuals with
  `QT_SCALE_FACTOR=2 python tools/screenshots.py OUT`.

## Rules

- Behaviour questions: do what Notepad2 does (menus, shortcuts, dialogs, defaults).
- Tests: `python -m pytest` (offscreen). Tests never write the real settings (conftest) or, outside CI, the registry.
- Releases: bump `__version__` in `pr7w/__init__.py` and add a `## x.y.z` section to CHANGELOG.md, then push:
  CI publishes that version by itself once every check has passed (the "Is this version released yet?"
  step; this session can't start workflows or push tags). Run workflow / `v*` tags still work.
