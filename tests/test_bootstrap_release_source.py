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


# --- self-update (01.09.2026) ------------------------------------------


@pytest.mark.parametrize(
    "version, expected",
    [
        ("v1.2.3", (1, 2, 3)),
        ("1.2.3", (1, 2, 3)),
        ("v0.1.0", (0, 1, 0)),
        ("2.0", (2, 0)),
    ],
)
def test_parse_version_parses_dotted_numeric(version, expected):
    assert release_source.parse_version(version) == expected


@pytest.mark.parametrize("version", ["v1.2.3-beta", "not-a-version", "", "v"])
def test_parse_version_raises_on_non_numeric(version):
    with pytest.raises(ValueError):
        release_source.parse_version(version)


@pytest.mark.parametrize(
    "candidate, current, expected",
    [
        ("v1.1.0", "v1.0.0", True),
        ("v1.0.0", "v1.1.0", False),
        ("v1.0.0", "v1.0.0", False),
        # Numeric comparison, not string comparison - "1.10.0" < "1.9.0" as
        # plain strings but must compare as NEWER numerically.
        ("v1.10.0", "v1.9.0", True),
        ("v1.9.0", "v1.10.0", False),
    ],
)
def test_is_newer_version_numeric_comparison(candidate, current, expected):
    assert release_source.is_newer_version(candidate, current) is expected


def test_is_newer_version_falls_back_to_true_when_unparseable():
    # An unparseable tag must never make the self-update check go silent -
    # see is_newer_version()'s docstring.
    assert release_source.is_newer_version("v1.2.3-beta", "v1.0.0") is True


def test_is_newer_version_equal_unparseable_strings_is_false():
    assert release_source.is_newer_version("nightly", "nightly") is False


def test_check_for_update_returns_none_when_already_latest(monkeypatch):
    monkeypatch.setattr(
        release_source,
        "fetch_latest_release_metadata",
        lambda: {"tag_name": "v1.0.0", "assets": [{"name": "app.zip", "browser_download_url": "https://x/app.zip"}]},
    )
    assert release_source.check_for_update("v1.0.0") is None


def test_check_for_update_returns_none_when_current_is_newer(monkeypatch):
    # Local dev build ahead of the last tagged release, say.
    monkeypatch.setattr(
        release_source,
        "fetch_latest_release_metadata",
        lambda: {"tag_name": "v1.0.0", "assets": [{"name": "app.zip", "browser_download_url": "https://x/app.zip"}]},
    )
    assert release_source.check_for_update("v2.0.0") is None


def test_check_for_update_returns_update_info_when_newer_release_exists(monkeypatch):
    monkeypatch.setattr(
        release_source,
        "fetch_latest_release_metadata",
        lambda: {
            "tag_name": "v1.2.0",
            "body": "Release notes here.",
            "assets": [{"name": "app.zip", "browser_download_url": "https://x/app-1.2.0.zip"}],
        },
    )
    info = release_source.check_for_update("v1.0.0")
    assert info == release_source.UpdateInfo(
        version="v1.2.0", zip_url="https://x/app-1.2.0.zip", release_notes="Release notes here."
    )


def test_check_for_update_propagates_missing_zip_asset(monkeypatch):
    monkeypatch.setattr(
        release_source,
        "fetch_latest_release_metadata",
        lambda: {"tag_name": "v1.2.0", "assets": []},
    )
    with pytest.raises(ReleaseSourceError):
        release_source.check_for_update("v1.0.0")


def test_check_for_update_propagates_network_errors(monkeypatch):
    def fake_fetch():
        raise ReleaseSourceError("no network")

    monkeypatch.setattr(release_source, "fetch_latest_release_metadata", fake_fetch)
    with pytest.raises(ReleaseSourceError):
        release_source.check_for_update("v1.0.0")


def test_download_release_downloads_and_extracts_the_given_zip_url(tmp_path, monkeypatch):
    zip_path = _make_release_zip(tmp_path, wrapped=True)

    def fake_download_to_file(url, dest, progress_cb=None):
        assert url == "https://x/app-1.2.0.zip"
        dest.write_bytes(zip_path.read_bytes())

    monkeypatch.setattr(release_source, "_download_to_file", fake_download_to_file)
    info = release_source.UpdateInfo(version="v1.2.0", zip_url="https://x/app-1.2.0.zip")
    dest = tmp_path / "installed"

    result = release_source.download_release(info, dest)

    assert result == dest
    assert (dest / "requirements.txt").is_file()
    assert (dest / "pipeline" / "__init__.py").is_file()
