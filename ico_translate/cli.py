"""Command-line entry point for ico_translate's manifest tracking (see
manifest.py) and batch translation (see batch.py).

    python -m ico_translate.cli scan
    python -m ico_translate.cli approve <number> <filename...> [--exclude <filename...>] [--note "..."]
    python -m ico_translate.cli translate --target-lang de --provider deepl --output-dir <path>
        [--limit N] [--only NUMMER,NUMMER,...] [--dry-run] [--yes]

All three subcommands default --root to the real ICO Google-Drive folder
and --manifest to ico_translate/source_manifest.json, so day-to-day use
needs no flags at all; both are still overridable for testing against a
smaller throwaway folder/manifest.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from pipeline.translation.cost_control import (
    DEEPL_PRICING,
    GOOGLE_PRICING,
    GROK_PRICING,
    OPENAI_PRICING,
    PricingModel,
    TranslationBudgetGuard,
)
from pipeline.translation.deepl_provider import DeepLProvider
from pipeline.translation.google_provider import GoogleTranslateProvider
from pipeline.translation.grok_provider import GrokProvider
from pipeline.translation.openai_provider import OpenAIProvider

from ico_translate.batch import (
    BATCH_ERROR_LOG_PATH,
    BatchResult,
    collect_translatable_texts,
    run_batch,
    select_documents,
)
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

# name (as used on --provider) -> (provider class, its PricingModel) - the
# "simple string -> class mapping" the task asked for, nothing fancier.
PROVIDERS: dict[str, tuple[type, PricingModel]] = {
    "deepl": (DeepLProvider, DEEPL_PRICING),
    "google": (GoogleTranslateProvider, GOOGLE_PRICING),
    "openai": (OpenAIProvider, OPENAI_PRICING),
    "grok": (GrokProvider, GROK_PRICING),
}


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


def _parse_only(value: str | None) -> set[str] | None:
    if not value:
        return None
    return {part.strip() for part in value.split(",") if part.strip()}


def _print_translate_report(result: BatchResult) -> None:
    print()
    print("=== Kurzreport ===")
    print(
        f"Dokumente: {result.documents_translated} uebersetzt, "
        f"{result.documents_failed} fehlgeschlagen (von {result.documents_planned} geplant)"
    )
    print(
        f"Absaetze:  {result.paragraphs_translated} uebersetzt, "
        f"{result.paragraphs_skipped} uebersprungen, {result.paragraphs_failed} fehlgeschlagen"
    )
    print(f"Gesendete Zeichen: {result.total_chars_sent:,}")
    print(f"Gesamtlaufzeit: {result.elapsed_seconds:.1f}s")
    print(f"Gesamtkosten laut BudgetGuard-Logging: ${result.actual_cost:.4f}")
    if result.errors:
        print(f"\nFehlgeschlagene Dokumente ({len(result.errors)}), siehe auch {BATCH_ERROR_LOG_PATH}:")
        for number, filename, message in result.errors:
            print(f"  {number} {filename!r}: {message}")


def _cmd_translate(args: argparse.Namespace) -> int:
    root = Path(args.root)
    manifest_path = Path(args.manifest)
    output_dir = Path(args.output_dir)

    if args.provider not in PROVIDERS:
        print(
            f"FEHLER: unbekannter Provider {args.provider!r} (bekannt: {', '.join(PROVIDERS)})",
            file=sys.stderr,
        )
        return 1
    provider_cls, pricing = PROVIDERS[args.provider]
    provider = provider_cls()

    only_numbers = _parse_only(args.only)
    confirm_callback = (lambda message: True) if args.yes else None
    guard = TranslationBudgetGuard(provider, pricing, confirm_callback=confirm_callback)

    documents = select_documents(manifest_path, only_numbers=only_numbers, limit=args.limit)
    print(
        f"{len(documents)} Dokument(e) ausgewaehlt (Provider: {provider.model_name}, "
        f"Zielsprache: {args.target_lang})."
    )
    if not documents:
        return 0

    if args.dry_run:
        char_count, cost = guard.estimate_run(collect_translatable_texts(root, documents))
        print(f"[dry-run] geschaetzte Zeichen: {char_count:,}")
        print(f"[dry-run] geschaetzte Kosten: ${cost:.4f}")
        print("[dry-run] keine Uebersetzung durchgefuehrt.")
        return 0

    result = run_batch(
        manifest_path=manifest_path,
        source_folder=root,
        output_dir=output_dir,
        provider=provider,
        target_lang=args.target_lang,
        budget_guard=guard,
        limit=args.limit,
        only_numbers=only_numbers,
    )

    if result.aborted:
        print("Lauf abgebrochen: Kostenschaetzung nicht bestaetigt (siehe --yes fuer nicht-interaktive Laeufe).")
        return 1

    _print_translate_report(result)
    return 1 if result.documents_failed else 0


def build_parser() -> argparse.ArgumentParser:
    # --root/--manifest are defined TWICE on purpose: once with real
    # defaults (`common_top`, used only on the top-level parser) and once
    # with default=SUPPRESS (`common_sub`, used on every subparser) - so
    # both "ico_translate --root X scan" and "ico_translate scan --root X"
    # work. argparse's subparsers action parses the subcommand's own args
    # into a FRESH namespace and then unconditionally copies every one of
    # its attributes onto the outer namespace, including untouched
    # defaults - with a plain (non-SUPPRESS) default on both parsers,
    # that silently clobbers a --root given BEFORE the subcommand back to
    # the subparser's own default. SUPPRESS on the subparser copy means
    # "not given here" leaves no attribute at all, so the outer value
    # survives untouched whenever the subcommand doesn't repeat the flag.
    common_top = argparse.ArgumentParser(add_help=False)
    common_top.add_argument("--root", default=str(DEFAULT_ROOT), help="ICO-Ordner (Google-Drive-Pfad)")
    common_top.add_argument("--manifest", default=str(DEFAULT_MANIFEST), help="Pfad zur Manifest-JSON-Datei")

    common_sub = argparse.ArgumentParser(add_help=False)
    common_sub.add_argument("--root", default=argparse.SUPPRESS, help="ICO-Ordner (Google-Drive-Pfad)")
    common_sub.add_argument("--manifest", default=argparse.SUPPRESS, help="Pfad zur Manifest-JSON-Datei")

    parser = argparse.ArgumentParser(prog="ico_translate", parents=[common_top])
    subparsers = parser.add_subparsers(dest="command", required=True)

    scan_parser = subparsers.add_parser(
        "scan", parents=[common_sub], help="Ordner scannen, Manifest abgleichen und auto_approved-Faelle uebernehmen"
    )
    scan_parser.add_argument(
        "--report", help="Unstimmigkeiten-Bericht in diese Datei schreiben statt auf die Konsole auszugeben"
    )
    scan_parser.set_defaults(func=_cmd_scan)

    approve_parser = subparsers.add_parser(
        "approve", parents=[common_sub], help="Datei(en) fuer eine Dokumentnummer manuell als approved eintragen"
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

    translate_parser = subparsers.add_parser(
        "translate", parents=[common_sub], help="Alle (oder eine Teilmenge der) approved Manifest-Dokumente uebersetzen"
    )
    translate_parser.add_argument("--target-lang", required=True, help="Zielsprachcode, z.B. de")
    translate_parser.add_argument(
        "--provider", required=True, choices=sorted(PROVIDERS), help="Uebersetzungs-Provider"
    )
    translate_parser.add_argument("--output-dir", required=True, help="Zielordner fuer die uebersetzten .docx")
    translate_parser.add_argument("--limit", type=int, help="Nur die ersten N ausgewaehlten Dokumente verarbeiten")
    translate_parser.add_argument(
        "--only", help="Nur diese Dokumentnummer(n), kommagetrennt (z.B. 1440,1868)"
    )
    translate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur Kostenschaetzung + Dokumentanzahl anzeigen, nichts uebersetzen",
    )
    translate_parser.add_argument(
        "--yes",
        action="store_true",
        help="Kostenschaetzung automatisch bestaetigen statt interaktiv nachzufragen "
        "(fuer nicht-interaktive/automatisierte Laeufe)",
    )
    translate_parser.set_defaults(func=_cmd_translate)

    return parser


def main(argv: list[str] | None = None) -> int:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
