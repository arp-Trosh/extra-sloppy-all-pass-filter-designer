# SPDX-License-Identifier: GPL-3.0-only
"""Win32 control access for the original Apf.exe.

Runs INSIDE Wine under the Windows embeddable Python (ctypes only, no third-party packages).
Talks to the VB6 form purely through window messages, so no mouse/keyboard is used.

    python.exe w32.py dump                 -> JSON list of all child controls
    python.exe w32.py run <job.json>       -> execute a job, write JSON result
"""

import ctypes
import json
import os
import sys
import time
from ctypes import wintypes as wt

u32 = ctypes.WinDLL("user32", use_last_error=True)
WNDENUMPROC = ctypes.WINFUNCTYPE(wt.BOOL, wt.HWND, wt.LPARAM)
u32.SendMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]
u32.SendMessageW.restype = ctypes.c_ssize_t
u32.SendMessageTimeoutW.argtypes = [
    wt.HWND,
    wt.UINT,
    wt.WPARAM,
    wt.LPARAM,
    wt.UINT,
    wt.UINT,
    ctypes.POINTER(ctypes.c_size_t),
]
u32.PostMessageW.argtypes = [wt.HWND, wt.UINT, wt.WPARAM, wt.LPARAM]

WM_SETTEXT, WM_GETTEXT, WM_GETTEXTLENGTH = 0x000C, 0x000D, 0x000E
BM_CLICK = 0x00F5
TITLE = "J-Tek All Pass Filter Designer"


def find_form() -> int:
    hwnd = u32.FindWindowW(None, TITLE)
    if not hwnd:
        raise SystemExit(f"window {TITLE!r} not found")
    return hwnd


def get_text(hwnd: int) -> str:
    n = u32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
    buf = ctypes.create_unicode_buffer(n + 1)
    u32.SendMessageW(hwnd, WM_GETTEXT, n + 1, ctypes.addressof(buf))
    return buf.value


def set_text(hwnd: int, text: str) -> None:
    buf = ctypes.create_unicode_buffer(text)
    u32.SendMessageW(hwnd, WM_SETTEXT, 0, ctypes.addressof(buf))


def class_name(hwnd: int) -> str:
    buf = ctypes.create_unicode_buffer(256)
    u32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def rect(hwnd: int, parent: int) -> list[int]:
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    pt = wt.POINT(r.left, r.top)
    u32.ScreenToClient(parent, ctypes.byref(pt))
    return [pt.x, pt.y, r.right - r.left, r.bottom - r.top]


def screen_rect(hwnd: int) -> list[int]:
    r = wt.RECT()
    u32.GetWindowRect(hwnd, ctypes.byref(r))
    return [r.left, r.top, r.right - r.left, r.bottom - r.top]


def children(form: int) -> list[dict]:
    out: list[dict] = []

    def cb(h, _):
        out.append(
            {
                "hwnd": h,
                "class": class_name(h),
                "rect": rect(h, form),
                "visible": bool(u32.IsWindowVisible(h)),
                "text": get_text(h),
            }
        )
        return True

    u32.EnumChildWindows(form, WNDENUMPROC(cb), 0)
    return out


def click(hwnd: int, wait: float = 0.3) -> None:
    # PostMessage so a modal MsgBox raised by the click cannot block us.
    u32.PostMessageW(hwnd, BM_CLICK, 0, 0)
    time.sleep(wait)


def msgboxes() -> list[dict]:
    """Return (and dismiss) any message boxes owned by the app."""
    found: list[dict] = []

    def cb(h, _):
        if class_name(h) == "#32770" and u32.IsWindowVisible(h):
            texts = []
            btns = []

            def ccb(c, _):
                t = get_text(c)
                if class_name(c) == "Button":
                    btns.append(c)
                elif t:
                    texts.append(t)
                return True

            u32.EnumChildWindows(h, WNDENUMPROC(ccb), 0)
            found.append({"title": get_text(h), "text": texts})
            if btns:
                click(btns[0], 0.2)
        return True

    u32.EnumWindows(WNDENUMPROC(cb), 0)
    return found


def main() -> None:
    cmd = sys.argv[1]
    form = find_form()
    if cmd == "dump":
        print(json.dumps(children(form), indent=1))
    elif cmd == "run":
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import job_runner  # noqa: PLC0415  (same directory)

        with open(sys.argv[2], encoding="utf-8") as f:
            job = json.load(f)
        res = job_runner.run(form, job)
        with open(sys.argv[3], "w", encoding="utf-8") as f:
            json.dump(res, f, indent=1)


if __name__ == "__main__":
    main()
