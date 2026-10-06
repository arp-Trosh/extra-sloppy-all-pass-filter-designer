#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Check the reconstructed maths against the captured fixtures of the original Apf.exe.

This is the evidence behind docs/ORIGINAL_BEHAVIOUR.md. It deliberately contains its own
small reference model (independent of src/esapf) so the Phase 1 conclusions can be re-run.

    uv run tools/oracle/verify_model.py
"""

import json
from math import atan, cos, degrees, log10, pi, radians, sin, sqrt, tan
from pathlib import Path

from PIL import Image

FIX = Path(__file__).resolve().parents[2] / "tests" / "fixtures" / "original"
Q_COEFFS = [(1, 1), (2, 5), (15, 9), (150, 13), (1707, 17), (20910, 21)]


def design(f1: float, f2: float, n: int, q_terms: int = 5, tau_terms: int = 4):
    """Oppelt (VHF Comms 2/1987) eqs. 7-12. Returns (tau_path1, tau_path2) in seconds."""
    w1, w2 = 2 * pi * f1, 2 * pi * f2
    k = w1 / w2
    eps = 0.5 * (1 - sqrt(k)) / (1 + sqrt(k))
    q = sum(a * eps**p for a, p in Q_COEFFS[:q_terms])
    tau1 = []
    for v in range(n):
        kv = (4 * v + 1) / (8 * n)
        num = sum(q ** (m * (m + 1)) * cos((2 * m + 1) * pi * kv) for m in range(tau_terms))
        den = sum(
            (-1) ** m * q ** (m * (m + 1)) * sin((2 * m + 1) * pi * kv) for m in range(tau_terms)
        )
        tau1.append(num / den / sqrt(w1 * w2))
    return tau1, [1 / (w1 * w2 * t) for t in tau1]


def phase_error_deg(f: float, tau1: list[float], tau2: list[float]) -> float:
    w = 2 * pi * f
    return degrees(2 * sum(atan(w * t) for t in tau1) - 2 * sum(atan(w * t) for t in tau2)) - 90


def suppression_db(err_deg: float) -> float:
    return -20 * log10(abs(tan(radians(err_deg) / 2)))


def rows(values: dict[str, str]) -> int:
    return max(
        (int(k.split("_")[1]) for k in values if k.startswith("R1_") and values[k]), default=0
    )


def check_design(q_terms: int, tau_terms: int) -> tuple[int, int, int]:
    """Return (R values checked, R mismatches beyond display rounding, F mismatches)."""
    checked = bad_r = bad_f = 0
    for path in sorted(FIX.glob("design_*.json")):
        v = json.loads(path.read_text())["steps"][-1]["reads"][-1]["values"]
        n = rows(v)
        if not n:
            continue
        c = float(v["C1_1"]) * 1e-9
        tau1, tau2 = design(float(v["F1"]), float(v["F2"]), n, q_terms, tau_terms)
        for i in range(n):
            for rc, fc, t in (("R1", "F1", tau1[i]), ("R2", "F2", tau2[i])):
                checked += 1
                bad_r += f"{t / c / 1e3:.6f}" != v[f"{rc}_{i + 1}"]
                bad_f += int(1 / (2 * pi * t)) != int(v[f"{fc}_{i + 1}"])  # truncation
    return checked, bad_r, bad_f


def graph_rms(cid: str, step: int) -> tuple[float, float]:
    """RMS pixel error of the blue (phase) and red (suppression) curves vs the model."""
    rec = json.loads((FIX / f"{cid}.json").read_text())["steps"][step - 1]
    v = rec["reads"][-1]["values"]
    scale = float(v["ScaleTop"])
    n = rows(v)
    tau1 = [float(v[f"R1_{i}"]) * float(v[f"C1_{i}"]) * 1e-6 for i in range(1, n + 1)]
    tau2 = [float(v[f"R2_{i}"]) * float(v[f"C2_{i}"]) * 1e-6 for i in range(1, n + 1)]
    px = Image.open(FIX / rec["graph_png"]).convert("RGB").load()
    sb = sr = 0.0
    nb = nr = 0
    for x in range(3, 452):
        f = 10 ** (2 + (x - 1) / 226.5)
        e = phase_error_deg(f, tau1, tau2)
        blue = [y for y in range(2, 207) if px[x, y] == (0, 0, 255)]
        red = [y for y in range(2, 207) if px[x, y] == (255, 0, 0)]
        if blue and max(blue) - min(blue) <= 3:
            sb += (sum(blue) / len(blue) - (104 - e / scale * 103)) ** 2
            nb += 1
        s = suppression_db(e) if e else 999.0
        if red and max(red) - min(red) <= 3 and s < 78:
            sr += (sum(red) / len(red) - (208 - s / 80 * 207)) ** 2
            nr += 1
    return sqrt(sb / max(nb, 1)), sqrt(sr / max(nr, 1))


def main() -> None:
    print("Design R/F values (q-series terms, tau-series terms) -> checked, R bad, F bad")
    for qt, tt in [(5, 4), (5, 5), (4, 4), (5, 3)]:
        print(f"  q={qt} tau={tt}: {check_design(qt, tt)}")
    print("Graph RMS pixel error (blue phase, red suppression)")
    for cid, step in [
        ("kk7b", 2),
        ("an1981", 2),
        ("n4bcu", 2),
        ("design_270_3600_n1", 1),
        ("design_270_3600_n6", 1),
        ("design_50_5000_n5_c10", 1),
    ]:
        b, r = graph_rms(cid, step)
        print(f"  {cid:24s} blue {b:5.2f}px  red {r:5.2f}px")


if __name__ == "__main__":
    main()
