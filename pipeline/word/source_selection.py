"""Source-document selection for Word-path batch processing: given a
folder of .docx files, group them by document number and pick the correct
source when a duplicate pair exists (see Backlog.md's "Duplikat-
Quellenregel").

Real project files (G:\\...\\ICO PDFs\\) confirmed the naming scheme: a
duplicate pair is "<number> <NAME>.docx" plus "<number> <NAME> (LS).docx"
(same number, "(LS)" suffix before the extension) - e.g.
"1854 MNEMOSYNE.docx" / "1854 MNEMOSYNE (LS).docx". Six of the seven known
pairs are content-identical (source choice is arbitrary); MNEMOSYNE's
(LS) version has ~35 substantial extra paragraphs the plain version lacks
and MUST be the source (see LS_PREFERRED_ICOS).

Grouping is by the leading document NUMBER, not by ICO name: a real,
confirmed case in the project folder has "1771 SILENCE.docx" (313
paragraphs, domain masguardian.org) and "1868 SILENCE.docx" (52
paragraphs, domain northernsea.org) - two completely independent,
unrelated documents from different developers that happen to reuse the
same codename. Grouping by name alone would have wrongly lumped both of
those together with the real "1868 SILENCE (LS).docx" duplicate into one
3-candidate conflict; grouping by number keeps 1771 and 1868 apart, since
an (LS) duplicate always shares its non-(LS) counterpart's number while
an unrelated document with the same name doesn't.

Not a full batch pipeline yet - just the selection building block.
"""
from __future__ import annotations

import re
from pathlib import Path

from pipeline.translation.protected_terms import derive_protected_term

_LEADING_NUMBER_RE = re.compile(r"^(\d+)\s+")
_LS_SUFFIX_RE = re.compile(r"\s*\(LS\)\s*$", re.IGNORECASE)

# ICO names (uppercase) with a known "(LS)"-duplicate situation (see
# Backlog.md's "Duplikat-Quellenregel"). resolve_source_document() only
# auto-resolves a 2-candidate duplicate for names in this set; a duplicate
# for any OTHER ICO name is unexpected and raises UnresolvedDuplicateError
# instead of silently guessing which file is "correct".
KNOWN_DUPLICATE_ICOS = frozenset(
    {"HARMONICJ", "MNEMOSYNE", "CONTINUUM", "AXIOMCRADLE", "WOUNDS", "ONEPERCENT", "SILENCE"}
)

# Subset of KNOWN_DUPLICATE_ICOS whose (LS) variant is the correct source
# despite being a "duplicate" - because it contains substantially more
# content than the non-(LS) version (~35 extra paragraphs for MNEMOSYNE).
# Every other known duplicate pair is content-identical (only XML-
# formatting-artifact differences), so the non-(LS) version is used there.
# A set - not a single hardcoded name inline in resolve_source_document() -
# so a future newly-discovered MNEMOSYNE-like special case is a one-line
# addition here instead of a code change.
LS_PREFERRED_ICOS = frozenset({"MNEMOSYNE"})


class UnresolvedDuplicateError(Exception):
    """Raised by resolve_source_document() when a set of candidates can't
    be resolved to a single source automatically - deliberately fails
    loudly instead of guessing (see resolve_source_document()), the same
    error-handling philosophy tools/compare_providers.py uses for
    per-block provider failures: surface the problem clearly rather than
    silently picking one.
    """


class MissingDocumentNumberError(Exception):
    """Raised by extract_document_number() when a filename has no leading
    "<number> " prefix - fails loudly rather than silently putting such a
    file into some fallback group (see extract_document_number()).
    """


def extract_document_number(path: Path) -> str:
    """The leading document number from `path`'s filename (e.g. "1868"
    from "1868 SILENCE (LS).docx") - the actual grouping key
    discover_documents() uses for duplicate detection: an (LS) duplicate
    always shares its counterpart's number, while two independent
    documents that merely happen to reuse the same ICO codename (a real,
    confirmed case - see the module docstring) have different numbers and
    must not be grouped together.

    The number sits before the name (and "(LS)", which is at the very
    end), so no "(LS)"-stripping is needed here the way document_ico_name()
    needs it - matching against the start of the filename is unambiguous
    either way.

    Raises MissingDocumentNumberError if the filename has no leading
    "<number> " prefix at all.
    """
    match = _LEADING_NUMBER_RE.match(path.stem.strip())
    if match is None:
        raise MissingDocumentNumberError(
            f"{path.name!r} has no leading '<number> ' prefix - cannot determine its document number."
        )
    return match.group(1)


def _is_ls_variant(path: Path) -> bool:
    """Whether `path`'s filename ends in "(LS)" (case-insensitive, before
    the extension) - e.g. "1854 MNEMOSYNE (LS).docx".
    """
    return bool(_LS_SUFFIX_RE.search(path.stem))


def document_ico_name(filename: str) -> str:
    """The document's ICO name, for protected_terms.py purposes and for
    picking the right entry from KNOWN_DUPLICATE_ICOS/LS_PREFERRED_ICOS -
    NOT used for duplicate grouping anymore (see discover_documents()).
    derive_protected_term() (pipeline.translation.protected_terms) with a
    trailing "(LS)" tag - if present - stripped too, so e.g.
    "1854 MNEMOSYNE (LS).docx" and "1854 MNEMOSYNE.docx" both resolve to
    the same name "MNEMOSYNE" (derive_protected_term() alone would return
    "MNEMOSYNE (LS)" for the first one).
    """
    return _LS_SUFFIX_RE.sub("", derive_protected_term(filename)).strip()


def discover_documents(root: Path) -> dict[str, list[Path]]:
    """Group every .docx directly under `root` by extract_document_number()
    - not by document_ico_name() (see the module docstring for why: two
    independent documents can coincidentally share the same derived name
    while having different numbers). Not recursive - the real project
    folder is flat (verified).
    """
    groups: dict[str, list[Path]] = {}
    for path in sorted(root.glob("*.docx")):
        number = extract_document_number(path)
        groups.setdefault(number, []).append(path)
    return groups


def resolve_source_document(ico_name: str, candidates: list[Path]) -> Path:
    """Pick the correct source .docx for `ico_name` out of `candidates`
    (the same-document-number group from discover_documents(), or built
    by hand). `ico_name` is the document's ICO name (see
    document_ico_name()), NOT its document number - discover_documents()
    groups by number, so a caller iterating its result needs to derive
    the name itself, e.g. via document_ico_name(candidates[0].name),
    before calling this.

    - Exactly 1 candidate: returned directly, no duplicate question - the
      name plays no role at all here.
    - Exactly 2 candidates, one being the (LS) variant of the other, AND
      `ico_name` (case-insensitive) is in KNOWN_DUPLICATE_ICOS: the (LS)
      variant is chosen if `ico_name` is in LS_PREFERRED_ICOS, otherwise
      the non-(LS) variant.
    - Anything else - more than 2 candidates, a duplicate for an ICO name
      not in KNOWN_DUPLICATE_ICOS, or 2 candidates that aren't a clean
      (LS)/non-(LS) pair - raises UnresolvedDuplicateError rather than
      guessing, listing every candidate path so the mismatch can be
      resolved by hand.
    """
    if len(candidates) == 1:
        return candidates[0]

    normalized_name = ico_name.strip().upper()

    if len(candidates) == 2 and normalized_name in KNOWN_DUPLICATE_ICOS:
        ls_candidates = [p for p in candidates if _is_ls_variant(p)]
        non_ls_candidates = [p for p in candidates if not _is_ls_variant(p)]
        if len(ls_candidates) == 1 and len(non_ls_candidates) == 1:
            prefer_ls = normalized_name in LS_PREFERRED_ICOS
            return ls_candidates[0] if prefer_ls else non_ls_candidates[0]

    raise UnresolvedDuplicateError(
        f"Cannot automatically resolve {len(candidates)} candidate(s) for ICO "
        f"{ico_name!r} (not a known (LS)-duplicate pair, or an unexpected "
        f"candidate shape) - resolve by hand: {[str(p) for p in candidates]}"
    )
