# ARBEITSSTAND - Amelanq Netz-Anmeldung

**Stand: 31.10.2026, 02:25 · v0.3.0 · Branch `main`**

---

## 1. UI/UX-Phase 30.10.2026 — alle 6 Sprints komplett

Alle Sprints aus dem Review (`docs/ux-review-2026-10-30.md`) sind umgesetzt, deployet
und via Playwright-Browser verifiziert (JS: NONE in jedem View).

| Sprint | Commits | Inhalt |
|---|---|---|
| Phase 0a/0b/0c/0d | `fc00ddb` | Pagination (10/Seite + Zeilen-Selector), Suche (tokenisiert), Status-Filter, Anlagen-Tabs, Toasts (global ToastHost) |
| Admin-Guard | `b229c37` | Admin-Login-Guard + 500ms-Delay bereinigt |
| P2 Karten/Editor | `089e462` | Kunden-Karte mit Zusammenfassung (Stat-Zeile), Anlagen-Editor ersetzt statische Liste |
| UI/UX-Review | `a77c6ea` | 12 Verbesserungsvorschläge + 2-Sprint-Roadmap (docs) |
| Feld-Höhen/Buttons | `8c09842`, `e4e0600` | InputField H=38px, Text 14px; ButtonField H=38px; Zurück+Close in Kopfzeile; „Kunde anlegen" statt „Anlegen" |
| Installer-Kunde | `5f539b1`, `6683454` | „Neue Anmeldung" (Titel+Submit); Zurück+Close; 14px/38px |
| FormCompany | `f9d48c4` | „← Zurück" + Titel in Kopfzeile; Footer: Abbrechen (grau) links + „Firma anlegen" (gelb) rechts |

**Konsistenz-Stand (alle 3 Views identisch):**
- InputField / ButtonField: `h-9` (38px), Text 14px
- Kopfzeile: `← Zurück` (12px grau) links, Titel (18px), `✕ Formular schließen` rechts
- Fußzeile: `Abbrechen` (14px grau) links, gelber Submit (14px bold, 38px) rechts
- Submit-Labels: „Kunde anlegen", „Firma anlegen", „Anmeldung abschließen"

## 2. Layout-Fixes 31.10.2026

- **InstallerLayout.vue:** Header jetzt wie AdminLayout (h-12, border-b, Titel links, Logo rechts 32px) — war vorher h-16, Logo 54px links.
- **Installer-Kunden-Table:** gleiche Breite wie Admin (max-w-6xl)
- **Installer-Kunden-Liste:** 32px-Padding entfernt (px-8 → px-0), Tabelle läuft bis an die Kanten
- **KundenView (beide):** „Zurück zur Übersicht" (22px padding) über der Tabelle statt links im Header
- **Zurück in Kunden-Detail:** `→ Alle Kunden` (12px, grau) statt „← Zurück" — gleiche Struktur wie Firmen
- **Kunden-Detail-Footer:** `Zurück` (grau, 12px) links + gelber `Kunde speichern` rechts — wie in allen anderen Forms
- **Kunden-Detail-Formular:** `grid-cols-2` mit Gap (vorher: einspaltig, Felder überlappend)
- **Anlage-Formular:** `grid-cols-2` mit Gap; „Erste Inbetriebnahme" (nicht „Inbetriebnahme"); „PV-Art" (nicht „PV-Art (Modul)" für String-Module)
- **Anlage-Details (read-only):** `grid-cols-2` mit Gap
- **Anlage-Buttons:** „Lageplan erstellen" links + „PDF exportieren" rechts — gleiche Zeile wie „Lageplan erstellen"/„Speichern" im Edit-Modus

## 3. Offene Punkte

1. **InstallerLayout.vue beforeEach-Pattern:** Stand 30.10. — noch NICHT geprüft/gemacht (alter Route-Guard-Mechanismus).
2. **Installer-API 401** (Oathkeeper-Mutator setzt `X-Kratos-Identity-ID` nicht ans Backend) — Oathkeeper-Logauswertung nie gefahren.
3. **Phase 4b Netzbetreiber-Suche:** Datenquelle mit Kolya klären (Bundesnetzregister / Netzentstehungsregister / PLZ-Map).
4. **Lageplan-Eckfall bei 45°-Kanten:** Kante parallel zu Schraffurlinie wird übersprungen — bei exakt 45° fehlt eine Randlinie.
5. **Dokumente an Anlage hängen:** PDF-Export als `DocumentRef` speichern (Upload-Service + `documents`-feld).
6. **Kolya-Test der Lageplan-Integration:** Kunde anlegen → PV-Anlage → Adresse/Grundstück ausfüllen → Lageplan erstellen → speichern → Mongo prüfen + PDF exportieren.

## 4. Infrastruktur-Zustand

- Dev-Stack Port 8092 (na-*): nginx, oathkeeper, kratos, kratos-pgdb, backend, frontend, mongodb, redis, weasyprint — alle up.
- **na-backend:** Bind-Mount (`backend/src` → `/app/src`), Uvicorn `--reload` — Datei-Änderung = sofort aktiv.
- **na-frontend:** `docker compose build` + `up -d` nach jeder Änderung. BUILD_TIME im Bundle verifizieren.
- **na-weasyprint:** intern (kein Host-Port), `POST /render` mit `{html}` → A4-PDF.

## 5. Einheiten (Lageplan)

- Zeichenfläche: 891×630 px = 297×210 mm (A4 quer), **1 SVG-Einheit = 1 mm**
- Canvas-Punkte aus Konva: **px**
- `hatch_spacing`: **mm** (Default 4)
- Backend `svg_renderer.py`: nimmt px-Punkte, gibt mm-SVG aus (`_mm = v/3`)
- Frontend `LageplanElement.vue`: Canvas rendert in px mit `MM_PX = 3`

## 6. Arbeitsregeln

- **Nichts ungefragt anlegen** — erst fragen, dann Code.
- **Vor „fertig" die Ausgabe prüfen** — konkret testen, nicht behaupten.
- **Frontend-Änderungen:** immer `docker compose build` + Neu-Start, BUILD_TIME verifizieren.
- **Backend-Änderungen:** Bind-Mount + `--reload`, Container-Quellcode == Host-Quellcode verifizieren.
- **Kein Raten** — URL/Feature/ID erst im Code/Stack verifizieren.
- **Production tabu** (timesheets.amelanq.com); hier nur Dev (8092).

## 7. Nächste Schritte (nach Kolya-Freigabe)

1. **Kolya-Test der Lageplan-Integration** (s. obigen Punkt 6)
2. **Dokumente an Anlage hängen** (s. obigen Punkt 5)
3. **Installer-API 401** fixen (s. obigen Punkt 2)
4. **InstallerLayout beforeEach-Pattern** prüfen und ggf. aufräumen
5. **Lageplan 45°-Eckfall** — nur falls Kolya es bemerkt
