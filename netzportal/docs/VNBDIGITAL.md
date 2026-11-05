# VNBdigital – Adresssuche und automatische Betreiberzuordnung

Untersucht am 4. November 2026: [VNBdigital](https://www.vnbdigital.de/). Die Integration verwendet die öffentlich von der Webseite aufgerufene GraphQL-Schnittstelle; eine zugesicherte öffentliche Entwickler-API oder dauerhafte Verfügbarkeit wurde nicht festgestellt.

## Beobachtetes Protokoll

Die ausgelieferte Startseite setzt `GATEWAY_GRAPHQL_URI` auf `/gateway/graphql`. Der untersuchte JavaScript-Build `/assets/index-CPTA31pm.js` enthält zwei relevante Leseabfragen:

```graphql
query ($searchTerm: String!) {
  vnb_search(searchTerm: $searchTerm) {
    _id title subtitle url type
  }
}
```

Adresse als `Straße Hausnummer, PLZ Ort`. Ein präziser Treffer hat `type=LOCATION` und eine URL wie `/overview?coordinates=50.110931,8.688347&searchType=LOCATION`. Die Koordinaten stehen hier in Reihenfolge **Breitengrad,Längengrad**.

```graphql
query ($coordinates: String, $filter: vnb_FilterInput) {
  vnb_coordinates(coordinates: $coordinates) {
    vnbs(filter: $filter) { _id name types voltageTypes }
  }
}
```

Der Filter `{"voltageTypes":["Niederspannung"]}` ist entscheidend: In den Live-Proben lieferte dieselbe Koordinatensuche ohne Filter eine leere Betreiberliste. Es wird Strom/Niederspannung gesucht, nicht anhand eines Firmennamens der Betreiber geraten. Anlagen mit Anschluss in Mittel-/Hochspannung benötigen einen späteren eigenen Ablauf.

Live ausschließlich mit öffentlichen Beispieladressen geprüft:

- `Kurt-Schumacher-Straße 8, 60311 Frankfurt am Main` → `50.110931,8.688347` → NRM Netzdienste Rhein-Main GmbH, ID `7376`.
- `Rheinallee 41, 55118 Mainz` → `50.010517,8.264109` → Mainzer Netze GmbH, ID `405`.
- Die Firmensuche bestätigte zusätzlich Energienetze Mittelrhein GmbH & Co. KG, ID `350`, sowie e-netz Südhessen AG, ID `134`.

Die Zuordnung zu Portaladaptern verwendet ausschließlich diese verifizierten IDs, keine unscharfe Namenssuche. Änderung oder unbekannte ID sperren die Registrierung, statt ein falsches Portal auszuwählen.

Die statische Untersuchung wurde durch gezielte Lese-HTTP-Abfragen bestätigt. Die automatische REA-Vollanalyse des großen Bundles erreichte ihr Zeitlimit; sie ist kein Vollständigkeitsbeleg. Beobachtet wurde der beschriebene Suchpfad, nicht jede Funktion der Webseite. Es wurde keine Anlage an ein Netzbetreiberportal übertragen.

## Service-Endpunkt

`POST /api/v1/network-operators/resolve`, geschützt mit `Authorization: Bearer <NETZPORTAL_API_KEY>`:

```json
{
  "street": "Kurt-Schumacher-Straße",
  "house_number": "8",
  "postal_code": "60311",
  "city": "Frankfurt am Main"
}
```

Antwort enthält `source`, `queried_at`, `address`, `voltage_level`, `status`, `operator`, `provider`, gegebenenfalls `location` und `candidates`.

Status:

- `resolved`: genau ein genauer Adresstreffer und genau ein angebundener Niederspannungsbetreiber.
- `unsupported`: genauer Treffer, aber dieser Betreiber besitzt noch keinen Adapter. Die Anlagenmaske warnt mit dem Betreibernamen und dem Hinweis, dass der Netzbetreiber zuerst im System aufgenommen werden muss; der Start bleibt gesperrt.
- `not_found`: kein genauer Hausadress-/Betreibertreffer.
- `ambiguous_address` / `ambiguous_operator`: Mehrdeutigkeit, keine automatische Auswahl.
- HTTP 503 `vnbdigital_unavailable`: Timeout, HTTP-/GraphQL-Fehler oder unerwartete Antwort. Der Backend-Relay liefert bei Servicefehlern einen bereinigten 502-Fehler.

Straße inklusive Hausnummer und PLZ müssen genau passen; der eingegebene Ortsname muss im zurückgegebenen Ort enthalten sein. Groß-/Kleinschreibung und `ß/ss` werden normalisiert. Es gibt bewusst keine Fallback-Auswahl nur nach PLZ oder Straße. Andere Schreibweisen, Stadtteil- oder Ortsaliasnamen können deshalb eine Adresskorrektur erfordern. Externe Treffer-URLs werden nicht aufgerufen; nur Koordinaten aus relativen `/overview`-URLs im deutschen Bereich werden ausgewertet.

## Anlagenablauf und Daten

Der Browser ruft nur den Admin-Relay auf. Der Relay ermittelt aus dem Datenbankstand die Adresse der **gewählten Anlage**. Bei `address_from_customer=true` verwendet er die Kundenadresse; andernfalls die eigene Anlagenadresse. An VNBdigital werden nur die Adressdaten übertragen. Der öffentliche GraphQL-Zugriff benötigt weder Netzbetreiberpasswörter noch Cookies oder einen Service-Bearer; diese werden nicht an VNBdigital gesendet.

Vorschau, Prüfung und Start ermitteln den Betreiber jeweils erneut. Der Prüf-Request enthält `expected_operator_id` aus der Vorschau, aber keinen frei wählbaren Provider. Datenhash, Betreiber-ID, Status und Admin-Freigabe werden vor dem Schreiben geprüft. Das Suchergebnis wird am anlagenbezogenen Registrierungsvorgang protokolliert; keine Änderung der gespeicherten Kundenadresse erfolgt automatisch. Ungeklärte Treffer werden nicht persistiert und nicht geraten.

Das UI zeigt den ermittelten Namen, die Quellseite und die gefundene Adresse. Bei ungespeicherten Änderungen ist die Netzanmeldung deaktiviert; nach Speichern und erneutem Öffnen wird der aktuelle Stand verwendet. Installateure sehen keinen Startbereich. Der Server lehnt die Aktionen unabhängig von der Oberfläche ohne Admin-Schema oder bei Status unterhalb „In Prüfung“ ab.

Die Registrierung bleibt auf die bisherigen Entwurfsfunktionen begrenzt; insbesondere unterstützt Mainzer weiterhin ausschließlich lokale Vorbereitung. Kein endgültiges Absenden.
