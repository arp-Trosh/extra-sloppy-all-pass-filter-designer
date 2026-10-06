# SPDX-License-Identifier: GPL-3.0-only
"""GUI entry point: ``esapf-gui`` or ``python -m esapf.gui``.

``esapf-gui --bill`` starts in Bill Mode (the practical window); Ctrl+B switches between
the two windows. ``esapf-gui --self-test`` starts the windows offscreen, presses Design with
the default inputs, checks the result and exits with status 0 (used by CI on the built
executables).
"""

import os
import sys
from importlib.resources import files

from PySide6.QtGui import QIcon, QKeySequence, QShortcut
from PySide6.QtWidgets import QApplication

from esapf.gui.bill_window import BillWindow
from esapf.gui.main_window import MainWindow

# Default design (270-3600 Hz, n = 3, C = 10 nF) as displayed by the original program.
SELF_TEST_EXPECTED = ["174.456750", "23.106614", "5.170433"]
BILL_SELF_TEST_EXPECTED = ["174456.79", "23106.62", "5170.43"]  # exact design (U8)
SWITCH_KEY = "Ctrl+B"


def self_test(window: MainWindow, bill: BillWindow) -> int:
    window.state.design()
    window.refresh()
    shown = [w.text() for w in window.cells["R1"][:3]]
    image = window.grab()
    ok = shown == SELF_TEST_EXPECTED and not image.isNull() and window.state.network is not None
    print(f"self-test {'passed' if ok else 'FAILED'}: R1 = {shown}")
    bill.state.design()
    bill.refresh()
    bill_shown = [w.text() for w in bill.cells["R1"][:3]]
    bill_ok = bill_shown == BILL_SELF_TEST_EXPECTED and not bill.grab().isNull()
    print(f"Bill Mode self-test {'passed' if bill_ok else 'FAILED'}: R1 = {bill_shown} Ω")
    return 0 if ok and bill_ok else 1


class ModeSwitcher:
    """Shows one window at a time and carries F1, F2, C and the section count over on each
    switch. Classic n per path <-> Bill Mode total 2n; an odd total rounds up to n."""

    def __init__(self, classic: MainWindow, bill: BillWindow) -> None:
        self.classic, self.bill = classic, bill
        for w in (classic, bill):
            QShortcut(QKeySequence(SWITCH_KEY), w).activated.connect(self.toggle)
        classic.bill_button.clicked.connect(self.toggle)
        bill.classic_button.clicked.connect(self.toggle)

    def toggle(self) -> None:
        if self.classic.isVisible():
            self._switch(self.classic, self.bill)
        else:
            self._switch(self.bill, self.classic)

    def _switch(self, source: MainWindow | BillWindow, target: MainWindow | BillWindow) -> None:
        src, dst = source.state, target.state
        dst.f1, dst.f2, dst.c = src.f1, src.f2, src.c
        classic, bill = self.classic.state, self.bill.state
        if dst is bill and bill.sections != 2 * classic.n:
            bill.select_sections(2 * classic.n)
        elif dst is classic and classic.n != bill.rows(1):
            classic.select_n(bill.rows(1))
        target.refresh()
        target.move(source.pos())
        source.hide()
        target.show()


def main() -> int:
    testing = "--self-test" in sys.argv
    if testing:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication(sys.argv)
    app.setApplicationName("Extra Sloppy All Pass Filter Designer")
    app.setWindowIcon(QIcon(str(files("esapf.gui") / "icon.png")))
    window, bill = MainWindow(), BillWindow()
    if testing:
        return self_test(window, bill)
    switcher = ModeSwitcher(window, bill)  # noqa: F841 (keeps the connections alive)
    (bill if "--bill" in sys.argv else window).show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
