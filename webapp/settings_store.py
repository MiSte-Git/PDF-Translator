"""JSON-file settings persistence for webapp/ - the QSettings replacement.

Why this exists: ui/app.py persists form state via
`QSettings("PDF-Translator", "Document Translator")` (an OS-native store
- Windows registry, macOS plist, or an INI file on Linux, depending on
Qt's backend). webapp/ has no Qt and therefore no QSettings - see this
package's own docstring for why the pilot UI is being rebuilt without
PySide6. This module is a plain, stdlib-only JSON file at the
OS-conventional per-user config location, covering the same PURPOSE
(remember what the user picked last time so they don't have to retype
it) without any Qt dependency.

Deliberately NOT using a third-party config-dir library (e.g.
platformdirs) - three sys.platform branches is little enough code to not
be worth a new dependency, matching image_translate_cli/review_server.py's
own "stdlib only" ethos that the rest of webapp/ follows too.

Field names mirror ui/app.py::_persist_form_state()/_restore_form_state()
where they overlap, minus the PDF/Word-only fields (form.mode,
form.image_mode, form.ico_mode, form.exclude_header, form.exclude_footer)
that don't apply to the images-only pilot this module was built for.
Extending this to the other modes later just means adding more keys to
DEFAULTS - not a structural change.
"""
from __future__ import annotations

import copy
import json
import os
import sys
from pathlib import Path
from typing import Any

APP_NAME = "PDF-Translator"

# Mirrors ui/app.py's own defaults: "provider" (SettingsDialog, line 94),
# "max_chars" (DEFAULT_MAX_CHARS_PER_RUN), "language" (LanguageManager's
# own "de" default), "last_source_dir"/"last_output_dir" (both "" - an
# empty string already means "use the current/home directory" throughout
# ui/app.py's file-dialog calls), and the images-mode subset of
# form.* (target_lang defaults to "DE" exactly like ui/app.py's
# self.target_lang = QLineEdit("DE")).
DEFAULTS: dict[str, Any] = {
    "provider": "deepl",
    "max_chars": 500_000,
    "language": "de",
    "last_source_dir": "",
    "last_output_dir": "",
    "form": {
        "source_lang": "",
        "target_lang": "DE",
        "protected_terms": "",
        "ocr_engine": "tesseract",
        "inpainting_backend": "box_overlay",
    },
}


def config_dir() -> Path:
    """The OS-conventional per-user config directory for this app -
    mirrors what QSettings picks automatically on each platform, but
    computed by hand since webapp/ has no Qt to delegate to.
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or str(Path.home() / "AppData" / "Roaming")
        return Path(base) / APP_NAME
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / APP_NAME
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / "pdf-translator"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def load(path: Path | None = None) -> dict[str, Any]:
    """Reads the settings file, merged over DEFAULTS so a missing key (a
    fresh install, or a file written before a new field existed) never
    raises - the same "always return something usable" contract
    ui/app.py's `settings.value(key, default, type=...)` calls have
    today. A missing or corrupt file quietly falls back to DEFAULTS
    rather than crashing the server on startup.
    """
    target = path or settings_path()
    result = copy.deepcopy(DEFAULTS)
    try:
        raw = json.loads(target.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return result
    if isinstance(raw, dict):
        for key, value in raw.items():
            if key == "form" and isinstance(value, dict):
                result["form"].update(value)
            else:
                result[key] = value
    return result


def save(values: dict[str, Any], path: Path | None = None) -> None:
    """Read-modify-write: merges `values` (may be a partial update, e.g.
    just `{"form": {"target_lang": "FR"}}`) onto whatever is already
    stored, then writes the whole file back. No concurrent-writer
    concern - webapp/ is a single local user, single server process
    (see job_bridge.py's "one job at a time" assumption).
    """
    target = path or settings_path()
    current = load(target)
    for key, value in values.items():
        if key == "form" and isinstance(value, dict):
            current["form"].update(value)
        else:
            current[key] = value
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(current, indent=2, ensure_ascii=False), encoding="utf-8")
