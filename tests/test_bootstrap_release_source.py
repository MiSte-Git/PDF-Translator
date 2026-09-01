"""Tests for bootstrap/release_source.py."""
from __future__ import annotations

import zipfile

import pytest

from bootstrap import release_source
from bootstrap.release_source import ReleaseSourceError


def test_resolve_zip_asset_url_finds_zip_asset():
    metadata = {
        "assets": [
            {"name": "checksums.txt", "browser_download_url": "https://example/checksums.txt"},
            {"name": "TranslatePDF-1.2.3.zip", "browser_download_url": "https://example/app.zip"},
        ]
    }
    assert release_source.resolve_zip_asset_url(metadata) == "https://example/app.zip"


def test_resolve_zip_asset_url_raises_without_zip_asset():
    with pytest.raises(ReleaseSourceError):
        release_source.resolve_zip_asset_url({"assets": []})


def _make_release_zip(tmp_path, wrapped: bool) -> "Path":
    zip_path = tmp_path / "release.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        prefix = "TranslatePDF-1.2.3/" if wrapped else ""
        zf.writestr(f"{prefix}requirements.txt", "PyMuPDF\n")
        zf.writestr(f"{prefix}pipeline/__init__.py", "")
        zf.writestr(f"{prefix}ui/app.py", "# app\n")
    return zip_path


def test_extract_zip_flattened_unwraps_single_top_level_dir(tmp_path):
    zip_path = _make_release_zip(tmp_path, wrapped=True)
    dest = tmp_path / "extracted"
    release_source._extract_zip_flattened(zip_path, dest)
    assert (dest / "requirements.txt").is_file()
    assert (dest / "pipeline" / "__init__.py").is_file()
    assert (dest / "ui" / "app.py").is_file()
    # No leftover wrapper directory.
    assert not (dest / "TranslatePDF-1.2.3").exists()


def test_extract_zip_flattened_without_wrapper(tmp_path):
    zip_path = _make_release_zip(tmp_path, wrapped=False)
    dest = tmp_path / "extracted"
    release_source._extract_zip_flattened(zip_path, dest)
    assert (dest / "requirements.txt").is_file()


def test_download_app_source_uses_dev_directory_override(tmp_path):
    source = tmp_path / "dev-source"
    (source / "pipeline").mkdir(parents=True)
    (source / "pipeline" / "__init__.py").write_text("")
    (source / "requirements.txt").write_text("PyMuPDF\n")

    dest = tmp_path / "installed"
    result = release_source.download_app_source(dest, dev_source_override=str(source))
    assert result == dest
    assert (dest / "requirements.txt").is_file()
    assert (dest / "pipeline" / "__init__.py").is_file()


def test_download_app_source_uses_dev_zip_override(tmp_path):
    zip_path = _make_release_zip(tmp_path, wrapped=True)
    dest = tmp_path / "installed"
    release_source.download_app_source(dest, dev_source_override=str(zip_path))
    assert (dest / "requirements.txt").is_file()


def test_download_app_source_rejects_invalid_override(tmp_path):
    bogus = tmp_path / "not-a-real-thing.txt"
    bogus.write_text("nope")
    with pytest.raises(ReleaseSourceError):
        release_source.download_app_source(tmp_path / "dest", dev_source_override=str(bogus))


def test_download_app_source_reads_env_var_when_override_not_passed(tmp_path, monkeypatch):
    source = tmp_path / "dev-source"
    source.mkdir()
    (source / "marker.txt").write_text("x")
    monkeypatch.setenv(release_source.DEV_SOURCE_ENV_VAR, str(source))
    dest = tmp_path / "installed"
    release_source.download_app_source(dest)
    assert (dest / "marker.txt").is_file()


def test_fetch_latest_release_metadata_wraps_network_errors(monkeypatch):
    import urllib.error

    def fake_urlopen(*args, **kwargs):
        raise urllib.error.URLError("no network")

    monkeypatch.setattr(release_source.urllib.request, "urlopen", fake_urlopen)
    with pytest.raises(ReleaseSourceError):
        release_source.fetch_latest_release_metadata()
