# Analyse: Mainzer Netze

Stand: 2. November 2026. Ausgangspunkt: `https://installateure.mainzer-netze.de/login`.

## Plattform und Anmeldung

Das Portal ist eine epilot-Anwendung mit konfigurierbaren Seiten und Amazon-Cognito-Anmeldung. Die ausgelieferte Anwendung nutzt **USER_SRP_AUTH**. Der Adapter bildet diesen Ablauf nach; ein Browser ist nicht erforderlich.

1. Öffentliche Tenant-Konfiguration: `GET https://customer-portal-api.sls.epilot.io/v2/portal/public/config?domain=installateure.mainzer-netze.de`.
2. Prüfung der tatsächlich untersuchten User-Pool-/Client-ID, um eine unerwartete Tenant-Änderung vor dem Login zu erkennen.
3. Cognito `InitiateAuth` mit `USER_SRP_AUTH` und öffentlichem SRP-Wert.
4. `RespondToAuthChallenge` für `PASSWORD_VERIFIER`, einschließlich `Session`, falls zurückgegeben.
5. Verwendung des zurückgegebenen **IdToken**, wie im Portal-Client beobachtet, für die epilot-Portal-API.
6. `GET /v2/portal/user`: Prüfung, dass das Konto die konfigurierte E-Mail enthält.

SRP-Berechnungen stammen aus `pycognito`; Netzwerkzugriffe und Timeouts bleiben im eigenen HTTP-Client. Weitere Challenges wie MFA oder Passwortwechsel sind nicht automatisiert. Secrets und Tokens werden nicht an API-Aufrufer zurückgegeben. Es werden weder administrative AWS-Zugangsdaten noch ein Administratorzugang zu epilot benötigt.

Referenzen: [AWS InitiateAuth](https://docs.aws.amazon.com/cognito-user-identity-pools/latest/APIReference/API_InitiateAuth.html), [pycognito](https://github.com/NabuCasa/pycognito), [epilot Portal API](https://docs.epilot.io/docs/sdk/clients/customer-portal/).

## Nachgewiesene Portalbereiche

Das Konto lieferte 18 konfigurierte Seiten. Darunter sind öffentliche/systeminterne Seiten und Detailseiten; diese Liste ist kein Beweis für 18 gleichzeitig sichtbare Menüeinträge.

| Bereich | Seitenschlüssel |
|---|---|
| Anmeldung | `login` |
| Registrierung | `register` |
| Wartendes Konto | `pending-account` |
| Aktivierung | `activation` |
| Übersicht | `dashboard` |
| Passwort vergessen | `forgot-password` |
| Erfolgsseite | `success` |
| Neue E-Mail | `new-email` |
| Passwortänderung | `change` |
| Mein Konto | `my-account` |
| Wartung | `maintenance` |
| E-Mail-Bestätigung | `confirm-email` |
| Konzessionsmanagement | `konzessionsmanagement` |
| Dokumente | `documents` |
| Anfragen | `opportunities` |
| Support | `support` |
| Kontakt | `contact` |
| Kontobenutzer | `account-users` |

Konfigurierte Schnellaktionen:

- **Erzeugungs- und/oder Verbrauchsanlage (inkl. Stromzähler) anmelden**: Journey-Einstieg.
- **Sonstige Anliegen Stromzähler**: interner Support-Link, z. B. für Demontagen und Messkonzeptänderungen.
- **Gastkonzession für zusätzliche Sparte beantragen**: Journey-Einstieg mit konto-/zielgruppenabhängigen Sichtbarkeitsregeln.

`GET /workflows` liefert die aktuellen Ziel-/Journey-IDs und die Sichtbarkeitskonfiguration. Er führt keine Journey aus und sendet keine kontobezogenen vorausgefüllten Parameter an externe Formulare.

## Datenmodell: Anfragen sind Opportunities

Die Übersicht verwendet `opportunity`, nicht `order`. Das Live-Konto enthielt eine Opportunity und null Orders. Eine reine Order-Abfrage würde hier irrtümlich eine leere Antragsliste suggerieren.

Die öffentliche API `/applications` verwendet deshalb `POST /v2/portal/entity:search` mit `slug=opportunity`, expliziten Feldern und `from`/`size`. Sie sammelt alle Seiten entsprechend der Upstream-Pagination.

Einzelheiten werden mit `POST /v2/portal/entity:get`, `slug=opportunity`, `entity_id`, `hydrate=true` gelesen. Die geprüfte Anfrage lieferte 107 lesbare Attribute. Darunter:

- Standort-/Lieferadresse und Beteiligte.
- Art der Anlage, Netzebene, vorhandener Stromzähler.
- Messkonzept und bestehende Erzeugungsanlagen.
- PV-Gesamtmodulleistung, Wechselrichterleistung.
- Modulhersteller/-typ und Leistungen.
- Wechselrichterhersteller/-typ und ZEREZ-Angabe.
- Speicherhersteller/-typ, Kapazität, Leistungsdaten und Speicherwechselrichter/ZEREZ.
- Angaben zu Ladeeinrichtungen und Steuerbarkeit.
- Zahlungsanspruch und beschreibende Angaben.
- Dateireferenzen und Prozess-/Statusattribute.

Dies sind lesbare Attribute einer bestehenden Anfrage. Daraus allein folgt weder, dass sie alle beschreibbar sind, noch dass es sich um eine vollständige Pflichtfeldliste für neue Anträge handelt. Bedingte Journey-Schritte können zusätzliche Daten erfordern.

## Implementierte Endpunkte

- Sitzungsanmeldung/-prüfung.
- Anfragenliste und Einzelanfrage.
- Konfigurierte Seiten/Schnellaktionen.
- Schemaabfrage über `GET /v2/portal/schemas`.
- Paginierte Entity-Suche und Detailabfrage.

Nachgewiesene Schemawerte: `account`, `contact`, `file`, `opportunity`, `order`, `portal_user`, `contract`, `meter`, `meter_counter`. Die Suchschnittstelle ist auf diese Werte begrenzt; das Portal kontrolliert zusätzlich die Kontoberechtigungen. Ein `file`-Datensatz ist noch kein Dateidownload. Signierte Download-URLs werden nicht weitergereicht.

## Grenzen und nächster Schritt

Ein zukünftiger Schreibadapter muss die PV-Journey mit ihren Versionen, Abhängigkeiten, Dateiübertragungen und Abschlussaktionen untersuchen. Die ausgelieferten API-Definitionen enthalten auch Schreiboperationen; ihre bloße Existenz ist keine Verifikation. Deshalb gibt es in dieser Version weder eine allgemeine PATCH-Weiterleitung noch eine vermeintlich fertige „PV anmelden“-Schreibfunktion.

Statische REA-Auswertung: ausgewählte veröffentlichte JavaScript-Dateien. Sie war wegen dynamischer Beziehungen und begrenzter semantischer Erfassung teilweise unvollständig. Die hier als implementiert beschriebenen Funktionen wurden zusätzlich erfolgreich mit einer eigenständigen HTTP-Anmeldung und über FastAPI geprüft.
