# Extra Sloppy All Pass Filter Designer — Roadmap

A GPL-3.0 clean-room re-implementation of the J-Tek *All Pass Filter Designer* (`Apf.exe`, 2002–2004) by Lawrence Woolf, GJ3RAX.

**Original program page:** <https://www.gj3rax.com/apf.htm>
**Repository:** <https://github.com/arp-Trosh/extra-sloppy-all-pass-filter-designer>
**Licence:** GPL-3.0-only
**Status:** Phases 0–1 complete (2026-10-06). Phases 2–5 are next. The Phase 6 extensions are deferred (§7.1).

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
- pyqtgraph for fast interactive log-axis plots. Matplotlib stays an option for exporting publication-quality images.

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
│   │   ├── allpass.py        # section phase, chain phase, phase difference
│   │   ├── design.py         # Oppelt/elliptic design → τ, f90, R, C
│   │   └── metrics.py        # phase error, suppression, band statistics
│   ├── model.py              # Design dataclass
│   ├── gui/
│   │   ├── main_window.py    # replica of the original layout/workflow
│   │   ├── table.py          # editable R/C table
│   │   └── plot.py           # phase-error + suppression twin-axis plot
│   └── cli.py                # `esapf design 270 3600 -n 3 -c 10n` → table / CSV
├── tests/
│   ├── test_oppelt_example.py   # article example, numbers in §3.5
│   ├── test_vs_original.py      # JSON fixtures from the Wine oracle
│   └── fixtures/
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
| **0. Setup** ✅ | Git and GitHub repo (private), GPL-3.0. The original runs under Wine 11.19 (`tools/wine.sh original`). VBDec 8.4.24 runs under Wine and parses `apf.exe` (`tools/wine.sh vbdec`). Python skeleton: `uv`, `ruff`, `mypy --strict`, `pytest`, PySide6 6.11 and pyqtgraph. | ✅ Done 2026-10-06; see §7.2. |
| **1. Oracle capture** ✅ | 44 reference cases captured automatically on Xvfb (§4.2). The open points in §3.5 are settled. | ✅ Done 2026-10-06: `tests/fixtures/original/`, `docs/ORIGINAL_BEHAVIOUR.md`. Decompilation was **not needed**, so Phase 2b is expected to be skipped. |
| **2. Core maths** | `core/` modules and CLI. | All fixtures match the original to the displayed precision, and the article example matches. |
| **2b. (only if needed)** | P-code disassembly of the functions that don't match. | Every difference explained. |
| **3. GUI parity** | Qt window that replicates the original layout and workflow: Design, Phase, Reset C, Clear, n = 1–6, scale buttons, tooltips, validation messages. | Side-by-side screenshots look equivalent, and a user can repeat the three web examples. |
| **4. Packaging & CI** | GitHub Actions: tests, then PyInstaller on Windows and Linux. Release artefacts are attached to GitHub Releases. | Working `.exe` checked on Win10/11 (by you or a VM) plus an AppImage or Arch run. |
| **5. Docs** | README, `FORMULAS.md` and a final work summary with the formulas. | The deliverable for goal #2. |
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

### 7.1 Phase 6 backlog (to be decided after Phases 1–5)

Nothing here is scheduled. Once Phase 5 is done, each item will be marked **Accept**, **Reject** or **Later** and given a priority. Effort: S is under ½ session, M is about 1 session, L is several sessions.

| # | Extension | What it gives the user | Effort | Depends on | Decision |
|---|---|---|---|---|---|
| 6.1 | **Any number of sections** (n > 6) | Wider bandwidth or a smaller phase error than the original allows | S | 2 | Undecided |
| 6.2 | **Exact elliptic design** (`scipy.special.ellipk/ellipj`) | Independent check of Oppelt's series; the design stays accurate for extreme F2/F1 ratios | S | 2 | Undecided |
| 6.3 | **E-series snapping** (E12/E24/E48/E96/E192) | Rounds the ideal R values to parts you can buy and shows the resulting performance | S | 2, 3 | Undecided |
| 6.4 | **Series/parallel resistor-pair search** | Finds the 2-resistor combination closest to each ideal R (the web page suggests this) | M | 6.3 | Undecided |
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
| GPL compatibility of dependencies | PySide6 (LGPL-3), pyqtgraph (MIT), NumPy and SciPy (BSD) are all GPL-3.0 compatible. |

---

## 9. Decisions

| # | Decision | Status |
|---|---|---|
| 1 | Method: black box plus the literature; P-code decompilation only as a fallback | ✅ Approved 2026-10-06 |
| 2 | Stack: Python + PySide6 + pyqtgraph | ✅ Approved 2026-10-06 |
| 3 | Licence: GPL-3.0 | ✅ 2026-10-06 |
| 4 | Name: *Extra Sloppy All Pass Filter Designer* (repo `extra-sloppy-all-pass-filter-designer`, package `esapf`) | ✅ 2026-10-06 |
| 5 | Hosting: GitHub repository, **kept private until the software is finished** | ✅ Created 2026-10-06 |
| 6 | UI: Phase 3 replicates the original 2002 layout. A modernised UI is optional backlog item 6.14. | ✅ Confirmed 2026-10-06 |
| 7 | Phase 6 extensions | ⏸ Deferred until Phases 1–5 are complete (§7.1) |

---

### Sources

- GJ3RAX program page and examples: <https://www.gj3rax.com/apf.htm>, `kk7b.htm`, `an1981.htm`, `n4bcu.htm` (downloaded by `reference/fetch.sh`)
- R. Oppelt, DB2NP, *VHF Communications* 2/1987, pp. 66–72: <https://www.worldradiohistory.com/Archive-DX/VHF-Communications/VHF-COMM.1987.2.pdf> (downloaded by `reference/fetch.sh`)
- G. Wunsch, "Zur praktischen Berechnung von Zwei-Phasen-Netzwerken", *Nachrichtentechnik* 4/1958 (cited by Oppelt; not retrieved)
