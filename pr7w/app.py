"""Starting PR7-W.

    pr7w [FILE] [/g LINE[,COL]]      open FILE (at a line, Notepad2's /g); -g works too
    pr7w --register | --unregister   "Edit with PR7-W" on Explorer's menu and "Open with" (this user only)
    pr7w --version
"""

from __future__ import annotations

import sys
from pathlib import Path


def parse(argv: list[str]) -> tuple[str | None, str | None, tuple[int, int] | None]:
    """(action, file, (line, col)) from the command line."""
    action, path, goto = None, None, None
    it = iter(argv)
    for a in it:
        if a in ("--register", "--unregister", "--register-menu", "--unregister-menu", "--register-open-with",
                 "--unregister-open-with", "--version", "--help"):
            action = a
        elif a.lower() in ("/g", "-g"):
            spec = next(it, "")
            parts = [p for p in spec.replace(";", ",").split(",") if p.strip()]
            try:
                goto = (int(parts[0]), int(parts[1]) if len(parts) > 1 else 1)
            except (ValueError, IndexError):
                raise SystemExit(f"/g needs a line number, e.g. /g 120 or /g 120,8 (got '{spec}').")
        elif a.startswith(("--", "/")) and not Path(a).exists():
            raise SystemExit(f"Unknown option {a}. See pr7w --help.")
        else:
            path = a
    return action, path, goto


def main(argv: list[str] | None = None) -> int:
    from . import __version__
    action, path, goto = parse(list(sys.argv[1:] if argv is None else argv))
    if action == "--help":
        print(__doc__)
        return 0
    if action == "--version":
        print(f"PR7-W {__version__}")
        return 0
    if action:
        from . import shell
        return shell.run(action)
    from PyQt6.QtGui import QIcon
    from PyQt6.QtWidgets import QApplication
    from . import theme
    QApplication.setApplicationName("PR7-W")
    QApplication.setOrganizationName("Paragon")
    app = QApplication.instance() or QApplication([sys.argv[0]])
    theme.load_fonts()
    app.setPalette(theme.palette())
    app.setStyleSheet(theme.stylesheet())
    ico = Path(__file__).parent / "icons" / "app.ico"
    if ico.exists():
        app.setWindowIcon(QIcon(str(ico)))
    from .main_window import MainWindow
    w = MainWindow(path, goto)
    w.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
