"""Regression guard for wiring the eigenständige Bildübersetzung
(TranslationMode.IMAGES, RoadMap.md Phase 3) into the Qt Start-button flow
(ui/app.py). Mirrors tests/test_ui_word_mode.py's fixtures/conventions -
see that module's docstring for the QThreadPool.start() monkeypatch
rationale (only the worker CLASS/constructor args matter here, never a
real background run).

IMAGES mode differs from the other three in two structural ways this file
specifically checks: (1) TranslationRequest.source_paths may hold several
files at once (every other mode's validation_errors() rejects that), so
_start() must build ONE ImageTranslationWorker for the whole batch rather
than the per-file worker_cls dict lookup the other modes share; (2) it has
its own ocr_engine/inpainting_backend dropdowns (hidden for every other
mode) that must round-trip through TranslationRequest into the worker.
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
from ui.image_job import ImageBatchJobResult, ImageBatchStats
from ui.models import TranslationMode, TranslationRequest
from ui.workers import ImageTranslationWorker


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance() or QApplication([])
    return app


@pytest.fixture()
def no_run_thread_pool(monkeypatch: pytest.MonkeyPatch):
    """See tests/test_ui_word_mode.py's identically-named fixture - same
    QThreadPool.start() interception, duplicated here rather than shared
    via a conftest.py to keep this file's dependency on that one explicit.
    """
    started: list[object] = []
    monkeypatch.setattr(QThreadPool, "start", lambda self, worker: started.append(worker))
    return started


def _image_sources(tmp_path: Path, count: int = 2) -> tuple[Path, ...]:
    # Content doesn't need to be a real, decodable image: analyze_request()
    # only attempts real OCR when ocr_engine_available() is True (see
    # ui/analysis.py), and this dispatch test never lets a worker actually
    # run (see no_run_thread_pool above) - only TranslationRequest.
    # validation_errors()' is_file()/suffix checks need to pass.
    paths = []
    for i in range(count):
        path = tmp_path / f"photo{i}.png"
        path.write_bytes(b"not decoded in this test")
        paths.append(path)
    return tuple(paths)


def _prepare_confirmed_images_run(window: MainWindow, sources: tuple[Path, ...]) -> None:
    window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.IMAGES))
    window.paths = sources
    window.provider.setCurrentText("deepl")
    window.last_result = analyze_request(TranslationRequest(TranslationMode.IMAGES, sources, provider="deepl"))
    window.confirm.setEnabled(True)
    window.confirm.setChecked(True)


def test_images_mode_is_not_blocked_as_unexecutable(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.IMAGES))
        assert window._start_blocked_reason() != "start.blocked_mode"
    finally:
        window.close()


def test_ocr_engine_and_inpainting_rows_only_visible_for_images_mode(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.IMAGES))
        assert window.form.isRowVisible(window.ocr_engine)
        assert window.form.isRowVisible(window.inpainting_backend)

        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.WORD))
        assert not window.form.isRowVisible(window.ocr_engine)
        assert not window.form.isRowVisible(window.inpainting_backend)
    finally:
        window.close()


def test_request_carries_ocr_engine_and_inpainting_backend(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.IMAGES))
        request = window._request()
        assert request.ocr_engine == "tesseract"
        assert request.inpainting_backend == "box_overlay"

        index = window.inpainting_backend.findData("cv_inpainting")
        assert index != -1
        window.inpainting_backend.setCurrentIndex(index)
        assert window._request().inpainting_backend == "cv_inpainting"
    finally:
        window.close()


def test_start_dispatches_one_image_translation_worker_for_the_whole_batch(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    no_run_thread_pool: list[object],
    tmp_path: Path,
) -> None:
    """The Nacheinander/alle-automatisch decision (RoadMap.md Phase 3): a
    multi-file IMAGES selection must dispatch exactly ONE
    ImageTranslationWorker carrying every selected source, not one worker
    per file and not just source_paths[0] (the gap this whole feature
    fixed - see ui/image_job.py::run_image_batch_job()'s docstring).
    """
    monkeypatch.setattr(app_module, "credential_status", lambda provider: "credential.keyring")
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *a, **k: str(tmp_path))
    monkeypatch.setattr(QMessageBox, "question", lambda *a, **k: QMessageBox.Yes)

    window = MainWindow()
    window.show()
    try:
        sources = _image_sources(tmp_path, count=3)
        _prepare_confirmed_images_run(window, sources)

        window._start()

        assert len(no_run_thread_pool) == 1
        worker = no_run_thread_pool[0]
        assert isinstance(worker, ImageTranslationWorker)
        assert worker.sources == list(sources)
        assert worker.output_dir == tmp_path
        assert worker.ocr_engine_name == "tesseract"
        assert worker.inpainting_backend_name == "box_overlay"
    finally:
        window.close()


def test_start_blocks_with_a_warning_when_ocr_engine_unavailable(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    no_run_thread_pool: list[object],
    tmp_path: Path,
) -> None:
    """Fail-fast guard mirroring the missing-credential check just above it
    in _start() - an OCR engine that can't actually run (e.g. Tesseract
    not installed) must stop the run before any output folder is even
    asked for, not fail deep inside run_image_batch_job().
    """
    monkeypatch.setattr(app_module, "credential_status", lambda provider: "credential.keyring")
    monkeypatch.setattr(app_module, "ocr_engine_available", lambda name: False)
    warned: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda self, title, text, *a, **k: warned.append(text) or QMessageBox.Ok
    )
    directory_calls: list[object] = []
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **k: directory_calls.append(1) or str(tmp_path)
    )

    window = MainWindow()
    window.show()
    try:
        sources = _image_sources(tmp_path, count=1)
        _prepare_confirmed_images_run(window, sources)

        window._start()

        assert len(no_run_thread_pool) == 0
        assert not directory_calls
        assert warned
    finally:
        window.close()


def test_inpainting_backend_dropdown_offers_gpu_inpainting(qapp: QApplication) -> None:
    window = MainWindow()
    window.show()
    try:
        assert window.inpainting_backend.findData("gpu_inpainting") != -1
    finally:
        window.close()


def test_inpainting_backend_hint_shown_only_when_selected_backend_unavailable(
    qapp: QApplication, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Mirrors _update_ocr_engine_hint()'s already-tested behaviour, for
    the rewrite-backend dropdown - relevant in practice only for
    "gpu_inpainting" today (Box-Overlay/CvInpaintingBackend are always
    available, see inpainting_backend_available()'s docstring).
    """
    monkeypatch.setattr(app_module, "inpainting_backend_available", lambda name: False)
    window = MainWindow()
    window.show()
    try:
        window.mode.setCurrentIndex(list(TranslationMode).index(TranslationMode.IMAGES))
        index = window.inpainting_backend.findData("gpu_inpainting")
        window.inpainting_backend.setCurrentIndex(index)

        assert window.inpainting_backend_hint.isVisible()

        index = window.inpainting_backend.findData("box_overlay")
        monkeypatch.setattr(app_module, "inpainting_backend_available", lambda name: True)
        window.inpainting_backend.setCurrentIndex(index)

        assert not window.inpainting_backend_hint.isVisible()
    finally:
        window.close()


def test_start_blocks_with_a_warning_when_inpainting_backend_unavailable(
    qapp: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    no_run_thread_pool: list[object],
    tmp_path: Path,
) -> None:
    """Fail-fast guard mirroring test_start_blocks_with_a_warning_when_
    ocr_engine_unavailable() above, for the rewrite-backend choice (e.g.
    "gpu_inpainting" selected without a qualifying CUDA GPU).
    """
    monkeypatch.setattr(app_module, "credential_status", lambda provider: "credential.keyring")
    monkeypatch.setattr(app_module, "inpainting_backend_available", lambda name: False)
    warned: list[str] = []
    monkeypatch.setattr(
        QMessageBox, "warning", lambda self, title, text, *a, **k: warned.append(text) or QMessageBox.Ok
    )
    directory_calls: list[object] = []
    monkeypatch.setattr(
        QFileDialog, "getExistingDirectory", lambda *a, **k: directory_calls.append(1) or str(tmp_path)
    )

    window = MainWindow()
    window.show()
    try:
        sources = _image_sources(tmp_path, count=1)
        # Select the backend BEFORE _prepare_confirmed_images_run(): the
        # combo box's currentIndexChanged handler calls
        # _invalidate_analysis() (see _inpainting_backend_changed()),
        # which would otherwise reset the last_result/confirm state that
        # call just finished setting up.
        index = window.inpainting_backend.findData("gpu_inpainting")
        window.inpainting_backend.setCurrentIndex(index)
        _prepare_confirmed_images_run(window, sources)

        window._start()

        assert len(no_run_thread_pool) == 0
        assert not directory_calls
        assert warned
    finally:
        window.close()


def test_job_progress_wording_is_file_based_for_images_mode(
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
        sources = _image_sources(tmp_path, count=2)
        _prepare_confirmed_images_run(window, sources)

        window._start()

        assert window._job_progress_unit_key == "job.progress_count_files"
        window._job_total(2)
        window._job_stats(ImageBatchStats(translated=1, chars_sent=10, files_processed=1, files_total=2))
        assert "Bild" in window.job_status.text() or "image" in window.job_status.text().lower()
    finally:
        window.close()


def test_show_job_result_for_image_batch_hides_report_button_and_uses_output_dir(
    qapp: QApplication, tmp_path: Path
) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir()
    window = MainWindow()
    window.show()
    try:
        stats = ImageBatchStats(translated=2, chars_sent=20, files_processed=2, files_total=2)
        result = ImageBatchJobResult(output_dir, stats)

        window._job_finished(result)

        assert window.open_folder_button.isVisible()
        assert not window.open_report_button.isVisible()
        assert not window.correct_translation_button.isVisible()
        assert str(output_dir) in window.job_status.text()
    finally:
        window.close()
