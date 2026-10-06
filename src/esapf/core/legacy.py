# SPDX-License-Identifier: GPL-3.0-only
"""Behaviour of the original J-Tek program that is not maths: input parsing, display
formats and validation messages (docs/ORIGINAL_BEHAVIOUR.md §3 and §6)."""

import re
from collections.abc import Sequence
from dataclasses import dataclass

MSG_F1 = "F1 should not be below 10 Hz"
MSG_F2 = "F2 should not be below 10 Hz"
MSG_C = "The Capacitor value C(nF) Must be Specified and Greater than Zero"
MSG_COMPONENTS = "All Component Values MUST be Specified and Greater than Zero"
MIN_FREQUENCY_HZ = 10.0

_VB_NUMBER = re.compile(r"[+-]?(\d+\.?\d*|\.\d+)([eEdD][+-]?\d+)?")


def vb_val(text: str) -> float:
    """VB6 ``Val()``: whitespace is ignored, the longest leading number is used, else 0."""
    m = _VB_NUMBER.match(re.sub(r"\s", "", text))
    if not m:
        return 0.0
    return float(m.group(0).replace("d", "e").replace("D", "e"))


def format_r(r_kohm: float) -> str:
    """Resistor display after Design: VB ``Format(r, "####0.000000")``."""
    return f"{r_kohm:.6f}"


def format_f(f_hz: float) -> str:
    """90° frequency display: truncated to an integer (VB ``Int``)."""
    return str(int(f_hz))


class InputError(ValueError):
    """Invalid user input; str(error) is the original program's message box text."""


@dataclass(frozen=True)
class DesignInputs:
    f1: float
    f2: float
    c_nf: float


def parse_design_inputs(f1: str, f2: str, c_nf: str) -> DesignInputs:
    """Validate the Design inputs in the original order; only the first error is raised."""
    values = DesignInputs(vb_val(f1), vb_val(f2), vb_val(c_nf))
    if values.f1 < MIN_FREQUENCY_HZ:
        raise InputError(MSG_F1)
    if values.f2 < MIN_FREQUENCY_HZ:
        raise InputError(MSG_F2)
    if values.c_nf <= 0:
        raise InputError(MSG_C)
    return values


def parse_components(cells: Sequence[str]) -> list[float]:
    """Validate R/C table cells for the Phase button."""
    values = [vb_val(c) for c in cells]
    if not values or any(v <= 0 for v in values):
        raise InputError(MSG_COMPONENTS)
    return values
