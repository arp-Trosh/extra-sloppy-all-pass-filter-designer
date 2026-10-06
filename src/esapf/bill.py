# SPDX-License-Identifier: GPL-3.0-only
"""State and button semantics of Bill Mode, the practical window (ROADMAP.md §0).

Like esapf.form.FormState, every field is kept as the text the user sees and the Qt window
only renders it. Differences from the classic window: frequencies have 2 decimals (U1),
resistances are in ohms with 2 decimals (U2), the graph's X axis range is settable (U3),
each resistor is also shown as its nearest E-series value (U4) or the closest series pair
(U7), the graph can be drawn from either the ideal or the E-series resistors (U5), and each
capacitor is chosen from an E6 list or typed with a unit (U6).
"""

import re
from dataclasses import dataclass, field

from esapf.core import Network, Section, band_stats, oppelt_design
from esapf.core.eseries import SERIES, nearest, nearest_pair, values_between
from esapf.core.legacy import MSG_COMPONENTS, InputError, parse_design_inputs, vb_val
from esapf.core.metrics import PLOT_F_MAX, PLOT_F_MIN
from esapf.core.network import KOHM_NF_TO_S
from esapf.form import MAX_SECTIONS, SCALES

COLUMNS = ("F1", "R1", "S1", "C1", "F2", "R2", "S2", "C2")  # S = standard (E-series) R
SERIES_NAMES = tuple(SERIES)
SOURCES = ("ideal", "series")
RESISTOR_MODES = ("single", "pair")
MSG_AXIS = "The X axis needs 0 < Min < Max (Hz)"
OHM_PER_KOHM = 1000.0


def format_f(f_hz: float) -> str:
    """U1: frequency with 2 decimals."""
    return f"{f_hz:.2f}"


def format_ohm(r_ohm: float) -> str:
    """U2: resistance in ohms, rounded to 0.01 Ω."""
    return f"{r_ohm:.2f}"


def format_c(c_nf: float) -> str:
    """Capacitor with the most readable unit: 10 pF, 4.7 nF, 1 µF."""
    if c_nf < 1:
        return f"{c_nf * 1000:g} pF"
    if c_nf < 1000:
        return f"{c_nf:g} nF"
    return f"{c_nf / 1000:g} µF"


# U6: E6 capacitors from 10 pF to 1 µF.
CAPACITOR_CHOICES = tuple(format_c(c) for c in values_between("E6", 0.01, 1000))

_C_UNITS = {"p": 1e-3, "n": 1.0, "u": 1e3, "µ": 1e3, "μ": 1e3}  # to nF (micro sign / mu)
_C_TEXT = re.compile(r"\s*((?:\d+\.?\d*|\.\d+)(?:[eE][+-]?\d+)?)\s*([pnuµμ]?)[fF]?\s*")


def parse_c_nf(text: str) -> float:
    """Capacitor cell text -> nF. A bare number is nF (as in the classic window); p, n and
    u/µ suffixes, with or without F, are also accepted. Anything else gives 0."""
    m = _C_TEXT.fullmatch(text)
    if not m:
        return 0.0
    return float(m.group(1)) * _C_UNITS.get(m.group(2), 1.0)


def _empty_table() -> dict[str, list[str]]:
    return {c: [""] * MAX_SECTIONS for c in COLUMNS}


@dataclass
class BillState:
    f1: str = "270"
    f2: str = "3600"
    c: str = "10"
    n: int = 3
    scale: str = "1"
    series: str = "E24"
    source: str = "ideal"
    resistors: str = "single"
    f_min: str = f"{PLOT_F_MIN:g}"
    f_max: str = f"{PLOT_F_MAX:g}"
    cells: dict[str, list[str]] = field(default_factory=_empty_table)
    ideal: Network | None = None  # from the R and C cells
    standard: Network | None = None  # E-series R with the same C
    # Time constants of the last Design while its R values are untouched: changing a C
    # then recalculates that section's R (U6).
    design_tau: tuple[tuple[float, ...], tuple[float, ...]] | None = None

    # --- buttons ---------------------------------------------------------------------------

    def select_n(self, n: int) -> None:
        if isinstance(n, bool) or not 1 <= n <= MAX_SECTIONS:
            raise ValueError(n)
        self.n = n
        self.clear()

    def select_scale(self, scale: str) -> None:
        if scale not in SCALES:
            raise ValueError(scale)
        self.scale = scale

    def select_series(self, series: str) -> None:
        if series not in SERIES:
            raise ValueError(series)
        self.series = series
        self._update_standard()

    def select_resistors(self, mode: str) -> None:
        """U7: one series resistor per position, or a pair whose sum is closest."""
        if mode not in RESISTOR_MODES:
            raise ValueError(mode)
        self.resistors = mode
        self._update_standard()

    def select_source(self, source: str) -> None:
        if source not in SOURCES:
            raise ValueError(source)
        self.source = source

    def clear(self) -> None:
        self.cells = _empty_table()
        self.ideal = self.standard = self.design_tau = None

    def reset_c(self) -> None:
        """Copy the default C (nF) into the C cells, written like the list entries."""
        c_nf = parse_c_nf(self.c)
        text = format_c(c_nf) if c_nf > 0 else self.c
        for col in ("C1", "C2"):
            self.cells[col][: self.n] = [text] * self.n

    def design(self) -> None:
        """Design from F1, F2 and C. Raises InputError on invalid input."""
        self.reset_c()
        # The C box takes units like the cells; repr() hands the value to the classic
        # validation so the messages and their order stay the same.
        inp = parse_design_inputs(self.f1, self.f2, repr(parse_c_nf(self.c)))
        net = Network.from_design(oppelt_design(inp.f1, inp.f2, self.n), inp.c_nf)
        for i, (a, b) in enumerate(zip(net.path1, net.path2, strict=True)):
            self.cells["F1"][i], self.cells["R1"][i] = format_f(a.f90), format_ohm(_ohm(a.r_kohm))
            self.cells["F2"][i], self.cells["R2"][i] = format_f(b.f90), format_ohm(_ohm(b.r_kohm))
        self.ideal = net
        self.design_tau = (net.tau1, net.tau2)
        self._update_standard()

    def phase(self) -> None:
        """Recompute F, the E-series values and the graph from the R (Ω) and C cells."""
        rows = range(self.n)
        r1, r2 = ([vb_val(self.cells[c][i]) for i in rows] for c in ("R1", "R2"))
        c1, c2 = ([parse_c_nf(self.cells[c][i]) for i in rows] for c in ("C1", "C2"))
        if any(v <= 0 for v in r1 + r2 + c1 + c2):
            raise InputError(MSG_COMPONENTS)
        net = Network.from_values(_kohm(r1), c1, _kohm(r2), c2)
        for i, (a, b) in enumerate(zip(net.path1, net.path2, strict=True)):
            self.cells["F1"][i], self.cells["F2"][i] = format_f(a.f90), format_f(b.f90)
        self.ideal = net
        self._update_standard()

    def set_axis(self, f_min: str, f_max: str) -> None:
        """U3: set the graph's X axis range. Raises InputError if it is not 0 < min < max."""
        lo, hi = vb_val(f_min), vb_val(f_max)
        if not 0 < lo < hi:
            raise InputError(MSG_AXIS)
        self.f_min, self.f_max = f_min, f_max

    # --- derived values --------------------------------------------------------------------

    @property
    def network(self) -> Network | None:
        """What the graph shows (U5)."""
        return self.standard if self.source == "series" else self.ideal

    @property
    def axis(self) -> tuple[float, float]:
        return vb_val(self.f_min), vb_val(self.f_max)

    @property
    def band(self) -> tuple[float, float]:
        """F1 and F2 as numbers, ascending (0 if not a number)."""
        f1, f2 = vb_val(self.f1), vb_val(self.f2)
        return min(f1, f2), max(f1, f2)

    @property
    def scale_value(self) -> float:
        return vb_val(self.scale)

    def band_summary(self) -> str:
        """Worst phase error and suppression between F1 and F2 for the plotted network."""
        net, (f1, f2) = self.network, self.band
        if net is None or f1 <= 0:
            return ""
        st = band_stats(f1, f2, net.tau1, net.tau2)
        return (
            f"{f1:g}–{f2:g} Hz: max error {st.max_abs_error_deg:.4f}°,"
            f" min suppression {st.min_suppression_db:.1f} dB"
        )

    def set_cell(self, col: str, row: int, text: str) -> None:
        """Set a table cell (row is 1-based, as in the UI).

        Editing an R ends the link to the last Design. Changing a C while that link holds
        recalculates the section's R so that its 90° frequency stays as designed (U6)."""
        self.cells[col][row - 1] = text
        if col[0] == "R":
            self.design_tau = None
        elif col[0] == "C" and self.design_tau is not None:
            self._redesign_r()

    def _redesign_r(self) -> None:
        assert self.design_tau is not None
        paths = []
        for p, taus in enumerate(self.design_tau, start=1):
            c_nf = [parse_c_nf(t) for t in self.cells[f"C{p}"][: len(taus)]]
            if any(c <= 0 for c in c_nf):
                return  # wait until every C is valid again
            paths.append(
                tuple(Section(t / (c * KOHM_NF_TO_S), c) for t, c in zip(taus, c_nf, strict=True))
            )
        self.ideal = Network(paths[0], paths[1])
        for p, path in enumerate(paths, start=1):
            self.cells[f"R{p}"][: len(path)] = [format_ohm(_ohm(s.r_kohm)) for s in path]
        self._update_standard()

    def _update_standard(self) -> None:
        net = self.ideal
        if net is None:
            return
        paths = []
        for col, path in (("S1", net.path1), ("S2", net.path2)):
            if self.resistors == "pair":
                pairs = [nearest_pair(_ohm(s.r_kohm), self.series) for s in path]
                texts = [f"{format_ohm(a)} + {format_ohm(b)}" for a, b in pairs]
                std = [a + b for a, b in pairs]
            else:
                std = [nearest(_ohm(s.r_kohm), self.series) for s in path]
                texts = [format_ohm(r) for r in std]
            self.cells[col][: len(std)] = texts
            paths.append((_kohm(std), [s.c_nf for s in path]))
        (r1, c1), (r2, c2) = paths
        self.standard = Network.from_values(r1, c1, r2, c2)


def _ohm(r_kohm: float) -> float:
    return r_kohm * OHM_PER_KOHM


def _kohm(r_ohm: list[float]) -> list[float]:
    return [r / OHM_PER_KOHM for r in r_ohm]


__all__ = [
    "CAPACITOR_CHOICES",
    "RESISTOR_MODES",
    "SERIES_NAMES",
    "SOURCES",
    "BillState",
    "InputError",
]
