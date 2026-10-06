# SPDX-License-Identifier: GPL-3.0-only
"""Component-level description of the two-path network (R in kΩ, C in nF, as in the UI)."""

from collections.abc import Sequence
from dataclasses import dataclass

from esapf.core.design import Design, f90

# kΩ * nF = 1e3 * 1e-9 s
KOHM_NF_TO_S = 1e-6


@dataclass(frozen=True)
class Section:
    r_kohm: float
    c_nf: float

    @property
    def tau(self) -> float:
        return self.r_kohm * self.c_nf * KOHM_NF_TO_S

    @property
    def f90(self) -> float:
        return f90(self.tau)


@dataclass(frozen=True)
class Network:
    path1: tuple[Section, ...]
    path2: tuple[Section, ...]

    @property
    def tau1(self) -> tuple[float, ...]:
        return tuple(s.tau for s in self.path1)

    @property
    def tau2(self) -> tuple[float, ...]:
        return tuple(s.tau for s in self.path2)

    @classmethod
    def from_design(cls, design: Design, c_nf: float) -> "Network":
        """All capacitors equal to c_nf; resistors chosen to realise the design."""

        def path(taus: Sequence[float]) -> tuple[Section, ...]:
            return tuple(Section(t / (c_nf * KOHM_NF_TO_S), c_nf) for t in taus)

        return cls(path(design.tau1), path(design.tau2))

    @classmethod
    def from_values(
        cls,
        r1_kohm: Sequence[float],
        c1_nf: Sequence[float],
        r2_kohm: Sequence[float],
        c2_nf: Sequence[float],
    ) -> "Network":
        return cls(
            tuple(Section(r, c) for r, c in zip(r1_kohm, c1_nf, strict=True)),
            tuple(Section(r, c) for r, c in zip(r2_kohm, c2_nf, strict=True)),
        )
