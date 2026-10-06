# SPDX-License-Identifier: GPL-3.0-only
"""GUI entry point: ``esapf-gui`` or ``python -m esapf.gui``.

``esapf-gui --self-test`` starts the window offscreen, presses Design with the default
inputs, checks the result and exits with status 0 (used by CI on the built executables).
"""

import os
import sys
from importlib.resources import files

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from esapf.gui.main_window import MainWindow

# Default design (270-3600 Hz, n = 3, C = 10 nF) as displayed by the original program.
SELF_TEST_EXPECTED = ["174.456750", "23.106614", "5.170433"]


def self_test(window: MainWindow) -> int:
    window.state.design()
    window.refresh()
    shown = [w.text() for w in window.cells["R1"][:3]]
    image = window.grab()
    ok = shown == SELF_TEST_EXPECTED and not image.isNull() and window.state.network is not None
    print(f"self-test {'passed' if ok else 'FAILED'}: R1 = {shown}")
    return 0 if ok else 1


def main() -> int:
    testing = "--self-test" in sys.argv
    if testing:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    app.setApplicationName("Extra Sloppy All Pass Filter Designer")
    app.setWindowIcon(QIcon(str(files("esapf.gui") / "icon.png")))
    window = MainWindow()
    if testing:
        return self_test(window)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
