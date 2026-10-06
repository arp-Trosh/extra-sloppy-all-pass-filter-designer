# Extra Sloppy All Pass Filter Designer

A modern, cross-platform (Linux / Windows 10 / Windows 11) re-implementation of the
J-Tek **All Pass Filter Designer** by Lawrence Woolf, GJ3RAX. The tool designs and analyses
the 90° phase-difference all-pass networks used in phasing-type SSB transmitters and receivers.

The original is a 2002 Visual Basic 6 program that is no longer maintained and whose source
code is lost (<https://www.gj3rax.com/apf.htm>). This project is a **clean-room
re-implementation**. It is built from the published mathematics (R. Oppelt, DB2NP,
*VHF Communications* 2/1987) and checked against the original program running under Wine.
No code from the original is used.

> **Status:** Phases 0–5 complete. It runs on Linux and Windows 10/11, reproduces the original
> exactly, and its formulas are documented. See **[docs/SUMMARY.md](docs/SUMMARY.md)** for the
> outcome and **[ROADMAP.md](ROADMAP.md)** for the plan and the optional extensions.

## Bill Mode

Besides the classic window, which copies the 2002 original, there is a practical window
called **Bill Mode**. Click **Bill Mode** (or **Classic Mode** to go back), or press **Ctrl+B**,
to switch between them (F1, F2, C and the section
count carry over), or start with `esapf-gui --bill`. Bill Mode shows:

- 90° frequencies to 2 decimal places and resistances in ohms (to 0.01 Ω);
- the nearest E6, E12, E24, E48, E96 or E192 resistor next to each calculated value, or the
  pair from that series whose sum comes closest;
- a drop-down list of E6 capacitors (10 pF to 1 µF) for each section, which also accepts typed
  values such as `4.7n` or `0.1µ`. After Design, changing a capacitor recalculates that
  section's resistor so its 90° frequency stays put;
- the graph from either the perfect or the E-series resistors, with a settable X-axis range,
  a frequency scale, and the worst-case error and suppression in the F1–F2 band.

## Documentation

| Document | For |
|---|---|
| [docs/SUMMARY.md](docs/SUMMARY.md) | What was done, the formulas, and the findings |
| [docs/FORMULAS.md](docs/FORMULAS.md) | All formulas with derivations and verification status |
| [docs/ORIGINAL_BEHAVIOUR.md](docs/ORIGINAL_BEHAVIOUR.md) | Specification of the original program (black-box tested) |
| [docs/DEVELOPING.md](docs/DEVELOPING.md) | Architecture, extending, testing, releasing |
| [docs/WINDOWS_TEST.md](docs/WINDOWS_TEST.md) | Manual test checklist for Windows 10/11 |
| [CLAUDE.md](CLAUDE.md) | Short guide for AI coding assistants |

## Download

Single-file executables for **Windows (x64)** and **Linux (x86_64)** are built by GitHub Actions.
You can get them from the *Releases* page, or from the artefacts of the latest CI run. No
installation is needed: download and run.

- **Windows:** the executable is not code-signed. If SmartScreen warns, choose *More info → Run anyway*.
- **Linux:** run `chmod +x esapf-gui-*-linux-x86_64` first. It needs glibc 2.35 or newer (Ubuntu 22.04+, Debian 12+, Fedora 36+ and Arch all qualify).

## Running from source

```sh
uv run esapf-gui                     # the GUI (or: python -m esapf.gui)
uv run esapf-gui --bill              # start in Bill Mode
```

## Building the executable

```sh
uv run --group build packaging/build.py     # -> dist/esapf-gui (Linux) or dist/esapf-gui.exe (Windows)
dist/esapf-gui --self-test                  # headless check: runs a design, exit code 0 = OK
```

PyInstaller builds only for the OS it runs on, so the Windows `.exe` must be built on Windows.
CI does this; see `.github/workflows/ci.yml`. Pushing a tag `v*` publishes a GitHub Release.

## Command line

```sh
uv run esapf design 270 3600 -n 3 -c 10          # like the Design button
uv run esapf analyse --path1 649:2.7,232:1,52.3:1 --path2 15:1,113:1,511:1 --band 300 3000
uv run esapf design 50 5000 -n 5 --csv sweep.csv # also write the 100 Hz–10 kHz sweep
```

## Reference material

The original executable, web pages and the 1987 article are copyright their authors and are
not included in this repository. To download them locally:

```sh
reference/fetch.sh
```

## Development

Requires [uv](https://docs.astral.sh/uv/).

```sh
uv sync                 # create .venv with all dependencies
uv run pytest           # tests
uv run ruff check .     # lint      (uv run ruff format . to format)
uv run mypy             # type-check the maths core
uv run esapf --help     # CLI
```

### Running the original program (Linux, Wine)

```sh
tools/wine.sh setup [--vbdec] [--oracle]  # project-local prefix in .wine/, VB6 runtime
                                          #   (+ VBDec disassembler, + oracle helper Python)
tools/wine.sh original          # run the original Apf.exe
tools/wine.sh vbdec             # open Apf.exe in VBDec
tools/wine.sh kill
```

### Re-capturing the reference fixtures (needs Xvfb, xdotool, ImageMagick)

```sh
tools/wine.sh setup --oracle
tools/oracle/capture.py [case ...]       # runs on a private Xvfb display (:99), never on your desktop
uv run tools/oracle/verify_model.py      # re-check the formulas against the fixtures
```

## Credits

- Lawrence Woolf, GJ3RAX: original *All Pass Filter Designer* (J-Tek, 2002–2004)
- Dr. (Eng.) Ralph Oppelt, DB2NP: design equations, *VHF Communications* 2/1987, pp. 66–72

## Licence

GPL-3.0-only. See [LICENSE](LICENSE).
