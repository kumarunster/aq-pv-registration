# UI/UX-Review — Amelanq Netz-Anmeldung

**Stand: 30.10.2026, 21:30 · Dev-Stack 8092 · Headless-Chromium 1440×900**

---

## Was gut funktioniert

| Bereich | Status |
|---|---|
| Login (Admin + Installer) | ✅ Error-State sichtbar, Redirect funktioniert |
| Kundenliste: Suche + Status-Filter + Pagination | ✅ 25/Seite, Debounce 300 ms |
| Kunden-Karte: Zusammenfassung statt 200 Chips | ✅ 258 px (vorher 8918 px) |
| Formular: Kunde-Tab / Anlagen-Tab | ✅ Tabs oben, klare Struktur |
| Anlagen-Tab: Liste ↔ Editor (v-if/v-else) | ✅ Editor ersetzt Liste, ← Zurück |
| Suchleiste + Status-Select + „+ Anlage" in einer Zeile | ✅ gleiche Höhe (34–38 px), gleiche Font |
| Speichern/Abbrechen-Button: sichtbar ohne Scrollen | ✅ pos y=738 px (viewport 900 px) |
| Leerzustand: „Keine Kunden gefunden" | ✅ |
| Nav: ⚡ Logo → Home, 🏢 Firmen, 👤 Kunden, Abmelden | ✅ |

---

## Verbesserungsvorschläge (priorisiert)

### P0 — Dringend (beim nächsten Testlauf störend)

1. **Unsaved-Changes-Warnung fehlt.**
   - Im Formular ein Feld ändern → Seite verlassen → **keine Warnung**, Daten verloren.
   - Fix: `beforeunload`-Handler + interne Navigation: `router.beforeEach` prüft
     `formDirty` → Confirm-Dialog „Änderungen verwerfen?".
   - Aufwand: ~30 Min.

2. **Konsole: 404 + 400 Fehler bei jedem Login.**
   - `Failed to load resource: 404` und `400 (Bad Request)` — vermutlich
     Oathkeeper- oder Kratos-Call, der nicht passt.
   - Fix: DevTools → Network → den 404/400-Request identifizieren.
   - Aufwand: 10–15 Min. (Diagnose)

3. **„Formular schließen"-Button fehlt im Header.**
   - In der Kundenliste: „+ Neuer Kunde" wird zu „Formular schließen",
     aber **innerhalb des Formulars** gibt es keinen „Schließen"-Button
     außerhalb von „Abbrechen" (der macht `cancel`).
   - „Abbrechen" und „Formular schließen" sind semantisch doppelt.
   - Fix: Im Formular-Header rechts neben den Tabs einen „✕ Schließen" setzen,
     der `emit('cancel')` triggert. „Abbrechen" am Formular-Ende bleibt
     als sekundäre Aktion.
   - Aufwand: 10 Min.

### P1 — Wichtig (beim nächsten Feature-Release)

4. **Anlagen-Editor: 2016 px hoch — viel Scrollen.**
   - Der PlantForm hat viele Abschnitte: Status, Adresse, Grundstueck,
     Anlagetyp, kW, PV-Module, MStR, Wechselrichter, Speicher, Checkliste,
     Lageplan, Notizen.
   - Fix: **Accordions** pro Abschnitt (aufzuklappen), Standard: nur
     Status + Adresse + Anlagetyp sichtbar, Rest collapsed.
   - Aufwand: 45–60 Min.

5. **Kein Fortschrittsbalken / „Gespeichert" Indikator.**
   - Nach dem Speichern: Toast „Gespeichert" (existiert) — aber kein
     visueller Marker, dass der Kunde aktuell bearbeitet wird.
   - Fix: Im Formular-Header neben „Kunde bearbeiten" einen
     „● ungespeicherte Änderungen" Indicator, wenn `formDirty`.
   - Aufwand: 15 Min.

6. **Anlagen-Liste: keine Sortierung.**
   - Tabelle ist in Einfüge-Reihenfolge. Bei 200 Anlagen:
     nach Adresse, Status, oder kWp sortierbar?
   - Fix: Column-Header klickbar → `sortKey` + `sortDir` State.
   - Aufwand: 30 Min.

7. **Mobile (375×812): Kundenliste und Formular.**
   - Screenshots zeigen: Layout bricht nicht, aber die Anlagen-Tabelle
     wird sehr schmal. Der „+ Anlage"-Button und der Status-Select
     könnten unter die Suchleiste.
   - Fix: `flex-wrap` auf der Suchleiste bei `md:`-Breakpoint,
     Tabelle → `overflow-x-auto` Wrapper.
   - Aufwand: 20 Min.

### P2 — Schön-hätte (nächstes Sprint)

8. **Kundenliste: „Neuer Kunde" Button ist oben rechts, aber
   bei 25 Kunden pro Seite nicht sofort sichtbar auf kleinen Screens.**
   - Fix: Sticky-Header für die Listen-Toolbar (Suche + Button).
   - Aufwand: 10 Min.

9. **Anlagen-Tab: „Anlagen (200)" — bei 0 Anlagen: „Anlagen (0)".**
   - Kein Problem, aber der Tab-Button sollte bei 0 Anlagen
     nicht klickbar sein (oder „+ Anlage" direkt zeigen).
   - Aufwand: 5 Min.

10. **Firmen-View: kein Zusammenhang mit Kunden.**
    - Wenn ich eine Firma bearbeite, sehe ich nicht, wie viele
      Kunden/Anlagen sie hat.
    - Fix: In der Firmen-Karte eine Zusammenfassung
      „X Kunden · Y Anlagen" (serverseitig aggregiert).
    - Aufwand: 30 Min.

11. **Kein „Letzte Änderung" / „Erstellt von" in der Kundenliste.**
    - Bei 200+ Kunden: wer hat wann geändert?
    - Fix: `updated_at` + `updated_by` im Backend, in der Karte anzeigen.
    - Aufwand: 30 Min. (Backend + Frontend)

12. **Lageplan-Pflicht: ⚠ in der Tabelle, aber kein direkter
    „Jetzt erstellen"-Link.**
    - Fix: Im Editor: wenn `anlagetyp === 'pv'` und `!lageplan`,
      ein roter Banner „⚠ Lageplan fehlt" mit Button „Jetzt erstellen".
    - Aufwand: 15 Min.

---

## Roadmap (nächste 2 Sprints)

### Sprint 1 (P0 + P1, ~3–4 h)
- [ ] **P0-1:** Unsaved-Changes-Warnung (`beforeunload` + router-Guard)
- [ ] **P0-2:** 404/400-Konsole-Fehler identifizieren + fixen
- [ ] **P0-3:** „✕ Schließen" im Formular-Header
- [ ] **P1-4:** Accordions im Anlage-Editor (Status/Adresse/Typ sichtbar, Rest collapsed)
- [ ] **P1-5:** „● ungespeicherte Änderungen" Indicator
- [ ] **P1-6:** Anlagen-Tabelle: Sortierung (Adresse, Status, kWp)
- [ ] **P1-7:** Mobile: `overflow-x-auto` auf Tabelle, `flex-wrap` auf Suchleiste

### Sprint 2 (P2, ~2–3 h)
- [ ] **P2-8:** Sticky-Header für Listen-Toolbar
- [ ] **P2-9:** Anlagen-Tab bei 0 Anlagen: „+ Anlage" statt klickbaren Tabs
- [ ] **P2-10:** Firmen-Karte: Kunden/Anlagen-Zusammenfassung
- [ ] **P2-11:** Kundenliste: „Letzte Änderung" + „Erstellt von"
- [ ] **P2-12:** Lageplan-Pflicht: roter Banner im Editor mit „Jetzt erstellen"

---

## Screenshots

MEDIA:/home/moltbot/clawd/media/browser/ux-review2/01-landing.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/02-admin-login.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/05-kunden-liste.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/06-form-kunde.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/07-anlagen-liste.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/08-anlage-editor-top.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/11-leerzustand.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/15-mobile-login.png
MEDIA:/home/moltbot/clawd/media/browser/ux-review2/16-mobile-kunden.png
