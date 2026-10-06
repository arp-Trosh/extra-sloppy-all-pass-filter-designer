# SPDX-License-Identifier: GPL-3.0-only
"""Geometry, colours, fonts and texts of the original 2002 window (client pixels).

Control rectangles come from the Win32 dump of the original (tools/oracle/w32.py dump);
static-text positions were measured from tests/fixtures/original/form_*_form.png.
"""

from dataclasses import dataclass

WINDOW_SIZE = (520, 474)

# Colours (RGB)
FORM_BG = (192, 255, 255)
BUTTON_FACE = (212, 208, 200)
SELECTED = (255, 255, 191)  # selected n / scale button, inactive table rows
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
SHADOW_OUTER = (166, 166, 166)
SHADOW_INNER = (106, 106, 106)
LIGHT_INNER = (227, 227, 227)

# TrueType fonts only: "MS Sans Serif" (the original's font) is a bitmap font on Windows,
# which Qt renders without bold and with wrong metrics. Microsoft Sans Serif is its
# TrueType successor (shipped with Windows 10/11); Liberation Sans is metric-compatible Arial.
FONT_FAMILIES = ["Microsoft Sans Serif", "Arial", "Liberation Sans", "Helvetica", "DejaVu Sans"]
FONT_LARGE_PX = 14  # ~10 pt bold MS Sans Serif: labels, inputs, buttons (width-matched)
FONT_SMALL_PX = 12  # ~8 pt bold: table, headers, axis labels (width-matched)

Rect = tuple[int, int, int, int]

# --- Controls --------------------------------------------------------------------------------
F1_BOX: Rect = (56, 8, 57, 24)
F2_BOX: Rect = (56, 40, 57, 24)
C_BOX: Rect = (176, 40, 41, 24)
N_BUTTONS: list[Rect] = [(176 + 32 * i, 8, 33, 25) for i in range(6)]
DESIGN_BUTTON: Rect = (376, 8, 137, 25)
RESET_C_BUTTON: Rect = (224, 40, 73, 25)
PHASE_BUTTON: Rect = (304, 40, 65, 25)
CLEAR_BUTTON: Rect = (376, 40, 65, 25)
EXIT_BUTTON: Rect = (448, 40, 65, 25)
SCALE_BUTTONS: list[Rect] = [(120 + 40 * i, 440, 41, 25) for i in range(7)]
GRAPH: Rect = (32, 216, 455, 209)
SCALE_TOP: Rect = (0, 216, 29, 19)
SCALE_BOTTOM: Rect = (0, 408, 30, 19)

TABLE_COLUMNS = {"F1": (32, 73), "R1": (104, 97), "C1": (200, 49),
                 "F2": (272, 73), "R2": (344, 97), "C2": (440, 49)}  # fmt: skip
TABLE_TOP, TABLE_ROW_STEP, TABLE_ROW_HEIGHT = 96, 16, 19


def cell_rect(col: str, row: int) -> Rect:
    """Rectangle of a table cell; row is 1-based."""
    x, w = TABLE_COLUMNS[col]
    return (x, TABLE_TOP + TABLE_ROW_STEP * (row - 1), w, TABLE_ROW_HEIGHT)


# --- Static texts: (left, cap-top, text, colour, large?) -------------------------------------
@dataclass(frozen=True)
class Text:
    x: int
    y: int
    text: str
    colour: tuple[int, int, int] = BLACK
    large: bool = False


STATIC_TEXTS = [
    Text(9, 15, "F1 Hz", large=True),
    Text(9, 46, "F2 Hz", large=True),
    Text(129, 15, "Filters", large=True),
    Text(129, 44, "C (nF)", large=True),
    Text(47, 82, "F1( ) Hz"),
    Text(118, 82, "R1( ) kOhms"),
    Text(203, 82, "C1( ) nF"),
    Text(287, 82, "F2( ) Hz"),
    Text(358, 82, "R2( ) kOhms"),
    Text(443, 82, "C2( ) nF"),
    Text(79, 202, "Phase Error Degrees", BLUE),
    Text(329, 202, "Suppression dB", RED),
    Text(489, 215, "80", RED),
    Text(489, 263, "60", RED),
    Text(489, 314, "40", RED),
    Text(489, 366, "20", RED),
    Text(493, 414, "0", RED),
    Text(22, 314, "0", BLUE),
    Text(33, 426, "100"),
    Text(129, 426, "Hz"),
    Text(254, 426, "1k"),
    Text(471, 426, "10k"),
    Text(29, 447, "Phase Scale", BLUE, large=True),
]
ROW_LABEL_X, ROW_LABEL_Y = 8, 100  # "(1)".."(n)", one per active row, step TABLE_ROW_STEP

# --- Tooltips (verbatim from the original executable) ----------------------------------------
TIP_F1 = "Change lower frequency of range."
TIP_F2 = "Change upper frequency of range."
TIP_C = "Set default capacitor value in nF."
TIP_N = ["One filter in each path.", "Two filters in each path.",
         "Three filters in each path.", "Four filters in each path.",
         "Five filters in each path.", "Six filters in each path."]  # fmt: skip
TIP_DESIGN = "Calculate values and display graph"
TIP_RESET_C = "Sets all capacitor values to default"
TIP_PHASE = "Recalculates and displays graph after any values have been changed manually."
TIP_CLEAR = "Clears graph and all calculated values."
TIP_EXIT = "Quit the program."
TIP_GRAPH = "Phase Error Relative to 90 Degrees"


def tip_scale(scale: str) -> str:
    unit = "degrees" if scale in ("10", "5", "2") else "degree"
    return f"Set phase graph scale to +/- {scale} {unit}."
