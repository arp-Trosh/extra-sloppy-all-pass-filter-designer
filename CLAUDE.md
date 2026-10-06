# CLAUDE.md: notes for AI assistants working on this repo

Extra Sloppy All Pass Filter Designer is a GPL-3.0 clean-room re-implementation of GJ3RAX's
2002 VB6 *All Pass Filter Designer* (90° phase networks for phasing SSB). It uses Python 3.14,
PySide6 and NumPy, managed with uv.

## Commands
- `uv run pytest`: all tests, about 2 s, offscreen Qt.
- `uv run ruff check . && uv run ruff format --check . && uv run mypy`: must pass (CI runs these).
- `uv run esapf-gui` runs the GUI; `uv run esapf design 270 3600 -n 3 -c 10` runs the CLI.
- `uv run --group build packaging/build.py` builds the executable; `dist/esapf-gui --self-test`
  checks it.

## Invariants (do not break)
- `src/esapf/core/` is pure maths: no Qt imports (a test enforces it). Internal units are
  seconds and hertz; the UI uses kΩ, nF and Hz.
- `oppelt_design()` defaults (5 nome terms, 4 τ terms) reproduce the original exactly. Never
  change the defaults; add new algorithms as new functions.
- Button behaviour lives in `src/esapf/form.py` (`FormState`), not in widgets.
- The classic window (`gui/layout.py`, `gui/graph.py`) must keep matching the original.
  `tests/test_vs_original.py`, `test_form_replay.py` and `test_gui.py` check this against
  fixtures captured from the real program. Put new features in new dialogs or views.
- Fonts must stay TrueType (`layout.FONT_FAMILIES`). The bitmap "MS Sans Serif" breaks on Windows.
- `tests/fixtures/original/` is ground truth captured from `Apf.exe`. Never edit it by hand;
  re-capture with `tools/oracle/capture.py` (see docs/DEVELOPING.md).
- Third-party files (the original exe, web pages, the 1987 article) are never committed;
  `reference/fetch.sh` downloads them.
- Every source file starts with `# SPDX-License-Identifier: GPL-3.0-only`.

## Where to read
- `docs/FORMULAS.md`: all formulas, with their verification status.
- `docs/ORIGINAL_BEHAVIOUR.md`: the spec of the original (formats, buttons, validation, graph).
- `docs/DEVELOPING.md`: architecture, recipes for extensions, releasing.
- `ROADMAP.md`: phases, decisions and the Phase 6 backlog. The user decides phase by phase.
