# SPDX-License-Identifier: GPL-3.0-only
"""IEC 60063 preferred-number series (E6 ... E192) and nearest-value lookup."""

from bisect import bisect_left
from math import floor, log10

_E24 = (
    1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1,
)  # fmt: skip


def _computed(n: int) -> tuple[float, ...]:
    """E48/E96/E192: 3 significant figures of 10^(i/n), with the one IEC exception."""
    values = [round(10 ** (i / n), 2) for i in range(n)]
    if n == 192:
        values[185] = 9.20  # IEC 60063 lists 920, not the computed 919
    return tuple(values)


SERIES: dict[str, tuple[float, ...]] = {
    "E6": _E24[::4],
    "E12": _E24[::2],
    "E24": _E24,
    "E48": _computed(48),
    "E96": _computed(96),
    "E192": _computed(192),
}


def nearest(value: float, series: str) -> float:
    """The series value closest to value (smallest absolute, hence relative, error)."""
    if value <= 0:
        raise ValueError("value must be > 0")
    d = floor(log10(value))
    if value >= 10.0 ** (d + 1):  # log10 rounding just below a power of ten
        d += 1
    candidates = [round(m * 10.0**d, 12 - d) for m in SERIES[series]] + [10.0 ** (d + 1)]
    i = bisect_left(candidates, value)
    if i == 0:
        return candidates[0]
    below, above = candidates[i - 1], candidates[min(i, len(candidates) - 1)]
    return below if value - below <= above - value else above


def values_between(series: str, lo: float, hi: float) -> list[float]:
    """All values of a series from lo to hi inclusive, ascending."""
    out = []
    for d in range(floor(log10(lo)) - 1, floor(log10(hi)) + 2):
        for m in SERIES[series]:
            v = round(m * 10.0**d, 12 - d)
            if lo * (1 - 1e-9) <= v <= hi * (1 + 1e-9):
                out.append(v)
    return out


# Parts below value / PAIR_MIN_RATIO change the sum by less than 0.1 % and are not considered.
PAIR_MIN_RATIO = 1000.0


def nearest_pair(value: float, series: str) -> tuple[float, float]:
    """Two series values (larger first) whose sum is closest to value.

    On a tie the pair with the larger main resistor wins, so the second part is a trim."""
    if value <= 0:
        raise ValueError("value must be > 0")
    parts = values_between(series, value / PAIR_MIN_RATIO, value)  # spans 3 decades
    best = (parts[-1], parts[0])
    best_err = abs(sum(best) - value)
    for i in range(len(parts) - 1, -1, -1):
        a = parts[i]
        j = bisect_left(parts, value - a, 0, i + 1)  # b <= a
        for b in parts[max(j - 1, 0) : min(j + 1, i + 1)]:
            err = abs(a + b - value)
            if err < best_err - 1e-9 * value:
                best, best_err = (a, b), err
    return best
