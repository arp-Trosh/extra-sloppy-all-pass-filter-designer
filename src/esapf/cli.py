# SPDX-License-Identifier: GPL-3.0-only
"""Command-line interface.

esapf design 270 3600 -n 3 -c 10            design + table, like the Design button
esapf analyse --path1 649:2.7,232:1,52.3:1 --path2 15:1,113:1,511:1 --band 300 3000
add --csv FILE to either command to write the phase-error/suppression sweep
"""

import argparse
import csv
import sys
from collections.abc import Sequence

import numpy as np

from esapf import __version__
from esapf.core import Network, Section, band_stats, log_grid, oppelt_design, phase_error_deg
from esapf.core.legacy import InputError, format_f, format_r, parse_design_inputs
from esapf.core.metrics import PLOT_F_MAX, PLOT_F_MIN, suppression_db


def parse_path(text: str) -> tuple[Section, ...]:
    """'R:C,R:C,...' with R in kΩ and C in nF."""
    try:
        pairs = [item.split(":") for item in text.split(",")]
        sections = tuple(Section(float(r), float(c)) for r, c in pairs)
    except ValueError as e:
        raise argparse.ArgumentTypeError(f"expected R:C,R:C,... (kΩ:nF), got {text!r}") from e
    if any(s.r_kohm <= 0 or s.c_nf <= 0 for s in sections):
        raise argparse.ArgumentTypeError("all component values must be > 0")
    return sections


def print_table(net: Network, formatted_r: bool) -> None:
    cols = ("F1() Hz", "R1() kΩ", "C1() nF", "F2() Hz", "R2() kΩ", "C2() nF")
    print(f"{'':4}{cols[0]:>9}{cols[1]:>14}{cols[2]:>9}   {cols[3]:>9}{cols[4]:>14}{cols[5]:>9}")
    for i, (a, b) in enumerate(zip(net.path1, net.path2, strict=True), start=1):
        r1 = format_r(a.r_kohm) if formatted_r else f"{a.r_kohm:g}"
        r2 = format_r(b.r_kohm) if formatted_r else f"{b.r_kohm:g}"
        print(
            f"({i}) {format_f(a.f90):>9}{r1:>14}{a.c_nf:>9g}   "
            f"{format_f(b.f90):>9}{r2:>14}{b.c_nf:>9g}"
        )


def report(net: Network, band: Sequence[float] | None, csv_path: str | None, points: int) -> None:
    if band:
        st = band_stats(band[0], band[1], net.tau1, net.tau2)
        print(
            f"\n{min(band):g}-{max(band):g} Hz: max |phase error| {st.max_abs_error_deg:.4f}°, "
            f"min suppression {st.min_suppression_db:.1f} dB"
        )
    if csv_path:
        f = log_grid(PLOT_F_MIN, PLOT_F_MAX, points)
        err = phase_error_deg(f, net.tau1, net.tau2)
        sup = suppression_db(err)
        with open(csv_path, "w", newline="") as fh:
            w = csv.writer(fh)
            w.writerow(["frequency_hz", "phase_error_deg", "suppression_db"])
            for row in zip(f, err, np.minimum(sup, 999.0), strict=True):
                w.writerow([f"{x:.6g}" for x in row])
        print(f"sweep written to {csv_path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="esapf", description="Extra Sloppy All Pass Filter Designer"
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="cmd", required=True)

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--csv", metavar="FILE", help="write 100 Hz-10 kHz sweep to CSV")
    common.add_argument("--points", type=int, default=1001, help="sweep points (default 1001)")

    d = sub.add_parser("design", parents=[common], help="design a network (Design button)")
    d.add_argument("f1", help="lower band edge, Hz")
    d.add_argument("f2", help="upper band edge, Hz")
    d.add_argument(
        "-n",
        type=int,
        choices=range(1, 7),
        default=3,
        metavar="1-6",
        help="sections per path (default 3)",
    )
    d.add_argument("-c", default="10", help="capacitor value, nF (default 10)")

    a = sub.add_parser("analyse", parents=[common], help="analyse given components (Phase)")
    a.add_argument("--path1", type=parse_path, required=True, help="R:C,... in kΩ:nF")
    a.add_argument("--path2", type=parse_path, required=True, help="R:C,... in kΩ:nF")
    a.add_argument(
        "--band", type=float, nargs=2, metavar=("F1", "F2"), help="report worst case over this band"
    )

    args = parser.parse_args(argv)
    if args.cmd == "design":
        try:
            inp = parse_design_inputs(args.f1, args.f2, args.c)
        except InputError as e:
            print(f"ERROR: {e}", file=sys.stderr)
            return 2
        net = Network.from_design(oppelt_design(inp.f1, inp.f2, args.n), inp.c_nf)
        print_table(net, formatted_r=True)
        report(net, (inp.f1, inp.f2), args.csv, args.points)
    else:
        if len(args.path1) != len(args.path2):
            parser.error("--path1 and --path2 must have the same number of sections")
        net = Network(args.path1, args.path2)
        print_table(net, formatted_r=False)
        report(net, args.band, args.csv, args.points)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
