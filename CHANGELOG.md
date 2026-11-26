# Changelog

## 0.5.3

- The family list (`family.py`) knows the three newest Paragon apps: PR7-HW (hardware information), PR7-BK
  (backups) and PR7-TM (terminal), so links between the apps and the PR7-U offer find them.

## 0.5.2

- The family list (`family.py`) knows the four newest Paragon apps: PR7-HX (hex editor), PR7-DB (SQLite browser),
  PR7-UN (uninstaller) and PR7-LN (launcher), so links between the apps and the PR7-U offer find them.

## 0.5.1

- The family's list knows the newest apps (PR7-HB, PR7-FS, PR7-AR, PR7-WM), so links between apps and Check for Updates find them.

## 0.5.0

- **One finish for the whole family.** Choosing OBSIDIAN or AURORA here switches every Paragon app, open ones included (within a couple of seconds), and every app starts in the family's choice.
- In AURORA, group titles and selected rows are dark and readable (they were white on the light finish).

## 0.4.1

- Knows the whole family: PR7-DU, PR7-CB, PR7-IS, PR7-PM and PR7-SM are in its list of family apps (their permanent install IDs), so the family links find them when they're installed.

## 0.4.0

- **Check for Updates knows PR7-U**, the family installer. When it's installed, the update window has **Update All in PR7-U**, and a check by hand that finds PR7-W up to date offers to open PR7-U for the rest of the family.

## 0.3.0

- **Check for updates**: a few seconds after starting (at most once a day) PR7-W asks GitHub whether a newer release is out; if so, a note offers What's new, Install Now (downloads with progress, installs over this copy, and PR7-W reopens), Later or Skip This Version. "? > Check for Updates" checks by hand. Only the app's name is sent.

## 0.2.0

- Replace Windows Notepad (Settings, and a ticked installer task): notepad.exe starts PR7-W instead
  (Windows' Image File Execution Options redirect, both registry views; administrator permission, one
  UAC prompt). Notepad's command line is understood after Windows' `/z` hand-off, including unquoted
  names with spaces and `/p` / `/pt` (print and exit). Uninstalling restores Notepad; another program's
  redirect is never touched.
- Default text editor: PR7-W registers with Windows (RegisteredApplications, Capabilities) for its 162
  file types; Settings > Default Text Editor... opens Windows' Default apps page for it.
- Printing: Page Setup (colour mode: colour on white / black on white / screen colours; zoom; header
  and footer; paper and margins) and Print (Ctrl+P, Selection). Header: file name and date; footer: page
  number. On paper the text uses darker shades of the family hues.
- Customize Schemes (Ctrl+F12): colour (family swatches), bold, italic, underline for a role in every
  scheme or one style of one scheme; live preview, Cancel undoes; saved per finish.
- AURORA, the light finish (View > Finish): warm pearl dimmed 10%, ink lettering, black keys and menus;
  dark-on-pearl syntax colours. Dialog headers show the current finish.

## 0.1.0

First version.

- Notepad2's window in the Paragon OBSIDIAN look: menus (File, Edit, View, Settings, ?), toolbar, editor
  (Scintilla via QScintilla) with line numbers, bookmark margin and code folding, status bar
  (Ln : lines, Col, Sel, size, encoding, line endings, INS/OVR, scheme).
- Files: open, save, save as, save copy, revert, recent files, drag and drop, save prompts, reload
  when changed by another program (ask / automatic / off). Encodings as Notepad2 (ANSI, Unicode,
  Unicode Big Endian, UTF-8, UTF-8 with Signature, others) and Recode; line endings CR+LF / LF / CR;
  opening and saving unchanged is byte-exact; a warning before saving characters the encoding can't hold.
- 40 syntax schemes chosen by file name, extension or #! line (F12 to pick, Shift+F12 for plain text),
  all in one family colour scheme.
- Find / Replace (regex, whole word, case, transform backslashes, wrap, in selection), Go To.
- Edit > Lines / Block / Convert / Insert: move, duplicate, cut / copy / delete line, split, join, join
  paragraphs, sort (logical, case, duplicates, unique, shuffle), indent, enclose, pad, strip, compress,
  merge / remove blank lines, modify lines, line and stream comments, case conversions, tabify /
  untabify, URL and C escapes, hex, HTML/XML tag, date/time, file name, GUID.
- View and Settings toggles (word wrap, long line marker, guides, whitespace, line endings, wrap
  symbols, braces, current line, margins, folding, toolbar, header, status bar, zoom, font, tabs,
  auto indent, auto close HTML/XML, always on top, transparent mode), saved between sessions.
- Explorer: "Edit with PR7-W" and "Open with" (per user). Installer (Inno Setup, per user) and CI.
