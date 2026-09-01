# Google Drive einrichten (für die Ordnersuche)

Damit der PDF-Translator einen Google-Drive-Ordner durchsuchen kann,
braucht er einmalig einen eigenen OAuth-"Desktop app"-Zugang. Das kann die
App nicht selbst anlegen - Google verlangt, dass jede Anwendung ihren
eigenen, im Google Cloud Console registrierten Client verwendet. Diese
Einrichtung macht man einmal; danach reicht im Programm "Mit Google
verbinden".

## 1. Google-Cloud-Projekt anlegen (falls noch keins vorhanden)

1. https://console.cloud.google.com öffnen, mit dem Google-Konto anmelden,
   das auch die zu durchsuchenden Drive-Ordner besitzt (oder das
   mindestens Lesezugriff darauf hat).
2. Oben links auf die Projektauswahl klicken -> "Neues Projekt" -> einen
   beliebigen Namen vergeben (z. B. "PDF Translator") -> Erstellen.

## 2. Drive API aktivieren

1. Im Menü links: "APIs & Dienste" -> "Bibliothek".
2. Nach "Google Drive API" suchen, öffnen, "Aktivieren" klicken.

## 3. OAuth-Zustimmungsbildschirm einrichten

1. "APIs & Dienste" -> "OAuth-Zustimmungsbildschirm".
2. Nutzertyp "Extern" wählen (reicht für den persönlichen Gebrauch), außer
   es liegt ein Google-Workspace-Konto mit interner Option vor.
3. App-Name (frei wählbar), eigene E-Mail-Adresse als Support-Kontakt
   eintragen, speichern.
4. Unter "Testnutzer" die eigene Google-Kontoadresse hinzufügen, solange
   die App im Testmodus bleibt (reicht für den persönlichen Gebrauch -
   eine Veröffentlichung/Google-Prüfung ist für die eigene Nutzung nicht
   nötig).
5. Scope muss NICHT manuell hinzugefügt werden - der PDF-Translator fragt
   beim Verbinden selbst nach `drive.readonly` (nur Lesezugriff, siehe
   pipeline/drive_auth.py).

## 4. OAuth-Client-ID erstellen

1. "APIs & Dienste" -> "Zugangsdaten" -> "+ Zugangsdaten erstellen" ->
   "OAuth-Client-ID".
2. Anwendungstyp: **Desktop-App** (wichtig - nicht "Web-Anwendung").
3. Einen beliebigen Namen vergeben, erstellen.
4. Es erscheinen eine **Client-ID** und ein **Client-Secret** - beide
   werden im nächsten Schritt gebraucht.

## 5. Im PDF-Translator eintragen und verbinden

1. Im Merge-Dialog auf "Ordner durchsuchen …" klicken, oben auf "Google
   Drive" umschalten.
2. Client-ID und Client-Secret aus Schritt 4 in die beiden Felder
   einfügen, "Zugangsdaten speichern" klicken (landet im OS-Schlüsselbund,
   siehe pipeline/credentials.py - genau wie die Übersetzungs-Provider-
   Schlüssel).
3. "Mit Google verbinden" klicken - es öffnet sich der Standard-
   Google-Anmeldebildschirm im Browser. Zustimmen (bei "Diese App wurde
   nicht verifiziert" - normal im Testmodus - auf "Erweitert" ->
   "Zur App (unsicher) wechseln" klicken, es ist die eigene, selbst
   angelegte App).
4. Zurück im Programm: Status wechselt auf "Verbunden".

## Danach

- Der Ordnerlink lässt sich direkt aus Google Drive kopieren (Rechtsklick
  auf den Ordner -> "Link kopieren") und im Feld "Drive-Ordnerlink oder
  -ID" einfügen.
- Heruntergeladene Treffer bleiben im gewählten Cache-Ordner liegen (siehe
  Backlog.md 01.09.2026 für die genaue Logik).
- Zugriff später entziehen: entweder im Programm "Trennen" klicken (löscht
  nur den lokal gespeicherten Token), oder unter
  https://myaccount.google.com/permissions den Zugriff der App komplett
  widerrufen.
