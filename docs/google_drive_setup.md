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

   **Nicht verwechseln (02.09.2026, Michael):** Das ist eine andere Seite
   als "Zugangsdaten" -> dein OAuth-Client -> "Clientschlüssel"-Status
   "Aktiviert". Letzteres sagt nur, dass der Clientschlüssel selbst
   gültig/nicht widerrufen ist - nichts darüber, ob die Drive API für das
   Projekt freigeschaltet ist. Die richtige Seite hier zeigt oben
   "Dienstname: drive.googleapis.com" und "Status: Aktiviert".

## 3. OAuth-Zustimmungsbildschirm einrichten

1. "APIs & Dienste" -> "OAuth-Zustimmungsbildschirm".
2. Nutzertyp "Extern" wählen (reicht für den persönlichen Gebrauch), außer
   es liegt ein Google-Workspace-Konto mit interner Option vor.
3. App-Name (frei wählbar), eigene E-Mail-Adresse als Support-Kontakt
   eintragen, speichern.
4. Unter "Testnutzer" die eigene Google-Kontoadresse hinzufügen, solange
   die App im Testmodus bleibt (reicht für den persönlichen Gebrauch -
   eine Veröffentlichung/Google-Prüfung ist für die eigene Nutzung nicht
   nötig). **Wichtig:** genau die Adresse eintragen, mit der man sich
   später beim "Mit Google verbinden" auch tatsächlich anmeldet - sonst
   kommt beim Anmelden "Zugriff blockiert: Die Überprüfung von [App]
   durch Google wurde nicht abgeschlossen" (ein harter Block OHNE
   Umgehungsmöglichkeit). Das ist eine andere, striktere Meldung als die
   Warnung "Diese App wurde nicht verifiziert" in Schritt 5.3 unten (die
   hat einen "Erweitert"-Link zum Fortfahren) - der harte Block bedeutet
   konkret: das gerade verwendete Google-Konto steht nicht in dieser
   Testnutzer-Liste.
5. Scope muss NICHT manuell hinzugefügt werden - der PDF-Translator fragt
   beim Verbinden selbst nach `drive.readonly` (nur Lesezugriff, siehe
   pipeline/drive_auth.py).

## 4. OAuth-Client-ID erstellen

1. "APIs & Dienste" -> "Zugangsdaten" -> "+ Zugangsdaten erstellen" ->
   "OAuth-Client-ID".
2. Anwendungstyp: **Desktop-App** (wichtig - nicht "Web-Anwendung").
3. Einen beliebigen Namen vergeben, erstellen.
4. Es erscheint ein Dialog mit **Client-ID** und **Client-Secret** -
   direkt dort unten auf **"JSON HERUNTERLADEN"** klicken (empfohlen,
   siehe Schritt 5 unten) statt beide Werte einzeln abzutippen. Die
   Datei enthält Client-ID, Client-Secret UND die Projekt-ID bereits
   korrekt gebündelt - manuelles Kopieren ist fehleranfällig (z. B.
   versehentlich einen API-Schlüssel statt der Client-ID eingefügt, oder
   die Projekt-ID separat suchen müssen).

## 5. Im PDF-Translator eintragen und verbinden

1. Im Merge-Dialog auf "Ordner durchsuchen …" klicken, oben auf "Google
   Drive" umschalten.
2. **Empfohlen:** "Aus JSON-Datei laden …" klicken und die in Schritt 4.4
   heruntergeladene Datei wählen - füllt Client-ID, Client-Secret und
   Projekt-ID automatisch korrekt aus. Alternativ lassen sich alle drei
   Werte auch von Hand eintragen (z. B. wenn die Datei nicht mehr
   vorliegt); die Projekt-ID steht dann oben links in der Projektauswahl
   neben dem Projektnamen, oder auf der "Zugangsdaten"-Seite oben im
   Bereich "Projektinformationen".
3. "Zugangsdaten speichern" klicken (landet im OS-Schlüsselbund, siehe
   pipeline/credentials.py - genau wie die Übersetzungs-Provider-
   Schlüssel). Schlägt das fehl (z. B. kein OS-Schlüsselbund verfügbar),
   erscheint jetzt eine Fehlermeldung mit dem konkreten Grund, statt
   stillschweigend nichts zu tun.
4. "Mit Google verbinden" klicken - es öffnet sich der Standard-
   Google-Anmeldebildschirm im Browser, mit genau dem Google-Konto
   anmelden, das in Schritt 3.4 als Testnutzer eingetragen wurde.
   Zustimmen (bei "Diese App wurde nicht verifiziert" - normal im
   Testmodus - auf "Erweitert" -> "Zur App (unsicher) wechseln" klicken,
   es ist die eigene, selbst angelegte App).
5. Zurück im Programm: Status wechselt auf "Verbunden".

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

## Fehlerbehebung

- **"Prüfen"/eine Ordnersuche meldet einen Google-HttpError** (z. B.
  "Project '...' not found or deleted."): Das Anmelden selbst (Schritt 5.4 -
  Browser öffnet sich, Konto bestätigen, App vertrauen) prüft nur
  Client-ID/Client-Secret; der Fehler beim anschließenden Zugriff auf einen
  Ordner kommt aus einem anderen Wert - meist die Projekt-ID. Ein falscher
  Ordnerlink/eine falsche Ordner-ID meldet sich mit einer anderen, expliziten
  Meldung ("Datei/Ordner nicht gefunden" mit der Ordner-ID im Text), nicht
  mit einer Meldung über ein "Project". "Verknüpfen" mit dem eigenen
  Google-Konto ist an dieser Stelle kein separater Schritt - wer das
  Cloud-Projekt im eigenen Konto angelegt hat (Schritt 1), hat automatisch
  Zugriff darauf; eine fehlende Berechtigung sähe ohnehin anders aus (eine
  403-"permission denied"-Meldung, nicht "not found or deleted").
- **Was genau verwendet wurde, steht im Log** (seit 02.09.2026): Menü
  "Einstellungen" -> "Log-Datei öffnen …", oder direkt
  `~/.pdf-translator/logs/app.log`. Dort steht bei jedem Verbindungsversuch
  eine gekürzte Vorschau der tatsächlich verwendeten Projekt-ID sowie ob sie
  aus einer Umgebungsvariable oder aus dem Schlüsselbund (also aus diesem
  Dialog) stammt.
- **Ein im Dialog gespeicherter Wert scheint wirkungslos**: Seit 02.09.2026
  hat für die drei Drive-Zugangsdaten (Client-ID, Client-Secret, Projekt-ID)
  und den Refresh-Token der im Schlüsselbund gespeicherte Wert (also das,
  was "Zugangsdaten speichern"/die Anmeldung hier im Dialog erzeugt) immer
  Vorrang - eine gleichnamige Umgebungsvariable (`GOOGLE_DRIVE_CLIENT_ID`,
  `GOOGLE_DRIVE_CLIENT_SECRET`, `GOOGLE_DRIVE_PROJECT_ID`,
  `GOOGLE_DRIVE_REFRESH_TOKEN`) wirkt nur noch, solange im Schlüsselbund
  gar nichts gespeichert ist. Bei einer älteren Programmversion (davor)
  galt das Gegenteil: eine gesetzte Umgebungsvariable hatte immer Vorrang,
  auch vor einem frisch gespeicherten Wert - falls das Verhalten weiterhin
  seltsam wirkt, in der Shell, aus der die App gestartet wird, einmal
  `env | grep GOOGLE_DRIVE` prüfen.
- **403 "accessNotConfigured" / "Google Drive API has not been used in
  project ... before or it is disabled"** (02.09.2026, nachdem die
  Projekt-ID korrigiert war): eine korrekte Projekt-ID allein reicht nicht
  - Schritt 2 oben ("Drive API aktivieren") muss für GENAU dieses Projekt
  einmalig gemacht worden sein. Die Meldung nennt bereits den direkten
  Link (`https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=<Projekt-ID>`)
  - öffnen, "Aktivieren" klicken, ein bis zwei Minuten warten (Google
  braucht kurz, bis das propagiert), dann erneut "Prüfen"/die Suche
  starten. Am einfachsten zu erkennen im Log
  (`~/.pdf-translator/logs/app.log`, oder "Einstellungen" -> "Log-Datei
  öffnen …") an `reason: 'accessNotConfigured'` bzw. Status 403 - anders
  als die Projekt-ID-Fehler oben (Status 400) ist das kein
  Konfigurationsfehler dieser App, sondern ein fehlender Schritt in der
  Google Cloud Console für dieses eine Projekt.
