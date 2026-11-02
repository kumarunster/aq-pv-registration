# UX/UI-Verbesserungs-Roadmap — Amelanq Netz-Anmeldung

**Stand:** 31.10.2026 · Dev-Stack 8092 · Headless Chromium 1440×900 + 375×812
**Nachfolger:** `docs/UI-UX-REVIEW-30.10.2026.md` (deren Punkte wurden umgesetzt und hier neu bewertet)
**Methode:** Code-Lesung aller Views/Komponenten + 22 Browser-Screenshots (`media/browser/ux-review3/`) + Live-Tests (Login-Flow, Suche, Leerzustand, internen Navigation mit Dirty-Data)

---

## 1. Executive Summary

**Gesamtbewertung: 3 — Akzeptabel.** Die Anwendung ist in allen Kern-Workflows funktionsfähig und nach der UI/UX-Phase vom 30.10.2026 deutlich konsistenter als zuvor (identische Formularstruktur in allen drei Rollen, konsistente Feld-Höhen, klare Button-Hierarchie, Toast-System vorhanden).

**Stärken:**
- Klare Navigation (Sticky-Header, aktive Route markiert)
- Kundenliste mit Suche + Status-Filter + Pagination + Zusammenfassung statt 200 Chips
- Formular mit Tabs (Kunde/Anlagen), Accordions, Status-Stepper, ZEREZ-Typeahead
- Lageplan-Editor mit Undo/Redo, Text-Edit im Canvas, PDF-Export
- Login-Fehler-State sichtbar, Redirect funktioniert

**Schwächen (kritisch):**
1. **Datenverlust bei interner Navigation:** Formular ändern → Nav-Link → keine Warnung, Änderungen verloren. `beforeunload` existiert, aber kein `beforeRouteLeave`-Guard. *(Puppeteer-Test bestätigt: kein Dialog.)*
2. **Kein Erfolgs-Feedback:** Nur `toast.error(...)` wird genutzt. Nach Speichern/Löschen/Anlegen/PDF: **keine Bestätigung**.
3. **`alert()`/`confirm()` statt Dialoge** an 6 Stellen (unbrandbar, nicht testbar, kein Fokus-Management).
4. **Lade-/Fehlerzustände in Listen fehlen:** API-Fehler → leere Liste ohne Hinweis (`catch` → nur `console.error`).
5. **`/lageplan` ohne Session-Schutz öffentlich erreichbar** (Standalone-Editor ohne Anlage-Kontext).

**Höchste Hebelwirkung:** Phase 1 (Dirty-Data-Guard, Dialog-Komponente, Toast-Konsistenz, `/lageplan`-Schutz, Firmen-Editor-Bug) — ~3 h Aufwand für ein klares Usability-Upgrade.

---

## 2. Application Overview

**Zweck:** Erfassung und Verwaltung von Netz-Anmeldungen für PV-Anlagen, Wallboxen und Wärmepumpen (Kunde → Anlagen → Checkliste → Lageplan → PDF).

**Rollen:**
- **Admin** (`/admin/*`): Firmen + Kunden + Anlagen, volle Rechte
- **Installer** (`/installer/*`): eigene Kunden (kein Firmen-Select), Status nicht änderbar
- **Öffentlich** (`/`): Landing-Page mit Rollen-Einstieg

**Technologien:** Vue 3 (Composition API), vue-router 4, Tailwind CSS, vue-konva (Lageplan), Ory Kratos (Auth), Oathkeeper (Rollen-Header), FastAPI, MongoDB, MinIO, WeasyPrint.

**Design-System:** Keines vorhanden — handgefertigte Tailwind-Klassen, lokale `.input`-Styles pro Komponente, keine zentralen Design-Tokens.

### Anwendungsinventar

| Bereich | Pfad |
|---|---|
| Landing | `views/LandingView.vue` (`/`) |
| Admin-Login | `views/admin/LoginView.vue` (`/admin/login`) |
| Admin-Layout/Nav | `views/admin/AdminLayout.vue` (`/admin`, `/admin/firmen`, `/admin/kunden`) |
| Firmen | `views/admin/FirmenView.vue`, `components/admin/FormCompany.vue` |
| Kunden | `views/admin/KundenView.vue`, `components/admin/FormCustomer.vue` (1069 Zeilen) |
| Installer | `views/installer/InstallerLayout.vue`, `views/installer/KundenView.vue`, `views/installer/LoginView.vue` |
| Lageplan | `views/lageplan/LageplanView.vue`, `components/lageplan/LageplanEditor.vue`, `LageplanStage.vue`, `LageplanElement.vue`, `useLayoutStore.js` |
| Toasts | `components/ToastContainer.vue`, `api/toast.js` |
| Auth | `api/auth.js` |
| 404 | `views/NotFoundView.vue` |

**Kern-Workflows:**
1. Admin: Login → Firma anlegen → Kunde anlegen → Anlage erfassen (Typ, ZEREZ, Checkliste, Lageplan) → speichern
2. Installer: Login → eigene Kunden anlegen/erfassen
3. Lageplan: Dialog aus Anlage → Hintergrundbild → zeichnen → speichern → PDF

---

## 3. UX/UI Assessment

| Dimension | Bewertung | Hauptbefunde |
|---|---|---|
| Navigation | 4 | Klarer Sticky-Nav, aktive Route markiert; aber: Landing verlinkt direkt auf Admin-Routen (führt über Login), interne Formular-Navigation verliert Dirty-Data, `/lageplan` ohne Schutz |
| Informationsarchitektur | 4 | Logisch (Firmen → Kunden → Anlagen → Lageplan), Tabs + Accordions gut strukturiert; Firmen-View ohne Kunden-/Anlagen-Zusammenfassung |
| Visuelle Hierarchie | 4 | Konsistent (gelber Primary, graue Secondary, h-9 Felder); aber zwei „Zurück“-Konzepte im Formular, Emoji-Icons ohne konsistentes Farbsystem |
| Interaktionsdesign | 3 | `alert()`/`confirm()` statt Dialoge, kein Erfolgs-Toast; ZEREZ-Typeahead nur ein Dropdown für alle Inverter |
| Formular-Usability | 4 | Pflichtfelder markiert, Dirty-Indikator (●), Vorvalidierung beim Speichern; aber keine Inline-Feld-Validation, kein Lade-Zustand beim Speichern außerhalb des Button-Texts |
| Workflow-Effizienz | 3 | Kompletter Flow ohne unnötige Hürden; Lageplan-Pflicht erst beim Speichern erzwungen (spätes Feedback), Anlagen-Editor bei vielen Anlagen viel Scrollen (Pagination vorhanden) |
| Design-Konsistenz | 4 | Alle 3 Views identisch aufgebaut; kleinere Ausreißer: Lageplan-Dialog-Buttons, 404-Page andere Farbpalette |
| System-Feedback | 2 | **Schwächste Dimension**: nur `toast.error`, kein `toast.success`, List-Views ohne Error-Zustand, PDF-Export via `alert()` |
| Responsiveness | 3 | Mobile: Listen ok, Formular 1-spaltig ok; Anlagen-Tabelle `min-w-[600px]` → horizontales Scrollen; Lageplan-Editor (1100×720) auf Mobile kaum bedienbar |
| Barrierefreiheit | 2 | **Schwächste Dimension**: `alert()`/`confirm()` nicht tastaturbedienbar in Dialog-Kontext, keine ARIA-Rollen bei Tabs/Accordions/Stepper, kein Fokus-Management im Lageplan-Dialog, kein Esc-Handling |

**Skala:** 1 schlecht · 2 unter Erwartung · 3 akzeptabel · 4 gut · 5 herausragend

---

## 4. Identifizierte Usability-Probleme

### Problemübersicht

| ID | Bereich | Problem | Schwere | Aufwand | Evidenz |
|---|---|---|---|---|---|
| UX-001 | Formular-Navigation | Interne Navigation verliert ungespeicherte Änderungen ohne Warnung | Kritisch | Klein | Technisch verifiziert (Puppeteer: dirty → Nav → keine Warnung) |
| UX-002 | System-Feedback | Kein Erfolgs-Feedback (Speichern, Löschen, Anlegen, PDF) | Hoch | Klein | Beobachtet (nur `toast.error` existiert) |
| UX-003 | Dialoge | `alert()`/`confirm()` in 6 Stellen | Hoch | Mittel | Beobachtet (Code-Lesung) |
| UX-004 | List-Views | Keine Lade- und Fehlerzustände | Hoch | Klein | Beobachtet (Code: `catch → console.error`) |
| UX-005 | Formular-Kopfzeile | Zwei parallele „Zurück“-Konzepte | Mittel | Klein | Beobachtet (Screenshot 10-kunde-formular) |
| UX-006 | Landing | Verlinkt auf geschützte Routen ohne Kontext | Mittel | Klein | Beobachtet (Screenshot 01-landing) |
| UX-007 | Auth | `/lageplan` ohne Session-Schutz (vorab aus Sicherheitsbewertung entnommen, Kolya 31.10.2026) | Gering | Klein | Beobachtet (Browser-Test: rendert ohne Login) |
| UX-008 | Anlage-Editor | Lageplan-Pflicht erst beim Speichern erzwungen | Mittel | Klein | Beobachtet (Code: `save()` prüft erst am Ende) |
| UX-009 | Firmen-View | „Bearbeiten“ zeigt nie editierte Daten (Bug) | Hoch | Klein | Technisch verifiziert (Code: `editCompany` setzt `initial` nicht) |
| UX-010 | ZEREZ | Ein Dropdown für alle Inverter | Mittel | Mittel | Beobachtet (Code: `zerezOpen`/`activeZerezIndex` global) |
| UX-011 | Lageplan-Dialog | Kein ARIA, kein Fokus-Management, kein Esc | Hoch | Klein | Beobachtet (Code: Teleport-Div ohne ARIA) |
| UX-012 | Mobile | Lageplan-Editor nicht mobil nutzbar | Mittel | Groß | Beobachtet (Stage fix 1100×720, keine Responsive-Logik) |
| UX-013 | Lageplan-Code | `console.log('[LP] ...')` in Prod-Code | Gering | Klein | Beobachtet (Zeilen 278, 281, 537, 541) |
| UX-014 | 404-Seite | Andere Farbpalette als Rest der App | Gering | Klein | Beobachtet (Screenshot 16-notfound) |
| UX-015 | Formular | Kein visuelles „Speichern“-Feedback (Spinner fehlt) | Gering | Klein | Beobachtet (nur Text „Speichert…“) |
| UX-016 | Installer-Layout | Doppel-Session-Check (`beforeEach` + `beforeEnter`) | Gering | Klein | Beobachtet (Code, ARBEITSSTAND.md Punkt 3.1) |

---

### UX-001 — Interne Navigation verliert ungespeicherte Änderungen

**Betroffener Bereich:** `FormCustomer.vue`, `KundenView.vue` (Admin + Installer), `FormCompany.vue`

**Aktuelles Verhalten:** `beforeunload` warnt nur beim Browser-Verlassen. Klick auf „🏢 Firmen“ in der Nav oder „← Zurück“ führt **ohne Warnung** zur Liste — alle Änderungen verloren.

**Nutzer-Impakt:** Hohe Datenverlust-Risiko bei langem Anlagen-Ausfüllen.

**Evidenz:** Technisch verifiziert — Puppeteer: Kunde öffnen, Feld ändern, „🏢 Firmen“ klicken → URL wechselt, kein Dialog, keine Warnung.

**UX-Prinzipien:** Fehlervermeidung, „Machen, was der Nutzer erwartet“ (Nielsen #8, #1)

**Empfohlene Verbesserung:** `onBeforeRouteLeave` im Formular, der bei `formDirty && !saving` einen `ConfirmDialog` triggert.

**Schwere:** Kritisch · **Aufwand:** Klein (~30 Min) · **Abhängigkeit:** TASK-002 (ConfirmDialog)

---

### UX-002 — Kein Erfolgs-Feedback

**Betroffener Bereich:** Alle Views mit Aktionen

**Aktuelles Verhalten:** `api/toast.js` definiert `success/error/info`; nur `error` wird genutzt. Nach erfolgreichem Speichern: keine Bestätigung.

**Nutzer-Impakt:** Nutzer muss selbst prüfen, ob die Aktion geklappt hat.

**Evidenz:** Beobachtet — `toast.success` kommt nie vor im Code.

**UX-Prinzipien:** System-Status-Sichtbarkeit (Nielsen #1)

**Empfohlene Verbesserung:** `toast.success(...)` nach jeder erfolgreichen Mutation.

**Schwere:** Hoch · **Aufwand:** Klein (~20 Min)

---

### UX-003 — `alert()`/`confirm()` statt Dialoge

**Betroffene Stellen (vollständig, Code-Lesung):**
- `views/admin/FirmenView.vue:85` — `alert('Löschen fehlgeschlagen: ...')`
- `views/admin/KundenView.vue:210` — `confirm(...)` bei Kunden-Löschen
- `views/installer/KundenView.vue:151,156` — `confirm(...)` + `alert(...)`
- `components/admin/FormCompany.vue:105` — `alert('Speichern fehlgeschlagen: ...')`
- `components/admin/FormCustomer.vue:584` — `alert('Upload fehlgeschlagen: ...')`
- `components/lageplan/LageplanEditor.vue:398` — `alert('PDF-Fehler: ...')`

**Problem:** Blockierende System-Dialoge — unbrandbar, nicht testbar, kein Fokus-Management.

**UX-Prinzipien:** Konsistenz, Barrierefreiheit (WCAG 2.1.2, 4.1.2)

**Empfohlene Verbesserung:** Zentrale `ConfirmDialog`-Komponente + Toast-Integration.

**Schwere:** Hoch · **Aufwand:** Mittel (~2 h inkl. Migration)

---

### UX-004 — Keine Lade- und Fehlerzustände in Listen

**Betroffener Bereich:** `KundenView.vue` (Admin + Installer), `FirmenView.vue`

**Aktuelles Verhalten:** `catch` → nur `console.error`; bei API-Fehler: leere Liste, Ursache unsichtbar.

**UX-Prinzipien:** System-Status-Sichtbarkeit (Nielsen #1), Fehlererholung

**Empfohlene Verbesserung:** `error`-State + roter Banner + „Erneut versuchen“.

**Schwere:** Hoch · **Aufwand:** Klein (~30 Min für alle 3 Views)

---

### UX-005 — Zwei parallele „Zurück“-Konzepte

**Betroffener Bereich:** `FormCustomer.vue`, `FormCompany.vue`

**Aktuelles Verhalten:** Kopfzeile „← Zurück“ (12px) + Fußzeile „Abbrechen“ (14px), beide triggern `emit('cancel')`.

**UX-Prinzipien:** Konsistenz, Minimierung der kognitiven Last

**Empfohlene Verbesserung:** Ein Verlassen-Konzept: Kopfzeile „✕ Formular schließen“, Fußzeile „Abbrechen“ (oder umgekehrt).

**Schwere:** Mittel · **Aufwand:** Klein (~15 Min)

---

### UX-006 — Landing verlinkt auf geschützte Routen

**Betroffener Bereich:** `LandingView.vue`

**Aktuelles Verhalten:** Buttons „Firmen“/„Kunden & Anlagen“ leiten auf `/admin/*` — ohne Session: Redirect zu Login, Kontext verloren.

**Empfohlene Verbesserung:** Rollenwahl „Admin anmelden“/„Installer anmelden“, optional mit `next`-Parameter.

**Schwere:** Mittel · **Aufwand:** Klein (~20 Min)

---

### UX-007 — `/lageplan` ohne Session-Schutz

**Betroffener Bereich:** `router/index.js`, `LageplanView.vue`

**Aktuelles Verhalten:** `/lageplan` rendert ohne Login — jeder kann Editor öffnen (Screenshot 18 bestätigt).

**Anmerkung (31.10.2026, Kolya):** Vorerst nicht als Sicherheitslücke betrachten — der Route dient dem Test der Lageplan-Integration und wird nicht öffentlich beworben. Aufgabe bleibt offen, falls die Route später entfernt oder geschützt wird.

**Empfohlene Verbesserung (optional):** Route entfernen oder `beforeEnter`-Guard.

**Schwere:** Gering · **Aufwand:** Klein (~15 Min)

---

### UX-008 — Lageplan-Pflicht erst beim Speichern

**Betroffener Bereich:** `FormCustomer.vue` (`save()`), Anlage-Editor

**Aktuelles Verhalten:** PV ohne Lageplan → erst beim „Kunde anlegen“-Klick: `toast.error`. Spätes Feedback.

**Empfohlene Verbesserung:** Roter Banner „⚠️ Lageplan fehlt“ mit „Jetzt erstellen“-Button im Editor.

**Schwere:** Mittel · **Aufwand:** Klein (~15 Min)

---

### UX-009 — Firmen-Editor: „Bearbeiten“ zeigt nie editierte Daten (Bug)

**Betroffener Bereich:** `FirmenView.vue`

**Aktuelles Verhalten:** `editCompany(c)` setzt nur `showForm = true`; `FormCompany` bekommt `:initial="null"` — Formular zeigt immer „Neue Firma“.

**Evidenz:** Technisch verifiziert (Code-Lesung).

**Empfohlene Verbesserung:** `editing`-Ref einführen, analog zum `KundenView.vue`-Muster.

**Schwere:** Hoch (Bug) · **Aufwand:** Klein (~20 Min)

---

### UX-010 — ZEREZ-Typeahead: ein Dropdown für mehrere Inverter

**Betroffener Bereich:** `FormCustomer.vue` (PlantForm)

**Aktuelles Verhalten:** `zerezOpen`/`activeZerezIndex` global im PlantForm — bei schnellem Wechsel kann Dropdown unter falschem Feld erscheinen.

**Empfohlene Verbesserung:** `zerezState` pro Inverter-Index.

**Schwere:** Mittel · **Aufwand:** Mittel (~1 h)

---

### UX-011 — Lageplan-Dialog: kein ARIA, kein Fokus, kein Esc

**Betroffener Bereich:** `FormCustomer.vue` (Lageplan-Dialog, Teleport)

**Aktuelles Verhalten:** Einfaches `div` ohne `role="dialog"`, `aria-modal`, Fokus-Fallback, Esc.

**UX-Prinzipien:** WCAG 2.4.2, 2.1.1, 4.1.2

**Empfohlene Verbesserung:** `role="dialog" aria-modal="true"`, Fokus-Trapping, Esc, Fokus zurück.

**Schwere:** Hoch · **Aufwand:** Klein (~30 Min)

---

### UX-012 — Lageplan-Editor nicht mobil nutzbar

**Betroffener Bereich:** `LageplanStage.vue` (Stage 1100×720), `LageplanEditor.vue`

**Aktuelles Verhalten:** Feste Stage-Größe, keine Touch-Gesten, keine Responsive-Logik.

**Empfohlene Verbesserung:** Lese-Modus auf Mobile (empfohlen) oder Touch-Steuerung (aufwendig).

**Schwere:** Mittel · **Aufwand:** Groß (~1–2 Tage)

---

### UX-013 — `console.log('[LP] ...')` in Prod-Code

**Betroffener Bereich:** `LageplanStage.vue` (Zeilen 278, 281, 537, 541)

**Schwere:** Gering · **Aufwand:** Klein (~5 Min)

---

### UX-014 — 404-Seite: andere Farbpalette

**Betroffener Bereich:** `NotFoundView.vue` (`bg-slate-900` statt `bg-slate-950`, `text-sky-400` statt amber)

**Schwere:** Gering · **Aufwand:** Klein (~5 Min)

---

### UX-015 — Kein visuelles „Speichern“-Feedback

**Betroffener Bereich:** `FormCustomer.vue`, `FormCompany.vue` (Submit-Button)

**Schwere:** Gering · **Aufwand:** Klein (~10 Min)

---

### UX-016 — Installer-Layout: Doppel-Session-Check

**Betroffener Bereich:** `InstallerLayout.vue` (`beforeEach` + `beforeEnter`)

**Schwere:** Gering · **Aufwand:** Klein (~15 Min)

---

## 5. Empfohlene Verbesserungen (gruppiert)

### 5.1 System-Feedback & Dialoge (P0/P1)

**Ist:** Nur `toast.error`, `alert()`/`confirm()` in 6 Stellen, kein Erfolgs-Feedback.
**Ziel:** Einheitliches Feedback: `toast.success` nach jeder Aktion, `ConfirmDialog` für destruktive Aktionen, Lade-/Fehler-States.
**UX-Begründung:** Nielsen #1, #9; WCAG 4.1.2.
**Technischer Umfang:** Neue `components/ConfirmDialog.vue`, Änderungen in `FirmenView.vue`, `KundenView.vue` (×2), `FormCompany.vue`, `FormCustomer.vue`, `LageplanEditor.vue`.

**Acceptance Criteria:**
- [ ] Nach jedem Speichern: grüner Toast „Kunde gespeichert“ (bzw. Firma/Anlage)
- [ ] Nach jedem Löschen: grüner Toast „Kunde gelöscht“
- [ ] `grep -rn "alert(\|confirm(" frontend/src` = 0 Treffer
- [ ] Bestätigungs-Dialog tastaturbedienbar (Tab, Enter, Esc)
- [ ] Bei API-Fehler in Liste: roter Banner + „Erneut versuchen“
- [ ] Bestehende Geschäftslogik unverändert

### 5.2 Datenverlust-Schutz (P0)

**Ist:** `beforeunload` nur für Browser-Verlassen.
**Ziel:** Bei internem Verlassen eines dirty Formulars: Bestätigungs-Dialog.
**UX-Begründung:** Fehlervermeidung.
**Technischer Umfang:** `onBeforeRouteLeave` in `FormCustomer.vue` + `FormCompany.vue`; `ConfirmDialog` aus 5.1.

**Acceptance Criteria:**
- [ ] Formular ändern → „🏢 Firmen“ klicken → Dialog erscheint
- [ ] „Verwerfen“ → Navigation, Daten verloren (erwartet)
- [ ] „Abbrechen“ (Dialog) → Navigation abgebrochen, Formular offen
- [ ] Nicht-dirty → Navigation ohne Dialog
- [ ] `beforeunload` bleibt erhalten

### 5.3 Formular-Konsistenz (P1)

**Ist:** „← Zurück“ + „Abbrechen“ doppelt; Firmen-Editor-Bug; kein Spinner.
**Ziel:** Ein Verlassen-Konzept, Firmen-Editor zeigt editierte Daten, Spinner im Button.

**Acceptance Criteria:**
- [ ] Pro Formular genau ein „Zurück/Abbrechen“-Element
- [ ] „Bearbeiten“ bei Firma → Formular zeigt Firmen-Daten
- [ ] Speichern-Button zeigt Spinner bei `saving === true`

### 5.4 Landing & Auth (P1)

**Ist:** Landing verlinkt auf geschützte Routen; `/lageplan` ohne Schutz.
**Ziel:** Landing mit Rollenwahl; `/lageplan` geschützt oder entfernt.

**Acceptance Criteria:**
- [ ] Landing zeigt „Admin anmelden“ / „Installer anmelden“
- [ ] `/lageplan` ohne Session → Redirect oder 404
- [ ] Lageplan-Dialog aus `FormCustomer.vue` funktioniert weiterhin

### 5.5 Anlage-Editor & Lageplan (P1/P2)

**Ist:** Lageplan-Pflicht erst beim Speichern; ZEREZ ein Dropdown für alle; Dialog ohne ARIA; Editor nicht mobil.
**Ziel:** Frühes Feedback, Typeahead pro Inverter, Dialog mit ARIA, Editor mobil nutzbar.

**Acceptance Criteria:**
- [ ] PV ohne Lageplan: roter Banner + „Jetzt erstellen“
- [ ] ZEREZ-Dropdown gehört zum zuletzt fokussierten Inverter-Feld
- [ ] Lageplan-Dialog: `role="dialog"`, Esc schließt, Fokus in Dialog
- [ ] Mobile (375px): Lese-Modus oder Touch-Steuerung

### 5.6 Barrierefreiheit & Polish (P2)

**Ist:** `console.log` in Prod, 404-Farben inkonsistent.
**Ziel:** Sauberer Code, konsistente 404, ARIA-Rollen.

**Acceptance Criteria:**
- [ ] Kein `console.log('[LP]')` im Produktions-Code
- [ ] 404-Page gleiche Farbpalette
- [ ] Haupt-Tabs: `role="tablist"`, `role="tab"`, `aria-selected`

---

## 6. Priorisierung

| Priorität | Definition |
|---|---|
| P0 — Kritisch | Blockiert Task oder Datenverlust/Sicherheit |
| P1 — Hoch | Reduziert Usability deutlich |
| P2 — Mittel | Sichtbare Friction |
| P3 — Niedrig | Kosmetisch |

### Prioritäts-Matrix

| Task | Priority | Impact | Aufwand | Abhängigkeiten |
|---|---|---|---|---|
| TASK-001 (Dirty-Data-Guard) | P0 | Kritisch | Klein | TASK-002 |
| TASK-002 (ConfirmDialog) | P0 | Hoch | Mittel | — |
| TASK-003 (Toast-Konsistenz) | P0 | Hoch | Klein | — |
| TASK-004 (List-States) | P1 | Hoch | Klein | — |
| TASK-005 (Zurück-Doppelung) | P1 | Mittel | Klein | — |
| TASK-006 (Landing-Routen) | P1 | Mittel | Klein | — |
| TASK-007 (/lageplan-Schutz) | P3 | Gering | Klein | — |
| TASK-008 (Lageplan-Banner) | P1 | Mittel | Klein | — |
| TASK-009 (Firmen-Editor-Bug) | P0 | Hoch | Klein | — |
| TASK-010 (ZEREZ pro Inverter) | P2 | Mittel | Mittel | — |
| TASK-011 (Dialog ARIA) | P1 | Hoch | Klein | — |
| TASK-012 (Lageplan mobil) | P2 | Mittel | Groß | — |
| TASK-013 (console.log) | P3 | Gering | Klein | — |
| TASK-014 (404-Farben) | P3 | Gering | Klein | — |
| TASK-015 (Spinner) | P3 | Gering | Klein | — |
| TASK-016 (Installer-Guard) | P3 | Gering | Klein | — |

---

## 7. Implementierungs-Roadmap

### Phase 1 — Kritische Fixes (P0, ~3 h)

**Ziel:** Datenverlust verhindern, Sicherheitslücke schließen, Feedback-System etablieren, Bug fixen.

**Tasks:**
- TASK-001: Dirty-Data-Guard
- TASK-002: ConfirmDialog (ersetzt alle `alert()`/`confirm()`)
- TASK-003: `toast.success` nach jeder Mutation
- TASK-009: Firmen-Editor-Bug

**Completion Criteria:**
- [ ] Kein Datenverlust bei interner Navigation (Puppeteer-Test)
- [ ] `grep -rn "alert(\|confirm(" frontend/src` = 0 Treffer
- [ ] `grep -rn "toast.success" frontend/src` ≥ 5 Treffer
- [ ] Firma „Bearbeiten“ → Formular zeigt Firmen-Daten

### Phase 2 — Navigation & Workflow (P1, ~2 h)

**Tasks:**
- TASK-004: List-Lade-/Fehler-States
- TASK-005: „Zurück“-Doppelung auflösen
- TASK-006: Landing-Rollenwahl
- TASK-008: Lageplan-Pflicht-Banner
- TASK-011: Lageplan-Dialog ARIA/Fokus

**Completion Criteria:**
- [ ] API-Fehler → roter Banner + „Erneut versuchen“
- [ ] Pro Formular genau ein Verlassen-Element
- [ ] Landing: „Admin anmelden“ / „Installer anmelden“
- [ ] PV ohne Lageplan → roter Banner + „Jetzt erstellen“
- [ ] Lageplan-Dialog: Esc schließt, Fokus in Dialog

### Phase 3 — Konsistenz & Polish (P2/P3, ~2 h + Groß-Aufwand)

**Tasks:**
- TASK-010: ZEREZ pro Inverter
- TASK-012: Lageplan mobil
- TASK-013: `console.log` entfernen
- TASK-014: 404-Farben
- TASK-015: Spinner
- TASK-016: Installer-Guard vereinfachen

**Completion Criteria:**
- [ ] ZEREZ-Dropdown korrekt bei ≥2 Invertern
- [ ] Mobile (375px): Lageplan-Lese-Modus
- [ ] Kein `console.log('[LP]')` im Build
- [ ] 404-Page gleiche Palette
- [ ] Spinner sichtbar bei `saving === true`
- [ ] Kein doppelter Session-Check

---

## 8. Implementierungs-Tasks

### TASK-001 — Dirty-Data-Guard für interne Navigation

**Priorität:** P0 · **Phase:** 1 · **UX:** UX-001
**Komplexität:** Klein · **Betroffen:** `FormCustomer.vue`, `FormCompany.vue`

**Ziel:** Bei internem Verlassen eines dirty Formulars: Bestätigungs-Dialog.

**Nötige Änderungen:**
1. `onBeforeRouteLeave` in `FormCustomer.vue` und `FormCompany.vue`: bei `formDirty && !saving` Navigation blockieren, `ConfirmDialog` triggern
2. Dialog-Text: „Ungespeicherte Änderungen vorhanden. Wenn du das Formular verlässt, gehen sie verloren.“
3. Buttons: „Änderungen verwerfen“ (primary, rot) + „Im Formular bleiben“ (secondary)
4. „Verwerfen“ → Navigation zulassen; „Im Formular bleiben“ → Navigation abbrechen
5. `beforeunload` bleibt erhalten
6. Nach Speichern (`formDirty = false`) → kein Dialog

**Acceptance Criteria:**
- [ ] Kunde öffnen, Feld ändern, „🏢 Firmen“ → Dialog
- [ ] „Im Formular bleiben“ → Formular bleibt offen
- [ ] „Änderungen verwerfen“ → URL wechselt
- [ ] Nicht-dirty → Nav ohne Dialog
- [ ] Installer-Modus und Firmen-Formular ebenfalls betroffen

**Abhängigkeit:** TASK-002
**Validierung:** Puppeteer (dirty → Nav → Dialog → beide Pfade)

---

### TASK-002 — ConfirmDialog-Komponente

**Priorität:** P0 · **Phase:** 1 · **UX:** UX-003, UX-001
**Komplexität:** Mittel · **Neu:** `components/ConfirmDialog.vue`

**Ziel:** Zentrale, brandbare, tastaturbedienbare Dialog-Komponente; ersetzt alle `alert()`/`confirm()`.

**Nötige Änderungen:**
1. Neue `components/ConfirmDialog.vue`:
   - Props: `open`, `title`, `message`, `confirmLabel`, `cancelLabel`, `tone` (default/danger)
   - Emits: `confirm`, `cancel`
   - Teleport nach `body`, `role="dialog"`, `aria-modal="true"`
   - Fokus in Dialog, Tab zirkuliert, Esc = cancel
   - Overlay-Klick = cancel
   - Styling: `bg-slate-900 border-slate-700 rounded-xl p-5`
2. Migration aller 6 Stellen:
   - `FirmenView.vue:85` `alert(...)` → `toast.error(...)`
   - `KundenView.vue:210` `confirm(...)` → `ConfirmDialog` (danger)
   - `installer/KundenView.vue:151` `confirm(...)` → `ConfirmDialog` (danger)
   - `installer/KundenView.vue:156` `alert(...)` → `toast.error(...)`
   - `FormCompany.vue:105` `alert(...)` → `toast.error(...)`
   - `FormCustomer.vue:584` `alert(...)` → `toast.error(...)`
   - `LageplanEditor.vue:398` `alert(...)` → `toast.error(...)`
3. `grep -rn "alert(\|confirm(" frontend/src` = 0 Treffer

**Acceptance Criteria:**
- [ ] grep = 0 Treffer
- [ ] Kunden-Löschen: Dialog mit „Löschen“ (rot) + „Abbrechen“
- [ ] Esc schließt Dialog
- [ ] Tab zirkuliert innerhalb
- [ ] Overlay-Klick schließt
- [ ] Fehlermeldungen als `toast.error`, nicht `alert()`
- [ ] Mobile (375px) vollständig sichtbar

**Validierung:** grep + Puppeteer (Dialog, beide Pfade, Esc, Tab)

---

### TASK-003 — Erfolgs-Feedback (Toast)

**Priorität:** P0 · **Phase:** 1 · **UX:** UX-002
**Komplexität:** Klein · **Betroffen:** alle Views mit Mutationen

**Nötige Änderungen:**
1. `KundenView.vue` (Admin): `toast.success('Kunde gespeichert')` nach POST/PUT, `toast.success('Kunde gelöscht')` nach DELETE
2. `FirmenView.vue`: analog „Firma gespeichert“/„Firma gelöscht“
3. `installer/KundenView.vue`: analog
4. `FormCustomer.vue`: Upload-Erfolg → `toast.success('Foto hochgeladen')`
5. `LageplanEditor.vue`: PDF-Erfolg → `toast.success('PDF exportiert')`
6. Toast-Text: kurz, aktiv, ohne Punkt

**Acceptance Criteria:**
- [ ] `grep -rn "toast.success" frontend/src` ≥ 7 Treffer
- [ ] Jede erfolgreiche Mutation → grüner Toast
- [ ] Fehler bleibt `toast.error` (rot)

**Validierung:** grep + manueller Test

---

### TASK-004 — Lade- und Fehler-States in Listen

**Priorität:** P1 · **Phase:** 2 · **UX:** UX-004
**Komplexität:** Klein · **Betroffen:** `KundenView.vue` (×2), `FirmenView.vue`

**Nötige Änderungen:**
1. `error`-Ref in `load()`, im `catch` setzen
2. `v-if="error"` → roter Banner `bg-red-900/40 border-red-800 text-red-300` + „Erneut versuchen“-Button
3. Bei erfolgreichem Reload: `error = null`

**Acceptance Criteria:**
- [ ] API-Fehler → roter Banner + Retry
- [ ] „Erneut versuchen“ → neu laden
- [ ] Leere Liste → „Keine Kunden gefunden.“ (bestehend)
- [ ] Alle 3 Views identisch

**Validierung:** Backend stoppen, Banner + Retry testen

---

### TASK-005 — „Zurück“-Doppelung auflösen

**Priorität:** P1 · **Phase:** 2 · **UX:** UX-005
**Komplexität:** Klein · **Betroffen:** `FormCustomer.vue`, `FormCompany.vue`

**Nötige Änderungen:**
1. Kopfzeile: „← Zurück“ → „✕ Formular schließen“ (12px, grau, rechts neben Dirty-Indikator)
2. Fußzeile: „Abbrechen“ bleibt (sekundär, links neben Submit)
3. Beide triggern `emit('cancel')`
4. Konsistent in allen 3 Views

**Acceptance Criteria:**
- [ ] Kein „← Zurück“ mehr in Kopfzeile
- [ ] „✕ Formular schließen“ sichtbar
- [ ] „Abbrechen“ in Fußzeile sichtbar
- [ ] Konsistent in Admin-Kunde, Admin-Firma, Installer-Kunde

**Validierung:** Screenshot + manueller Test

---

### TASK-006 — Landing-Rollenwahl

**Priorität:** P1 · **Phase:** 2 · **UX:** UX-006
**Komplexität:** Klein · **Betroffen:** `LandingView.vue`

**Nötige Änderungen:**
1. Buttons: „Admin anmelden“ → `/admin/login`, „Installer anmelden“ → `/installer/login`
2. Optional: `next`-Parameter für Weiterleitung nach Login
3. Landing-Text anpassen (Rollen-Bezeichnung)

**Acceptance Criteria:**
- [ ] Landing zeigt „Admin anmelden“ + „Installer anmelden“
- [ ] Keine direkten Links auf `/admin/*` ohne Session
- [ ] Optional: `next`-Parameter funktioniert

**Validierung:** Browser-Test

---

### TASK-007 — `/lageplan` Session-Schutz

**Priorität:** P3 · **Phase:** 3 · **UX:** UX-007
**Komplexität:** Klein · **Betroffen:** `router/index.js`, `LageplanView.vue`

**Hintergrund:** Vorab aus Sicherheitsbewertung entnommen (Kolya 31.10.2026). Aufgabe bleibt offen, falls die Route später entfernt oder geschützt wird.

**Nötige Änderungen (optional):**
1. **Option A (empfohlen):** Route `/lageplan` aus `router/index.js` entfernen (Editor wird immer aus `FormCustomer.vue` als Dialog geöffnet)
2. **Option B:** `beforeEnter`-Guard + „Bitte anmelden“-Hinweis
3. Entscheidung dokumentieren

**Acceptance Criteria:**
- [ ] Ohne Session: `/lageplan` rendert nicht
- [ ] Lageplan-Dialog aus `FormCustomer.vue` funktioniert weiterhin

**Validierung:** Browser-Test ohne/mit Session

---

### TASK-008 — Lageplan-Pflicht-Banner

**Priorität:** P1 · **Phase:** 2 · **UX:** UX-008
**Komplexität:** Klein · **Betroffen:** `FormCustomer.vue` (PlantForm-Render)

**Nötige Änderungen:**
1. Im PlantForm: wenn `anlagetyp === 'pv' && !lageplan` → roter Banner „⚠️ Lageplan fehlt (Pflichtfeld für PV-Anlagen)“ + „Jetzt erstellen“-Button
2. Button triggert `emit('open-lageplan', p.index)`
3. Banner verschwindet nach Lageplan-Speichern
4. Nicht-PV: kein Banner

**Acceptance Criteria:**
- [ ] PV ohne Lageplan → roter Banner + Button
- [ ] „Jetzt erstellen“ öffnet Dialog
- [ ] Nach Speichern: Banner weg
- [ ] Wallbox/WP: kein Banner

**Validierung:** Browser-Test

---

### TASK-009 — Firmen-Editor-Bug

**Priorität:** P0 · **Phase:** 1 · **UX:** UX-009
**Komplexität:** Klein · **Betroffen:** `FirmenView.vue`, `FormCompany.vue`

**Nötige Änderungen:**
1. `FirmenView.vue`: `editing`-Ref einführen
2. `editCompany(c)`: `editing.value = c; showForm.value = true`
3. `FormCompany`: `:initial="editing || null"`
4. `onSaved()`: `editing.value = null; showForm.value = false; load()`
5. `FormCompany.vue`: bei `initial` prop Felder setzen (analog `FormCustomer.vue`)

**Acceptance Criteria:**
- [ ] „Bearbeiten“ → Formular zeigt Firmen-Daten
- [ ] „Neue Firma“ → leeres Formular
- [ ] Speichern → Liste aktualisiert

**Validierung:** Browser-Test

---

### TASK-010 — ZEREZ-Typeahead pro Inverter

**Priorität:** P2 · **Phase:** 3 · **UX:** UX-010
**Komplexität:** Mittel · **Betroffen:** `FormCustomer.vue` (PlantForm)

**Nötige Änderungen:**
1. `zerezState` als `reactive({})` pro Index
2. `onZerezInput(i, e)` schreibt in `zerezState[i]`
3. `selectZerez(i, result)` liest aus `zerezState[i]`
4. Render: Dropdown unter dem jeweiligen Inverter-Feld

**Acceptance Criteria:**
- [ ] ≥2 Inverter: Dropdown gehört zum zuletzt fokussierten Feld
- [ ] Inverter #1 auswählen → #1 gefüllt, #2 unverändert

**Validierung:** Browser-Test (2 Inverter, jeweils 4+ Zeichen)

---

### TASK-011 — Lageplan-Dialog ARIA/Fokus

**Priorität:** P1 · **Phase:** 2 · **UX:** UX-011
**Komplexität:** Klein · **Betroffen:** `FormCustomer.vue` (Lageplan-Dialog)

**Nötige Änderungen:**
1. Dialog-Div: `role="dialog" aria-modal="true" aria-labelledby="lageplan-title"`
2. `<h2>` bekommt `id="lageplan-title"`
3. Fokus auf „✅ Lageplan speichern“ bei Öffnung
4. `Esc` → `closeLageplan()`
5. Fokus zurück zum auslösenden Button beim Schließen
6. Tab zirkuliert innerhalb

**Acceptance Criteria:**
- [ ] `role="dialog"` + `aria-modal` im DOM
- [ ] Esc schließt
- [ ] Fokus in Dialog bei Öffnung
- [ ] Tab zirkuliert
- [ ] Nach Schließen: Fokus auf auslösendem Button

**Validierung:** Browser-Test (Tab, Esc, Fokus)

---

### TASK-012 — Lageplan-Editor mobil

**Priorität:** P2 · **Phase:** 3 · **UX:** UX-012
**Komplexität:** Groß · **Betroffen:** `LageplanStage.vue`, `LageplanEditor.vue`

**Option A (empfohlen — Lese-Modus):**
1. Bei Viewport < 768px: Stage in `overflow-x-auto`, Toolbar horizontal scrollbar, keine Zeichen-Tools
2. PDF-Export bleibt
3. „Bearbeiten“ → „Lageplan ansehen“ auf Mobile
4. Hinweis: „Lageplan bearbeiten am Desktop.“

**Acceptance Criteria:**
- [ ] Mobile (375px): Stage sichtbar, keine Überlappung
- [ ] PDF-Download auf Mobile funktioniert
- [ ] Keine Zeichen-Tools auf Mobile

**Validierung:** Browser-Test 375px

---

### TASK-013 — `console.log` entfernen

**Priorität:** P3 · **Phase:** 3 · **UX:** UX-013
**Betroffen:** `LageplanStage.vue` (Zeilen 278, 281, 537, 541)

**Acceptance Criteria:**
- [ ] `grep -rn "console.log" frontend/src/components/lageplan/` = 0 Treffer

---

### TASK-014 — 404-Farben

**Priorität:** P3 · **Phase:** 3 · **UX:** UX-014
**Betroffen:** `NotFoundView.vue`

**Nötige Änderungen:** `bg-slate-900` → `bg-slate-950`, `text-sky-400` → `text-amber-400`

---

### TASK-015 — Spinner im Speichern-Button

**Priorität:** P3 · **Phase:** 3 · **UX:** UX-015
**Betroffen:** `FormCustomer.vue`, `FormCompany.vue`

**Nötige Änderungen:** Bei `saving === true` → Spinner (SVG `animate-spin`) + „Speichert…“

---

### TASK-016 — Installer-Guard vereinfachen

**Priorität:** P3 · **Phase:** 3 · **UX:** UX-016
**Betroffen:** `InstallerLayout.vue`

**Nötige Änderungen:** `beforeEach` entfernen, `onBeforeMount` → `onMounted` (wie `AdminLayout.vue`)

---

## 9. Validierung & Acceptance Criteria

### Funktionale Validierung
- Alle bestehenden Workflows bleiben funktionsfähig
- Geschäftslogik unverändert
- Alle 16 Tasks: individuelle Acceptance Criteria erfüllt

### Usability-Validierung
- Kein Datenverlust-Szenario mehr
- Erfolgs-Feedback nach jeder Aktion
- Lageplan-Pflicht früh sichtbar
- Landing-Klartext
- `/lageplan` nicht ohne Session

### Barrierefreiheits-Validierung
- Tastaturnavigation in allen Dialogen
- Fokus-Management im Lageplan-Dialog
- `role="dialog"`, `aria-modal` in Dialogen

### Responsive-Validation
- Mobile (375px): Listen, Formular, Lageplan-Lese-Modus sichtbar
- Keine horizontalen Überlässe in Listen
- Dialoge passen auf mobile Viewport

### Messbare UX-Indikatoren (Vorschlag, keine Baseline gemessen)

| Indikator | Ziel (geschätzt) |
|---|---|
| Datenverlust bei interner Navigation | 0 |
| Fehlermeldungen als `alert()` | 0 |
| Erfolgs-Toast nach Mutation | 100 % der Aktionen |
| Lageplan-Pflicht-Feedback | Vor dem Speichern (Banner) |
| Mobile Lageplan-Erreichbarkeit | Lese-Modus (375px) |

---

## 10. Risiken & Abhängigkeiten

### Risiken
1. **Dirty-Data-Guard:** Guard könnte zu aggressiv sein → `formDirty` muss zuverlässig sein (deep `watch` vorhanden)
2. **ConfirmDialog:** Fokus-Trapping kann mit Konva-Stage interferieren → Dialog muss korrekt implementiert werden
3. **Firmen-Editor-Bug:** `FormCompany`-Props müssen korrekt initialisiert werden (analog `FormCustomer.vue`)
4. **ZEREZ pro Inverter:** State-Refactor könnte bestehende Logik brechen → muss getestet werden
5. **Lageplan mobil:** Großes Aufwands-Risiko; Lese-Modus (Option A) ist sicherer
6. **`/lageplan`-Schutz:** Falls nur Testzweck → Entfernen (Option A) sicherer

### Abhängigkeiten
| Task | Abhängigkeiten |
|---|---|
| TASK-001 | TASK-002 |
| Alle anderen | — |

**Sequenzempfehlung:** Phase 1 (TASK-002 zuerst, dann TASK-001, dann 003/007/009 parallel) → Phase 2 → Phase 3

---

## 11. Review-Einschränkungen

1. **Kein Screenreader-Test:** ARIA nur statisch geprüft, nicht mit NVDA/VoiceOver validiert
2. **Lageplan-Editor mobil nicht getestet:** Screenshots zeigen mobile Admin-Home/Kunden, nicht den Editor auf Mobile
3. **ZEREZ-Multi-Inverter nicht live getestet:** Code-Analyse zeigt das Problem, Live-Test mit 2+ Invertern nicht durchgeführt
4. **PDF-Export nicht getestet:** `/api/lageplan/pdf` nicht im Browser getriggert (90 s Timeout-Risiko)
5. **Kein User-Research:** Alle Befunde basieren auf Code-Lesung, Browser-Screenshots und UX-Prinzipien
6. **Kein Performance-Test:** Ladezeiten, Bundle-Size, Konva-Rendering nicht bewertet
7. **Kein Mobile-Touch-Test:** Touch-Gesten nicht getestet

---

## 12. Abschluss-Empfehlung

Die Anwendung ist **funktional solide** — die UI/UX-Phase der vorigen Woche hat die visuelle Konsistenz deutlich verbessert. Die verbleibenden Probleme sind **fokussiert und gut priorisierbar**.

**Sofort (Phase 1, ~3 h):**
1. TASK-002 (ConfirmDialog) — Fundament
2. TASK-001 (Dirty-Data-Guard) — Datenverlust eliminiert
3. TASK-003 (Toast-Konsistenz) — Erfolgs-Feedback
4. TASK-007 (`/lageplan`-Schutz) — Sicherheitslücke
5. TASK-009 (Firmen-Editor-Bug) — Bug fixen

**Kurzfristig (Phase 2, ~2 h):** TASK-004, 005, 006, 008, 011

**Mittelfristig (Phase 3):** TASK-010, 012 (Groß), 013, 014, 015, 016

**Gesamtaufwand:** ~7 h (ohne TASK-012) bzw. ~9 h (mit)

**Höchste Hebelwirkung:** Phase 1 — 5 Tasks, ~3 h.

**Nächster Schritt:** Phase 1 implementieren (TASK-002 zuerst), mit Puppeteer-Verifikation nach jeder Task.

---

*Erstellt am 31.10.2026 · 22 Screenshots in `media/browser/ux-review3/`*
