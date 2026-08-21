"""Shared pytest fixtures for the whole test suite.

QSettings isolation (Backlog.md 21.08.2026): ui/app.py's MainWindow now
persists its form state and last-used source/output folders (a real user
asked for both, so they don't have to retype every field or re-navigate to
the same folders on every run) via QSettings("PDF-Translator", "Document
Translator") - the OS-native, really-on-disk settings store the real app
uses (an .ini-style file under $HOME/.config on Linux, the registry on
Windows).

Without this fixture, one test FILE's MainWindow.close() calls leak
persisted state into every OTHER test file's fresh MainWindow() within the
same pytest run (and even across separate runs on a real machine, since
that file genuinely persists between process invocations) - not a
hypothetical risk: it produced a real hang/failure in
tests/test_ui_images_mode.py while this feature was being developed,
caused by tests/test_ui_word_mode.py's own window.close() calls (run
first, alphabetically) writing real state into the real settings file.

autouse=True + function scope redirects EVERY
QSettings("PDF-Translator", "Document Translator") construction, in every
test file, to a fresh temp directory for the duration of that one test -
no test ever sees another test's persisted state, and the real
per-machine settings file used by the actual application is never touched
by the test suite at all. QSettings.setPath() must target Format.
NativeFormat specifically (not IniFormat) - ui/app.py's QSettings(org, app)
two-argument constructor defaults to NativeFormat, which on Linux happens
to also be an .ini-style file but is a DIFFERENT Format enum value with
its own, separately-configured path; redirecting only IniFormat (a natural
first guess) silently does nothing for it.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QSettings


@pytest.fixture(autouse=True)
def _isolated_qsettings(tmp_path: Path):
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.UserScope, str(tmp_path))
    QSettings.setPath(QSettings.Format.NativeFormat, QSettings.Scope.SystemScope, str(tmp_path))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, str(tmp_path))
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.SystemScope, str(tmp_path))
    yield
