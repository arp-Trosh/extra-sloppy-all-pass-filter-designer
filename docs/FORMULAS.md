# Formulas

These are all the formulas used by the original J-Tek *All Pass Filter Designer* (GJ3RAX,
2002–2004) and by this re-implementation.

Each formula is marked with how it was established:

- **[oracle]** reproduces the original program exactly (tests in `tests/test_vs_original.py`).
- **[article]** reproduces Oppelt's published worked example (`tests/test_core.py`).
- **[proven]** was checked against exact Jacobi elliptic functions (`tests/test_elliptic.py`).

Notation:

- F is frequency in Hz, ω = 2πF.
- τ = R·C is a time constant.
- Path 1 and path 2 are the two all-pass chains, each with n sections.

---

## 1. First-order all-pass section

The circuit is an op-amp with R1 (input) and R2 (feedback), where R1 = R2. Its non-inverting
input is fed from the signal through a series R with a C to ground. GJ3RAX's schematic calls
the frequency-setting pair C3 and R4.

```
H(jω) = (1 − jωτ) / (1 + jωτ),        τ = R·C
|H(jω)| = 1                             (constant gain, provided R1 = R2)
φ(ω) = −2·arctan(ωτ)                    (0° at DC → −180° at ∞)
φ = −90°  at  F90 = 1 / (2π·R·C)                                       [oracle]
```

If R and C are swapped, H becomes −H. The phase then runs from −180° to 0°, and the phase
*difference* between the two chains is unchanged.

**Display in the original:** F( ) = `Int(F90)` (truncated). R( ) = `Format(R[kΩ], "0.000000")`.
R in kΩ times C in nF gives τ in µs.

## 2. Two-path network and phase error

```
Δφ(ω) = 2·Σ_v arctan(ω·τ1_v) − 2·Σ_v arctan(ω·τ2_v)        (Oppelt eq. 13)
ε(ω)  = Δφ(ω) − 90°                                           [oracle]
```

ε is the phase error plotted in blue by the original. It is signed, and positive means the
difference is above 90°.

## 3. Unwanted-sideband suppression

In a phasing SSB modulator or demodulator the two audio paths are mixed with quadrature
carriers and summed. Let the audio phase difference be 90° + ε and the path gain ratio be A.
The wanted and unwanted sidebands then add up to:

```
wanted   ∝ 1 + A² + 2A·cos ε
unwanted ∝ 1 + A² − 2A·cos ε

S = 10·log10[(1 + A² + 2A·cos ε) / (1 + A² − 2A·cos ε)]  dB
```

For equal amplitudes (A = 1), the case the original uses:

```
S = 10·log10[(1 + cos ε)/(1 − cos ε)] = −20·log10|tan(ε/2)|            [oracle]
```

| ε | 0.1° | 0.5° | 1° | 2° | 5° |
|---|---|---|---|---|---|
| S | 61.2 dB | 47.2 dB | 41.2 dB | 35.2 dB | 27.2 dB |

The original plots S in red on a fixed 0–80 dB axis. ε = 0 gives S = ∞.
`esapf.core.suppression_db(err, amplitude_ratio=A)` also handles A ≠ 1.

## 4. Design: equiripple 90° network (Oppelt / Wunsch / Darlington)

Given the band F1…F2 and n sections per path, the time constants that minimise the largest
|ε| over the band are the elliptic-function (Chebyshev/equiripple) solution. The original
uses Oppelt's closed form (*VHF Communications* 2/1987, eqs. 7–12):

```
κ   = F1 / F2                                                  (7)
ε0  = ½ · (1 − √κ) / (1 + √κ)                                  (8)
q   = ε0 + 2ε0⁵ + 15ε0⁹ + 150ε0¹³ + 1707ε0¹⁷                  (9)   ← exactly 5 terms [oracle]
k_v = (4v + 1) / (8n),          v = 0 … n−1                    (10)

          Σ_{m=0..3} q^(m(m+1)) · cos((2m+1)·π·k_v)
τ1_v = ─────────────────────────────────────────────── · 1/√(ω1·ω2)   (11) ← exactly 4 terms [oracle]
       Σ_{m=0..3} (−1)^m · q^(m(m+1)) · sin((2m+1)·π·k_v)

τ2_v = 1 / (ω1 · ω2 · τ1_v)                                    (12)
R_v  = τ_v / C              (all capacitors equal to the default C)
```

- Row v + 1 of path 1 (columns F1, R1, C1) holds τ1_v. Its F90 rises down the table.
- Row v + 1 of path 2 holds τ2_v. Its F90 falls down the table.
- The formulas are symmetric in F1 and F2.

**Verification:**

- **[article]** For 270–3600 Hz and n = 4, the code gives τ1 = 2344.8, 369.52, 123.44 and
  36.173 µs, and τ2 = 11.114, 70.524, 211.11 and 720.43 µs. The maximum error is 0.011°.
- **[oracle]** All 132 R values in 19 Design cases match the original to every displayed digit.

### 4.1 What the series are (closed form)

Eq. 9 is the series expansion of the **Jacobi nome** q = exp(−π·K′/K) for the modulus
k = √(1 − κ²), where the complementary modulus k′ = κ. The ratio in eq. 11 is a ratio of theta
functions θ2/θ1, which gives:

```
τ1_v = cs(2K·k_v, k) / ω1          cs = cn/sn,  K = K(k)  (complete elliptic integral)   [proven]
```

### 4.2 Achievable accuracy

The phase error ripples equally between ±ε_max across the band:

```
ε_max ≈ 4 · q^(2n)  radians                                                         [proven]
```

This is accurate to 0.1 % for n ≥ 2. Each extra section per path multiplies the error by
about q², which is about 0.08 for a 270–3600 Hz band.

| Band | n = 2 | n = 3 | n = 4 | n = 6 |
|---|---|---|---|---|
| 300–3000 Hz | 1.08° | 0.074° | 0.0051° | 0.00002° |
| 270–3600 Hz | 1.60° | 0.133° | 0.011° | 0.00008° |

### 4.3 Limitation of the original's truncation

Five terms of eq. 9 and four of eq. 11 are plenty for speech bands. Up to F2/F1 = 20 the
worst-case error is within 0.04 % of optimal. For very wide bands, however, q gets large and the
truncated series no longer converges well:

| Band, n | Exact elliptic design | Original (5/4 terms) |
|---|---|---|
| 270–3600 Hz, n = 3 | 0.1335° | 0.1335° |
| 50–5000 Hz, n = 5 | 0.0607° | 0.0636° |
| 10–20000 Hz, n = 6 | **0.315°** | **1.57°** |
| 10–100000 Hz, n = 6 | **0.86°** | **9.97°** |

More series terms help, but they converge slowly once F2/F1 is above about 50. For example,
`oppelt_design(..., nome_terms=7, tau_terms=8)` still gives 0.0611° at 50–5000 Hz. The exact
design in §4.4 (`elliptic_design`, used by Bill Mode) gives the optimal values in the left column.

### 4.4 Any total number of sections, odd or even (`elliptic_design`, Bill Mode)

The equiripple solution is really defined for **N poles in total**, not n per path. Place them at

```
k_j = (2j + 1) / (4N),   j = 0 … N−1,     τ_j = cs(2K·k_j, k) / ω1                 [proven]
```

and give them alternately to the two paths: path 1 takes even j, path 2 takes odd j. Because
cs(K − u)·cs(u) = k′, pole j and pole N−1−j are reciprocal partners: τ_j·τ_{N−1−j} = 1/(ω1ω2).

- **Even N = 2n:** the even j are exactly Oppelt's k_v = (4v + 1)/(8n) (eq. 10), and every
  path-1 pole's partner is in path 2 (eq. 12). This is the design of §4.
- **Odd N:** path 1 gets (N + 1)/2 sections and path 2 gets (N − 1)/2. The middle pole
  j = (N − 1)/2 is its own partner, τ = 1/√(ω1ω2), so its f90 is the geometric centre √(F1·F2).
  It is in path 1 when N ≡ 1 (mod 4) and in path 2 otherwise. Above the band, path 1 has one
  extra 180° of phase lag, but inside the band the difference is still 90° ± ε.

In both cases the error ripples equally, reaching ±ε_max N + 1 times across the band
(Chebyshev alternation), with

```
ε_max ≈ 4 · q^N  radians          (asymptotic; within 0.2 % once ε_max < 1°)              [proven]
```

So each extra section, odd or even, multiplies the error by about q. For 270–3600 Hz:

| N | 5 | 6 | 7 | 8 | 9 | 11 | 12 |
|---|---|---|---|---|---|---|---|
| ε_max | 0.462° | 0.133° | 0.0386° | 0.0111° | 0.0032° | 0.00027° | 0.00008° |

`elliptic_design(f1, f2, total)` computes q exactly with the arithmetic-geometric mean,
q = exp(−π·agm(1, k′)/agm(1, k)), and sums eq. 11's theta series until its terms fall below
1e-18. This removes the truncation problem of §4.3. For even N it agrees with
`oppelt_design(f1, f2, N/2)` to within 2·10⁻⁷ relative for speech bands; that is at most 0.04 Ω
on a 174 kΩ resistor. `oppelt_design()` and the classic window are unchanged.
`tests/test_elliptic.py` checks all of this against mpmath's Jacobi functions.

## 5. Graph geometry of the original (for the replica)

The graph area is 455 × 209 px with a 2-px sunken border. Coordinates are in pixels.

```
x = 1 + 226.5·log10(F / 100)          100 Hz … 10 kHz (two decades)
y_phase = 104 − (ε / scale)·103        scale ∈ {10, 5, 2, 1, 0.5, 0.2, 0.1} degrees
y_supp  = 208 − (S / 80)·207           0 … 80 dB
```

See `docs/ORIGINAL_BEHAVIOUR.md` §4 for the grid and colours.

## References

1. R. Oppelt, DB2NP, "The Generation and Demodulation of SSB Signals using the Phasing
   Method", *VHF Communications* 2/1987, pp. 66–72.
2. G. Wunsch, "Zur praktischen Berechnung von Zwei-Phasen-Netzwerken",
   *Nachrichtentechnik* 4/1958, pp. 154–158.
3. S. Darlington, "Realization of a constant phase difference", *Bell System Technical
   Journal* 29 (1950), pp. 94–104.
4. L. Woolf, GJ3RAX, J-Tek All Pass Filter Designer, <https://www.gj3rax.com/apf.htm>.
