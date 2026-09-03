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

Keyring isolation (03.09.2026): pipeline/credentials.py falls back to the
OS keyring (Secret Service / Credential Locker / Keychain) whenever no
environment variable is set. On a developer machine where the real app has
stored real credentials there - Michael's, after setting up the Google-
Drive-Ordnersuche - tests that only clear env vars and then expect "not
configured" (tests/test_drive_auth.py) read the REAL stored Client-ID/
project ID and fail with those real values in the assertion output. The
suite was written in a sandbox without any keyring backend, where the
fallback silently returned None. _no_real_keyring below makes every test
behave like that sandbox: _keyring_module() returns None, so only env vars
count. Tests that want a keyring install their own fake by monkeypatching
_keyring_module themselves (tests/test_credentials.py) - a later
monkeypatch.setattr in the test body overrides this fixture's, so nothing
there needs to change.

(webapp/settings_store.py's own isolation - Task #14, 27.08.2026 - lives
as a file-local autouse fixture in tests/test_webapp_jobs_api.py instead
of here: unlike QSettings, tests/test_webapp_settings_store.py's own
test_config_dir_* tests deliberately exercise config_dir()'s real
platform branching, so a suite-wide patch of that one function here would
break exactly the tests meant to verify it.)
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


@pytest.fixture(autouse=True)
def _no_real_keyring(monkeypatch: pytest.MonkeyPatch):
    from pipeline import credentials as credentials_module

    monkeypatch.setattr(credentials_module, "_keyring_module", lambda: None)
    yield
