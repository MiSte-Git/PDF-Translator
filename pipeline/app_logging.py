"""Zentrale Logging-Konfiguration für die Desktop-App.

Michael (02.09.2026), nachdem ein Google-Drive-Fehler trotz mehrfachem
Neuladen/Speichern der Zugangsdaten unverändert blieb: "Haben wir kein Log
für genau solche Fälle?" - die ehrliche Antwort war bis dahin: nein.
ui/app.py hatte zwar schon ein `log = logging.getLogger(__name__)` und
zwei log.*-Aufrufe (Update-Check-Fehler, Übersetzungslauf-Fehler), aber
OHNE dass irgendwo `logging.basicConfig()`/ein Handler gesetzt wurde -
Pythons Root-Logger ohne Handler verschluckt alles unterhalb WARNING
lautlos, und selbst WARNING+ landete bestenfalls kurz auf stderr, nie in
einer Datei, die man nach dem Schließen der App noch anschauen könnte.
Für genau die Art von Fehler, die Michael gerade wiederholt per Screenshot
durchgeben musste (ein Google-HttpError beim Auflösen eines Drive-Ordners),
gab es also buchstäblich keine Aufzeichnung.

configure_logging() richtet einen einzigen, rotierenden Datei-Handler auf
dem Root-Logger ein - wird genau einmal beim Start aus ui/app.py::main()
aufgerufen, ist aber idempotent (mehrfacher Aufruf, z. B. in Tests, hängt
keinen zweiten Handler an). Bewusst KEIN zusätzlicher Konsolen-Handler:
Michael startet die App teils direkt in der Shell (siehe
02.09.2026-Prozess-Exit-Fix, "python -m ui.app") und sieht dort ohnehin
schon stdout/stderr-Ausgaben Dritter (z. B. die "Please visit this URL to
authorize..."-Zeile von google_auth_oauthlib, oder die
google.api_core-FutureWarning) - eine zweite Kopie auf stderr würde das
nur verdoppeln, während die Datei tatsächlich über einen einzelnen
Programmlauf hinaus erhalten bleibt und sich als Ganzes anhängen/teilen
lässt (z. B. hier in den Chat einfügen, statt einen Screenshot zu machen).

**Default-Level DEBUG, nicht INFO (korrigiert 02.09.2026, Fortsetzung 7):**
Der erste Wurf dieser Datei setzte hier INFO - genau dadurch tauchten die
`pipeline/credentials.py::get_api_key()`-Zeilen ("geladen aus
Umgebungsvariable ..."/"geladen aus dem OS-Schlüsselbund"), die als DEBUG
geloggt werden, in Michaels erstem echten app.log gar nicht erst auf. Das
war der eine Fall, für den dieses ganze Feature gebaut wurde - eine
Fehlkonfiguration bei der Suche nach der wahren Ursache sofort auffindbar
zu machen -, und ausgerechnet der wurde durch das eigene Default
verschluckt. Bei diesem Programm gibt es keine heiße Schleife, die DEBUG
zu einer echten Log-Flut machen würde, also überwiegt der Diagnosewert
klar.
"""
from __future__ import annotations

import logging
import logging.handlers
from pathlib import Path

# ~/.pdf-translator/ ist bislang von keiner anderen Stelle im Programm
# belegt (siehe Backlog.md 02.09.2026, Fortsetzung 5) - QSettings selbst
# nutzt die plattformeigenen Config-Pfade unter dem Organisations-/App-
# Namen "PDF-Translator"/"Document Translator" (ui/app.py), nicht das
# Home-Verzeichnis direkt.
LOG_DIR = Path.home() / ".pdf-translator" / "logs"
LOG_FILE = LOG_DIR / "app.log"

_configured = False


def configure_logging(level: int = logging.DEBUG) -> Path:
    """Hängt einen rotierenden Datei-Handler an den Root-Logger (max. 3x
    2 MB, danach werden die ältesten Einträge verworfen) und gibt den Pfad
    der Log-Datei zurück - z. B. für den "Log-Datei öffnen"-Knopf im
    Einstellungen-Dialog. Wiederholte Aufrufe sind ein No-Op (idempotent),
    damit z. B. Tests, die main() mehrfach indirekt anstoßen, nicht
    mehrfach denselben Handler registrieren.

    Default DEBUG (nicht INFO) - siehe dieses Moduls Docstring, Abschnitt
    "Default-Level DEBUG, nicht INFO": genau auf DEBUG-Level loggt
    pipeline/credentials.py::get_api_key(), woher (Umgebungsvariable vs.
    Schlüsselbund) jeder einzelne Zugangsdaten-Wert kam - ohne DEBUG bleibt
    diese für die Fehlersuche zentrale Information unsichtbar.
    """
    global _configured
    if _configured:
        return LOG_FILE
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s"))
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(level)
    _configured = True
    logging.getLogger(__name__).info("Logging gestartet -> %s", LOG_FILE)
    return LOG_FILE
