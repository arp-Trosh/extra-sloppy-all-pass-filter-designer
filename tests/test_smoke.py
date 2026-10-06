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
    code = "import sys, esapf.core; assert not any(m.startswith('PySide6') for m in sys.modules)"
    subprocess.run([sys.executable, "-c", code], check=True)


def test_gui_starts_offscreen() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication

    from esapf.gui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    assert (w.width(), w.height()) == (520, 474)
    assert app is not None


def test_gui_self_test_entry_point() -> None:
    env = os.environ | {"QT_QPA_PLATFORM": "offscreen"}
    out = subprocess.run(
        [sys.executable, "-m", "esapf.gui", "--self-test"],
        capture_output=True, text=True, env=env, timeout=60,
    )  # fmt: skip
    assert out.returncode == 0, out.stdout + out.stderr
    assert "self-test passed" in out.stdout
