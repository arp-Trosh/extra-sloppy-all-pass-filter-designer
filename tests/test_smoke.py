# SPDX-License-Identifier: GPL-3.0-only
"""Phase 0 smoke tests: the package and the GUI stack import and run."""

import os
import subprocess
import sys

import esapf


def test_version() -> None:
    assert esapf.__version__


def test_cli_version() -> None:
    out = subprocess.run(
        [sys.executable, "-m", "esapf.cli", "--version"], capture_output=True, text=True, check=True
    )
    assert esapf.__version__ in out.stdout


def test_core_has_no_gui_imports() -> None:
    code = (
        "import sys, esapf.core; "
        "assert not any(m.startswith(('PySide6', 'pyqtgraph')) for m in sys.modules)"
    )
    subprocess.run([sys.executable, "-c", code], check=True)


def test_qt_stack_offscreen() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    import pyqtgraph as pg
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance() or QApplication([])
    plot = pg.PlotWidget()
    plot.setLogMode(x=True)
    plot.plot([100, 1000, 10000], [0.0, 0.5, -0.5])
    assert app is not None
