# SPDX-License-Identifier: GPL-3.0-only
"""Sideband suppression and band statistics."""

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
import numpy.typing as npt

from esapf.core.allpass import FloatArray, phase_error_deg

# Graph range of the original program (fixed, independent of F1/F2).
PLOT_F_MIN = 100.0
PLOT_F_MAX = 10_000.0


def suppression_db(error_deg: npt.ArrayLike, amplitude_ratio: float = 1.0) -> FloatArray:
    """Unwanted-sideband suppression for a phase error (degrees) and amplitude ratio A.

    S = (1 + A^2 + 2A cos e) / (1 + A^2 - 2A cos e); for A = 1 this is -20 log10|tan(e/2)|,
    the formula used by the original. A zero error gives +inf.
    """
    e = np.radians(np.asarray(error_deg, dtype=np.float64))
    a = amplitude_ratio
    with np.errstate(divide="ignore"):
        if a == 1.0:
            return np.asarray(-20 * np.log10(np.abs(np.tan(e / 2))), dtype=np.float64)
        num = 1 + a * a + 2 * a * np.cos(e)
        den = 1 + a * a - 2 * a * np.cos(e)
        return np.asarray(10 * np.log10(num / den), dtype=np.float64)


def log_grid(
    f_min: float = PLOT_F_MIN, f_max: float = PLOT_F_MAX, points: int = 1001
) -> FloatArray:
    """Logarithmically spaced frequencies, inclusive."""
    return np.geomspace(f_min, f_max, points)


@dataclass(frozen=True)
class BandStats:
    max_abs_error_deg: float
    min_suppression_db: float


def band_stats(
    f1: float, f2: float, tau1: Sequence[float], tau2: Sequence[float], points: int = 2001
) -> BandStats:
    """Worst-case phase error and suppression over f1..f2."""
    f = log_grid(min(f1, f2), max(f1, f2), points)
    err = np.abs(phase_error_deg(f, tau1, tau2))
    worst = float(err.max())
    return BandStats(worst, float(suppression_db(worst)))
