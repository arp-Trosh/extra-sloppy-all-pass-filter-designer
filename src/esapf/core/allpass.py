# SPDX-License-Identifier: GPL-3.0-only
"""Phase response of first-order all-pass sections and of the two-path network.

A first-order section H(jw) = (1 - jw*tau) / (1 + jw*tau) has |H| = 1 and
phase -2*atan(w*tau). The network output is the phase difference between path 1 and 2.
"""

from collections.abc import Sequence

import numpy as np
import numpy.typing as npt

FloatArray = npt.NDArray[np.float64]


def chain_phase_deg(f: npt.ArrayLike, taus: Sequence[float]) -> FloatArray:
    """Phase lag (degrees, positive) of a chain of sections: sum of 2*atan(w*tau)."""
    w = 2 * np.pi * np.asarray(f, dtype=np.float64)
    t = np.asarray(taus, dtype=np.float64)
    return np.degrees(2 * np.arctan(np.multiply.outer(w, t)).sum(axis=-1))


def phase_difference_deg(
    f: npt.ArrayLike, tau1: Sequence[float], tau2: Sequence[float]
) -> FloatArray:
    """Phase of path 2 output relative to path 1 output (Oppelt eq. 13), in degrees."""
    return chain_phase_deg(f, tau1) - chain_phase_deg(f, tau2)


def phase_error_deg(f: npt.ArrayLike, tau1: Sequence[float], tau2: Sequence[float]) -> FloatArray:
    """Deviation from the ideal 90° difference, signed as plotted by the original."""
    return phase_difference_deg(f, tau1, tau2) - 90.0
