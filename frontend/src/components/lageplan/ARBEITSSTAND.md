# Lageplan-Editor — Arbeitsstand

## Stand 25.10.2026, 10:19 — Konva-Beispiel übernommen, Test ausstehend

Kolya hat am 25.10. die Freigabe gegeben ("bauen"), nachdem ich mich tagelang
mit selbstgebauten Handles verrannt hatte. Vorgabe: **sein Konva-Beispiel 1:1
übertragen, keine Eigenbauten, keine Raterei.**

### Umgesetzt (gebaut, noch NICHT verifiziert)

1. **`LageplanElement.vue`**
   - jede Element-Group bekommt `name: 'el-' + element.id`
   - per-Element `<v-transformer>` entfernt, `VTransformer`-Import raus
   - `transformend`-Emit entfernt
   - Config enthält **kein** `rotation`/`scaleX`/`scaleY` — genau das ist der Trick
     aus dem Beispiel: was nicht in der Config steht, kann Vue beim Re-Render
     nicht überschreiben, also bleibt die Transformation am Konva-Node stehen.

2. **`LageplanStage.vue`**
   - **ein** `<v-transformer ref="trRef">` als letztes Kind des `<v-layer ref="layerRef">`
   - `attachTransformer(id)`: `layerNode.findOne('.el-' + id)` → `trNode.nodes([node])`
     → `moveToTop()` → `batchDraw()`
   - `watch(() => props.store.selectedId, ...)` mit `nextTick`
   - `handleStageClick`: Abwahl nur wenn `activeTool === 'select'` **und** Target
     ist die Stage selbst oder ein `Image`
     (Guard auf activeTool nötig: sonst würde der Klick direkt nach dem Aufziehen
     eines Rechtecks die frische Auswahl sofort wieder wegnehmen)
   - `:store="store"` an `LageplanElement` durchgereicht — fehlte vorher komplett,
     dadurch war `draggable` immer false und Objekte ließen sich nicht verschieben
   - `boundBoxFunc`: Mindestgröße 4px
   - `onElementTransformEnd` entfernt
   - Container-Höhe: `stageHeight + 'px'` (vorher Einheit vergessen → ungültiges CSS)

3. **`useLayoutStore.js`**
   - Rückgabe in `reactive({...})` gewrappt.
     Grund: Der Store wurde als **plain object mit Refs** zurückgegeben und als
     Prop durchgereicht. `props.store` wird nicht ausgepackt, also war
     `store.selectedId === el.id` ein Vergleich Ref-Objekt gegen String →
     immer false, und `store.activeTool = 'rect'` hat den Ref **ersetzt**.
     Mit `reactive()` packt Vue die verschachtelten Refs beim Zugriff aus.

4. **`LageplanHandles.vue`** (mein Eigenbau) entfernt
   → liegt unter `~/Backups/lageplan/LageplanHandles.vue.<timestamp>`

Build läuft durch: `dist/assets/LageplanView-OlX2V70j.js`, BUILD_TIME
`2026-10-25T10:19:01.000Z`.

### Deploy + erster Test (25.10.2026, 10:21) — Kernanforderung erfüllt

Deployed: `index-CAqMX5Y1.js`, BUILD_TIME `2026-10-25T10:19:01.000Z`,
Container `na-frontend` neu gebaut und gestartet.

**Playwright-Messung (Screenshots `/home/moltbot/clawd/t1-drei.png` … `t6-r3-selected.png`):**

| Schritt | Messung | Bewertung |
|---|---|---|
| T1 3 Rechtecke à 200×150 | Rechtecke vom Farbfilter nicht erfasst | Testproblem, nicht App |
| T3 R1 skaliert | Box 299×224 (Soll 300×225) | **passt** |
| T4 R2 ausgewählt | R1 weiterhin 300×225 | **Zustand bleibt** ✔ |
| T6 R3 ausgewählt | R1 weiterhin 300×225 | **Zustand bleibt** ✔ |
| T5 Rotation R2 | keine gedrehte Box gefunden | **unklar — offen** |

Keine Konsolenfehler, kein PAGEERROR.

**Damit belegt:** Skalieren funktioniert und der transformierte Zustand
überlebt die Auswahl eines anderen Objekts — genau der Punkt, der
tagelang kaputt war. Ursache war die Kombination aus per-Element-Transformer,
`rotation` in der Vue-Config und dem nicht ausgepackten Store-Ref.

**Sichtprüfung der Screenshots (25.10.2026, 10:22) — bestätigt:**
- 3 Rechtecke werden sauber platziert (hellblaue Fläche `#dbeafe`,
  Rand kräftig blau)
- Auswahl zeigt den Konva-Transformer: 8 weiße Anker + Rotations-Handle
  über der Oberkante, mit Verbindungslinie — Standard-Konva-Optik
- Nach dem Skalieren ist R1 sichtbar größer, Rahmen und Anker sitzen bündig
- In T6 (R3 angeklickt) ist R1 **weiterhin vergrößert** — der Zustand bleibt

**Zweiter Testlauf (10:24, Handle-Offset 50) — Screenshots `v1`–`v4`:**
- `v1` R1 skaliert: korrekt, Transformer sitzt bündig
- `v2` R2 angeklickt: **Auswahl springt NICHT um**, Transformer bleibt an R1
- `v3` nach dem Rotations-Drag: **alle Anker weg**, nichts gedreht,
  Eigenschaften-Panel verschwunden → Auswahl wurde komplett gelöscht
- `v4` R3 angeklickt: Transformer hängt wieder an **R1**, nicht an R3;
  Panel sagt „rect" — also ist R1 weiterhin selektiert

**Diagnose (belegt, nicht geraten):** Skalieren und Persistenz funktionieren.
Kaputt ist der **Auswahlwechsel**: ein Klick auf ein anderes Element ändert
`selectedId` nicht. Wahrscheinlichste Ursache — zu prüfen, nicht annehmen:
`handleStageClick` feuert nach `onElementClick` (Konva-Bubbling: der Klick
auf das Element blubbert zur Stage). Die Abwahl-Bedingung prüft zwar auf
`target === stageNode`, aber die Reihenfolge Element-Klick → Stage-Klick
kann die frisch gesetzte Auswahl wieder kassieren.
Gegenprobe im Beispiel: dort sitzt `@click` am Shape **und** an der Stage,
und die Stage-Abwahl greift nur bei `target === stage || className === 'Image'`.
→ Nächster Schritt: in `onElementClick` und `handleStageClick` je ein
`console.log` mit `e.target.getClassName()` + `name()`, Testlauf, Logs lesen.
Erst danach ändern.

**Farbwerte für den Cluster-Test:** Füllung ist sehr helles Blau
(ca. `#dbeafe`), **nicht** `#1d4ed8`. Für Messungen den Rand nehmen
oder die Store-Defaults auslesen statt raten.

### Code-Stand an den Klick-Handlern (25.10.2026, 10:26)

`LageplanStage.vue`, Zeilennummern zum Wiederfinden:
- Z. 14/15: `<v-stage @click="handleStageClick" @tap="handleStageClick">`
- Z. 48: `<LageplanElement @click="onElementClick(el)">`
- Z. 251 `onElementClick(el)`: setzt `props.store.selectedId = el.id`,
  nur wenn `activeTool === 'select'`
- Z. 260 `attachTransformer(id)`: `layerNode.findOne('.el-' + id)` →
  `trNode.nodes([node])` → `moveToTop()` → `batchDraw()`
- Z. 271: `watch(() => props.store.selectedId, id => nextTick(() => attachTransformer(id)))`
- Z. 277 `handleStageClick(e)`: Abwahl nur bei `activeTool === 'select'`
  **und** `target === stageNode || target.getClassName() === 'Image'`

### URSACHE GEFUNDEN (25.10.2026, 10:28) — alle Elemente haben dieselbe ID

Debug-Logs im Browser (eingebaut, bleiben auf Kolyas Wunsch drin):

```
[LP] onElementClick preview tool= select
[LP] selectedId gesetzt -> preview
[LP] handleStageClick target= Rect name= isStage= false
```

Bei **jedem** Element-Klick kommt `preview` — nie eine echte Element-ID.

Der Grund steht in `useLayoutStore.js` Z. 30-35:
```js
function addElement(element) {
  const id = element.id || nextId()   // <-- element.id ist 'preview'
  layout.elements.push({ ...element, id })
```
Das Vorschau-Objekt wird in `LageplanStage.vue` Z. 192/194/196 mit
`id: 'preview'` erzeugt. In `onMouseUp` (Z. 234) wird genau dieses Objekt an
`addElement` übergeben — `element.id` ist also gesetzt und `nextId()` läuft nie.
**Folge: jedes gezeichnete Element heißt `preview`.**

Damit erklärt sich alles beobachtete Verhalten:
- `store.selectedId === el.id` trifft auf **alle** Elemente zu
- `layerNode.findOne('.el-preview')` liefert immer den **ersten** Treffer (R1)
  → der Transformer klebt an R1, egal was angeklickt wird
- der Rotations-Drag greift am falschen Node an → Auswahl verschwindet

Mein vorheriger Verdacht (Klick blubbert zur Stage und kassiert die Auswahl)
war **falsch**: `handleStageClick` sieht bei Element-Klicks `target= Rect`,
fällt also korrekt durch die Abwahl-Bedingung und löscht nichts.
Gut, dass erst gemessen wurde.

**Fix gebaut (Freigabe 25.10. 10:28), eine Zeile in `onMouseUp`:**
```js
const el = previewElement.value
previewElement.value = null
if (!el) return
delete el.id          // <-- sonst bleibt jedes Element 'preview'
```
Die ursprünglich vorgeschlagenen Fixes (Preview nullen) hätten **nicht**
geholfen — `previewElement.value = null` passiert bereits in Z. 235.

---

## ✅ 25.10.2026, 10:29 — Editor funktioniert, verifiziert

Deployed: `LageplanView-DiL6Uabp.js`, BUILD_TIME `2026-10-25T10:28:54`.

**Konsolen-Logs — IDs sind jetzt eindeutig:**
```
[LP] onElementClick el-1792920567290-1 -> selectedId gesetzt
[LP] onElementClick el-1792920568606-2 -> selectedId gesetzt
[LP] onElementClick el-1792920569956-3 -> selectedId gesetzt
```
Die Auswahl springt sauber zwischen allen drei Objekten. Keine PAGEERRORs.

**Sichtprüfung (Screenshots `/home/moltbot/clawd/w1`–`w5`):**

| Screenshot | Ergebnis |
|---|---|
| `w1-drei.png` | 3 Rechtecke à 200×150 platziert |
| `w2-r3-gewaehlt.png` | Auswahl springt R1 → R2 → R3 |
| `w3-r1-skaliert.png` | R1 auf ~300×225 skaliert, Anker sitzen bündig |
| `w4-r2-gedreht.png` | R2 um 45° gedreht, **Anker drehen mit** (Raute) |
| `w5-final.png` | R3 ausgewählt — R1 bleibt groß, R2 bleibt gedreht |

**Damit sind alle vier Anforderungen erfüllt:**
platzieren ✔ · skalieren ✔ · drehen ✔ · Zustand überlebt Auswahlwechsel ✔

Debug-Logs bleiben auf Kolyas ausdrücklichen Wunsch im Code.

**Nächster Schritt laut Kolya:** sichern + committen, danach die nächsten
Schritte besprechen. PDF-Export bleibt bewusst ausgeklammert.

---

## 25.10.2026, 12:57 — Rechteck OK, **Schraffur kaputt** (neue Meldung)

Kolya: „ok, mit dem rechteck funktioniert / Schraffur ist nun kaputt"
→ Noch **nicht committet**. Erst Schraffur reparieren.

### Befund aus dem Code (nur gelesen, noch nichts geändert)

**`LageplanStage.vue`**
- Z. 195/196 `onMouseDown`, Werkzeug `hatching`:
  `previewElement.value = { id: 'preview', kind: 'hatching', points: [[p.x,p.y]],
   fill: 'none', stroke: '#1d4ed8', stroke_width: 1, hatch_angle: 45, hatch_spacing: 4 }`
- Z. 221-225 `onMouseMove`: hängt Punkte an `points` an bzw. ersetzt den letzten
- Z. 249 `onMouseUp`: übernimmt nur, wenn `el.points.length >= 3`

**`LageplanElement.vue`**
- Z. 9: Schraffur-Group hat `name: 'el-' + element.id` (von mir ergänzt) ✔
- Z. 10: Umriss `<v-line :points="flatPoints" closed fill=element.fill ...>`
- Z. 12: Schraffurlinien `v-for` über `hatchLines`
- `flatPoints` (Z. 38-43): flacht `element.points` ([[x,y],…]) auf [x,y,x,y,…] ab
- `hatchLines` (Z. 46 ff.): diagonale Linien über die Bounding-Box der Punkte

### URSACHE BELEGT (25.10.2026, 13:00) — `points` wächst nie über 2

**Reproduziert:** Schraffur-Werkzeug gewählt, von (200,200) nach (400,350)
gezogen → **Canvas bleibt leer**, Store bekommt nichts, Klick danach trifft
nur die Stage (`[LP] handleStageClick target= Stage … abgewaehlt`).
Screenshots: `/home/moltbot/clawd/h1-schraffur-gezeichnet.png`,
`h2-schraffur-geklickt.png`.

**Der Widerspruch steckt in `LageplanStage.vue`:**
```js
// onMouseMove, Z. 219-225
} else if (tool === 'hatching' && previewElement.value) {
  if (previewElement.value.points.length < 2) {
    previewElement.value.points.push([p.x, p.y])      // nur 1x erreicht
  } else {
    previewElement.value.points[len - 1] = [p.x, p.y] // ersetzt ab dann nur
  }
}

// onMouseUp, Z. 249
} else if (tool === 'hatching' && el.points.length >= 3) {
  props.store.addElement(el)
}
```
Start = 1 Punkt, die erste Mausbewegung pusht auf 2, **jede weitere ersetzt
nur den letzten**. `points.length` bleibt also für immer 2 — die Bedingung
`>= 3` in `onMouseUp` ist nie erfüllt. Die Schraffur wird nie angelegt.

**Nicht von mir verursacht:** `git diff` auf `LageplanStage.vue` zeigt
keine meiner Änderungen an `hatching` oder `points`. Der Widerspruch
stammt aus dem Commit-Stand. Vorher fiel es nicht auf, weil die Auswahl
ohnehin nicht funktionierte.

**Kolyas Entscheidung 25.10. 13:00: „genau wie beim rechteck"** → Variante (a).

### Gebaut (25.10.2026, 13:01) — Build `2026-10-25T13:01:31`

`LageplanStage.vue`, `onMouseMove`:
```js
} else if (tool === 'hatching' && previewElement.value) {
  // Wie beim Rechteck: aus Start- und Aktuellpunkt ein 4-Punkt-Polygon
  const x1 = Math.min(s.x, p.x), y1 = Math.min(s.y, p.y)
  const x2 = Math.max(s.x, p.x), y2 = Math.max(s.y, p.y)
  previewElement.value.points = [[x1,y1],[x2,y1],[x2,y2],[x1,y2]]
}
```
`onMouseUp`: Mindestgröße jetzt über die Bounding-Box (`w > 5 && h > 5`)
statt über `points.length >= 3`.

**Testergebnis (Screenshots `s1`–`s4`):**
- `s1` Schraffur lässt sich aufziehen, wird angelegt, Panel zeigt `hatching` ✔
- `s3` Schraffur skaliert sauber mit Transformer ✔
- `s4` Rechteck angeklickt → Auswahl springt um, Schraffur **bleibt groß** ✔
- Logs: `onElementClick el-…-1` (Line) und `el-…-2` (Rect), eindeutige IDs,
  keine PAGEERRORs ✔

### Schraffur-Optik: schwarz statt orange — Ursachen belegt (25.10., 13:20)

Kolyas Vorgabe: **orange Linien auf transparentem Grund, Umriss ebenfalls
orange.** Rückfrage von ihm: „Das hat schon mal funktioniert, wieso ist das
jetzt kaputt?"

**Antwort aus der Historie — es war nie orange:**
- `git log` zeigt für die Lageplan-Dateien **genau einen** Commit: `312ae8c`
- Dort steht bereits `fill: 'none', stroke: '#1d4ed8'` (blau)
- `grep` über `frontend/src` + `backend/src` nach `f97316|orange|ea580c|fb923c`
  findet **nichts**
- Der einzige Orangeton im Projekt waren die Anker meiner selbstgebauten
  `LageplanHandles.vue` (`#f97316`) — die Datei ist gelöscht
  (liegt in `~/Backups/lageplan/`)
- Backend `schemas.py`: `HatchingElement.stroke` default `#1d4ed8`,
  `fill` default `"none"`

→ Das Orange, das Kolya erinnert, waren sehr wahrscheinlich meine
Transformer-Anker, nicht die Schraffur.

**Warum jetzt schwarz — und warum das keine Regression ist:**
`fill: 'none'` ist in **SVG** gültig (der Backend-Renderer nutzt es korrekt),
in **Canvas/Konva** aber nicht. Konva reicht den Wert an `ctx.fillStyle`
durch; ein ungültiger Wert wird ignoriert und es bleibt bei Schwarz.
Vorher fiel das nie auf, weil wegen `points.length >= 3` überhaupt nie
eine Schraffur entstanden ist. Jetzt, wo sie entsteht, wird der alte
Fehler zum ersten Mal sichtbar.

**Zweiter Fehler — Schraffurlinien fehlen komplett.**
`hatchLines` in `LageplanElement.vue` (Z. 46 ff.) setzt
`x1b = minX, y1b = minX + d` und `x2b = maxX, y2b = maxX + d` und
überspringt die Linie, sobald **einer** der beiden Endpunkte außerhalb
`[minY, maxY]` liegt. Bei 200×150 liegen die beiden y-Werte 200 px
auseinander, die Box ist aber nur 150 hoch → fast jede Linie fällt raus.
Der Backend-Renderer `svg_renderer._hatch_lines` macht es richtig:
er schneidet die Gerade `y = x + d` mit **allen vier** Kanten der
Bounding-Box und nimmt den ersten und letzten Treffer.

### Gebaut (Freigabe 25.10. 13:21) — Build `2026-10-25T13:22:15`

1. `LageplanElement.vue`: neues `konvaFill`-Computed —
   `!f || f === 'none' ? null : f`. Store-/Backend-Wert `'none'` bleibt,
   Konva bekommt `null` = echte Transparenz.
2. `hatchLines` durch die 4-Kanten-Schnittlogik aus `svg_renderer.py` ersetzt.
3. `LageplanStage.vue`: Schraffur-Default `stroke: '#f97316'` (orange),
   färbt Umriss und Linien (beide lesen `element.stroke`).
4. Backend `schemas.py` **nicht** angefasst — Default dort weiterhin
   `#1d4ed8`. Funktional egal (jedes Element trägt sein `stroke` mit),
   aber Frontend und Backend driften auseinander. Offen.

**Ergebnis (Screenshots `o1-schraffur.png`, `o3-final.png`):**
Schraffur ist transparent mit orangen 45°-Linien und orangem Umriss,
skaliert sauber mit dem Transformer und bleibt erhalten, wenn das
Rechteck ausgewählt wird. Keine PAGEERRORs, IDs eindeutig.

### Restdefekt: unschraffiertes Dreieck oben rechts

In beiden Screenshots bleibt die obere rechte Ecke ohne Linien.
Ursache ist der Startwert der Schleife — er stammt aus dem Backend und
ist dort **genauso falsch**:
```js
for (let d = minX - maxY; d < maxX - minY; d += spacing)
```
Für `y = x + d` liegt die Ecke unten links bei `d = maxY - minX`,
die Ecke oben rechts bei `d = minY - maxX`.
Beispiel 200..400 × 200..350: nötig ist `d` von **-200 bis +150**,
die Schleife läuft aber von **-150 bis +200** — unten rechts wird
ins Leere gerechnet, oben rechts fehlt der Streifen.

**Behoben am 25.10. 13:26** (Build `2026-10-25T13:26:09`), eine Zeile in
`LageplanElement.vue`:
```js
for (let d = minY - maxX; d <= maxY - minX; d += spacing)
```
Gegenprobe mit zwei Schraffuren — breit (200×150) und hoch (150×250):
beide sind vollständig durchschraffiert, auch oben rechts.
Screenshot `/home/moltbot/clawd/p1-schraffur-ecken.png`.

**Backend bleibt unangetastet.** Kolya am 25.10. 13:24 deutlich:
„wieso machst du am beackend rum? ich habe doch ausdrücklich gesagt,
editor zuerst!" — `svg_renderer.py` wurde nur *gelesen*, um die Formel
nicht neu zu erfinden; geändert ist dort nichts (`git diff` betrifft
ausschließlich die drei Editor-Dateien). Dass derselbe Bereichsfehler
auch im Backend steckt, ist **kein Thema**, bis der Editor fertig ist.

### Schraffurabstand: mm wurden als Pixel gelesen (25.10. 13:29)

Kolya: „die schraffur linien sind viel zu eng zueinander."

`hatch_spacing` ist ein **Millimeter**-Wert (Default 4). Die Zeichenfläche
läuft aber mit **3 px/mm** (`LageplanStage.vue` Z. 97/98:
`PAGE_W = 297 * 3`, `PAGE_H = 210 * 3` — A4 quer). `hatchLines` hat die 4
direkt als Pixelabstand verwendet → 4 px statt 12 px, also dreimal zu dicht.

Fix in `LageplanElement.vue` (Build `2026-10-25T13:29:31`):
```js
const MM_PX = 3
const spacing = (props.element.hatch_spacing || 4) * MM_PX
```
Gegenprobe mit breiter (200×150) und hoher (150×250) Schraffur: Linien
stehen sichtbar auseinander, Ecken weiterhin vollständig gefüllt.
Screenshot `/home/moltbot/clawd/q1-abstand.png`.

Merke: Die Element-Koordinaten im Store sind **Pixel** (3 px/mm), die
Schraffur-Parameter aus dem Backend-Schema sind **Millimeter**. Wer die
beiden verwechselt, bekommt genau solche Faktor-3-Fehler.

---

## Text direkt im Canvas bearbeiten (25.10.2026, 14:30)

Kolyas Vorgabe 14:21: „bitte editable text direkt in kanva" + Konva-Beispiel
(DOM-Textarea über dem Konva-Text). Freigabe: „passt".
`prompt()` ist damit raus.

### Gebaut — Build `2026-10-25T14:28`

**`LageplanElement.vue`**
- `<v-text>` bekommt `width: element.width || undefined` und
  `visible: !editing` (neues Prop `editing`)
- `@dblclick`/`@dbltap` → `emit('edit', element)`
- Group feuert `@transform` → `emit('transform', element)`

**`LageplanStage.vue`**
- `editingId`-Ref; Element bekommt `:editing="editingId === el.id"`
- `startTextEdit(el, isNew)`: DOM-`<textarea>` über `absolutePosition()` +
  `stage.container().getBoundingClientRect()`, Stil vom Konva-Node geerbt.
  Zusätzlich zum Beispiel: `fontSize` und Breite werden mit
  `getAbsoluteScale().x` multipliziert, weil unsere Stage zoomt.
  Enter bestätigt, Shift+Enter bricht um, Escape verwirft, Klick außerhalb
  bestätigt. Leerer Text → Element wird wieder entfernt.
- Text-Werkzeug legt ein leeres Element an und öffnet sofort den Editor
- `attachTransformer`: bei `kind === 'text'` nur `middle-left`/`middle-right`,
  sonst alle acht Anker

### Fallstrick: Fokus (gemessen, nicht geraten)
`ta.focus()` direkt nach dem Anlegen wirkt **nicht** — der auslösende Klick
zieht den Fokus danach auf `<body>` zurück. Gemessen:
`document.activeElement` war `BODY`, getippter Text kam nie an, Enter und
Escape liefen ins Leere. Lösung: Fokus in denselben `setTimeout`, in dem
auch der Outside-Click-Listener registriert wird.

### Verifiziert
- Klick mit Text-Werkzeug öffnet Textarea, Fokus liegt darauf ✔
- Tippen + Enter schreibt den Text ins Canvas ✔
- Doppelklick öffnet den Editor mit vorhandenem Inhalt ✔
- Enter übernimmt die Änderung („Garage Nord" → „Carport Sued") ✔
- Escape schließt ohne leeres Element zu hinterlassen ✔
- Keine PAGEERRORs ✔

**Testhinweis:** Ein Doppelklick auf die **linke Textkante** trifft den
Transformer-Anker `middle-left`, nicht den Text — dann öffnet sich der
Editor nicht. In der Textmitte klicken. Betrifft nur die Kanten.

### Offener Defekt: Breiten-Drag rechnet zu stark
Anker `middle-right` von 160 px um 70 px nach links gezogen → erwartet 90,
gemessen **46**. `scaleX` landet korrekt wieder auf 1, der Text bricht also
um statt sich zu verzerren — aber der Faktor stimmt nicht.

Ursache: Im Beispiel hängt der Transformer **direkt am Text-Node**, und
`handleTransform` setzt `scaleX` genau auf diesem Node zurück. Bei uns hängt
er an der **Group**, während die Breite vom **Text-Kind** gelesen wird.
`@transform` feuert während des Ziehens laufend; das Zurücksetzen von
`group.scaleX` mitten im Drag bringt den Transformer aus dem Tritt, die
Skalierung multipliziert sich auf (0,5625 → ~0,32).

Sauberer Weg, Kolya vorlegen: für Text-Elemente `name: 'el-' + id` und
`draggable` auf den **Text-Node** statt auf die Group legen. Dann hängt der
Transformer wie im Beispiel direkt am Text. **Noch nicht gebaut.**

### Gemessen (25.10.2026, 14:44) — Textgröße 24px nicht sichtbar

Kolya 14:39: „erstmal so commiten und pushen. danach: der Text soll
doppelt so groß sein. der Text soll auf einem hellen hintergrund
erscheinen."

Commit `7c11a92` gepusht, dann `font_size` 12→24 und A4-`fill: '#f8fafc'`
gebaut, Build `2026-10-25T14:45:31.000Z`, Container neu.

**Gemessen:**
- Helliger Hintergrund: ✔ Pixel (150,226) = (248,250,252)
- `fontSize` des Text-Nodes: **12**, erwartet 24.
  `grep` in der Source: `font_size: 24` ist in `LageplanStage.vue` Z. 211.

**Bedeutung:** Die laufende App lief noch mit dem alten JS — die
Build-Zeit im geladenen Bundle war weiterhin die alte. Der Text wurde
also mit der alten Größe erzeugt.

**Warum das wichtig ist:** Ohne das Messen wäre die Aussage
„doppelt so groß" als erledigt durchgegangen, wäre aber falsch gewesen.

### Korrektur (25.10.2026, 15:16): Heller Hintergrund NUR am Textfeld

Kolya: „nein, nur am text feld soll der helle hintergrud sein!"

Die A4-Füllung `fill: '#f8fafc'`, die ich gebaut hatte, ist wieder raus
(das A4-Rechteck ist wieder ohne Füllung). Damit ist `fill` **noch nicht**
an dem Text-Element, aber die Probe läuft:

- Konva `Text` kennt das Attribut `background` plus `padding`.
- `t.background()` ist **keine** Getter-Funktion — `getAttr('background')`
  ist der Weg zum Auslesen.

Nächster Schritt: `background: '#f8fafc'` + `padding` in
`LageplanElement.vue` (Text-Config), und die Textarea bekommt dieselbe
Füllung, damit sie wie ein Teil des Feldes wirkt, nicht wie ein Fenster
darauf.

### Zwischenstand (25.10.2026, 15:29) — Hintergrund am Text noch nicht sichtbar

Kolya 15:24: „ich sehe keinen hintergrund am text" — richtig, das war
gemessen, nicht nur geglaubt.

Bisher gebaut:
- A4-Füllung `fill: '#f8fafc'` ist wieder raus (Kolya 15:16:
  „nein, nur am text feld soll der helle hintergrund sein!").
- Text-Node hat im Konva-Template `background: '#f8fafc'` und
  `padding: 4`.
- Gemessen: `t.getAttr('background')` liefert `#f8fafc`, der Node liegt
  korrekt im Layer, `visible: true`. **Aber die Pixel im Feld sind dunkel**
  (`[2,6,23]`) — der Hintergrund wird also nicht gerendert, nur gespeichert.

**Offene Frage, noch nicht getrennt:**
1. Vue-Konva übergibt `background` nicht sauber an den Konva-Node
   (Prüfung: `getAttrs()` im echten Template).
2. Konva rendert `background` beim Text anders als erwartet
   (Prüfung: frischer `Konva.Text` in derselben Stage, ohne Vue).

**Noch nicht gebaut:**
- Hintergrund für die Textarea beim Inline-Edit (sonst sieht sie aus
  wie ein Fenster auf dem Textfeld, nicht wie ein Teil davon).
- Breiten-Drag-Faktor für Text (steht weiter oben in dieser Datei).

**Koordinaten für Playwright (gemessen, nicht geraten):**
Canvas 1100×720, BoundingBox `x=65, y=89`. Stage 1100×720, PAGE 891×630,
daraus `panX=(1100-891)/2=104.5`, `panY=(720-630)/2=45`.
Umrechnung Layer→Bildschirm: `screenX = 65 + 104.5 + layerX`,
`screenY = 89 + 45 + layerY`.

### Nächster Schritt
Rotation sauber nachmessen (Handle-Offset 50), Farbfilter aus den
Store-Defaults ableiten. Erst wenn Skalieren **und** Drehen belegt sind:
Kolya melden, dann sichern + committen.

---

## Verifiziertes Konva-Verhalten (Headless-Tests 25.10.2026)

Das ist der Grund, warum alle meine Eigenbau-Versuche scheitern mussten:

1. `Konva.Transformer` feuert beim Ziehen eines Handles **nur** `dragstart`/`dragend`
   auf dem Transformer-Node. **Kein** `transform`, **kein** `transformend` —
   weder am Transformer noch am transformierten Node.
2. Bei `dragend` ist `e.target` der **Transformer**, nicht das Element.
3. Nach `dragend` ist `node.scale()` bereits auf `{x:1,y:1}` zurückgesetzt;
   Konva hat Position und Größe direkt am Node angewendet.
   → Über `scale()` ist nach dem Drag nichts mehr abzulesen.
4. `Group.width()`/`height()` liefern **0** (Groups haben keine eigene Größe).
   Meine Rückrechnung `width() * scaleX()` ergab deshalb 0 bzw. `Infinity`.
5. `listening: false` an einer Parent-Group unterbindet Maus-Events an **allen**
   Kindern, auch wenn die selbst `listening: true` haben.
6. vue-konva `@transformend` am `<v-group>` feuert beim Transformer-Drag nicht.

**Konsequenz:** Es gibt keinen sauberen Weg, nach einem Transformer-Drag die
Skalierung auszulesen. Deshalb funktioniert Kolyas Beispiel — es liest sie
gar nicht aus, sondern lässt die Transformation am Konva-Node stehen.

## Offener Punkt für später (NICHT ohne Freigabe anfassen)
Der Store kennt nach einer Transformation weiterhin die alten Werte
(Breite/Höhe/Rotation). Für den PDF-Export müssen die echten Werte her.
Kolyas Ansage am 25.10.: **PDF-Export ist jetzt nicht das Thema.**
Erst Editor fertig, sichern, committen — dann weitersehen.
Denkbarer Weg: beim Export die Werte aus den Konva-Nodes auslesen
(`node.getClientRect()` / `node.rotation()`), statt während der Bearbeitung
zurückzuschreiben.

---

## Regeln aus diesem Projektverlauf
- Kolyas Beispielcode ist Vorgabe, nicht Inspiration.
- Nichts bauen ohne ausdrückliche Freigabe ("bauen" / "mach das" / "ja").
- Vor jeder Erfolgsmeldung: selbst testen, messen, Screenshots.
- Nicht dieselbe Diagnose wiederholen — wenn eine Erklärung einmal gesagt ist
  und nicht trägt, neue Hypothese suchen statt denselben Satz nochmal schreiben.
