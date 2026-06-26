"""Application entry points for menu bar and other UI modes."""

import sys


def menubar():
    """Launch macOS menu bar app."""
    from zhixing.ui.menubar import run_menubar
    run_menubar()


def main():
    """Entry point: python -m zhixing.app menubar"""
    if len(sys.argv) > 1 and sys.argv[1] in ("menubar", "--menubar"):
        menubar()
    else:
        print("用法: python -m zhixing.app menubar")
        print("  menubar      启动菜单栏应用")


if __name__ == "__main__":
    main()
