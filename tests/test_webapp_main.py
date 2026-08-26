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

import pytest
import webview

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
