"""`python -m webapp` - the pywebview app-shell bootstrap (Schritt 6 of
the local-server + pywebview migration, see Backlog.md 26.08.2026 and
/root/.claude/plans/moonlit-humming-brook.md). Starts webapp/server.py's
HTTP server on a background thread (the same create_server() Schritt
2-5 already use) and opens a NATIVE app window pointed at it via
pywebview, instead of the system browser tab webapp/server.py::main()
(Schritt 3's interim entry point) opens.

Why pywebview over the plain browser tab (see the plan's own reasoning
under "Datei-/Ordnerauswahl läuft NICHT über die HTTP-API"): a real
native OS file/folder dialog (create_file_dialog()). The two textfields
in webapp/static/index.html for source images/output folder were an
explicit, documented interim placeholder exactly because a browser's own
`<input type="file">` cannot reveal a real filesystem path for security
reasons - the Api class below is what replaces them, exposed to
webapp/static/app.js as `pywebview.api.pick_images()`/
`pywebview.api.pick_output_dir()` (see that file's own comments on the
pywebview-vs-plain-browser feature detection it does around those two
calls).

GUI backend: explicitly forced to Qt (`gui="qt"` below) via `qtpy` +
the PySide6/QtWebEngine the existing ui/ Qt app already requires - see
requirements.txt's comment. Chosen deliberately over letting pywebview
auto-detect (which tries GTK first on Linux): this pilot needs no NEW
heavy GUI toolkit dependency beyond what Document Translator already
installs, and Qt is the one guaranteed to already be present. Verified
end-to-end under Xvfb with QtWebEngine (window opens, loads the real
server, `window.pywebview.api.*` is callable from the page) - see
Backlog.md's Schritt-6 entry for exactly what was and wasn't possible to
verify headlessly (a real native file dialog needs an actual person
clicking it, same boundary tests/test_ui_images_mode.py already
documents for the Qt app's own dialogs).
"""
from __future__ import annotations

import threading

import webview

from webapp.server import create_server

# Mirrors ui/models.py::MODE_EXTENSIONS[TranslationMode.IMAGES] - kept as
# a literal tuple here rather than importing that dict, since this is a
# pywebview file-type filter string (a different shape entirely), not a
# suffix set; "Alle Dateien" is included as a fallback for a real-world
# file with an unusual or missing extension, matching how ui/app.py's own
# QFileDialog filter for images already includes an "all files" option.
_IMAGE_FILE_TYPES = (
    "Bilder (*.png;*.jpg;*.jpeg;*.webp;*.tif;*.tiff;*.bmp)",
    "Alle Dateien (*.*)",
)


class Api:
    """Exposed to the frontend as `pywebview.api.*`. Every method here
    runs on pywebview's own JS-bridge thread when called from
    JavaScript; a Python list/None return value is JSON-serialized to
    the caller automatically - app.js's pick handlers just `await` the
    call like any other promise.
    """

    def pick_images(self) -> list[str]:
        """Backs the "Bilder auswählen"-Button (dialog.choose_images) -
        a multi-select native open-file dialog. Returns an empty list if
        the user cancels (never None), so app.js can always safely treat
        the result as an array.
        """
        window = webview.active_window()
        if window is None:
            return []
        selection = window.create_file_dialog(
            webview.FileDialog.OPEN, allow_multiple=True, file_types=_IMAGE_FILE_TYPES
        )
        return list(selection) if selection else []

    def pick_output_dir(self) -> str | None:
        """Backs the "Zielordner wählen"-Button (dialog.choose_output_dir) -
        a single-folder native dialog, mirroring
        ui/app.py::_start()'s QFileDialog.getExistingDirectory() call.
        Returns None if the user cancels.
        """
        window = webview.active_window()
        if window is None:
            return None
        selection = window.create_file_dialog(webview.FileDialog.FOLDER)
        return selection[0] if selection else None


def main() -> None:
    httpd = create_server()
    port = httpd.server_address[1]
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    webview.create_window(
        "Document Translator",
        f"http://127.0.0.1:{port}/",
        js_api=Api(),
        width=900,
        height=900,
        min_size=(640, 600),
    )
    try:
        webview.start(gui="qt")
    finally:
        httpd.shutdown()
        httpd.server_close()


if __name__ == "__main__":
    main()
