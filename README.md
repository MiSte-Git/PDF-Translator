# PDF-Translator

Übersetzt PDF-, Word- (DOCX) und PowerPoint- (PPTX) Dokumente in eine andere
Sprache, ohne die Formatierung zu verändern – Layout, Schriftarten, Header/
Footer, Foliennummern und definierte Schutzbereiche bleiben erhalten.
Optional auch Übersetzung von Text in eingebetteten Bildern (OCR +
Rückschreibung). Quelldateien werden nie überschrieben.

Unterstützte Übersetzungs-Provider: DeepL, Google Translate, OpenAI und Grok
(xAI). Die Oberfläche ist zweisprachig (Deutsch/Englisch).

Es gibt zwei Wege, PDF-Translator zu benutzen – such dir den passenden aus:

- **[Für alle anderen](#für-alle-anderen-geführte-installation)** – ein
  geführter Installations-Assistent mit eigener Oberfläche, keine
  Kommandozeile nötig.
- **[Für Entwickler:innen](#für-entwicklerinnen)** – Quellcode klonen,
  Abhängigkeiten selbst installieren, direkt aus dem Repository heraus
  starten.

Beide Wege installieren am Ende exakt dasselbe Programm; der geführte
Assistent macht im Hintergrund nichts anderes, als was im Entwickler-Weg von
Hand gemacht wird (siehe [Architektur](#architektur-der-geführten-installation)
unten).

## Für alle anderen (geführte Installation)

1. Lade die passende Datei für dein Betriebssystem von der
   [Releases-Seite](https://github.com/MiSte-Git/TranslatePDF/releases)
   herunter:
   - Windows: `pdf-translator-setup-windows.exe`
   - macOS: `pdf-translator-setup-macos`
   - Linux: `pdf-translator-setup-linux`
2. Datei ausführen. Es öffnet sich ein Fenster, keine Kommandozeile nötig.
3. Der Assistent führt dich durch:
   - **Sprache** – automatisch nach Systemsprache vorausgewählt (Fallback
     Englisch, wenn die Systemsprache weder Deutsch noch Englisch ist),
     jederzeit umschaltbar.
   - **Online oder Lokal** – *Online* nutzt einen Cloud-Anbieter (laufende
     Kosten pro Übersetzung, eigener API-Schlüssel nötig – dazu gleich
     mehr). *Lokal* übersetzt/bearbeitet Bilder direkt auf diesem Rechner,
     keine laufenden Kosten, braucht aber eine ausreichend starke
     NVIDIA-Grafikkarte (mindestens ca. 8 GB Grafikspeicher empfohlen) und
     einen größeren einmaligen Download. Auf dem Mac steht *Lokal* in
     dieser Version nicht zur Verfügung – dort geht es automatisch mit
     *Online* weiter.
   - **Prüfung der Grafikkarte** (nur bei *Lokal*) – der Assistent prüft
     direkt, ob sich der lokale Modus auf diesem Rechner überhaupt lohnt,
     *bevor* der große Download beginnt.
   - **Installation** – läuft automatisch im Hintergrund in eine eigene,
     versteckte Umgebung im Benutzerprofil. Dafür sind **keine
     Administrator-/root-Rechte** nötig, es wird nichts systemweit
     installiert.
   - **API-Schlüssel** (nur bei *Online*) – optional, jederzeit
     überspringbar und später in den Einstellungen der App nachholbar.
     Eine Checkliste zeigt alle vier Anbieter; für jeden angehakten folgt
     ein eigener, kurzer Schritt mit Link zur Anmeldeseite.
   - **Fertig** – ein Eintrag im Anwendungsmenü/Startmenü/Applications-
     Ordner ist angelegt, die App kann direkt gestartet werden.
4. Eine Anmerkung zum ersten Start: die Builds sind aktuell **nicht
   signiert** (Code-Signing ist für eine spätere Version vorgesehen).
   Windows SmartScreen bzw. macOS Gatekeeper zeigen deshalb beim allerersten
   Start eine Warnung – "Weitere Informationen"/"Trotzdem öffnen" (Windows)
   bzw. Rechtsklick → "Öffnen" (macOS) bestätigt den Start einmalig.

Ein Eintrag im Anwendungsmenü ist überall das Ergebnis, kein `.deb`/`.rpm`/
`.msi`/`.dmg` nötig – Details dazu unten unter
[Architektur](#architektur-der-geführten-installation).

## Für Entwickler:innen

```bash
git clone https://github.com/MiSte-Git/TranslatePDF.git
cd TranslatePDF
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
# optional, für Bildübersetzung/OCR:
pip install -r requirements-ocr.txt
```

Start der Desktop-Oberfläche (PySide6/Qt):

```bash
python -m ui.app
```

Alternativ die lokale Server-/Browser-Variante:

```bash
python -m webapp
```

API-Schlüssel für die Übersetzungs-Provider werden entweder als
Umgebungsvariable gesetzt (`DEEPL_API_KEY`, `GOOGLE_TRANSLATE_API_KEY`,
`OPENAI_API_KEY`, `GROK_API_KEY`/`XAI_API_KEY`) oder – bequemer – über den
Einstellungen-Dialog der App im OS-Schlüsselbund gespeichert (Windows
Credential Locker/macOS Keychain/Linux Secret Service, via
`pipeline/credentials.py`).

Tests ausführen:

```bash
python -m pytest
```

Commit-/PR-Konventionen und die Architekturregel "`pipeline/` bleibt
UI-frei" stehen in [`CONTRIBUTING.md`](CONTRIBUTING.md). Offene Arbeiten und
Hintergrund zu bereits gelösten Einzelfällen stehen in
[`RoadMap.md`](RoadMap.md) und [`Backlog.md`](Backlog.md).

## Architektur der geführten Installation

Der Installations-Assistent (`bootstrap/`) ist bewusst ein eigenständiges,
sehr kleines `tkinter`-Programm – Teil jeder Standard-Python-Installation,
kein PySide6/Qt nötig für dieses eine Fenster. Er läuft in zwei Stufen:

1. **Stufe 1 – der Assistent selbst:** führt durch Sprache, Online/Lokal,
   GPU-Prüfung, lädt dann den eigentlichen Programmcode als Release-ZIP von
   GitHub Releases herunter, legt eine eigene virtuelle Python-Umgebung
   (venv) im Benutzerprofil an und installiert die Abhängigkeiten dort mit
   `pip install -r requirements.txt` (plus `-ocr`/`-gpu`-Varianten je nach
   gewähltem Modus) – **exakt derselbe Befehl**, den auch der
   Entwickler-Weg oben von Hand ausführt. Alle Abhängigkeiten kommen dabei
   von PyPI bzw. (für die GPU-Variante von PyTorch) direkt von pytorch.org,
   nicht von GitHub.
2. **Stufe 2 – die eigentliche App:** der heruntergeladene Code plus die
   eben installierten Abhängigkeiten, im eigenen venv. Der Anwendungsmenü-
   Eintrag, den der Assistent am Ende anlegt, zeigt direkt auf dieses
   venv – es gibt also keinen separaten "Build" der eigentlichen App, nur
   den ganz normalen `python -m ui.app`-Start aus dem Entwickler-Weg, bloß
   automatisiert.

Weil dabei nichts außerhalb des Benutzerprofils landet, sind für die
Installation zu keinem Zeitpunkt Administrator-/root-Rechte nötig – das ist
auch der eigentliche Grund, warum kein klassischer System-Installer
(`.deb`/`.rpm`/`.msi`) gebraucht wird, nicht nur eine kosmetische
Entscheidung. Für den Eintrag im Anwendungsmenü legt der Assistent je nach
Betriebssystem selbst das passende, ebenfalls rechtefreie Äquivalent an:
eine `.desktop`-Datei unter Linux, eine `.lnk`-Verknüpfung im Startmenü
unter Windows, ein `.app`-Bundle unter macOS. Automatisches Anheften an die
Taskleiste/das Dock kann dabei kein Installer der Welt erzwingen – das
verbieten Windows und macOS aus Sicherheitsgründen programmatisch –, aber
das gilt für jeden Installer gleichermaßen und ist kein Nachteil dieses
Ansatzes.

Der Assistenten-Build für alle drei Plattformen läuft automatisiert über
[`.github/workflows/build-bootstrap.yml`](.github/workflows/build-bootstrap.yml)
(PyInstaller, `windows-latest`/`macos-latest`/`ubuntu-latest`) und wird bei
jedem Versions-Tag zusammen mit einem Quellcode-ZIP als GitHub-Release
veröffentlicht.

Ausführlicher Hintergrund zu den einzelnen Entscheidungen (GPU-Schwellwert,
Zeitpunkt der API-Schlüssel-Eingabe, Mehrsprachigkeit, Verzicht auf
`.deb`/`.rpm`) steht im internen Projekt-Dokument
"deployment-strategie-bootstrapper-01-09-2026".
