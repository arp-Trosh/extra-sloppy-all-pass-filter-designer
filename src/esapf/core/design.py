# SPDX-License-Identifier: GPL-3.0-only
"""Design of a 90° phase-difference network from two chains of first-order all-pass sections.

Closed-form equiripple (Jacobi elliptic) solution as published by R. Oppelt, DB2NP,
"The Generation and Demodulation of SSB Signals using the Phasing Method",
VHF Communications 2/1987, eqs. 7-12 (after G. Wunsch, Nachrichtentechnik 4/1958).

The default series truncation (5 nome terms, 4 time-constant terms) is exactly what the
original J-Tek program uses; see docs/ORIGINAL_BEHAVIOUR.md §1.
"""

from dataclasses import dataclass
from math import cos, pi, sin, sqrt

# Series for the Jacobi nome q in terms of eps (Oppelt eq. 9): q = sum(a * eps**p).
NOME_SERIES: tuple[tuple[int, int], ...] = (
    (1, 1),
    (2, 5),
    (15, 9),
    (150, 13),
    (1707, 17),
    (20910, 21),
    (268616, 25),
)
ORIGINAL_NOME_TERMS = 5
ORIGINAL_TAU_TERMS = 4


@dataclass(frozen=True)
class Design:
    """Time constants of both paths, in seconds, row order as shown by the original.

    Path 1 holds the poles whose 90° frequency rises row by row, path 2 the reciprocal
    partners (tau1[i] * tau2[i] = 1 / (w1 * w2)).
    """

    tau1: tuple[float, ...]
    tau2: tuple[float, ...]

    @property
    def n(self) -> int:
        return len(self.tau1)


def nome(f1: float, f2: float, terms: int = ORIGINAL_NOME_TERMS) -> float:
    """Jacobi nome q for the band f1..f2 (Oppelt eqs. 7-9). Symmetric in f1, f2."""
    sk = sqrt(f1 / f2)
    eps = 0.5 * (1 - sk) / (1 + sk)
    return sum(a * eps**p for a, p in NOME_SERIES[:terms])


def oppelt_design(
    f1: float,
    f2: float,
    n: int,
    nome_terms: int = ORIGINAL_NOME_TERMS,
    tau_terms: int = ORIGINAL_TAU_TERMS,
) -> Design:
    """Time constants for n sections per path covering f1..f2 Hz (Oppelt eqs. 10-12)."""
    if n < 1:
        raise ValueError("n must be >= 1")
    if f1 <= 0 or f2 <= 0:
        raise ValueError("frequencies must be > 0")
    w1, w2 = 2 * pi * f1, 2 * pi * f2
    q = nome(f1, f2, nome_terms)
    tau1 = []
    for v in range(n):
        k = (4 * v + 1) / (8 * n)
        num = sum(q ** (m * (m + 1)) * cos((2 * m + 1) * pi * k) for m in range(tau_terms))
        den = sum(
            (-1) ** m * q ** (m * (m + 1)) * sin((2 * m + 1) * pi * k) for m in range(tau_terms)
        )
        tau1.append(num / den / sqrt(w1 * w2))
    tau2 = [1 / (w1 * w2 * t) for t in tau1]
    return Design(tuple(tau1), tuple(tau2))


def f90(tau: float) -> float:
    """Frequency (Hz) at which a section with time constant tau shifts by 90°."""
    return 1 / (2 * pi * tau)
