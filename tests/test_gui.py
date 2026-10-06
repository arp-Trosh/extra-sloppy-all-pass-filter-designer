# SPDX-License-Identifier: GPL-3.0-only
"""Drive the real Qt widgets through every captured case (typing and clicking, offscreen)
and compare what the window shows with what the original showed."""

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QLineEdit, QMessageBox, QWidget

from esapf.form import SCALES
from esapf.gui.graph import GraphWidget
from esapf.gui.main_window import MainWindow
from oracle import FIXTURES
from test_vs_original import GRAPH_READS, network_from_table

CASES = sorted(p.stem for p in FIXTURES.glob("*.json"))


@pytest.fixture(scope="module")
def app() -> QApplication:
    inst = QApplication.instance()
    return inst if isinstance(inst, QApplication) else QApplication([])


@pytest.fixture
def window(app: QApplication, monkeypatch: pytest.MonkeyPatch) -> MainWindow:
    w = MainWindow()
    w.messages = []  # type: ignore[attr-defined]

    def fake_warning(parent: QWidget, title: str, text: str) -> None:
        assert title == "ERROR"
        w.messages.append(text)  # type: ignore[attr-defined]

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)
    w.show()
    return w


def type_into(edit: QLineEdit, text: str) -> None:
    """Replace the field's text with real key presses, as a user would."""
    edit.setFocus()
    edit.selectAll()
    QTest.keyClick(edit, Qt.Key.Key_Backspace)
    QTest.keyClicks(edit, text)


def widget_for(w: MainWindow, name: str) -> QLineEdit:
    if name in ("F1", "F2"):
        return w.f1 if name == "F1" else w.f2
    if name == "C":
        return w.c
    col, row = name.split("_")
    return w.cells[col][int(row) - 1]


def shown(w: MainWindow) -> dict[str, str]:
    out = {"F1": w.f1.text(), "F2": w.f2.text(), "C": w.c.text()}
    out |= {"ScaleTop": f"+{SCALES[w.scale_buttons.index(w.scale_group.checkedButton())]}"}
    out["ScaleBottom"] = "-" + out["ScaleTop"][1:]
    for col, cells in w.cells.items():
        out |= {f"{col}_{i}": e.text() for i, e in enumerate(cells, start=1)}
    return out


def click(w: MainWindow, name: str) -> None:
    if name.startswith("N"):
        w.n_buttons[int(name[1:]) - 1].click()
    elif name.startswith("S"):
        w.scale_buttons[SCALES.index(name[1:])].click()
    else:
        label = {"ResetC": "Reset C"}.get(name, name)
        next(b for b in w.findChildren(type(w.n_buttons[0])) if b.text() == label).click()


@pytest.mark.parametrize("cid", CASES)
def test_widgets_replay_original(window: MainWindow, cid: str) -> None:
    case = json.loads((FIXTURES / f"{cid}.json").read_text())
    for step in case["steps"]:
        window.messages.clear()  # type: ignore[attr-defined]
        for op in step["ops"]:
            kind, *args = op
            if kind == "set":
                edit = widget_for(window, args[0])
                if edit.isReadOnly():  # read-only cells can only be set by the program
                    pytest.fail(f"{args[0]} is read-only but the original let the user type")
                type_into(edit, args[1])
            elif kind == "click":
                click(window, args[0])
            elif kind == "read":
                expected = next(r["values"] for r in step["reads"] if r["label"] == args[0])
                assert shown(window) == expected
        expected_msgs = [t for m in step.get("msgboxes", []) for b in m["boxes"] for t in b["text"]]
        assert window.messages == expected_msgs  # type: ignore[attr-defined]


@pytest.mark.parametrize("r", GRAPH_READS, ids=lambda r: r.id)
def test_graph_pixels_match_original(app: QApplication, tmp_path: Path, r) -> None:  # type: ignore[no-untyped-def]
    g = GraphWidget()
    g.set_data(network_from_table(r), float(r.values["ScaleTop"]))
    out = tmp_path / "g.png"
    g.grab().save(str(out))
    mine = np.asarray(Image.open(out).convert("RGB"))
    orig = np.asarray(Image.open(r.graph_png).convert("RGB"))
    identical = np.all(mine == orig, axis=-1).mean()
    assert identical > 0.975, f"only {identical:.1%} identical"


def test_inactive_and_frequency_cells_are_read_only(window: MainWindow) -> None:
    assert window.state.n == 3
    assert not window.cells["R1"][2].isReadOnly()
    assert window.cells["R1"][3].isReadOnly()
    assert window.cells["F1"][0].isReadOnly() and window.cells["F2"][0].isReadOnly()


def test_tooltips_present(window: MainWindow) -> None:
    assert window.f1.toolTip() == "Change lower frequency of range."
    assert window.scale_buttons[0].toolTip() == "Set phase graph scale to +/- 10 degrees."
    assert window.scale_buttons[-1].toolTip() == "Set phase graph scale to +/- 0.1 degree."
