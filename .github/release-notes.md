**Extra Sloppy All Pass Filter Designer** is a modern re-implementation of the J-Tek *All Pass
Filter Designer* by Lawrence Woolf, GJ3RAX, a 2002 tool for designing 90° all-pass phase
networks for phasing SSB transmitters and receivers. It reproduces the original's results
exactly and runs on Windows 10/11 and Linux.

## What's new in 0.2.0

**Bill Mode**, a second, practical window. Open it with the new **Bill Mode** button in the
classic window or with Ctrl+B. It adds:

- 90° frequencies to 2 decimal places, and resistances in ohms (to 0.01 Ω);
- the nearest **E6, E12, E24, E48, E96 or E192** resistor next to each calculated value, or the
  **pair** from that series whose sum comes closest;
- the graph drawn from either the perfect or the E-series resistors, with a settable
  frequency range, axis labels, and the worst-case error and suppression across F1–F2;
- a drop-down list of **E6 capacitors (10 pF to 1 µF)** for each section; after Design, picking
  a capacitor recalculates that section's resistor;
- **2 to 12 sections in total, odd counts included** (3, 5, 7, 9, 11), designed exactly with
  elliptic functions. This also fixes the original's loss of accuracy for very wide bands.

The classic window still reproduces the original program exactly. Its only change is the
Bill Mode button, for which the Design button was made narrower.

## Download

| System | File |
|---|---|
| Windows 10 / 11 (64-bit) | `esapf-gui-…-windows-x64.exe` |
| Linux x86-64 (glibc 2.35+: Ubuntu 22.04+, Debian 12+, Fedora 36+, Arch) | `esapf-gui-…-linux-x86_64` |

Each download is a single file, and nothing needs installing.

- **Windows:** the program is not code-signed. If SmartScreen says *"Windows protected your
  PC"*, click **More info → Run anyway**. The first start takes a few seconds.
- **Linux:** run `chmod +x esapf-gui-*-linux-x86_64`, then start the file.

## Testing

Pre-releases (`-rc`) are for testing. The checklist is in
[docs/WINDOWS_TEST.md](https://github.com/arp-Trosh/extra-sloppy-all-pass-filter-designer/blob/main/docs/WINDOWS_TEST.md).
Please report results as a GitHub issue, or to the person who sent you the link.

## More

- How it works and all the formulas:
  [docs/SUMMARY.md](https://github.com/arp-Trosh/extra-sloppy-all-pass-filter-designer/blob/main/docs/SUMMARY.md)
- Licence: GPL-3.0. The program comes with no warranty.
- Credits: Lawrence Woolf, GJ3RAX (original program) and Dr. Ralph Oppelt, DB2NP (design equations).
