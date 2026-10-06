# Summary of the work

**Project:** Extra Sloppy All Pass Filter Designer. This is a GPL-3.0 clean-room
re-implementation of the J-Tek *All Pass Filter Designer* by Lawrence Woolf, GJ3RAX (VB6,
2002–2004, source code lost). Phases 0–5 were completed on 2026-10-06.

## The three goals

| Goal | Result |
|---|---|
| **1. Run on modern systems** (Linux, Windows 10, Windows 11) | Python/Qt application, built by CI as single-file executables: `esapf-gui-…-windows-x64.exe` (49 MB) and `…-linux-x86_64` (71 MB, glibc ≥ 2.35, X11 and Wayland). Both pass an automatic self-test on their own OS in CI. The Linux build also runs on Arch, and the Windows build under Wine. **Still pending:** a test on real Windows hardware (`docs/WINDOWS_TEST.md`). |
| **2. Know the formulas** | Fully recovered and verified; see below and `docs/FORMULAS.md`. |
| **3. Easy to maintain and extend** | Layered code (maths core / behaviour / GUI), `mypy --strict`, 313 tests that run in about 2 s on Linux and Windows CI, a developer guide (`docs/DEVELOPING.md`), an AI-assistant guide (`CLAUDE.md`), and a Phase 6 backlog of 16 costed extensions. |

## How the original was reverse-engineered

No decompilation was needed.

1. **Literature.** The author credits R. Oppelt, DB2NP (*VHF Communications* 2/1987). I found
   a scan of that issue, rebuilt the equations from its poor OCR, and reproduced the article's
   own worked example (time constants and the 0.011° error).
2. **Binary triage.** `Apf.exe` is VB6 **P-code**, so x86 decompilers would only have shown
   the VB interpreter's calls. Its readable strings gave the error messages, number formats and
   tooltips.
3. **Black-box oracle.** I ran the original under Wine on a private virtual display. A Python
   helper inside Wine drove it purely with Win32 messages (set text, click, read text, catch
   message boxes), with no mouse, keyboard or OCR. It captured 44 cases: every n, wide and
   narrow bands, edge cases, validation, button behaviour, all scales and the three published
   designs. Each case recorded the displayed values and graph screenshots.
4. **Fitting.** Comparing the oracle with the maths settled the details: exactly **5 nome
   terms and 4 time-constant terms** (all 132 R values match to every displayed digit), F
   **truncated**, R shown to 6 decimals, and the graph geometry and suppression formula
   (curves match to under 1 px RMS).
5. **Fallback not needed.** The P-code disassembler VBDec runs under Wine and was kept ready,
   but no difference was ever left unexplained.

## The formulas

**One section:** an op-amp all-pass with R1 = R2, and a series R with C to ground:

```
H(jω) = (1 − jωτ)/(1 + jωτ),   |H| = 1,   φ = −2·arctan(ωτ),   τ = R·C,   F90 = 1/(2πRC)
```

**Network of two chains with n sections each:**

```
Δφ(ω) = 2·Σ arctan(ωτ1_v) − 2·Σ arctan(ωτ2_v)          phase error  ε = Δφ − 90°
```

**Unwanted-sideband suppression** (amplitude ratio A; the original assumes A = 1):

```
S = 10·log10[(1 + A² + 2A·cos ε)/(1 + A² − 2A·cos ε)]   →   S = −20·log10|tan(ε/2)|   (A = 1)
1° of phase error → 41.2 dB
```

**Design** (Oppelt eqs. 7–12, equiripple / Darlington, with the original's exact truncation):

```
κ = F1/F2,   ε0 = ½(1 − √κ)/(1 + √κ),   q = ε0 + 2ε0⁵ + 15ε0⁹ + 150ε0¹³ + 1707ε0¹⁷
k_v = (4v+1)/(8n),  v = 0…n−1
τ1_v = [Σ_{m=0..3} q^{m(m+1)} cos((2m+1)πk_v)] / [Σ_{m=0..3} (−1)^m q^{m(m+1)} sin((2m+1)πk_v)] / √(ω1ω2)
τ2_v = 1/(ω1ω2·τ1_v),     R = τ/C
```

**Closed form**, new in this work and verified against exact elliptic functions. q is the
Jacobi nome for the modulus k = √(1 − κ²), and:

```
τ1_v = cs(2K·k_v, k)/ω1          maximum phase error  ε_max ≈ 4·q^{2n} rad
```

For example, 270–3600 Hz gives 0.133° with n = 3 and 0.011° with n = 4.

## Findings about the original

- It is accurate for speech bands. Up to F2/F1 = 20 it is within 0.04 % of the optimal design.
- Its truncated series is **suboptimal for very wide bands**. For 10 Hz–20 kHz with n = 6 it
  gives 1.57° where 0.315° is achievable, and for 10–100 kHz it gives 9.97° vs 0.86°. Backlog
  item 6.2 would fix this.
- It has some quirks, which the replica reproduces faithfully:
  - F values are truncated.
  - *Reset C* does not validate its input.
  - Changing n clears everything.
  - There is no F1 < F2 check (none is needed, since the maths is symmetric).
  - There is no upper frequency limit.

## What was built

| Part | Contents |
|---|---|
| `esapf.core` | Design, analysis, suppression (including amplitude imbalance), band statistics, and the original's input/format/validation rules |
| `esapf-gui` | Replica of the 2002 window: same layout, colours, tooltips and behaviour. The graph is 98–99 % pixel-identical to the original's. Exit shows an About box with credits and the GPL notice. |
| `esapf` (CLI) | `design` and `analyse` commands, with CSV sweep export |
| CI | Tests on Linux and Windows, builds, self-tests, artefacts, and releases on `v*` tags |
| Tooling | Wine setup, oracle capture, model verification, GUI render/diff, icon generator |
| Docs | `FORMULAS.md`, `ORIGINAL_BEHAVIOUR.md`, `DEVELOPING.md`, `WINDOWS_TEST.md`, `CLAUDE.md`, `ROADMAP.md` |

## Deviations from the plan

- **No pyqtgraph.** A small custom painter reproduces the original graph exactly and keeps the
  build smaller.
- **No AppImage.** A single-file Linux executable serves the same purpose with less tooling.
- **Title and Exit dialog** are the new project's, as described above.

## Open items

1. Run the real Windows 10/11 test (`docs/WINDOWS_TEST.md`). A friend of the user will do this.
2. Choose Phase 6 extensions from `ROADMAP.md` §7.1.
3. Optional: tag a first release (`v0.1.0`), and decide on public visibility. Before going
   public, consider rewriting commit author e-mails to GitHub's noreply address.

## Credits

- Lawrence Woolf, GJ3RAX: original program and published example designs.
- Dr. Ralph Oppelt, DB2NP: design equations (after G. Wunsch, 1958 and S. Darlington, 1950).
- KK7B (R2/T2), Philips AN1981 and N4BCU: the example networks used as test cases.
