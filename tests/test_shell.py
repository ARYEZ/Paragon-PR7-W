"""Explorer integration (Windows; writes the registry, so CI machines only)."""

import os

import pytest

from pr7w import shell

pytestmark = pytest.mark.skipif(os.name != "nt" or not os.environ.get("CI"),
                                reason="writes Explorer's registration; Windows CI machines only")


def test_register_and_unregister():
    import winreg
    assert shell.run("--register") == 0
    try:
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\*\shell\{shell.VERB}\command")
        cmd, _ = winreg.QueryValueEx(k, "")
        assert cmd.endswith('"%1"') and "pr7w" in cmd.lower()
        k = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Classes\.py\OpenWithProgids")
        winreg.QueryValueEx(k, shell.PROGID)
        assert shell.menu_registered()
    finally:
        assert shell.run("--unregister") == 0
    assert not shell.menu_registered()
