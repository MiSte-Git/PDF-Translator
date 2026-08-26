"""One-time/rerunnable export: ui/i18n_data.py's DE/EN catalogues -> plain
JSON files under webapp/static/i18n/, so the browser frontend (Schritt 3
of the local-server+pywebview migration, see Backlog.md 26.08.2026) uses
the exact same German/English strings as the Qt app - "Übersetzungsanbieter"
means the same thing in both UIs because it IS the same string, not a
separately maintained copy that can drift.

Not imported at server runtime (webapp/server.py never imports
ui.i18n_data - see webapp/__init__.py's "must never import PySide6"
docstring; ui/i18n_data.py itself has no Qt import, but keeping the
export as a standalone, occasionally-rerun script rather than a runtime
dependency matches the migration plan's own wording: "wird daraus per
kleinem Export-Skript befüllt (einmalig von Hand oder als kleines
Build-Skript, kein Laufzeit-Import von ui.i18n_data in den
Server-Prozess nötig)").

Usage: python -m webapp.tools.export_i18n
Rerun after any change to ui/i18n_data.py's DE/EN dicts to keep the
frontend catalogues in sync - there is no test enforcing this (a runtime
import would make that easy, an export script cannot self-check without
becoming the thing it was written to avoid), so this must be run by hand
whenever a relevant key changes.
"""
from __future__ import annotations

import json
from pathlib import Path

from ui.i18n_data import CATALOGUES

STATIC_I18N_DIR = Path(__file__).resolve().parent.parent / "static" / "i18n"


def export() -> None:
    STATIC_I18N_DIR.mkdir(parents=True, exist_ok=True)
    for locale, catalogue in CATALOGUES.items():
        target = STATIC_I18N_DIR / f"{locale}.json"
        target.write_text(
            json.dumps(catalogue, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote {target} ({len(catalogue)} keys)")


if __name__ == "__main__":
    export()
