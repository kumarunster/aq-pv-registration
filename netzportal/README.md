# PV-Netzanmeldung – Multi-Provider API

**Version 0.4.0 · Stand: 4. November 2026**

Dieses Projekt ist die technische Grundlage für eine betreiberübergreifende Automatisierung von PV-Netzanmeldungen. Es bindet **NRM**, **Energienetze Mittelrhein (ENM)**, **Mainzer Netze** und **e-netz Südhessen** über getrennte Adapter an eine gemeinsame HTTP-API an.

Die Anmeldung erfolgt serverseitig mit den konfigurierten Zugangsdaten. API-Aufrufer benötigen nur den separaten Bearer-Schlüssel. Ein offener Browser, Codex oder ein manueller Export von Cookies ist für den laufenden Betrieb nicht erforderlich. Die Adapter verwenden die tatsächlich untersuchten Anmelde- und Abfrageprotokolle der jeweiligen Portale.

**Aktueller Umfang:** automatischer Login, Vorgangslisten, ausgewählte Lesefunktionen und eine erste API für Entwürfe. NRM/ENM: leerer Produktentwurf im Warenkorb; e-netz: initiale Strommeldung mit Standort; Mainzer: ausschließlich lokale JSON-Vorbereitung. Technische PV-Daten werden derzeit nur lokal gespeichert. **Kein endgültiges Absenden ist implementiert.** Portal-Schreibvorgänge sind synthetisch getestet, aber ohne reale Anlagendaten noch nicht live verifiziert. Die Integration ist inoffiziell.

Das JSON-Format, alle neuen Endpunkte und die genauen Grenzen stehen in **[Entwurfs-API](docs/DRAFTS.md)**.

## Automatische Netzbetreibersuche

`POST /api/v1/network-operators/resolve` ermittelt über die öffentliche VNBdigital-Adresssuche den Niederspannungsnetzbetreiber. Der Endpunkt verlangt den Service-Bearer. Er überträgt ausschließlich Straße, Hausnummer, PLZ und Ort; keine Betreiber-/Komponentendaten. Details und verifizierte Live-Beispiele: [VNBdigital](docs/VNBDIGITAL.md).

In der integrierten Anwendung erscheint die Netzanmeldung im eigenen Tab „Netzanmeldung“ der PV-Anlagenmaske, nur für Admins ab Status „In Prüfung“ (einschließlich „Angemeldet“ und „Abgeschlossen“). Die Betreiberauswahl erfolgt automatisch; Mehrdeutigkeiten oder nicht angebundene Betreiber sperren den Start.

## Verifizierter Funktionsumfang

| Anbieter-ID | Anmeldung | Implementierte Funktionen | Live-Ergebnis im verwendeten Konto |
|---|---|---|---|
| `nrm` | Keycloak/SAML → Simplifier | Bestehende Installationsliste, gemeinsame Vorgangsliste, Zusammenfassung eines Vorgangs, Sitzungsprüfung | 3 Anträge |
| `enm` | Simplifier-Login | Vorgangsliste, Zusammenfassung, Produktkatalog mit Kategorien, Produktmetadaten/Checklisten, Sitzungsprüfung | 2 Anträge; 6 Produkt-Unterkategorien |
| `mainzer` | Amazon Cognito SRP | Anfragenliste mit Pagination, vollständige lesbare Anfrageattribute, Entity-Suche/-Details, Schemata, konfigurierte Portalseiten und Schnellaktionen, Sitzungsprüfung | 1 Anfrage; 9 Entity-Schemata; 18 konfigurierte Seiten; 3 Schnellaktionen |
| `enetz` | Java-Formularlogin/Session-Cookie | Meldungsstatus mit Pagination, sichtbarer Detail-Reiter, Menü, Hinweise/Hinweisdetails, Aufgaben-Erstseite und Optionen vor „Anlegen“ | 2 Meldungen einschließlich 1 Entwurf |

Bei e-netz Südhessen waren zunächst ungelesene Hinweise vorgeschaltet. Nachdem der Kontoinhaber sie selbst gelesen und bestätigt hatte, wurden Statusliste, Details, Aufgaben und Einstiegsformular erneut erfolgreich geprüft. Neue Hinweise können den Zugriff später wieder sperren; dann liefert die API einen ausdrücklichen Fehler statt einer leeren Liste.

Die ausführlichen Analysen stehen unter:

- [ENM](docs/ENM.md)
- [Mainzer Netze](docs/MAINZER.md)
- [e-netz Südhessen](docs/ENETZ.md)
- [Architektur und nächste Ausbauschritte](docs/ARCHITECTURE.md)
- [Historische NRM-Einzelanbindung v0.1](docs/NRM-v0.1.md)

## Installation ohne Docker

Voraussetzungen: Python **3.11+**, Internetzugang zu den Portalen und gültige Zugangsdaten. Verifiziert wurde mit Python 3.14. Docker wird hier nicht benötigt und wurde für diese Erweiterung nicht gestartet.

Im Projektordner:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
python -m nrm_api
```

Alternativ startet der installierte Befehl `nrm-api` denselben Dienst.

Standardadresse: `http://127.0.0.1:8080`.

- [Swagger UI](http://127.0.0.1:8080/docs)
- [ReDoc](http://127.0.0.1:8080/redoc)
- [OpenAPI JSON](http://127.0.0.1:8080/openapi.json)
- [Prozessstatus](http://127.0.0.1:8080/health)

Die statische API-Beschreibung liegt außerdem als `openapi.json` im Projektordner.

## Zugangsdaten und Konfiguration

In dieser Repository-Kopie sind keine Zugangsdaten enthalten. `.env.example` nach `.env` kopieren, mindestens ein Zugangspaar konfigurieren und die Datei mit `chmod 600 .env` schützen. Keine Secrets veröffentlichen.

Für einen neuen Installationsort `.env.example` nach `.env` kopieren und ausfüllen. Um Passwörter mit `$`, Leerzeichen oder `#` in Compose/dotenv unverändert zu übernehmen, einfache Anführungszeichen verwenden: `ENM_PASSWORD='beispiel$passwort#'`.

| Variable | Bedeutung |
|---|---|
| `NRM_USERNAME`, `NRM_PASSWORD` | NRM-Zugang |
| `ENM_USERNAME`, `ENM_PASSWORD` | ENM-Zugang |
| `MAINZER_USERNAME`, `MAINZER_PASSWORD` | Mainzer-Netze-Zugang |
| `ENETZ_USERNAME`, `ENETZ_PASSWORD` | e-netz-Südhessen-Zugang |
| `NETZPORTAL_API_KEY` | Gemeinsamer API-Bearer-Schlüssel, mindestens 32 Zeichen; identischer Name in Backend, Service und Compose |
| `PV_DATA_DIR` | Persistentes Verzeichnis für SQLite-Entwurfsjournal; Standard `.state` im Projekt, Docker `/data` |
| `NRM_HOST` | Listenadresse, Standard `127.0.0.1` |
| `NRM_PORT` | Port, Standard `8080` |
| `NRM_TIMEOUT_SECONDS` | Timeout je HTTP-Austausch, Standard 30 Sekunden, erlaubt 1–120 |

Einzelne Anbieter können unkonfiguriert bleiben. Mindestens ein vollständiges Zugangspaar und der API-Schlüssel sind erforderlich. Bei einem Anbieter müssen Benutzername und Passwort gemeinsam gesetzt oder beide leer sein. Prozess-Umgebungsvariablen haben Vorrang vor `.env`.

Zugangsdatenänderungen erfordern einen Prozessneustart. Die erste autorisierte Abfrage meldet sich bei Bedarf automatisch an. `/health` prüft nur den API-Prozess und löst keine Portal-Anmeldung aus.

Die Anbieter arbeiten mit getrennten HTTP-Clients, Cookies, Tokens und Sperren. Tokens bleiben im Arbeitsspeicher. Ablauf bzw. HTTP 401/403 führen zu höchstens einer erneuten Anmeldung mit Wiederholung der Leseabfrage. MFA, Passwortwechsel und andere zusätzliche Authentifizierungsschritte werden nicht umgangen.

## API verwenden

Alle `/api/v1/...`-Endpunkte verlangen:

```http
Authorization: Bearer YOUR_API_KEY
```

In Swagger UI unter **Authorize** nur den Schlüsselwert eintragen. Die Dokumentationsseiten und `/health` sind ohne Bearer erreichbar; Kundendaten nicht.

Beispiel, wenn `NETZPORTAL_API_KEY` bereits im Terminal exportiert ist:

```bash
curl --fail-with-body \
  -H "Authorization: Bearer ${NETZPORTAL_API_KEY}" \
  http://127.0.0.1:8080/api/v1/providers/enm/applications
```

Die vom Dienst geladene `.env` exportiert keine Variablen in die Shell. Dieses Python-Beispiel liest denselben lokalen Schlüssel, ohne ihn auszugeben:

```python
import httpx
from nrm_api.config import Settings

settings = Settings.from_env()
headers = {"Authorization": f"Bearer {settings.api_key}"}
base = "http://127.0.0.1:8080/api/v1"

with httpx.Client(headers=headers, timeout=240) as client:
    for provider in ("nrm", "enm", "mainzer", "enetz"):
        response = client.get(f"{base}/providers/{provider}/applications")
        response.raise_for_status()
        print(provider, response.json()["total"])
```

Eine kalte Abfrage kann mehrere Login-HTTP-Austausche benötigen; `NRM_TIMEOUT_SECONDS` gilt je Austausch, nicht als Gesamtlimit. Ein großer Katalog oder viele Seiten können mehr als 240 Sekunden benötigen. Ein globales Operationslimit ist noch nicht implementiert.

### Gemeinsame Endpunkte

| Methode | Pfad | Zweck |
|---|---|---|
| GET | `/api/v1/providers` | Anbieter, Konfiguration, implementierte Fähigkeiten und Grenzen; kein Live-Verfügbarkeitstest |
| POST | `/api/v1/providers/{provider}/session` | Zugangsdaten anmelden bzw. Sitzung prüfen; kein Portal-Token in der Antwort |
| GET | `/api/v1/providers/{provider}/applications` | Vollständige derzeit abfragbare Vorgangsliste gemäß Anbieter-Semantik |
| GET | `/api/v1/providers/{provider}/applications/{id}` | Anbieterabhängige Details bzw. Zusammenfassung |

Gültige Anbieterwerte: `nrm`, `enm`, `mainzer`, `enetz`.

Sitzungsantwort, synthetisch:

```json
{
  "provider": "enetz",
  "authenticated": true,
  "action_required": false,
  "reason": null
}
```

Listen verwenden folgenden gemeinsamen Umschlag:

```json
{
  "provider": "enm",
  "retrieved_at": "2026-11-02T12:00:00Z",
  "total": 1,
  "items": [{"id": "example", "status": "In Bearbeitung"}]
}
```

Die Elemente sind bewusst **anbieterabhängig**; das Beispiel zeigt nur das Umschlagformat. Ein noch nicht spezifiziertes gemeinsames PV-Anlagenmodell wird nicht vorgetäuscht.

- **NRM/ENM:** `id`, `application_number`, `order_id`, `order_number`, `order_product_number`, `product_id`, `product_name`, `request_type`, `request_type_name`, `status_code`, `status`, `submitted_on`, `location`, `applicant`, `connection_taker`, `division`, `is_open`, `is_closed`, `is_assigned`, `unread_comments_count`. IDs sind Strings, `submitted_on` ISO-Datum oder null. Adressen bleiben als Portaltext erhalten. Einzelabfragen liefern derzeit diese Zusammenfassung, nicht die technischen Formularwerte.
- **Mainzer:** `_id`, `_title`, `_schema`, `status`, `_created_at`, `_updated_at` sowie verfügbare Anfrage-/Adressfelder. Anfragen sind `opportunity`-Entities. Einzelabfragen liefern lesbare Entity-Attribute einschließlich technischer Angaben, soweit sie in diesem Konto verfügbar sind.
- **e-netz:** `id`, `status`, `type`, `connection_object_number`, `location`, `city`, `submitted_on_display`, `division`, `is_draft`, `detail_path`. Die Liste enthält auch Entwürfe. Einzeldetails bestehen aus `summary`, `fields`, `scope=currently_rendered_tab`, `complete=false`. Andere Reiter und abhängige Formularbereiche sind darin nicht enthalten.

Eine „Installation“ bzw. ein Vorgang entspricht hier einem Portal-Antrag und **keinem deduplizierten physischen Standort**. Mehrere Anträge am selben Standort bleiben getrennt. Die Anzahl ist kein Anlagenbestand.

### Anbieterbezogene Endpunkte

| Anbieter | Methode/Pfad hinter `/api/v1/providers/{provider}` | Funktion |
|---|---|---|
| ENM | GET `/catalog` | Kategorien, Unterkategorien und Produktmetadaten |
| ENM | GET `/products/{product_id}` | Produktinformationen, Beschreibung, Checklisten und Dokumentmetadaten; kein editierbares Formular |
| Mainzer | GET `/menus` | Konfigurierte Portalseiten, inklusive System-/öffentlicher Seiten; keine Zusage, dass jede Seite im Menü sichtbar ist |
| Mainzer | GET `/workflows` | Schnellaktionen/Journey-IDs und Sichtbarkeitsregeln; keine Ausführung |
| Mainzer | GET `/schemas` | Lesbare Entity-Schemata und technische Attributdefinitionen |
| Mainzer | GET `/entities/{schema}?offset=0&limit=100` | Paginierte Entity-Suche; maximal 100 Einträge je Seite |
| Mainzer | GET `/entities/{schema}/{entity_id}` | Lesbare Details einer Entity |
| e-netz | GET `/menus` | Authentifizierte Navigationslinks |
| e-netz | GET `/notices` | Erste Hinweisseite, ausdrücklich `complete=false`; keine Lesebestätigung |
| e-netz | GET `/notices/{notice_id}` | Inhalt eines Hinweises, ohne Bestätigung |
| e-netz | GET `/tasks` | Erste Aufgabenseite, ausdrücklich `complete=false` |
| e-netz | GET `/registration-options` | Felder/Spartenauswahl vor „Anlegen“, ohne einen Antrag anzulegen |

Mainzer-Schemata sind auf die nachgewiesenen Werte `account`, `contact`, `file`, `opportunity`, `order`, `portal_user`, `contract`, `meter`, `meter_counter` begrenzt. Upstream-Berechtigungen des Kontos gelten weiterhin. Es gibt keinen beliebigen Proxy für URLs oder Backend-Methoden.

Der bisherige Endpunkt **`GET /api/v1/installations`** bleibt unverändert als NRM-Kompatibilitätspfad erhalten. Er liefert `source`, `retrieved_at`, `total`, `installations` statt des neuen `items`-Formats und kontaktiert ausschließlich NRM.

### Pagination und Vollständigkeit

- Mainzer-Anfragen werden bis `has_more=false` gesammelt. Doppelte IDs, wechselnde Gesamtzahlen, nicht fortschreitende Ergebnisse oder mehr als 100 Seiten führen zu Fehlern statt stiller Kürzung. Die gezielte Entity-Suche liefert jeweils eine Seite mit Upstream-Pagination.
- e-netz-Meldungsstatus wird über die nachgewiesene JSF-Weiter-Schaltfläche gesammelt, bis die letzte Seite erreicht ist. Formularzustand und Filter bleiben erhalten; keine Zeilenaktion wird mitgesendet. Die Traversierung ist auf 100 Seiten begrenzt und prüft wiederholte Seiten/IDs. Im Live-Konto war nur eine Seite vorhanden; die Mehrseitenlogik ist zusätzlich synthetisch getestet.
- NRM/ENM liefern die Portalantwort für `tabKey=all`, `offset=0`. Ein serverseitiger Höchstumfang ist nicht etabliert; bei NRM veränderten getestete Offsets die Liste nicht. Größere Konten erfordern eine gesonderte Prüfung der Upstream-Grenzen.
- e-netz-Hinweise/Aufgaben und e-netz-Formulardetails sind ausdrücklich Teilausschnitte.

### Fehler

| HTTP | Bedeutung |
|---|---|
| 401 | API-Schlüssel fehlt oder ist ungültig; keine Portal-Abfrage |
| 404 | Datensatz nicht im Konto zugänglich |
| 409 | Portal verlangt eine Handlung des Kontoinhabers, z. B. neue Hinweise bestätigen |
| 422 | Ungültige Anbieter-ID, Parameter oder Seitengröße |
| 501 | Diese Operation ist für den gewählten Anbieter noch nicht implementiert |
| 502 | Portal-Anmeldung/Sitzung fehlgeschlagen oder unerwartetes Datenformat |
| 503 | Anbieter nicht konfiguriert, Netzwerk-/Serverausfall oder Rate-Limit |
| 504 | Upstream-Timeout |

Beispiel:

```json
{
  "error": {
    "code": "portal_action_required",
    "message": "e-netz requires the account holder to read and acknowledge outstanding portal notices.",
    "provider": "enetz"
  }
}
```

Die alte NRM-Route behält ihre bisherigen `nrm_*`-Fehlercodes. Bei anderen Providern werden entsprechende Login-/Sitzungsfehler als `portal_*` ausgegeben. Interne HTTP-Antworten und Authentifizierungsdaten werden nicht in Fehlermeldungen kopiert.

## Docker/Compose in diesem Repository

Der Service ist als `na-netzportal` in `../_infrastructure/docker-compose.yml` eingebunden. Er veröffentlicht keinen Host-Port und nutzt den Bind-Mount `_infrastructure/na-netzportal/volume:/data`. Der Backend-Relay ist unter `/api/admin/registration` erreichbar. Konfiguration und Ablauf: [Integration](../docs/AUTO-REGISTRY.md).

Die Live-Ergebnisse unten stammen aus der vorausgehenden Einzelservice-Analyse vom 2. November 2026; es wurde in dieser Repository-Integration kein Portal-Schreibvorgang ausgelöst.

## Tests und Live-Prüfung

```bash
python -m pytest -q
```

Derzeit **57 automatisierte Tests** mit synthetischen Daten. Sie prüfen unter anderem:

- Bestehenden NRM-SAML-Ablauf und Rückwärtskompatibilität.
- ENM-Anmeldung, anbietergebundene Host-/Token-Verwendung und Sitzungswiederverwendung.
- Mainzer-SRP-Austausch, unveränderten Tenant, kein Klartext-Passwort im SRP-Request, Pagination und Dublettenfehler.
- e-netz-Formularlogin, vorgeschaltete Hinweise, fehlende implizite Bestätigung und JSF-Seitenwechsel ohne Löschaktion.
- Entwurfs-Idempotenz über Neustarts, keine blinde Schreibwiederholung, keine Warenkorbersetzung, ausschließlich erlaubte Anlegeaktion sowie lokale JSONs für alle vier Anbieter.
- Bearer-Schutz, fehlende Provider-Konfiguration, nicht implementierte Operationen, Timeouts und Entfernen von Secrets/signierten URLs.

Live wurden am 2. November 2026 die drei neuen Logins sowie die jeweils beschriebenen Listen/Detail-/Metadaten-Endpunkte über FastAPI getestet. Die alte NRM-Liste lieferte weiterhin drei Anträge. Nach manueller Bestätigung der e-netz-Hinweise wurden die nun erreichbaren Endpunkte nochmals live geprüft. Die Livesitzungen wurden unabhängig von den Browsercookies aufgebaut. Es wurden keine Formulare gespeichert, Meldungen angelegt, Dokumente hochgeladen oder Anträge abgesendet.

## Struktur

```text
nrm-netzanmeldung/
├── README.md
├── pyproject.toml
├── openapi.json
├── Dockerfile
├── compose.yaml
├── .env.example
├── .env                     # lokal, privat, nicht verteilen
├── nrm_api/
│   ├── app.py               # Lifecycle, Bearer, alter NRM-Endpunkt
│   ├── platform.py          # Provider-Registry und gemeinsame Routen
│   ├── drafts.py            # Entwurfsinitialisierung, lokale JSONs, Idempotenzjournal
│   ├── providers.py         # ENM-, Mainzer- und e-netz-Adapter
│   ├── client.py            # bestehender NRM-SAML-/Simplifier-Client
│   ├── config.py
│   ├── errors.py
│   ├── models.py
│   └── __main__.py
├── tests/
│   ├── test_api.py
│   └── test_providers.py
└── docs/
    ├── ENM.md
    ├── MAINZER.md
    ├── ENETZ.md
    ├── ARCHITECTURE.md
    └── NRM-v0.1.md
```

## Was noch fehlt für eine automatische PV-Anmeldung

Ein gemeinsames PV-Datenmodell mit Betreiber, Standort, Anlagenkomponenten, Messkonzept und Dokumenten; betreiberspezifische Feldabbildungen und Validierung; vollständige Formularbefüllung und Wiederaufnahme bestehender Portalentwürfe; Dateiübertragung; sowie ein gesonderter, kontrollierter finaler Absendevorgang. Diese Schreibabläufe müssen jeweils am tatsächlichen Formular bzw. Workflow untersucht und verifiziert werden. Ein sichtbarer Menüpunkt oder ein Attributschema allein beweist nicht, dass die entsprechende Aktion bereits automatisiert werden kann.
