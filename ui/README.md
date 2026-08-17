# Desktop-UI

Start: `python -m ui.app`

Die Oberfläche verlangt eine explizite Auswahl zwischen PDF, Präsentation,
Word/Writer und einzelnen Bildern. Eine automatische Dateityperkennung findet
nicht statt. Vor einem Übersetzungsstart analysiert sie Textmenge,
Dokumenteinheiten und Bilder und zeigt Laufgrenze, lokalen Monatsverbrauch,
Freikontingent sowie eine grobe Kostenschätzung.

Die Oberfläche ist zur Laufzeit zwischen Deutsch und Englisch umschaltbar.
Französisch, Spanisch, Italienisch, Niederländisch, Finnisch, Kroatisch und
Russisch sind als zukünftige Sprachkataloge registriert und bis zur Befüllung
in der Auswahl als „vorbereitet“ deaktiviert.

## Präsentationen (PowerPoint/Impress) übersetzen

Als einziger Modus ist „Präsentation übersetzen“ bereits vollständig an den
Startknopf angebunden (siehe `ui/pptx_job.py`, RoadMap.md Phase 1):

1. Datei wählen, Analyse laufen lassen, Kostenschätzung und Analysehinweise
   prüfen und die Checkbox „Analyse und Kostenschätzung geprüft“ aktivieren.
2. „Übersetzung starten“ öffnet einen Zielordner-Dialog. Der Zieldateiname
   wird automatisch aus Quellname + Zielsprache gebildet und bei Kollision
   fortlaufend nummeriert (`Deck_DE.pptx`, `Deck_DE (2).pptx`, …) - Quelle und
   Ziel können technisch nie identisch sein.
3. Eine letzte Kostenbestätigung mit Zeichenzahl, Schätzkosten und Zieldatei
   erscheint unmittelbar vor dem ersten API-Aufruf.
4. Während des Laufs zeigt das Panel „Lauf und Ergebnis“ die aktuelle
   Folie/Shape/Absatz-Position sowie einen Fortschrittsbalken; „Abbrechen“
   stoppt den Lauf zwischen zwei API-Aufrufen (nie mittendrin) und behält
   bereits übersetzte Absätze als klar gekennzeichnetes Teilergebnis.
5. Nach Abschluss zeigt das Panel Kurzstatistik (übersetzt/übersprungen/
   fehlgeschlagen/gesendete Zeichen), verlinkt die Ausgabedatei und einen
   QA-Bericht (Textdatei neben der Ausgabedatei) mit allen gefundenen
   Überlaufrisiken gegenüber dem Original - diese werden nur gemeldet, nie
   automatisch umformatiert.

Provider- und Netzwerkfehler werden verständlich angezeigt und über das
Standard-`logging`-Modul protokolliert, niemals mit dem API-Schlüssel im Text.

## Aktuelle Grenzen

- PDF, Word/Writer und Bilder sind analysierbar, aber ihr Startknopf ist noch
  nicht verbunden (folgt mit RoadMap.md Phase 2/3).
- Bei „Bilder einzeln auswählen“ folgt die Vorschau-/Auswahlansicht später.
- OCR und Bildübersetzung sind noch nicht implementiert; deren Zeichen- und
  Modellkosten können daher vor OCR noch nicht beziffert werden.
- API-Schlüssel in einer Umgebungsvariable gelten nur für den laufenden
  Prozess. Dauerhafte Ablage erfolgt optional über einen verfügbaren OS-Keyring.
- Die Kostenwerte sind Schätzmodelle aus `pipeline.translation.cost_control`,
  keine Abrechnungsauskunft des jeweiligen Anbieters.
- Mehrere Aufträge nacheinander (Warteschlange/Stapelverarbeitung) sind noch
  nicht möglich; ein Lauf muss abgeschlossen oder abgebrochen sein, bevor der
  nächste startet.
