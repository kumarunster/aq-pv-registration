# Arbeitsstand: UX/UI-Improvement-Roadmap

**Stand:** 02.11.2026 19:45
**Auftrag:** Alle Punkte aus `UX_UI_IMPROVEMENT_ROADMAP.md` umsetzen; App muss weiterlaufen.
**Status: 🟢 P2-10 + P2-11 + TASK-010 umgesetzt und live verifiziert; Test-IDs vergeben; Puppeteer-Anlauf grün**

**Fortschritt 09:01–10:05:**
- ✅ TASK-004 Lade-/Fehler-States in Listen (FirmenView + admin/KundenView + installer/KundenView)
- ✅ TASK-006 Landing-Rollenwahl (LandingView mit Admin/Installer-Buttons)
- ✅ TASK-008 Lageplan-Pflicht-Banner bei PV ohne Lageplan (roter Banner + „Jetzt erstellen"-Button)
- ✅ TASK-013 console.log aus Lageplan-Editor entfernt
- ✅ P2-9 Anlagen-Tab zeigt „+ Anlage" bei 0 Anlagen
- ✅ Frontend neu gebaut und deployed
- ✅ Acceptance-Tests: alle grün (Login, Firma speichern/löschen, ConfirmDialog, etc.)

---

## ✅ Test-IDs + frischer Puppeteer-Anlauf (02.11.2026 18:45–19:00)

- **Test-IDs in `FormCustomer.vue`** (28 IDs): `#customer-form`, `#customer-form-save`, `#customer-form-cancel`, `#cust-firstname/lastname/address-street/plz/city/phone/email/iban`, `#cust-company`, `#plant-search`, `#plant-status-filter`, `#plant-add`, `#plant-anlagetyp`, `#plant-kwp/kw/kwh`, `#plant-gemarkung/flur/flurstueck`, `#plant-panel-*`, `#plant-inverter-N-*`, `#plant-battery-*`, `#plant-lageplan-create/edit`, `#plant-notes`, u.a.
- **Puppeteer-Anlauf grün (`scripts/verify_p211_final.mjs`):** Login → `#customer-form` → alle Felder per ID gefüllt → Firma gewählt → `#customer-form-save` → POST 201 → Mongo-Audit-Felder → Audit-Zeile in Liste sichtbar
- **Test-Daten in Mongo:** „Christof Kreuter“ (18:24), „Sebastian Rose“ (18:39), „P211Test 879731“ (18:41) — auf Wunsch bereinigen
- **Debug-Instrumentierung entfernt, Frontend sauber neu gebaut** (Bundle ohne `console.log`)

---

## ✅ Heute umgesetzt (02.11.2026, uncommitted)

- **P2-10 Firmen-Karte: Kunden/Anlagen-Zusammenfassung** — ✅ fertig + verifiziert
  - Backend: `GET /api/admin/companies/stats` (Aggregation über `plants[].company_id`)
  - Bugfix: fehlendes `await` bei Mongo-Aggregation → 500 behoben
  - Frontend: FirmenView zeigt `👥 X Kunden · 🔌 Y Anlagen`
- **P2-11 Kundenliste: „Zuletzt geändert“ / „Erstellt von“** — ✅ Code fertig + **live verifiziert**
  - Backend: `customers.create()` setzt `created_at`/`updated_at`/`updated_by`; `update(..., updated_by)` setzt beide
  - Router admin + installer übergeben Kratos-Identity als `updated_by`
  - Frontend: admin/KundenView + installer/KundenView zeigen Audit-Zeile
  - **Verifiziert (18:41 Puppeteer + 18:24/18:39 manuell):** POST 201 → Kunde in Mongo mit Audit-Feldern → Liste zeigt „Zuletzt geändert: 2.11.2026 · von 21d4557b-…"
- **TASK-010 ZEREZ pro Inverter** — ✅ fertig
  - `FormCustomer.vue`: `zerezState` Map pro Inverter-Index, Dropdown direkt unter jeder Inverter-Zeile
- **TASK-001 Dirty-Data-Guard** — ✅ fertig (vorher unrichtig als „offen“ gelistet)
- **Entfernt auf Kolyas Wunsch:** TASK-012 (Lageplan mobil), TASK-007 (`/lageplan`-Schutz)

## 🐞 ~~Offener Bug: Kunden-Formular speichert nicht via UI~~ — AUFGEKLÄRT (02.11. 18:40)

**Es gab keinen App-Bug.** Der Save funktioniert seit dem Frontend-Rebuild (08:05) — verifiziert durch Kolyas manuelle Tests:
- 18:24 Kunde „Christof Kreuter“ → POST 201 + Toast + Mongo-Audit-Felder
- 18:39 Kunde „Sebastian Rose“ → POST 201 + Toast + Mongo-Audit-Felder

Mein Puppeteer-Test-Harness triggerte die Vue-`save()`-Funktion nicht korrekt (Test-Problem, keine Ursache in der App). Debugging-Instrumentierung wurde wieder entfernt, Frontend neu gebaut.

---

## ✅ Bereits umgesetzt (uncommitted in Workspace)

| Task | Beschreibung | Status |
|---|---|---|
| TASK-002 | `components/ConfirmDialog.vue` (Teleport, role=dialog, aria-modal, Esc, Focus, Overlay-Klick) | ✅ Code fertig |
| — | Migration aller `alert()`/`confirm()` → ConfirmDialog/Toast (`grep "alert(\|confirm("` = 0 Treffer) | ✅ FirmenView, KundenView (admin+installer), FormCompany, FormCustomer, LageplanEditor |
| TASK-003 | `toast.success` nach Speichern/Löschen/Upload/PDF | ✅ 7+ Treffer |
| TASK-009 | Firmen-Editor-Bug: `editing`-Ref in FirmenView, `:initial="editing || null"` | ✅ Code fertig |
| — | Toast-System (`api/toast.js` + `ToastContainer.vue` mit Teleport + role=status) | ✅ |

**Geänderte Dateien (git status):**
- `frontend/src/components/admin/FormCompany.vue`
- `frontend/src/components/admin/FormCustomer.vue`
- `frontend/src/components/lageplan/LageplanEditor.vue`
- `frontend/src/views/admin/FirmenView.vue`
- `frontend/src/views/admin/KundenView.vue`
- `frontend/src/views/installer/KundenView.vue`
- Neu: `frontend/src/components/ConfirmDialog.vue`, `UX_UI_IMPROVEMENT_ROADMAP.md`, `scripts/ux-review3.mjs`, `media/`

---

## 🚀 Save-Bug FIX (02.11.2026 08:05)

**Root-Cause:** Der laufende `na-frontend`-Container lief mit einem **alten Build**
(`index-C1Rcq20z.js`, Build vom 01.11. 06:19), der einen `/logout`-Trigger bei
Firmen-Speichern enthielt. Der aktuelle Workspace-Code (mit den UX-Patches vom
31.10.) war **nie deployed**.

**Fix:** `docker compose build na-frontend --no-cache && up -d na-frontend`
→ Frischer Build `index-CDKrGo4t.js` → Bug weg.

**Verifiziert (Puppeteer + Trace + Mongo):**
- ✅ `POST /api/admin/companies` → 201
- ✅ Toast „✅ Firma gespeichert“ erscheint
- ✅ Neue Firma ist in der Liste sichtbar
- ✅ Kein `/logout`-Request im Trace
- ✅ Firma in Mongo gespeichert (`Testfirma *`)
- ✅ Test-Daten aus Mongo bereinigt

**Abnahme-Test-Ergebnis (acceptance4.mjs):**
- ✅ Login, Installer-Login
- ✅ Firma speichern + Toast + in Liste
- ✅ Bearbeiten-Formular öffnet (Titel „Firma bearbeiten“)
- ✅ Name vorgefüllt beim Bearbeiten
- ✅ ConfirmDialog öffnet/schließt (Esc + Button)
- ✅ Firma gelöscht (Confirm-Button)
- ✅ Kunden-Suche vorhanden
- ✅ Keine JS-Seitenfehler

---

## ⏭️ Noch zu implementieren (Phase 2/3)

| Phase | Tasks | Status |
|---|---|---|
| 2 (P1) | TASK-001 Dirty-Data-Guard (`beforeunload` in FormCustomer/FormCompany + ConfirmDialog bei Schließen/Navigation) | ✅ fertig (02.11.) |
| 2 (P1) | TASK-004 Lade-/Fehler-States in Listen (3 Views: error-Banner + Retry) | ✅ fertig (alle 3 Views) |
| 2 (P1) | TASK-005 „Zurück"-Doppelung auflösen (Kopfzeile „✕ Formular schließen") | ✅ bereits konsistent (31.10.) |
| 2 (P1) | TASK-006 Landing-Rollenwahl („Admin anmelden"/"Installer anmelden" statt Direkt-Links) | ✅ fertig |
| 2 (P1) | TASK-008 Lageplan-Pflicht-Banner bei PV ohne Lageplan | ✅ fertig (roter Banner + „Jetzt erstellen"-Button) |
| 2 (P1) | TASK-011 Lageplan-Dialog ARIA/Fokus/Esc | ✅ bereits in ConfirmDialog |
| 3 (P2/P3) | TASK-010 ZEREZ pro Inverter | ✅ fertig (02.11.) |
| 3 (P2/P3) | TASK-012 Lageplan mobil (Groß!) | ❌ entfernt (2.11., auf Wunsch von Kolya) |
| 3 (P3) | TASK-013 console.log entfernen | ✅ fertig |
| 3 (P3) | TASK-014 404-Farben anpassen | ❌ offen (Phase 3) |
| 3 (P3) | TASK-015 Spinner bei langen Operationen | ❌ offen (Phase 3) |
| 3 (P3) | TASK-016 Installer-Guard aufräumen | ❌ offen (Phase 3) |
| 3 (P3) | TASK-007 `/lageplan`-Schutz (optional) | ❌ entfernt (2.11., auf Wunsch von Kolya) |
| P2-9 | Anlagen-Tab bei 0 Anlagen: „+ Anlage" statt klickbaren Tabs | ✅ fertig |
| P2-10 | Firmen-Karte: Kunden/Anlagen-Zusammenfassung | ✅ fertig + verifiziert (02.11.) |
| P2-11 | Kundenliste: „Zuletzt geändert" / "Erstellt von" | ✅ fertig + live verifiziert (02.11.) |
| — | Test-IDs in FormCustomer + frischer Puppeteer-Anlauf | ✅ fertig (02.11. 19:00) |

---

## 📌 Nächste Schritte (in Reihenfolge)

1. **Bugfix: Kunden-Formular speichert nicht via UI** (blockiert P2-11-Verifizierung)
2. **P2-11 verifizieren** (API-Direkttest + UI)
3. **Phase-3-Tasks** nach Priorität:
   - TASK-014 404-Farben (15 Min)
   - TASK-015 Spinner (30 Min)
   - TASK-016 Installer-Guard aufräumen (30 Min)
4. Komplettes Puppeteer-Test-Suite + Screenshots
5. Roadmap-Status aktualisieren + commit (NUR Quellcode; Gedächtnisdateien via Tarball-Backup)

## Dev-Stack

- Compose: `_infrastructure/docker-compose.yml` (Projekt `na-`, Port 8092)
- Login: admin@amelanq.com / Admin1234!
- Frontend-Container: `na-frontend`, Build: `docker compose -f _infrastructure/docker-compose.yml build na-frontend --no-cache`
- Puppeteer: `puppeteer-core` + Chrome `/home/moltbot/.cache/puppeteer/chrome/linux-146.0.7680.76/chrome-linux64/chrome`
  (args: `--no-sandbox --disable-dev-shm-usage --disable-gpu`)
