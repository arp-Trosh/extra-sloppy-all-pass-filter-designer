# SPDX-License-Identifier: GPL-3.0-only
"""Helpers to read the fixtures captured from the original program (tests/fixtures/original).

Each fixture is a case with steps; a step holds the ops sent to the original, the control
values read back ("reads"), any message boxes, and optionally a graph screenshot.
"""

import json
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from esapf.core.legacy import InputError
from esapf.form import FormState

FIXTURES = Path(__file__).parent / "fixtures" / "original"
COLUMNS = ("F1", "R1", "C1", "F2", "R2", "C2")


@dataclass(frozen=True)
class Read:
    case: str
    step: int
    label: str
    values: dict[str, str]
    ops: list[list[str]]
    msgboxes: list[str]  # message texts raised during this step
    graph_png: Path | None

    @property
    def id(self) -> str:
        return f"{self.case}:{self.step}:{self.label}"

    @property
    def rows(self) -> int:
        return sum(1 for i in range(1, 7) if self.values.get(f"R1_{i}"))

    def column(self, col: str) -> list[str]:
        return [self.values[f"{col}_{i}"] for i in range(1, self.rows + 1)]

    def clicked(self, button: str) -> bool:
        return ["click", button] in self.ops


def reads() -> Iterator[Read]:
    for path in sorted(FIXTURES.glob("*.json")):
        case = json.loads(path.read_text())
        for i, step in enumerate(case["steps"], start=1):
            msgs = [t for m in step.get("msgboxes", []) for b in m["boxes"] for t in b["text"]]
            png = FIXTURES / step["graph_png"] if "graph_png" in step else None
            for r in step["reads"]:
                yield Read(case["id"], i, r["label"], r["values"], step["ops"], msgs, png)


def apply(st: FormState, op: list[str]) -> str | None:
    """Apply one captured op; return the message box text it raised, if any."""
    kind, *args = op
    if kind == "set":
        name, text = args
        if name in ("F1", "F2"):
            setattr(st, name.lower(), text)
        elif name == "C":
            st.c = text
        else:
            col, row = name.split("_")
            st.set_cell(col, int(row), text)
    elif kind == "click":
        button = args[0]
        try:
            if button.startswith("N"):
                st.select_n(int(button[1:]))
            elif button.startswith("S"):
                st.select_scale(button[1:])
            else:
                {"Design": st.design, "Phase": st.phase, "ResetC": st.reset_c,
                 "Clear": st.clear}[button]()  # fmt: skip
        except InputError as e:
            return str(e)
    return None
