"""Command-line entry point for image_translate_cli (see CLI.md for the
full documented contract).

    python -m image_translate_cli.cli check --config config.json
    python -m image_translate_cli.cli translate --config config.json \\
        --input img1.png img2.png --output-dir ./translated \\
        [--report report.json] [--dry-run] [--yes]
    python -m image_translate_cli.cli translate --config config.json \\
        --input-dir ./screenshots --output-dir ./translated
    python -m image_translate_cli.cli correct \\
        --source original.png --regions edited_regions.json \\
        --output corrected.png [--inpainting-backend box_overlay]

Three subcommands. `check` and `translate` mirror the "check availability
before spending a real run" pattern already used throughout this project
(ui/analysis.py, ico_translate/cli.py's --dry-run) - `check` costs nothing
(no OCR, no provider call) and lets a caller like TME preflight a config
(right provider credentials configured, chosen OCR/inpainting backend
actually available) before it commits to a `translate` run.

`correct` (22.08.2026, Michael: "Ich schicke ein Bild in die CLI, bekomme
eine Vorschau um etwaige Korrekturen zu machen und bekomme dann ein
übersetztes Bild zurück") is the headless counterpart of
ui/image_job.py::run_image_correction_job() / ui/image_correction_dialog.py
- `translate`'s report already includes every region's editable state
(see image_translate_cli/report.py::RegionRecord), a caller edits
`translated_text` (and optionally geometry) in its own UI, and `correct`
re-renders from that against the PRISTINE source - no OCR, no provider
call, no cost. This is what lets ANY calling app support correction
without reimplementing the re-render mechanism itself; the actual editing
UI (a table, a canvas, a chat flow) stays the calling app's own concern.

`review` (22.08.2026, Michael: "Ich möchte aber gerne die Korrektur Logik
mit UI auslagern. Ansonsten muss jede App das gleiche nochmal bauen.") goes
one step further than `correct`: it ALSO ships the editing UI itself, as a
local browser page (see review_server.py), instead of leaving even that to
every calling app. `review` takes the same `--regions` input `correct`
does, opens a browser tab to edit it interactively, and re-renders via the
exact same path once the human clicks "Anwenden" - so a caller that wants
zero UI of its own can use `review`, while a caller with its own editing
UI (e.g. a table in its own app) still has `correct` available.

Bildpfad(e) + Config rein, übersetzte Bilder + JSON-Report raus - exactly
the contract Backlog.md's "Cross-Projekt: Bildübersetzung als Basis für
TME" entry (21.08.2026) sketched, now concrete.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from pipeline.images.inpainting import InpaintingError
from pipeline.images.ocr import OcrError
from pipeline.images.translate_image import translate_image
from pipeline.registry import (
    build_inpainting_backend,
    build_ocr_engine,
    build_provider,
    get_provider_spec,
    inpainting_backend_available,
    ocr_engine_available,
    provider_credential_status,
)
from pipeline.translation.base import TranslationError
from pipeline.translation.cost_control import TranslationBudgetGuard

from image_translate_cli.config import ConfigError, ImageTranslateConfig, load_config
from image_translate_cli.regions_io import RegionsError, load_regions_file
from image_translate_cli.report import (
    ImageResult,
    build_correction_report,
    build_report,
    regions_from_replacements,
)
from image_translate_cli.review_server import run_review_session

# Provider name/pricing/credential-check all come from
# pipeline.registry.PROVIDER_REGISTRY now (22.08.2026, Michael: "für die
# Zukunft offen und dynamisch behalten") - this module no longer keeps its
# own copy of that mapping, so a future provider registered there (see
# that module's docstring) needs NO change here at all.

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".tif", ".tiff", ".webp"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _collect_inputs(args: argparse.Namespace) -> list[Path]:
    if args.input_dir:
        directory = Path(args.input_dir)
        return sorted(
            p for p in directory.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS
        )
    return [Path(p) for p in args.input]


def _dest_for(input_path: Path, output_dir: Path, taken: set[Path]) -> Path:
    """Same basename as `input_path`, inside `output_dir`; a numeric
    suffix is appended if that name was already used earlier IN THIS RUN
    (`taken`) - e.g. two --input paths from different directories sharing
    a basename. Existing files in `output_dir` from a PREVIOUS run are
    deliberately not checked/avoided: re-running `translate` with the same
    --output-dir is expected to overwrite that run's own prior output.
    """
    candidate = output_dir / input_path.name
    if candidate not in taken:
        return candidate
    stem, suffix = input_path.stem, input_path.suffix
    counter = 2
    while True:
        candidate = output_dir / f"{stem} ({counter}){suffix}"
        if candidate not in taken:
            return candidate
        counter += 1


def _cmd_check(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    ok = True

    creds_ok, creds_detail = provider_credential_status(config.provider)
    print(f"provider {config.provider}: {'OK' if creds_ok else 'FEHLT'}")
    if not creds_ok:
        print(f"  {creds_detail}")
        ok = False

    ocr_ok = ocr_engine_available(config.ocr.backend)
    print(f"ocr.backend {config.ocr.backend}: {'OK' if ocr_ok else 'NICHT VERFÜGBAR'}")
    ok = ok and ocr_ok

    inpainting_ok = inpainting_backend_available(config.inpainting.backend)
    print(
        f"inpainting.backend {config.inpainting.backend}: "
        f"{'OK' if inpainting_ok else 'NICHT VERFÜGBAR'}"
    )
    ok = ok and inpainting_ok

    return 0 if ok else 1


def _dry_run_estimate(config: ImageTranslateConfig, inputs: list[Path]) -> tuple[int, float]:
    """OCR every input (no translation, no inpainting - nothing is
    written, no provider call happens) and estimate the combined char
    count/cost via the same TranslationBudgetGuard.estimate_run() the real
    run's budget check uses. A CONSERVATIVE OVER-estimate: unlike the real
    run, this counts every region above ocr.min_confidence without also
    applying the height-ratio outlier filter (translate_image.py's
    _max_plausible_height(), a private helper not part of this module's
    stable surface) - see CLI.md's "Dry-Run" section.
    """
    ocr_engine = build_ocr_engine(config.ocr.backend)
    provider = build_provider(config.provider)
    pricing = get_provider_spec(config.provider).pricing
    guard = TranslationBudgetGuard(provider, pricing, max_chars_per_run=config.budget.max_chars_per_run)

    texts: list[str] = []
    for input_path in inputs:
        regions = ocr_engine.recognize(str(input_path), language=config.ocr.language)
        texts.extend(r.text for r in regions if r.confidence >= config.ocr.min_confidence)
    return guard.estimate_run(texts)


def _cmd_translate(args: argparse.Namespace) -> int:
    try:
        config = load_config(args.config)
    except ConfigError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    inputs = _collect_inputs(args)
    if not inputs:
        print("FEHLER: keine Eingabebilder gefunden (--input/--input-dir).", file=sys.stderr)
        return 2
    missing = [p for p in inputs if not p.is_file()]
    if missing:
        print(f"FEHLER: Datei(en) nicht gefunden: {', '.join(str(p) for p in missing)}", file=sys.stderr)
        return 2

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    if args.dry_run:
        char_count, cost = _dry_run_estimate(config, inputs)
        print(f"[dry-run] {len(inputs)} Bild(er), geschätzte Zeichen: {char_count:,}")
        print(f"[dry-run] geschätzte Kosten: ${cost:.4f}")
        print("[dry-run] keine Übersetzung durchgeführt.")
        return 0

    confirm_callback = (lambda message: True) if (args.yes or not config.budget.confirm) else None
    provider = TranslationBudgetGuard(
        build_provider(config.provider),
        get_provider_spec(config.provider).pricing,
        max_chars_per_run=config.budget.max_chars_per_run,
        confirm_callback=confirm_callback,
    )

    started_at = _now_iso()
    start_time = time.monotonic()
    results: list[ImageResult] = []
    taken_destinations: set[Path] = set()

    for input_path in inputs:
        destination = _dest_for(input_path, output_dir, taken_destinations)
        taken_destinations.add(destination)
        ocr_engine = build_ocr_engine(config.ocr.backend)
        inpainting_backend = build_inpainting_backend(config.inpainting.backend)
        try:
            stats = translate_image(
                source_path=str(input_path),
                destination_path=str(destination),
                ocr_engine=ocr_engine,
                inpainting_backend=inpainting_backend,
                provider=provider,
                protected_terms=config.protected_terms,
                target_lang=config.target_lang,
                source_lang=config.source_lang,
                ocr_language=config.ocr.language,
                min_confidence=config.ocr.min_confidence,
                max_height_ratio=config.ocr.max_height_ratio,
            )
        except (OcrError, InpaintingError, TranslationError) as exc:
            # Mirrors translate_image()'s own "one bad region doesn't
            # abort the image" policy, one level up: one bad IMAGE (OCR
            # couldn't even start, or the final inpainting write failed)
            # doesn't abort the batch - recorded as status "failed" and
            # the loop moves on to the next input.
            print(f"{input_path}: FEHLER ({exc})", file=sys.stderr)
            results.append(
                ImageResult(input=str(input_path), output=None, status="failed", error=str(exc))
            )
            continue

        status = "cancelled" if stats.cancelled else "ok"
        print(f"{input_path} -> {destination} ({status}, {stats.translated} übersetzt)")
        results.append(
            ImageResult(
                input=str(input_path),
                output=str(destination),
                status=status,
                translated=stats.translated,
                skipped=stats.skipped,
                failed=stats.failed,
                chars_sent=stats.chars_sent,
                errors=list(stats.errors),
                regions=regions_from_replacements(stats.replacements),
            )
        )

    finished_at = _now_iso()
    elapsed_seconds = time.monotonic() - start_time
    report = build_report(
        config=config,
        results=results,
        started_at=started_at,
        finished_at=finished_at,
        elapsed_seconds=elapsed_seconds,
        estimated_cost_usd=None,
    )
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        Path(args.report).write_text(report_json + "\n", encoding="utf-8")
        print(f"Report geschrieben nach {args.report}")
    else:
        print(report_json)

    return 1 if any(r.status == "failed" for r in results) else 0


def _cmd_correct(args: argparse.Namespace) -> int:
    """Re-render `--source` with the (possibly edited) regions from
    `--regions` - no OCR, no provider call, no cost. See this module's
    docstring and CLI.md's "correct" section for the full workflow this is
    one half of (`translate` produces the editable state, a caller's own
    UI edits it, this re-renders it).
    """
    source = Path(args.source)
    if not source.is_file():
        print(f"FEHLER: Quelldatei nicht gefunden: {source}", file=sys.stderr)
        return 2

    try:
        replacements = load_regions_file(args.regions)
    except RegionsError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    destination = Path(args.output)
    if destination.resolve() == source.resolve():
        print("FEHLER: --output darf nicht mit --source identisch sein.", file=sys.stderr)
        return 2

    try:
        inpainting_backend = build_inpainting_backend(args.inpainting_backend)
    except ValueError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    started_at = _now_iso()
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        inpainting_backend.apply(str(source), replacements, str(destination))
    except InpaintingError as exc:
        print(f"{source}: FEHLER ({exc})", file=sys.stderr)
        result = ImageResult(input=str(source), output=None, status="failed", error=str(exc))
        return_code = 1
    else:
        print(f"{source} -> {destination} ({len(replacements)} Region(en) neu eingefügt)")
        result = ImageResult(
            input=str(source),
            output=str(destination),
            status="ok",
            translated=len(replacements),
            regions=regions_from_replacements(replacements),
        )
        return_code = 0
    finished_at = _now_iso()

    report = build_correction_report(
        result=result,
        inpainting_backend_name=args.inpainting_backend,
        started_at=started_at,
        finished_at=finished_at,
    )
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        Path(args.report).write_text(report_json + "\n", encoding="utf-8")
        print(f"Report geschrieben nach {args.report}")
    else:
        print(report_json)

    return return_code


def _cmd_review(args: argparse.Namespace) -> int:
    """Like `correct`, but the (possibly edited) regions come from a human
    editing them in a local browser tab (see review_server.py) instead of
    an already-edited --regions file prepared by the calling app itself.
    `--regions` here is the STARTING point shown in the browser (typically
    straight from `translate`'s report), not the final result.
    """
    source = Path(args.source)
    if not source.is_file():
        print(f"FEHLER: Quelldatei nicht gefunden: {source}", file=sys.stderr)
        return 2

    try:
        initial_replacements = load_regions_file(args.regions)
    except RegionsError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    destination = Path(args.output)
    if destination.resolve() == source.resolve():
        print("FEHLER: --output darf nicht mit --source identisch sein.", file=sys.stderr)
        return 2

    try:
        inpainting_backend = build_inpainting_backend(args.inpainting_backend)
    except ValueError as exc:
        print(f"FEHLER: {exc}", file=sys.stderr)
        return 2

    started_at = _now_iso()
    outcome, edited = run_review_session(
        source_path=str(source),
        initial_replacements=initial_replacements,
        host=args.host,
        port=args.port,
        open_browser=not args.no_browser,
        timeout_seconds=args.timeout,
    )

    if outcome == "cancel":
        print("Abgebrochen (im Browser).", file=sys.stderr)
        result = ImageResult(input=str(source), output=None, status="cancelled")
        return_code = 3
    elif outcome == "timeout":
        print(f"FEHLER: Zeitüberschreitung ({args.timeout}s) ohne Aktion im Browser.", file=sys.stderr)
        result = ImageResult(
            input=str(source),
            output=None,
            status="failed",
            error="Zeitüberschreitung ohne Anwenden/Abbrechen im Browser.",
        )
        return_code = 1
    else:  # "apply"
        assert edited is not None
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            inpainting_backend.apply(str(source), edited, str(destination))
        except InpaintingError as exc:
            print(f"{source}: FEHLER ({exc})", file=sys.stderr)
            result = ImageResult(input=str(source), output=None, status="failed", error=str(exc))
            return_code = 1
        else:
            print(f"{source} -> {destination} ({len(edited)} Region(en) neu eingefügt)")
            result = ImageResult(
                input=str(source),
                output=str(destination),
                status="ok",
                translated=len(edited),
                regions=regions_from_replacements(edited),
            )
            return_code = 0

    finished_at = _now_iso()
    report = build_correction_report(
        result=result,
        inpainting_backend_name=args.inpainting_backend,
        started_at=started_at,
        finished_at=finished_at,
        command="review",
    )
    report_json = json.dumps(report, indent=2, ensure_ascii=False)
    if args.report:
        Path(args.report).write_text(report_json + "\n", encoding="utf-8")
        print(f"Report geschrieben nach {args.report}")
    else:
        print(report_json)

    return return_code


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="image_translate_cli")
    subparsers = parser.add_subparsers(dest="command", required=True)

    check_parser = subparsers.add_parser(
        "check", help="Provider-Zugangsdaten sowie OCR-/Inpainting-Backend-Verfügbarkeit prüfen, ohne zu übersetzen"
    )
    check_parser.add_argument("--config", required=True, help="Pfad zur Config-JSON-Datei")
    check_parser.set_defaults(func=_cmd_check)

    translate_parser = subparsers.add_parser("translate", help="Bild(er) übersetzen")
    translate_parser.add_argument("--config", required=True, help="Pfad zur Config-JSON-Datei")
    input_group = translate_parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input", nargs="+", help="Ein oder mehrere Bildpfade")
    input_group.add_argument(
        "--input-dir", help="Ordner, dessen Bilddateien (nicht rekursiv) übersetzt werden"
    )
    translate_parser.add_argument("--output-dir", required=True, help="Zielordner für die übersetzten Bilder")
    translate_parser.add_argument(
        "--report", help="JSON-Report in diese Datei schreiben statt auf stdout auszugeben"
    )
    translate_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Nur Zeichen-/Kostenschätzung anzeigen (lokale OCR, kein Provider-Aufruf), nichts übersetzen",
    )
    translate_parser.add_argument(
        "--yes",
        action="store_true",
        help="Kostenbestätigung automatisch erteilen, unabhängig von config.budget.confirm "
        "(für nicht-interaktive Aufrufer wie TME)",
    )
    translate_parser.set_defaults(func=_cmd_translate)

    correct_parser = subparsers.add_parser(
        "correct",
        help="Ein Bild mit (ggf. bearbeiteten) Regionen aus 'translate' neu rendern - kein OCR, kein Provider-Aufruf",
    )
    correct_parser.add_argument(
        "--source", required=True, help="Die PRISTINE Originaldatei (nicht die bereits übersetzte!)"
    )
    correct_parser.add_argument(
        "--regions",
        required=True,
        help="JSON-Datei mit (ggf. bearbeiteten) Regionen - siehe 'translate'-Report results[].regions",
    )
    correct_parser.add_argument("--output", required=True, help="Zieldatei für das neu gerenderte Bild")
    correct_parser.add_argument(
        "--inpainting-backend",
        default="box_overlay",
        help="Rückschreibe-Backend (Default: box_overlay) - siehe 'check' für Verfügbarkeit",
    )
    correct_parser.add_argument(
        "--report", help="JSON-Report in diese Datei schreiben statt auf stdout auszugeben"
    )
    correct_parser.set_defaults(func=_cmd_correct)

    review_parser = subparsers.add_parser(
        "review",
        help="Ein Bild in einer lokalen Browser-Ansicht interaktiv korrigieren und neu rendern",
    )
    review_parser.add_argument(
        "--source", required=True, help="Die PRISTINE Originaldatei (nicht die bereits übersetzte!)"
    )
    review_parser.add_argument(
        "--regions",
        required=True,
        help="JSON-Datei mit den Ausgangs-Regionen (typischerweise aus 'translate' - results[].regions), "
        "die im Browser angezeigt/bearbeitet werden",
    )
    review_parser.add_argument("--output", required=True, help="Zieldatei für das neu gerenderte Bild")
    review_parser.add_argument(
        "--inpainting-backend",
        default="box_overlay",
        help="Rückschreibe-Backend (Default: box_overlay) - siehe 'check' für Verfügbarkeit",
    )
    review_parser.add_argument(
        "--report", help="JSON-Report in diese Datei schreiben statt auf stdout auszugeben"
    )
    review_parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind-Adresse des lokalen Korrektur-Servers (Default: 127.0.0.1, d.h. nur vom selben Rechner "
        "erreichbar - siehe CLI.md, Abschnitt 'review')",
    )
    review_parser.add_argument(
        "--port",
        type=int,
        default=0,
        help="Port des lokalen Korrektur-Servers (Default: 0 = vom Betriebssystem frei vergeben, "
        "die tatsächliche URL wird auf stdout ausgegeben)",
    )
    review_parser.add_argument(
        "--no-browser",
        action="store_true",
        help="Browser nicht automatisch öffnen (nur die URL ausgeben) - z. B. wenn der Aufrufer die "
        "URL selbst in einem eigenen Fenster/WebView öffnen will",
    )
    review_parser.add_argument(
        "--timeout",
        type=float,
        default=1800.0,
        help="Sekunden, die auf 'Anwenden'/'Abbrechen' im Browser gewartet wird, bevor mit Exit-Code 1 "
        "abgebrochen wird (Default: 1800 = 30 Minuten; 0 = unbegrenzt warten)",
    )
    review_parser.set_defaults(func=_cmd_review)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
