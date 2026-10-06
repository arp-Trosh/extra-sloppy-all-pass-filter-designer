# SPDX-License-Identifier: GPL-3.0-only
"""Bill Mode: the practical window for the user requests in ROADMAP.md §0, driven by
esapf.bill.BillState. The classic window (main_window.py) stays a replica of the original."""

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from esapf.bill import (
    CAPACITOR_CHOICES,
    RESISTOR_MODES,
    SECTION_CHOICES,
    SERIES_NAMES,
    BillState,
    InputError,
)
from esapf.form import MAX_SECTIONS, SCALES
from esapf.gui.bill_graph import BillGraph

TITLE = "Extra Sloppy All Pass Filter Designer: Bill Mode"
SOURCE_LABELS = {"ideal": "Perfect R", "series": "E-series R"}
RESISTOR_LABELS = {"single": "Single", "pair": "Pair (sum)"}
READ_ONLY = ("F1", "S1", "F2", "S2")
INITIAL_SIZE = (1100, 720)  # fits a 1366 x 768 laptop screen; the window is resizable
UNITS = {"F": "Hz", "R": "Ω"}
TIP_C_CELL = (
    "Pick an E6 value or type one: a bare number is nF; p, n and µ (or u) are also accepted."
    " After Design, changing C recalculates R to keep the 90° frequency."
)


def header_text(col: str, series: str, resistors: str = "single") -> str:
    """Column heading: F1 (Hz), R1 (Ω), R1 E24 (Ω), R1 E24 pair (Ω), C1, ..."""
    kind, path = col[0], col[1]
    if kind == "S":
        return f"R{path} {series}{' pair' if resistors == 'pair' else ''} (Ω)"
    if kind == "C":
        return f"C{path}"
    return f"{kind}{path} ({UNITS[kind]})"


class BillWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.state = BillState()
        self.setWindowTitle(TITLE)
        self.setStyleSheet('QLineEdit[readOnly="true"] { background: palette(window); }')
        root = QVBoxLayout(self)

        # --- design inputs and buttons -----------------------------------------------------
        top = QHBoxLayout()
        root.addLayout(top)
        inputs = QGroupBox("Design")
        top.addWidget(inputs)
        g = QGridLayout(inputs)
        self.f1 = self._edit(lambda t: setattr(self.state, "f1", t), "Lower band edge, Hz (≥ 10)")
        self.f2 = self._edit(lambda t: setattr(self.state, "f2", t), "Upper band edge, Hz (≥ 10)")
        self.c = self._edit(
            lambda t: setattr(self.state, "c", t), "Default capacitor: nF, or with p, n or µ"
        )
        for row, (label, edit, unit) in enumerate(
            (("F1", self.f1, "Hz"), ("F2", self.f2, "Hz"), ("C", self.c, "nF"))
        ):
            g.addWidget(QLabel(label), row, 0)
            g.addWidget(edit, row, 1)
            g.addWidget(QLabel(unit), row, 2)

        sections = QHBoxLayout()
        total_label = QLabel("Sections:")
        total_label.setToolTip("Total over both paths; for odd totals path 1 has one more")
        sections.addWidget(total_label)
        self.sections_group, self.sections_buttons = self._choice(
            sections, [str(n) for n in SECTION_CHOICES],
            lambda i: self._run(lambda: self.state.select_sections(SECTION_CHOICES[i])),
        )  # fmt: skip
        g.addLayout(sections, 3, 0, 1, 3)

        actions = QHBoxLayout()
        for text, action in (
            ("Design", self.state.design),
            ("Phase", self.state.phase),
            ("Reset C", self.state.reset_c),
            ("Clear", self.state.clear),
        ):
            b = QPushButton(text)
            b.clicked.connect(partial(self._run, action))
            actions.addWidget(b)
        g.addLayout(actions, 4, 0, 1, 3)

        # --- resistor series and graph source ----------------------------------------------
        options = QGroupBox("Resistors")
        top.addWidget(options)
        o = QVBoxLayout(options)
        series_row = QHBoxLayout()
        series_row.addWidget(QLabel("Series:"))
        self.series_group, self.series_buttons = self._choice(
            series_row, list(SERIES_NAMES),
            lambda i: self._run(lambda: self.state.select_series(SERIES_NAMES[i])),
        )  # fmt: skip
        o.addLayout(series_row)
        source_row = QHBoxLayout()
        source_row.addWidget(QLabel("Graph from:"))
        sources = list(SOURCE_LABELS)
        self.source_group, self.source_buttons = self._choice(
            source_row, list(SOURCE_LABELS.values()),
            lambda i: self._run(lambda: self.state.select_source(sources[i])),
        )  # fmt: skip
        o.addLayout(source_row)
        parts_row = QHBoxLayout()
        parts_row.addWidget(QLabel("Resistors:"))
        modes = list(RESISTOR_LABELS)
        self.resistor_group, self.resistor_buttons = self._choice(
            parts_row, list(RESISTOR_LABELS.values()),
            lambda i: self._run(lambda: self.state.select_resistors(modes[i])),
        )  # fmt: skip
        self.resistor_buttons[1].setToolTip(
            "Two resistors from the selected series whose sum is closest to the calculated R"
        )
        o.addLayout(parts_row)
        self.classic_button = QPushButton("Classic Mode")
        self.classic_button.setToolTip("Switch to the original 2002 window (Ctrl+B)")
        o.addWidget(self.classic_button)
        o.addStretch()

        # --- table -------------------------------------------------------------------------
        table = QGridLayout()
        root.addLayout(table)
        self.headers: dict[str, QLabel] = {}
        self.cells: dict[str, list[QLineEdit]] = {}  # for C columns, the combo's line edit
        self.c_boxes: dict[str, list[QComboBox]] = {}
        for c, col in enumerate(self.state.cells, start=1):
            self.headers[col] = QLabel()
            self.headers[col].setAlignment(Qt.AlignmentFlag.AlignCenter)
            table.addWidget(self.headers[col], 0, c)
            table.setColumnStretch(c, 2 if col[0] == "S" else 1)  # room for "a + b"
            self.cells[col] = []
            for row in range(1, MAX_SECTIONS + 1):
                if col[0] == "C":
                    box = self._c_box(col, row)
                    self.c_boxes.setdefault(col, []).append(box)
                    table.addWidget(box, row, c)
                    line = box.lineEdit()
                    assert line is not None
                    self.cells[col].append(line)
                else:
                    e = self._edit(self._cell_setter(col, row))
                    table.addWidget(e, row, c)
                    self.cells[col].append(e)
        self.row_labels = [QLabel(f"({row})") for row in range(1, MAX_SECTIONS + 1)]
        for row, row_label in enumerate(self.row_labels, start=1):
            table.addWidget(row_label, row, 0)

        # --- graph and its controls --------------------------------------------------------
        controls = QHBoxLayout()
        root.addLayout(controls)
        controls.addWidget(QLabel("Phase scale ±°:"))
        self.scale_group, self.scale_buttons = self._choice(
            controls, list(SCALES), lambda i: self._run(lambda: self.state.select_scale(SCALES[i]))
        )
        controls.addStretch()
        controls.addWidget(QLabel("X axis"))
        self.f_min = QLineEdit(self.state.f_min)
        self.f_max = QLineEdit(self.state.f_max)
        for label, edit in (("Min", self.f_min), ("Max", self.f_max)):
            edit.setAlignment(Qt.AlignmentFlag.AlignRight)
            edit.setMaximumWidth(80)
            edit.returnPressed.connect(self._apply_axis)
            controls.addWidget(QLabel(label))
            controls.addWidget(edit)
        controls.addWidget(QLabel("Hz"))
        apply_axis = QPushButton("Set axis")
        apply_axis.clicked.connect(self._apply_axis)
        controls.addWidget(apply_axis)

        self.graph = BillGraph()
        root.addWidget(self.graph, stretch=1)
        self.summary = QLabel()
        root.addWidget(self.summary)

        self.resize(INITIAL_SIZE[0], max(INITIAL_SIZE[1], self.minimumSizeHint().height()))
        self.refresh()

    # --- construction helpers --------------------------------------------------------------

    def _edit(self, on_edit: Callable[[str], None], tip: str | None = None) -> QLineEdit:
        e = QLineEdit()
        e.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        e.setMinimumWidth(70)
        if tip:
            e.setToolTip(tip)
        e.textEdited.connect(on_edit)
        return e

    def _choice(
        self, row: QHBoxLayout, labels: list[str], on_select: Callable[[int], None]
    ) -> tuple[QButtonGroup, list[QPushButton]]:
        group = QButtonGroup(self)
        buttons = []
        for i, text in enumerate(labels):
            b = QPushButton(text)
            b.setCheckable(True)
            # Let rows of short labels (eleven section counts) shrink below the style's
            # default button width so the window fits laptop screens.
            b.setMinimumWidth(b.fontMetrics().horizontalAdvance(text) + 16)
            b.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
            b.clicked.connect(partial(lambda i, _checked=False: on_select(i), i))
            group.addButton(b)
            row.addWidget(b)
            buttons.append(b)
        return group, buttons

    def _cell_setter(self, col: str, row: int) -> Callable[[str], None]:
        return lambda text: self.state.set_cell(col, row, text)

    def _c_box(self, col: str, row: int) -> QComboBox:
        """U6: editable capacitor drop-down; a new C may recalculate R, hence the refresh."""
        box = QComboBox()
        box.setEditable(True)
        box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        box.addItems(CAPACITOR_CHOICES)
        box.setMaxVisibleItems(len(CAPACITOR_CHOICES))
        box.setCurrentIndex(-1)
        box.setToolTip(TIP_C_CELL)
        line = box.lineEdit()
        assert line is not None
        line.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        def changed(text: str) -> None:
            self.state.set_cell(col, row, text)
            self.refresh()

        line.textEdited.connect(changed)
        box.textActivated.connect(changed)
        return box

    # --- actions ---------------------------------------------------------------------------

    def _run(self, action: Callable[[], None]) -> None:
        try:
            action()
        except InputError as e:
            self.refresh()
            QMessageBox.warning(self, "ERROR", str(e))
        self.refresh()

    def _apply_axis(self) -> None:
        self._run(lambda: self.state.set_axis(self.f_min.text(), self.f_max.text()))

    # --- state -> widgets ------------------------------------------------------------------

    def refresh(self) -> None:
        st = self.state
        for widget, text in (
            (self.f1, st.f1),
            (self.f2, st.f2),
            (self.c, st.c),
            (self.f_min, st.f_min),
            (self.f_max, st.f_max),
        ):
            if widget.text() != text:
                widget.setText(text)
        for col, header in self.headers.items():
            header.setText(header_text(col, st.series, st.resistors))
        for col, widgets in self.cells.items():
            for row, w in enumerate(widgets):
                active = row < st.rows(int(col[1]))
                if w.text() != st.cells[col][row]:
                    w.setText(st.cells[col][row])
                boxes = self.c_boxes.get(col)
                (boxes[row] if boxes else w).setEnabled(active)
                if w.isReadOnly() != (col in READ_ONLY):
                    w.setReadOnly(col in READ_ONLY)
                    w.style().polish(w)  # re-apply the readOnly style rule
        for row, row_label in enumerate(self.row_labels):
            row_label.setEnabled(row < st.rows(1))
        self.sections_buttons[SECTION_CHOICES.index(st.sections)].setChecked(True)
        self.scale_buttons[SCALES.index(st.scale)].setChecked(True)
        self.series_buttons[SERIES_NAMES.index(st.series)].setChecked(True)
        self.source_buttons[list(SOURCE_LABELS).index(st.source)].setChecked(True)
        self.resistor_buttons[RESISTOR_MODES.index(st.resistors)].setChecked(True)
        band = st.band if st.band[0] > 0 else None
        self.graph.set_data(st.network, st.scale_value, st.axis, band)
        self.summary.setText(st.band_summary())
