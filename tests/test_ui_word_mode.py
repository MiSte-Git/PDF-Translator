"""Regression guard for wiring DOCX and PDF into the shared UI job flow
(RoadMap.md Phase 2/Word and Phase 2/PDF): MainWindow._start() must
dispatch to WordTranslationWorker for Word mode, PdfTranslationWorker for
PDF mode, and keep dispatching to PresentationTranslationWorker for
Presentation mode - all three share the same _EXECUTABLE_MODES/_start()
code path (see ui/app.py), so a mistake there could easily route one
mode's job through another's worker.

QThreadPool.start() is monkeypatched to just record the worker instead of
actually running it: the real worker would hit a real (probably
unconfigured, in this sandbox) provider on a background thread, which is
slow, network-dependent, and irrelevant to what this test checks - only
which worker CLASS ui/app.py chose to construct.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QThreadPool
from PySide6.QtWidgets import QApplication, QFileDialog, QMessageBox

import ui.app as app_module
from ui.analysis import analyze_request
from ui.app import MainWindow
from ui.models import TranslationMode, TranslationRequest
from ui.workers import PdfTranslationWorker, PresentationTranslationWorker, WordTranslationWorker

PPTX_FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"
DOCX_FIXTURE = Path(__file__).parent / "fixtures" / "representative.docx"
PDF_FIXTURE = Path(__file__).parent / "fixtures" / "representative.pdf"


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture()
def no_run_thread_pool(monkeypatch: pytest.MonkeyPatch):
    """Intercepts QThreadPool.start() to capture the worker without ever
    calling worker.run() - see module docstring.
    """
    started: list[object] = []
    monkeypatch.setattr(QThreadPool, "start", lambda self, worker: started.append(worker))
    return started


def _prepare_confirmed_run(window: MainWindow, mode: TranslationMode, fixture: Path, tmp_path: Path) -> None:
    window.mode.setCurrentIndex(list(TranslationMode).index(mode))
    window.paths = (fixture,)
    window.provider.setCurrentText("deepl")
    window.last_result = analyze_request(TranslationRequest(mode, (fixture,), provider="deepl"))
    window.confirm.setEnabled(True)
    window.confirm.setChecked(True)


@pytest.mark.parametrize(
    ("mode", "fixture", "expected_worker_cls"),
    [
        (TranslationMode.WORD, DOCX_FIXTURE, WordTranslationWorker),
        (TranslationMode.PRESENTATION, PPTX_FIXTURE, PresentationTranslationWorker),
        (TranslationMode.PDF, PDF_FIXTURE, PdfTranslationWorker),
    ],
)
def test_start_dispatches_the_matching_worker_class(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    no_run_thread_pool: list[object],
    tmp_path: Path,
    mode: TranslationMode,
    fixture: Path,
    expected_worker_cls: type,
) -> None:
    monkeypatch.setattr(app_module, "credential_status", lambda provider: "credential.keyring")
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    window = MainWindow()
    window.show()
    try:
        _prepare_confirmed_run(window, mode, fixture, tmp_path)

        window._start()

        assert len(no_run_thread_pool) == 1
        assert isinstance(no_run_thread_pool[0], expected_worker_cls)
    finally:
        window.close()


def test_word_mode_is_no_longer_blocked_as_unexecutable(qapp: QApplication) -> None:
    """Before DOCX was wired up, _start_blocked_reason() returned
    "start.blocked_mode" for Word regardless of analysis/confirmation state
    - confirms that's no longer the case now that Word is executable.
    """
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.WORD))
        assert window._start_blocked_reason() != "start.blocked_mode"
    finally:
        window.close()


def test_pdf_mode_is_no_longer_blocked_as_unexecutable(qapp: QApplication) -> None:
    """Same regression guard as test_word_mode_is_no_longer_blocked_as_
    unexecutable() above, for PDF (RoadMap.md Phase 2/PDF) - PDF was the
    last remaining mode still hitting "start.blocked_mode" unconditionally.
    """
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.PDF))
        assert window._start_blocked_reason() != "start.blocked_mode"
    finally:
        window.close()


def test_ico_mode_checkbox_only_visible_and_active_for_word_mode(qapp: QApplication) -> None:
    """Regression guard for the "ICO document" special case (RoadMap.md):
    the checkbox must be Word-only (no PDF/PPTX equivalent exists yet) and
    must never carry a stale checked state into a mode that ignores it -
    see MainWindow._mode_changed().
    """
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.WORD))
        assert window.form.isRowVisible(window.ico_mode)
        window.ico_mode.setChecked(True)

        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.PRESENTATION))
        assert not window.form.isRowVisible(window.ico_mode)
        assert not window.ico_mode.isChecked()
    finally:
        window.close()


def test_request_carries_ico_mode_flag(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.WORD))
        window.ico_mode.setChecked(True)
        assert window._request().ico_mode is True

        window.ico_mode.setChecked(False)
        assert window._request().ico_mode is False
    finally:
        window.close()


def test_word_worker_receives_ico_mode_from_request(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    no_run_thread_pool: list[object],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(app_module, "credential_status", lambda provider: "credential.keyring")
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    window = MainWindow()
    window.show()
    try:
        _prepare_confirmed_run(window, TranslationMode.WORD, DOCX_FIXTURE, tmp_path)
        window.ico_mode.setChecked(True)

        window._start()

        assert len(no_run_thread_pool) == 1
        assert no_run_thread_pool[0].ico_mode is True
    finally:
        window.close()


def test_exclude_header_footer_checkboxes_only_visible_and_active_for_pdf_mode(
    qapp: QApplication,
) -> None:
    """Regression guard for the "Header/Footer ausschließen" checkboxes
    (RoadMap.md Phase 2/PDF, added after a live user run against a real
    document had its header translated along with the body - see
    pipeline/pdf/template.py's detect_header_footer_zones()): both must be
    PDF-only (mirroring ico_mode's Word-only pattern above) and must never
    carry a stale checked state into a mode that ignores them - see
    MainWindow._mode_changed().
    """
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.PDF))
        assert window.form.isRowVisible(window.exclude_header)
        assert window.form.isRowVisible(window.exclude_footer)
        window.exclude_header.setChecked(True)
        window.exclude_footer.setChecked(True)

        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.PRESENTATION))
        assert not window.form.isRowVisible(window.exclude_header)
        assert not window.form.isRowVisible(window.exclude_footer)
        assert not window.exclude_header.isChecked()
        assert not window.exclude_footer.isChecked()
    finally:
        window.close()


def test_request_carries_exclude_header_footer_flags(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.PDF))

        window.exclude_header.setChecked(True)
        window.exclude_footer.setChecked(False)
        request = window._request()
        assert request.exclude_header is True
        assert request.exclude_footer is False

        window.exclude_header.setChecked(False)
        window.exclude_footer.setChecked(True)
        request = window._request()
        assert request.exclude_header is False
        assert request.exclude_footer is True
    finally:
        window.close()


def test_pdf_worker_receives_exclude_header_footer_from_request(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    no_run_thread_pool: list[object],
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(app_module, "credential_status", lambda provider: "credential.keyring")
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    window = MainWindow()
    window.show()
    try:
        _prepare_confirmed_run(window, TranslationMode.PDF, PDF_FIXTURE, tmp_path)
        window.exclude_header.setChecked(True)
        window.exclude_footer.setChecked(True)

        window._start()

        assert len(no_run_thread_pool) == 1
        assert no_run_thread_pool[0].exclude_header is True
        assert no_run_thread_pool[0].exclude_footer is True
    finally:
        window.close()
