# Roadmap: PV-Lageplan-Editor

## 1. Projektziel

Entwicklung eines webbasierten Lageplan-Editors für die Erstellung von Lageplänen zur Anmeldung und Registrierung von Photovoltaikanlagen bei Netzbetreibern.

Der Benutzer lädt einen Screenshot einer Liegenschaftskarte hoch, zeichnet darauf PV-Anlagenkomponenten und Beschriftungen ein und exportiert den fertigen Lageplan als A4-PDF.

**Grundprinzip:**
- Zeichnen und Bearbeiten im Browser
- Speicherung der Zeichnungsdaten als JSON
- PDF-Rendering ausschließlich im Python-Backend
- SVG-basierte Vektorannotation
- Keine serverseitigen Screenshots des Frontends
- Kein Canvas-Bild als Grundlage des PDF-Exports

## 2. Technologie-Stack

### Frontend
- Vue 3 mit Composition API
- TypeScript
- Vite
- Konva.js mit vue-konva
- Pinia für State Management
- PrimeVue für UI-Komponenten
- Axios für Backend-Kommunikation

### Backend
- Python 3.12+
- FastAPI
- Pydantic v2
- Jinja2
- WeasyPrint
- Pillow für Bildvalidierung und -verarbeitung

### Tests
- Vitest für Frontend-Unit-Tests
- Playwright für End-to-End-Tests
- Pytest für Backend-Tests
- PDF-Validierung mit pypdf

### Architekturvorgaben
- Frontend und Backend getrennt entwickeln
- Gemeinsames versioniertes JSON-Datenmodell
- Keine Datenbank für den MVP
- Keine Benutzerverwaltung für den MVP
- Keine externen Cloud-Dienste erforderlich
- Sämtliche Rendering-Funktionen müssen lokal ausführbar sein

---

## 3. Zielstruktur des Projekts

```text
pv-lageplan/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   └── editor/
│   │   │       ├── LageplanEditor.vue
│   │   │       ├── EditorToolbar.vue
│   │   │       ├── EditorCanvas.vue
│   │   │       ├── PropertiesPanel.vue
│   │   │       ├── ProjectInfo.vue
│   │   │       └── layers/
│   │   │           ├── BackgroundLayer.vue
│   │   │           ├── ShapesLayer.vue
│   │   │           └── SelectionLayer.vue
│   │   ├── composables/
│   │   │   ├── useDrawing.ts
│   │   │   ├── useSelection.ts
│   │   │   ├── useHistory.ts
│   │   │   └── useZoom.ts
│   │   ├── stores/
│   │   │   └── lageplan.ts
│   │   ├── services/
│   │   │   ├── imageImport.ts
│   │   │   └── pdfExport.ts
│   │   └── types/
│   │       └── lageplan.ts
│   └── package.json
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── models/
│   │   │   └── lageplan.py
│   │   ├── routers/
│   │   │   └── lageplan.py
│   │   ├── services/
│   │   │   ├── image_service.py
│   │   │   ├── svg_renderer.py
│   │   │   └── pdf_renderer.py
│   │   └── templates/
│   │       └── lageplan.html
│   ├── tests/
│   └── pyproject.toml
├── examples/
├── README.md
└── docker-compose.yml
```

---

# Phase 1 – Projektgrundlage

## Ziel

Ein lauffähiges Vue-Frontend und FastAPI-Backend mit funktionierender Kommunikation.

### Aufgaben

- [ ] Vue-3-Projekt mit Vite und TypeScript initialisieren.
- [ ] vue-konva, Konva, Pinia, PrimeVue und Axios installieren.
- [ ] FastAPI-Projekt mit Python-Paketverwaltung aufsetzen.
- [ ] Pydantic, Jinja2, WeasyPrint und Pillow installieren.
- [ ] CORS für lokale Entwicklung konfigurieren.
- [ ] API-Health-Endpunkt `GET /api/health` implementieren.
- [ ] Entwicklungsbefehle dokumentieren.
- [ ] Optional Docker Compose für beide Services bereitstellen.

### Abnahmekriterien

- Vue-Anwendung startet lokal.
- FastAPI startet lokal.
- Frontend kann den Health-Endpunkt aufrufen.
- WeasyPrint kann ein einfaches Test-PDF erzeugen.
- Alle Abhängigkeiten sind dokumentiert.

---

# Phase 2 – Datenmodell

## Ziel

Ein einheitliches, serialisierbares Datenmodell für Frontend und Backend.

### Anforderungen

Jeder Lageplan besteht aus:

1. Projektdaten
2. Seiteneinstellungen
3. Hintergrundbild
4. Zeichenobjekten
5. Zeichenreihenfolge

### Objekttypen

**Rectangle**
- ID
- Position
- Breite und Höhe
- Konturfarbe
- Konturstärke
- Füllfarbe
- Transparenz
- Schraffurtyp
- Schraffurfarbe

**Arrow**
- ID
- Startpunkt
- Endpunkt
- Farbe
- Linienstärke
- Pfeilspitzengröße

**Text**
- ID
- Position
- Textinhalt
- Schriftgröße
- Schriftfarbe
- Hintergrundfarbe
- Innenabstand
- Mehrzeiligkeit

### Technische Vorgaben

- [ ] Eindeutige IDs für alle Objekte verwenden.
- [ ] Zeichenobjekte über eine diskriminierte Union anhand von `type` modellieren.
- [ ] Koordinaten ausschließlich im logischen Dokumentkoordinatensystem speichern.
- [ ] Viewport-Zoom und Pan niemals in Dokumentkoordinaten übernehmen.
- [ ] Einheitliches Koordinatensystem mit Ursprung links oben verwenden.
- [ ] Ein festes Seitenverhältnis für A4 definieren.
- [ ] Schema-Version im Dokument vorsehen.
- [ ] Datenmodell mit Pydantic im Backend validieren.
- [ ] Passende TypeScript-Typen erstellen.

### Abnahmekriterien

- Lageplan lässt sich vollständig als JSON serialisieren.
- JSON kann ohne Datenverlust wieder geladen werden.
- Frontend- und Backend-Datenmodelle sind kompatibel.
- Ungültige Objektdaten werden mit verständlichen Fehlermeldungen zurückgewiesen.

---

# Phase 3 – Editor und Hintergrundkarte

## Ziel

Ein interaktiver Editor mit einer festen Dokumentfläche.

### Aufgaben

- [ ] Konva Stage implementieren.
- [ ] A4-Hochformat als logische Dokumentfläche definieren.
- [ ] Hintergrundbild per Dateiauswahl importieren.
- [ ] PNG, JPEG und WebP unterstützen.
- [ ] Bild proportional einpassen.
- [ ] Hintergrundbild verschieben und skalieren können.
- [ ] Hintergrund nach Positionierung sperren.
- [ ] Zoom per Mausrad implementieren.
- [ ] Pan per entsprechendem Werkzeug implementieren.
- [ ] Funktion „An Seite anpassen“ implementieren.
- [ ] Seitenbegrenzung sichtbar darstellen.
- [ ] Transparente oder leere Seitenbereiche weiß darstellen.

### Wichtige Vorgaben

Die Hintergrundkarte muss ihre ursprüngliche Bildqualität behalten. Beim Zoomen darf keine dauerhafte Neuberechnung oder Reduzierung der Originalauflösung erfolgen.

Die Darstellung im Browser darf von der tatsächlichen Dokumentauflösung unabhängig sein.

### Abnahmekriterien

- Benutzer kann eine Liegenschaftskarte hochladen.
- Karte wird korrekt und proportional dargestellt.
- Zoom und Pan funktionieren flüssig.
- Hintergrund lässt sich sperren.
- Dokumentkoordinaten bleiben beim Zoomen unverändert.

---

# Phase 4 – Zeichenwerkzeuge

## Ziel

Implementierung der drei grundlegenden Zeichenwerkzeuge.

## 4.1 Rechteck

### Aufgaben

- [ ] Rechteck durch Klicken und Ziehen erstellen.
- [ ] Rechteck auswählen.
- [ ] Rechteck verschieben.
- [ ] Rechteck über Transformationspunkte skalieren.
- [ ] Konturfarbe konfigurieren.
- [ ] Füllfarbe konfigurieren.
- [ ] Transparenz konfigurieren.
- [ ] Konturstärke konfigurieren.
- [ ] Rechteck löschen.
- [ ] Rechteck duplizieren.

## 4.2 Schraffiertes Rechteck

### Aufgaben

- [ ] Diagonale Schraffur implementieren.
- [ ] Kreuzschraffur implementieren.
- [ ] Schraffur deaktivieren können.
- [ ] Schraffurfarbe konfigurieren.
- [ ] Schraffurabstand definieren.
- [ ] Schraffur beim Skalieren korrekt darstellen.

### Vorgabe

Schraffuren als Pattern rendern, nicht als zahlreiche unabhängige Zeichenobjekte.

## 4.3 Pfeil

### Aufgaben

- [ ] Pfeil durch Ziehen von Start- zu Endpunkt erstellen.
- [ ] Pfeil auswählen und verschieben.
- [ ] Startpunkt separat bearbeiten.
- [ ] Endpunkt separat bearbeiten.
- [ ] Farbe und Linienstärke konfigurieren.
- [ ] Pfeilspitzengröße konfigurieren.
- [ ] Pfeil löschen.

## 4.4 Text mit Hintergrund

### Aufgaben

- [ ] Textfeld per Klick erstellen.
- [ ] Text über ein HTML-Textarea bearbeiten.
- [ ] Mehrzeilige Texte unterstützen.
- [ ] Hintergrundrechteck automatisch an Textgröße anpassen.
- [ ] Innenabstand konfigurieren.
- [ ] Schriftgröße konfigurieren.
- [ ] Schriftfarbe konfigurieren.
- [ ] Hintergrundfarbe konfigurieren.
- [ ] Textfeld verschieben.
- [ ] Textfeld löschen.

### Abnahmekriterien

- Alle Objekttypen lassen sich erstellen und bearbeiten.
- Werkzeuge funktionieren bei unterschiedlichen Zoomstufen.
- Objektpositionen bleiben stabil.
- Änderungen sind sofort sichtbar.
- Alle Eigenschaften werden im JSON gespeichert.

---

# Phase 5 – Auswahl, Eigenschaften und Undo/Redo

## Ziel

Produktive und intuitive Bearbeitung der Zeichnung.

### Aufgaben

- [ ] Auswahlwerkzeug implementieren.
- [ ] Aktives Objekt visuell hervorheben.
- [ ] Konva Transformer für geeignete Objekte einsetzen.
- [ ] Eigenschaftenpanel für das ausgewählte Objekt implementieren.
- [ ] Farben über Color Picker ändern.
- [ ] Objekt über Delete/Backspace löschen.
- [ ] Escape zum Abbrechen aktueller Aktionen unterstützen.
- [ ] Undo/Redo über History-Stack implementieren.
- [ ] Tastenkürzel für Undo/Redo unterstützen.
- [ ] Objekte in der Zeichenreihenfolge nach vorne/hinten bewegen.
- [ ] Aktive Werkzeugauswahl in der Toolbar hervorheben.

### Technische Vorgaben

- History auf Basis von Änderungen am Dokumentmodell.
- Nicht jede Mausbewegung als separaten History-Eintrag speichern.
- Drag- und Resize-Aktionen als einzelne Undo-Operation behandeln.
- Kein Undo/Redo für reine Viewport-Änderungen erforderlich.

### Abnahmekriterien

- Alle Bearbeitungsschritte können rückgängig gemacht werden.
- Undo/Redo funktioniert auch nach Verschieben und Skalieren.
- Auswahl und Eigenschaftenpanel bleiben synchron.
- Keine unbeabsichtigten Änderungen an gesperrten Objekten.

---

# Phase 6 – SVG-Renderer im Backend

## Ziel

Die JSON-Zeichnungsdaten serverseitig in SVG umwandeln.

### Aufgaben

- [ ] `svg_renderer.py` implementieren.
- [ ] SVG-Root mit definiertem `viewBox` erzeugen.
- [ ] Hintergrundbild positionieren.
- [ ] Rechtecke in SVG umwandeln.
- [ ] Schraffuren über SVG-Patterns erzeugen.
- [ ] Pfeile mit Linien und Pfeilspitzen erzeugen.
- [ ] Textfelder mit Hintergrundrechteck erzeugen.
- [ ] Objekt-Reihenfolge beibehalten.
- [ ] Transparenzen korrekt übernehmen.
- [ ] Sonderzeichen in Texten korrekt escapen.
- [ ] Zeilenumbrüche in SVG-Texten unterstützen.
- [ ] Schriftarten kontrolliert festlegen.

### Besondere Anforderungen

Der SVG-Renderer darf nicht vom Browser abhängig sein.

Er muss vollständig auf Grundlage der JSON-Daten arbeiten.

Für die Textdarstellung müssen Frontend und Backend abgestimmte Schriftarten und Layoutregeln verwenden. Textumbrüche und Textfeldabmessungen dürfen nicht allein aus browserabhängigen Messwerten abgeleitet werden.

### Abnahmekriterien

- JSON wird in valides SVG umgewandelt.
- Rechtecke und Schraffuren stimmen visuell mit dem Frontend überein.
- Pfeile zeigen auf die korrekten Koordinaten.
- Textfelder werden korrekt positioniert.
- Keine ungewollten Verschiebungen oder Skalierungen.

---

# Phase 7 – PDF-Rendering mit WeasyPrint

## Ziel

Erzeugung eines druckfähigen A4-PDFs aus dem Lageplan.

### Aufgaben

- [ ] Jinja2-HTML-Vorlage erstellen.
- [ ] A4-Seitenformat definieren.
- [ ] Seitenränder festlegen.
- [ ] Projekttitel einfügen.
- [ ] Adresse einfügen.
- [ ] Gemarkung, Flur und Flurstück einfügen.
- [ ] SVG-Lageplan in HTML einbetten.
- [ ] PDF mit WeasyPrint erzeugen.
- [ ] PDF über FastAPI zurückgeben.
- [ ] Passenden Dateinamen erzeugen.
- [ ] Content-Type `application/pdf` setzen.

### API

`POST /api/lageplan/render`

**Request:** JSON-Dokument des Lageplans mit Referenz auf das zuvor hochgeladene Hintergrundbild.

**Response:** PDF als Binärdatei.

### Layout

- A4 Hochformat
- Titel und Projektdaten oben
- Lageplan darunter
- Optional Nordpfeil
- Weißer Seitenhintergrund
- Keine abgeschnittenen Objekte
- Keine zusätzlichen leeren Seiten

### Abnahmekriterien

- PDF wird vollständig im Backend erzeugt.
- Export funktioniert ohne Browser-Screenshot.
- Annotationen bleiben vektorbasiert.
- Hintergrundbild ist korrekt eingebettet.
- Text und Pfeile entsprechen der Editoransicht.
- PDF enthält genau eine A4-Seite.

---

# Phase 8 – Import, Export und Projektspeicherung

## Ziel

Benutzer können ihre Lagepläne exportieren und später weiterbearbeiten.

### Aufgaben

- [ ] JSON-Export implementieren.
- [ ] JSON-Import implementieren.
- [ ] Hintergrundbild zusammen mit dem Projekt wiederherstellen.
- [ ] PDF-Download im Frontend implementieren.
- [ ] Ladeanzeige während PDF-Erzeugung anzeigen.
- [ ] Backend-Fehler verständlich anzeigen.
- [ ] Dateinamen aus Projektdaten erzeugen.
- [ ] Schema-Version beim JSON-Import prüfen.

### Vorgabe

Für einen eigenständig wiederherstellbaren Projekt-Export ein ZIP-Format mit `project.json` und Hintergrundbild vorsehen. Reine JSON-Exporte dürfen nur dann als vollständig bezeichnet werden, wenn alle referenzierten Assets dauerhaft verfügbar sind.

### Abnahmekriterien

- Gespeicherte Projekte lassen sich erneut öffnen.
- Sämtliche Zeichnungsobjekte bleiben erhalten.
- Hintergrundbild wird korrekt wiederhergestellt.
- PDF-Export funktioniert nach erneutem Laden.

---

# Phase 9 – Qualitätssicherung

## Ziel

Sicherstellen, dass Frontend-Darstellung und PDF-Ausgabe übereinstimmen.

### Backend-Tests

- [ ] Rechteck-Rendering testen.
- [ ] Schraffur-Rendering testen.
- [ ] Pfeil-Rendering testen.
- [ ] Textfeld-Rendering testen.
- [ ] Sonderzeichen und Umlaute testen.
- [ ] PDF-Seitenformat testen.
- [ ] Ungültige JSON-Daten testen.
- [ ] Fehlende Hintergrundbilder testen.
- [ ] Bildgrößen und Upload-Limits testen.
- [ ] Unsichere externe SVG-/HTML-Referenzen blockieren.

### Frontend-Tests

- [ ] Hintergrundbild-Import testen.
- [ ] Rechteck erstellen und bearbeiten.
- [ ] Pfeil erstellen und bearbeiten.
- [ ] Textfeld erstellen und bearbeiten.
- [ ] Zoom und Koordinatentransformation testen.
- [ ] Undo/Redo testen.
- [ ] Projekt speichern und laden.
- [ ] PDF-Export auslösen.

### Visuelle Regressionstests

Mindestens drei Referenzfälle erstellen:

1. Einfacher Lageplan mit Rechteck
2. Lageplan mit Schraffur, Pfeilen und mehreren Textfeldern
3. Komplexer Lageplan mit mehreren überlappenden Objekten

Die resultierenden PDFs müssen visuell mit den erwarteten Ergebnissen verglichen werden.

---

# Phase 10 – Dokumentation und Fertigstellung

### Aufgaben

- [ ] README mit Installationsanleitung erstellen.
- [ ] Frontend-Startbefehl dokumentieren.
- [ ] Backend-Startbefehl dokumentieren.
- [ ] WeasyPrint-Systemabhängigkeiten dokumentieren.
- [ ] API-Schnittstelle dokumentieren.
- [ ] JSON-Schema dokumentieren.
- [ ] Beispielprojekt bereitstellen.
- [ ] Beispiel-PDF erzeugen.
- [ ] Bekannte Einschränkungen dokumentieren.

## Definition of Done

Das Projekt ist fertig, wenn ein Benutzer:

1. Den Editor öffnen kann.
2. Einen Screenshot der Liegenschaftskarte hochladen kann.
3. Rechtecke mit und ohne Schraffur zeichnen kann.
4. Farben und Transparenzen verändern kann.
5. Pfeile zeichnen und bearbeiten kann.
6. Textfelder mit Hintergrund erstellen kann.
7. Alle Objekte verschieben, skalieren oder löschen kann.
8. Änderungen rückgängig machen kann.
9. Den Lageplan als Projekt speichern und wieder öffnen kann.
10. Ein korrektes A4-PDF über das Python-Backend exportieren kann.

---

# Verbindliche Arbeitsanweisungen für den Coding-Agenten

1. Implementiere die Phasen in der angegebenen Reihenfolge.
2. Prüfe vor jeder Phase den bestehenden Projektstand und verwende vorhandene Komponenten, sofern sie geeignet sind.
3. Erstelle keine unnötigen Abstraktionsschichten oder zusätzlichen Frameworks.
4. Verwende konsequent TypeScript im Frontend und Typannotationen im Python-Backend.
5. Trenne Zeichenlogik, Datenmodell und PDF-Rendering sauber voneinander.
6. Verwende keine Canvas-Screenshots für den PDF-Export.
7. Verwende für PDF-Annotationen SVG-Vektorelemente.
8. Implementiere jede Funktion vollständig, einschließlich Fehlerbehandlung.
9. Schreibe für kritische Funktionen automatisierte Tests.
10. Führe nach jeder Phase die relevanten Tests aus und behebe Fehler, bevor du fortfährst.
11. Dokumentiere technische Entscheidungen, die vom ursprünglichen Plan abweichen.
12. Halte die Roadmap aktuell und markiere abgeschlossene Aufgaben.
13. Erstelle nach jeder Phase eine kurze Zusammenfassung der implementierten Funktionen und Testergebnisse.
14. Frage nur bei Entscheidungen nach, die eine wesentliche Änderung der Anforderungen oder Architektur bedeuten.
15. Verwende für den MVP keine Datenbank, Authentifizierung oder externe Dienste, sofern diese nicht ausdrücklich benötigt werden.

**Priorität:** Ein einfacher, stabiler und gut bedienbarer Lageplan-Editor mit reproduzierbarem, serverseitigem PDF-Rendering ist wichtiger als ein umfangreicher Funktionskatalog.
