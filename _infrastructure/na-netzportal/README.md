# na-netzportal – lokale Servicekonfiguration und Daten

- `.env`: private Portal-Zugangsdaten; aus `.env.example` erstellen, Rechte 0600.
- `volume/`: persistentes SQLite-Journal und lokale Anlagen-JSONs. Bind-Mount nach `/data`; nicht in Git einchecken.
- Quellcode und Dockerfile bleiben unter `../../netzportal`.

Vor dem ersten Start auf dem Linux-Docker-Host, aus `_infrastructure`:

```bash
cp na-netzportal/.env.example na-netzportal/.env
chmod 600 na-netzportal/.env
sudo install -d -o 10001 -g 10001 -m 700 na-netzportal/volume
```

Zugangspaare in `.env` konfigurieren. Den gemeinsamen `NETZPORTAL_API_KEY` in `_infrastructure/.env` setzen; Compose übergibt ihn an Backend und Service. Der Service läuft als UID/GID 10001 und benötigt Schreibrechte auf `volume`.

Bei bestehenden Installationen das bisherige benannte Volume vor der Umstellung sichern und dessen Inhalt bei gestopptem Service vollständig nach `volume/` übernehmen. Besitzer auf 10001:10001 setzen und Dateirechte erhalten. Das Journal nicht leer ersetzen: Es verhindert doppelte Anlegeversuche. Der Compose-Wechsel migriert vorhandene Daten nicht automatisch.
