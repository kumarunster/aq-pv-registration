# ARBEITSSTAND - Amelanq Netz-Anmeldung

**Stand: 28.10.2026, 12:15 · v0.3.0 · Branch `feature/lageplan-editor`**

---

## 1. Lageplan-Editor — heute fertiggestellt (28.10.2026)

### ✅ Hauptintegration (Commit `686983a`, 28.10. ~19:45)
- **Editor im Anlagen-Formular:** `FormCustomer.vue` hat pro Anlage einen
  📐-Abschnitt (Status ✓/leer, Button Erstellen/Bearbeiten → Fullscreen-Dialog).
  Titel + Adresse aus Kundendaten vorbefüllt; `getLayout()` übernimmt die
  Konva-Node-Positionen beim Schließen. **PV ohne Lageplan = Speichern abgebrochen** (Pflichtfeld).
- **Mongo-Persistenz:** `PlantCreate`/`PlantUpdate` +`lageplan: Optional[LageplanDocument]`
  +`documents: list[DocumentRef]`; inline in `customers.plants` (list[dict]) →
  keine Migration nötig.
- **PDF-Header:** `_wrap_html` zeigt jetzt Titel, **Adresse** (metadata.adresse)
  und „Gemarkung: X — Flur: Y — Flurstück: Z" (pdftotext verifiziert).
- **Editor-Panel:** Projektdaten (Titel/Adresse/Gemarkung/Flur/Flurstück) in
  `metadata`; `initialLayout`-Prop lädt gespeicherten Plan; `defineExpose({getLayout})`.

### ✅ PDF-Export verifiziert (vorher)
- **Commit `cd03538`** — `syncFromCanvas`: lokale Positionen + Rotation aus Konva-Node.
  (Group-Transformation statt globaler Matrix; `offset.x += node.x`).
- **Commit `20cd247`** — `syncFromCanvas`: nur Group-Position, keine Addition
  innerer Shapes (verhinderte Doppelverschiebung).
- **Commit `e4f086a`** — `syncFromCanvas`: Punkte als `[x,y]`-Arrays statt
  `{x,y}`-Objekte (Backend erwartet `list[tuple[float, float]]`; vorher
  Pydantic 422 `tuple_type`).
- **Commit `43897f1`** — `_hatch_lines`: Schraffur-Linien über Polygonkanten
  statt Bounding-Box.
  - Vorher: `d`-Iteration über BBox (`min_x−max_y` … `max_x−min_y`) + AABB-Heuristik
    → bei schiefen Polygonen nur 13 Linien in der unteren linken Ecke statt ~70.
  - Jetzt: `d` über `min/max(y−x)` der Ecken, parametrischer Kanten-Schnitt
    (t ∈ [0,1]), Entdopplung an Ecken, paarweise Verbindung (auch konkave
    Polygone). Punkte px, `hatch_spacing` mm → px (×3), Ausgabe mm.
  - **Verifiziert gegen Kolyas Polygon** (520,136)–(926,146)–(882,558)–(476,548) px:
    70 Linien, Abdeckung x 159.1–308.4 mm / y 45.4–186.1 mm = Polygon komplett gefüllt.
- **Kolya-Abnahme 28.10.:** „jetzt hat es endlich funktioniert mit dem
  schraffierten Rechteck" — rect, hatching, arrow, N-Pfeil, Hintergrund
  alle an der richtigen Stelle im PDF.

### Alle Commits auf `origin/feature/lageplan-editor` und `main`
```
686983a feat(lageplan): Hauptintegration — Editor in Anlagen-Formular + Mongo-Persistenz
2665bb9 docs: ARBEITSSTAND 28.10.2026 (Lageplan-PDF fertig, nächste Schritte)
43897f1 fix(lageplan): Schraffur-Linien über Polygonkanten statt Bounding-Box
e4f086a fix(lageplan): syncFromCanvas - Punkte als [x,y]-Arrays statt {x,y}-Objekte
20cd247 fix(lageplan): syncFromCanvas - nur Group-Position, keine Addition innerer Shapes
cd03538 fix(lageplan): syncFromCanvas - lokale Positionen + Rotation aus Node
```

### Einheiten (wichtig für alle künftigen Lageplan-Arbeit)
- Zeichenfläche: 891×630 px = 297×210 mm (A4 quer), **1 SVG-Einheit = 1 mm**
- Canvas-Punkte aus Konva: **px**
- `hatch_spacing`: **mm** (Default 4)
- Backend `svg_renderer.py`: nimmt px-Punkte, gibt mm-SVG aus (`_mm = v/3`)
- Frontend `LageplanElement.vue`: Canvas rendert in px mit `MM_PX = 3`

## 2. Infrastruktur-Zustand (28.10.2026)

- Dev-Stack Port 8092 (na-*): nginx, oathkeeper, kratos, kratos-pgdb,
  backend, frontend, mongodb, redis, weasyprint alle up.
- **na-backend:** healthy, Code via Bind-Mount (`backend/src` → `/app/src`),
  Uvicorn `--reload` — Datei-Änderung = sofort aktiv, kein Rebuild nötig.
- **na-frontend:** Bild wird bei `docker compose build` gebacken —
  nach Frontend-Änderungen: `npm run build` (optional) + `docker compose build
  --no-cache na-frontend` + `docker compose up -d na-frontend`.
  BUILD_TIME im ausgelieferten Bundle prüfen (war der Stolperstein am 28.10.:
  Frontend-Bild vom 27.10. lief weiter, während Backend-Änderungen live waren).
- **na-weasyprint:** eigenständiger Service, intern (kein Host-Port),
  `POST /render` mit `{html}` → A4-PDF.

## 3. Offene Punkte (nicht heute angefasst)

1. **Installer-API 401** (Oathkeeper-Mutator setzt
   `X-Kratos-Identity-ID` nicht ans Backend) — siehe Stand 21.10.,
   Oathkeeper-Logauswertung noch nie gefahren.
2. **Phase 4b Netzbetreiber-Suche**: Datenquelle mit Kolya klären
   (Bundesnetzregister / Netzentstehungsregister / PLZ-Map), dann Service.
3. **Lageplan: Speichern/Integration** in Anlagen-Formular (Phase 8 der
   Lageplan-Roadmap im `router.py`-Header) — noch nicht gestartet.
4. **Lageplan-Eckfall bei 45°-Kanten:** Kante parallel zu Schraffurlinie
   wird übersprungen (denom ≈ 0) — bei exakt 45°-Kanten fehlt eine Randlinie.
   Falls Kolya es bemerkt: parallel-Spezialfall ergänzen.

## 4. Arbeitsregeln (bewährt am 28.10.)

- **Nichts ungefragt anlegen** — erst fragen, dann Code.
- **Vor „fertig" die Ausgabe prüfen**: SVG-/PDF-Ausgabe konkret testen
  (Linien-Anzahl, mm-Abdeckung gegen Polygon-BBox), nicht behaupten.
- **Frontend-Änderungen**: immer `docker compose build` + Neu-Start,
  BUILD_TIME im ausgelieferten Bundle verifizieren — Host-Build allein reicht nicht.
- **Backend-Änderungen**: Bind-Mount + `--reload`, `docker restart` genügt;
  Container-Quellcode == Host-Quellcode verifizieren.
- Bilder: `view_image` mit `path` testen, bevor „keine Bilderkennung".
- **Kein Raten** — URL/Feature/ID erst im Code/Stack verifizieren.
- **Production tabu** (timesheets.amelanq.com); hier nur Dev (8092).

## 5. Nächste Schritte (Reihenfolge, erst nach Kolya-Freigabe)

1. **Lageplan-Integration in Anlagen-Formular** (erst als Plan notiert, noch
   nicht gebaut): `FormCustomer.vue`/`PlantForm` bekommt pro Anlage einen
   📐-Abschnitt (Status ✓/leer + „Erstellen“/„Bearbeiten“-Button) und öffnet
   den `LageplanEditor` in einem Fullscreen-Dialog (initialLayout aus der
   Anlage, Titel/Adresse vorbefüllt, `getLayout()` beim Schließen →
   `plant.lageplan`). PV ohne Lageplan = Speichern abgebrochen (Pflichtfeld,
   Logik steht schon im save() — UI fehlt).
2. **Anlage: Adress- + Grundstückdaten übernehmen:** Im PlantForm ein
   Abschnitt „📍 Anlage-Adresse“ (Straße + Nr, PLZ, Ort, Telefon, E-Mail, IBAN
   — separate Felder `plant.address_*`, nicht die Kundendaten) und „🏡
   Grundstück“ (separate Felder `plant.gemarkung`/`flur`/`flurstueck`).
   Backend: PlantCreate/PlantUpdate um die Felder erweitern; Gemarkung/Flur/
   Flurstück zusätzlich in `lageplan.metadata` spiegeln (PDF-Header nutzt sie).
3. **Kolya-Test der Integration:** Kunde anlegen → PV-Anlage → Adresse/
   Grundstück ausfüllen → Lageplan erstellen → speichern → in Mongo prüfen
   (`customers.plants[*].lageplan`, `address_*`, `gemarkung`) + PDF aus dem
   Formular exportieren.
4. **Dokumente an Anlage hängen:** PDF-Export aus dem Formular direkt als
   `DocumentRef` speichern (Upload-Service + `documents`-Feld nutzen;
   Aktuell wird nur das JSON gespeichert, das PDF wird on-the-fly erzeugt).
5. **Installer-API 401:** Oathkeeper-Logs bei EINEM Installer-Request auswerten.
