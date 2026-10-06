# SPDX-License-Identifier: GPL-3.0-only
"""Design of a 90° phase-difference network from two chains of first-order all-pass sections.

Closed-form equiripple (Jacobi elliptic) solution as published by R. Oppelt, DB2NP,
"The Generation and Demodulation of SSB Signals using the Phasing Method",
VHF Communications 2/1987, eqs. 7-12 (after G. Wunsch, Nachrichtentechnik 4/1958).

The default series truncation (5 nome terms, 4 time-constant terms) is exactly what the
original J-Tek program uses; see docs/ORIGINAL_BEHAVIOUR.md §1.
"""

from dataclasses import dataclass
from math import cos, exp, isclose, pi, sin, sqrt

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


def _agm(a: float, b: float) -> float:
    """Arithmetic-geometric mean (converges quadratically; the cap guards ulp cycling)."""
    for _ in range(64):
        if isclose(a, b, rel_tol=4e-16, abs_tol=0.0):
            break
        a, b = (a + b) / 2, sqrt(a * b)
    return a


def exact_nome(f1: float, f2: float) -> float:
    """Jacobi nome q = exp(-pi K'/K) for modulus k = sqrt(1 - (F1/F2)^2), without the
    truncated series of eq. 9: K = pi / (2 agm(1, k')), K' = pi / (2 agm(1, k))."""
    kappa = min(f1, f2) / max(f1, f2)  # complementary modulus k'
    if kappa >= 1:
        return 0.0
    k = sqrt((1 - kappa) * (1 + kappa))
    return exp(-pi * _agm(1.0, kappa) / _agm(1.0, k))


def elliptic_design(f1: float, f2: float, total: int) -> Design:
    """Exact equiripple design for any total number of sections, odd or even (U8).

    The N = total poles sit at k_j = (2j + 1) / (4N), j = 0 ... N-1 (for even N this is
    Oppelt's eq. 10), and alternate between the paths: path 1 takes even j, path 2 odd j.
    Pole j and pole N-1-j are reciprocal partners (tau_j tau_{N-1-j} = 1/(w1 w2)). For odd
    N path 1 has one extra section, and the middle pole j = (N-1)/2 is its own partner,
    tau = 1/sqrt(w1 w2); it is in path 1 if N = 1 mod 4, otherwise in path 2. The phase
    error ripples equally with peaks of about 4 q^N radians (docs/FORMULAS.md §4.4).

    q comes from the AGM and eq. 11's theta series is summed to convergence, so this is
    also accurate for very wide bands where the original's truncation is not (§4.3).
    For even N it agrees with oppelt_design(f1, f2, N // 2) to the latter's precision.
    """
    if total < 1:
        raise ValueError("total must be >= 1")
    if f1 <= 0 or f2 <= 0:
        raise ValueError("frequencies must be > 0")
    w1, w2 = 2 * pi * f1, 2 * pi * f2
    q = exact_nome(f1, f2)
    terms = 1
    while terms < 64 and q ** (terms * (terms + 1)) > 1e-18:
        terms += 1
    taus = []
    for j in range(total):
        k = (2 * j + 1) / (4 * total)
        num = sum(q ** (m * (m + 1)) * cos((2 * m + 1) * pi * k) for m in range(terms))
        den = sum((-1) ** m * q ** (m * (m + 1)) * sin((2 * m + 1) * pi * k) for m in range(terms))
        taus.append(num / den / sqrt(w1 * w2))
    # Row order as in the original: path 1 f90 rising, path 2 f90 falling.
    return Design(tuple(taus[0::2]), tuple(sorted(taus[1::2])))


def f90(tau: float) -> float:
    """Frequency (Hz) at which a section with time constant tau shifts by 90°."""
    return 1 / (2 * pi * tau)
