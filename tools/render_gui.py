#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Render the Qt window offscreen after replaying a captured case, for visual comparison
with the original (tests/fixtures/original/<case>_<step>_form.png).

    uv run tools/render_gui.py <case> <out.png> [--diff original.png diff.png]
"""

import json
import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))

from PySide6.QtWidgets import QApplication  # noqa: E402

from esapf.gui.main_window import MainWindow  # noqa: E402
from oracle import FIXTURES, apply  # noqa: E402


def main() -> None:
    cid, out = sys.argv[1], sys.argv[2]
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    for step in json.loads((FIXTURES / f"{cid}.json").read_text())["steps"]:
        for op in step["ops"]:
            apply(w.state, op)
    w.refresh()
    w.show()
    app.processEvents()
    w.grab().save(out)
    if "--diff" in sys.argv:
        from PIL import Image, ImageChops

        orig_path, diff_path = sys.argv[sys.argv.index("--diff") + 1 :][:2]
        orig = Image.open(orig_path).convert("RGB")
        orig = orig.crop((3, 29, 523, 503))  # strip the Win32 frame of the capture
        mine = Image.open(out).convert("RGB")
        diff = ImageChops.difference(orig, mine)
        diff.save(diff_path)
        bbox = diff.getbbox()
        same = sum(1 for p in diff.getdata() if p == (0, 0, 0))
        print(f"identical pixels: {same / (520 * 474):.1%}  diff bbox: {bbox}")


if __name__ == "__main__":
    main()
