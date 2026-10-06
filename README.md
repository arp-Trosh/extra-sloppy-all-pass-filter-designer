# Extra Sloppy All Pass Filter Designer

A modern, cross-platform (Linux / Windows 10 / Windows 11) re-implementation of the
J-Tek **All Pass Filter Designer** by Lawrence Woolf, GJ3RAX. The tool designs and analyses
the 90° phase-difference all-pass networks used in phasing-type SSB transmitters and receivers.

The original is a 2002 Visual Basic 6 program that is no longer maintained and whose source
code is lost (<https://www.gj3rax.com/apf.htm>). This project is a **clean-room
re-implementation**. It is built from the published mathematics (R. Oppelt, DB2NP,
*VHF Communications* 2/1987) and checked against the original program running under Wine.
No code from the original is used.

> **Status:** Phases 0–2 complete. The maths core and CLI reproduce the original exactly
> ([docs/ORIGINAL_BEHAVIOUR.md](docs/ORIGINAL_BEHAVIOUR.md)). The GUI comes in Phase 3. See [ROADMAP.md](ROADMAP.md).

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
