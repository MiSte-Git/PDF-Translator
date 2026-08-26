"""Coverage for webapp/__main__.py's Api class (Schritt 6 of the local-
server + pywebview migration, see Backlog.md 26.08.2026) - the pywebview
JS-API bridge that replaces webapp/static/index.html's two interim
textfields (source images, output folder) with real native OS dialogs.

Deliberately does NOT open a real pywebview window or need a display:
Api.pick_images()/pick_output_dir() only ever call
webview.active_window().create_file_dialog() - monkeypatching
webview.active_window() to return a small fake window object exercises
Api's own logic (argument shape, None/cancel handling, no-window
fallback) without any GUI toolkit involved. A real native dialog still
needs an actual person clicking it - verified once by hand under Xvfb
with QtWebEngine while building this step (window opens, loads the real
server, window.pywebview.api.pick_images/pick_output_dir are callable
from the page) - the same "automated up to the OS dialog boundary, then
verified manually" split tests/test_ui_images_mode.py already documents
for the Qt app's own file dialogs.
"""
from __future__ import annotations

from pathlib import Path

import pytest
import webview

import webapp.__main__ as main_module
from webapp.__main__ import Api, _IMAGE_FILE_TYPES


class _FakeWindow:
    def __init__(self, return_value):
        self.return_value = return_value
        self.calls: list[tuple] = []

    def create_file_dialog(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.return_value


def test_pick_images_returns_selected_paths(monkeypatch: pytest.MonkeyPatch) -> None:
    window = _FakeWindow(("/tmp/a.png", "/tmp/b.png"))
    monkeypatch.setattr(webview, "active_window", lambda: window)

    result = Api().pick_images()

    assert result == ["/tmp/a.png", "/tmp/b.png"]
    (args, kwargs) = window.calls[0]
    assert args[0] == webview.FileDialog.OPEN
    assert kwargs["allow_multiple"] is True
    assert kwargs["file_types"] == _IMAGE_FILE_TYPES


def test_pick_images_returns_empty_list_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webview, "active_window", lambda: _FakeWindow(None))
    assert Api().pick_images() == []


def test_pick_images_returns_empty_list_without_an_active_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webview, "active_window", lambda: None)
    assert Api().pick_images() == []


def test_pick_output_dir_returns_the_selected_folder(monkeypatch: pytest.MonkeyPatch) -> None:
    window = _FakeWindow(("/tmp/out",))
    monkeypatch.setattr(webview, "active_window", lambda: window)

    result = Api().pick_output_dir()

    assert result == "/tmp/out"
    (args, kwargs) = window.calls[0]
    assert args[0] == webview.FileDialog.FOLDER


def test_pick_output_dir_returns_none_when_cancelled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webview, "active_window", lambda: _FakeWindow(None))
    assert Api().pick_output_dir() is None


def test_pick_output_dir_returns_none_without_an_active_window(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(webview, "active_window", lambda: None)
    assert Api().pick_output_dir() is None


def test_open_folder_launches_the_platform_opener_on_linux(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """Real user feedback (26.08.2026): "Es fehlt auch noch ein Button um
    den Zielordner ... zu öffnen." - Api.open_folder() shells out to the
    platform's own file-manager opener (pywebview has no built-in "reveal
    this existing folder" call, only create_file_dialog()). `tmp_path` is
    a REAL directory - is_dir() is exercised for real, only the actual
    process launch is faked.
    """
    monkeypatch.setattr(main_module.platform, "system", lambda: "Linux")
    calls = []
    monkeypatch.setattr(main_module.subprocess, "Popen", lambda args: calls.append(args))

    result = Api().open_folder(str(tmp_path))

    assert result is True
    assert calls == [["xdg-open", str(tmp_path)]]


def test_open_folder_launches_the_platform_opener_on_macos(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module.platform, "system", lambda: "Darwin")
    calls = []
    monkeypatch.setattr(main_module.subprocess, "Popen", lambda args: calls.append(args))

    result = Api().open_folder(str(tmp_path))

    assert result is True
    assert calls == [["open", str(tmp_path)]]


def test_open_folder_launches_the_platform_opener_on_windows(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main_module.platform, "system", lambda: "Windows")
    calls = []
    monkeypatch.setattr(main_module.os, "startfile", lambda path: calls.append(path), raising=False)

    result = Api().open_folder(str(tmp_path))

    assert result is True
    assert calls == [str(tmp_path)]


def test_open_folder_returns_false_for_a_path_that_is_not_a_directory(tmp_path: Path) -> None:
    missing = tmp_path / "does-not-exist"
    assert Api().open_folder(str(missing)) is False

    a_file = tmp_path / "photo.png"
    a_file.write_bytes(b"")
    assert Api().open_folder(str(a_file)) is False


def test_open_folder_returns_false_when_the_launch_itself_fails(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(main_module.platform, "system", lambda: "Linux")

    def _raise(args):
        raise OSError("xdg-open not found")

    monkeypatch.setattr(main_module.subprocess, "Popen", _raise)

    assert Api().open_folder(str(tmp_path)) is False


def test_main_wires_the_server_and_window_together_without_blocking(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exercises main() itself without ever calling the real, blocking
    webview.start() - both webview.create_window() and webview.start()
    are monkeypatched to fakes that just record their arguments, so this
    stays a fast, headless test instead of needing a real window."""
    import webapp.__main__ as main_module

    create_window_calls = []
    start_calls = []

    def fake_create_window(title, url, **kwargs):
        assert title == "Document Translator"
        assert url.startswith("http://127.0.0.1:")
        assert isinstance(kwargs["js_api"], Api)
        create_window_calls.append((title, url, kwargs))

    def fake_start(**kwargs):
        assert kwargs.get("gui") == "qt"
        start_calls.append(kwargs)

    monkeypatch.setattr(main_module.webview, "create_window", fake_create_window)
    monkeypatch.setattr(main_module.webview, "start", fake_start)

    main_module.main()

    assert len(create_window_calls) == 1
    assert len(start_calls) == 1
