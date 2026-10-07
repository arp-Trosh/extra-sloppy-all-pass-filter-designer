#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Render the README screenshots offscreen: the classic window and Bill Mode, each after
Design with the default inputs (270-3600 Hz, C = 10 nF).

    uv run tools/screenshots.py [out_dir]      # default: docs/images
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]

from PySide6.QtWidgets import QApplication, QWidget  # noqa: E402

from esapf.gui.bill_window import BillWindow  # noqa: E402
from esapf.gui.main_window import MainWindow  # noqa: E402


def save(app: QApplication, window: QWidget, path: Path) -> None:
    window.show()
    app.processEvents()
    if focused := app.focusWidget():
        focused.clearFocus()  # no text cursor in the F1 field
    app.processEvents()
    window.grab().save(str(path))
    print(path.relative_to(ROOT) if path.is_relative_to(ROOT) else path)


def main() -> None:
    out = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else ROOT / "docs" / "images"
    out.mkdir(parents=True, exist_ok=True)
    existing = QApplication.instance()
    app = existing if isinstance(existing, QApplication) else QApplication([])

    classic = MainWindow()
    classic.state.design()
    classic.refresh()
    save(app, classic, out / "classic.png")
    classic.hide()

    bill = BillWindow()
    bill.state.select_series("E96")
    bill.state.design()
    bill.state.select_source("series")
    bill.refresh()
    save(app, bill, out / "bill_mode.png")


if __name__ == "__main__":
    main()
