# Amelanq Netz-Anmeldung

Erfassung von Kunden und PV-Anlagen, Wallboxen und Wärmepumpen mit getrennten Admin-/Installateurbereichen. FastAPI/MongoDB-Backend, Vue-Frontend, Kratos/Oathkeeper-Authentifizierung, MinIO-Dokumentablage und separater PDF-Service.

Der Branch `auto-registry` ergänzt einen **eigenständigen Netzportal-Service** und einen **Admin-Relay** für die geprüfte Vorbereitung von PV-Netzanmeldungen. Aktueller Stand vom 4. November 2026: [Analyse, Ablauf und Grenzen](docs/AUTO-REGISTRY.md).

## Netzanmeldung

Unter **Admin → Kunden & Anlagen → Kunde bearbeiten → Anlagen → Anlage öffnen** ist bei PV-Anlagen ab Status **„In Prüfung“** der eigene Tab **„Netzanmeldung“** verfügbar (auch bei „Angemeldet“ und „Abgeschlossen“). Der Netzbetreiber wird über die Anlagenadresse und VNBdigital automatisch ermittelt. Daten prüfen und mit Prüfvermerk freigeben. Erst danach kann derselbe Admin die lokale JSON-Vorbereitung oder einen unterstützten Portalentwurf starten. Installateure können diese API nicht auslösen. Änderungen am geprüften Datenstand erfordern eine erneute Prüfung.

NRM/ENM unterstützen derzeit leere Produktentwürfe, e-netz Südhessen die initiale Strommeldung mit Standort. Mainzer unterstützt bislang ausschließlich lokale JSON-Vorbereitung. Vollständige technische Formularbefüllung und endgültiges Absenden sind nicht implementiert. Die Portal-Schreibabläufe sind noch nicht live verifiziert.

## Struktur

```text
backend/            FastAPI, MongoDB-Repositories und Admin-Relay
frontend/           Vue 3, Admin- und Installateuransichten
netzportal/         Eigenständige Portal-API, Dockerfile und Tests
_infrastructure/    Compose, Nginx, Kratos/Oathkeeper und Infrastruktur
docs/               Analyse und Funktionsbeschreibung
VERSION             Gemeinsame Version des bestehenden Projekts
```

## Konfiguration und Start auf dem Zielserver

```bash
cd _infrastructure
cp .env.template .env
cp na-netzportal/.env.example na-netzportal/.env
# Infrastruktur-Secrets, NETZPORTAL_API_KEY und Portal-Zugangspaare setzen
chmod 600 .env na-netzportal/.env
sudo install -d -o 10001 -g 10001 -m 700 na-netzportal/volume
docker compose up -d --build
```

`NETZPORTAL_API_KEY` muss zufällig und mindestens 32 Zeichen lang sein. Compose verwendet ihn für Backend und Service. Zugangspaare gehören ausschließlich in `_infrastructure/na-netzportal/.env`; reale Zugangsdaten sind nicht enthalten. Details zu Konfiguration, Persistenz und Fehlerabgleich: [AUTO-REGISTRY.md](docs/AUTO-REGISTRY.md).

Standardzugang: `http://localhost:8092`. Nginx veröffentlicht den einzigen Host-Port. Der Netzportal-Service ist ausschließlich über den Backend-Relay erreichbar, hat ein eigenes Netz und ein persistentes Journal. Docker wurde bei dieser Erweiterung lokal nicht gestartet.

## Tests

Backend und Netzportal-Service verwenden getrennte Python-Umgebungen. Der Frontend-Build läuft mit `npm ci && npm run build` im Verzeichnis `frontend`.

## Automatische Liegenschaftskarte

Der eigenständige Dienst `na-kataster` erzeugt aus einer Adresse ein Kartenbild
(standardmäßig 60 Meter Breite) und Grundstücksinformationen. Port `8765` wird
nicht am Host veröffentlicht. Der Zugriff erfolgt über das authentifizierte
Backend-Relay unter `/api/admin/liegenschaftskarte` bzw.
`/api/installer/liegenschaftskarte`, einschließlich benutzergebundener Downloads.

Architektur, API-Beispiele, Konfiguration und Tests:
[docs/LIEGENSCHAFTSKARTE.md](docs/LIEGENSCHAFTSKARTE.md).

## Status
```bash
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt -r backend/requirements-dev.txt
PYTHONPATH=backend .venv/bin/python -m pytest backend/tests -q
```

[Service-API](netzportal/README.md) · [Entwurfsformat](netzportal/docs/DRAFTS.md)
