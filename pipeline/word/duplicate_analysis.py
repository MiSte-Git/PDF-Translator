"""Comparison/pre-sorting data for an UnresolvedDuplicateError group from
pipeline/word/source_selection.py - metadata + a pairwise text-similarity
score per candidate, and a rough heuristic classification built on top of
that data. Nothing here decides anything: classify_group() is a pre-sort
for a human to confirm, not an input to resolve_source_document() (which
this module doesn't touch).

No existing similarity metric was found elsewhere in the project (checked
for a "compare_pairs.ps1" and any difflib/SequenceMatcher use - neither
exists), so this uses difflib.SequenceMatcher directly, as suggested.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from difflib import SequenceMatcher
from pathlib import Path

from pipeline.word.base import BREAK_MARKER, WordParagraph
from pipeline.word.docx_engine import DocxEngine

# classify_group() thresholds for difflib.SequenceMatcher.ratio() (0..1).
# Deliberately coarse/conservative - see classify_group()'s docstring for
# why "uneindeutig" is the fallback rather than a forced guess.
_LOW_SIMILARITY_THRESHOLD = 0.5
_HIGH_SIMILARITY_THRESHOLD = 0.9

_DEVELOPER_RE = re.compile(r"Developer:\s*(.*?)(?=QSI ICO:|$)", re.IGNORECASE)
_ICO_RE = re.compile(r"QSI ICO:\s*(.*)$", re.IGNORECASE)
_DATE_RE = re.compile(r"^[A-Za-z]+ \d{1,2},\s*\d{4}$")


@dataclass
class CandidateInfo:
    """Per-document metadata for one candidate in a duplicate group."""
    path: Path
    developer_name: str | None
    ico_name: str | None
    domain: str | None
    date: str | None
    paragraph_count: int
    file_size: int
    modified_time: datetime
    error: str | None = None
    """Set instead of the fields above if this candidate couldn't be
    opened/parsed (e.g. an unexpected .docx structure) - analysis
    continues for the rest of the group rather than aborting."""


@dataclass
class GroupAnalysis:
    """analyze_candidate_group()'s result: per-candidate metadata plus a
    pairwise text-similarity score for every candidate pair.
    """
    candidates: list[CandidateInfo]
    similarity: dict[tuple[int, int], float] = field(default_factory=dict)
    """(i, j) with i < j, indices into `candidates` -> SequenceMatcher
    ratio (0..1) between their translatable body text. Missing a pair if
    either candidate failed to open (see CandidateInfo.error)."""


def _paragraph_texts(paragraphs: list[WordParagraph]) -> list[str]:
    """One flattened, BREAK_MARKER-stripped text string per paragraph."""
    return [
        "".join(run.text for run in paragraph.runs).replace(BREAK_MARKER, " ").strip()
        for paragraph in paragraphs
    ]


def _find_labeled(texts: list[str], label: str) -> str | None:
    """First paragraph text starting with `label` (case-insensitive),
    label stripped - e.g. _find_labeled(texts, "Domain:") ->
    "northernsea.org" for a paragraph reading "Domain: northernsea.org".
    """
    prefix = label.lower()
    for text in texts:
        if text.lower().startswith(prefix):
            return text[len(label):].strip()
    return None


def _find_date(texts: list[str]) -> str | None:
    """First paragraph text matching a bare "Month DD, YYYY" date - the
    page-1 metadata block's date line has no label prefix (confirmed
    structure - e.g. "July 28, 2026"), so it's matched by shape.
    """
    for text in texts:
        if _DATE_RE.match(text):
            return text
    return None


def _find_developer_and_ico(header_texts: list[str]) -> tuple[str | None, str | None]:
    """"Developer: X" / "QSI ICO: Y" from the header - confirmed to often
    sit in the SAME paragraph with no separator between them (e.g.
    "Developer: The Korolev DirectiveQSI ICO: INERTIARA"), so this
    searches within each paragraph's own text rather than a naive
    prefix-per-paragraph match.
    """
    for text in header_texts:
        if "developer:" in text.lower():
            developer_match = _DEVELOPER_RE.search(text)
            ico_match = _ICO_RE.search(text)
            developer = developer_match.group(1).strip() if developer_match else None
            ico = ico_match.group(1).strip() if ico_match else None
            return developer or None, ico or None
    return None, None


def _analyze_one(path: Path) -> tuple[CandidateInfo, str]:
    """Open `path` once (DocxEngine - no separate parsing) and extract
    both the CandidateInfo metadata and its full translatable body text
    (for similarity comparison - not stored on CandidateInfo itself, kept
    out of analyze_candidate_group()'s printed-friendly result).
    """
    stat = path.stat()
    try:
        engine = DocxEngine()
        engine.open(str(path))

        paragraphs = engine.get_paragraphs()
        header_footer = engine.get_header_footer_paragraphs()
        header_paragraphs = header_footer[: len(engine._header_paragraph_elements)]

        developer_name, ico_name = _find_developer_and_ico(_paragraph_texts(header_paragraphs))

        metadata_texts = _paragraph_texts([p for p in paragraphs if not p.translatable])
        domain = _find_labeled(metadata_texts, "Domain:")
        date = _find_date(metadata_texts)

        body_text = " ".join(_paragraph_texts([p for p in paragraphs if p.translatable]))

        info = CandidateInfo(
            path=path,
            developer_name=developer_name,
            ico_name=ico_name,
            domain=domain,
            date=date,
            paragraph_count=len(paragraphs),
            file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
        )
        return info, body_text
    except Exception as exc:  # noqa: BLE001 - one bad file must not abort the whole group
        info = CandidateInfo(
            path=path,
            developer_name=None,
            ico_name=None,
            domain=None,
            date=None,
            paragraph_count=0,
            file_size=stat.st_size,
            modified_time=datetime.fromtimestamp(stat.st_mtime),
            error=f"{type(exc).__name__}: {exc}",
        )
        return info, ""


def analyze_candidate_group(paths: list[Path]) -> GroupAnalysis:
    """Extract per-candidate metadata and pairwise text similarity for an
    UnresolvedDuplicateError group. A candidate that fails to open/parse
    gets CandidateInfo.error set instead of aborting the whole group; its
    pairwise similarities are simply omitted (empty body text would only
    produce a meaningless 0.0 ratio).
    """
    results = [_analyze_one(path) for path in paths]
    candidates = [info for info, _ in results]
    texts = [text for _, text in results]

    similarity: dict[tuple[int, int], float] = {}
    for i in range(len(candidates)):
        if candidates[i].error:
            continue
        for j in range(i + 1, len(candidates)):
            if candidates[j].error:
                continue
            similarity[(i, j)] = SequenceMatcher(None, texts[i], texts[j]).ratio()

    return GroupAnalysis(candidates=candidates, similarity=similarity)


def classify_group(analysis: GroupAnalysis) -> str:
    """Rough heuristic pre-sort for a human to confirm - NOT an input to
    resolve_source_document(), which never calls this. Four buckets:

    - "wahrscheinlich unabhaengige Dokumente": domain and/or developer
      name differ (and at least one of those fields is known) AND the
      minimum pairwise similarity is low (< _LOW_SIMILARITY_THRESHOLD).
    - "wahrscheinlich Sync-Duplikat": minimum pairwise similarity is high
      (>= _HIGH_SIMILARITY_THRESHOLD) and paragraph count/date agree
      across all candidates - looks like the same content saved twice.
    - "wahrscheinlich Versions-Update": minimum pairwise similarity is at
      least moderate (>= _LOW_SIMILARITY_THRESHOLD) but paragraph count
      or date differ between candidates - related content that changed
      over time.
    - "uneindeutig": the deliberate fallback whenever none of the above
      patterns clearly applies (including: fewer than 2 usable
      candidates, e.g. because of a CandidateInfo.error) - safer to admit
      ambiguity than to force a wrong bucket.
    """
    candidates = analysis.candidates
    if len(candidates) < 2 or not analysis.similarity:
        return "uneindeutig"

    min_similarity = min(analysis.similarity.values())

    domains = {c.domain for c in candidates if c.domain}
    developers = {c.developer_name for c in candidates if c.developer_name}
    same_domain = len(domains) == 1
    same_developer = len(developers) == 1
    domain_or_developer_known = bool(domains) or bool(developers)

    paragraph_counts = {c.paragraph_count for c in candidates}
    dates = {c.date for c in candidates if c.date}
    counts_or_dates_differ = len(paragraph_counts) > 1 or len(dates) > 1

    if (
        domain_or_developer_known
        and not (same_domain and same_developer)
        and min_similarity < _LOW_SIMILARITY_THRESHOLD
    ):
        return "wahrscheinlich unabhaengige Dokumente"

    if min_similarity >= _HIGH_SIMILARITY_THRESHOLD and not counts_or_dates_differ:
        return "wahrscheinlich Sync-Duplikat"

    if min_similarity >= _LOW_SIMILARITY_THRESHOLD and counts_or_dates_differ:
        return "wahrscheinlich Versions-Update"

    return "uneindeutig"
