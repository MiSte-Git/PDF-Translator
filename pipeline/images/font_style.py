"""Font-Stil-Erkennung (Familie, Fett, Kursiv) für das Rückschreiben
übersetzter Bildtexte (RoadMap.md Phase 3: "Textregionen, Leserichtung,
Schrift, Farbe und Hintergrund erfassen - ... echte Schrifterkennung
(Font-Matching) weiterhin offen").

Hintergrund (22.08.2026, Michael, nach einem Google-Translate-Bildvergleich
mit einer eigenen Test-Infografik): unsere Rückschreibung landete bei rund
60-70% Layout-Genauigkeit gegenüber Googles sichtbar saubererem Ergebnis -
der auffälligste Einzelfaktor war, dass jede Übersetzung IMMER in
DejaVuSans Regular gerendert wurde, unabhängig vom tatsächlichen
Original-Schriftbild (Serif/Sans-Serif, kursiv). Michael entschied sich
explizit für klassische Bildverarbeitung statt eines trainierten
Font-Klassifikators ("gleich richtig machen, wenn es nicht zwingend den
pragmatischen Weg vorher braucht" + klassische Bildverarbeitung statt
ML-Modell) - keine neue Modell-Abhängigkeit, läuft überall, sofort
einsatzbereit, dafür auf Kategorie-Ebene (Serif/Sans-Serif, Fett, Kursiv)
begrenzt statt echter Font-FAMILIEN-Erkennung ("Arial" vs. "Helvetica" ist
damit nicht unterscheidbar - optisch ohnehin kaum ein Unterschied).
Monospace-Erkennung ist bewusst NICHT Teil dieser Runde (bräuchte
zeichenweise Segmentierung für eine verlässliche Breiten-Gleichmäßigkeits-
Messung, die project-eigene Zeilen-Erkennung liefert nur Zeilen- keine
Zeichen-Boxen) - dokumentiert als offener Folgepunkt in Backlog.md, nicht
stillschweigend als "erledigt" behandelt.

Methodik: bewusst dieselbe RELATIVE Vergleichs-Strategie, die
pipeline.images.inpainting._estimate_is_bold() (21.08.2026) für die
Fett-Erkennung eingeführt hat, jetzt konsistent auf alle drei Stil-Achsen
angewendet - ein ABSOLUTER Schwellwert (z. B. "Serif, wenn Score > X")
würde auf einem realen, verrauschten JPEG/Screenshot nicht zuverlässig
über verschiedene Bilder hinweg funktionieren (dieselbe Lektion, die schon
_estimate_is_bold()s Docstring für Fett-Erkennung festhält). Stattdessen:
denselben Vergleichstext synthetisch in den JEWEILS in Frage kommenden
Varianten rendern (z. B. Sans vs. Serif, beide Regular), an beiden
dieselbe Kennzahl messen, und die reale Region der Variante zuordnen,
deren synthetischer Wert numerisch näher am beobachteten Wert liegt -
robust gegenüber Bild-zu-Bild-Rauschen, weil nur die REIHENFOLGE der
beiden Vergleichswerte zählt, nicht ihr Absolutwert.

Exploratorische Heuristik, keine Garantie (mirrors _estimate_is_bold()s
eigene Einordnung) - ein ungewöhnliches Original-Schriftbild, eine stark
strukturierte/photografische Umgebung oder sehr kurzer Text (wenige
Ink-Pixel, wenig Signal) können weiterhin zu einer falschen Einschätzung
führen. Kein Font-Datenbank-Abgleich, keine Zeichenerkennung jenseits der
bereits vorhandenen OCR.

Bekannte Grenze, bewusst nicht "wegoptimiert" (22.08.2026, nach einer
breiten synthetischen Text/Größe/Stil-Matrix zusätzlich zu den echten
pytest-Fällen): alle drei classify_*()-Funktionen rendern ihre
synthetischen Referenzen bei der vom Aufrufer übergebenen `size` -
üblicherweise pipeline.images.inpainting._initial_font_size(region), nur
eine grobe `region.height * 0.8`-Schätzung. Weicht diese Schätzung um
mehrere Pixel von der tatsächlichen Original-Schriftgröße ab (bei realen
OCR-Boxen abhängig von Auf-/Unterlängen im jeweiligen Text durchaus
üblich), sinkt die Trefferquote spürbar - in dieser Matrix bei exakt
passender Größe 100%, bei realistisch abweichender Schätzung nur rund
60-65% je Achse. Ein Kalibrierungsversuch (Referenzgröße anhand der
beobachteten Tinten-Höhe nachjustieren) wurde gebaut und wieder verworfen:
er verbesserte Familie geringfügig, verschlechterte Kursiv-Erkennung aber
messbar und blieb in Summe kein klarer Gewinn - siehe git-Historie dieser
Datei, falls das erneut aufgegriffen werden soll. Für jetzt: dokumentierte
Grenze statt stillschweigender Präzisionsannahme, konsistent mit der
Exploratorische-Heuristik-Einordnung oben.
"""
from __future__ import annotations

from dataclasses import dataclass

from pipeline.images.ocr import OcrTextRegion

# Debian/Ubuntu-Pfad (fonts-dejavu-core) - VERIFIZIERT, siehe
# pipeline/images/inpainting.py's ursprüngliche _FALLBACK_FONT_PATHS
# (18.08.2026) und die Cloud-Sandbox dieser Session. Die übrigen Einträge
# sind unverifizierte Best-Effort-Kandidaten für andere Distributionen -
# load_font() fällt ohnehin auf Pillows eingebauten Default-Font zurück,
# wenn KEINER der Kandidaten existiert (siehe dessen Docstring), also kein
# Absturzrisiko, falls diese zusätzlichen Pfade auf einem realen Zielsystem
# nicht stimmen sollten.
_FONT_DIRS = (
    "/usr/share/fonts/truetype/dejavu",  # Debian/Ubuntu - verifiziert
    "/usr/share/fonts/dejavu",  # Fedora/RHEL - unverifiziert
    "/usr/share/fonts/truetype/ttf-dejavu",  # ältere Debian-Varianten - unverifiziert
)

# (family, bold, italic) -> Dateiname. Serif nutzt "Italic" (DejaVus
# eigene Bezeichnung für den echten kursiven Schnitt der Serif-Familie),
# Sans nutzt "Oblique" (DejaVu Sans hat keinen echten kursiven Schnitt,
# nur einen künstlich geneigten) - kosmetisch identisch relevant für unsere
# Zwecke (beide rendern sichtbar geneigten Text), daher hier einheitlich
# über denselben `italic`-Parameter angesprochen.
_FONT_FILENAMES: dict[tuple[str, bool, bool], str] = {
    ("sans_serif", False, False): "DejaVuSans.ttf",
    ("sans_serif", True, False): "DejaVuSans-Bold.ttf",
    ("sans_serif", False, True): "DejaVuSans-Oblique.ttf",
    ("sans_serif", True, True): "DejaVuSans-BoldOblique.ttf",
    ("serif", False, False): "DejaVuSerif.ttf",
    ("serif", True, False): "DejaVuSerif-Bold.ttf",
    ("serif", False, True): "DejaVuSerif-Italic.ttf",
    ("serif", True, True): "DejaVuSerif-BoldItalic.ttf",
}

# Luminance-Differenz zum geschätzten Hintergrund, ab der ein Pixel als
# "Tinte" zählt (siehe _binary_ink_mask() unten) - unverändert von
# pipeline.images.inpainting._INK_LUMINANCE_THRESHOLD (21.08.2026, gegen
# echte JPEG-Regionen kalibriert), hierher verschoben, weil dieses Modul
# jetzt der EINZIGE Ort ist, der Ink-Pixel klassifiziert - inpainting.py
# importiert bei Bedarf von hier zurück, statt eine zweite Kopie zu führen.
_INK_LUMINANCE_THRESHOLD = 40


@dataclass(frozen=True)
class FontStyle:
    """Ergebnis von estimate_font_style() - was `_load_font()`
    (pipeline/images/inpainting.py, jetzt load_font() hier) braucht, um die
    passende DejaVu-Datei zu wählen."""

    family: str  # "sans_serif" oder "serif" - siehe Moduldoc (kein "monospace" in dieser Runde)
    bold: bool
    italic: bool


def _candidate_paths(family: str, bold: bool, italic: bool) -> tuple[str, ...]:
    filename = _FONT_FILENAMES.get((family, bold, italic))
    if filename is None:
        return ()
    return tuple(f"{directory}/{filename}" for directory in _FONT_DIRS)


def load_font(size: int, bold: bool = False, family: str = "sans_serif", italic: bool = False):
    """Load a font at the given PIXEL SIZE. Ersetzt pipeline/images/
    inpainting.py's ursprüngliches _load_font() (18.08.2026, nur
    Regular/Bold DejaVu Sans) - Aufrufer, die weiterhin nur `bold`
    angeben (family/italic auf Default belassen), bekommen exakt dasselbe
    Ergebnis wie vorher (DejaVu Sans, Regular oder Bold).

    Fallback-Kaskade, wenn die exakte (family, bold, italic)-Kombination
    auf diesem System fehlt: erst ohne Kursiv (dieselbe Familie/Stärke,
    Regular-Neigung), dann ohne Fett, dann Sans-Serif Regular, zuletzt
    Pillows eingebauter Default-Font - nie eine Exception, siehe
    pipeline/images/inpainting.py's ursprüngliche Begründung dafür
    (mögliche Standalone-Version ohne bestimmte vorinstallierte Fonts).
    """
    from PIL import ImageFont

    size = max(1, size)
    cascade = [
        (family, bold, italic),
        (family, bold, False),
        (family, False, False),
        ("sans_serif", bold, italic),
        ("sans_serif", bold, False),
        ("sans_serif", False, False),
    ]
    tried: set[tuple[str, bool, bool]] = set()
    for combo in cascade:
        if combo in tried:
            continue
        tried.add(combo)
        for path in _candidate_paths(*combo):
            try:
                return ImageFont.truetype(path, size)
            except OSError:
                continue
    return ImageFont.load_default()


def _binary_ink_mask(
    image, x: int, y: int, width: int, height: int, background: tuple[int, int, int]
) -> list[list[bool]]:
    """2D-Gitter (mask[Zeile][Spalte]), das für jedes Pixel innerhalb der
    Box markiert, ob es als "Tinte" (Teil eines Glyphen-Strichs) statt
    Hintergrund zählt - dieselbe Luminance-Differenz-Regel wie
    pipeline.images.inpainting._ink_ratio() (das jetzt intern auf dieser
    Maske aufbaut, siehe _ink_ratio() unten), aber als vollständiges
    2D-Gitter statt nur einer Verhältniszahl - Familie/Kursiv-Erkennung
    brauchen die tatsächliche Zeilen-/Spalten-VERTEILUNG der Ink-Pixel,
    nicht nur ihren Anteil.
    """
    img_w, img_h = image.size
    x0, y0 = max(0, x), max(0, y)
    x1, y1 = min(img_w, x + width), min(img_h, y + height)
    if x1 <= x0 or y1 <= y0:
        return []
    pixels = image.load()
    bg_luminance = 0.299 * background[0] + 0.587 * background[1] + 0.114 * background[2]
    mask: list[list[bool]] = []
    for py in range(y0, y1):
        row = []
        for px in range(x0, x1):
            r, g, b = pixels[px, py]
            luminance = 0.299 * r + 0.587 * g + 0.114 * b
            row.append(abs(luminance - bg_luminance) > _INK_LUMINANCE_THRESHOLD)
        mask.append(row)
    return mask


def _mask_ink_ratio(mask: list[list[bool]]) -> float:
    """Fraction of True (ink) pixels in `mask`. Shared arithmetic behind
    _ink_ratio()/_synthetic_ink_ratio() below."""
    total = sum(len(row) for row in mask)
    if total == 0:
        return 0.0
    ink = sum(sum(row) for row in mask)
    return ink / total


def _ink_ratio(image, x: int, y: int, width: int, height: int, background: tuple[int, int, int]) -> float:
    """Fraction of pixels classified as ink by _binary_ink_mask() - siehe
    dessen Docstring. Verhält sich identisch zu pipeline.images.
    inpainting._ink_ratio() vor dieser Umstrukturierung (22.08.2026), nur
    jetzt über die geteilte Maske implementiert statt einer eigenen
    Pixel-Schleife."""
    return _mask_ink_ratio(_binary_ink_mask(image, x, y, width, height, background))


def _render_sample_mask(text: str, font) -> list[list[bool]]:
    """Rendert `text` schwarz auf weiß in `font` und liefert dessen
    Ink-Maske - die synthetische Referenz, gegen die eine reale Region
    verglichen wird (siehe Moduldoc). Dieselbe Render-Logik wie
    pipeline.images.inpainting._synthetic_ink_ratio() vor dieser
    Umstrukturierung, nur mit der vollen Maske statt nur dem Ink-Anteil
    als Rückgabe, damit auch Serif-/Kursiv-Kennzahlen (nicht nur der
    Ink-Anteil für Fett) darauf laufen können."""
    from PIL import Image, ImageDraw

    probe = ImageDraw.Draw(Image.new("RGB", (1, 1)))
    bbox = probe.textbbox((0, 0), text, font=font)
    width = max(1, bbox[2] - bbox[0] + 4)
    height = max(1, bbox[3] - bbox[1] + 4)
    sample = Image.new("RGB", (width, height), "white")
    ImageDraw.Draw(sample).text((2, 2), text, fill="black", font=font)
    return _binary_ink_mask(sample, 0, 0, width, height, (255, 255, 255))


def _synthetic_ink_ratio(text: str, font) -> float:
    return _mask_ink_ratio(_render_sample_mask(text, font))


def _trim_to_ink_bbox(mask: list[list[bool]]) -> list[list[bool]]:
    """Crops `mask` to the tight bounding box of its True (ink) pixels -
    removes an OCR bounding box's padding/slack rows and columns before
    _serif_score()/_slant_ratio() run on it, so a REAL region (a loose OCR
    box, with real slack above ascenders and below descenders - Tesseract
    line boxes are not tightly cropped to the glyphs) and a SYNTHETIC
    comparison sample (already tightly cropped via ImageDraw.textbbox() in
    _render_sample_mask()) are compared on the same, padding-free basis.

    Without this, a real region's PADDING rather than its glyph SHAPE
    could dominate these zone-based metrics - found empirically while
    building this module (22.08.2026): a plain DejaVu Sans line was
    misclassified as Serif purely because its OCR box's empty top/bottom
    rows skewed _serif_score()'s edge-zone variance, even though the
    synthetic Sans/Serif reference scores themselves were both computed
    on tightly-cropped samples and barely differed from each other.
    Deliberately NOT applied inside _ink_ratio() - _estimate_is_bold()'s/
    classify_bold()'s existing RELATIVE ink-RATIO comparison already
    tolerates this same padding fine in practice (confirmed by its
    existing, real-image-calibrated tests, unchanged by this function;
    also confirmed the other way round, 22.08.2026 - trimming the
    observed mask there was tried and made both the real bold-detection
    test AND a broader synthetic accuracy check WORSE, not better, so
    that direction was reverted), so trimming there risks disturbing
    already-verified behaviour for no benefit.

    Uses a small RELATIVE noise floor (rather than "any ink pixel at
    all") when deciding which edge rows/columns still count as part of
    the glyph content: found empirically (22.08.2026) that a handful of
    single-digit-pixel-count rows from anti-aliasing at a glyph's very
    edge can appear in a real region but not in its synthetic reference
    (or vice versa) purely from sub-pixel rendering-position differences
    - just a row or two of this noise is enough to shift which rows fall
    into _serif_score()'s edge-vs-middle thirds, or which band
    _slant_ratio() puts them in. A row/column only counts as "real"
    content once its ink count reaches 8% of the strongest row's/
    column's count, which real strokes clear by a wide margin while
    isolated anti-aliasing fringes do not.

    Returns `mask` unchanged if it has no ink pixels at all (nothing to
    trim to - the empty-mask callers above already special-case this).
    """
    row_counts = [sum(row) for row in mask]
    if not any(row_counts):
        return mask
    row_floor = max(1, int(max(row_counts) * 0.08))
    ink_rows = [i for i, count in enumerate(row_counts) if count >= row_floor]
    top, bottom = ink_rows[0], ink_rows[-1]
    cropped_rows = mask[top : bottom + 1]
    col_counts = [sum(row[j] for row in cropped_rows) for j in range(len(cropped_rows[0]))] if cropped_rows[0] else []
    if not any(col_counts):
        return cropped_rows
    col_floor = max(1, int(max(col_counts) * 0.08))
    ink_cols = [j for j, count in enumerate(col_counts) if count >= col_floor]
    left, right = ink_cols[0], ink_cols[-1]
    return [row[left : right + 1] for row in cropped_rows]


def _variance(values: list[float]) -> float:
    if not values:
        return 0.0
    mean = sum(values) / len(values)
    return sum((v - mean) ** 2 for v in values) / len(values)


def _serif_score(mask: list[list[bool]]) -> float:
    """Höher = eher Serif. Serifen (die kleinen horizontalen Füßchen an
    Schaft-Enden) erzeugen in der obersten und untersten Zeilenzone einer
    Textzeile eine ungleichmäßigere Ink-Pixel-Verteilung von Zeile zu
    Zeile als in der mittleren Zone (dort dominiert reine, weitgehend
    konstante Schaftbreite) - gemessen als Verhältnis der Zeilen-Ink-Anzahl-
    VARIANZ am oberen+unteren Rand gegenüber der Varianz in der Mitte.
    Reine Bildverarbeitungs-Kennzahl, kein Abgleich gegen eine Font-
    Datenbank - siehe classify_family() für den relativen Vergleich, der
    daraus eine Serif/Sans-Serif-Entscheidung ableitet, und die Moduldoc
    für die Methodik-Begründung insgesamt. Trimmt zuerst auf die enge
    Ink-Bounding-Box (siehe _trim_to_ink_bbox()) - sonst würde eine reale
    OCR-Box mit viel Leerraum über/unter dem eigentlichen Text die
    Rand-Varianz verzerren."""
    mask = _trim_to_ink_bbox(mask)
    height = len(mask)
    if height < 6:
        return 0.0
    third = max(1, height // 3)
    row_counts = [sum(row) for row in mask]
    edge_rows = row_counts[:third] + row_counts[height - third :]
    mid_rows = row_counts[third : height - third]
    if not edge_rows or not mid_rows:
        return 0.0
    return _variance(edge_rows) / (_variance(mid_rows) + 1e-6)


def _slant_ratio(mask: list[list[bool]]) -> float:
    """Schätzt die systematische Scherung (Kursiv-Neigung) als
    Ink-Spalten-Schwerpunkt-Verschiebung pro Zeilenband, normiert auf die
    Boxbreite: die Maske wird in mehrere horizontale Bänder geteilt, je
    Band der mittlere x-Wert aller Ink-Pixel bestimmt, und die Steigung
    dieser Schwerpunkte über die Bänder per einfacher linearer Regression
    geschätzt. Ein über mehrere Buchstaben hinweg KONSISTENTER Trend
    (nicht nur die zufällige Form eines einzelnen Buchstabens) ist das
    Signal für echte Kursivschrift - siehe classify_italic() für den
    relativen Vergleich und die Moduldoc für die Methodik-Begründung.
    Vorzeichen ist Implementierungsdetail (hängt von der Bildkoordinaten-
    Konvention ab) - classify_italic() vergleicht nur den ABSTAND zu den
    synthetischen Referenzwerten, nicht das Vorzeichen für sich. Trimmt
    zuerst auf die enge Ink-Bounding-Box (siehe _trim_to_ink_bbox()) - aus
    demselben Grund wie _serif_score(): eine reale OCR-Box mit Leerraum
    über/unter dem Text würde sonst die Bänder-Aufteilung verzerren."""
    mask = _trim_to_ink_bbox(mask)
    height = len(mask)
    if height < 8:
        return 0.0
    num_bands = 4
    band_height = max(1, height // num_bands)
    centroids: list[tuple[int, float]] = []
    for band_index in range(num_bands):
        y0 = band_index * band_height
        y1 = height if band_index == num_bands - 1 else y0 + band_height
        xs = [col for row in mask[y0:y1] for col, ink in enumerate(row) if ink]
        if xs:
            centroids.append((band_index, sum(xs) / len(xs)))
    if len(centroids) < 2:
        return 0.0
    width = len(mask[0]) if mask and mask[0] else 1
    n = len(centroids)
    mean_i = sum(c[0] for c in centroids) / n
    mean_x = sum(c[1] for c in centroids) / n
    numerator = sum((c[0] - mean_i) * (c[1] - mean_x) for c in centroids)
    denominator = sum((c[0] - mean_i) ** 2 for c in centroids)
    if denominator == 0:
        return 0.0
    slope_per_band = numerator / denominator
    return slope_per_band / max(1, width)


def _resolve_sample_text(region: OcrTextRegion, candidate_text: str) -> str:
    """The ORIGINAL recognized text whenever OCR found one, else the
    translated candidate text - see classify_bold()'s docstring (mirrors
    the reasoning pipeline.images.inpainting._estimate_is_bold()'s
    docstring already documented at length: comparing the SAME string
    against its own synthetic renders isolates font style as the only
    variable, rather than confounding it with per-string ink-density
    differences)."""
    sample_text = region.text if region.text.strip() else candidate_text
    return sample_text if sample_text.strip() else ""


def classify_bold(
    image,
    region: OcrTextRegion,
    background: tuple[int, int, int],
    candidate_text: str,
    size: int,
    family: str = "sans_serif",
) -> bool:
    """Generalizes pipeline.images.inpainting._estimate_is_bold()
    (21.08.2026) to compare against the given FAMILY's synthetic Regular/
    Bold references instead of always DejaVu Sans - with the default
    family="sans_serif" this reproduces that function's exact original
    behaviour (inpainting.py now keeps a thin _estimate_is_bold() wrapper
    around this for backward compatibility, see that module). `size` is
    the caller's already-computed comparison font size (pipeline.images.
    inpainting._initial_font_size(region)) - kept a required parameter
    here rather than this module re-deriving it, so font_style.py has no
    dependency back on inpainting.py's rendering-loop constants. Defaults
    to False whenever there is nothing to compare against, or the two
    synthetic references happen to be identical (e.g. Bold isn't
    installed on this system and both fall back to the same file)."""
    sample_text = _resolve_sample_text(region, candidate_text)
    if not sample_text:
        return False
    regular_font = load_font(size, family=family, bold=False)
    bold_font = load_font(size, family=family, bold=True)
    regular_ratio = _synthetic_ink_ratio(sample_text, regular_font)
    bold_ratio = _synthetic_ink_ratio(sample_text, bold_font)
    if regular_ratio == bold_ratio:
        return False
    observed = _ink_ratio(image, region.x, region.y, region.width, region.height, background)
    return abs(observed - bold_ratio) < abs(observed - regular_ratio)


def classify_family(
    image, region: OcrTextRegion, background: tuple[int, int, int], candidate_text: str, size: int
) -> str:
    """Serif vs. Sans-Serif, per _serif_score() (siehe dort) und derselben
    Referenzvergleichs-Methodik wie classify_bold(). Regular-Gewicht für
    beide synthetischen Referenzen (Fett-/Kursiv-Erkennung laufen erst
    NACHDEM die Familie feststeht, siehe estimate_font_style() - eine
    fette Serif-Zeile würde sonst fälschlich gegen Sans-Serif-Referenzen
    verglichen). `size` siehe classify_bold()s Docstring. Default
    "sans_serif" bei fehlendem Vergleichstext oder wenn beide Referenzen
    zufällig denselben Score ergeben."""
    sample_text = _resolve_sample_text(region, candidate_text)
    if not sample_text:
        return "sans_serif"
    sans_font = load_font(size, family="sans_serif", bold=False)
    serif_font = load_font(size, family="serif", bold=False)
    sans_score = _serif_score(_render_sample_mask(sample_text, sans_font))
    serif_score = _serif_score(_render_sample_mask(sample_text, serif_font))
    if sans_score == serif_score:
        return "sans_serif"
    observed_mask = _binary_ink_mask(image, region.x, region.y, region.width, region.height, background)
    observed_score = _serif_score(observed_mask)
    return "serif" if abs(observed_score - serif_score) < abs(observed_score - sans_score) else "sans_serif"


def classify_italic(
    image,
    region: OcrTextRegion,
    background: tuple[int, int, int],
    candidate_text: str,
    size: int,
    family: str = "sans_serif",
    bold: bool = False,
) -> bool:
    """Kursiv-Erkennung per _slant_ratio() (siehe dort), verglichen gegen
    synthetische Referenzen in der bereits ermittelten Familie/Stärke
    (`family`/`bold` - siehe estimate_font_style()s Reihenfolge: Familie
    zuerst, dann Fett, dann Kursiv, jede Stufe nutzt die vorherige als
    Vergleichsbasis). `size` siehe classify_bold()s Docstring. Default
    False bei fehlendem Vergleichstext oder identischen Referenzwerten."""
    sample_text = _resolve_sample_text(region, candidate_text)
    if not sample_text:
        return False
    regular_font = load_font(size, family=family, bold=bold, italic=False)
    italic_font = load_font(size, family=family, bold=bold, italic=True)
    regular_slant = _slant_ratio(_render_sample_mask(sample_text, regular_font))
    italic_slant = _slant_ratio(_render_sample_mask(sample_text, italic_font))
    if regular_slant == italic_slant:
        return False
    observed_mask = _binary_ink_mask(image, region.x, region.y, region.width, region.height, background)
    observed_slant = _slant_ratio(observed_mask)
    return abs(observed_slant - italic_slant) < abs(observed_slant - regular_slant)


def estimate_font_style(
    image, region: OcrTextRegion, background: tuple[int, int, int], candidate_text: str, size: int
) -> FontStyle:
    """One-Stop-Ersatz für pipeline.images.inpainting._estimate_is_bold(),
    von allen drei InpaintingBackend.apply()-Implementierungen seit
    22.08.2026 genutzt (RoadMap.md Phase 3, Font-Matching): schätzt
    Familie, Fett und Kursiv in dieser Reihenfolge (jede Stufe nutzt die
    vorherige als Vergleichsbasis für die nächste - siehe classify_italic()
    s Docstring). `image` muss die UNVERÄNDERTEN Original-Pixel dieser
    Region zeigen (vor jeder Rückschreibung/Überdeckung), exakt wie
    _estimate_is_bold() das schon verlangte. `size` siehe classify_bold()s
    Docstring - üblicherweise pipeline.images.inpainting._initial_font_size
    (region), vom Aufrufer EINMAL pro Region berechnet und an alle drei
    classify_*()-Aufrufe unten weitergereicht.

    Fällt komplett auf FontStyle("sans_serif", False, False) zurück, wenn
    weder region.text noch candidate_text irgendeinen vergleichbaren Text
    liefern - derselbe "nichts zum Vergleichen, also Standard" Fall wie
    bei _estimate_is_bold()."""
    sample_text = _resolve_sample_text(region, candidate_text)
    if not sample_text:
        return FontStyle(family="sans_serif", bold=False, italic=False)
    family = classify_family(image, region, background, candidate_text, size)
    bold = classify_bold(image, region, background, candidate_text, size, family=family)
    italic = classify_italic(image, region, background, candidate_text, size, family=family, bold=bold)
    return FontStyle(family=family, bold=bold, italic=italic)
