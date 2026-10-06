# SPDX-License-Identifier: GPL-3.0-only
"""Bill Mode (ROADMAP.md §0, U1-U5): E-series lookup, BillState and the Qt window."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QWidget

from esapf.bill import MSG_AXIS, BillState, InputError, format_f, format_ohm
from esapf.core.eseries import SERIES, nearest
from esapf.form import FormState
from esapf.gui.app import ModeSwitcher
from esapf.gui.bill_window import BillWindow, header_text
from esapf.gui.main_window import MainWindow

# --- E-series ----------------------------------------------------------------------------


def test_series_tables() -> None:
    assert {k: len(v) for k, v in SERIES.items()} == {
        "E6": 6, "E12": 12, "E24": 24, "E48": 48, "E96": 96, "E192": 192,
    }  # fmt: skip
    assert SERIES["E6"] == (1.0, 1.5, 2.2, 3.3, 4.7, 6.8)
    assert SERIES["E12"] == (1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2)
    assert {2.7, 3.0, 3.6, 4.3, 5.1, 6.2, 9.1} <= set(SERIES["E24"])
    assert {1.47, 3.32, 4.99, 9.76} <= set(SERIES["E96"])
    assert SERIES["E48"] == SERIES["E96"][::2]
    assert SERIES["E96"] == SERIES["E192"][::2]
    assert 9.20 in SERIES["E192"] and 9.19 not in SERIES["E192"]  # IEC exception
    for values in SERIES.values():
        assert list(values) == sorted(set(values))


@pytest.mark.parametrize(
    ("value", "series", "expected"),
    [
        (12.3, "E6", 10.0),  # absolute nearest: 2.3 below vs 2.7 above
        (12.6, "E6", 15.0),
        (174456.75, "E24", 180000.0),
        (174456.75, "E96", 174000.0),
        (9.6e6, "E192", 9.65e6),
        (9.9, "E12", 10.0),  # rounds up into the next decade
        (0.0012, "E24", 0.0012),
        (1000.0, "E6", 1000.0),
        (999.9999999, "E6", 1000.0),
    ],
)
def test_nearest(value: float, series: str, expected: float) -> None:
    assert nearest(value, series) == pytest.approx(expected, rel=1e-12)


def test_nearest_rejects_non_positive() -> None:
    with pytest.raises(ValueError):
        nearest(0, "E12")


# --- BillState ---------------------------------------------------------------------------


def test_formats() -> None:
    assert format_f(91.2345) == "91.23"  # U1: 2 decimals, not truncated to an integer
    assert format_ohm(174456.7499) == "174456.75"  # U2: ohms, 0.01 Ω


def test_design_matches_classic_in_ohms() -> None:
    classic, bill = FormState(), BillState()
    classic.design()
    bill.design()
    for col in ("R1", "R2"):
        for k, b in zip(classic.cells[col][:3], bill.cells[col][:3], strict=True):
            assert float(b) == pytest.approx(float(k) * 1000, abs=0.005)
    assert bill.cells["F1"][:3] == ["91.23", "688.79", "3078.17"]
    assert bill.cells["S1"][:3] == ["180000.00", "24000.00", "5100.00"]  # E24 default
    assert bill.cells["C1"][:3] == ["10"] * 3


def test_series_and_source() -> None:
    st = BillState()
    st.design()
    assert st.network is st.ideal
    st.select_series("E6")
    assert st.cells["S1"][:3] == ["150000.00", "22000.00", "4700.00"]
    st.select_source("series")
    assert st.network is st.standard and st.standard is not None
    assert st.standard.path1[0].r_kohm == pytest.approx(150.0)
    assert "max error 2.16" in st.band_summary()
    st.select_source("ideal")
    assert "max error 0.13" in st.band_summary()
    with pytest.raises(ValueError):
        st.select_series("E3")
    with pytest.raises(ValueError):
        st.select_source("other")


def test_series_before_design_is_harmless() -> None:
    st = BillState()
    st.select_series("E96")
    assert st.standard is None and st.cells["S1"] == [""] * 6


def test_phase_reads_ohms() -> None:
    st = BillState(n=1)
    st.set_cell("R1", 1, "15915.49")  # 1/(2π·15915.49 Ω·10 nF) ≈ 1000 Hz
    st.set_cell("C1", 1, "10")
    st.set_cell("R2", 1, "1591.55")
    st.set_cell("C2", 1, "10")
    st.phase()
    assert st.cells["F1"][0] == "1000.00"
    assert st.cells["F2"][0] == "10000.00"
    assert st.cells["S1"][0] == "16000.00"
    st.set_cell("C2", 1, "")
    with pytest.raises(InputError):
        st.phase()


def test_axis() -> None:
    st = BillState()
    assert st.axis == (100.0, 10000.0)
    st.set_axis("20", "20000")
    assert st.axis == (20.0, 20000.0)
    for lo, hi in (("500", "500"), ("0", "100"), ("1000", "100"), ("x", "100")):
        with pytest.raises(InputError, match=MSG_AXIS.replace("(", r"\(").replace(")", r"\)")):
            st.set_axis(lo, hi)
    assert st.axis == (20.0, 20000.0)  # unchanged after an error


def test_select_n_clears() -> None:
    st = BillState()
    st.design()
    st.select_n(5)
    assert st.n == 5 and st.ideal is None and st.cells["S1"] == [""] * 6


# --- Qt window ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app() -> QApplication:
    inst = QApplication.instance()
    return inst if isinstance(inst, QApplication) else QApplication([])


@pytest.fixture
def messages(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    out: list[str] = []

    def fake_warning(parent: QWidget, title: str, text: str) -> None:
        out.append(text)

    monkeypatch.setattr(QMessageBox, "warning", fake_warning)
    return out


def button(w: QWidget, text: str) -> QPushButton:
    return next(b for b in w.findChildren(QPushButton) if b.text() == text)


def test_window_flow(app: QApplication, messages: list[str]) -> None:
    w = BillWindow()
    w.show()
    button(w, "Design").click()
    assert [e.text() for e in w.cells["R1"][:3]] == ["174456.75", "23106.61", "5170.43"]
    assert w.headers["S1"].text() == "R1 E24 (Ω)"
    button(w, "E96").click()
    assert w.headers["S2"].text() == "R2 E96 (Ω)"
    assert w.cells["S1"][0].text() == "174000.00"
    assert w.cells["S1"][0].isReadOnly() and not w.cells["R1"][0].isReadOnly()
    assert not w.cells["R1"][3].isEnabled()
    button(w, "E-series R").click()
    assert w.graph._network is w.state.standard
    w.f_min.setText("1000")
    w.f_max.setText("10")
    button(w, "Set axis").click()
    assert messages == [MSG_AXIS] and w.f_min.text() == "100"  # reverted to the state
    w.f_min.setText("50")
    w.f_max.returnPressed.emit()
    assert w.graph._axis == (50.0, 10000.0)
    assert w.summary.text().startswith("270–3600 Hz")
    assert not w.grab().isNull()


def test_header_text() -> None:
    assert [header_text(c, "E12") for c in ("F1", "R2", "S1", "C2")] == [
        "F1 (Hz)", "R2 (Ω)", "R1 E12 (Ω)", "C2 (nF)",
    ]  # fmt: skip


def test_mode_switch_carries_inputs(app: QApplication) -> None:
    classic, bill = MainWindow(), BillWindow()
    switcher = ModeSwitcher(classic, bill)
    classic.state.f1, classic.state.c = "300", "22"
    classic.state.select_n(4)
    classic.show()
    switcher.toggle()
    assert bill.isVisible() and not classic.isVisible()
    assert (bill.state.f1, bill.state.c, bill.state.n) == ("300", "22", 4)
    assert bill.f1.text() == "300"
    bill.state.f2 = "3000"
    bill.classic_button.click()
    assert classic.isVisible() and classic.state.f2 == "3000"
