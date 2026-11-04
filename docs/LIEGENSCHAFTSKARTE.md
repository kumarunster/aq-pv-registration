# Automatische Liegenschaftskarte: Architektur und Integration

## Analyse des bestehenden Projekts

Das Projekt besteht aus einem FastAPI-Backend (Python 3.12), einer Vue-SPA, MongoDB,
MinIO und mehreren eigenständigen Compose-Diensten. Nginx ist der einzige externe
Einstiegspunkt. Admin- und Installer-Routen laufen bereits über Oathkeeper/Kratos;
das Backend erhält die geprüfte Identität als `X-Kratos-Identity-ID`.
Der bestehende WeasyPrint-Service dient als Vorbild für die eigenständige
Katasterkomponente. Grundstücksfelder existieren bereits im Anlagenmodell; der neue
Abruf überschreibt diese Felder nicht automatisch.

## Datenfluss

```text
Browser -> Nginx -> Oathkeeper/Kratos -> FastAPI-Backend
                                         |
                                         +-> MongoDB: Ergebnis + Benutzerzuordnung
                                         |
                                         +-> na-kataster:8765 -> Photon / Landesdienste
                                                   |
                                                   +-> Volume: PNG / JSON / Cache
```

`na-kataster` hat keine Host-Portfreigabe und keine Nginx-Route. Auf seinem privaten
Service-Netz liegen nur Kataster und Backend. Weil Katasterabfragen Internetzugriff
benötigen, besitzt der Container zusätzlich ein eigenes Egress-Netz. Port `8765`
wird ausschließlich als Container-Port deklariert. Der Dienst läuft nicht als Root.

Der Backend-Relay akzeptiert keine frei wählbaren URLs oder Dateipfade. Er überträgt
keine Browser-Cookies oder Identitätsheader an den Katasterdienst. Erfolgreiche
Ergebnisse werden in der MongoDB-Collection `liegenschaftskarten` unter einer
eindeutigen Ergebnis-ID und `created_by` gespeichert. Die Collection wird beim ersten
Abruf automatisch angelegt; der eindeutige `_id`-Index von MongoDB genügt für die
benutzergebundenen Einzelabfragen. Auch Admin-Downloads sind auf den Ersteller
begrenzt. Fremde oder unbekannte IDs liefern HTTP 404.

## Backend-API

Basis je nach Benutzeroberfläche:

- Admin: `/api/admin/liegenschaftskarte`
- Installer: `/api/installer/liegenschaftskarte`

Beide Pfade benutzen die vorhandenen Oathkeeper-Regeln. Alle folgenden Endpunkte
setzen eine gültige Sitzung voraus; es gibt keinen öffentlichen Kataster-Endpunkt.

| Methode | Relativer Pfad | Funktion |
|---|---|---|
| GET | `/laender` | Länder und konfigurierte Datenquellen |
| POST | `/auszug` | Adresse abfragen, standardmäßig 60 m Breite |
| GET | `/ergebnisse/{id}/karte.png` | PNG über Backend-Relay |
| GET | `/ergebnisse/{id}/grundstueck.json` | Gespeichertes Ergebnis als JSON |

Beispiel mit gültigem, lokal gespeichertem Kratos-Session-Cookie:

```bash
curl --max-time 330 --cookie cookies.txt \
  -H 'Content-Type: application/json' \
  -d '{"adresse":"Im Schönenfelde 14, 21109 Hamburg","breite_meter":60,"nur_amtlich":true}' \
  http://localhost:8092/api/admin/liegenschaftskarte/auszug
```

Pflichtfeld: `adresse` (5–300 Zeichen); optional: `breite_meter` (10–1000, Standard 60),
`nur_amtlich` (boolesch, Standard `true`). Unbekannte Felder werden abgelehnt.

Die Antwort enthält die unveränderten fachlichen Ergebnisse, Warnungen, Quellen,
Bounding Box und Teilstatus des Katasterdienstes. Ausschließlich die Dateilinks
werden auf den Backend-Namensraum des Aufrufers umgeschrieben:

```json
{
  "status": "ok",
  "grundstuecke": [{"gemarkung":"Wilhelmsburg","flur":null,"flurstueck":"2798"}],
  "dateien": {
    "bild": "/api/admin/liegenschaftskarte/ergebnisse/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/karte.png",
    "json": "/api/admin/liegenschaftskarte/ergebnisse/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/grundstueck.json"
  }
}
```

Die Beispiel-ID ist ein Platzhalter. Die tatsächlichen Links aus der Antwort
verwenden und die Sitzung auch beim Download mitsenden. JSON wird aus dem gespeicherten
Ergebnis erzeugt; PNG wird nach Eigentümerprüfung vom internen Dienst abgerufen.
Downloads sind mit `Cache-Control: private, no-store` versehen. Es werden keine
Ergebnisse automatisch mit Kunden, Anlagen oder MinIO-Dokumenten verknüpft.

Der vorhandene globale Frontend-Axios-Client hat einen Timeout von 10 Sekunden.
Ein UI-Aufrufer dieses neuen Endpunkts muss einen längeren Timeout setzen, etwa:

```javascript
const response = await client.post('/admin/liegenschaftskarte/auszug', {
  adresse: 'Im Schönenfelde 14, 21109 Hamburg',
  breite_meter: 60,
  nur_amtlich: true,
}, { timeout: 330000 })
```

## Abruf in der Anlagenmaske

Im Anlageneditor (Admin und Installer) steht oberhalb des Lageplan-Abschnitts die
Aktion **„Karte & Grundstücksdaten laden“**. Sie verwendet die Kundenadresse, wenn
„Adresse vom Kunden übernehmen“ gesetzt ist, ansonsten die eigene Anlagenadresse.
Voraussetzung sind Straße mit Hausnummer, fünfstellige PLZ und Ort. Der Abruf ist
auch vor dem erstmaligen Speichern eines Kunden möglich und startet bewusst per
Klick, nicht bei jedem Tastendruck.

Nach erfolgreicher Suche werden Gemarkung, Flur und Flurstück übernommen. Eine im
Datensatz nicht geführte Flur bleibt leer (beispielsweise Hamburg). Nur ein einzelner,
eindeutiger und vollständiger Grundstückstreffer wird übertragen. Bei Grenzfällen,
fehlenden Zugängen oder mehreren Treffern bleiben vorhandene Grundstücksfelder erhalten.

Das Kartenbild wird über den authentifizierten Relay heruntergeladen und als
Data-URL im `lageplan` gespeichert. Dadurch kann der vorhandene Editor es unmittelbar
verwenden, und gespeicherte Pläne bleiben auch für andere berechtigte Benutzer sowie
beim PDF-Export unabhängig von der benutzergebundenen Download-URL verfügbar.
Vorhandene Zeichnungselemente und eigene Layout-Metadaten bleiben erhalten. Nach
einem erneuten Bildabruf muss die Ausrichtung bestehender Zeichnungen geprüft werden.

Statusanzeigen:

- `✓ erfasst`: Ein Lageplan ist in der Anlage vorhanden.
- `✓ Hintergrundbild geladen`: Katasterbild zur aktuellen Adresse übernommen.
- `✓ Grundstücksinfos gefunden`: Eindeutiger Treffer zur aktuellen Adresse; Felder
  stimmen weiterhin mit dem übernommenen Treffer überein.
- Laden, Fehler, Teilresultate und geänderte Adressen erhalten eigene Hinweise.

Die Bestätigung wird in `plants[].kataster` zusammen mit Adresse, Abrufzeit,
Flurstückskennzeichen und Fläche gespeichert. Änderungen an Adresse oder manuell
bearbeiteten Grundstücksfeldern verhindern eine veraltete grüne Trefferanzeige.
Ein im Editor manuell ersetztes Bild entfernt die Bestätigung des Katasterhintergrunds.
Während des Abrufs ist Speichern gesperrt; Antworten für inzwischen geänderte
Adressen oder entfernte Anlagen werden verworfen. Netzwerkfehler lassen vorhandene
Lagepläne unverändert. Karte und Grundstücksdaten können auch unabhängig voneinander
als Teilresultat übernommen werden.

**Die Übernahme ändert zunächst das Formular. Mit „Speichern“ werden Bild,
Grundstücksfelder und Abrufstatus zusammen mit den Anlagendaten dauerhaft gesichert.**

## Fehler und Teilresultate

- HTTP 401: keine vom Gateway bestätigte Identität.
- HTTP 422: ungültige Eingabe oder nicht eindeutig auflösbare Adresse.
- HTTP 429: ein Katasterabruf läuft bereits; `Retry-After: 10` beachten.
- HTTP 502: Katasterdienst nicht erreichbar oder ungültige Antwort.
- HTTP 504: Katasterdienst überschreitet den Relay-Timeout.
- HTTP 404: Ergebnis/Bild fehlt oder gehört einem anderen Benutzer.

HTTP 200 kann ein fachliches Teilresultat (`status: "teilweise"`) enthalten.
`grundstueck_status`, `bild.status`, `dateien.bild` und `hinweise` prüfen. Insbesondere
liefert Bayern ohne berechtigten Zugang keine vollständigen Grundstücksdaten.

## Compose und Konfiguration

Die projektweite Datei `_infrastructure/docker-compose.yml` baut den Dienst aus
`kataster/Dockerfile`. Bei einer bestehenden Installation die neuen Werte aus
`_infrastructure/.env.template` übernehmen und auf dem Zielsystem ausführen:

```bash
cd _infrastructure
docker compose up -d --build na-kataster na-backend
# Die Gateway-Timeouts wurden ebenfalls angepasst:
docker compose restart na-oathkeeper na-nginx
```

Der normale Gesamtstart (`docker compose up -d --build`) ist ebenfalls möglich.
Nginx bleibt der einzige externe Einstiegspunkt. Der Backend-Start wartet auf den
Healthcheck des Katastercontainers.

| Einstellung | Ort | Standard |
|---|---|---|
| `KATASTER_URL` | Backend/Compose | `http://na-kataster:8765` (intern festgelegt) |
| `KATASTER_TIMEOUT_SECONDS` | `.env` / Backend | `300` |
| `KATASTER_PHOTON_URL` | `.env` / Kataster | öffentlicher Photon-Demoserver |
| `KATASTER_BY_USER`, `KATASTER_BY_PASSWORD` | `.env` / Kataster | leer, optionaler berechtigter Zugang |

Nginx-Read-Timeout und Oathkeeper-Write-/Idle-Timeout sind auf 330 Sekunden gesetzt,
damit sie vor dem Backend nicht vorzeitig abbrechen. Bei Änderung des Relay-Timeouts
auch diese Werte und den UI-Timeout entsprechend abstimmen.

PNG, rohe JSON-Dateien und Cache liegen im benannten Volume `na-kataster-data`.
Die Benutzerzuordnung und das über die API gelieferte JSON liegen in MongoDB.
Beide Datenbestände zusammen sichern/aufbewahren. Es gibt derzeit keine automatische
Löschung oder Aufbewahrungsfrist; `docker compose down` erhält das Volume.
Der optionale authentifizierte Bayern-WFS wurde mangels Zugangsdaten nicht live
getestet. Weitere Hinweise zu Quellen und Datenqualität stehen in `kataster/README.md`.

## Prüfungen ohne Docker Engine

```bash
cd backend
python -m pytest

cd ../kataster
python -m unittest discover -s tests -v

cd ../_infrastructure
docker compose --env-file .env.template config --quiet
```

Backend-Tests verwenden Mongo-Mocks, die echte FastAPI-Routen und einen kontrollierten
httpx-Upstream. Sie prüfen die Weiterleitung, Eigentümerprüfung, Downloadlinks,
Validierung, Fehler und Timeouts sowie die Compose-Netzgrenzen. Die Katastertests
prüfen Adress-/Geometrielogik und den internen HTTP-Service. Diese Tests benötigen
keine laufenden Docker-Container oder externen Landesdienste.

Ein kompletter Start mit Nginx, Oathkeeper, MongoDB und Katastercontainer muss auf
einem Docker-Zielsystem verifiziert werden. Auf dem Entwicklungscomputer wird
ausdrücklich keine Docker Engine gestartet.

Ursprünglicher Integrationsprüfstand 03.11.2026: 47 Backend-Tests und 23 Katastertests bestanden;
Compose-Konfiguration erfolgreich validiert. Zusätzlich wurde „Im Schönenfelde 14,
21109 Hamburg“ über den echten lokalen Python-Katasterservice und den Backend-Relay
abgerufen: Wilhelmsburg, Flurstück 2798, Fläche 1005 m²; PNG- und JSON-Download
erfolgreich, Download durch einen anderen Benutzer mit 404 abgewiesen. Bei diesem
Smoke-Test war MongoDB durch `mongomock` ersetzt und die Identität wurde direkt am
Test-Backend gesetzt. Oathkeeper, Docker-Netze und Container wurden nicht gestartet.

Referenz für die konfigurierten Oathkeeper-Timeouts:
[Versionsschema v0.40.7](https://github.com/ory/oathkeeper/blob/v0.40.7/.schema/config.schema.json).

Frontend-Erweiterung: 23 Frontend-Tests, 49 Backend-Tests und
Frontend-Produktionsbuild erfolgreich. Frontend-Tests prüfen Admin/Installer,
Kunden-/Anlagenadresse, Übernahme, Speicherung/Wiederöffnen, Teilresultate,
Adresse-Änderungen während eines Requests und Fehlerzustände. Der echte
Lageplan-Editor ist in den Formulartests durch einen kontrollierten Test-Editor
ersetzt; eine zusätzliche visuelle Prüfung im echten Browser ließ sich in dieser
Umgebung nicht zuverlässig starten. Es wurde keine Docker Engine gestartet.
