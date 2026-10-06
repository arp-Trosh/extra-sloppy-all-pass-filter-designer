# SPDX-License-Identifier: GPL-3.0-only
"""Phase-error / suppression graph, drawn exactly like the original PictureBox
(docs/ORIGINAL_BEHAVIOUR.md §4). Coordinates are widget pixels of the 455 x 209 box."""

import numpy as np
from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QPen, QPolygonF
from PySide6.QtWidgets import QWidget

from esapf.core import Network, phase_error_deg, suppression_db
from esapf.gui import layout as L

WIDTH, HEIGHT = L.GRAPH[2], L.GRAPH[3]
CLIENT = (2, 2, WIDTH - 4, HEIGHT - 4)  # inside the 2-px sunken border
V_DASHED = (70, 110, 138, 160, 177, 193, 206, 217, 295, 335, 363, 385, 403, 418, 431, 443)
H_DASHED = (53, 156)
V_AXIS, H_AXIS = 226, 104  # 2-px solid lines at x = 226..227 and y = 104..105
DASH, GAP = 3, 3


def x_to_f(x: np.ndarray) -> np.ndarray:
    """Pixel column -> frequency: 100 Hz at x = 1, 10 kHz at x = 454 (two decades)."""
    return np.asarray(100 * 10 ** ((x - 1) / 226.5), dtype=np.float64)


def phase_to_y(error_deg: np.ndarray, scale: float) -> np.ndarray:
    return np.asarray(104 - error_deg / scale * 103, dtype=np.float64)


def suppression_to_y(s_db: np.ndarray) -> np.ndarray:
    return np.asarray(208 - np.minimum(s_db, 1000) / 80 * 207, dtype=np.float64)


def qcolor(rgb: tuple[int, int, int]) -> QColor:
    return QColor(*rgb)


class GraphWidget(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setFixedSize(WIDTH, HEIGHT)
        self._network: Network | None = None
        self._scale = 1.0

    def set_data(self, network: Network | None, scale: float) -> None:
        self._network, self._scale = network, scale
        self.update()

    # --- painting --------------------------------------------------------------------------

    def paintEvent(self, event: QPaintEvent) -> None:  # noqa: N802 (Qt API)
        p = QPainter(self)
        p.fillRect(0, 0, WIDTH, HEIGHT, qcolor(L.WHITE))
        self._border(p)
        p.setClipRect(*CLIENT)
        self._grid(p)
        if self._network is not None:
            self._curves(p, self._network)
        p.end()

    def _border(self, p: QPainter) -> None:
        w, h = WIDTH - 1, HEIGHT - 1
        for colour, lines in (
            (L.SHADOW_OUTER, [(0, 0, w, 0), (0, 0, 0, h)]),
            (L.SHADOW_INNER, [(1, 1, w - 1, 1), (1, 1, 1, h - 1)]),
            (L.LIGHT_INNER, [(1, h - 1, w - 1, h - 1), (w - 1, 1, w - 1, h - 1)]),
            (L.WHITE, [(0, h, w, h), (w, 0, w, h)]),
        ):
            p.setPen(qcolor(colour))
            for line in lines:
                p.drawLine(*line)

    def _grid(self, p: QPainter) -> None:
        black = qcolor(L.BLACK)
        x0, y0, cw, ch = CLIENT
        for x in V_DASHED:
            for y in range(y0, y0 + ch, DASH + GAP):
                p.fillRect(x, y, 1, DASH, black)
        for y in H_DASHED:
            for x in range(x0, x0 + cw, DASH + GAP):
                p.fillRect(x, y, DASH, 1, black)
        p.fillRect(V_AXIS, y0, 2, ch, black)
        p.fillRect(x0, H_AXIS, cw, 2, black)

    def _curves(self, p: QPainter, net: Network) -> None:
        xs = np.arange(1, WIDTH, dtype=np.float64)
        err = phase_error_deg(x_to_f(xs), net.tau1, net.tau2)
        for ys, colour in (
            (phase_to_y(err, self._scale), L.BLUE),
            (suppression_to_y(suppression_db(err)), L.RED),
        ):
            ys = np.clip(ys, -10_000, 10_000)
            pen = QPen(qcolor(colour), 2)
            pen.setCapStyle(Qt.PenCapStyle.FlatCap)
            p.setPen(pen)
            # +0.5: a fitted pixel row/column index refers to the pixel's centre.
            points = [QPointF(x + 0.5, y + 0.5) for x, y in zip(xs, ys, strict=True)]
            p.drawPolyline(QPolygonF(points))
