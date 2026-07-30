# Contributing

Danke für dein Interesse an diesem Projekt! Ein paar kurze Hinweise, bevor du loslegst.

## Code-Stil

- Type Hints für alle öffentlichen Funktionen und Methoden verwenden.
- Kurze Docstrings auf Englisch (eine Zeile reicht meist, kein ausführlicher
  Prosa-Text).
- Bestehenden Stil im jeweiligen Modul beibehalten (PEP 8, snake_case
  Funktionen/Variablen, UPPER_CASE Konstanten).

## Architektur: pipeline/ bleibt UI-frei

`pipeline/` darf keine Abhängigkeit auf PySide6/Qt oder sonstigen UI-Code
haben. Die Pipeline muss eigenständig (z. B. per CLI oder in Tests) ohne
laufende UI nutzbar sein. UI-spezifischer Code gehört ausschließlich nach
`ui/`.

## Commit-Konventionen

- Commits klein und fokussiert halten – eine logische Änderung pro Commit.
- Kurze, aussagekräftige Commit-Message in der Gegenwartsform (z. B. "Add
  DeepL provider", "Fix reflow for rotated pages").
- Keine Zugangsdaten, API-Keys oder private Testdateien (z. B. PDFs mit
  echten/persönlichen Inhalten) committen.

## Pull Requests

1. Branch von `main` erstellen.
2. Änderungen klein und fokussiert halten.
3. PR mit kurzer Beschreibung öffnen: was ändert sich und warum.
4. Wird bei Gelegenheit reviewt – bei größeren Änderungen vorher gerne ein
   Issue zur Abstimmung anlegen.
