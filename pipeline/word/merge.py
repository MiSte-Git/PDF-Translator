"""DOCX merge/insert (01.09.2026) - mirrors pipeline/pdf/pymupdf_engine.py's
merge_pdfs(), on Michael's follow-up: "Jetzt noch das ganze für *.docx.
Kann man überhaupt mittlerweile ca. 2000 docx zusammenführen?"

This is the only file in the project allowed to import `docx`
(python-docx) or `docxcompose` - the same import-exclusivity rule
pymupdf_engine.py already applies to PyMuPDF and pipeline/drive_auth.py
applies to the Google API libraries, for the identical reason: nothing
outside this file needs to know these two libraries exist. python-docx
itself has no native "append another document's body" operation (it was
only ever in requirements.txt for python-docx-based fixture generation
elsewhere in the test suite); docxcompose (4teamwork, actively maintained,
built on python-docx) fills that gap - it deep-copies each appended
document's content, remapping numbering (`numId`/`abstractNumId`) and
matching styles by name to avoid the ID collisions/renumbering breakage a
naive python-docx-only concatenation would produce.

Whole-file merge only (confirmed with Michael, 01.09.2026) - unlike
merge_pdfs()'s per-source page-range selection, DOCX has no fixed "pages"
in the file itself (pagination is a rendering-time concept, dependent on
viewer/printer/fonts installed), so a MergeSourceSpec-style page-range
concept doesn't have a DOCX equivalent; MergeSourceSpec's PDF-only
`pages` field simply has no counterpart here.

Two behaviors deliberately differ from merge_pdfs(), both explained where
they happen below:
1. A section break (new page) is inserted between every two merged
   documents (DOCX has no page concept as noted above, so nothing does
   this automatically the way PDF's own page boundaries do) - a SECTION
   break rather than a plain page break since 03.09.2026, because each
   document must keep its own header/footer, and in OOXML those are
   section properties (see _append_as_own_section()).
2. A single source that fails to APPEND (as opposed to fails to OPEN) is
   skipped with a warning rather than aborting the whole run - see
   _merge_sequential()'s docstring for why this is not simply
   "merge_pdfs() copied for DOCX", but a deliberate deviation.

Batching for large merges (Michael, 01.09.2026: "automatisch batchen"
confirmed) - see merge_docx_files()'s docstring for the two-level
chunk-then-merge-chunks architecture and why it exists: no library here
is built for streaming/incremental merging (everything happens in
memory), and there are no published reports of anyone merging on the
order of 1000-2000 separate .docx files with this stack - see
Backlog.md 01.09.2026 for the researched background.
"""
from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Sequence

DEFAULT_BATCH_SIZE = 100
"""Chunk size for merge_docx_files()'s two-level batching - picked as a
round, conservative number comfortably below any scale that's been
publicly reported working with docxcompose (see Backlog.md 01.09.2026's
research summary: essentially untested territory above a few dozen files
in any public report found), not derived from a specific measured limit
on this machine. Exposed as a parameter, not hardcoded, so it can be
tuned later against real documents/real hardware without a code change.
"""


@dataclass
class WordMergeStats:
    segments: int
    """Sources successfully appended (across every batch) - can be LESS
    than len(sources) if some were skipped after a per-file append failure
    (see _merge_sequential()'s docstring) or the run was cancelled."""
    files_processed: int
    """Distinct source files actually opened, counted by resolved path -
    mirrors PdfMergeStats.files_processed's identical dedup convention
    (the same file listed twice, e.g. a repeated cover page, counts once
    here)."""
    batches: int
    """Number of first-level chunk files produced during batching - 0 if
    the whole merge fit in a single pass (len(sources) <= batch_size), in
    which case no intermediate files were ever written to disk at all."""
    cancelled: bool = False
    warnings: list[str] = field(default_factory=list)
    """Per-file notes that do NOT represent the whole run failing - an
    append-compatibility skip (see _merge_sequential()), or an open
    failure discovered only once inside a later batch iteration (see the
    two-level path below for why that can't simply abort the same way the
    single-pass path's open failures do)."""


def _open_docx(path: Path):
    """Open `path` as a python-docx Document, wrapping any failure (missing,
    not a valid .docx/corrupt zip, encrypted) into a clear, file-named
    ValueError - mirrors merge_pdfs()'s identical treatment of a source
    that can't even be opened. Local import: see module docstring for why
    `docx` is only ever imported inside this one file.
    """
    from docx import Document

    try:
        return Document(str(path))
    except Exception as exc:  # noqa: BLE001 - re-raised as a clear, file-named ValueError below
        raise ValueError(f'"{path.name}" konnte nicht geöffnet werden: {exc}') from exc


def _copy_image_relationship(composer, dest_part, relationship):
    """Add an image relationship on `dest_part` pointing at the same image
    `relationship` already points at, going through python-docx's own
    Package.image_parts registry - NOT Composer.add_relationship()'s
    generic, package-wide filename scan.

    03.09.2026 (Michael's real merged file, "ist defekt und kann deshalb
    nicht geöffnet werden"): the two pick image numbers independently and
    can choose the SAME "next free" partname, e.g. word/media/image12.jpeg
    twice - a duplicate zip entry, which is exactly the kind of damage
    that triggers this dialog. docxcompose's own add_images()/add_shapes()
    (used for images inside the appended BODY, called from
    Composer.append() itself) name new image parts via
    `composer.pkg.image_parts._get_by_sha1()`/`_add_image_part()`, a
    Package-level, SHA1-deduplicating cache that is separate from and
    unaware of Composer.add_relationship()'s own FILENAME_IDX_RE-based
    scan of the package (used for every OTHER relationship type - fonts,
    external hyperlinks, diagrams - see _copy_header_footer_part()'s
    docstring for why the generic path is fine there). Since a header can
    itself embed images (a repeated logo, most commonly), it must use the
    SAME `image_parts` registry as body images so the two never hand out
    the same name - and as a bonus this also deduplicates the identical
    logo image referenced by many merged headers, exactly like
    Composer.add_images() would for a body image reused across documents.
    """
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docxcompose.composer import ImageWrapper

    image_parts = composer.pkg.image_parts
    target_part = relationship.target_part
    new_image_part = image_parts._get_by_sha1(target_part.sha1)
    if new_image_part is None:
        new_image_part = image_parts._add_image_part(ImageWrapper(target_part))
    return dest_part.relate_to(new_image_part, RT.IMAGE)  # already the rId string, see Part.relate_to()


def _copy_header_footer_part(composer, relationship) -> str:
    """Copy the header/footer part behind `relationship` (from an appended
    document) into the composer's master package and return the new rId
    the master document part refers to it by.

    Not delegated to Composer.add_relationship(): that creates a generic
    opc Part (blob only), but docxcompose's own renumber_docpr_ids()/
    renumber_nvpicpr_ids() later iterate every header/footer part of the
    master expecting a real python-docx HeaderPart/FooterPart with an
    `.element` - a generic Part there raises AttributeError inside
    append(). So the part is recreated as the proper class with a deep
    copy of its XML; the parts IT references (fonts, external hyperlinks,
    diagrams, ...) are copied with add_relationship() and their rIds
    rewritten inside the copied XML explicitly, rather than relying on
    the "same insertion order gives the same rIds" assumption docxcompose
    makes for itself. The one exception is an IMAGE relationship (a logo
    in the header, most commonly) - see _copy_image_relationship() for why
    that specific type cannot go through add_relationship() as well.
    """
    from copy import deepcopy

    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.opc.packuri import PackURI
    from docx.oxml.ns import nsmap
    from docx.parts.hdrftr import FooterPart, HeaderPart

    source_part = relationship.target_part
    package = composer.doc.part.package
    if relationship.reltype == RT.HEADER:
        part_class, prefix = HeaderPart, "/word/header"
    else:
        part_class, prefix = FooterPart, "/word/footer"

    existing = {str(part.partname) for part in package.iter_parts()}
    number = 1
    while f"{prefix}{number}.xml" in existing:
        number += 1
    new_part = part_class(
        PackURI(f"{prefix}{number}.xml"), source_part.content_type, deepcopy(source_part.element), package
    )

    inner_rid_map: dict[str, str] = {}
    for rid, inner_rel in source_part.rels.items():
        if inner_rel.reltype == RT.IMAGE and not inner_rel.is_external:
            inner_rid_map[rid] = _copy_image_relationship(composer, new_part, inner_rel)
        else:
            inner_rid_map[rid] = composer.add_relationship(source_part, new_part, inner_rel).rId
    if inner_rid_map:
        r_ns = nsmap["r"]
        for element in new_part.element.iter():
            for attribute, value in list(element.attrib.items()):
                if attribute.startswith("{%s}" % r_ns) and value in inner_rid_map:
                    element.set(attribute, inner_rid_map[value])

    return composer.doc.part.relate_to(new_part, relationship.reltype)


def _ensure_blank_header_footer(composer, sectpr) -> None:
    """Give `sectpr` an explicit (empty) default header and footer where it
    has none, so nothing is inherited from the section before it - see
    _append_as_own_section(). Even-page/first-page variants are left
    alone: they only apply when the section itself asks for them."""
    from docx.opc.constants import RELATIONSHIP_TYPE as RT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn
    from docx.parts.hdrftr import FooterPart, HeaderPart

    package = composer.doc.part.package
    for tag, part_class, reltype in (
        ("w:headerReference", HeaderPart, RT.HEADER),
        ("w:footerReference", FooterPart, RT.FOOTER),
    ):
        if sectpr.xpath(f"{tag}[@w:type='default']"):
            continue
        rid = composer.doc.part.relate_to(part_class.new(package), reltype)
        reference = OxmlElement(tag)
        reference.set(qn("w:type"), "default")
        reference.set(qn("r:id"), rid)
        # schema order: headerReference* first, then footerReference*
        anchors = sectpr.xpath("w:footerReference" if tag == "w:footerReference" else "w:headerReference")
        if anchors:
            anchors[-1].addnext(reference)
        elif tag == "w:footerReference" and sectpr.xpath("w:headerReference"):
            sectpr.xpath("w:headerReference")[-1].addnext(reference)
        else:
            sectpr.insert(0, reference)


def _append_as_own_section(composer, doc) -> None:
    """Append `doc` to `composer` so that it keeps ITS OWN header/footer
    (03.09.2026, Michael: "Beim Zusammenführen der Worddokumente wird [...]
    der Header des ersten Dokuments übernommen. Auf jeden Fall ist dort auf
    jeder Seite der gleiche Header.").

    Why docxcompose alone gets this wrong: Composer.append() copies only
    the body CONTENT of the appended document. Its body-level <w:sectPr>
    (page size, margins - and the header/footer references) is dropped,
    and every headerReference/footerReference inside inner sections is
    stripped (remove_header_and_footer_references()). Headers/footers are
    section properties in OOXML, so all appended content silently falls
    under the master document's single section - i.e. the FIRST file's
    header on every page. docxcompose's own comment calls the situation
    "really messy" and leaves it at that.

    What this does instead, per appended document:
    1. Copies every header/footer part the document references (with the
       images etc. those parts reference, via Composer.add_relationship())
       into the master package and remembers old rId -> new rId.
    2. Calls Composer.append() with its header-reference stripping and its
       "inherit the master's headers into the first new section" fix-up
       disabled (both are instance-level overrides, nothing global).
    3. Turns the boundary into a real section break: the master's current
       body-level sectPr (which describes the PREVIOUS document's last
       section) moves into a new paragraph placed right before the
       appended content - that is how OOXML ends a section - and a copy of
       the appended document's own body-level sectPr becomes the new
       body-level sectPr. The appended document's first section is forced
       to start on a new page (w:type nextPage), which also replaces the
       explicit page-break paragraph the merge used to insert: a page
       break followed by a nextPage section break would leave an empty
       page in between.
    4. Remaps the header/footer rIds in the appended content's inner
       sectPrs and in the new body-level sectPr to the copied parts.

    Nothing about the master document is touched until append() has
    succeeded, so a docxcompose append failure (see _merge_sequential())
    still leaves the composed document exactly as it was.
    """
    from copy import deepcopy

    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    body = composer.doc.element.body
    r_id = qn("r:id")
    ref_xpath = ".//w:headerReference|.//w:footerReference"

    # 1. header/footer parts -> master package
    rid_map: dict[str, str] = {}
    for ref in doc.element.body.xpath(ref_xpath):
        old_rid = ref.get(r_id)
        if old_rid in rid_map or old_rid not in doc.part.rels:
            continue
        rid_map[old_rid] = _copy_header_footer_part(composer, doc.part.rels[old_rid])

    # 2. append with docxcompose's header handling switched off (this
    #    composer instance only)
    old_body_sectpr = body.find(qn("w:sectPr"))
    insert_at = composer.append_index()
    composer.remove_header_and_footer_references = lambda _doc, _element: None
    composer.first_section_properties_added = True
    composer.append(doc)

    # 3. section break at the boundary, appended document's sectPr at the end
    source_sectpr = doc.element.body.find(qn("w:sectPr"))
    if old_body_sectpr is not None:
        break_paragraph = OxmlElement("w:p")
        break_ppr = OxmlElement("w:pPr")
        break_ppr.append(deepcopy(old_body_sectpr))
        break_paragraph.append(break_ppr)
        body.insert(insert_at, break_paragraph)
        body.remove(old_body_sectpr)
        insert_at += 1
    new_body_sectpr = deepcopy(source_sectpr if source_sectpr is not None else old_body_sectpr)
    if new_body_sectpr is not None:
        body.append(new_body_sectpr)

    # 4. remap header/footer references of the appended content only
    #    (master rIds could coincidentally share the same strings)
    new_elements = list(body)[insert_at:]
    first_boundary_sectpr = None
    for element in new_elements:
        for sectpr in element.xpath(".//w:sectPr|self::w:sectPr"):
            if first_boundary_sectpr is None:
                first_boundary_sectpr = sectpr
            for ref in sectpr.xpath(ref_xpath):
                mapped = rid_map.get(ref.get(r_id))
                if mapped is not None:
                    ref.set(r_id, mapped)

    if first_boundary_sectpr is not None:
        # A section without its own default header/footer reference
        # INHERITS the previous section's in OOXML - i.e. the previous
        # document's. Standalone, that document had a blank one, so give
        # it an explicit empty part to keep the merge faithful.
        _ensure_blank_header_footer(composer, first_boundary_sectpr)
        section_type = first_boundary_sectpr.find(qn("w:type"))
        if section_type is None:
            section_type = OxmlElement("w:type")
            # schema order: headerReference*, footerReference*, footnotePr?,
            # endnotePr?, type?, pgSz?, ...
            predecessors = first_boundary_sectpr.xpath(
                "w:headerReference|w:footerReference|w:footnotePr|w:endnotePr"
            )
            if predecessors:
                predecessors[-1].addnext(section_type)
            else:
                first_boundary_sectpr.insert(0, section_type)
        section_type.set(qn("w:val"), "nextPage")


def _restore_body(body, children_before) -> None:
    """Put `body`'s children back to exactly `children_before` (same
    elements, same order) after a failed append - see _merge_sequential().
    lxml moves an element on append, so re-appending the snapshot also
    pulls back an original that a partial append had detached (the
    body-level sectPr _append_as_own_section() relocates, for instance).
    """
    for element in list(body):
        body.remove(element)
    for element in children_before:
        body.append(element)


def _merge_sequential(
    sources: Sequence[Path],
    total_for_progress: int,
    done_before: int,
    progress_callback: Callable[[str], None] | None,
    should_cancel: Callable[[], bool] | None,
):
    """Merge `sources` (a flat list, batching handled by the caller) into
    one in-memory python-docx Document via docxcompose. Returns
    (document_or_None, appended_count, cancelled, warnings) - `document`
    is None only if `sources` was empty or cancelled before the first
    file was even opened.

    Two DIFFERENT kinds of per-source failure are handled deliberately
    differently, unlike merge_pdfs() (which hard-fails on any source
    problem):
    - Opening a source fails (missing/corrupt/not-a-docx): this is almost
      always a real problem with the merge's INPUT LIST itself, exactly
      like merge_pdfs()'s treatment - raises ValueError, aborting the
      whole run. The caller should not have listed a file it can't read.
    - Appending an OPENED, valid .docx fails inside docxcompose (a known,
      documented category of docxcompose limitation - SmartArt, certain
      text boxes, malformed complex-field structures; see Backlog.md
      01.09.2026's research summary): this is a property of that ONE
      file's content, unrelated to whether the merge's input list is
      correct. At the 1000-2000 file scale this feature is explicitly
      built for, aborting an otherwise-successful multi-hour run over one
      such file would be disproportionate - so this case is caught,
      recorded as a warning, and that file is skipped; the merge
      continues with the rest. This is a deliberate deviation from
      merge_pdfs()'s stricter policy, not an oversight - documented here
      and in Backlog.md 01.09.2026.
    """
    from docxcompose.composer import Composer

    warnings: list[str] = []
    composer: "Composer | None" = None
    appended = 0
    cancelled = False

    for index, path in enumerate(sources):
        if should_cancel is not None and should_cancel():
            cancelled = True
            break
        if progress_callback is not None:
            progress_callback(f"Datei {done_before + index + 1}/{total_for_progress}: {path.name}")

        doc = _open_docx(path)  # hard-fail on open, see docstring above

        if composer is None:
            composer = Composer(doc)
            appended += 1
            continue

        # Was composer.doc.add_page_break() + composer.append(doc) until
        # 03.09.2026 - see _append_as_own_section() for why that lost
        # every appended document's header/footer.
        body = composer.doc.element.body
        body_before = list(body)
        try:
            _append_as_own_section(composer, doc)
        except Exception as exc:  # noqa: BLE001 - soft-fail, see docstring above
            # docxcompose inserts element by element and can fail halfway
            # (e.g. on a SmartArt part of the 5th paragraph) - without this
            # rollback the first half of the "skipped" document silently
            # stayed in the result while the warning claimed it was
            # skipped (Michael, 03.09.2026: "Das sind solche Fehler die
            # nicht so gut auffallen."). Restoring the body's exact
            # previous child list drops everything the failed append
            # inserted; parts/styles it may have added to the package stay
            # behind unreferenced, which is harmless to the content.
            _restore_body(body, body_before)
            warnings.append(f'"{path.name}" konnte nicht angehängt werden und wurde übersprungen ({exc}).')
            continue
        appended += 1

    return (composer.doc if composer is not None else None), appended, cancelled, warnings


def merge_docx_files(
    sources: Sequence[Path],
    destination: Path,
    batch_size: int = DEFAULT_BATCH_SIZE,
    progress_callback: Callable[[str], None] | None = None,
    should_cancel: Callable[[], bool] | None = None,
) -> WordMergeStats:
    """Merge whole DOCX files, in list order, into one new .docx at
    `destination` - the DOCX counterpart of merge_pdfs(), whole-file only
    (see module docstring for why there is no page-range equivalent).

    A section break (new page) is inserted between every two sources'
    content (DOCX has no inherent page boundary the way PDF pages give
    merge_pdfs() one for free) so the merged result reads as distinct
    documents joined at page boundaries rather than paragraphs from
    different sources running together - and every source keeps its own
    header/footer and page setup (see _append_as_own_section()).

    Batching (Michael, 01.09.2026 - "automatisch batchen" confirmed): if
    `sources` fits within one `batch_size` (default 100), it is merged in
    a single pass with no intermediate files, exactly like merge_pdfs().
    Above that, sources are split into `batch_size`-sized groups, each
    merged into its own temporary "chunk" .docx first, and THOSE chunk
    files are then merged together the same way into `destination` - a
    genuine two-level merge, not a single continuous pass, so that:
    - the process never has to hold docxcompose's cumulative style/
      numbering bookkeeping for los of 2000 originals open across the
      whole run at once (only one batch's worth at a time, per level),
    - a crash partway through leaves the already-completed chunk files on
      disk as valid, inspectable .docx files (in the TemporaryDirectory,
      so gone once this call returns - but present for the duration of a
      long run, unlike a pure in-memory single pass which loses
      everything on a crash).
    This two-level shape matches what Michael confirmed explicitly (merge
    ~100 into an intermediate result, then merge the intermediates) rather
    than being read as "any batching" - see the AskUserQuestion exchange
    recorded in Backlog.md 01.09.2026. A style/numbering-matching decision
    docxcompose makes when merging chunk B is made relative to what chunk
    B's own composer already contains, not against every one of the
    original 2000 files' styles directly - in rare cases this could
    theoretically resolve a style-name collision slightly differently
    than one giant flat merge of all 2000 at once would have; documented
    here as an accepted, low-probability trade-off (not a hidden bug) in
    exchange for the crash-resilience and memory-bounding above.

    Cancellation is cooperative, polled BETWEEN sources while ORIGINAL
    files are still being opened and appended (both in the single-pass
    path and, in the two-level path, within each first-level batch).
    Deliberately NOT polled again during the two-level path's final
    "merge the completed chunk files together" pass: should_cancel is
    normally a threading.Event, which once set stays set - polling it
    there too would make that pass immediately bail out and keep only the
    FIRST completed chunk, silently discarding every other chunk the
    first-level loop had already finished. Consolidating already-produced
    chunk files is comparatively fast, bounded work, so it always runs to
    completion once started - the practical effect is that a cancelled
    batched run keeps everything completed up to the batch that was in
    progress when cancellation was requested, not just the first batch.
    Either way, whatever was already merged is still saved
    (stats.cancelled=True), the same "keep the partial result" choice
    merge_pdfs() makes.

    Raises ValueError for: an empty `sources` list; a source that can't
    even be opened (see _merge_sequential()'s docstring - this always
    aborts, at either merge level); or every source being skipped/
    cancelled before anything was ever appended.
    """
    if not sources:
        raise ValueError("Keine Quelldateien zum Zusammenführen angegeben.")

    sources = [Path(p) for p in sources]
    total = len(sources)
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)

    resolved_seen: set[Path] = set()
    for path in sources:
        resolved_seen.add(path.resolve())
    files_processed = len(resolved_seen)

    if total <= batch_size:
        doc, appended, cancelled, warnings = _merge_sequential(sources, total, 0, progress_callback, should_cancel)
        if doc is None:
            raise ValueError("Keine der Quelldateien konnte übernommen werden - keine Ausgabe erzeugt.")
        doc.save(str(destination))
        return WordMergeStats(
            segments=appended, files_processed=files_processed, batches=0, cancelled=cancelled, warnings=warnings
        )

    # --- two-level batched path -----------------------------------------
    all_warnings: list[str] = []
    cancelled = False
    total_appended = 0
    chunk_paths: list[Path] = []

    with tempfile.TemporaryDirectory(prefix="pdf_translator_docx_merge_") as tmp:
        tmp_dir = Path(tmp)
        chunks = [sources[i : i + batch_size] for i in range(0, total, batch_size)]

        for batch_index, chunk in enumerate(chunks):
            if progress_callback is not None:
                progress_callback(f"Batch {batch_index + 1}/{len(chunks)} wird zusammengeführt …")
            doc, appended, chunk_cancelled, warnings = _merge_sequential(
                chunk, total, total_appended, progress_callback, should_cancel
            )
            all_warnings.extend(warnings)
            total_appended += appended
            if doc is not None:
                chunk_path = tmp_dir / f"batch_{batch_index:04d}.docx"
                doc.save(str(chunk_path))
                chunk_paths.append(chunk_path)
            if chunk_cancelled:
                cancelled = True
                break

        if not chunk_paths:
            raise ValueError("Keine der Quelldateien konnte übernommen werden - keine Ausgabe erzeugt.")

        if len(chunk_paths) == 1:
            # A plain rename would raise if the OS temp dir and destination
            # are on different filesystems (common - /tmp is often tmpfs) -
            # shutil.move() falls back to copy+delete in that case.
            shutil.move(str(chunk_paths[0]), str(destination))
        else:
            if progress_callback is not None:
                progress_callback(f"Führe {len(chunk_paths)} Zwischenergebnisse zusammen …")
            # should_cancel is deliberately NOT passed through here (unlike
            # the first-level loop above): should_cancel is normally a
            # threading.Event that, once set, stays set - if this second
            # pass polled it too, cancelling partway through batch 3 of 5
            # would make THIS pass immediately bail out as well and only
            # keep chunk 1, silently discarding chunks 2 and 3's already-
            # completed work. Consolidating the chunks that already exist
            # on disk is comparatively fast, bounded work (no new files are
            # opened beyond len(chunk_paths) of them), so it always runs to
            # completion once started, keeping everything the first-level
            # pass did manage to finish before it was told to stop.
            final_doc, _final_appended, _final_cancelled, final_warnings = _merge_sequential(
                chunk_paths, len(chunk_paths), 0, None, None
            )
            all_warnings.extend(final_warnings)
            assert final_doc is not None  # not cancellable here (should_cancel=None above), and chunk_paths is non-empty
            final_doc.save(str(destination))

    return WordMergeStats(
        segments=total_appended,
        files_processed=files_processed,
        batches=len(chunk_paths),
        cancelled=cancelled,
        warnings=all_warnings,
    )
