# SPDX-License-Identifier: GPL-3.0-only
"""Regression tests against the behaviour captured from the original Apf.exe (Phase 1).

See docs/ORIGINAL_BEHAVIOUR.md for the specification these fixtures back up.
"""

import numpy as np
import pytest
from PIL import Image

from esapf.core import Network, oppelt_design, phase_error_deg, suppression_db
from esapf.core.legacy import (
    InputError,
    format_f,
    format_r,
    parse_components,
    parse_design_inputs,
    vb_val,
)
from oracle import Read, reads

ALL = list(reads())


def sets_cells(r: Read) -> bool:
    return any(op[0] == "set" and "_" in op[1] for op in r.ops)


DESIGN_READS = [
    r
    for r in ALL
    if r.rows
    and not r.msgboxes
    and (r.clicked("Design") or r.label.startswith("scale_"))
    and not sets_cells(r)
]
PHASE_READS = [r for r in ALL if r.clicked("Phase") and not r.msgboxes]
VALIDATION_READS = [r for r in ALL if r.clicked("Design") or r.clicked("Phase")]
GRAPH_READS = [
    r
    for r in ALL
    if r.graph_png
    and r.rows
    and not r.msgboxes
    and (r.clicked("Design") or r.clicked("Phase") or r.label.startswith("scale_"))
]


def network_from_table(r: Read) -> Network:
    def col(c: str) -> list[float]:
        return [vb_val(x) for x in r.column(c)]

    return Network.from_values(col("R1"), col("C1"), col("R2"), col("C2"))


def test_fixture_selection_is_not_empty() -> None:
    assert len(DESIGN_READS) >= 25
    assert len(PHASE_READS) >= 6
    assert len(GRAPH_READS) >= 30


@pytest.mark.parametrize("r", DESIGN_READS, ids=lambda r: r.id)
def test_design_table_matches_original(r: Read) -> None:
    inp = parse_design_inputs(r.values["F1"], r.values["F2"], r.values["C"])
    net = Network.from_design(oppelt_design(inp.f1, inp.f2, r.rows), inp.c_nf)
    assert [format_r(s.r_kohm) for s in net.path1] == r.column("R1")
    assert [format_r(s.r_kohm) for s in net.path2] == r.column("R2")
    assert [format_f(s.f90) for s in net.path1] == r.column("F1")
    assert [format_f(s.f90) for s in net.path2] == r.column("F2")
    assert r.column("C1") == r.column("C2") == [r.values["C"]] * r.rows


@pytest.mark.parametrize("r", PHASE_READS, ids=lambda r: r.id)
def test_phase_frequencies_match_original(r: Read) -> None:
    net = network_from_table(r)
    assert [format_f(s.f90) for s in net.path1] == r.column("F1")
    assert [format_f(s.f90) for s in net.path2] == r.column("F2")


@pytest.mark.parametrize("r", VALIDATION_READS, ids=lambda r: r.id)
def test_validation_matches_original(r: Read) -> None:
    expected = r.msgboxes[0] if r.msgboxes else None
    if r.clicked("Design"):
        check = lambda: parse_design_inputs(r.values["F1"], r.values["F2"], r.values["C"])  # noqa: E731
    else:
        cells = [r.values.get(f"{c}_{i}", "") for c in ("R1", "C1", "R2", "C2") for i in (1, 2, 3)]
        check = lambda: parse_components(cells if any(cells) else [])  # noqa: E731
    if expected is None:
        check()
    else:
        with pytest.raises(InputError) as e:
            check()
        assert str(e.value) == expected


# Graph geometry of the original PictureBox (docs/ORIGINAL_BEHAVIOUR.md §4).
def x_to_f(x: np.ndarray) -> np.ndarray:
    return 100 * 10 ** ((x - 1) / 226.5)


def curve_rows(px: np.ndarray, rgb: tuple[int, int, int]) -> dict[int, float]:
    """Mean y of a thin curve of the given colour, per pixel column (thin parts only)."""
    mask = np.all(px == rgb, axis=-1)
    out = {}
    for x in range(3, 452):
        ys = np.nonzero(mask[2:207, x])[0] + 2
        if ys.size and ys.max() - ys.min() <= 3:
            out[x] = float(ys.mean())
    return out


@pytest.mark.parametrize("r", GRAPH_READS, ids=lambda r: r.id)
def test_graph_curves_match_original(r: Read) -> None:
    assert r.graph_png is not None
    net = network_from_table(r)
    scale = float(r.values["ScaleTop"])
    px = np.asarray(Image.open(r.graph_png).convert("RGB"))

    # Only compare where the model curve lies inside the plot; where the original's 2-px
    # line leaves through the top/bottom edge, its visible stub is clipped.
    def rms(points: dict[int, float], model_y: np.ndarray) -> float:
        obs = np.array(list(points.values()))
        inside = (model_y > 4) & (model_y < 204)
        if inside.sum() < 5:
            return 0.0
        return float(np.sqrt(np.mean((obs[inside] - model_y[inside]) ** 2)))

    blue = curve_rows(px, (0, 0, 255))
    xs = np.array(list(blue))
    err = phase_error_deg(x_to_f(xs), net.tau1, net.tau2) if blue else np.array([])
    assert rms(blue, 104 - err / scale * 103) < 1.0

    red = curve_rows(px, (255, 0, 0))
    xs = np.array(list(red))
    s = suppression_db(phase_error_deg(x_to_f(xs), net.tau1, net.tau2)) if red else np.array([])
    assert rms(red, 208 - np.minimum(s, 80) / 80 * 207) < 1.5
