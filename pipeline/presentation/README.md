# PPTX-OOXML-Engine: Phase 1

Die erste Version stellt einen verlustarmen PPTX-Roundtrip bereit. Sie liest
Folientext direkt aus DrawingML und ändert beim Writeback ausschließlich
vorhandene `<a:t>`-Textknoten. Shapes, Absätze und Beziehungen werden nicht neu
aufgebaut. Ein unveränderter Roundtrip ist eine byte-identische Dateikopie.

Phase 2a ergänzt eine providerunabhängige HTML-Brücke. Jeder bestehende Run
wird durch einen identitätsbehafteten `<span data-run="…">` geschützt;
vorhandene Zeilenumbrüche erhalten eigene Marker. Nach der Übersetzung werden
Markerzahl und Reihenfolge strikt validiert, bevor Text in die bestehenden
`<a:t>`-Knoten zurückgeschrieben wird. Provider, BudgetGuard und API-Aufruf
werden vom Aufrufer bereitgestellt; die Engine selbst kennt keine Zugangsdaten.

## Unterstützt

- normale Textfelder auf Folien
- folienlokale Platzhalter
- Tabellenzellen
- Text-Shapes in beliebig tief verschachtelten Gruppen
- vollständiges Run-Inventar: normalisierte häufige Eigenschaften plus das
  vollständige originale `<a:rPr>`-XML
- Position, Größe und Rotation als auslesbare Metadaten
- statische, konservative Meldung wahrscheinlichen Textüberlaufs
- API-freie Kostenvorschau über alle tatsächlich zu sendenden HTML-Payloads
- geschützte Begriffe über die bestehende `protected_terms`-Implementierung
- harter Übersetzungsausschluss für Footer-, Datums- und
  Foliennummern-Platzhalter (`ftr`, `dt`, `sldNum`)

## Noch nicht unterstützt

- SmartArt-Text
- Diagramm-/Chart-Text
- Sprecher- und Foliennotizen
- eingebettete OLE-Objekte
- Text in Bildern
- Text auf Mastern und Layouts
- WordArt-spezifische Texteffekte als normalisierte Eigenschaften (sie bleiben
  im rohen `<a:rPr>` vollständig dokumentiert)
- automatische Schriftverkleinerung, Shape-Vergrößerung oder sonstige
  Layoutkorrekturen
- Live-Übersetzung und produktive Provider-Auswahl in UI/CLI (noch nicht
  verdrahtet)

Nicht unterstützte Bestandteile werden nicht interpretiert und bleiben beim
No-op-Roundtrip byte-identisch. Bei einem Text-Writeback bleiben alle
unveränderten Paketbestandteile byte-identisch.

## Überlauferkennung

OOXML speichert kein verbindliches Ergebnis der PowerPoint-Texteinteilung.
`detect_text_overflow()` liefert deshalb eine statische Schätzung anhand von
Shape-Größe, Schriftgröße und Textmenge. Auch Autofit-Textkörper werden als
Risiko gemeldet, wenn ihre Textmenge die ursprüngliche Geometrie voraussichtlich
überschreitet: Autofit kann sonst den Text in geschützte Footerbereiche wachsen
lassen. Die visuelle Prüfung durch PowerPoint oder LibreOffice bleibt maßgeblich.
`compare_overflow()` vergleicht Ausgabe und Quelldokument und meldet nur neue
oder verschärfte Risiken; bereits vorhandene Layoutprobleme bleiben als Baseline
sichtbar, blockieren aber nicht automatisch eine Übersetzung.

## Prüfstrategie

`tests/fixtures/representative.pptx` enthält einen rotierten Platzhalter, ein
Textfeld in einer Gruppe und eine Tabelle. Die automatisierten Tests prüfen:

- byte-identischen No-op-Roundtrip
- identische Rasterung des No-op-Roundtrips über LibreOffice
- unveränderte strukturelle Fingerprints bei gezieltem Text-Writeback
- byte-identische Beziehungen und sonstige Paketbestandteile
- Extraktion und Formatdokumentation aller unterstützten Container
- Quellschutz und Überlaufmeldung
