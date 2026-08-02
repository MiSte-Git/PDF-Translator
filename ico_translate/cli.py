"""Command-line entry point for ico_translate's manifest tracking (see
manifest.py for the actual scan/diff logic).

    python -m ico_translate.cli scan
    python -m ico_translate.cli approve <number> <filename...> [--exclude <filename...>] [--note "..."]

Both subcommands default --root to the real ICO Google-Drive folder and
--manifest to ico_translate/source_manifest.json, so day-to-day use needs
no flags at all; both are still overridable for testing against a smaller
throwaway folder.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ico_translate.manifest import (
    ChangedFile,
    FileEntry,
    ManifestEntry,
    MissingFile,
    NewDuplicateGroup,
    ScanDiff,
    apply_auto_approved,
    diff_against_manifest,
    load_manifest,
    save_manifest,
    scan_folder,
)

DEFAULT_ROOT = Path(r"G:\.shortcut-targets-by-id\1IGMZBUMVcTHj4z9wsDrSRb6xzdS0klPn\ICO PDFs")
DEFAULT_MANIFEST = Path(__file__).resolve().parent / "source_manifest.json"


def _format_issue_report(diff: ScanDiff) -> str:
    lines: list[str] = []

    if diff.changed:
        lines.append(f"=== changed ({len(diff.changed)}) ===")
        for item in diff.changed:
            lines.append(f"  Nummer {item.number}, Datei {item.filename!r}: {item.reason}")
            if item.manifest_entry is not None:
                lines.append(
                    f"    Manifest:  mtime={item.manifest_entry.mtime} sha256={item.manifest_entry.sha256}"
                )
            lines.append(f"    Aktuell:   mtime={item.current_mtime} sha256={item.current_sha256}")
        lines.append("")

    if diff.new_duplicate:
        lines.append(f"=== new_duplicate ({len(diff.new_duplicate)}) ===")
        for group in diff.new_duplicate:
            lines.append(
                f"  Nummer {group.number} ({len(group.files)} Dateien) - "
                f"Einschaetzung (classify_group): {group.suggestion}"
            )
            for path in group.files:
                lines.append(f"    {path.name}")
        lines.append("")

    if diff.missing:
        lines.append(f"=== missing ({len(diff.missing)}) ===")
        for item in diff.missing:
            lines.append(
                f"  Nummer {item.number}, Datei {item.filename!r} steht im Manifest, "
                "ist im Ordner nicht mehr auffindbar"
            )
        lines.append("")

    return "\n".join(lines).rstrip("\n")


def _cmd_scan(args: argparse.Namespace) -> int:
    root = Path(args.root)
    manifest_path = Path(args.manifest)

    manifest = load_manifest(manifest_path)
    scan_result = scan_folder(root)
    diff = diff_against_manifest(scan_result, manifest)

    if diff.auto_approved:
        save_manifest(manifest_path, apply_auto_approved(manifest, diff))

    print(f"Scan von {root}")
    print(f"Manifest: {manifest_path}")
    print(f"  auto_approved: {len(diff.auto_approved)}")
    print(f"  unchanged:     {len(diff.unchanged)}")
    print(f"  changed:       {len(diff.changed)}")
    print(f"  new_duplicate: {len(diff.new_duplicate)}")
    print(f"  missing:       {len(diff.missing)}")

    if not diff.has_issues():
        print("\nKeine Unstimmigkeiten.")
        return 0

    report = _format_issue_report(diff)
    if args.report:
        report_path = Path(args.report)
        report_path.write_text(report + "\n", encoding="utf-8")
        print(f"\nUnstimmigkeiten-Bericht geschrieben nach {report_path}")
    else:
        print()
        print(report)

    return 1


def _cmd_approve(args: argparse.Namespace) -> int:
    root = Path(args.root)
    manifest_path = Path(args.manifest)
    manifest = load_manifest(manifest_path)

    files: list[FileEntry] = []
    for filename in args.filenames:
        path = root / filename
        if not path.exists():
            print(f"FEHLER: Datei nicht gefunden: {path}", file=sys.stderr)
            return 1
        files.append(FileEntry.from_path(path))

    excluded = list(args.exclude or [])
    for filename in excluded:
        if not (root / filename).exists():
            print(f"WARNUNG: excluded-Datei nicht im Ordner gefunden: {root / filename}", file=sys.stderr)

    manifest[args.number] = ManifestEntry(
        status="approved", files=files, excluded=excluded, note=args.note or ""
    )
    save_manifest(manifest_path, manifest)

    summary = f"Nummer {args.number}: {len(files)} Datei(en) als approved eingetragen"
    if excluded:
        summary += f", {len(excluded)} excluded"
    print(summary + ".")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ico_translate")
    parser.add_argument("--root", default=str(DEFAULT_ROOT), help="ICO-Ordner (Google-Drive-Pfad)")
    parser.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Pfad zur Manifest-JSON-Datei")

    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan", help="Ordner scannen, Manifest abgleichen und auto_approved-Faelle uebernehmen"
    )
    scan_parser.add_argument(
        "--report", help="Unstimmigkeiten-Bericht in diese Datei schreiben statt auf die Konsole auszugeben"
    )
    scan_parser.set_defaults(func=_cmd_scan)

    approve_parser = subparsers.add_parser(
        "approve", help="Datei(en) fuer eine Dokumentnummer manuell als approved eintragen"
    )
    approve_parser.add_argument("number", help="Dokumentnummer")
    approve_parser.add_argument("filenames", nargs="+", help="Dateiname(n), die als approved gelten")
    approve_parser.add_argument(
        "--exclude",
        nargs="+",
        help="Dateiname(n) unter derselben Nummer, die bewusst NICHT approved werden "
        "(z.B. eine unterlegene (LS)-Variante)",
    )
    approve_parser.add_argument("--note", help="Freitext-Notiz zur Entscheidung")
    approve_parser.set_defaults(func=_cmd_approve)

    return parser


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
