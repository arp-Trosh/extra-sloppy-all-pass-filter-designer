# Behaviour of the original J-Tek Apf.exe

This is the specification for the re-implementation. It was obtained by black-box testing of
the original (`Apf.exe`, version of 28 Jan 2004, SHA-256 `b6bb5682…16bb26c`) under Wine 11.19.
No decompilation was used.

- **Evidence:** 44 captured cases in `tests/fixtures/original/` (control values, message boxes
  and graph screenshots).
- **Captured with:** `tools/oracle/capture.py`.
- **Re-checked by:** `uv run tools/oracle/verify_model.py`.

## 1. Design maths (exact)

Source: R. Oppelt, DB2NP, *VHF Communications* 2/1987, eqs. 7–12. The series truncation was
identified from the oracle and is **part of the spec**, because it changes the results at wide
frequency ratios.

```
κ   = F1 / F2
ε   = ½ · (1 − √κ) / (1 + √κ)
q   = ε + 2ε⁵ + 15ε⁹ + 150ε¹³ + 1707ε¹⁷                      (exactly 5 terms)
k_v = (4v + 1) / (8n),   v = 0 … n−1
        Σ_{m=0..3} q^(m(m+1)) · cos((2m+1)·π·k_v)
τ1_v = ───────────────────────────────────────────── · 1/√(ω1·ω2)   (exactly 4 terms, m = 0..3)
        Σ_{m=0..3} (−1)^m q^(m(m+1)) · sin((2m+1)·π·k_v)
τ2_v = 1 / (ω1 · ω2 · τ1_v)          ω = 2πF
R_v  = τ_v / C
```

- **Path 1** (columns F1( ), R1( ), C1( )) gets τ1. Row *v + 1* holds the pole with
  k_v = (4v+1)/(8n). Its f90 rises row by row (e.g. 91, 688, 3078 Hz).
- **Path 2** gets τ2 in the same row order, so its f90 falls (10654, 1411, 315 Hz).
- **Accuracy of this model:** all 132 R values in the 19 Design cases match the original
  character for character.
  - Using 5 τ-terms instead of 4 breaks 48 of them.
  - Using 4 q-terms breaks 121 of them.
- **Symmetry:** the formula is symmetric in F1 and F2. Swapped limits (3600/270) give
  results identical to 270/3600, and the program does no swap or check. Equal limits
  (κ = 1, q = 0) are accepted and also produce a design.

## 2. Analysis maths (Phase button and graph)

```
τ_i       = R_i · C_i                                    (from the table: kΩ × nF → µs)
Δφ(f)     = 2·Σ arctan(2πf·τ1_i) − 2·Σ arctan(2πf·τ2_i)
ε(f)      = Δφ(f) − 90°                                  (signed; plotted in blue)
S(f)      = −20·log10|tan(ε/2)|  ≡ 10·log10[(1+cos ε)/(1−cos ε)]   (plotted in red)
```

- **Fit to the graphs:**
  - The blue curve matches with 0.4–0.6 px RMS.
  - The red curve matches with 0.5–1.2 px RMS.
- **Rejected alternatives:**
  - −20·log10|sin(ε/2)| is 1–2 dB off at large ε.
  - −20·log10|ε/2| is about 1 dB off at large ε.

## 3. Display formats

| Field | Format |
|---|---|
| F( ) Hz | `Int(1/(2π·τ))`, **truncated** (91.23 → 91, 315.8 → 315). After Phase it is computed from the R and C in the table. |
| R( ) kΩ after Design | `Format(R, "####0.000000")`, i.e. 6 decimals with a leading 0 below 1 (e.g. `0.678990`). |
| R( ), C( ) after editing | Left exactly as the user typed them; Phase does not reformat them. |
| C( ) nF after Design or Reset C | Copied verbatim from the default C box (e.g. `10`, `4.7`, `-10`). |
| Scale labels | `+1` / `-1`, `+0.5` / `-0.5`, and so on, following the selected scale button. |

## 4. Graph geometry

The graph is a PictureBox of 455 × 209 px. Its client area starts after a 2-px 3-D inset
border. Coordinates below are window pixels.

| Element | Mapping |
|---|---|
| x | `x = 1 + 226.5·log10(f / 100)`: 100 Hz at the left edge, 10 kHz at the right edge (2 decades) |
| Blue phase error | `y = 104 − (ε / scale)·103`: ±scale reaches the top and bottom edges |
| Red suppression | `y = 208 − (S / 80)·207`: 0 dB at the bottom, 80 dB at the top |
| Grid | Black solid vertical line at 1 kHz and black solid horizontal line at 0 / 40 dB, both 2 px wide. Dashed verticals at 200…900 Hz and 2…9 kHz, dashed horizontals at ±scale/2 (= 60 and 20 dB). |
| Off-range values | Clipped at the edges. A blue curve beyond ±scale is not visible. Near S > 80 dB peaks the red line meets the top edge for a few pixels; whether it is clamped or clipped can't be told apart at pixel level, and either reproduces the look. |
| Colours | Phase `#0000FF`, suppression `#FF0000`, grid `#000000`. The background is the system window colour. |

- The axis range is **fixed**: F1 and F2 only affect Design, never the plot range. In the
  `change_f_then_phase` case the graph is pixel-identical.
- Labels outside the PictureBox:
  - "Phase Error Degrees" in blue and "Suppression dB" in red.
  - Left axis ±scale / 0 in blue.
  - Right axis 0…80 in red, in steps of 20.
  - Bottom axis "100", "Hz", "1k" and "10k".

## 5. Buttons and state

| Action | Behaviour |
|---|---|
| Startup | F1 = 270, F2 = 3600, C = 10, n = 3 selected (yellow), scale 1 selected, table empty, empty grid. |
| **Filters 1–6** | Selects n (the selected button turns yellow). **Clears the table and the graph.** |
| **Design** | Validates the inputs (§6), fills n rows (F, R, C = default C) and draws the graph. Keeps the current scale. |
| **Reset C** | Copies the C box into the C cells of the n selected rows, even before Design. **No validation**: 0, −10 and empty are all copied. R is not recomputed. |
| **Phase** | Validates the table. Recomputes the F columns from R·C and redraws. Does not change R or C. On error, the table and graph are left as they were. |
| **Clear** | Empties all table cells and resets the graph to the empty grid. F1, F2, C, n and scale are kept. |
| **Scale buttons** | Change the ± labels and redraw the blue curve. The selection is shown in yellow and persists across Design. |
| **Exit** | Closes the program. The author's page says an about box with the old e-mail address is shown on exit (not captured; not needed). |

## 6. Validation (modal MsgBox, title `ERROR`)

Checks run in this order, and only the first failure is reported:

1. F1 < 10, empty or non-numeric (`abc`) → `F1 should not be below 10 Hz`
2. F2 < 10 → `F2 should not be below 10 Hz`
3. C ≤ 0 or empty (on Design) → `The Capacitor value C(nF) Must be Specified and Greater than Zero`
4. Phase with any component cell in the active rows ≤ 0 or empty, including an empty table →
   `All Component Values MUST be Specified and Greater than Zero`. Observed for R = 0, R empty
   and an empty table; C cells are assumed to be checked the same way, as the message says.

- There is **no upper limit** on F1 or F2. 10–100000 Hz is accepted.
- No check is made that F1 < F2.

## 7. Window layout

The window is a fixed 520 × 474 client area at 800×600-era sizing, with a light-cyan
background. The exact control rectangles are listed in `tools/oracle/job_runner.py` and the
`dump` output of `tools/oracle/w32.py`. Reference screenshots:
`form_startup_1_form.png` and `form_kk7b_2_form.png`.
