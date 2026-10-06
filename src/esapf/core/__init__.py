# SPDX-License-Identifier: GPL-3.0-only
"""Pure maths: all-pass design and analysis. Must not import any GUI module."""

from esapf.core.allpass import chain_phase_deg, phase_difference_deg, phase_error_deg
from esapf.core.design import Design, f90, nome, oppelt_design
from esapf.core.metrics import BandStats, band_stats, log_grid, suppression_db
from esapf.core.network import Network, Section

__all__ = [
    "BandStats",
    "Design",
    "Network",
    "Section",
    "band_stats",
    "chain_phase_deg",
    "f90",
    "log_grid",
    "nome",
    "oppelt_design",
    "phase_difference_deg",
    "phase_error_deg",
    "suppression_db",
]
