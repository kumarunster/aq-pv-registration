# Entwurfs-API – Version 0.3

Diese Erweiterung bereitet PV-Netzanmeldungen vor. Sie enthält keinen Endpunkt zum endgültigen Absenden. Zugangsdaten bleiben serverseitig; alle folgenden Endpunkte verlangen den vorhandenen Bearer-Schlüssel.

## Umfang je Portal

| Anbieter | `target=portal` | Noch nicht umgesetzt |
|---|---|---|
| NRM / ENM | PV-Produkt als leeren Warenkorbentwurf initialisieren; bestehender Warenkorb blockiert die Aktion | Standort, Betreiber, technische Formulare, Dokumente, Wiederaufnahme |
| e-netz Südhessen | Strom / Bezugs-/Liefermeldung mit Standort und optionaler Bemerkung über „Anlegen“ initialisieren | Betreiber, Komponenten, nachfolgende Reiter, Dokumente, Wiederaufnahme |
| Mainzer Netze | HTTP 409 `portal_draft_unavailable` | Remote-Entwurf: Die untersuchte PV-Journey bietet keine verifizierte Fortschrittsspeicherung |
| Alle vier | `target=local`: JSON ausschließlich in dieser API speichern | Kein Portalvorgang entsteht durch lokale Speicherung |

Die Anlegefunktionen sind mit simulierten Antworten getestet. **Es wurde kein neuer Portalentwurf für Testzwecke angelegt; die schreibenden Abläufe sind noch nicht live verifiziert.** Login, Lesefunktionen und Formular-/Workflowanalyse wurden live untersucht. Das ist noch keine vollständige automatische PV-Anmeldung.

Bei Mainzer ist in der untersuchten privaten PV-Journey `settings.savingProgress` nicht aktiviert; der Abruf gespeicherter Benutzersitzungen lieferte 404. Eine Submission oder Entity-Erstellung wäre kein nachgewiesener Entwurfsersatz und wird deshalb nicht ausgeführt.

## Endpunkte

Basis: `/api/v1/providers/{provider}`, Anbieter `nrm`, `enm`, `mainzer`, `enetz`.

| Methode | Pfad | Wirkung |
|---|---|---|
| GET | `/drafts/prepare?product_id=...` | Anmeldung und Prüfung des Einstiegs; keine persistente Antragserstellung. e-netz setzt im temporären JSF-Formular Strom; Mainzer meldet die Einschränkung. |
| POST | `/drafts` | Entwurf initialisieren oder JSON lokal speichern; `Idempotency-Key` erforderlich |
| GET | `/drafts/{draft_id}` | Lokal gespeicherte Erstellungsquittung; bei lokalen Entwürfen auch JSON. Kein erneuter Portalabruf. |

`prepare` meldet unter anderem Umfang und `write_live_verified=false`. NRM/ENM benötigen eine aktuell gültige PV-Produkt-ID. ENM stellt diese über `/catalog` bereit; eine Produkt-ID ist keine Vorgangs-ID. Ohne Produkt-ID kann der Warenkorb geprüft werden, aber keine Erstellung freigegeben werden.

## Dein JSON

Für die erste Übergabe eignet sich lokale Speicherung. Das Beispiel ist synthetisch und wurde nicht an ein Portal übertragen:

```json
{
  "target": "local",
  "site": {
    "postal_code": "12345",
    "city": "Musterstadt",
    "street": "Musterstraße",
    "house_number": "1",
    "district": ""
  },
  "note": "Vorbereitung PV-Anmeldung",
  "plant": {
    "operator": {"name": "Beispiel Betreiber"},
    "pv_power_kwp": 10.0,
    "inverters": [],
    "storage": []
  }
}
```

`plant` ist derzeit ein freies JSON-Objekt zur lokalen Vorbereitung, noch kein validiertes technisches PV-Schema. Die darin gezeigten Schlüssel sind Vorschläge. Die Abbildung deiner tatsächlichen Daten auf die Portalformulare folgt im nächsten Schritt. Keine Passwörter oder Portal-Tokens in Anlagendaten aufnehmen.

Für einen **leeren NRM-/ENM-Portalentwurf** lautet der Body ausschließlich:

```json
{"target": "portal", "product_id": 250}
```

250 ist eine bei ENM untersuchte Produkt-ID; vor Nutzung anhand des aktuellen Katalogs prüfen. Standort, Bemerkung und nichtleere `plant`-Daten werden in diesem Modus mit 422 abgelehnt, damit nichts unbemerkt verloren geht.

Für **e-netz**: `target=portal`, `site` wie oben, optional `note`; `product_id` weglassen und `plant` leer lassen. Das erzeugt nur den Einstieg der Strommeldung. Es befüllt noch keine vollständige PV-Anlage.

Unbekannte oberste Felder, etwa `submit`, werden abgelehnt. Standort verlangt fünfstellige PLZ, Ort, Straße und Hausnummer. `target` ist standardmäßig `portal`; für ausschließlich lokale Vorbereitung ausdrücklich `local` angeben.

## Aufruf und Wiederholungen

```http
POST /api/v1/providers/enetz/drafts
Authorization: Bearer YOUR_API_KEY
Idempotency-Key: pv-projekt-2026-001
Content-Type: application/json
```

Der Schlüssel muss 8–128 Zeichen aus Buchstaben, Ziffern, `_ . : -` enthalten. Pro Konto, Anbieter und Schlüssel wird höchstens ein Schreibversuch gestartet. Derselbe Schlüssel mit demselben Body liefert nach Erfolg dieselbe Quittung; ein anderer Body liefert 409. Das Journal bleibt über Prozessneustarts erhalten.

Nach einem Timeout oder unklaren Ergebnis wird die Schreibaktion **nicht automatisch wiederholt**. Weitere Aufrufe mit demselben Schlüssel liefern 409 `draft_outcome_uncertain`. Dann den Portalzustand kontrollieren; nicht einfach einen neuen Schlüssel verwenden. Auch ein Absturz zwischen Journalreservierung und Portalaufruf führt vorsorglich zu diesem Zustand. Ein manueller Abgleich und die Freigabe blockierter Schlüssel sind noch nicht implementiert.

Erfolgsantwort: HTTP 201, `storage=portal|local`, `status=draft`, `submitted=false`, `creation_verification=read_back|local_commit`, `fields_saved` und `limitations`. Portalentwürfe werden nach dem Anlegen zurückgelesen. Eine Wiederholung liefert ebenfalls 201 mit derselben ID. Das Feld `submitted=false` beschreibt ausschließlich den hier ausgeführten Erstellungsablauf; die Quittung ist kein aktueller Portalstatus.

## Speicherung und Betrieb

`PV_DATA_DIR` legt das Verzeichnis fest, Standard `.state` im Projekt. SQLite-Datei: `drafts.sqlite3`, Dateirechte 0600. Sie enthält Idempotenzdaten, Quittungen und bei lokalen Entwürfen die vollständigen Anlagendaten im Klartext. Zugangsdaten werden dort nicht gespeichert. Verzeichnis und Backups entsprechend schützen.

Journal nicht löschen oder zwischen Instanzen trennen: Sonst geht der Schutz gegen doppelte Schreibversuche verloren. Mehrere Prozesse auf demselben Host müssen dieselbe SQLite-Datei verwenden; verteilte Hosts mit getrennten Journalen sind nicht unterstützt. Gleichzeitige externe Portalbearbeitung kann durch die API-Sperren nicht ausgeschlossen werden.

Die integrierte Compose-Datei unter `_infrastructure` verwendet `/data` und den Bind-Mount `_infrastructure/na-netzportal/volume:/data`. Docker wurde lokal nicht gestartet. Ohne Docker genügt der bisherige Python-Start. Es gibt derzeit keine Änderungs-, Lösch-, Upload- oder Absende-Endpunkte für Entwürfe.
