# UI/UX-Analyse — Kunde mit 200 Anlagen (10.10.2026)

Testkunde: **Baugenossenschaft Langen** (cust_id `6ae46b5bd540b93ec05677d0`),
200 PV-Anlagen, 33% ohne Status, 67% mit Status.

## Gemessene Zahlen (Headless Chromium, 1280×900)

| Fläche | Wert | Problem |
|---|---|---|
| Kunden-Karte in der Liste | **8918 px** (≈9× Viewport) | 200 Anlage-Chips inline — Karte scrollt endlos, andere Kunden unter ihr nicht sichtbar |
| Kundenliste (Suche „Baugenossenschaft") | 12 s bis render | Akzeptabel, aber träge |
| Formular (Formular oben) | **3499 px** | ~4× Viewport, scrollen zum Speichern-Button nötig |
| Formular-DOM | **1238 Nodes** (aktiv: 1 Tab) | OK dank v-if auf PlantForm |
| Formular-Render | 8 s | träge, aber ok |
| Sprung zu Anlage 50 (Tab-Klick) | 1.62 s | akzeptabel |
| Tab-Leiste | 200 Buttons | **nicht scrollbar** — ohne Horizontal-Scroll weg, kein Indikator |

## Befund (Priorität)

1. **Tab-Leiste ist bei >5 Anlagen unbrauchbar.** 200 Buttons, kein
   Horizontal-Scroll, kein Indikator. → Sticky Tab-Leiste mit
   `overflow-x-auto`, Auto-Scroll zum aktiven Tab, ggf. Suche/
   Sprungfeld („Anlage #…") + Nummerierung nach Adresse
   (Haus 1…200).
2. **Kunden-Karte zeigt alle Anlagen inline (8918 px).** Bei
   200 Anlagen muss die Liste nur eine Zusammenfassung zeigen:
   „200 Anlagen · 134 abgeschlossen · 42 angemeldet · 24 in Prüfung ·
   0 ohne Status" + „Details" → Kunden-Detailseite (getrennt von
   der Liste). Sonst ist die Liste bei großen Kunden unbrauchbar.
3. **Formular-Layout:** Formular 3499 px, Speichern-Button erst am
   Ende. → Speichern/Abbrechen sticky unter dem Tab-Header, Anlage-
   Details kompakter (Accordion je Sektion: Adresse, PV-Details,
   Wechselrichter, Speicher, Checkliste, Lageplan, Notizen).
4. **Performance:** 8 s Formular-Render + 12 s Liste. Für 200+
   Anlagen: Lazy-Rendering (nur sichtbarer Tab + Nachbar-Tabs) und
   ggf. Server-seitiges Plant-Summary (status-Zählung) statt
   kompletter 200-Anlage-Payloads in der Liste.

## Vorschlag (nächster Schritt)

- **P1:** Sticky Tab-Leiste mit Horizontal-Scroll + „Anlage #"-Sprung.
- **P2:** Kunden-Karten-Zusammenfassung (Status-Zählung) + Detailseite.
- **P3:** Sticky Action-Bar (Speichern/Abbrechen) + Accordions im
  Anlage-Tab.

Screenshots: `media/browser/ux200_form_top.png`, `media/browser/ux200_tab50.png`
