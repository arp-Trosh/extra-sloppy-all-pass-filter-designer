# Developing and extending

This guide covers how the code is organised, the rules that keep it maintainable, and recipes
for the most likely changes.

## Setup

```sh
uv sync                      # Python 3.14 (.python-version), all runtime + dev dependencies
uv run pytest                # 300+ tests, about 2 s; GUI tests run offscreen
uv run ruff check . && uv run ruff format --check . && uv run mypy      # what CI runs
uv run esapf-gui             # the GUI
uv run esapf design 270 3600 -n 3 -c 10      # the CLI
```

## Layout and layering

```
src/esapf/
  core/            pure maths (NumPy only). NEVER imports Qt; a test enforces this.
    design.py        Oppelt design → time constants        (docs/FORMULAS.md §4)
    allpass.py       phase of chains, phase error          (§1–2)
    metrics.py       suppression, band statistics           (§3)
    network.py       Section / Network: R [kΩ], C [nF] ↔ τ [s]
    legacy.py        original-program quirks: VB Val(), display formats, error messages
    eseries.py       IEC 60063 E6…E192 tables, nearest standard value
  form.py          FormState: window state as displayed text + button semantics (no Qt)
  bill.py          BillState: the same for Bill Mode (ohms, E-series, axis range)
  gui/             Qt widgets only render FormState / BillState and forward events
    layout.py        geometry, colours, fonts, tooltips of the 2002 window
    graph.py         QPainter replica of the original graph
    main_window.py   widgets ↔ FormState binding (the classic window)
    bill_graph.py    Bill Mode graph: resizable, labelled, settable X range
    bill_window.py   Bill Mode window (Qt layouts) ↔ BillState binding
    app.py           entry point (esapf-gui), --bill, Ctrl+B mode switch, --self-test
  cli.py           command line (esapf)
tests/             see "Tests" below
tools/             wine.sh (original under Wine), oracle/ (fixture capture), render_gui.py
packaging/         PyInstaller spec + build script, icon generator
docs/              FORMULAS, ORIGINAL_BEHAVIOUR (the spec), WINDOWS_TEST, this file
```

**Rules**

1. Maths lives in `core/` and is unit-tested without a GUI. New calculations go there first.
2. Behaviour lives in `form.py` (classic) and `bill.py` (Bill Mode), not in widgets. That is what lets the captured fixtures be
   replayed headlessly.
3. The classic window must keep matching the original. `tests/test_vs_original.py`,
   `test_form_replay.py` and `test_gui.py` fail if it drifts. New features go in Bill Mode
   (ROADMAP.md §0) or in other new windows or dialogs, never in the classic layout.
4. Units at the boundaries: the classic UI uses kΩ, nF and Hz; Bill Mode shows Ω (`bill.py`
   converts); `core` uses seconds and hertz.
   `Section` converts between them.
5. `mypy --strict` covers all of `src/`. Ruff enforces style (line length 100).
6. Every source file starts with `# SPDX-License-Identifier: GPL-3.0-only`.

## Tests

| File | What it guards |
|---|---|
| `test_core.py` | Oppelt's published example, design identities, metrics, legacy parsing, CLI |
| `test_elliptic.py` | closed forms in FORMULAS.md, against exact Jacobi functions (mpmath) |
| `test_vs_original.py` | every captured table, recalculation, validation message and graph curve |
| `test_form_replay.py` | all 44 captured cases replayed through `FormState` |
| `test_gui.py` | the same cases through the real widgets, and graph pixels vs the original |
| `test_bill.py` | E-series tables and lookup, `BillState`, the Bill Mode window, mode switching |
| `test_smoke.py` | imports, the core/Qt separation, CLI and GUI entry points |

The fixtures in `tests/fixtures/original/` come from the original `Apf.exe`. To add a case:

1. Add it to `tools/oracle/cases.py`.
2. Run `tools/wine.sh setup --oracle`, then `tools/oracle/capture.py <case>`. This runs on a
   private Xvfb display and needs Xvfb, xdotool and ImageMagick.
3. Commit the new JSON and PNG files. The tests pick them up automatically.

## Recipes

**Add a calculation** (e.g. tolerance analysis, 6.5):

1. Add a function in `core/` (e.g. `core/tolerance.py`) taking `Network` or time constants.
2. Export it in `core/__init__.py`.
3. Write unit tests.
4. Expose it in the CLI (`cli.py` subcommand) and/or the GUI.

**Add a GUI feature without disturbing the replica:**

1. Add state and logic to `FormState`, or to a new state class, and test it headlessly.
2. Add the widgets in a separate dialog or window opened from a new control. For example, a
   small menu button in an unused corner, or a right-click context menu on the graph or table.
3. Add a `test_gui.py` test that drives it with `QTest`.

**Change the design algorithm** (e.g. exact elliptic, 6.2):

1. Keep `oppelt_design()` with its default 5/4-term truncation, because the replica must
   reproduce the original.
2. Add a separate function (e.g. `elliptic_design()`) and a UI or CLI option to choose it.
3. `tests/test_elliptic.py::exact` is a ready-made reference.

**Allow more than 6 sections:** `core` already supports any n. The classic window is limited
to 6 by its layout (6 table rows and 6 buttons), so a larger n needs a new view.

## Releasing

1. Bump `__version__` in `src/esapf/__init__.py`, which is the only place the version lives.
2. Commit, then `git tag vX.Y.Z && git push --tags`.
3. CI tests, builds and self-tests the executables, then publishes a GitHub Release with
   `esapf-gui-X.Y.Z-windows-x64.exe` and `…-linux-x86_64`. The release text comes from
   `.github/release-notes.md`. Tags with a suffix (`v0.2.0-rc1`) become pre-releases, and the
   matching PEP 440 version is `0.2.0rc1`.
4. Before announcing, run `docs/WINDOWS_TEST.md` on real Windows.

**Local build:** `uv run --group build packaging/build.py`, then `dist/esapf-gui --self-test`.
PyInstaller only builds for the OS it runs on. To see the Windows `.exe` under Wine, use
`wine esapf-gui.exe --self-test` with the prefix from `tools/wine.sh setup`.

## Troubleshooting

- **The GUI test fails only on one OS:** fonts differ between platforms, but the tests compare
  text and graph pixels only (the graph draws no text), so look for real behaviour
  differences first.
- **The built executable fails `--self-test`:** check the plugin and library filters in
  `packaging/esapf-gui.spec`. Qt needs `platforms/qoffscreen` for the self-test, and
  `qxcb`/`qwayland`/`qwindows` for real use.
- **Text in the window is not bold or is misplaced on Windows:** a bitmap font has been
  picked. Keep `layout.FONT_FAMILIES` TrueType only.
