# SPDX-License-Identifier: GPL-3.0-only
"""State and button semantics of the original main window, independent of any GUI toolkit.

All fields are kept as the text the user sees, exactly like the VB6 TextBoxes of the
original (docs/ORIGINAL_BEHAVIOUR.md §5). The Qt window only renders this state and
forwards clicks, so the behaviour can be replayed against the captured fixtures headlessly.
"""

from dataclasses import dataclass, field

from esapf.core import Network, oppelt_design
from esapf.core.legacy import (
    InputError,
    format_f,
    format_r,
    parse_components,
    parse_design_inputs,
    vb_val,
)

MAX_SECTIONS = 6
COLUMNS = ("F1", "R1", "C1", "F2", "R2", "C2")
SCALES = ("10", "5", "2", "1", "0.5", "0.2", "0.1")


def _empty_table() -> dict[str, list[str]]:
    return {c: [""] * MAX_SECTIONS for c in COLUMNS}


@dataclass
class FormState:
    f1: str = "270"
    f2: str = "3600"
    c: str = "10"
    n: int = 3
    scale: str = "1"
    cells: dict[str, list[str]] = field(default_factory=_empty_table)
    network: Network | None = None  # what the graph shows; None = empty grid

    # --- buttons ---------------------------------------------------------------------------

    def select_n(self, n: int) -> None:
        """Filters 1-6: select the section count; clears the table and the graph."""
        if isinstance(n, bool) or not 1 <= n <= MAX_SECTIONS:
            raise ValueError(n)
        self.n = n
        self.clear()

    def select_scale(self, scale: str) -> None:
        if scale not in SCALES:
            raise ValueError(scale)
        self.scale = scale

    def clear(self) -> None:
        self.cells = _empty_table()
        self.network = None

    def reset_c(self) -> None:
        """Copy the default C into the C cells of the active rows (no validation)."""
        for col in ("C1", "C2"):
            self.cells[col][: self.n] = [self.c] * self.n

    def design(self) -> None:
        """Design button. Raises InputError (message box text) on invalid input."""
        self.reset_c()  # the original fills the C cells before validating anything
        inp = parse_design_inputs(self.f1, self.f2, self.c)
        net = Network.from_design(oppelt_design(inp.f1, inp.f2, self.n), inp.c_nf)
        for i, (a, b) in enumerate(zip(net.path1, net.path2, strict=True)):
            self.cells["F1"][i], self.cells["R1"][i] = format_f(a.f90), format_r(a.r_kohm)
            self.cells["F2"][i], self.cells["R2"][i] = format_f(b.f90), format_r(b.r_kohm)
        self.network = net

    def phase(self) -> None:
        """Phase button: recompute F( ) and the graph from the R and C cells."""
        rows = range(self.n)
        values = parse_components(
            [self.cells[c][i] for c in ("R1", "C1", "R2", "C2") for i in rows]
        )
        r1, c1, r2, c2 = (values[k * self.n : (k + 1) * self.n] for k in range(4))
        net = Network.from_values(r1, c1, r2, c2)
        for i, (a, b) in enumerate(zip(net.path1, net.path2, strict=True)):
            self.cells["F1"][i], self.cells["F2"][i] = format_f(a.f90), format_f(b.f90)
        self.network = net

    # --- helpers ---------------------------------------------------------------------------

    @property
    def scale_value(self) -> float:
        return vb_val(self.scale)

    def set_cell(self, col: str, row: int, text: str) -> None:
        """Set a table cell (row is 1-based, as in the UI)."""
        self.cells[col][row - 1] = text


__all__ = ["SCALES", "FormState", "InputError"]
