# SPDX-License-Identifier: GPL-3.0-only
"""Reference cases captured from the original Apf.exe (Phase 1 oracle).

Each case is a list of steps; each step is a list of ops (see job_runner.py) and is
followed by a screenshot of the graph when "shot" is true. The app is restarted
before every case so cases are independent.
"""

SCALES = ["10", "5", "2", "1", "0.5", "0.2", "0.1"]


def design(f1, f2, n, c="10", scale=None):
    ops = [
        ["set", "F1", f1],
        ["set", "F2", f2],
        ["set", "C", c],
        ["click", "ResetC"],
        ["click", f"N{n}"],
        ["click", "Design"],
    ]
    if scale:
        ops.append(["click", f"S{scale}"])
    return ops + [["read", "after_design"]]


def components(r1, c1, r2, c2):
    ops = []
    for i, (a, b, c, d) in enumerate(zip(r1, c1, r2, c2, strict=True), start=1):
        ops += [
            ["set", f"R1_{i}", a],
            ["set", f"C1_{i}", b],
            ["set", f"R2_{i}", c],
            ["set", f"C2_{i}", d],
        ]
    return ops


def published(f1, f2, n, c, r1, c1, r2, c2, scale):
    return [
        {"ops": design(f1, f2, n, c), "shot": False},
        {
            "ops": [
                *components(r1, c1, r2, c2),
                ["click", "Phase"],
                ["click", f"S{scale}"],
                ["read", "after_phase"],
            ],
            "shot": True,
        },
    ]


CASES: dict[str, dict] = {}


def case(cid, desc, steps):
    CASES[cid] = {"description": desc, "steps": steps}


# --- Startup state -----------------------------------------------------------------------
case("startup", "Initial state, no button pressed", [{"ops": [["read", "startup"]], "shot": True}])

# --- Design: default band, every n, every scale -------------------------------------------
for n in range(1, 7):
    case(
        f"design_270_3600_n{n}",
        f"Design 270-3600 Hz, n={n}, C=10 nF",
        [{"ops": design("270", "3600", n), "shot": True}],
    )
case(
    "scales_default",
    "Default design (n=3), graph at every phase scale",
    [{"ops": design("270", "3600", 3), "shot": False}]
    + [{"ops": [["click", f"S{s}"], ["read", f"scale_{s}"]], "shot": True} for s in SCALES],
)

# --- Design: other bands / C values / edge cases ------------------------------------------
for f1, f2, n, c in [
    ("300", "3000", 3, "10"),
    ("50", "5000", 5, "10"),
    ("100", "10000", 6, "10"),
    ("10", "20000", 6, "10"),  # widest ratio: discriminates series term counts
    ("10", "100000", 6, "10"),
    ("1000", "2000", 1, "10"),
    ("200", "4000", 4, "4.7"),
    ("270", "3600", 3, "0.1"),
    ("270", "3600", 3, "1000"),
    ("270.5", "3599.5", 2, "10"),
    ("3600", "270", 3, "10"),  # swapped limits
    ("1000", "1000", 2, "10"),  # equal limits
    ("10", "10", 1, "10"),
]:
    cid = f"design_{f1}_{f2}_n{n}_c{c}".replace(".", "p")
    desc = f"Design {f1}-{f2} Hz, n={n}, C={c} nF"
    case(cid, desc, [{"ops": design(f1, f2, n, c), "shot": True}])

# --- Input validation ----------------------------------------------------------------------
for cid, f1, f2, c in [
    ("valid_f1_below_10", "9.9", "3600", "10"),
    ("valid_f2_below_10", "270", "5", "10"),
    ("valid_c_zero", "270", "3600", "0"),
    ("valid_c_empty", "270", "3600", ""),
    ("valid_c_negative", "270", "3600", "-10"),
    ("valid_f1_text", "abc", "3600", "10"),
    ("valid_f1_empty", "", "3600", "10"),
]:
    desc = f"Validation: F1={f1!r} F2={f2!r} C={c!r}"
    case(cid, desc, [{"ops": design(f1, f2, 3, c), "shot": True}])

# --- Button behaviour ----------------------------------------------------------------------
case(
    "reset_c",
    "Design, change default C to 22, Reset C, then Design again",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {"ops": [["set", "C", "22"], ["click", "ResetC"], ["read", "after_resetc"]], "shot": True},
        {"ops": [["click", "Design"], ["read", "after_redesign"]], "shot": True},
    ],
)
case(
    "clear",
    "Design then Clear",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {"ops": [["click", "Clear"], ["read", "after_clear"]], "shot": True},
    ],
)
case(
    "change_n_after_design",
    "Design n=3, then press n=4 without Design",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {"ops": [["click", "N4"], ["read", "after_n4"]], "shot": True},
    ],
)
case(
    "phase_without_design",
    "Press Phase on an empty table",
    [
        {"ops": [["click", "Phase"], ["read", "after_phase"]], "shot": True},
    ],
)
case(
    "edit_c_then_phase",
    "Default design, C1(1)=10.1 nF, Phase",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {
            "ops": [["set", "C1_1", "10.1"], ["click", "Phase"], ["read", "after_phase"]],
            "shot": True,
        },
    ],
)
case(
    "edit_r_then_phase",
    "Default design, R2(3)=50 kOhm, Phase",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {"ops": [["set", "R2_3", "50"], ["click", "Phase"], ["read", "after_phase"]], "shot": True},
    ],
)
case(
    "edit_r_zero_then_phase",
    "Default design, R1(2)=0, Phase",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {"ops": [["set", "R1_2", "0"], ["click", "Phase"], ["read", "after_phase"]], "shot": True},
    ],
)
case(
    "edit_r_empty_then_phase",
    "Default design, R1(2) empty, Phase",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {"ops": [["set", "R1_2", ""], ["click", "Phase"], ["read", "after_phase"]], "shot": True},
    ],
)
case(
    "change_f_then_phase",
    "Default design, change F1/F2 to 500/2000, Phase (no Design)",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {
            "ops": [
                ["set", "F1", "500"],
                ["set", "F2", "2000"],
                ["click", "Phase"],
                ["read", "after_phase"],
            ],
            "shot": True,
        },
    ],
)

# --- Published designs (from the GJ3RAX example pages) -------------------------------------
case(
    "kk7b",
    "KK7B R2/T2 network",
    published(
        "270",
        "3600",
        3,
        "1",
        ["649", "232", "52.3"],
        ["2.7", "1", "1"],
        ["15", "113", "511"],
        ["1", "1", "1"],
        "1",
    ),
)
case(
    "an1981",
    "Philips AN1981 network (118 kOhm correction)",
    published(
        "280",
        "3200",
        3,
        "1",
        ["1740", "237", "54.9"],
        ["1", "1", "1"],
        ["16.2", "118", "511"],
        ["1", "1", "1"],
        "1",
    ),
)
case(
    "n4bcu",
    "N4BCU 5-section network",
    published(
        "50",
        "5000",
        5,
        "10",
        ["104.7", "149.8", "43.09", "12.77", "3.261"],
        ["100", "10", "10", "10", "10"],
        ["0.968", "6.761", "23.52", "79.36", "31.07"],
        ["10", "10", "10", "10", "100"],
        "0.2",
    ),
)

# --- Misc behaviour (added after first analysis pass) -------------------------------------
case(
    "scale_persists_across_design",
    "Design, scale 0.5, Design again: is the scale kept?",
    [
        {"ops": design("270", "3600", 3), "shot": False},
        {"ops": [["click", "S0.5"], ["click", "Design"], ["read", "after_redesign"]], "shot": True},
    ],
)
case(
    "valid_all_bad",
    "Validation order: F1, F2 and C all invalid",
    [
        {"ops": design("5", "5", 3, "0"), "shot": False},
    ],
)
case(
    "form_kk7b",
    "Full-window reference screenshot with the KK7B design",
    [
        {"ops": design("270", "3600", 3, "1"), "shot": False},
        {
            "ops": [
                *components(
                    ["649", "232", "52.3"], ["2.7", "1", "1"], ["15", "113", "511"], ["1", "1", "1"]
                ),
                ["click", "Phase"],
                ["read", "after_phase"],
            ],
            "shot": True,
            "form_shot": True,
        },
    ],
)
case(
    "form_startup",
    "Full-window reference screenshot at startup",
    [{"ops": [["read", "startup"]], "shot": False, "form_shot": True}],
)
