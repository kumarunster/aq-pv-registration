# How-To — Amelanq Netz-Anmeldung

Kurze Anleitungen für die wichtigsten Operationen.
Alle Befehle laufen aus diesem Ordner (`_infrastructure/`).

---

## Dev-Stack starten / stoppen

**IMMER mit dem Dev-Override starten:**

```bash
cd /home/moltbot/clawd/projects/amelanq-netz-anmeldung/_infrastructure

# Dev: docker-compose.dev.yml ueberschreibt die Standard-compose
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d"
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml ps"
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml down"
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml logs -f na-backend"
```

**Warum der Override im Dev noetig ist:** Die Standard-`docker-compose.yml` ist
auf **Produktion** ausgelegt — `na-nginx` haengt am externen Netz `proxy`
(dem nginx-proxy + acme-companion) und hat **kein** Host-Port-Mapping. Ohne
diesen Proxy schlaegt `docker compose up` lokal fehl (`network proxy ... not found`).

Der Override `docker-compose.dev.yml`:
- gibt `na-nginx` ein Host-Port-Mapping (`${PUBLIC_HTTP_PORT}:80`)
- ersetzt das externe `proxy`-Netz durch ein lokales Bridge-Netz (`na-proxy-dev`)
- die `VIRTUAL_HOST` / `LETSENCRYPT_*`-Variablen bleiben leer (kein Proxy da)

Die App ist danach lokal unter `http://localhost:${PUBLIC_HTTP_PORT}` (Port 8092) erreichbar.

**Produktion (auf dem Prod-Host mit nginx-proxy):**
```bash
sg docker -c "docker compose up -d"      # nur die Standard-compose
```
Hier uebernimmt der externe nginx-proxy die Veroeffentlichung samt TLS; das
externe Netz `proxy` und die Variablen `VIRTUAL_HOST`, `LETSENCRYPT_HOST`,
`LETSENCRYPT_EMAIL` in der `.env` muessen gesetzt sein.

**Docker-Rechte:** User `moltbot` ist in der `docker`-Gruppe, Tool-Shells laden
sie aber nicht immer. Deshalb `sg docker -c "..."` verwenden. **Niemals `sudo docker`.**

---

## 1.) Admin-User anlegen

Admin-Identity in Kratos anlegen (E-Mail + Passwort + Name, Rolle `admin`).
Das Skript prüft: Container läuft, Passwort mindestens 8 Zeichen.
Existiert die E-Mail schon → das Passwort der bestehenden Identity wird
aktualisiert (Schema/Rolle wird nicht gewechselt).

**Ausführung (aus `_infrastructure/`):**

```bash
./scripts/create_identity.sh \
  admin@amelanq.com \
  'DeinPasswortMin8' \
  "Kolya Raitsev" \
  admin
```

Danach kann man sich unter `/admin/login` mit E-Mail + Passwort einloggen.

**Alternative ohne Skript:**
```bash
KRATOS_PASSWORD='***' ./scripts/create_identity.sh \
  admin@amelanq.com 'DeinPasswortMin8' "Kolya Raitsev" admin
```

**Wichtige Hinweise:**

- Das Skript legt **nur** die Kratos-Identity + das Passwort an.
- Es macht **keinen** Oathkeeper-Grant, **keine** Session, **keinen** Login.
- Nach dem Anlegen: Login unter `http://localhost:8092/admin/login`.
- Der Admin-Schutz am Backend (`/api/admin/`) prüft die Kratos-Schema-Id:
  nur Identities mit Schema `admin` kommen durch, sonst 403.

---

## 2.) Installer-User anlegen

Installer-Identity in Kratos anlegen (E-Mail + Passwort + Name + **Firma**,
Rolle `installer`). Der Firmenname ist Pflichtfeld, weil das Kratos-Schema
`installer` das Trait `company` verlangt.

**Ausführung (aus `_infrastructure/`):**

```bash
./scripts/create_identity.sh \
  installateur@amelanq.com \
  'DeinPasswortMin8' \
  "Hans Meier" \
  installer \
  "Meier Solar GmbH"
```

Danach kann sich der Installer unter `/installer/login` einloggen und sieht
nur seine eigenen Kunden/Anlagen (`/api/installer/` filtert auf
`created_by = <Identity-ID>`).

**Wichtige Hinweise:**

- 5. Argument = Firmenname, ohne das bricht das Skript ab.
- Existiert die E-Mail schon → Passwort-Update (Schema bleibt).
- Der Installer hat keinen Zugriff auf `/api/admin/` (403).

---

## 3.) Backend / Frontend nach `git pull` neu bauen

```bash
# Beides neu bauen
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build na-backend na-frontend"

# Nur Backend (z. B. nach Python-Änderungen)
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build na-backend"

# Nur Frontend (z. B. nach Vue-Änderungen)
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d --build na-frontend"
```

**Prüfung nach dem Rebuild:**
```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8092/healthz
```

**Wenn nur nginx-Config geändert wurde** (`nginx/nginx.conf`):
```bash
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d na-nginx"
```

**Wenn nur eine Env-Variablen-Änderung war** (`.env`):
```bash
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml up -d"
```

---

## 4.) Vor dem Prod-Deployment prüfen

1. `.env` auf dem Prod-Host: `VIRTUAL_HOST`, `LETSENCRYPT_HOST`,
   `LETSENCRYPT_EMAIL` mit dem echten Domain-Wert setzen.
2. Externes Docker-Netz `proxy` muss auf dem Prod-Host existieren
   (nginx-proxy + acme-companion).
3. Secrets setzen: `MONGO_PASSWORD`, `KRATOS_DB_PASSWORD`,
   `KRATOS_COOKIE_SECRET` / `KRATOS_CIPHER_SECRET` (je **32 Zeichen hex**),
   `MINIO_PASSWORD`, `NETZPORTAL_API_KEY`.
4. `APP_ENV=production` in der `.env`.
5. Nur die Standard-Compose starten (ohne Dev-Override):
   ```bash
   sg docker -c "docker compose up -d"
   ```
6. Port-Regel prüfen — nur der Proxy soll öffentlich sein:
   ```bash
   sg docker -c "docker compose ps --format '{{.Name}} {{.Ports}}'" | grep -E "0\.0\.0\.0|:::"
   # Erwartet: NUR der nginx-proxy (kein na-*)
   ```
7. TLS: acme-companion erzeugt das Zertifikat für `LETSENCRYPT_HOST`.
   Danach unter `https://<domain>` testen.

---

## Rollen & Rechte

| Rolle | Kratos-Schema | Login | API | Sicht |
|---|---|---|---|---|
| Admin | `admin` | `/admin/login` | `/api/admin/` | alle Firmen + Kunden + Anlagen |
| Installer | `installer` | `/installer/login` | `/api/installer/` | nur eigene Kunden/Anlagen |
| Kunde | – | – (kein Login) | – | öffentlich: `/` + Registrierung |

- Oathkeeper prüft für `/api/admin/` und `/api/installer/` eine gültige
  Kratos-Session und setzt die Identity-Header (`X-Kratos-Identity-*`).
- Das Backend prüft zusätzlich die Schema-Id: Admin-Routen nur bei Schema
  `admin` (sonst 403), Installer-Routen filtern auf `created_by`.

---

## Häufige Fehler

| Symptom | Ursache | Fix |
|---|---|---|
| `network proxy ... not found` bei `docker compose up` | Dev ohne Override | Immer mit `-f docker-compose.yml -f docker-compose.dev.yml` starten |
| Kratos startet nicht, `length must be <= 32` | Secret zu lang (64 hex = 32 Byte) | `KRATOS_CIPHER_SECRET` mit `openssl rand -hex 16` (32 Zeichen) setzen |
| Admin-Login klappt, aber API 403 | Identity hat Schema `installer` statt `admin` | Identity mit Schema `admin` anlegen (5. Arg. `admin`) |
| Installer sieht keine Kunden | `created_by` weicht ab | Kunden/Anlagen über `/api/installer/` anlegen, nicht über Admin |
| Frontend zeigt alten Build | Browser-Cache | Hard-Reload (iPhone: Lade-Button halten → "Laden und Aktualisieren") |
| Backend nach Rebuild nicht gesund | `na-backend` hängt | `docker logs na-backend` prüfen, neu starten |

---

## Ports (Pflichtregel)

**NUR `na-nginx` hat im Dev ein Host-Port-Mapping.** In Produktion kein
Host-Port — der externe nginx-proxy erreicht `na-nginx` über das Netz `proxy`.

```bash
sg docker -c "docker compose -f docker-compose.yml -f docker-compose.dev.yml ps --format '{{.Name}} {{.Ports}}'" | grep -E "0\.0\.0\.0|:::"
# Erwartet: NUR die Zeile mit na-nginx
```
