#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Capture reference fixtures from the original Apf.exe running under Wine on Xvfb.

Runs on the Linux host (stdlib only). Everything happens on a private virtual X display,
so the user's desktop, mouse and keyboard are never touched.

    tools/oracle/capture.py [case-id ...]      (default: all cases in cases.py)

Requires: Xvfb, xdotool, ImageMagick `import`, and `tools/wine.sh setup --oracle`.
Output: tests/fixtures/original/<case>.json, <case>_<step>.png (graph area) and
<case>_<step>_form.png (whole window, for selected steps).
"""

import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(Path(__file__).parent))
from cases import CASES  # noqa: E402

DISPLAY = os.environ.get("ESAPF_XVFB_DISPLAY", ":99")
OUT = ROOT / "tests" / "fixtures" / "original"
PYWIN = ROOT / ".tools" / "pywin" / "python.exe"
W32 = ROOT / "tools" / "oracle" / "w32.py"
ENV = {k: v for k, v in os.environ.items() if k != "WAYLAND_DISPLAY"} | {
    "DISPLAY": DISPLAY,
    "WINEPREFIX": str(ROOT / ".wine"),
    "WINEDEBUG": "-all",
}


def winpath(p: Path) -> str:
    return "Z:" + str(p).replace("/", "\\")


def ensure_xvfb() -> None:
    sock = Path(f"/tmp/.X11-unix/X{DISPLAY.lstrip(':')}")
    if not sock.exists():
        subprocess.Popen(
            ["Xvfb", DISPLAY, "-screen", "0", "1024x768x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(50):
            if sock.exists():
                return
            time.sleep(0.1)
        raise SystemExit("Xvfb did not start")


def window_up() -> bool:
    r = subprocess.run(
        ["xdotool", "search", "--name", "^J-Tek All Pass Filter Designer$"],
        env=ENV,
        capture_output=True,
    )
    return r.returncode == 0


def restart_app() -> None:
    subprocess.run(["wineserver", "-k"], env=ENV, capture_output=True)
    time.sleep(0.5)
    subprocess.Popen(
        ["wine", "apf.exe"],
        cwd=ROOT / "reference" / "original",
        env=ENV,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    for _ in range(150):
        if window_up():
            time.sleep(0.5)
            return
        time.sleep(0.1)
    raise SystemExit("Apf.exe window did not appear")


def run_job(ops: list) -> dict:
    with tempfile.TemporaryDirectory(dir=ROOT / ".tools") as td:
        job, res = Path(td) / "job.json", Path(td) / "res.json"
        job.write_text(json.dumps({"ops": [*ops, ["geom"]]}))
        p = subprocess.run(
            ["wine", str(PYWIN), str(W32), "run", winpath(job), winpath(res)],
            env=ENV,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if not res.exists():
            return {"error": (p.stdout + p.stderr).strip()[-2000:], "alive": window_up()}
        out = json.loads(res.read_text())
        out["alive"] = window_up()
        return out


def screenshot(rect: list[int], dest: Path) -> None:
    x, y, w, h = rect
    subprocess.run(
        [
            "import",
            "-display",
            DISPLAY,
            "-window",
            "root",
            "-crop",
            f"{w}x{h}+{x}+{y}",
            "+repage",
            str(dest),
        ],
        check=True,
    )


def capture(cid: str) -> None:
    spec = CASES[cid]
    restart_app()
    steps = []
    for i, step in enumerate(spec["steps"], start=1):
        res = run_job(step["ops"])
        rec = {"ops": step["ops"], **res}
        if step.get("shot") and res.get("alive") and "graph_screen_rect" in res:
            time.sleep(0.3)
            png = OUT / f"{cid}_{i}.png"
            screenshot(res["graph_screen_rect"], png)
            rec["graph_png"] = png.name
        if step.get("form_shot") and res.get("alive") and "form_screen_rect" in res:
            png = OUT / f"{cid}_{i}_form.png"
            screenshot(res["form_screen_rect"], png)
            rec["form_png"] = png.name
        steps.append(rec)
    (OUT / f"{cid}.json").write_text(
        json.dumps({"id": cid, "description": spec["description"], "steps": steps}, indent=1) + "\n"
    )
    alive = all(s.get("alive") for s in steps)
    boxes = sum(len(s.get("msgboxes", [])) for s in steps)
    print(f"{cid:40s} steps={len(steps)} msgboxes={boxes} {'ok' if alive else 'APP DIED'}")


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    ensure_xvfb()
    for cid in sys.argv[1:] or list(CASES):
        capture(cid)
    subprocess.run(["wineserver", "-k"], env=ENV, capture_output=True)


if __name__ == "__main__":
    main()
