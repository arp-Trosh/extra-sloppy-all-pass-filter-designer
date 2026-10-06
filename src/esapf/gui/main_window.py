# SPDX-License-Identifier: GPL-3.0-only
"""Main window: a replica of the original 2002 layout, driven by esapf.form.FormState."""

from collections.abc import Callable
from functools import partial

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPaintEvent
from PySide6.QtWidgets import QButtonGroup, QLineEdit, QMessageBox, QPushButton, QWidget

from esapf import __version__
from esapf.form import SCALES, FormState, InputError
from esapf.gui import layout as L
from esapf.gui.graph import GraphWidget

TITLE = "Extra Sloppy All Pass Filter Designer"

ABOUT = f"""{TITLE} {__version__}

A re-implementation of the J-Tek All Pass Filter Designer
by Lawrence Woolf, GJ3RAX (2002-2004).

Design equations: R. Oppelt, DB2NP,
VHF Communications 2/1987.

This program is free software, licensed under the
GNU General Public License version 3 (GPL-3.0-only).
It comes with ABSOLUTELY NO WARRANTY."""


def font(large: bool) -> QFont:
    f = QFont()
    f.setFamilies(L.FONT_FAMILIES)
    f.setPixelSize(L.FONT_LARGE_PX if large else L.FONT_SMALL_PX)
    f.setBold(True)
    return f


def rgb(c: tuple[int, int, int]) -> str:
    return f"rgb({c[0]},{c[1]},{c[2]})"


BUTTON_CSS = f"""
QPushButton {{ background: {rgb(L.BUTTON_FACE)}; color: black; border: 2px solid;
               border-color: {rgb(L.WHITE)} {rgb(L.SHADOW_INNER)}
                             {rgb(L.SHADOW_INNER)} {rgb(L.WHITE)}; }}
QPushButton:pressed {{ border-color: {rgb(L.SHADOW_INNER)} {rgb(L.WHITE)}
                                    {rgb(L.WHITE)} {rgb(L.SHADOW_INNER)}; }}
QPushButton:checked {{ background: {rgb(L.SELECTED)}; }}
QPushButton:focus {{ outline: none; }}
"""


def edit_css(bg: tuple[int, int, int]) -> str:
    return (
        f"QLineEdit {{ background: {rgb(bg)}; color: black; padding: 0 2px;"
        f" border: 2px solid; border-color: {rgb(L.SHADOW_INNER)} {rgb(L.WHITE)}"
        f" {rgb(L.WHITE)} {rgb(L.SHADOW_INNER)}; }}"
    )


class MainWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.state = FormState()
        self.setWindowTitle(TITLE)
        self.setFixedSize(*L.WINDOW_SIZE)
        self.setStyleSheet(BUTTON_CSS)
        self._large, self._small = font(True), font(False)

        self.f1 = self._edit(L.F1_BOX, L.TIP_F1, lambda t: setattr(self.state, "f1", t))
        self.f2 = self._edit(L.F2_BOX, L.TIP_F2, lambda t: setattr(self.state, "f2", t))
        self.c = self._edit(L.C_BOX, L.TIP_C, lambda t: setattr(self.state, "c", t))

        self.cells: dict[str, list[QLineEdit]] = {}
        for col in L.TABLE_COLUMNS:
            self.cells[col] = [
                self._edit(L.cell_rect(col, row), None, self._cell_setter(col, row), large=False)
                for row in range(1, 7)
            ]

        self.n_group = QButtonGroup(self)
        self.n_buttons = []
        for i, rect in enumerate(L.N_BUTTONS):
            b = self._button(rect, str(i + 1), L.TIP_N[i], partial(self._select_n, i + 1))
            b.setCheckable(True)
            self.n_group.addButton(b)
            self.n_buttons.append(b)

        self.scale_group = QButtonGroup(self)
        self.scale_buttons = []
        for rect, s in zip(L.SCALE_BUTTONS, SCALES, strict=True):
            b = self._button(rect, s, L.tip_scale(s), partial(self._select_scale, s))
            b.setCheckable(True)
            self.scale_group.addButton(b)
            self.scale_buttons.append(b)

        self._button(L.DESIGN_BUTTON, "Design", L.TIP_DESIGN, lambda: self._run(self.state.design))
        self._button(L.RESET_C_BUTTON, "Reset C", L.TIP_RESET_C,
                     lambda: self._run(self.state.reset_c))  # fmt: skip
        self._button(L.PHASE_BUTTON, "Phase", L.TIP_PHASE, lambda: self._run(self.state.phase))
        self._button(L.CLEAR_BUTTON, "Clear", L.TIP_CLEAR, lambda: self._run(self.state.clear))
        self._button(L.EXIT_BUTTON, "Exit", L.TIP_EXIT, self._exit)
        # Not in the original; esapf.gui.app.ModeSwitcher connects it.
        self.bill_button = QPushButton("Bill Mode", self)
        self.bill_button.setGeometry(*L.BILL_MODE_BUTTON)
        self.bill_button.setFont(self._large)
        self.bill_button.setToolTip(L.TIP_BILL_MODE)

        self.graph = GraphWidget(self)
        self.graph.move(L.GRAPH[0], L.GRAPH[1])
        self.graph.setToolTip(L.TIP_GRAPH)

        self.refresh()

    # --- construction helpers --------------------------------------------------------------

    def _edit(
        self,
        rect: L.Rect,
        tip: str | None,
        on_edit: Callable[[str], None],
        large: bool = True,
    ) -> QLineEdit:
        e = QLineEdit(self)
        e.setGeometry(*rect)
        e.setFont(self._large if large else self._small)
        e.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        e.setStyleSheet(edit_css(L.WHITE))
        if tip:
            e.setToolTip(tip)
        e.textEdited.connect(on_edit)
        return e

    def _button(self, rect: L.Rect, text: str, tip: str, slot: Callable[..., None]) -> QPushButton:
        b = QPushButton(text, self)
        b.setGeometry(*rect)
        b.setFont(self._large)
        b.setToolTip(tip)
        b.clicked.connect(slot)
        return b

    def _cell_setter(self, col: str, row: int) -> Callable[[str], None]:
        return lambda text: self.state.set_cell(col, row, text)

    # --- actions ---------------------------------------------------------------------------

    def _run(self, action: Callable[[], None]) -> None:
        try:
            action()
        except InputError as e:
            self.refresh()  # e.g. Design copies C into the table before validating
            QMessageBox.warning(self, "ERROR", str(e))
        self.refresh()

    def _select_n(self, n: int, _checked: bool = False) -> None:
        self._run(lambda: self.state.select_n(n))

    def _select_scale(self, s: str, _checked: bool = False) -> None:
        self._run(lambda: self.state.select_scale(s))

    def _exit(self) -> None:
        QMessageBox.about(self, f"About {TITLE}", ABOUT)
        self.close()

    # --- state -> widgets ------------------------------------------------------------------

    def refresh(self) -> None:
        st = self.state
        for widget, text in ((self.f1, st.f1), (self.f2, st.f2), (self.c, st.c)):
            if widget.text() != text:
                widget.setText(text)
        for col, widgets in self.cells.items():
            for row, w in enumerate(widgets):
                active = row < st.n
                if w.text() != st.cells[col][row]:
                    w.setText(st.cells[col][row])
                w.setReadOnly(not active or col in ("F1", "F2"))
                w.setFocusPolicy(
                    Qt.FocusPolicy.StrongFocus
                    if active and col not in ("F1", "F2")
                    else Qt.FocusPolicy.NoFocus
                )
                w.setStyleSheet(edit_css(L.WHITE if active else L.SELECTED))
        self.n_buttons[st.n - 1].setChecked(True)
        self.scale_buttons[SCALES.index(st.scale)].setChecked(True)
        self.graph.set_data(st.network, st.scale_value)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.fillRect(self.rect(), QColor(*L.FORM_BG))
        for t in L.STATIC_TEXTS:
            self._text(p, t.x, t.y, t.text, t.colour, t.large)
        for row in range(1, self.state.n + 1):
            y = L.ROW_LABEL_Y + L.TABLE_ROW_STEP * (row - 1)
            self._text(p, L.ROW_LABEL_X, y, f"({row})", L.BLACK, True)
        for rect, sign in ((L.SCALE_TOP, "+"), (L.SCALE_BOTTOM, "-")):
            p.setFont(self._small)
            p.setPen(QColor(*L.BLUE))
            p.drawText(*rect, Qt.AlignmentFlag.AlignCenter, f"{sign}{self.state.scale}")
        p.end()

    def _text(
        self,
        p: QPainter,
        x: int,
        cap_top: int,
        text: str,
        colour: tuple[int, int, int],
        large: bool,
    ) -> None:
        f = self._large if large else self._small
        p.setFont(f)
        p.setPen(QColor(*colour))
        p.drawText(x, cap_top + QFontMetrics(f).capHeight(), text)
