"""Config file schema for image_translate_cli (see CLI.md for the full
documented contract this mirrors in code).

Deliberately a JSON *file* passed via --config, not a long flat list of CLI
flags (unlike ico_translate/cli.py's `translate` subcommand): a caller like
TME builds/stores this once per use case (e.g. "translate a Telegram
export's images to German via DeepL") and then invokes the CLI the same way
every time, with only the input files and output directory changing per
call - and the file is what gets versioned (CONFIG_SCHEMA_VERSION) so a
future incompatible change can be detected instead of silently
misinterpreted.

Never contains credentials (API keys): resolved the same way the rest of
this project already resolves them (pipeline.credentials - environment
variables, then the OS keyring), so a config file is safe to commit, log,
or hand to another program without redacting anything - directly serving
Backlog.md Phase 7's "Keine Schlüsselwerte in UI, Logs, Reports oder
Fehlermeldungen ausgeben" principle, extended to config files too.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.images.translate_image import DEFAULT_MAX_HEIGHT_RATIO, DEFAULT_MIN_OCR_CONFIDENCE
from pipeline.registry import INPAINTING_BACKEND_FACTORIES, OCR_ENGINE_FACTORIES, PROVIDER_FACTORIES
from pipeline.translation.cost_control import DEFAULT_MAX_CHARS_PER_RUN

# Bumped whenever a change to this schema could change how an EXISTING
# config file is interpreted (a field's meaning/default changes, a field is
# removed, a previously-optional field becomes required). Adding a new
# optional field with a backward-compatible default does NOT need a bump -
# mirrors CLI.md's own versioning policy, see that file's "Versionierung"
# section.
CONFIG_SCHEMA_VERSION = 1


class ConfigError(ValueError):
    """Raised for any problem with a config file: missing/unreadable file,
    invalid JSON, unknown/unsupported schema_version, a missing required
    field, or a value outside its allowed choices (e.g. an unknown
    provider name). Always includes enough detail (field name + the
    invalid value) to fix the file without needing to read this module -
    see CLI.md's "Fehlerbehandlung" section for the exit-code contract
    built on top of this.
    """


@dataclass
class OcrConfig:
    backend: str = "tesseract"
    """One of pipeline.registry.OCR_ENGINE_FACTORIES's keys."""
    language: str | None = None
    """Engine-specific language hint (Tesseract: 3-letter code, e.g. "eng"
    or "deu"). None lets the engine fall back to its own default - see
    pipeline.images.ocr.OcrEngine.recognize()."""
    min_confidence: float = DEFAULT_MIN_OCR_CONFIDENCE
    max_height_ratio: float = DEFAULT_MAX_HEIGHT_RATIO


@dataclass
class InpaintingConfig:
    backend: str = "box_overlay"
    """One of pipeline.registry.INPAINTING_BACKEND_FACTORIES's keys."""


@dataclass
class BudgetConfig:
    max_chars_per_run: int = DEFAULT_MAX_CHARS_PER_RUN
    confirm: bool = True
    """Whether an interactive y/n cost confirmation is required before
    translating (mirrors ico_translate/cli.py's --yes flag, which is the
    CLI-level override for this: passing --yes on the command line forces
    this to False for that one invocation regardless of what the config
    file says, for non-interactive/automated callers like TME)."""


@dataclass
class ImageTranslateConfig:
    provider: str
    """One of pipeline.registry.PROVIDER_FACTORIES's keys."""
    target_lang: str
    source_lang: str | None = None
    protected_terms: list[str] = field(default_factory=list)
    ocr: OcrConfig = field(default_factory=OcrConfig)
    inpainting: InpaintingConfig = field(default_factory=InpaintingConfig)
    budget: BudgetConfig = field(default_factory=BudgetConfig)


def _require(data: dict, key: str, context: str) -> object:
    if key not in data:
        raise ConfigError(f"{context}: Pflichtfeld {key!r} fehlt")
    return data[key]


def _check_choice(value: str, allowed: dict, field_name: str) -> str:
    if value not in allowed:
        raise ConfigError(
            f"{field_name}: unbekannter Wert {value!r} (erlaubt: {', '.join(sorted(allowed))})"
        )
    return value


def load_config(path: str | Path) -> ImageTranslateConfig:
    """Read and validate a config file. Raises ConfigError with a message
    identifying the exact problem (never a bare KeyError/JSONDecodeError) -
    see CLI.md's "Fehlerbehandlung" for how the `translate`/`check`
    commands turn this into an exit code.
    """
    path = Path(path)
    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise ConfigError(f"Config-Datei konnte nicht gelesen werden: {path} ({exc})") from exc

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Config-Datei ist kein gültiges JSON: {path} ({exc})") from exc

    if not isinstance(data, dict):
        raise ConfigError(f"Config-Datei muss ein JSON-Objekt sein, nicht {type(data).__name__}: {path}")

    schema_version = _require(data, "schema_version", "Config")
    if schema_version != CONFIG_SCHEMA_VERSION:
        raise ConfigError(
            f"Config schema_version {schema_version!r} wird nicht unterstützt "
            f"(erwartet: {CONFIG_SCHEMA_VERSION}). Siehe CLI.md, Abschnitt "
            "\"Versionierung\"."
        )

    provider = _check_choice(str(_require(data, "provider", "Config")), PROVIDER_FACTORIES, "provider")
    target_lang = str(_require(data, "target_lang", "Config"))
    source_lang = data.get("source_lang")
    protected_terms = list(data.get("protected_terms", []))

    ocr_data = data.get("ocr", {})
    ocr = OcrConfig(
        backend=_check_choice(
            str(ocr_data.get("backend", "tesseract")), OCR_ENGINE_FACTORIES, "ocr.backend"
        ),
        language=ocr_data.get("language"),
        min_confidence=float(ocr_data.get("min_confidence", DEFAULT_MIN_OCR_CONFIDENCE)),
        max_height_ratio=float(ocr_data.get("max_height_ratio", DEFAULT_MAX_HEIGHT_RATIO)),
    )

    inpainting_data = data.get("inpainting", {})
    inpainting = InpaintingConfig(
        backend=_check_choice(
            str(inpainting_data.get("backend", "box_overlay")),
            INPAINTING_BACKEND_FACTORIES,
            "inpainting.backend",
        )
    )

    budget_data = data.get("budget", {})
    budget = BudgetConfig(
        max_chars_per_run=int(budget_data.get("max_chars_per_run", DEFAULT_MAX_CHARS_PER_RUN)),
        confirm=bool(budget_data.get("confirm", True)),
    )

    return ImageTranslateConfig(
        provider=provider,
        target_lang=target_lang,
        source_lang=source_lang,
        protected_terms=protected_terms,
        ocr=ocr,
        inpainting=inpainting,
        budget=budget,
    )


def config_to_dict(config: ImageTranslateConfig) -> dict:
    """Serialize `config` back to a plain dict, e.g. for echoing the
    RESOLVED configuration (explicit defaults filled in) into a run's JSON
    report (see report.py) - safe to include as-is since a config never
    contains credentials (see this module's docstring).
    """
    return {
        "schema_version": CONFIG_SCHEMA_VERSION,
        "provider": config.provider,
        "target_lang": config.target_lang,
        "source_lang": config.source_lang,
        "protected_terms": list(config.protected_terms),
        "ocr": {
            "backend": config.ocr.backend,
            "language": config.ocr.language,
            "min_confidence": config.ocr.min_confidence,
            "max_height_ratio": config.ocr.max_height_ratio,
        },
        "inpainting": {"backend": config.inpainting.backend},
        "budget": {
            "max_chars_per_run": config.budget.max_chars_per_run,
            "confirm": config.budget.confirm,
        },
    }
