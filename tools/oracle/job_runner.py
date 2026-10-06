# SPDX-License-Identifier: GPL-3.0-only
"""Execute a scripted job against the original Apf.exe form (runs inside Wine).

A job is {"ops": [[op, *args], ...]} with ops:
    ["set", name, text]      WM_SETTEXT on a named control
    ["click", name]          BM_CLICK on a named button
    ["read", label]          snapshot all named text fields
    ["geom"]                 screen rectangles of the form and the graph PictureBox
    ["sleep", seconds]
Names: F1 F2 C, N1..N6 (filter count), Design ResetC Phase Clear,
       S10 S5 S2 S1 S0.5 S0.2 S0.1 (phase scale), table cells "<col><row>" with
       col in F1 R1 C1 F2 R2 C2 and row 1..6 (e.g. "R2_3"), ScaleTop ScaleBottom.
"""

import time

import w32

COLS = {32: "F1", 104: "R1", 200: "C1", 272: "F2", 344: "R2", 440: "C2"}


def named_controls(form: int) -> dict[str, int]:
    names: dict[str, int] = {}
    for c in w32.children(form):
        x, y, _, _ = c["rect"]
        cls, text = c["class"], c["text"]
        if cls.endswith("PictureBoxDC"):
            names["Graph"] = c["hwnd"]
        elif cls.endswith("TextBox"):
            if (x, y) == (56, 8):
                names["F1"] = c["hwnd"]
            elif (x, y) == (56, 40):
                names["F2"] = c["hwnd"]
            elif (x, y) == (176, 40):
                names["C"] = c["hwnd"]
            elif x == 0:
                names["ScaleTop" if y < 300 else "ScaleBottom"] = c["hwnd"]
            elif 96 <= y <= 176 and x in COLS:
                names[f"{COLS[x]}_{(y - 96) // 16 + 1}"] = c["hwnd"]
        elif cls.endswith("CommandButton"):
            if y == 8 and text in "123456":
                names[f"N{text}"] = c["hwnd"]
            elif y == 440:
                names[f"S{text}"] = c["hwnd"]
            else:
                names[text.replace(" ", "")] = c["hwnd"]
    return names


def is_text_field(name: str) -> bool:
    return name in ("F1", "F2", "C", "ScaleTop", "ScaleBottom") or "_" in name


def snapshot(names: dict[str, int]) -> dict[str, str]:
    return {k: w32.get_text(h) for k, h in sorted(names.items()) if is_text_field(k)}


def run(form: int, job: dict) -> dict:
    names = named_controls(form)
    out: dict = {"reads": [], "msgboxes": []}
    for op, *args in job["ops"]:
        if op == "set":
            w32.set_text(names[args[0]], str(args[1]))
        elif op == "click":
            w32.click(names[args[0]], job.get("wait", 0.4))
            boxes = w32.msgboxes()
            if boxes:
                out["msgboxes"].append({"after": args[0], "boxes": boxes})
        elif op == "read":
            out["reads"].append({"label": args[0], "values": snapshot(names)})
        elif op == "geom":
            out["graph_screen_rect"] = w32.screen_rect(names["Graph"])
            out["form_screen_rect"] = w32.screen_rect(form)
        elif op == "sleep":
            time.sleep(float(args[0]))
        else:
            raise ValueError(op)
    return out
