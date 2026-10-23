# ROADMAP — Amelanq Netz-Anmeldung

Anmeldung von PV-Anlagen, Wallboxen und Wärmepumpen bei den
Netzbetreibern in Deutschland.

**Stand: 21.10.2026 · v0.3.0 · Status: Admin-Frontend + Installer-UI (Login + Kunden) umgesetzt, Installer-API-Auth (401 trotz gültiger Session) offen, Netzbetreiber-Suche + Antragsformular offen**

> Aktualisiert am 20.10.2026 nach Abgleich mit Code und Dev-Stack.
> Vorgängerversion: 19.10.2026 (v0.2.0).

---

## Phase 0 — Gerüst ✅ ABGESCHLOSSEN (19.10.2026)

- [x] Projektstruktur 1:1 aus `amelanq-zeiterfassung` übernommen
- [x] `docker-compose.yml`, Prefix `na-`, alle Secrets aus `.env`
- [x] **Port-Check bestanden:** nur `na-nginx` (8092) nach außen
- [x] MongoDB + Redis + Backend + Frontend + Nginx
- [x] FastAPI-Skelett mit `/healthz` und `/api/status`
- [x] Vue-3-App mit Routing + Landing-View
- [x] `.env`, `.gitignore`, `README.md`

---

## Phase 1 — Datenmodell ✅ ABGESCHLOSSEN (19.10.2026)

- [x] Datenmodell nach Kolya-Spezifikation (19.10.2026):
      Firmen, Kunden, Anlagen (PV / Wallbox / Wärmepumpe)
- [x] MongoDB-Collections + Indizes (`init-mongo.js`, Migration v1)
- [x] Pydantic-Modelle + Migrations (Schema-Version 1)
- [x] CRUD-Routen: `/api/admin/companies`, `/api/admin/customers`
- [ ] **Tests** (pytest + mongomock-motor) — offen

---

## Phase 2 — Admin-Frontend ✅ UMGESETZT (19.10.2026)

- [x] Ory Kratos + Oathkeeper (Admin-Login, wie Zeiterfassung)
- [x] `frontend/src/views/admin/LoginView.vue`
- [x] `frontend/src/views/admin/AdminLayout.vue`
- [x] `frontend/src/views/admin/AdminHome.vue`
- [x] `frontend/src/views/admin/FirmenView.vue`
- [x] `frontend/src/views/admin/KundenView.vue`
- [x] Firmen-Formular (Name, Adresse, Kontakt, Signatur, Installer-ID)
- [x] Kunden-Formular (Kunde + Firmen-Auswahl + Anlagen)
- [x] Anlagen-Formular: PV (Module, MStR), Wechselrichter-Liste, Speicher
- [x] Landing-Seite mit Admin-Verlinkung
- [x] Nginx-Location `/api/admin/` → Oathkeeper

**Abnahme-Kriterien:** ✅ ALLE BESTANDEN (19.10.2026)
- [x] Alle Container `running`
- [x] `/healthz` → 200
- [x] Admin-Login + CRUD funktionieren

---

## Phase 3 — Installer-UI + API ⚠️ IN ARBEIT (Stand 20.10.2026)

**Ziel:** Installer können sich anmelden und ihre eigenen Kunden/Anlagen verwalten.

### 3a. Backend + Auth (teilweise umgesetzt)

- [x] `backend/src/routers/installer.py` — Routen `/api/installer/customers` (CRUD)
- [x] Kratos-Identity `installer@amelanq.com` (Schema `installer`)
- [x] Oathkeeper-Regel `installer-api` (Access-Rules, `cookie_session` + `header`-Mutator)
- [x] Installer-Passwort — per Kratos-Admin-API gesetzt (20.10.2026), Login funktioniert (200)
- [ ] **Installer-API 401** — `GET /api/installer/customers` liefert 401 trotz gültiger Session:
      Oathkeeper-Mutator setzt `X-Kratos-Identity-ID` nicht ans Backend.
      Nächster Schritt: Oathkeeper-Logs bei einem Installer-Request auswerten.

### 3b. Frontend ✅ UMGESETZT (21.10.2026)

- [x] `frontend/src/views/installer/LoginView.vue`
- [x] `frontend/src/views/installer/InstallerLayout.vue`
- [x] `frontend/src/views/installer/KundenView.vue`
- [x] Router-Einträge: `/installer/login`, `/installer` (mit Auth-Guard)
- [x] Nginx: `/installer/*` läuft über SPA-Fallback `location /` → frontend
- [x] Frontend neu gebaut, `http://<host>:8092/installer/login` → 200 (Login-Formular rendert)

### 3c. Abnahme-Kriterien (offen)

- [x] Installer-Login über `http://<host>:8092/installer/login` → 200 (21.10.2026)
- [ ] `GET /api/installer/customers` mit gültiger Session → 200 (Mutator setzt Header)
- [ ] Installer kann Kunden/Anlagen anlegen, die er selbst erstellt hat (`created_by` = eigene Identity-ID)
- [ ] Installer sieht **nicht** fremde Kunden/Anlagen

---

## Phase 4 — Automatische Netzbetreiber-Zuordnung ⚠️ NEU (Stand 20.10.2026)

**Kolya-Entscheidung (20.10.2026):** Netzbetreiber-Profile (manuelle Stammdaten,
Fristen, Erinnerungen) werden **nicht** gebaut. Stattdessen:

### 4a. Automatische Netzbetreiber-Suche anhand der Anlagen-Adresse

- [ ] Netzbetreiber (Verteilnetzbetreiber) automatisch aus der Anlagen-Adresse ermitteln
- [ ] Datenquelle: noch zu klären (Bundesnetzregister / Netzentstehungsregister /
      öffentliche API; Fallback: manuell gepflegte PLZ-→-Netzbetreiber-Map)
- [ ] Backend-Service `netzbetreiber.py` mit Cache (MongoDB, letzter Abfrage-Zeitstempel)
- [ ] Anzeige in Kunden-/Anlagen-Formular: Netzbetreiber automatisch ausgefüllt,
      manuell überschreibbar

### Abnahme-Kriterien (offen)

- [ ] Kunden-/Anlagen-Formular zeigt Netzbetreiber automatisch an
- [ ] Wert ist manuell überschreibbar (Feld bleibt editierbar)
- [ ] Cache-Mechanismus funktioniert (zweite Abfrage derselben Adresse ohne neuen API-Call)

---

## Phase 5 — Antragsformular (offen)

- [ ] Formular pro Anlagetyp (PV, Wallbox, Wärmepumpe)
- [ ] Anlage + Netzbetreiber zuordnen
- [ ] Antrag anlegen, Status verfolgen
- [ ] Dokumente anhängen (Anlagenblatt, Netzzugangsvertrag, …)

---

## Phase 6 — Status-Tracking (offen)

- [ ] Statusläufer je Antrag (erstellt, eingereicht, in Bearbeitung, zugestimmt, abgelehnt)
- [ ] Historie / Protokoll je Antrag
- [ ] Erinnerungen an fällige Nachtruere oder Fristen

---

## Phase 7 — Export / Bericht (offen)

- [ ] Übersicht je Kunde / je Netzbetreiber
- [ ] PDF- oder Excel-Export (Vorbild: Zeiterfassung-Export)
- [ ] Statistik: Anträge nach Anlagetyp und Region

---

## Noch offen (querschnittlich)

- **Tests**: pytest + mongomock-motor für Backend-Routen (Phase 1 + 3)
- **Installer-API 401**: Mutator setzt `X-Kratos-Identity-ID` nicht trotz gültiger Session (Phase 3a)
- **Datenmodell-Ergänzungen**: Status, Fristen, Dokumente (Phase 5–7)
- **Automatische Netzbetreiber-Zuordnung** aus Anlagen-Adresse (Phase 4)
- **Browser-Rückwärtsnavigation nach Logout** (23.10.2026): Nach dem Abmelden darf über die
  Browser-Zurück-Taste keine Seite mit Daten (z. B. `/installer/kunden`) mehr angezeigt
  werden — auch nicht aus dem BFCache. Ein Layout-Guard (`beforeEach` mit Session-Check)
  hat den Fall im Headless-Test abgedeckt, im echten Browser (Chromium, BFCache) tritt
  das Verhalten weiterhin auf. Bewusst aufgeschoben — Kolya entscheidet, wann wir es angehen.
- **Produktion**: Domain + TLS via nginx-proxy, Deployment-Strategie (später)

---

## Dev-Fixes & bekannte Probleme (20.10.2026)

- `KRATOS_COOKIE_SECRET` / `KRATOS_CIPHER_SECRET` müssen exakt 32 Zeichen sein
- `KRATOS_DB_PASSWORD` darf keine Special-Characters / Whitespace enthalten
- Docker-User braucht `docker`-Gruppe; sonst `sg docker -c "..."`
- Oathkeeper `check_session_url` muss auf den Kratos-**Public-Port** (4433) zeigen
- Oathkeeper `header`-Mutator in Access-Rules: `fields`-Liste mit `name`/`value`-Paaren
- **Status 21.10.2026**: `installer-api`-Regel ist textidentisch zur Admin-Regel (fields-Block
  vollständig, 1:1 aus Admin-Regel wiederhergestellt). Trotz gültiger Kratos-Session
  liefert `/api/installer/customers` 401 — der Mutator setzt den Header nicht ans Backend.
  Oathkeeper-Logs bei einem Installer-Request sind noch nicht ausgewertet.
