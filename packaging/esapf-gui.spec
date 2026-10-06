# SPDX-License-Identifier: GPL-3.0-only
# PyInstaller spec for the single-file GUI executable. Run via packaging/build.py.
# -*- mode: python -*-
import re
from pathlib import Path

ROOT = Path(SPECPATH).parent  # noqa: F821 (SPECPATH is injected by PyInstaller)

# Python modules the app never imports.
EXCLUDES = [
    "tkinter", "PIL", "pytest", "ssl", "_ssl", "PySide6.QtNetwork", "PySide6.QtQml", "PySide6.QtQuick",
    "PySide6.QtPdf", "PySide6.QtWebEngineCore", "PySide6.QtMultimedia", "PySide6.QtSvg",
]

# Qt plugins that pull in large libraries (Qt Quick/Qml via the virtual keyboard, QtPdf,
# GTK + a second ICU via the gtk3 theme) or target platforms a desktop app never uses.
DROP = re.compile(
    r"plugins/(egldeviceintegrations|generic)/"
    r"|plugins/platforms/(?!(lib)?q(xcb|wayland|windows|direct2d|offscreen))"
    r"|plugins/platformthemes/libqgtk3"
    r"|plugins/platforminputcontexts/libqtvirtualkeyboard"
    r"|plugins/imageformats/(?!(lib)?qico)"
    r"|plugins/iconengines/"
)
# Libraries only reachable through the dropped plugins, plus fontconfig: an old bundled
# fontconfig cannot parse newer distributions' /etc/fonts, so use the host's (always present).
DROP_LIBS = re.compile(r"(Qt6(Quick|Qml|Pdf|VirtualKeyboard|Network|Svg)\w*\.(so|dll))"
                       r"|^lib(gtk-3|gdk-3|cairo|glycin|icu\w+\.so\.7[89]|fontconfig\.so)")

a = Analysis(  # noqa: F821
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT / "src")],
    datas=[(str(ROOT / "src" / "esapf" / "gui" / "icon.png"), "esapf/gui"),
           (str(ROOT / "LICENSE"), ".")],
    excludes=EXCLUDES,
)


def keep(entry):
    dest = entry[0].replace("\\", "/")
    return not (DROP.search(dest) or DROP_LIBS.search(Path(dest).name))


a.binaries = [b for b in a.binaries if keep(b)]
a.datas = [d for d in a.datas if not d[0].replace("\\", "/").startswith("PySide6/Qt/translations")]

pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="esapf-gui",
    console=False,
    icon=str(ROOT / "packaging" / "icon.ico"),
    upx=False,
)
