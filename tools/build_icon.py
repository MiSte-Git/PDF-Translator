"""Regenerates the rasterised app icons in assets/ from assets/icon.svg.

assets/icon.svg is the single source of truth; the three derived files are
committed to the repository anyway so that neither the developer launcher
entry (python -m bootstrap.desktop_integration --dev), the bootstrapper's
Stage 2 launcher entry, nor ui/app.py's window icon need any SVG
rasteriser at runtime:

- assets/icon.png   256x256, used by the Linux .desktop entry and as
                    ui/app.py's window icon on every platform
- assets/icon.ico   multi-size, used by the Windows Start Menu .lnk
- assets/icon.icns  multi-size, used by the macOS .app bundle

Usage (one-off, only after editing icon.svg):

    pip install cairosvg pillow
    python tools/build_icon.py
"""
from __future__ import annotations

import io
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
ASSETS_DIR = REPO_ROOT / "assets"
SVG_PATH = ASSETS_DIR / "icon.svg"

PNG_SIZE = 256
ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
ICNS_SIZES = [16, 32, 64, 128, 256, 512]


def _render(svg_bytes: bytes, size: int):
    import cairosvg
    from PIL import Image

    png = cairosvg.svg2png(bytestring=svg_bytes, output_width=size, output_height=size)
    return Image.open(io.BytesIO(png)).convert("RGBA")


def main() -> int:
    try:
        import cairosvg  # noqa: F401
        from PIL import Image  # noqa: F401
    except ImportError as exc:
        print(f"Missing dependency: {exc}. Run: pip install cairosvg pillow", file=sys.stderr)
        return 1

    svg_bytes = SVG_PATH.read_bytes()

    _render(svg_bytes, PNG_SIZE).save(ASSETS_DIR / "icon.png", format="PNG")

    ico_frames = [_render(svg_bytes, s) for s in ICO_SIZES]
    ico_frames[-1].save(
        ASSETS_DIR / "icon.ico",
        format="ICO",
        sizes=[(s, s) for s in ICO_SIZES],
        append_images=ico_frames[:-1],
    )

    icns_frames = [_render(svg_bytes, s) for s in ICNS_SIZES]
    icns_frames[-1].save(
        ASSETS_DIR / "icon.icns",
        format="ICNS",
        append_images=icns_frames[:-1],
    )

    for name in ("icon.png", "icon.ico", "icon.icns"):
        print(f"wrote {ASSETS_DIR / name} ({(ASSETS_DIR / name).stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
