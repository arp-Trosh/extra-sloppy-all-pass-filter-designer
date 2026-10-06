# SPDX-License-Identifier: GPL-3.0-only
"""GUI entry point: ``esapf-gui`` or ``python -m esapf.gui``."""

import sys

from PySide6.QtWidgets import QApplication

from esapf.gui.main_window import MainWindow


def main() -> int:
    app = QApplication.instance() or QApplication(sys.argv)
    app.setApplicationName("Extra Sloppy All Pass Filter Designer")
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
