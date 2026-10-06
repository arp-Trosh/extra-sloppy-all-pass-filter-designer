#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Build the single-file GUI executable with PyInstaller for the current OS.

    uv run --group build packaging/build.py        -> dist/esapf-gui[.exe]

PyInstaller cannot cross-compile: the Windows .exe is built on Windows (GitHub Actions).
What goes into the bundle is controlled by packaging/esapf-gui.spec.
"""

import platform
from pathlib import Path

import PyInstaller.__main__

from esapf import __version__

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    print(f"Building esapf-gui {__version__} for {platform.system()} {platform.machine()}")
    PyInstaller.__main__.run(
        [
            str(ROOT / "packaging" / "esapf-gui.spec"),
            "--noconfirm",
            "--clean",
            f"--distpath={ROOT / 'dist'}",
            f"--workpath={ROOT / 'build'}",
        ]
    )


if __name__ == "__main__":
    main()
