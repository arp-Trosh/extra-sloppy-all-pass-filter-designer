# SPDX-License-Identifier: GPL-3.0-only
"""The closed forms quoted in docs/FORMULAS.md, checked against exact Jacobi elliptic
functions (mpmath): Oppelt's series = Jacobi nome / cs(), the ripple ~ 4 q^(2n), and the
exact design for any total number of sections, odd or even (elliptic_design, U8)."""

from math import pi

import mpmath as mp
import numpy as np
import pytest

from esapf.core import elliptic_design, exact_nome, nome, oppelt_design, phase_error_deg

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


def exact_total(f1: float, f2: float, total: int) -> tuple[list[float], float]:
    """All N poles tau_j = cs(2 K k_j, k) / w1 with k_j = (2j + 1) / (4N), and the nome."""
    m = 1 - (mp.mpf(min(f1, f2)) / max(f1, f2)) ** 2
    big_k = mp.ellipk(m)
    q = mp.exp(-mp.pi * mp.ellipk(1 - m) / big_k)
    taus = []
    for j in range(total):
        u = 2 * big_k * mp.mpf(2 * j + 1) / (4 * total)
        cs = mp.ellipfun("cn", u, m=m) / mp.ellipfun("sn", u, m=m)
        taus.append(float(cs) / (2 * pi * min(f1, f2)))
    return taus, float(q)


@pytest.mark.parametrize(("f1", "f2"), [(270, 3600), (300, 3000), (10, 20000), (3600, 270)])
def test_exact_nome(f1: float, f2: float) -> None:
    assert exact_nome(f1, f2) == pytest.approx(exact_total(f1, f2, 1)[1], rel=1e-13)
    assert exact_nome(1000, 1000) == 0.0


@pytest.mark.parametrize("total", [1, 2, 3, 5, 6, 7, 9, 11, 12, 15])
@pytest.mark.parametrize(("f1", "f2"), [(270, 3600), (50, 5000), (10, 100000)])
def test_elliptic_design_equals_jacobi_cs(f1: float, f2: float, total: int) -> None:
    taus, _ = exact_total(f1, f2, total)
    d = elliptic_design(f1, f2, total)
    assert (len(d.tau1), len(d.tau2)) == ((total + 1) // 2, total // 2)
    assert list(d.tau1) == pytest.approx(taus[0::2], rel=1e-12)
    assert list(d.tau2) == pytest.approx(sorted(taus[1::2]), rel=1e-12)


@pytest.mark.parametrize("total", [3, 5, 7, 9, 11])
@pytest.mark.parametrize(("f1", "f2"), [(270, 3600), (300, 3000), (10, 20000)])
def test_odd_totals_are_equiripple(f1: float, f2: float, total: int) -> None:
    """Odd N: equiripple, touching +-max N + 1 times (Chebyshev); max ~ 4 q^N."""
    d = elliptic_design(f1, f2, total)
    w1w2 = (2 * pi * f1) * (2 * pi * f2)
    centre = d.tau1 if total % 4 == 1 else d.tau2  # pole j = (N-1)/2, its own partner
    assert centre[len(centre) // 2] == pytest.approx(1 / np.sqrt(w1w2), rel=1e-12)
    f = np.geomspace(f1, f2, 200_001)
    err = phase_error_deg(f, d.tau1, d.tau2)
    limit = np.degrees(4 * exact_nome(f1, f2) ** total)
    if limit < 1:  # 4 q^N is the small-error asymptote (exact as q^N -> 0)
        assert np.abs(err).max() == pytest.approx(limit, rel=2e-3)
    peaks = np.flatnonzero(np.abs(err) > 0.999 * np.abs(err).max())
    groups = 1 + np.count_nonzero(np.diff(peaks) > 1)
    assert groups == total + 1


@pytest.mark.parametrize(("f1", "f2", "n"), [(270, 3600, 3), (300, 3000, 2), (270, 3600, 6)])
def test_even_total_matches_oppelt(f1: float, f2: float, n: int) -> None:
    d = elliptic_design(f1, f2, 2 * n)
    o = oppelt_design(f1, f2, n)
    assert d.tau1 == pytest.approx(o.tau1, rel=1e-6)
    assert d.tau2 == pytest.approx(o.tau2, rel=1e-6)


def test_elliptic_design_fixes_the_wide_band_limitation() -> None:
    d = elliptic_design(10, 20000, 12)
    assert max_error_deg(10, 20000, list(d.tau1), list(d.tau2)) == pytest.approx(0.315, abs=0.002)


def test_elliptic_design_rejects_bad_input() -> None:
    for args in ((270, 3600, 0), (0, 3600, 3), (270, -1, 3)):
        with pytest.raises(ValueError):
            elliptic_design(*args)
