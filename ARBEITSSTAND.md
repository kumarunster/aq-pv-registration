# ARBEITSSTAND - Amelanq Netz-Anmeldung

**Stand: 21.10.2026, 12:20 · v0.3.0**

---

## 1. Was heute umgesetzt wurde

### Roadmap neu aufgebaut (docs/ROADMAP.md)
- Vorher: flache "Schritte"-Liste, veraltet (19.10.2026).
- Jetzt: Phasen 0–7 mit Status, Abnahme-Kriterien und Querschnitt.
- **Kolya-Entscheidung 20.10.2026:** Netzbetreiber-Profile (manuelle Stammdaten,
  Fristen, Erinnerungen) werden NICHT gebaut.
- Stattdessen **Phase 4 — Automatische Zuordnung**:
  - **4b. Automatische Netzbetreiber-Suche** anhand der Anlagen-Adresse
    (Datenquelle zu klären: Bundesnetzregister / Netzentstehungsregister /
    Postleitzahl-Map als Start; Backend-Service + Mongo-Cache;
    automatisch ausgefüllt, manuell überschreibbar).

- ✅ Installer-UI (Phase 3b) steht: `views/installer/LoginView.vue`,
  `InstallerLayout.vue`, `KundenView.vue`; Router-Einträge `/installer/login`,
  `/installer` mit Auth-Guard. Frontend neu gebaut, na-frontend neu gestartet,
  `http://<host>:8092/installer/login` liefert 200 (SPA rendert Login-Formular).

### Installer-Auth (Phase 3a) — partiell
- ✅ Kratos-Identity `installer@amelanq.com` (Schema `installer`),
  Passwort `Installer1234!` per Admin-API gesetzt (PUT ok, pw version 0).
- ✅ Login via Kratos 200, whoami 200, identity.id korrekt.
- ❌ `GET /api/installer/customers` → 401 trotz gültiger Session:
  Oathkeeper-Mutator setzt `X-Kratos-Identity-ID` nicht ans Backend.
  Ursache offen, Oathkeeper-Logs noch nicht ausgewertet.
- ⚠️ `check_session_url` wurde heute zwischen 4433/4434 hin- und hergeschaltet;
  aktueller Wert: `http://na-kratos:4433/sessions/whoami` (wie Zeiterfassung).
- ⚠️ Die `installer-api`-Regel wurde um 16:00 durch eine sed-Bearbeitung
  beschädigt (Mutator-`fields:`-Block ging verloren) und wurde danach
  per Python-Skript 1:1 aus der Admin-Regel wiederhergestellt.

## 2. Was NICHT gebaut wurde (gegenüber Roadmap)

- Phase 4b (Netzbetreiber-Suche): nur in Roadmap festgehalten, kein Code.
- Tests: nur `backend/tests/test_healthz.py`.
- Netzbetreiber-Profile: bewusst verworfen (Kolya-Entscheidung).

## 3. Offene Fragen / Blocker

1. **Installer-API 401**: Oathkeeper-Logs bei einem Installer-Request
   auswerten (wird die `installer-api`-Regel gematcht? granted/denied?) —
   wurde noch nicht gefahren.
2. **Netzbetreiber-Datenquelle**: welche Quelle nutzen?
   - Bundesnetzregister / Netzentstehungsregister (API-Status prüfen)
   - Netzbetreiber-Versorgungsverzeichnis
   - Fallback: manuell gepflegte PLZ→Netzbetreiber-Map in MongoDB
   → Kolya-Entscheidung abwarten, KEINE Quelle annehmen.
3. Installer-Passwort: nur im Dev-Stack gesetzt, nicht in `.env`/Doku
   (bewusst; kein Prod-Bezug).

## 4. Infrastruktur-Zustand (20.10.2026 ~18:10)

- Dev-Stack läuft auf Port 8092 (na-*); Kratos, Oathkeeper, Backend,
  Frontend, MongoDB, Redis, PgDb alle up.
- Ports: nur na-nginx 8092 extern (Regel eingehalten).
- Oathkeeper neu gestartet nach letzter Config-Änderung.

## 5. Arbeitsregeln für die Fortsetzung

- **Kein Raten:** keine URL/Feature/ID behaupten, ohne es im Code/Stack
  verifiziert zu haben. (Zwei Vorfälle heute: `/installer`-Login und
  erfundene "ZEBRID-ID" — beide waren Halluzinationen.)
- **Nichts ungefragt anlegen:** Code/Views erst nach Kolya-Freigabe.
- Produktion (timesheets.amelanq.com o.ä.) bleibt tabu; hier nur Dev.
- Tagesnotiz: `memory/2026-10-20.md` wird parallel gepflegt.

## 6. Nächste Schritte (Reihenfolge, erst nach Kolya-Freigabe)

1. Installer-API 401: Oathkeeper-Logs bei einem Installer-Request auswerten (EIN Lauf)
2. Abnahme Phase 3c: Login → 200, Kunden-CRUD mit Session, `created_by`-Filter
3. Netzbetreiber-Suche: Datenquelle mit Kolya klären, dann Service + Cache
