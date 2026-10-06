# SPDX-License-Identifier: GPL-3.0-only
"""Unit tests of the maths core against the published article and basic identities."""

from math import pi, sqrt
from pathlib import Path

import numpy as np
import pytest

from esapf.cli import main
from esapf.core import (
    Network,
    Section,
    band_stats,
    chain_phase_deg,
    nome,
    oppelt_design,
    phase_error_deg,
    suppression_db,
)
from esapf.core.legacy import InputError, format_f, format_r, parse_components, vb_val

# --- Oppelt, VHF Communications 2/1987, worked example: 270-3600 Hz, n = 4 ----------------


def test_oppelt_auxiliary_quantities() -> None:
    k = 270 / 3600
    assert k == pytest.approx(0.075)
    eps = 0.5 * (1 - sqrt(k)) / (1 + sqrt(k))
    assert eps == pytest.approx(0.285, abs=5e-4)  # article: 0.285
    assert nome(270, 3600) == pytest.approx(0.289, abs=5e-4)  # article: 0.289


def test_oppelt_worked_example_time_constants() -> None:
    d = oppelt_design(270, 3600, 4)
    # Article values in µs. tau_02 is printed as 2344.6; the series gives 2344.8 (0.01 %).
    assert np.array(d.tau1) * 1e6 == pytest.approx([2344.6, 369.52, 123.44, 36.173], rel=2e-4)
    assert np.array(d.tau2) * 1e6 == pytest.approx([11.114, 70.524, 211.11, 720.43], rel=2e-4)


def test_oppelt_worked_example_phase_error() -> None:
    d = oppelt_design(270, 3600, 4)
    st = band_stats(270, 3600, d.tau1, d.tau2, points=5001)
    assert st.max_abs_error_deg == pytest.approx(0.011, abs=0.0005)  # article: 0.011°


# --- Design identities ---------------------------------------------------------------------


@pytest.mark.parametrize("n", range(1, 9))
def test_reciprocal_pairs_and_ordering(n: int) -> None:
    d = oppelt_design(300, 3000, n)
    w1w2 = (2 * pi * 300) * (2 * pi * 3000)
    assert np.array(d.tau1) * np.array(d.tau2) == pytest.approx(1 / w1w2)
    assert list(d.tau1) == sorted(d.tau1, reverse=True)  # path-1 f90 rises row by row


def test_symmetric_in_band_edges() -> None:
    a, b = oppelt_design(270, 3600, 3), oppelt_design(3600, 270, 3)
    assert a.tau1 == pytest.approx(b.tau1, rel=1e-14)
    assert a.tau2 == pytest.approx(b.tau2, rel=1e-14)


@pytest.mark.parametrize(("f1", "f2", "n"), [(300, 3000, 3), (270, 3600, 4), (50, 5000, 6)])
def test_equiripple_error_in_band(f1: float, f2: float, n: int) -> None:
    """The phase error ripples symmetrically about zero across the band."""
    d = oppelt_design(f1, f2, n, nome_terms=7, tau_terms=8)
    f = np.geomspace(f1, f2, 20001)
    e = phase_error_deg(f, d.tau1, d.tau2)
    assert e.max() == pytest.approx(-e.min(), rel=2e-2)


def test_more_sections_reduce_error() -> None:
    errs = []
    for n in range(1, 7):
        d = oppelt_design(270, 3600, n)
        errs.append(band_stats(270, 3600, d.tau1, d.tau2).max_abs_error_deg)
    assert errs == sorted(errs, reverse=True)


@pytest.mark.parametrize("bad", [(0, 3600, 3), (270, -1, 3), (270, 3600, 0)])
def test_design_rejects_invalid_arguments(bad: tuple[float, float, int]) -> None:
    with pytest.raises(ValueError):
        oppelt_design(*bad)


# --- All-pass and metrics --------------------------------------------------------------------


def test_single_section_is_90_degrees_at_f90() -> None:
    s = Section(r_kohm=15.9155, c_nf=10)  # tau = 159.155 µs -> f90 = 1000 Hz
    assert s.f90 == pytest.approx(1000, rel=1e-5)
    assert chain_phase_deg(1000, [s.tau]) == pytest.approx(90, abs=1e-3)
    assert chain_phase_deg(0, [s.tau]) == 0
    assert chain_phase_deg(1e9, [s.tau]) == pytest.approx(180, abs=1e-3)


def test_suppression_reference_points() -> None:
    assert suppression_db(1.0) == pytest.approx(41.18, abs=0.01)  # "about 41 dB" (GJ3RAX)
    assert suppression_db(0.0) == np.inf
    assert suppression_db(-2.0) == suppression_db(2.0)
    # General amplitude-imbalance form reduces to the A = 1 formula.
    assert suppression_db(3.0, amplitude_ratio=1.0 + 1e-12) == pytest.approx(suppression_db(3.0))
    # Pure amplitude error: A = 0.9, no phase error -> 20 log10(1.9/0.1)
    assert suppression_db(0.0, amplitude_ratio=0.9) == pytest.approx(25.575, abs=1e-3)


def test_network_from_design_round_trip() -> None:
    d = oppelt_design(270, 3600, 3)
    net = Network.from_design(d, c_nf=4.7)
    assert all(s.c_nf == 4.7 for s in net.path1 + net.path2)
    assert net.tau1 == pytest.approx(d.tau1)
    assert net.tau2 == pytest.approx(d.tau2)


# --- Original-program compatibility ----------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("270", 270),
        (" 3 600 ", 3600),
        ("4.7nF", 4.7),
        ("abc", 0),
        ("", 0),
        ("-10", -10),
        (".5", 0.5),
        ("1e3", 1000),
        ("1D2", 100),
        ("12.5.3", 12.5),
    ],
)
def test_vb_val(text: str, value: float) -> None:
    assert vb_val(text) == value


def test_display_formats() -> None:
    assert format_r(0.67899) == "0.678990"
    assert format_r(174.45675) == "174.456750"
    assert format_f(315.8) == "315"
    assert format_f(91.99) == "91"


def test_parse_components() -> None:
    assert parse_components(["1", "2.5"]) == [1, 2.5]
    for cells in ([], ["1", "0"], ["1", ""], ["-1"]):
        with pytest.raises(InputError):
            parse_components(cells)


# --- CLI ---------------------------------------------------------------------------------------


def test_cli_design(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["design", "270", "3600", "-n", "3", "-c", "10"]) == 0
    out = capsys.readouterr().out
    assert "174.456750" in out and "10654" in out and "50.401917" in out


def test_cli_design_validation(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["design", "5", "3600"]) == 2
    assert "F1 should not be below 10 Hz" in capsys.readouterr().err


def test_cli_analyse_csv(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    out = tmp_path / "sweep.csv"
    rc = main(
        [
            "analyse",
            "--path1",
            "649:2.7,232:1,52.3:1",
            "--path2",
            "15:1,113:1,511:1",
            "--band",
            "300",
            "3000",
            "--csv",
            str(out),
            "--points",
            "11",
        ]
    )
    assert rc == 0
    assert "min suppression 46.7 dB" in capsys.readouterr().out  # GJ3RAX: "exceed 45 dB"
    lines = out.read_text().splitlines()
    assert lines[0] == "frequency_hz,phase_error_deg,suppression_db" and len(lines) == 12
