# Extra Sloppy All Pass Filter Designer — Roadmap

A GPL-3.0 clean-room re-implementation of the J-Tek *All Pass Filter Designer* (`Apf.exe`, 2002–2004) by Lawrence Woolf, GJ3RAX.

**Original program page:** <https://www.gj3rax.com/apf.htm>
**Repository:** <https://github.com/arp-Trosh/extra-sloppy-all-pass-filter-designer>
**Licence:** GPL-3.0-only
**Status:** Phases 0–5 complete (2026-10-06). The Windows hardware test is pending, and Phase 6 is to be decided (§7.1). The final summary is in `docs/SUMMARY.md`. The Phase 6 extensions are deferred (§7.1). User feature requests U1–U8 are listed in §0.

---

## 0. User feature requests (received 2026-10-06), in order of ease

These requests come from a user of the program. They are listed **easiest first**. Effort uses the scale from §7.1: XS is under an hour, S is under ½ session, M is about 1 session, L is several sessions. **Nothing is scheduled yet.** The user decides phase by phase.

**Where these features go: "Bill Mode".** Items U1, U2, U3, U5, U6 and U8 change what the main window shows, but the classic window must keep matching the original (CLAUDE.md, decision 6), and `test_vs_original.py`, `test_form_replay.py` and `test_gui.py` enforce this. So all eight features go in a separate top-level window called **Bill Mode**. It reuses `core/`, keeps its button behaviour in a toolkit-free state class like `FormState`, and leaves the classic window and its tests unchanged. ✅ Decided 2026-10-06 (decision 8). **U1–U5 done 2026-10-06** (`bill.py`, `core/eseries.py`, `gui/bill_window.py`, `gui/bill_graph.py`; 21 tests in `tests/test_bill.py`). Switch with Ctrl+B or start with `esapf-gui --bill`. Bill Mode also shows the worst-case error and suppression in the F1–F2 band. U6–U8 are next, awaiting approval.

| # | Request (as received) | What it involves | Effort | Depends on | Backlog overlap |
|---|---|---|---|---|---|
| U1 ✅ | Show the real frequency to 2 decimal places | New formatter, e.g. `f"{f:.2f}"`. The original truncates F to an integer (`legacy.format_f`), so this goes only in the new view. | XS | View decision | — |
| U2 ✅ | Show resistances in ohms, not kilohms, rounded to 0.01 Ω | Formatter and column header (Ω). Input parsing must accept ohms in the new view. Note that 0.01 Ω is coarser than the original's 6 decimals of kΩ (0.001 Ω). | XS | View decision | — |
| U3 ✅ | Settable min/max frequency for the graph's X axis | The pixel↔frequency mapping in `gui/graph.py` is hard-coded to 100 Hz–10 kHz. Make it take `f_min`, `f_max` parameters, with the classic values as defaults, and add two input boxes and validation (min < max, both > 0). Grid lines and labels must follow the chosen decades. | S | View decision | 6.14 (zoom) |
| U4 ✅ | Selector buttons for E6, E12, E24, E48, E96 and E192; show the nearest standard resistor to each calculated value | `core/eseries.py` with the IEC 60063 tables and a nearest-value function (on a log scale, across decades). In the UI: a button group and an extra "R std" column per path. | S | — | Replaces 6.3 |
| U5 ✅ | Choose whether the graph is drawn from the "perfect" R values or the E-series values | A toggle that feeds either the ideal R values or the U4 values into the existing phase/suppression calculation. Showing both curves together would be a cheap extra. | S | U4 | Part of 6.8 |
| U6 | Each capacitor value selectable from a drop-down list of E6 values, 10 pF to 1 µF | 31 values (10, 15, 22, 33, 47, 68 × 10 pF…100 nF, plus 1 µF). Use editable `QComboBox` cells so measured values can still be typed (see 6.6). The resistors are recalculated from each section's own C. | M | View decision, U4 tables | Helps 6.6 |
| U7 | Choose single resistors or 2 resistors; with 2, pick the pair from the selected series whose **sum** is closest to the required R | Series-pair search in `core/eseries.py`. E192 over about 6 decades is around 1 200 values, so a sorted two-pointer search is instant. Show both parts and the error. Optional: parallel pairs as well. | M | U4 | Replaces 6.4 (series only) |
| U8 | Support 3, 5, 7, 9 and 11 sections in total (today only 2–12 in pairs) | Maths: the Darlington solution with N total poles places k_j = (2j+1)/(4N) alternately on the two paths. For even N this is exactly Oppelt's eq. 10. For odd N, one path gets one extra section, and the middle one has τ = 1/√(ω1ω2). This must go in a **new** function (the `oppelt_design()` defaults stay the same), checked against the exact elliptic reference in `test_elliptic.py`. The original can't be used as an oracle here. UI: the two paths have different row counts, and there are new count buttons. | M–L | View decision | Related to 6.1 |

**Suggested grouping:** a first batch of U1–U5 (one or two sessions, all small once Bill Mode exists), then U6 and U7, then U8 on its own because it is the only one that touches the design maths.

---

## 1. Executive summary

| Question | Answer |
|---|---|
| Decompile? | **No, not as the main route.** The design maths can be rebuilt from the article the author cites, and that rebuild has already been checked against real numbers (§3). We'll treat the original program as a **black box** under Wine and compare against it. P-code disassembly is a **fallback**, only for differences we can't explain. |
| If decompiling, which tools (Arch)? | Wine + **VBDec** (free P-code disassembler/debugger), with **P32Dasm** / **Semi VB Decompiler** as backups. `pefile`/`rizin` handle PE structure. Ghidra is **not** useful here because it can't read VB6 P-code. Details in §4.3. |
| Language | **Python 3 + PySide6 (Qt) + pyqtgraph**, with the maths in a pure-Python/NumPy core that has no GUI code. Speed is not a concern (§5). |
| Platforms | Linux, Windows 10, Windows 11 (macOS comes for free). |
| Licence / name | GPL-3.0; **Extra Sloppy All Pass Filter Designer**. The Python package is `esapf`. |

---

## 2. What we know about the original program

### 2.1 Binary facts (checked locally)

- `apf.exe`: PE32 i386 GUI, 66 kB, SHA-256 `b6bb5682…16bb26c`, downloaded by `reference/fetch.sh`.
- It is **Visual Basic 6 compiled to P-code, not native x86**:
  - The VB header (`VB5!` at 0x29DC) → `ProjectInfo.lpNativeCode = 0`.
  - The only runtime imports are `MethCallEngine`, `EVENT_SINK_*` and `__vbaExceptHandler`, which is the classic P-code signature.
  - What this means: x86 decompilers like Ghidra, IDA and rizin would only show the VB interpreter calls, not the program logic. If we ever decompile, we need a tool that understands VB P-code.
- Project path in the binary: `C:\Programming\VB6\All Pass Filter\APF6.vbp`. There is one form, `Form1`, with about 42 TextBoxes, 18 CommandButtons, 1 PictureBox and about 22 Labels.
- Recovered strings (useful for matching behaviour):
  - `All Component Values MUST be Specified and Greater than Zero`
  - `F1 should not be below 10 Hz` / `F2 should not be below 10 Hz`
  - `The Capacitor value C(nF) Must be Specified and Greater than Zero`
  - The number format `####0.000000`
  - The scale labels `±0.5`, `±0.2`, `±0.1`
  - The graph titles `Phase Error Degrees` and `Suppression dB`
- It needs `msvbvm60.dll`. It runs correctly under Wine 11.19 (confirmed in Phase 0), so we can use it as a test oracle.

### 2.2 Functional spec (from the web page and screenshots in `reference/web/`)

- **Inputs:** F1 and F2 (Hz, both ≥ 10), number of sections per path n ∈ {1…6}, default capacitor C (nF).
- **Buttons:**
  - **Design**: computes the 90° frequencies → R = τ / C → table and graph.
  - **Phase**: recomputes from R and C values the user edited.
  - **Reset C**, **Clear**, **Exit**.
  - Phase-scale buttons: 10, 5, 2, 1, 0.5, 0.2, 0.1 degrees.
- **Table:** two paths, n rows each, with columns F( ) Hz, R( ) kΩ and C( ) nF. Only R and C can be edited.
- **Graph:**
  - Log-frequency axis from 100 Hz to 10 kHz.
  - Blue curve: phase error in degrees, with a scale the user can change.
  - Red curve: unwanted-sideband suppression, fixed at 0–80 dB.
- **Fixed 800×600 layout.** It also has tooltips.

---

## 3. Formulas (already recovered and checked)

The author says the maths comes from **R. Oppelt, DB2NP, "The Generation and Demodulation of SSB Signals using the Phasing Method", VHF Communications 2/1987, pp. 66–72.** A scanned copy is saved in `reference/VHF-COMM.1987.2.pdf`. The OCR of that scan is poor, so the equations below were rebuilt by hand and then checked against the article's own worked example.

### 3.1 One first-order all-pass section (inverting op-amp, R1 = R2)

```
H(jω) = (1 − jωτ)/(1 + jωτ),   |H| = 1,   φ(ω) = −2·arctan(ωτ),   τ = R·C
f90 = 1/(2π·R·C)            (frequency where the phase shift is 90°)
```

### 3.2 Phase difference of two chains (A and B, each with n sections)

```
Δφ(ω) = 2·Σ_v [ arctan(ω·τ_v,B) − arctan(ω·τ_v,A) ]        (Oppelt eq. 13)
phase error ε(ω) = |Δφ(ω)| − 90°
```

### 3.3 Sideband suppression from the phase error (with equal amplitudes)

```
S_dB = 10·log10[(1 + cos ε)/(1 − cos ε)] = −20·log10( tan(|ε|/2) )
```

For ε = 1°, S ≈ 41.2 dB. This matches the "about 41 dB" quoted on the web page.

General form, which we can add later, for an amplitude ratio A:
`S = (1 + A² + 2A·cos ε)/(1 + A² − 2A·cos ε)`.

### 3.4 Design: Oppelt's closed form (a Darlington/Jacobi-elliptic equiripple solution, after Wunsch 1958)

```
κ   = ω1/ω2 = F1/F2                                        (7)
ε0  = ½ · (1 − √κ)/(1 + √κ)                                (8)
q   = ε0 + 2ε0⁵ + 15ε0⁹ + 150ε0¹³ + 1707ε0¹⁷               (9)  (Jacobi nome; the original uses exactly these 5 terms)
k_v = (4v + 1)/(8n),   v = 0 … n−1                         (10)

        Σ_{m=0..3} q^(m(m+1)) · cos((2m+1)π k_v)          (the original uses exactly 4 terms)
τ_v,B = ─────────────────────────────────── · 1/√(ω1ω2)    (11)
        Σ_{m=0..3} (−1)^m q^(m(m+1)) · sin((2m+1)π k_v)

τ_v,A = 1/(ω1·ω2·τ_v,B)                                    (12)
R_v   = τ_v / C
```

### 3.5 Verification already done

- **Oppelt's worked example** (270–3600 Hz, n = 4):
  - Our code gives τ_B = 2344.8, 369.52, 123.44 and 36.173 µs. The article gives 2344.6, 369.52, 123.44 and 36.173 µs.
  - Our code gives τ_A = 11.114, 70.524, 211.11 and 720.43 µs, an exact match with the article.
  - Our worst-case error in the band is **0.0111°**. The article states 0.011°.
- **Program's default case** (270–3600 Hz, n = 3):
  - Our f90 values are 91.2, 688.8 and 3078 Hz for one path, and 10654, 1411 and 316 Hz for the other.
  - The KK7B values shown in the program screenshot are 90, 686 and 3043 Hz, and 10610, 1408 and 311 Hz. KK7B's R2/T2 network turns out to be this design with practical component values.
- **Analysis side:** feeding the KK7B R and C values into §3.2–3.3 reproduces the shape of the curves in `kk7b.jpg`:
  - Zero crossing near 800 Hz.
  - Phase-error peak of +0.5° near 3 kHz.
  - Suppression of about 50 dB around 300 Hz.

**Settled in Phase 1** (full details in `docs/ORIGINAL_BEHAVIOUR.md`):
- **Series terms:** exactly 5 q-terms and 4 τ-terms. All 132 R values match the original character for character; any other combination fails.
- **Paths and sign:** path 1 = τ_B (rising f90), path 2 = τ_A. The plotted error is ε = 2Σatan(ωτ1) − 2Σatan(ωτ2) − 90°.
- **Display rounding:** R is shown with 6 decimals. F is truncated to an integer. ("649" and "52.3" in the KK7B screenshot were user-typed values.)
- **Graph:** fixed log axis from 100 Hz to 10 kHz over the full picture width. The pixel mapping is in the doc. Off-range parts are clipped at the edges.

---

## 4. Method: black box plus the literature, with decompilation held in reserve

### 4.1 Why not decompile first

The algorithm comes from published maths that we have already reproduced to 4–5 significant figures. Decompiling VB6 P-code is slow and the tools are Windows-only. The original also had no help file and has a simple UI that is fully documented in the screenshots. Comparing outputs against the original running under Wine is quicker and avoids copying any of the author's code: this is a clean-room re-implementation of public maths. Credit goes to GJ3RAX and DB2NP.

### 4.2 Black-box oracle (Phase 1)

**As implemented:**
- `apf.exe` runs under Wine on a private **Xvfb** display, so the user's desktop is never touched.
- A small Python helper runs *inside* Wine (Windows embeddable Python, ctypes only) and drives the VB6 form purely with Win32 messages: `WM_SETTEXT`, `WM_GETTEXT` and `BM_CLICK`. It also catches and dismisses `MsgBox` dialogs. No mouse, keyboard or OCR is involved.
- The graph PictureBox is cropped from the Xvfb screen with ImageMagick.
- **44 cases**, defined in `tools/oracle/cases.py`:
  - Design for every n from 1 to 6.
  - 13 other bands and C values, including the extremes 10–100000 Hz, swapped limits and equal limits.
  - All 7 scales.
  - 8 validation cases.
  - 9 button-behaviour cases.
  - The KK7B, AN1981 and N4BCU designs.
  - Full-window reference shots.
- Output goes to `tests/fixtures/original/`: JSON plus PNG files, 396 kB in total. Re-capturing produces byte-identical values and graphs.
- `tools/oracle/verify_model.py` re-checks the formulas against the fixtures.

### 4.3 Fallback: P-code decompilation toolchain on Arch Linux

We use this only if a black-box result can't be explained (for example an undocumented tweak or rounding rule).

| Tool | Role | How it runs on Arch |
|---|---|---|
| **VBDec** (sandsprite.com, freeware) | VB6 P-code disassembler with a debugger and form/resource viewer. **Main choice.** | Wine |
| **P32Dasm** (freeware) | P-code → readable opcode listing. Second opinion. | Wine |
| **Semi VB Decompiler** (open source) | P-code decompiler; also extracts forms (`.frm` layout). | Wine |
| VB Decompiler Lite (DotFix, free tier) | Optional cross-check; the full P-code decompiler is in the paid Pro version. | Wine |
| `python-pefile` / `rizin` | PE/VB header structures and string extraction (already used above). | pacman |
| `icoutils` (`wrestool`) | Pull out the icon and version resources. | pacman |
| Ghidra | **Not recommended.** It has no VB6 P-code processor and would only show `MethCallEngine`. | pacman (extra) |

**Checked in Phase 0:** VBDec 8.4.24 installs silently into the project Wine prefix and opens `apf.exe` (`tools/wine.sh setup --vbdec`, then `tools/wine.sh vbdec`). It needs `msvbvm60.dll` installed system-wide in the prefix, which the script does. P32Dasm and Semi VB Decompiler were not tried, because VBDec is enough.

---

## 5. Language choice: Python 3.12+

| Criterion | Python + PySide6 + pyqtgraph | Rust + egui (runner-up) | Single-file HTML/JS |
|---|---|---|---|
| Fast enough | Yes. About 2,000 points × 12 sections is roughly 24k `atan` calls, under 1 ms with NumPy. | Yes | Yes |
| How well LLMs know it | Best | Good | Best |
| Token cost per feature | Lowest (short code) | Higher (types, lifetimes, verbose UI code) | Low |
| Native desktop look on Linux and Windows | Qt, native | Custom immediate-mode UI | Browser |
| Distribution | PyInstaller → `.exe` / AppImage, 40–80 MB | One 5–10 MB binary, can cross-compile from Arch | Just a file |
| Maths ecosystem (`scipy.special.ellipk` for future exact-elliptic checks) | Excellent | Thin | Thin |

**Recommendation:** Python, because it has the lowest token cost and the strongest LLM fluency, which is exactly what the brief asks for.

**Toolkit:**
- PySide6 (official Qt binding, LGPL) for the UI.
- ~~pyqtgraph~~ **Changed in Phase 3:** the graph is a small custom `QPainter` widget. It reproduces the original's PictureBox pixel for pixel (≥ 97.5 % identical in tests), which pyqtgraph could not do, and dropping pyqtgraph keeps the Windows build smaller. pyqtgraph remains a good option for the modernised UI (6.14). Matplotlib stays an option for exporting publication-quality images.

**Tooling:**
- `uv` for environments and lock files.
- `pytest` for tests.
- `ruff` for lint and format.
- Type hints throughout, checked with `mypy` on the core.

**Packaging:** PyInstaller builds run on each target OS in GitHub Actions (Windows and Linux runners) and produce `esapf.exe` and an AppImage. On Arch it can also run straight from `uv run esapf`.

---

## 6. Proposed architecture

```
extra-sloppy-all-pass-filter-designer/
├── pyproject.toml            # name "extra-sloppy-apf", license GPL-3.0-only
├── LICENSE                   # GPL-3.0
├── src/esapf/
│   ├── core/                 # pure maths, no GUI imports (UI-independent, fully unit-tested)
│   │   ├── allpass.py        # section phase, chain phase, phase difference / error
│   │   ├── design.py         # Oppelt design → τ (original's 5/4-term truncation by default)
│   │   ├── metrics.py        # suppression (incl. amplitude imbalance), band statistics
│   │   ├── network.py        # Section / Network: R (kΩ), C (nF) ↔ τ
│   │   └── legacy.py         # original-program behaviour: VB Val(), display formats, validation
│   ├── gui/
│   │   ├── main_window.py    # replica of the original layout/workflow
│   │   ├── table.py          # editable R/C table
│   │   └── plot.py           # phase-error + suppression twin-axis plot
│   └── cli.py                # `esapf design 270 3600 -n 3 -c 10`, `esapf analyse ...` → table / CSV
├── tests/
│   ├── test_core.py             # article example, identities, metrics, legacy, CLI
│   ├── test_vs_original.py      # every captured fixture: tables, validation, graph curves
│   ├── oracle.py                # fixture loader
│   └── fixtures/original/       # 44 cases captured from Apf.exe (Phase 1)
├── tools/                    # wine.sh, oracle/ (capture + verify_model.py)
├── reference/
│   ├── fetch.sh              # downloads the original exe, web pages and article (SHA-256 checked)
│   └── (downloaded files — git-ignored, not redistributed)
└── docs/FORMULAS.md          # §3, expanded, with derivations
```

Keeping `core/` separate from the GUI means that every Phase 6 extension (§7.1) can be added later without touching the maths.

**Third-party material is not committed.** The original `Apf.exe`, the GJ3RAX web pages and the 1987 magazine scan are copyrighted by their authors. `reference/fetch.sh` downloads them from their original sources instead.

---

## 7. Phased plan

| Phase | Work | Deliverable / exit criterion |
|---|---|---|
| **0. Setup** ✅ | Git and GitHub repo (private), GPL-3.0. The original runs under Wine 11.19 (`tools/wine.sh original`). VBDec 8.4.24 runs under Wine and parses `apf.exe` (`tools/wine.sh vbdec`). Python skeleton: `uv`, `ruff`, `mypy --strict`, `pytest`, PySide6 6.11 (and pyqtgraph, later dropped in Phase 3). | ✅ Done 2026-10-06; see §7.2. |
| **1. Oracle capture** ✅ | 44 reference cases captured automatically on Xvfb (§4.2). The open points in §3.5 are settled. | ✅ Done 2026-10-06: `tests/fixtures/original/`, `docs/ORIGINAL_BEHAVIOUR.md`. Decompilation was **not needed**, so Phase 2b is expected to be skipped. |
| **2. Core maths** ✅ | `core/` modules and CLI. | ✅ Done 2026-10-06. All fixtures match the original to the displayed precision, and the article example matches (§7.4). |
| **2b. (only if needed)** ⏭ | P-code disassembly of the functions that don't match. | **Skipped**: there were no unexplained differences. |
| **3. GUI parity** ✅ | Qt window that replicates the original layout and workflow: Design, Phase, Reset C, Clear, n = 1–6, scale buttons, tooltips, validation messages. | ✅ Done 2026-10-06 (§7.5). Side-by-side screenshots are equivalent, and all 44 captured cases, including the three web examples, replay through the real widgets. |
| **4. Packaging & CI** ✅ | GitHub Actions: tests, then PyInstaller on Windows and Linux. Release artefacts are attached to GitHub Releases. | ✅ Done 2026-10-06 (§7.6). CI is green, and both executables pass their self-test on CI and on Arch (Linux natively, Windows under Wine). ☐ **Real Win10/11 test pending** (a friend will use `docs/WINDOWS_TEST.md`). |
| **5. Docs** ✅ | README, `FORMULAS.md` and a final work summary with the formulas. | ✅ Done 2026-10-06: `docs/SUMMARY.md`, `docs/FORMULAS.md`, `docs/DEVELOPING.md` and `CLAUDE.md`. New findings: the Jacobi closed form, the ripple formula ε ≈ 4q^(2n), and the original's suboptimal design for very wide bands. All are locked in by `tests/test_elliptic.py`. |
| **6. Extensions** | **Deferred.** Chosen from the backlog in §7.1 after Phases 1–5 are complete. | — |

Rough effort: Phases 0–5 take a few working sessions. Phase 1 needs the most hands-on time, because it means driving the GUI.

### 7.2 Phase 0 results (2026-10-06)

**Original program under Wine**
- `tools/wine.sh setup` creates the project-local prefix `.wine/` and installs the VB6 runtime with a native DLL override.
- `tools/wine.sh original` starts the program. The 520×474 form renders correctly with the defaults (F1 270 Hz, F2 3600 Hz, 3 filters, C = 10 nF, phase scale 1).
- The program window runs under XWayland. Note that Wine also creates a hidden 800×800 "APF6" owner window.

**What VBDec found in `apf.exe`**
- P-code, VB6, project `APF6`.
- One form (`Form1`) with 30 procedures and 90 embedded controls.
- Public subs include `calcdb`, `gcalc` and `gvalues`. These are the procedures to read if Phase 2b ever becomes necessary.

**Python environment**
- Python 3.14 managed by `uv`, with a committed `uv.lock`.
- `uv run pytest` runs 4 smoke tests, including a check that `esapf.core` never imports Qt, and an offscreen Qt/pyqtgraph log-axis plot.

**Automation for Phase 1**
- Xvfb was installed and used; see §4.2.

### 7.3 Phase 1 results (2026-10-06)

- **The maths is fully confirmed without decompiling.** Oppelt's equations with exactly 5 q-terms and 4 τ-terms reproduce every R value of the original. The phase and suppression formulas reproduce its graph to about 1 px.
- **Behaviour spec:** `docs/ORIGINAL_BEHAVIOUR.md` covers display formats, button semantics, validation order and messages, and the graph geometry and colours.
- **Quirks to reproduce faithfully** (Phase 3):
  - F columns are truncated, not rounded.
  - Reset C does no validation.
  - Changing n clears the table and the graph.
  - There is no F1 < F2 check (none is needed; the design is symmetric).
  - There is no upper frequency limit.
- **Fixtures** for the Phase 2 tests: `tests/fixtures/original/*.json` (44 cases) plus graph PNGs.
- **Phase 2b (decompilation):** not needed.

### 7.4 Phase 2 results (2026-10-06)

**Modules in `src/esapf/core/`** (NumPy only, `mypy --strict` clean, no Qt imports, enforced by a test):
- `design.py`: `oppelt_design(f1, f2, n, nome_terms=5, tau_terms=4)`. The defaults reproduce the original; more terms give the exact elliptic solution.
- `allpass.py`: chain phase, phase difference and phase error, vectorised over frequency.
- `metrics.py`: `suppression_db` (with an optional amplitude ratio, ready for 6.7), `band_stats` and `log_grid`.
- `network.py`: `Section` / `Network` in UI units (kΩ, nF), plus `Network.from_design`.
- `legacy.py`: the original's input parsing (VB `Val`), display formats (`%.6f` R, truncated F) and its four validation messages, checked in the original order.

**CLI:**
- `esapf design F1 F2 -n N -c C` prints the original's table and the in-band worst case.
- `esapf analyse --path1 R:C,... --path2 R:C,... [--band F1 F2]` analyses a given set of components.
- Both take `--csv FILE` to write the 100 Hz–10 kHz sweep.

**Tests: 179 passing in under 1 s.**
- All 42 captured Design tables: R to 6 decimals and F, character for character.
- All 7 Phase recalculations.
- All 53 validation outcomes and messages.
- The phase and suppression curves of 35 captured graphs, within 1.0 / 1.5 px RMS.
- Oppelt's worked example (τ values and the 0.011° error).
- Design identities: reciprocal pairs, symmetry, equiripple error, and error decreasing as n grows.
- The CLI.

### 7.5 Phase 3 results (2026-10-06)

**Run it:** `uv run esapf-gui` or `python -m esapf.gui`.

**Architecture:**
- `esapf/form.py` (`FormState`, no Qt) holds every field as displayed text and implements the button semantics from `docs/ORIGINAL_BEHAVIOUR.md` §5–6.
- `gui/main_window.py` only renders that state and forwards events.
- `gui/layout.py` holds the original geometry, colours, fonts and the **verbatim tooltips**, which were recovered from the exe's strings.
- `gui/graph.py` is the PictureBox replica.

**Fidelity:**
- **Layout:** the 520 × 474 window uses the original control rectangles taken from the Win32 dump. Static texts sit at their measured positions, using a bold sans font matched to the original's text widths (MS Sans Serif on Windows, Liberation Sans/Arial elsewhere).
- **Rows:** inactive rows are pale yellow and read-only, the F columns are read-only, and the row labels "(1)…(n)" follow n.
- **Graph:** 98–99 % of pixels are identical to the original's screenshots (the test threshold is 97.5 %). The remaining difference is how the 2-px curves are rasterised (Qt vs Windows GDI), plus the height of infinitely sharp suppression spikes, which depends on the sampling grid.

**Deliberate deviations:**
- **Window title:** "Extra Sloppy All Pass Filter Designer".
- **Exit:** shows an About box before quitting, as the original did. It credits GJ3RAX and DB2NP and carries the GPL-3.0 notice, instead of the author's dead e-mail address.

**Tests: 305 passing in about 1.6 s.**
- `test_form_replay.py`: all 44 cases through `FormState`.
- `test_gui.py`:
  - All 44 cases through the **real widgets**, with key presses into the fields and button clicks, comparing every displayed field and every error dialog.
  - Graph pixel comparison for 35 captured graphs.
  - Read-only rules and tooltips.
- `mypy --strict` now covers all of `src/`.

**Manual check:**
- The real X11 (xcb) build ran on a private Xvfb display. xdotool mouse clicks covered n = 5, Design, scale 0.2, an invalid-F1 error dialog, and Exit → About → quit.
- **A bug was caught and fixed:** `clicked(bool)` was overriding the lambda defaults of the n and scale buttons.

**Tool:** `uv run tools/render_gui.py <case> out.png --diff <original_form.png> diff.png` renders the window after replaying a case and diffs it against the original's screenshot.

### 7.6 Phase 4 results (2026-10-06)

**Build:**
- `uv run --group build packaging/build.py` runs PyInstaller and produces a single-file, windowed GUI executable with an icon.
- `packaging/esapf-gui.spec` filters out unused Qt plugins and libraries: the virtual keyboard (which drags in Qt Quick/Qml), QtPdf, the GTK theme (GTK plus a second ICU), and the embedded/VNC platforms. It also leaves out the bundled fontconfig, so the host's is used.

| Artefact | Size | Notes |
|---|---|---|
| `esapf-gui-<ver>-windows-x64.exe` | 49 MB | Not code-signed, so SmartScreen will show "More info → Run anyway". |
| `esapf-gui-<ver>-linux-x86_64` | 71 MB | Built on Ubuntu 22.04, so it needs glibc ≥ 2.35. Runs on X11 and Wayland. |

The roadmap originally planned an AppImage for Linux. A single-file PyInstaller binary does the same job (one file, no install) with no extra tooling.

**Self-test:** `esapf-gui --self-test` runs offscreen, presses Design, checks the displayed R values and exits with code 0. CI runs it on each built executable, on its own OS.

**CI** (`.github/workflows/ci.yml`, about 4 minutes per run):
1. Lint, format, mypy and all 306 tests on `ubuntu-latest` and `windows-latest`. The GUI and graph-pixel tests also pass on Windows.
2. Build and self-test on `windows-latest` and `ubuntu-22.04`, then upload the artefacts.
3. On a `v*` tag, publish a GitHub Release with both files.

Jobs and the self-test step have timeouts.

**Bugs found and fixed while doing this:**
1. The plugin filter had removed Qt's `offscreen` plugin. On Windows that made the windowed `.exe` hang behind Qt's modal "platform plugin not found" dialog.
2. The Windows build picked the bitmap font "MS Sans Serif". It showed up as unbolded, misplaced text when the CI `.exe` was run under Wine. The font list is now TrueType only, led by Microsoft Sans Serif.
3. The bundled fontconfig from Ubuntu 22.04 produced warnings on newer distributions.

**Pending:** a test on real Windows 10/11 hardware, using `docs/WINDOWS_TEST.md` (12 checks).

### 7.7 Phase 5 results (2026-10-06)

**Documents:**
- `docs/FORMULAS.md`: every formula, each marked by how it was verified: [oracle] matches the original, [article] matches Oppelt's example, [proven] matches exact elliptic functions.
- `docs/SUMMARY.md`: the final summary.
- `docs/DEVELOPING.md`: layering rules, test map, recipes for extensions, and the release procedure.
- `CLAUDE.md`: a short guide for AI assistants.

**New findings, all tested:**
- Oppelt's eq. 11 is τ1_v = cs(2K·k_v, k)/ω1, with q the Jacobi nome for k = √(1−κ²).
- The ripple is ε_max ≈ 4q^(2n).
- The original's 5/4-term truncation is within 0.04 % of optimal for F2/F1 ≤ 20, but up to 5–12× worse for 10 Hz–20/100 kHz. This is the motivation for item 6.2.

**Housekeeping:**
- The version now lives only in `src/esapf/__init__.py`.
- mpmath was added as a dev-only dependency for the elliptic reference tests.

### 7.1 Phase 6 backlog (to be decided after Phases 1–5)

Nothing here is scheduled. Once Phase 5 is done, each item will be marked **Accept**, **Reject** or **Later** and given a priority. Effort: S is under ½ session, M is about 1 session, L is several sessions.

| # | Extension | What it gives the user | Effort | Depends on | Decision |
|---|---|---|---|---|---|
| 6.1 | **Any number of sections** (n > 6) | Wider bandwidth or a smaller phase error than the original allows | S | 2 | Undecided |
| 6.2 | **Exact elliptic design** (`scipy.special.ellipk/ellipj`) | Independent check of Oppelt's series; the design stays accurate for extreme F2/F1 ratios | S | 2 | Undecided |
| 6.3 | **E-series snapping** (E12/E24/E48/E96/E192) | Rounds the ideal R values to parts you can buy and shows the resulting performance | S | 2, 3 | Superseded by U4/U5 (§0) |
| 6.4 | **Series/parallel resistor-pair search** | Finds the 2-resistor combination closest to each ideal R (the web page suggests this) | M | 6.3 | Series part superseded by U7 (§0) |
| 6.5 | **Monte-Carlo tolerance analysis** | Randomises R and C within their tolerances; plots the error envelope and a suppression yield histogram | M | 2, 3 | Undecided |
| 6.6 | **Matched-capacitor workflow** | Enter the measured C values, then the program recalculates the R values to compensate | S | 3 | Undecided |
| 6.7 | **Amplitude imbalance (R1 ≠ R2, gain mismatch)** | Suppression using the general formula with amplitude ratio A (§3.3) | S | 2 | Undecided |
| 6.8 | **Overlay / compare designs** | Several designs on one graph (e.g. KK7B vs ideal vs E96-snapped) | M | 3 | Undecided |
| 6.9 | **Save / load designs (JSON)** and a built-in library of the KK7B, AN1981 and N4BCU designs | Reproducible designs you can share | S | 2 | Undecided |
| 6.10 | **Export**: CSV data, PNG/SVG graphs, BOM | Documentation and use in other tools | S | 3 | Undecided |
| 6.11 | **SPICE netlist export** (op-amp all-pass chains) | Verification in LTspice or ngspice with real op-amp models | M | 2 | Undecided |
| 6.12 | **RC-position variant** (C and R swapped, phase 180° → 0°) | Covers both circuit forms that the original page mentions | S | 2 | Undecided |
| 6.13 | **Digital IIR Hilbert pair** (bilinear transform of the analogue design, or a direct digital design) | Coefficients for DSP/SDR use at a chosen sample rate | M | 2 | Undecided |
| 6.14 | **Modernised UI** (resizable window, dark mode, high-DPI, cursor read-out, zoom/pan) | Better usability on modern screens; the classic layout stays available | M | 3 | Undecided |
| 6.15 | **Web front end** (e.g. Pyodide, or a JS port of `core/`) | Runs in a browser with no install | L | 2 | Undecided |
| 6.16 | **macOS build** in CI | Third platform at almost no cost | S | 4 | Undecided |

---

## 8. Risks

| Risk | Mitigation |
|---|---|
| The original won't run under Wine | Its dependencies are minimal (one VB6 runtime). Backup: `winetricks vb6run`, or a Windows VM. |
| The original contains a hidden heuristic that differs from Oppelt | Phase 2b P-code disassembly with VBDec. |
| A GUI-automation oracle under Wine is flaky | The case count is small, so capture by hand plus screenshots is acceptable. |
| PyInstaller binary is large or flagged by antivirus | Acceptable for a hobby tool. Nuitka is the alternative if it becomes a problem. |
| Licence or attribution (the original was freeware with no licence stated) | Clean-room GPL-3.0 re-implementation of published maths, with no code copied. Third-party files are not redistributed (§6). Credit GJ3RAX and DB2NP in the About box and README. |
| GPL compatibility of dependencies | PySide6 (LGPL-3), NumPy (BSD) and Pillow (dev only, HPND) are all GPL-3.0 compatible. |

---

## 9. Decisions

| # | Decision | Status |
|---|---|---|
| 1 | Method: black box plus the literature; P-code decompilation only as a fallback | ✅ Approved 2026-10-06 |
| 2 | Stack: Python + PySide6 (pyqtgraph replaced by a custom QPainter graph in Phase 3, see §5) | ✅ Approved 2026-10-06 |
| 3 | Licence: GPL-3.0 | ✅ 2026-10-06 |
| 4 | Name: *Extra Sloppy All Pass Filter Designer* (repo `extra-sloppy-all-pass-filter-designer`, package `esapf`) | ✅ 2026-10-06 |
| 5 | Hosting: GitHub repository. **Public since 2026-10-06** (free CI minutes), with commit history rewritten to the GitHub noreply e-mail. The old private repo was renamed `…-old-private`. | ✅ 2026-10-06 |
| 6 | UI: Phase 3 replicates the original 2002 layout. A modernised UI is optional backlog item 6.14. | ✅ Confirmed 2026-10-06 |
| 7 | Phase 6 extensions | ⏸ Deferred until Phases 1–5 are complete (§7.1) |
| 8 | User requests U1–U8 (§0) go in a separate **Bill Mode** window; the classic window stays a replica. U1–U5 are the first batch. | ✅ 2026-10-06 |

---

### Sources

- GJ3RAX program page and examples: <https://www.gj3rax.com/apf.htm>, `kk7b.htm`, `an1981.htm`, `n4bcu.htm` (downloaded by `reference/fetch.sh`)
- R. Oppelt, DB2NP, *VHF Communications* 2/1987, pp. 66–72: <https://www.worldradiohistory.com/Archive-DX/VHF-Communications/VHF-COMM.1987.2.pdf> (downloaded by `reference/fetch.sh`)
- G. Wunsch, "Zur praktischen Berechnung von Zwei-Phasen-Netzwerken", *Nachrichtentechnik* 4/1958 (cited by Oppelt; not retrieved)
