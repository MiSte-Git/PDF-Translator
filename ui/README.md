# Desktop-UI – erster Ausbauschritt

Start: `python -m ui.app`

Die Oberfläche verlangt eine explizite Auswahl zwischen PDF, Präsentation,
Word/Writer und einzelnen Bildern. Eine automatische Dateityperkennung findet
nicht statt. Vor einem späteren Übersetzungsstart analysiert sie Textmenge,
Dokumenteinheiten und Bilder und zeigt Laufgrenze, lokalen Monatsverbrauch,
Freikontingent sowie eine grobe Kostenschätzung.

Die Oberfläche ist zur Laufzeit zwischen Deutsch und Englisch umschaltbar.
Französisch, Spanisch, Italienisch, Niederländisch, Finnisch, Kroatisch und
Russisch sind als zukünftige Sprachkataloge registriert und bis zur Befüllung
in der Auswahl als „vorbereitet“ deaktiviert.

## Aktuelle Grenzen

- Der Startknopf ist noch nicht mit den Übersetzungspipelines verbunden.
- Bei „Bilder einzeln auswählen“ folgt die Vorschau-/Auswahlansicht später.
- OCR und Bildübersetzung sind noch nicht implementiert; deren Zeichen- und
  Modellkosten können daher vor OCR noch nicht beziffert werden.
- API-Schlüssel in einer Umgebungsvariable gelten nur für den laufenden
  Prozess. Dauerhafte Ablage erfolgt optional über einen verfügbaren OS-Keyring.
- Die Kostenwerte sind Schätzmodelle aus `pipeline.translation.cost_control`,
  keine Abrechnungsauskunft des jeweiligen Anbieters.
