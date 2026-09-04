"""Regenerates the rasterised flag icons in assets/flags/ from the .svg
sources in the same directory - same pattern as tools/build_icon.py (see
that module's docstring), one PNG per locale rather than icon.png/.ico/
.icns since these are only ever used as small QIcon()s on the language-
switcher flag bar (ui/app.py::MainWindow), never as an OS-level app icon.

assets/flags/<code>.svg is the source of truth for each flag; the
matching assets/flags/<code>.png is committed to the repository anyway so
ui/app.py needs no SVG rasteriser at runtime (same reasoning as
APP_ICON_PATH using assets/icon.png, not icon.svg - see tools/build_icon.py).

All nine flags share one 30x20 (3:2) viewBox regardless of a country's
real flag proportions (Germany is really 3:5, Denmark-style crosses
aren't involved here at all, etc.) so they sit flush in a uniform-size
row of buttons - the same simplification most compact flag-icon sets
use. Deliberately simplified art (no coat of arms on the Spanish flag,
a plain 5x4 checkerboard standing in for Croatia's full coat of arms,
a Union Jack drawn with straight overlapping bars instead of true
mitred diagonals) - legible at ~28px wide is the only goal.

Usage (one-off, only after editing one of the .svg files):

    pip install cairosvg pillow
    python tools/build_flags.py
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
FLAGS_DIR = REPO_ROOT / "assets" / "flags"

# 2x a 28x19 display size, so QIcon still looks crisp on HiDPI screens.
PNG_WIDTH = 56
PNG_HEIGHT = 38


def main() -> int:
    try:
        import cairosvg
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run: pip install cairosvg pillow", file=sys.stderr)
        return 1

    svg_paths = sorted(FLAGS_DIR.glob("*.svg"))
    if not svg_paths:
        print(f"No .svg files found in {FLAGS_DIR}", file=sys.stderr)
        return 1

    for svg_path in svg_paths:
        png_path = svg_path.with_suffix(".png")
        cairosvg.svg2png(
            bytestring=svg_path.read_bytes(),
            output_width=PNG_WIDTH,
            output_height=PNG_HEIGHT,
            write_to=str(png_path),
        )
        print(f"wrote {png_path} ({png_path.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
