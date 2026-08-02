"""Manifest-based source tracking for the ICO Google-Drive folder: which
.docx file(s) are the approved translation source for each document
number, so a re-scan of the folder (files get added/renamed/touched by
Google Drive sync over time) can tell "nothing to do" apart from "a human
needs to look at this again" without re-litigating every already-decided
duplicate case.

Reuses pipeline/word/source_selection.py's discover_documents() (grouping
by leading document number) and pipeline/word/duplicate_analysis.py's
classify_group() (a rough heuristic pre-sort, offered here only as a
suggestion in new_duplicate diff entries - never used to auto-decide).

Manifest JSON shape, one entry per document number::

    {
      "1868": {
        "status": "approved",
        "files": [
          {"filename": "1868 SILENCE.docx", "mtime": "...", "sha256": "..."},
          {"filename": "1868 VALCYRON.docx", "mtime": "...", "sha256": "..."}
        ],
        "excluded": ["1868 SILENCE (LS).docx"],
        "note": "..."
      }
    }

"files" is a list because some document numbers genuinely have more than
one valid source (independent documents that happen to share a number,
e.g. 1868 SILENCE + VALCYRON) - the normal case is a list of exactly 1.
"excluded" is a separate list of filenames that are known to sit in the
folder under this number but were deliberately rejected as a source (e.g.
a superseded "(LS)" duplicate) - kept apart from "files" (the schema the
task specified) rather than folded into it, since a file can be excluded
for a specific reason but we still don't want it looking like a `changed`
approved file. Excluded filenames aren't tracked by mtime/sha256: nobody
cares if a file nobody will ever translate is touched or resaved.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from pipeline.word.duplicate_analysis import analyze_candidate_group, classify_group
from pipeline.word.source_selection import discover_documents

_HASH_CHUNK_SIZE = 1024 * 1024


def sha256_of(path: Path) -> str:
    """SHA-256 of `path`'s content, streamed rather than read whole -
    the folder holds ~2200 files, some with embedded images."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(_HASH_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mtime_of(path: Path) -> str:
    """`path`'s modification time as a stable, timezone-aware ISO-8601
    string - used as the manifest's cheap per-file change signal (see the
    module docstring: sha256 is only computed to confirm a real diff)."""
    return datetime.fromtimestamp(path.stat().st_mtime, tz=timezone.utc).isoformat()


@dataclass
class FileEntry:
    filename: str
    mtime: str
    sha256: str

    def to_dict(self) -> dict:
        return {"filename": self.filename, "mtime": self.mtime, "sha256": self.sha256}

    @staticmethod
    def from_dict(data: dict) -> FileEntry:
        return FileEntry(filename=data["filename"], mtime=data["mtime"], sha256=data["sha256"])

    @staticmethod
    def from_path(path: Path) -> FileEntry:
        return FileEntry(filename=path.name, mtime=mtime_of(path), sha256=sha256_of(path))


@dataclass
class ManifestEntry:
    status: str
    files: list[FileEntry]
    excluded: list[str] = field(default_factory=list)
    note: str = ""

    def to_dict(self) -> dict:
        data: dict = {"status": self.status, "files": [f.to_dict() for f in self.files]}
        if self.excluded:
            data["excluded"] = sorted(self.excluded)
        if self.note:
            data["note"] = self.note
        return data

    @staticmethod
    def from_dict(data: dict) -> ManifestEntry:
        return ManifestEntry(
            status=data["status"],
            files=[FileEntry.from_dict(f) for f in data.get("files", [])],
            excluded=list(data.get("excluded", [])),
            note=data.get("note", ""),
        )


Manifest = dict[str, ManifestEntry]


def load_manifest(path: Path) -> Manifest:
    """An empty manifest if `path` doesn't exist yet (first-ever scan),
    rather than raising - the whole point of `scan` is to be runnable
    against a not-yet-seeded manifest."""
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {number: ManifestEntry.from_dict(entry) for number, entry in raw.items()}


def save_manifest(path: Path, manifest: Manifest) -> None:
    """Sorted keys, stable 2-space indent - so manual `approve` edits
    produce small, reviewable Git diffs instead of a reshuffled file."""
    raw = {number: entry.to_dict() for number, entry in manifest.items()}
    path.write_text(
        json.dumps(raw, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def scan_folder(root: Path) -> dict[str, list[Path]]:
    """Thin wrapper around discover_documents() - kept as its own function
    so callers (and tests) depend on ico_translate.manifest for the whole
    scan step, without needing to know it's really source_selection.py
    underneath."""
    return discover_documents(root)


@dataclass
class AutoApproved:
    """A document number never seen before with exactly 1 file - approved
    without asking, since there's no duplicate question to decide."""
    number: str
    file: FileEntry


@dataclass
class ChangedFile:
    """A known, already-approved-or-excluded document number where the
    actual folder content disagrees with the manifest: either a tracked
    approved file's content genuinely changed (mtime differs AND the
    confirming hash differs too), or a file sits under this number that
    the manifest doesn't know as approved OR excluded (a new file dropped
    in later, most likely) - both are surfaced here rather than in
    new_duplicate, since new_duplicate is specifically for a NUMBER the
    manifest has never seen at all."""
    number: str
    filename: str
    reason: str
    manifest_entry: FileEntry | None
    current_mtime: str | None
    current_sha256: str | None


@dataclass
class NewDuplicateGroup:
    """A document number never seen before with more than 1 file - needs a
    human decision (see resolve_source_document()/classify_group()),
    `suggestion` is classify_group()'s pre-sort label, offered purely as a
    hint."""
    number: str
    files: list[Path]
    suggestion: str


@dataclass
class MissingFile:
    """A file the manifest lists as approved for this number that can no
    longer be found in the folder - surfaced rather than silently dropped,
    since a vanished source file breaks batch translation for that
    number."""
    number: str
    filename: str
    manifest_entry: FileEntry


@dataclass
class ScanDiff:
    auto_approved: list[AutoApproved] = field(default_factory=list)
    unchanged: list[tuple[str, str]] = field(default_factory=list)
    changed: list[ChangedFile] = field(default_factory=list)
    new_duplicate: list[NewDuplicateGroup] = field(default_factory=list)
    missing: list[MissingFile] = field(default_factory=list)

    def has_issues(self) -> bool:
        return bool(self.changed or self.new_duplicate or self.missing)


def diff_against_manifest(scan_result: dict[str, list[Path]], manifest: Manifest) -> ScanDiff:
    """Compare a fresh scan_folder() result against the current manifest,
    one document number at a time. See ScanDiff's field dataclasses for
    what each bucket means; nothing here mutates `manifest` - see
    apply_auto_approved() for the one bucket (auto_approved) that gets
    written back automatically.
    """
    diff = ScanDiff()

    for number, paths in sorted(scan_result.items(), key=lambda kv: int(kv[0])):
        entry = manifest.get(number)

        if entry is None:
            if len(paths) == 1:
                diff.auto_approved.append(
                    AutoApproved(number=number, file=FileEntry.from_path(paths[0]))
                )
            else:
                suggestion = classify_group(analyze_candidate_group(paths))
                diff.new_duplicate.append(
                    NewDuplicateGroup(number=number, files=list(paths), suggestion=suggestion)
                )
            continue

        scanned_by_name = {path.name: path for path in paths}
        approved_names = {f.filename for f in entry.files}
        known_names = approved_names | set(entry.excluded)

        for file_entry in entry.files:
            path = scanned_by_name.get(file_entry.filename)
            if path is None:
                diff.missing.append(
                    MissingFile(number=number, filename=file_entry.filename, manifest_entry=file_entry)
                )
                continue

            current_mtime = mtime_of(path)
            if current_mtime == file_entry.mtime:
                diff.unchanged.append((number, file_entry.filename))
                continue

            current_sha256 = sha256_of(path)
            if current_sha256 == file_entry.sha256:
                diff.unchanged.append((number, file_entry.filename))
            else:
                diff.changed.append(
                    ChangedFile(
                        number=number,
                        filename=file_entry.filename,
                        reason="mtime und sha256 weichen vom Manifest ab",
                        manifest_entry=file_entry,
                        current_mtime=current_mtime,
                        current_sha256=current_sha256,
                    )
                )

        for name, path in scanned_by_name.items():
            if name not in known_names:
                diff.changed.append(
                    ChangedFile(
                        number=number,
                        filename=name,
                        reason="unerwartete zusaetzliche Datei (weder approved noch excluded im Manifest)",
                        manifest_entry=None,
                        current_mtime=mtime_of(path),
                        current_sha256=None,
                    )
                )

    return diff


def apply_auto_approved(manifest: Manifest, diff: ScanDiff) -> Manifest:
    """A new manifest dict with diff.auto_approved written in as
    "approved" entries - changed/new_duplicate/missing are left completely
    untouched, since those need a manual `approve` decision."""
    updated = dict(manifest)
    for item in diff.auto_approved:
        updated[item.number] = ManifestEntry(status="approved", files=[item.file])
    return updated
