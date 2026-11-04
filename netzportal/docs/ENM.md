# Analyse: Energienetze Mittelrhein (ENM)

Stand: 2. November 2026. Analyse der ausgelieferten Anwendung und authentifizierter HTTP-Abfragen; keine Antragsänderungen.

## Zugang und Technik

Die angegebene Startadresse `https://netzportal.energienetze-mittelrhein.de/` lieferte HTTP 500. Der auf der [offiziellen ENM-Seite](https://www.energienetze-mittelrhein.de/netzanschluesse/netzportal/) verlinkte Einstieg funktioniert:

`https://netzportal.energienetze-mittelrhein.de/appDirect/Kundenmarktplatz/index.html`

Plattform: Simplifier/OpenUI5, gleiche Produktfamilie wie NRM, aber mit direkter Benutzeranmeldung statt NRM-Keycloak-SAML.

Nachgewiesener Ablauf:

1. `POST /genToken/` mit serverseitigem `user`/`pass`.
2. Rückgabe eines Simplifier-Tokens; verbleibende Gültigkeit aus dem Header `remainingTokenLifetime`, falls vorhanden.
3. `POST /client/1.0/executeBO`, Header `SimplifierToken` und `SimplifierApp: Kundenmarktplatz`.
4. `User.getCurrentUser`: Kontoprüfung und E-Mail für die Portalabfrage.
5. `ITIZ_KUN_Kundenapp.listOrdersForUser`: `tabKey=all`, `languageKey=deDE`, tatsächlicher Portalhostname, eigene Konto-E-Mail, `offset=0`.

Die Bibliothek übernimmt keinen NRM-Token für ENM. ENM hat einen separaten HTTP-Client und eine eigene Host-Allowlist. Login und Liste funktionierten unabhängig vom Browser. Im Konto waren zwei Anträge abrufbar. Identifikatoren, Namen und Adressen werden nicht in dieser Dokumentation vervielfältigt.

## Im Konto abrufbarer Produktkatalog

Oberkategorie: **Für Kunden und Partner**. Unterkategorien und Produkte:

1. **Netzanschluss**
   - Anmeldung steuerbare Verbrauchseinrichtung an vorhandene Messeinrichtung
   - Unverbindliche Verfügbarkeitsprüfung
   - Netzanschluss Neu
   - Netzanschlussänderung
   - Netzanschluss Demontage
   - Dacharbeiten
2. **Erzeugungsanlage**
   - Anmeldung einer Erzeugungsanlage
   - Inbetriebsetzung einer Erzeugungsanlage
   - Erhöhte Vergütung bei Volleinspeisern
   - Marktstammdatenregistrierung
   - Anmeldung einer Kleinsterzeugungsanlage und -speicher
   - Bestellung Fernsteuerbarkeit nach EEG §9
   - Rückmeldung Steuerungscheck
3. **Zähler Service**
   - Zählerdemontage
   - Wechsel auf intelligentes Messsystem (Smart Meter)
4. **Eintragung ins Installateurverzeichnis**
   - Neueintragung ins Installateurverzeichnis
5. **Zähleranlage**
   - Zählerantrag
   - Änderung einer Gasanlage
   - Anmeldung steuerbare Verbrauchseinrichtung an vorhandene Messeinrichtung
   - Inbetriebsetzung Zähleranlage abweichender MSB
6. **Installateur Service**
   - Plombenbestellung (Strom)
   - Ausweisverlängerung
   - Wichtige Informationen, Neuigkeiten und Anleitungen

Das ist der über das authentifizierte Katalog-Backend ermittelte Produktumfang, keine Behauptung, sämtliche dynamischen UI-Menüs ausgeführt zu haben. Account-/Dokument-/Schreibabläufe darüber hinaus wurden nicht verifiziert.

## Implementierte Backend-Leseoperationen

| Backend-Methode | Verwendung |
|---|---|
| `User.getCurrentUser` | Anmeldung prüfen |
| `ITIZ_KUN_Kundenapp.listOrdersForUser` | Vorgänge auflisten |
| `ITIZ_KUN_Kundenapp.loadCategoriesForUser` | Oberkategorien |
| `ITIZ_KUN_Kundenapp.loadSubCategoriesForUser` | Unterkategorien |
| `ITIZ_KUN_Kundenapp.loadProductsForUser` | Katalogprodukte |
| `ITIZ_KUN_Kundenapp.loadProductInformation` | Einzelprodukt, Checklisten und Dokumentmetadaten |

In der Live-Abfrage hatte „Anmeldung einer Erzeugungsanlage“ Produkt-ID **250**. Öffentliche Deeplinks nannten teilweise ältere IDs. Die API liest deshalb den aktuellen Katalog; die Anmeldung darf später nicht dauerhaft auf eine historische Produkt-ID festgelegt werden.

Die Liste und das Einzelprodukt 250 wurden über die neue API live abgerufen. Einzel-Antragsdetails sind derzeit nur die Listenzusammenfassung. `loadProductInformation` liefert Katalogmetadaten, nicht alle editierbaren Felddefinitionen eines konkreten PV-Antrags. Die Portalmethoden zum Editieren/Anlegen eines Produkts werden nicht aufgerufen.

## Grenzen und weiterer Ausbau

- Serverlimit/Pagination für die `all`-Antwort bei großen Konten noch offen.
- Keine Erstellung eines Warenkorb-/Antragsobjekts, keine Speichervorgänge.
- Keine Dokumentdownloads/-uploads oder Kommentare.
- Für den Schreibadapter müssen die aktuelle PV-Produktversion, Formularschritte, Feldvalidierung und dokumentierten Pflichtunterlagen separat ermittelt werden.
- Ein lesbares Produkt bedeutet noch nicht, dass alle Schritte ohne weitere Konto-/Installateurberechtigungen ausführbar sind.

Quellnachweise: ausgelieferte ENM-Dateien `Permission.js`, `Globals.js`, `KUN_Kundenapp.js` sowie die oben genannten erfolgreichen Produktionsantworten. Die statische REA-Auswertung untersuchte ausgewählte Dateien; dynamische Erreichbarkeit wurde ausschließlich für die explizit live geprüften Leseoperationen festgestellt.
