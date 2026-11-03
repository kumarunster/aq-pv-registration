# Amelanq Netz-Anmeldung

Anmeldung von PV-Anlagen, Wallboxen und Waermepumpen bei den
Netzbetreibern in Deutschland.

Stand: 19.10.2026 - v0.1.0 (Geruest-Phase)

## Struktur

Vorbild: `projects/amelanq-zeiterfassung` (gleiche Frameworks, gleiche
Compose-Struktur, Prefix `na-`).

```
backend/            FastAPI + motor (MongoDB async)
  src/main.py       App-Start, /healthz
  src/routers/      API-Routen (v0.1: status.py - Dummy)
  src/models/       Pydantic-Modelle (noch Platzhalter)
  src/services/     database.py (motor-Client)
  src/migrations/   Schema-Migrations-Runner (noch leer)
frontend/           Vue 3 + Vite + Tailwind
  src/views/        LandingView (Dummy mit Statusanzeige), NotFoundView
  src/api/          axios-Client
_infrastructure/    docker-compose.yml, nginx, mongodb, redis, .env
docs/               ROADMAP.md (und spaeter Spezifikationen)
scripts/            Hilfs-Skripte
VERSION             Gemeinsame Version fuer Backend + Frontend
```

## Start (Dev)

```bash
cd _infrastructure
cp .env.template .env        # MONGO_PASSWORD setzen!
docker compose up -d --build
```

- Web: http://localhost:8092
- Health: http://localhost:8092/healthz
- API: http://localhost:8092/api/status, http://localhost:8092/api/docs

## Ports

- `8092` - einziger externer Port (nginx). Alle anderen Dienste laufen
  nur im internen Compose-Netz (keine Host-Ports).

## Automatische Liegenschaftskarte

Der eigenständige Dienst `na-kataster` erzeugt aus einer Adresse ein Kartenbild
(standardmäßig 60 Meter Breite) und Grundstücksinformationen. Port `8765` wird
nicht am Host veröffentlicht. Der Zugriff erfolgt über das authentifizierte
Backend-Relay unter `/api/admin/liegenschaftskarte` bzw.
`/api/installer/liegenschaftskarte`, einschließlich benutzergebundener Downloads.

Architektur, API-Beispiele, Konfiguration und Tests:
[docs/LIEGENSCHAFTSKARTE.md](docs/LIEGENSCHAFTSKARTE.md).

## Status

Geruest laeuft als Dummy. Datenmodell, Netzbetreiber-Profile,
Antragsformular und Status-Tracking folgen laut `docs/ROADMAP.md`.
