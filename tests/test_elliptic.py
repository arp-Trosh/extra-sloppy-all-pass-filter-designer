# SPDX-License-Identifier: GPL-3.0-only
"""The closed forms quoted in docs/FORMULAS.md, checked against exact Jacobi elliptic
functions (mpmath): Oppelt's series = Jacobi nome / cs(), and the ripple ~ 4 q^(2n)."""

from math import pi

import mpmath as mp
import numpy as np
import pytest

from esapf.core import nome, oppelt_design, phase_error_deg

mp.mp.dps = 30


def exact(f1: float, f2: float, n: int) -> tuple[list[float], float]:
    """tau_v = cs(2 K k_v, k) / w1 with modulus k = sqrt(1 - (f1/f2)^2); and the exact nome."""
    m = 1 - (mp.mpf(f1) / f2) ** 2  # parameter m = k^2
    big_k = mp.ellipk(m)
    q = mp.exp(-mp.pi * mp.ellipk(1 - m) / big_k)
    taus = []
    for v in range(n):
        u = 2 * big_k * mp.mpf(4 * v + 1) / (8 * n)
        taus.append(float(mp.ellipfun("cn", u, m=m) / mp.ellipfun("sn", u, m=m)) / (2 * pi * f1))
    return taus, float(q)


def max_error_deg(f1: float, f2: float, tau1: list[float], tau2: list[float]) -> float:
    f = np.geomspace(f1, f2, 100_001)
    return float(np.abs(phase_error_deg(f, tau1, tau2)).max())


@pytest.mark.parametrize(("f1", "f2", "n"), [(270, 3600, 3), (300, 3000, 2), (270, 3600, 6)])
def test_series_equals_jacobi_cs(f1: float, f2: float, n: int) -> None:
    taus, q = exact(f1, f2, n)
    assert nome(f1, f2, terms=7) == pytest.approx(q, rel=1e-8)
    d = oppelt_design(f1, f2, n, nome_terms=7, tau_terms=8)
    assert d.tau1 == pytest.approx(taus, rel=1e-8)


@pytest.mark.parametrize(("f1", "f2", "n"), [(300, 3000, 2), (270, 3600, 3), (50, 5000, 5)])
def test_ripple_is_four_q_to_the_2n(f1: float, f2: float, n: int) -> None:
    taus, q = exact(f1, f2, n)
    w1w2 = (2 * pi * f1) * (2 * pi * f2)
    err = max_error_deg(f1, f2, taus, [1 / (w1w2 * t) for t in taus])
    assert err == pytest.approx(np.degrees(4 * q ** (2 * n)), rel=1e-3)


def test_original_truncation_is_suboptimal_for_very_wide_bands() -> None:
    """Documented limitation of the original: 10 Hz-20 kHz, n = 6."""
    taus, _ = exact(10, 20000, 6)
    w1w2 = (2 * pi * 10) * (2 * pi * 20000)
    best = max_error_deg(10, 20000, taus, [1 / (w1w2 * t) for t in taus])
    d = oppelt_design(10, 20000, 6)
    original = max_error_deg(10, 20000, list(d.tau1), list(d.tau2))
    assert best == pytest.approx(0.315, abs=0.002)
    assert original == pytest.approx(1.57, abs=0.01)
