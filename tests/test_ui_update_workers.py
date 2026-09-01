"""Tests for ui/workers.py's self-update workers (01.09.2026, Michael:
"Update sollte die App selbst prüfen.") - UpdateCheckWorker/
UpdateApplyWorker.

Both are QRunnable, so `.run()` is called directly here (synchronously, on
the test's own thread) rather than via QThreadPool - exactly what
QThreadPool.start() would eventually do on a worker thread, just without
the extra thread for a unit test. Signal connections are plain Python
callables appended to a list; PySide6 delivers a same-thread `emit()`
straight to connected slots with no event loop needed, so this needs no
QApplication instance.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from bootstrap.release_source import ReleaseSourceError, UpdateInfo
from ui import workers


def test_update_check_worker_emits_finished_with_none_when_no_update(monkeypatch):
    monkeypatch.setattr(workers.release_source, "check_for_update", lambda current: None)
    worker = workers.UpdateCheckWorker("v1.0.0")
    results = []
    worker.signals.finished.connect(lambda info: results.append(info))
    worker.signals.failed.connect(lambda msg: pytest.fail(f"unexpected failed signal: {msg}"))

    worker.run()

    assert results == [None]


def test_update_check_worker_emits_finished_with_update_info(monkeypatch):
    info = UpdateInfo(version="v1.2.0", zip_url="https://x/app.zip")
    monkeypatch.setattr(workers.release_source, "check_for_update", lambda current: info)
    worker = workers.UpdateCheckWorker("v1.0.0")
    results = []
    worker.signals.finished.connect(lambda i: results.append(i))

    worker.run()

    assert results == [info]


def test_update_check_worker_swallows_release_source_error_into_failed(monkeypatch):
    def fake_check(current):
        raise ReleaseSourceError("no network")

    monkeypatch.setattr(workers.release_source, "check_for_update", fake_check)
    worker = workers.UpdateCheckWorker("v1.0.0")
    finished_calls = []
    failed_calls = []
    worker.signals.finished.connect(lambda info: finished_calls.append(info))
    worker.signals.failed.connect(lambda msg: failed_calls.append(msg))

    worker.run()

    assert finished_calls == []
    assert len(failed_calls) == 1
    assert "no network" in failed_calls[0]


def test_update_apply_worker_downloads_into_app_source_dir_and_reinstalls_base_requirements(
    tmp_path, monkeypatch
):
    app_source_dir = tmp_path / "app"
    monkeypatch.setattr(workers.bootstrap_paths, "app_source_dir", lambda: app_source_dir)

    downloaded_to = []

    def fake_download_release(info, dest_dir, progress_cb=None):
        downloaded_to.append(dest_dir)
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "requirements.txt").write_text("PyMuPDF\n")
        (dest_dir / "requirements-ocr.txt").write_text("pytesseract\n")
        # No requirements-gpu.txt in this release - must not be an error.
        return dest_dir

    monkeypatch.setattr(workers.release_source, "download_release", fake_download_release)
    # No real torch in this test environment - requirements-gpu.txt (which
    # doesn't exist here anyway) must be skipped, not attempted.
    monkeypatch.setattr(workers.importlib.util, "find_spec", lambda name: None)

    installed = []
    monkeypatch.setattr(workers, "pip_install", lambda venv_python, requirements_file: installed.append(requirements_file))

    info = UpdateInfo(version="v1.2.0", zip_url="https://x/app.zip")
    worker = workers.UpdateApplyWorker(info)
    finished_calls = []
    worker.signals.finished.connect(lambda: finished_calls.append(True))
    worker.signals.failed.connect(lambda msg: pytest.fail(f"unexpected failed signal: {msg}"))

    worker.run()

    assert downloaded_to == [app_source_dir]
    assert installed == [app_source_dir / "requirements.txt", app_source_dir / "requirements-ocr.txt"]
    assert finished_calls == [True]


def test_update_apply_worker_reinstalls_gpu_requirements_only_if_torch_already_present(tmp_path, monkeypatch):
    app_source_dir = tmp_path / "app"
    monkeypatch.setattr(workers.bootstrap_paths, "app_source_dir", lambda: app_source_dir)

    def fake_download_release(info, dest_dir, progress_cb=None):
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "requirements.txt").write_text("PyMuPDF\n")
        (dest_dir / "requirements-gpu.txt").write_text("torch\n")
        return dest_dir

    monkeypatch.setattr(workers.release_source, "download_release", fake_download_release)
    # Simulate a LOCAL-mode install: torch is already importable here.
    monkeypatch.setattr(workers.importlib.util, "find_spec", lambda name: object() if name == "torch" else None)

    installed = []
    monkeypatch.setattr(workers, "pip_install", lambda venv_python, requirements_file: installed.append(requirements_file.name))

    worker = workers.UpdateApplyWorker(UpdateInfo(version="v1.2.0", zip_url="https://x/app.zip"))
    worker.run()

    assert "requirements-gpu.txt" in installed


def test_update_apply_worker_emits_failed_on_download_error(tmp_path, monkeypatch):
    app_source_dir = tmp_path / "app"
    monkeypatch.setattr(workers.bootstrap_paths, "app_source_dir", lambda: app_source_dir)

    def fake_download_release(info, dest_dir, progress_cb=None):
        raise ReleaseSourceError("download failed")

    monkeypatch.setattr(workers.release_source, "download_release", fake_download_release)

    worker = workers.UpdateApplyWorker(UpdateInfo(version="v1.2.0", zip_url="https://x/app.zip"))
    finished_calls = []
    failed_calls = []
    worker.signals.finished.connect(lambda: finished_calls.append(True))
    worker.signals.failed.connect(lambda msg: failed_calls.append(msg))

    worker.run()

    assert finished_calls == []
    assert len(failed_calls) == 1
    assert "download failed" in failed_calls[0]


def test_update_apply_worker_emits_failed_on_pip_install_error(tmp_path, monkeypatch):
    app_source_dir = tmp_path / "app"
    monkeypatch.setattr(workers.bootstrap_paths, "app_source_dir", lambda: app_source_dir)

    def fake_download_release(info, dest_dir, progress_cb=None):
        dest_dir.mkdir(parents=True, exist_ok=True)
        (dest_dir / "requirements.txt").write_text("PyMuPDF\n")
        return dest_dir

    monkeypatch.setattr(workers.release_source, "download_release", fake_download_release)
    monkeypatch.setattr(workers.importlib.util, "find_spec", lambda name: None)

    from bootstrap.installer import InstallError

    def fake_pip_install(venv_python, requirements_file):
        raise InstallError("pip failed")

    monkeypatch.setattr(workers, "pip_install", fake_pip_install)

    worker = workers.UpdateApplyWorker(UpdateInfo(version="v1.2.0", zip_url="https://x/app.zip"))
    failed_calls = []
    worker.signals.failed.connect(lambda msg: failed_calls.append(msg))

    worker.run()

    assert len(failed_calls) == 1
    assert "pip failed" in failed_calls[0]
