# Architektur und Ausbau zur PV-Anmeldeautomatik

## Aktueller Stand

Eine FastAPI-Anwendung enthält eine Anbieter-Registry und vier getrennte Portaladapter. Der Ordner-/Paketname `nrm-netzanmeldung` bleibt zur Kompatibilität bestehen. Die Multi-Provider-API liegt unter `/api/v1/providers`; der ursprüngliche NRM-Pfad `/api/v1/installations` bleibt erhalten.

- `client.py`: bestehender NRM-Client, SAML-Sitzung und allgemeine Simplifier-Abfrage. Der Upstream-Hostname ist nun eine Instanzeigenschaft; Host-Allowlist und Sitzung bleiben pro Anbieter getrennt.
- `providers.py`: `ENMClient`, `SimplifierAdapter`, `MainzerAdapter`, `ENetzAdapter`. Kein Adapter erhält URLs oder beliebige Backend-Operationen von API-Aufrufern.
- `platform.py`: Anbieter-Metadaten, Konfiguration, Routen und Fähigkeitsprüfung. Nicht unterstützte Kombinationen liefern 501.
- `config.py`: optionale Zugangspaare je Anbieter, gemeinsamer Bearer-Schlüssel.
- `app.py`: Lifecycle, Authentifizierung, Fehlerbehandlung und NRM-Kompatibilitätsroute.

## Datenverträge

Die Portale verwenden unterschiedliche Begriffe und Lebenszyklen:

- Simplifier: Order, OrderProduct, RequestNumber, Produktkatalog und Warenkorb.
- epilot: Opportunity, Order, Contact, Entity-Schemata und versionierte Journeys.
- JSF-Portal: Meldung, Baustelle, Meldungsdetails, Reiter und Formulartransaktion.

Deshalb werden aktuelle Leseantworten unter einem gemeinsamen Umschlag (`provider`, `retrieved_at`, `total`, `items`) geliefert; die Datensätze behalten ihre dokumentierte Anbieterstruktur. Eine Opportunity-ID ist keine NRM-Antragsnummer. Ein Entwurf ist nicht automatisch ein eingereichter Antrag, und mehrere Vorgänge können denselben Anlagenstandort betreffen.

Ein gemeinsames PV-Datenmodell muss ausdrücklich entwickelt und versioniert werden, statt diese Unterschiede stillschweigend gleichzusetzen.

## Sitzungen und Betrieb

Jeder Adapter besitzt eigene Tokens/Cookies und einen Lock. Sessions werden bei Bedarf erstellt, konservativ vor Ablauf erneuert und nach einem 401/403 höchstens einmal neu aufgebaut. Es gibt keine Tokenausgabe an Aufrufer und keine persistente Sessiondatei. Kundendatenantworten erhalten `Cache-Control: no-store`.

Ein Prozess unterstützt ein Zugangspaar pro Anbieter. Mehrere Mandanten pro Anbieter, verschlüsselte Secret-Verwaltung, verteilte Worker, Jobqueue und mandantenbezogene Autorisierung sind noch nicht enthalten. Der aktuelle Bearer-Schlüssel berechtigt zur gesamten konfigurierten Anbietergruppe. Bei einem späteren Mehrkundenbetrieb muss dieses Modell geändert werden.

Der synchrone Betrieb ist für überschaubare Anfragemengen gedacht. Kataloge und mehrseitige Listen werden sequenziell gelesen. Ein plattformweites Gesamtzeitlimit, Rate-Limiting, Ergebnis-Cache und Synchronisationsdatenbank fehlen noch.

## Empfohlene weitere Inkremente

1. **PV-Datenmodell und lokale Validierung**: Standort, Beteiligte, Leistungen/Komponenten, Messkonzept, Betriebsart, ZEREZ, Dokumente; Einheiten und Datenherkunft festlegen.
2. **Feldmapping je Anbieter**: aus echten Formularschritten/Journeys abgeleitet; Pflichtfelder und Bedingungen nachvollziehbar dokumentieren.
3. **Entwürfe**: gezielt anlegen, wiederaufnehmen und lesen; Provider-ID, Entwurfs-ID und persistierten Schritt speichern. Gegen doppelte Anlage absichern.
4. **Dokumente**: nachvollziehbare Zuordnung, Checksummen, Dateitypen/-größen und Wiederholbarkeit.
5. **Vorprüfung**: lokale Validierung sowie Portalvalidierung, ohne Finalisierung.
6. **Absenden als eigene Operation**: konkrete geprüfte Nutzdaten/Unterlagen, Idempotenz, Auditprotokoll und klare Trennung vom Speichern eines Entwurfs.
7. **Statusnachverfolgung**: Änderungen, Korrekturanforderungen und Rückmeldungen; Wiederaufnahme statt neuer Doppelanträge.

Aktuell werden keine Konten geändert, Hinweise quittiert, Anträge gespeichert/angelegt/abgesendet oder Dokumente hochgeladen. Sichtbare Funktionen und ausgelieferte Schreibmethoden sind Analyseergebnisse, keine fertig verifizierten Schreibadapter.

## Verifikationsgrenzen

Erfolgreiche Produktionsantworten belegen nur die konkret ausgeführten Operationen im angegebenen Konto zum Prüfzeitpunkt. Der vollständige dynamische Kontrollfluss aller Portale wurde nicht rekonstruiert. Die statische REA-Auswertung ausgewählter JavaScript-Dateien meldete begrenzte/teilweise Erfassung; daraus wird keine globale Vollständigkeit abgeleitet.

Automatisierte Tests verwenden synthetische Daten. Live-Prüfungen verwenden unabhängige HTTP-Sessions und lesen die vorhandenen Vorgänge. Docker wurde für diese Erweiterung nicht verwendet. Die Containerdateien bleiben für den Zielserver erhalten, sind aber in v0.2 nicht durch einen Containerlauf bestätigt.
