"""Guided, laymen-friendly installer for PDF-Translator (the "Bootstrapper").

Separate, standalone tkinter program - deliberately NOT part of the ui/
(PySide6) app and does not import it. Rationale (01.09.2026 project doc
"deployment-strategie-bootstrapper-01-09-2026.md"): a person without the
real app installed yet cannot run a PySide6 program to install PySide6, so
this package only depends on the Python standard library plus the already-
optional 'keyring' package (see pipeline/credentials.py) - both installed
before the real app's requirements.txt is fetched. Every submodule here
must keep that constraint; do not import PySide6, requests, or anything
from ui/ (other than the deliberately Qt-free ui/settings.py and
ui/i18n_data.py) or pipeline/ (other than the deliberately lightweight
pipeline/credentials.py) anywhere in this package.

Entry point: `python -m bootstrap` (see bootstrap/__main__.py) or the
PyInstaller-built executable produced by
.github/workflows/build-bootstrap.yml.
"""
