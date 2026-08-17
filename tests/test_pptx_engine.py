from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
from pathlib import Path
from zipfile import ZipFile

import pytest

from pipeline.presentation.pptx_engine import PptxEngine


FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _render_first_slide(pptx: Path, output_dir: Path) -> bytes:
    """Render through LibreOffice/Poppler for visual roundtrip checks."""
    completed = subprocess.run(
        [
            shutil.which("libreoffice") or "libreoffice",
            "--headless",
            "--convert-to",
            "pdf",
            "--outdir",
            str(output_dir),
            str(pptx),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert completed.returncode == 0
    pdf_path = output_dir / f"{pptx.stem}.pdf"
    raster_prefix = output_dir / "slide"
    subprocess.run(
        [
            shutil.which("pdftoppm") or "pdftoppm",
            "-f",
            "1",
            "-singlefile",
            "-r",
            "144",
            str(pdf_path),
            str(raster_prefix),
        ],
        check=True,
        capture_output=True,
        timeout=60,
    )
    return raster_prefix.with_suffix(".ppm").read_bytes()


def test_extracts_supported_text_containers_and_complete_run_inventory() -> None:
    engine = PptxEngine()
    engine.open(FIXTURE)

    containers = engine.get_text_containers()
    kinds = [container.kind for container in containers]
    assert kinds.count("placeholder") == 1
    assert kinds.count("text_box") == 1
    assert kinds.count("table_cell") == 4

    title = next(container for container in containers if container.kind == "placeholder")
    assert title.placeholder_type == "title"
    assert title.rotation == 420000
    assert title.x == 685800
    assert title.width == 7239000
    assert title.paragraphs[0].runs[0].formatting.properties["sz"] == "3300"
    assert title.paragraphs[0].runs[0].formatting.properties["b"] == "1"
    assert "<a:rPr" in title.paragraphs[0].runs[0].formatting.raw_rpr_xml

    grouped = next(container for container in containers if container.shape_name == "Body Text")
    assert grouped.group_path == ("20:Fixture Group",)
    assert grouped.paragraphs[0].runs[0].formatting.properties["i"] == "1"
    assert grouped.paragraphs[0].runs[0].formatting.properties["color_value"] == "333333"

    table_cells = [container for container in containers if container.kind == "table_cell"]
    assert [cell.table_cell for cell in table_cells] == [(0, 0), (0, 1), (1, 0), (1, 1)]
    assert [cell.text for cell in table_cells] == ["Bereich", "Status", "Tabelle", "Erfasst"]


def test_noop_roundtrip_is_byte_identical_and_source_is_untouched(tmp_path: Path) -> None:
    source_hash = _sha256(FIXTURE)
    output = tmp_path / "roundtrip.pptx"

    engine = PptxEngine()
    engine.open(FIXTURE)
    engine.save(output)

    assert _sha256(FIXTURE) == source_hash
    assert output.read_bytes() == FIXTURE.read_bytes()
    with ZipFile(output) as archive:
        assert archive.testzip() is None


def test_refuses_source_overwrite_and_existing_destination(tmp_path: Path) -> None:
    source = tmp_path / "source.pptx"
    shutil.copyfile(FIXTURE, source)
    engine = PptxEngine()
    engine.open(source)

    with pytest.raises(ValueError, match="overwrite"):
        engine.save(source)

    destination = tmp_path / "existing.pptx"
    destination.write_bytes(b"occupied")
    with pytest.raises(FileExistsError):
        engine.save(destination)


def test_writeback_changes_text_only_and_preserves_structure(tmp_path: Path) -> None:
    engine = PptxEngine()
    engine.open(FIXTURE)
    before = engine.structural_fingerprint()
    title = next(
        container for container in engine.get_text_containers() if container.kind == "placeholder"
    )
    run = title.paragraphs[0].runs[0]
    engine.set_run_text(run, "Geänderter Titel")

    output = tmp_path / "edited.pptx"
    engine.save(output)
    reopened = PptxEngine()
    reopened.open(output)

    assert reopened.structural_fingerprint() == before
    assert next(
        container for container in reopened.get_text_containers() if container.kind == "placeholder"
    ).text == "Geänderter Titel"

    with ZipFile(FIXTURE) as source_zip, ZipFile(output) as output_zip:
        source_names = source_zip.namelist()
        assert output_zip.namelist() == source_names
        for name in source_names:
            if name != "ppt/slides/slide1.xml":
                assert output_zip.read(name) == source_zip.read(name), name


def test_overflow_is_reported_without_mutating_layout() -> None:
    engine = PptxEngine()
    engine.open(FIXTURE)
    before = engine.structural_fingerprint()
    title = next(
        container for container in engine.get_text_containers() if container.kind == "placeholder"
    )
    engine.set_run_text(title.paragraphs[0].runs[0], "Sehr langer Text " * 100)

    findings = engine.detect_text_overflow()
    assert any(finding.shape_id == title.shape_id for finding in findings)
    assert engine.structural_fingerprint() == before
    assert title.width == 7239000
    assert title.rotation == 420000


def test_overflow_comparison_reports_only_new_or_worse_findings() -> None:
    baseline = PptxEngine()
    baseline.open(FIXTURE)
    translated = PptxEngine()
    translated.open(FIXTURE)
    title = next(
        container
        for container in translated.get_text_containers()
        if container.kind == "placeholder"
    )
    translated.set_run_text(title.paragraphs[0].runs[0], "Sehr langer Text " * 100)

    regressions = translated.compare_overflow(baseline)
    assert len(regressions) == 1
    assert regressions[0].shape_id == title.shape_id
    assert regressions[0].reason == "new_fit_risk"


def test_capability_catalog_explicitly_classifies_initial_scope() -> None:
    catalog = PptxEngine().capability_catalog()
    assert catalog["normal_text_boxes"] == "supported"
    assert catalog["tables"] == "supported"
    assert catalog["grouped_shapes"] == "supported recursively"
    for unsupported in (
        "smartart",
        "chart_text",
        "speaker_notes",
        "embedded_objects",
        "text_in_images",
    ):
        assert catalog[unsupported].startswith("not supported")


@pytest.mark.skipif(
    os.environ.get("RUN_PPTX_VISUAL_TESTS") != "1"
    or shutil.which("libreoffice") is None
    or shutil.which("pdftoppm") is None,
    reason="set RUN_PPTX_VISUAL_TESTS=1 with LibreOffice/Poppler available",
)
def test_noop_roundtrip_renders_pixel_identically(tmp_path: Path) -> None:
    output = tmp_path / "visual-roundtrip.pptx"
    engine = PptxEngine()
    engine.open(FIXTURE)
    engine.save(output)

    source_render_dir = tmp_path / "source-render"
    output_render_dir = tmp_path / "output-render"
    source_render_dir.mkdir()
    output_render_dir.mkdir()
    assert _render_first_slide(FIXTURE, source_render_dir) == _render_first_slide(
        output, output_render_dir
    )


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__]))
