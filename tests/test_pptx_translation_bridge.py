from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from zipfile import ZipFile

from lxml import html as lxml_html
from lxml import etree

from pipeline.presentation.base import PresentationParagraph, PresentationRun, RunFormatting
from pipeline.presentation.html_bridge import paragraph_to_html, translated_run_texts
from pipeline.presentation.pptx_engine import PptxEngine
from pipeline.presentation.translate_presentation import (
    collect_translatable_html,
    translate_presentation,
)
from pipeline.translation.base import TranslationResult
from pipeline.translation.base import TranslationError


FIXTURE = Path(__file__).parent / "fixtures" / "representative.pptx"


class FakeHtmlProvider:
    def translate_html(
        self, html: str, target_lang: str, source_lang: str | None = None
    ) -> TranslationResult:
        root = lxml_html.fromstring(f"<div>{html}</div>")
        for span in root.iter("span"):
            span.text = (span.text or "") + " [DE]"
        translated = "".join(
            lxml_html.tostring(child, encoding="unicode") for child in root
        )
        return TranslationResult(translated, source_lang or "", target_lang, "fake")


class FailingProvider:
    def translate_html(self, html: str, target_lang: str, source_lang: str | None = None):
        raise TranslationError("credential unavailable")


def test_html_bridge_preserves_run_and_break_identity() -> None:
    engine = PptxEngine()
    engine.open(FIXTURE)
    paragraph = engine.get_text_containers()[0].paragraphs[0]
    original = paragraph_to_html(paragraph)

    assert 'data-run="0"' in original.html
    assert translated_run_texts(original.html, original) == {
        index: run.text for index, run in enumerate(paragraph.runs)
    }


def test_symbol_only_runs_are_preserved_outside_translation_payload() -> None:
    paragraph = PresentationParagraph(
        runs=[
            PresentationRun("Translate me ", RunFormatting()),
            PresentationRun("\uf04a", RunFormatting(properties={"sym_typeface": "Wingdings"})),
        ]
    )
    converted = paragraph_to_html(paragraph)
    assert converted.run_indices == (0,)
    assert "\uf04a" not in converted.html
    assert translated_run_texts(
        '<span data-run="0">Übersetze mich </span>', converted
    ) == {0: "Übersetze mich "}


def test_urls_and_number_only_runs_are_not_sent_for_translation() -> None:
    paragraph = PresentationParagraph(
        runs=[
            PresentationRun("https://example.com/path", RunFormatting()),
            PresentationRun("2026", RunFormatting()),
            PresentationRun("Translate this", RunFormatting()),
        ]
    )
    converted = paragraph_to_html(paragraph)
    assert converted.run_indices == (2,)
    assert "example.com" not in converted.html
    assert "2026" not in converted.html


def test_collect_payloads_supports_upfront_cost_estimation() -> None:
    engine = PptxEngine()
    engine.open(FIXTURE)
    payloads = collect_translatable_html(engine)

    assert len(payloads) == 6
    assert all("data-run" in payload for payload in payloads)


def test_provider_failures_are_reported_with_location() -> None:
    engine = PptxEngine()
    engine.open(FIXTURE)
    stats = translate_presentation(
        engine,
        FailingProvider(),
        [],
        "de",
        "en",
        slide_paths={"ppt/slides/slide1.xml"},
    )
    assert stats.paragraphs_failed == 6
    assert len(stats.errors) == 6
    assert "slide1.xml" in stats.errors[0]
    assert "credential unavailable" in stats.errors[0]


def test_fake_translation_changes_only_text_nodes_and_keeps_protected_term(
    tmp_path: Path,
) -> None:
    engine = PptxEngine()
    engine.open(FIXTURE)
    before = engine.structural_fingerprint()

    stats = translate_presentation(
        engine,
        FakeHtmlProvider(),
        protected_terms=["PPTX-Roundtrip"],
        target_lang="de",
        source_lang="en",
    )

    assert stats.paragraphs_translated == 6
    assert stats.paragraphs_failed == 0
    assert stats.chars_sent > 0
    assert engine.structural_fingerprint() == before
    title = engine.get_text_containers()[0].text
    assert "PPTX-Roundtrip" in title
    assert "[DE]" in title

    output = tmp_path / "translated.pptx"
    engine.save(output)
    reopened = PptxEngine()
    reopened.open(output)
    assert reopened.structural_fingerprint() == before


def test_footer_date_and_slide_number_placeholders_are_never_translated(
    tmp_path: Path,
) -> None:
    """Exercise all three protected placeholder types on slide-local shapes."""
    ns = {
        "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    }
    with ZipFile(FIXTURE) as source:
        entries = [(info, source.read(info.filename)) for info in source.infolist()]
    slide_name = "ppt/slides/slide1.xml"
    slide = etree.fromstring(dict((info.filename, data) for info, data in entries)[slide_name])
    shapes = slide.xpath(".//p:sp", namespaces=ns)
    shape_tree = slide.find(".//p:cSld/p:spTree", ns)
    while len(shapes) < 3:
        clone = deepcopy(shapes[0])
        clone.find("p:nvSpPr/p:cNvPr", ns).set("id", str(90 + len(shapes)))
        shape_tree.append(clone)
        shapes.append(clone)
    for shape, placeholder_type, text in zip(
        shapes[:3],
        ("ftr", "dt", "sldNum"),
        ("Footer bleibt", "8/15/26", "19"),
        strict=True,
    ):
        placeholder = shape.find("p:nvSpPr/p:nvPr/p:ph", ns)
        if placeholder is None:
            placeholder = etree.SubElement(
                shape.find("p:nvSpPr/p:nvPr", ns), f"{{{ns['p']}}}ph"
            )
        placeholder.set("type", placeholder_type)
        shape.find("p:txBody/a:p/a:r/a:t", ns).text = text
    replacement = etree.tostring(slide, xml_declaration=True, encoding="UTF-8")
    protected_fixture = tmp_path / "protected-placeholders.pptx"
    with ZipFile(protected_fixture, "w") as output:
        for info, data in entries:
            output.writestr(info, replacement if info.filename == slide_name else data)

    engine = PptxEngine()
    engine.open(protected_fixture)
    protected = [container for container in engine.get_text_containers() if not container.translatable]
    assert {container.placeholder_type for container in protected} == {"ftr", "dt", "sldNum"}
    before = {container.placeholder_type: container.text for container in protected}

    translate_presentation(engine, FakeHtmlProvider(), [], "de", "en")
    after = {
        container.placeholder_type: container.text
        for container in engine.get_text_containers()
        if not container.translatable
    }
    assert after == before
