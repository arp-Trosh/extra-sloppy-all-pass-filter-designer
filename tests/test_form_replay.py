# SPDX-License-Identifier: GPL-3.0-only
"""Replay every captured case's button presses through FormState and compare every field
the original displayed afterwards, plus the message boxes it raised."""

import json

import pytest

from esapf.form import FormState
from oracle import FIXTURES, apply

CASES = sorted(p.stem for p in FIXTURES.glob("*.json"))


def snapshot(st: FormState) -> dict[str, str]:
    out = {"F1": st.f1, "F2": st.f2, "C": st.c}
    out |= {"ScaleTop": f"+{st.scale}", "ScaleBottom": f"-{st.scale}"}
    for col, cells in st.cells.items():
        out |= {f"{col}_{i}": v for i, v in enumerate(cells, start=1)}
    return out


@pytest.mark.parametrize("cid", CASES)
def test_replay_matches_original(cid: str) -> None:
    case = json.loads((FIXTURES / f"{cid}.json").read_text())
    st = FormState()
    for step in case["steps"]:
        msgs: list[str] = []
        for op in step["ops"]:
            if op[0] == "read":
                expected = next(r["values"] for r in step["reads"] if r["label"] == op[1])
                assert snapshot(st) == expected, f"{cid}: {op[1]}"
            elif (m := apply(st, op)) is not None:
                msgs.append(m)
        expected_msgs = [t for m in step.get("msgboxes", []) for b in m["boxes"] for t in b["text"]]
        assert msgs == expected_msgs


def test_startup_state() -> None:
    st = FormState()
    assert (st.f1, st.f2, st.c, st.n, st.scale, st.network) == ("270", "3600", "10", 3, "1", None)
