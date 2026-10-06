# SPDX-License-Identifier: GPL-3.0-only
"""Bill Mode graph: phase error and suppression on a labelled log axis whose range the user
sets (U3). Unlike esapf.gui.graph it is resizable and does not copy the original pixels."""

from math import ceil, floor, log10

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFontMetrics, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QSizePolicy, QWidget

from esapf.core import Network, phase_error_deg, suppression_db
from esapf.gui import layout as L

MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 46, 40, 20, 22
SUPPRESSION_TOP_DB = 80.0
GRID_MAJOR = QColor(150, 150, 150)
GRID_MINOR = QColor(220, 220, 220)
BAND_FILL = QColor(255, 255, 210)


def frequency_ticks(f_min: float, f_max: float) -> list[float]:
    """1..9 x 10^d grid frequencies inside [f_min, f_max]."""
    out = []
    for d in range(floor(log10(f_min)), ceil(log10(f_max)) + 1):
        for m in range(1, 10):
            f = m * 10.0**d
            if f_min * (1 - 1e-9) <= f <= f_max * (1 + 1e-9):
                out.append(f)
    return out


def frequency_label(f: float) -> str:
    return f"{f / 1000:g}k" if f >= 1000 else f"{f:g}"


class BillGraph(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setMinimumSize(420, 220)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._network: Network | None = None
        self._scale = 1.0
        self._axis = (100.0, 10_000.0)
        self._band: tuple[float, float] | None = None

    def set_data(
        self,
        network: Network | None,
        scale: float,
        axis: tuple[float, float],
        band: tuple[float, float] | None,
    ) -> None:
        self._network, self._scale, self._axis, self._band = network, scale, axis, band
        self.update()

    # --- mappings --------------------------------------------------------------------------

    def plot_rect(self) -> QRectF:
        return QRectF(
            MARGIN_LEFT,
            MARGIN_TOP,
            self.width() - MARGIN_LEFT - MARGIN_RIGHT,
            self.height() - MARGIN_TOP - MARGIN_BOTTOM,
        )

    def f_to_x(self, f: float) -> float:
        r, (lo, hi) = self.plot_rect(), self._axis
        return r.left() + (log10(f) - log10(lo)) / (log10(hi) - log10(lo)) * r.width()

    def x_to_f(self, x: np.ndarray) -> np.ndarray:
        r, (lo, hi) = self.plot_rect(), self._axis
        t = (x - r.left()) / r.width()
        return np.asarray(lo * (hi / lo) ** t, dtype=np.float64)

    # --- painting --------------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), QColor(*L.WHITE))
        r = self.plot_rect()
        if self._band is not None:
            x1, x2 = (self.f_to_x(f) for f in self._band)
            p.fillRect(QRectF(x1, r.top(), x2 - x1, r.height()).intersected(r), BAND_FILL)
        self._grid(p, r)
        if self._network is not None:
            p.setClipRect(r)
            self._curves(p, r, self._network)
            p.setClipping(False)
        p.setPen(QColor(*L.BLACK))
        p.drawRect(r)
        p.end()

    def _grid(self, p: QPainter, r: QRectF) -> None:
        fm = QFontMetrics(p.font())
        last_label_right = -1e9
        for f in frequency_ticks(*self._axis):
            x = self.f_to_x(f)
            mantissa = round(f / 10.0 ** floor(log10(f) + 1e-9))
            p.setPen(GRID_MAJOR if mantissa == 1 else GRID_MINOR)
            p.drawLine(QPointF(x, r.top()), QPointF(x, r.bottom()))
            if mantissa in (1, 2, 5):
                text = frequency_label(f)
                w = fm.horizontalAdvance(text)
                if x - w / 2 > last_label_right + 4:
                    p.setPen(QColor(*L.BLACK))
                    p.drawText(QPointF(x - w / 2, r.bottom() + fm.ascent() + 3), text)
                    last_label_right = x + w / 2
        for k in range(5):  # quarters: phase -s..+s on the left, 0..80 dB on the right
            y = r.bottom() - k / 4 * r.height()
            p.setPen(GRID_MAJOR if k == 2 else GRID_MINOR)
            p.drawLine(QPointF(r.left(), y), QPointF(r.right(), y))
            phase = (k - 2) / 2 * self._scale
            left = f"{phase:+g}" if phase else "0"
            p.setPen(QColor(*L.BLUE))
            p.drawText(
                QPointF(r.left() - fm.horizontalAdvance(left) - 4, y + fm.capHeight() / 2), left
            )
            p.setPen(QColor(*L.RED))
            p.drawText(QPointF(r.right() + 4, y + fm.capHeight() / 2), f"{k * 20}")
        p.setPen(QColor(*L.BLUE))
        p.drawText(QPointF(r.left(), r.top() - 6), "Phase Error Degrees")
        title = "Suppression dB"
        p.setPen(QColor(*L.RED))
        p.drawText(QPointF(r.right() - fm.horizontalAdvance(title), r.top() - 6), title)

    def _curves(self, p: QPainter, r: QRectF, net: Network) -> None:
        xs = np.arange(r.left(), r.right() + 1, dtype=np.float64)
        err = phase_error_deg(self.x_to_f(xs), net.tau1, net.tau2)
        mid, half = r.center().y(), r.height() / 2
        supp = np.minimum(suppression_db(err), 1000)
        for ys, colour in (
            (mid - err / self._scale * half, L.BLUE),
            (r.bottom() - supp / SUPPRESSION_TOP_DB * r.height(), L.RED),
        ):
            ys = np.clip(ys, -10_000, 10_000)
            pen = QPen(QColor(*colour), 2)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            p.drawPolyline(QPolygonF([QPointF(x, y) for x, y in zip(xs, ys, strict=True)]))
