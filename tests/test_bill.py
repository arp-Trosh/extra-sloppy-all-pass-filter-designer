# SPDX-License-Identifier: GPL-3.0-only
"""Bill Mode (ROADMAP.md §0, U1-U5): E-series lookup, BillState and the Qt window."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication, QMessageBox, QPushButton, QWidget

from esapf.bill import (
    CAPACITOR_CHOICES,
    MSG_AXIS,
    BillState,
    InputError,
    format_c,
    format_f,
    format_ohm,
    parse_c_nf,
)
from esapf.core.eseries import SERIES, nearest, nearest_pair, values_between
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


def test_values_between() -> None:
    assert values_between("E6", 0.01, 1000)[:7] == [0.01, 0.015, 0.022, 0.033, 0.047, 0.068, 0.1]
    assert len(values_between("E6", 0.01, 1000)) == 31
    assert values_between("E12", 1000, 2000) == [1000.0, 1200.0, 1500.0, 1800.0]


@pytest.mark.parametrize("series", ["E6", "E24", "E96"])
@pytest.mark.parametrize("value", [5170.43, 1493.78, 50401.92, 174456.75, 47.0, 0.37])
def test_nearest_pair_is_optimal(value: float, series: str) -> None:
    a, b = nearest_pair(value, series)
    assert a >= b and a in values_between(series, a, a) and b in values_between(series, b, b)
    parts = values_between(series, value / 1000, value)
    brute = min(abs(x + y - value) for x in parts for y in parts)
    assert abs(a + b - value) == pytest.approx(brute, abs=1e-9 * value)


def test_nearest_pair_examples() -> None:
    assert nearest_pair(5170.43, "E24") == (4700.0, 470.0)
    assert nearest_pair(174456.75, "E96") == (174000.0, 453.0)  # tie-break: big main part
    assert nearest_pair(2000.0, "E6") == (1000.0, 1000.0)  # two equal parts are allowed
    with pytest.raises(ValueError):
        nearest_pair(-1, "E6")


# --- BillState ---------------------------------------------------------------------------


def test_formats() -> None:
    assert format_f(91.2345) == "91.23"  # U1: 2 decimals, not truncated to an integer
    assert format_ohm(174456.7499) == "174456.75"  # U2: ohms, 0.01 Ω


def test_design_matches_classic_in_ohms() -> None:
    """Bill Mode uses the exact design; for speech bands it is within 0.04 Ω (2e-7) of the
    original's truncated series."""
    classic, bill = FormState(), BillState()
    classic.design()
    bill.design()
    for col in ("R1", "R2"):
        for k, b in zip(classic.cells[col][:3], bill.cells[col][:3], strict=True):
            assert abs(float(b) - float(k) * 1000) < 0.04 + 0.005  # + display rounding
    assert bill.cells["F1"][:3] == ["91.23", "688.79", "3078.17"]
    assert bill.cells["S1"][:3] == ["180000.00", "24000.00", "5100.00"]  # E24 default
    assert bill.cells["C1"][:3] == ["10 nF"] * 3


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
    st = BillState(sections=2)
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


def test_capacitor_choices() -> None:
    assert CAPACITOR_CHOICES[0] == "10 pF" and CAPACITOR_CHOICES[-1] == "1 µF"
    assert "4.7 nF" in CAPACITOR_CHOICES and "680 nF" in CAPACITOR_CHOICES
    assert len(CAPACITOR_CHOICES) == 31
    assert [format_c(c) for c in (0.0047, 4.7, 4700)] == ["4.7 pF", "4.7 nF", "4.7 µF"]
    for text in CAPACITOR_CHOICES:  # every choice reads back as itself
        assert format_c(parse_c_nf(text)) == text


@pytest.mark.parametrize(
    ("text", "nf"),
    [("10", 10.0), (" 10 pF", 0.01), ("4.7n", 4.7), ("1µF", 1000.0), ("1uf", 1000.0),
     ("0.1 μF", 100.0), ("2.2e1 nF", 22.0), (".5", 0.5),
     ("", 0.0), ("abc", 0.0), ("10 mF", 0.0), ("-10", 0.0)],
)  # fmt: skip
def test_parse_c_nf(text: str, nf: float) -> None:
    assert parse_c_nf(text) == pytest.approx(nf)


def test_changing_c_after_design_recalculates_r() -> None:
    st = BillState()
    st.design()
    f_before = st.cells["F1"][:3]
    st.set_cell("C1", 1, "22 nF")
    assert st.cells["R1"][0] == "79298.54"  # 174456.79 Ω * 10 / 22
    assert st.cells["R1"][1:3] == ["23106.62", "5170.43"]
    assert st.cells["F1"][:3] == f_before  # 90° frequencies kept
    assert st.cells["S1"][0] == "82000.00"
    assert st.ideal is not None and st.ideal.path1[0].c_nf == 22.0
    st.set_cell("C2", 3, "")  # invalid: nothing recalculated until it is valid again
    st.set_cell("C1", 2, "4.7 nF")
    assert st.cells["R1"][1] == "23106.62"
    st.set_cell("C2", 3, "10n")
    assert st.cells["R1"][1] == "49163.01"
    st.set_cell("R1", 3, "5000")  # a manual R ends the link to the design
    st.set_cell("C1", 3, "1 nF")
    assert st.cells["R1"][2] == "5000"
    st.phase()  # Phase reads the C units
    assert st.ideal.path1[2].c_nf == 1.0  # type: ignore[union-attr]


def test_pair_mode() -> None:
    st = BillState()
    st.select_resistors("pair")
    st.design()
    assert st.cells["S1"][:3] == ["150000.00 + 24000.00", "22000.00 + 1100.00", "4700.00 + 470.00"]
    assert st.standard is not None
    assert st.standard.path1[2].r_kohm == pytest.approx(5.17)
    st.select_source("series")
    assert st.band_summary() == "270–3600 Hz: max error 0.3241°, min suppression 51.0 dB"
    single = BillState(source="series")
    single.design()
    assert "max error 2.97" in single.band_summary()  # E24 singles are 9x worse here
    st.select_resistors("single")
    assert st.cells["S1"][2] == "5100.00"
    with pytest.raises(ValueError):
        st.select_resistors("triple")


def test_default_c_takes_units() -> None:
    st = BillState(c="0.1u")
    st.design()
    assert st.cells["C1"][0] == "100 nF"
    assert st.ideal is not None and st.ideal.path1[0].c_nf == pytest.approx(100.0)
    for bad in ("", "0", "x"):
        with pytest.raises(InputError, match="Capacitor"):
            BillState(c=bad).design()
    with pytest.raises(InputError, match="F1"):  # F1 is still checked first
        BillState(f1="5", c="").design()


def test_select_sections_clears() -> None:
    st = BillState()
    st.design()
    st.select_sections(5)
    assert st.sections == 5 and st.ideal is None and st.cells["S1"] == [""] * 6
    for bad in (1, 13, True):
        with pytest.raises(ValueError):
            st.select_sections(bad)


@pytest.mark.parametrize(("total", "rows", "error"), [
    (3, (2, 1), "5.5262"), (5, (3, 2), "0.4618"), (7, (4, 3), "0.0386"),
    (9, (5, 4), "0.0032"), (11, (6, 5), "0.0003"), (12, (6, 6), "0.0001"),
])  # fmt: skip
def test_odd_totals(total: int, rows: tuple[int, int], error: str) -> None:
    st = BillState(sections=total)
    assert (st.rows(1), st.rows(2)) == rows
    st.design()
    for p, n in enumerate(rows, start=1):
        for col in "FRSC":
            cells = st.cells[f"{col}{p}"]
            assert all(cells[:n]) and not any(cells[n:]), (col, p)
    assert f"max error {error}" in st.band_summary()
    f1 = [float(f) for f in st.cells["F1"][: rows[0]]]
    f2 = [float(f) for f in st.cells["F2"][: rows[1]]]
    assert f1 == sorted(f1) and f2 == sorted(f2, reverse=True)
    st.phase()  # unequal paths read back correctly
    assert st.ideal is not None and len(st.ideal.path1) == rows[0]
    st.set_cell("C2", rows[1], "22n")  # recalculation works on the shorter path too
    assert st.ideal.path2[-1].c_nf == 22.0


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
    assert [e.text() for e in w.cells["R1"][:3]] == ["174456.79", "23106.62", "5170.43"]
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
        "F1 (Hz)", "R2 (Ω)", "R1 E12 (Ω)", "C2",
    ]  # fmt: skip
    assert header_text("S2", "E96", "pair") == "R2 E96 pair (Ω)"


def test_mode_switch_carries_inputs(app: QApplication) -> None:
    classic, bill = MainWindow(), BillWindow()
    switcher = ModeSwitcher(classic, bill)
    classic.state.f1, classic.state.c = "300", "22"
    classic.state.select_n(4)
    classic.show()
    switcher.toggle()
    assert bill.isVisible() and not classic.isVisible()
    assert (bill.state.f1, bill.state.c, bill.state.sections) == ("300", "22", 8)
    assert bill.f1.text() == "300"
    bill.state.f2 = "3000"
    bill.classic_button.click()
    assert classic.isVisible() and classic.state.f2 == "3000"
    classic.bill_button.click()
    assert bill.isVisible() and not classic.isVisible()
    bill.state.select_sections(7)  # odd total -> classic rounds up to 4 per path ...
    classic.state.design()
    switcher.toggle()
    assert classic.state.n == 4 and classic.state.network is not None  # ... no clear needed
    switcher.toggle()
    assert bill.state.sections == 8


def test_window_odd_sections(app: QApplication) -> None:
    w = BillWindow()
    button(w, "7").click()
    button(w, "Design").click()
    assert [e.isEnabled() for e in w.cells["R1"]] == [True] * 4 + [False] * 2
    assert [b.isEnabled() for b in w.c_boxes["C2"]] == [True] * 3 + [False] * 3
    assert [x.isEnabled() for x in w.row_labels] == [True] * 4 + [False] * 2
    assert w.cells["R2"][2].text() and not w.cells["R2"][3].text()
    assert w.summary.text().startswith("270–3600 Hz: max error 0.0386")


def test_classic_bill_mode_button_fits(app: QApplication) -> None:
    from esapf.gui import layout as L

    w = MainWindow()
    b = w.bill_button
    assert b.geometry().getRect() == L.BILL_MODE_BUTTON
    assert b.fontMetrics().horizontalAdvance(b.text()) <= b.width() - 4  # inside the border
    design = next(x for x in w.findChildren(QPushButton) if x.text() == "Design")
    assert design.geometry().right() < b.geometry().left()


def test_window_capacitor_box_and_pairs(app: QApplication, messages: list[str]) -> None:
    w = BillWindow()
    w.show()
    button(w, "Design").click()
    box = w.c_boxes["C1"][0]
    assert box.count() == 31 and box.isEnabled() and not w.c_boxes["C1"][3].isEnabled()
    assert w.cells["C1"][0].text() == "10 nF"
    box.textActivated.emit("22 nF")  # what a pick from the list sends
    assert w.state.cells["C1"][0] == "22 nF"
    assert w.cells["R1"][0].text() == "79298.54"
    line = box.lineEdit()
    assert line is not None
    line.textEdited.emit("4.7n")  # typing
    assert w.cells["R1"][0].text() == "371184.66"  # from the exact τ, not the rounded R
    button(w, "Pair (sum)").click()
    assert w.headers["S1"].text() == "R1 E24 pair (Ω)"
    assert w.cells["S1"][2].text() == "4700.00 + 470.00"
    button(w, "Single").click()
    assert w.cells["S1"][2].text() == "5100.00"
    button(w, "Clear").click()
    assert line.text() == "" and messages == []
