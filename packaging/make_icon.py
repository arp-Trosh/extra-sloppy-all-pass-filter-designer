#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Generate the application icon: sine and cosine (90° apart) on the original's cyan.

uv run packaging/make_icon.py      -> src/esapf/gui/icon.png, packaging/icon.ico
"""

from math import hypot, pi, sin
from pathlib import Path

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SIZE = 256


def stroke(d: ImageDraw.ImageDraw, pts: list[tuple[float, float]], r: float, fill: tuple) -> None:
    """Smooth thick polyline: stamp discs densely along the path."""
    for (x0, y0), (x1, y1) in zip(pts, pts[1:], strict=False):
        steps = max(1, int(hypot(x1 - x0, y1 - y0) / (r / 4)))
        for k in range(steps + 1):
            x, y = x0 + (x1 - x0) * k / steps, y0 + (y1 - y0) * k / steps
            d.ellipse((x - r, y - r, x + r, y + r), fill=fill)


def draw() -> Image.Image:
    s = 4  # supersample
    n = SIZE * s
    im = Image.new("RGBA", (n, n), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle((8 * s, 8 * s, n - 8 * s, n - 8 * s), radius=40 * s,
                        fill=(192, 255, 255), outline=(0, 0, 0), width=8 * s)  # fmt: skip
    d.line((24 * s, n // 2, n - 24 * s, n // 2), fill=(0, 0, 0), width=5 * s)
    # sine (blue) and cosine (red): the two outputs of a 90° phase-difference network
    x0, x1, amp = 30 * s, n - 30 * s, 80 * s
    for phase, colour in ((0.0, (0, 0, 255)), (pi / 2, (255, 0, 0))):
        pts = [
            (x0 + (x1 - x0) * i / 200, n / 2 - amp * sin(2 * pi * 1.25 * i / 200 + phase))
            for i in range(201)
        ]
        stroke(d, pts, 9 * s, colour)
    return im.resize((SIZE, SIZE), Image.Resampling.LANCZOS)


def main() -> None:
    im = draw()
    im.save(ROOT / "src" / "esapf" / "gui" / "icon.png")
    im.save(ROOT / "packaging" / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print("icon written")


if __name__ == "__main__":
    main()
