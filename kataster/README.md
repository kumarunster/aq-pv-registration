# Interner Kataster-Service

Adresssuche, Katasterbild (standardmäßig 60 × 45 m) und Grundstücksinformationen für Deutschland.
Der Dienst wird ausschließlich über die projektweite Compose-Datei gestartet. Es gibt keine eigene Host-Portfreigabe.

- Container: `na-kataster`, interner HTTP-Port `8765`.
- Netzwerk `na-kataster-private`: nur Backend und Kataster, `internal: true`.
- Netzwerk `na-kataster-egress`: ausgehender Zugriff auf Photon und amtliche Landesdienste; keine veröffentlichten Ports.
- Daten/Cache: persistentes Volume `na-kataster-data` unter `/data`.
- Healthcheck: `GET /health`, im Dockerfile hinterlegt.
- Nicht-Root-Benutzer, schreibgeschütztes Root-Dateisystem, temporäres `/tmp`.

Die vollständige Einbindung und die geschützten Backend-Endpunkte sind in
[docs/LIEGENSCHAFTSKARTE.md](../docs/LIEGENSCHAFTSKARTE.md) beschrieben.

## Lokale Tests ohne Docker

```bash
cd kataster
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -v
```

Die HTTP-Tests öffnen kurz lokale Testports. Externe Geodienste werden dabei nicht abgefragt.

## Landesdaten

Die Adapter liegen unter `kataster/providers.json`; die eigentliche Logik unter `kataster/core.py`.
Die 15 Länder außer Bayern stellen öffentliche Flurstücksdaten bereit. Bayern liefert ohne berechtigten Zugang nur die reduzierte Parzellarkarte und den Grundstücksstatus `zugang_erforderlich`.
Nicht geführte Fluren bleiben `null`. Datenlücken und mehrdeutige Adresspunkte werden gekennzeichnet bzw. zurückgewiesen.
WFS-Kandidaten werden anhand der Flurstücksgeometrie einschließlich Innenringen geprüft. Kreisbögen werden mit maximal 1 mm Sehnenfehler angenähert.
Die Zuordnung eines Adresspunkts erfasst keine komplette grundbuchrechtliche Eigentumseinheit und ersetzt keinen förmlichen amtlichen Katasterauszug.

Die Kartendarstellung hängt vom jeweiligen Landesdienst ab. Bei entsprechendem Aufruf sind ausdrücklich gekennzeichnete Ersatzdaten/-darstellungen möglich. Quellen, Abrufnachweise und Original-Lizenzangaben der Dienste bleiben im Ergebnis-JSON erhalten.
Adressdaten werden an den eingestellten Photon-Dienst übermittelt, in Hessen gegebenenfalls zusätzlich an den amtlichen Suchdienst. Andere Dienste erhalten Koordinaten.
Für regelmäßigen Betrieb oder mehrere Benutzer einen eigenen/vertraglich gesicherten Photon-Dienst über `KATASTER_PHOTON_URL` konfigurieren; der öffentliche [Demoserver](https://github.com/komoot/photon#demo-server) erlaubt nur angemessene Abrufmengen und garantiert keine Verfügbarkeit.
