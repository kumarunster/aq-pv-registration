> Historische Dokumentation der NRM-Einzelanbindung (v0.1). Für die aktuelle Multi-Provider-Version gilt die README im Projektstamm.

# NRM Netzanmeldung API

Version **0.1.0** — first increment: list installations/applications from an NRM Netzportal account.

This is a standalone Python HTTP service that signs in to [NRM Netzportal](https://netzportal.nrm-netzdienste.de/appDirect/Kundenmarktplatz/index.html) with server-side credentials and returns the entries shown under **Meine NRM → Bestellungen → Alle** as structured JSON.

API consumers do not need to open the website, sign in interactively, or supply an NRM password. They call the service with its own bearer API key. The service handles NRM's SAML sign-in and session renewal automatically using HTTP requests. It does not depend on Codex, an open browser, browser cookies, Playwright, or manual session exports.

This is an **unofficial integration**, based on the portal's observed first-party requests. It is not an NRM-supported public API. This first version is read-only.

## What “installation” means

In this version, an installation is **one application/order-product in Bestellungen**, identified by its NRM order-product ID. It is not a deduplicated physical site or a list of commissioned PV systems. Several applications can concern the same property. The API preserves them as separate entries.

The endpoint returns all application types accessible to the configured account through the upstream `all` tab, including open and closed applications. Unsubmitted cart drafts are not included. It does not yet retrieve module, inverter, battery, document contents, or full application-form details.

## Quick start

Requirements: Python **3.11 or newer**, internet access to both NRM hosts, and a valid NRM account that can use password-based SAML sign-in. Development verification used Python 3.14.

Run commands from the `nrm-netzanmeldung` folder:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[test]'
```

A private `.env` was prepared locally with the credentials supplied for this task and a generated bearer key. It is excluded from Git and has file permissions `0600`. Do not overwrite that file with `.env.example` if you want to keep the existing configuration.

For a fresh installation elsewhere:

```bash
cp .env.example .env
chmod 600 .env
python -c 'import secrets; print(secrets.token_urlsafe(32))'
```

Edit `.env`, set the NRM username/password, and paste the generated key into `NETZPORTAL_API_KEY`. For Compose, single-quote passwords containing `$`, spaces, or `#` so they are treated literally (for example, `NRM_PASSWORD='literal$password'`). Never commit the real file or put it in a shared archive.

Start the service:

```bash
python -m nrm_api
# Equivalent after installation:
# nrm-api
```

The default address is `http://127.0.0.1:8080`.

- Interactive API documentation: [Swagger UI](http://127.0.0.1:8080/docs)
- Alternative documentation: [ReDoc](http://127.0.0.1:8080/redoc)
- Live schema: [OpenAPI JSON](http://127.0.0.1:8080/openapi.json)
- Process health: [health](http://127.0.0.1:8080/health)

In Swagger UI, click **Authorize** and enter only the value of `NETZPORTAL_API_KEY`.

The server fails at startup if the username/password are missing, the bearer key is shorter than 32 characters, or the configured timeout is outside its supported range. NRM credentials are checked lazily on the first authorized installations request, rather than by the health endpoint.

## Docker image and Docker Compose

The included `Dockerfile` packages the API as an independent Linux container using the official `python:3.14-slim` image. Python dependencies are installed from `pyproject.toml`. Runtime credentials are supplied when the container starts. The build context is allowlisted by `.dockerignore`; `.env`, tests, caches, documentation, and local environment files are excluded from the image.

Docker Engine/Desktop must be running and Docker Compose v2 must be installed. Run these commands from this folder. Keep the existing private `.env` or prepare one as described in Quick start.

```bash
# Validate without displaying the resolved credentials:
docker compose config --quiet

# Build the local image and start the service:
docker compose up --build -d

# Inspect status and startup logs:
docker compose ps
docker compose logs --tail=50 nrm-netzanmeldung

# Check process liveness:
curl --fail http://127.0.0.1:8080/health

# Stop and remove the container/network (keeps the image and .env):
docker compose down
```

If the Python development server is already using host port 8080, stop it first or change the Compose port mapping to `127.0.0.1:8081:8080`. The last port remains 8080 inside the container. API URLs on the host then use port 8081.

The supplied service description is:

```yaml
services:
  nrm-netzanmeldung:
    image: nrm-netzanmeldung:0.1.0
    build:
      context: .
      dockerfile: Dockerfile
    env_file:
      - .env
    environment:
      NRM_HOST: 0.0.0.0
      NRM_PORT: "8080"
    ports:
      - "127.0.0.1:8080:8080"
    restart: unless-stopped
    init: true
    read_only: true
    cap_drop:
      - ALL
    security_opt:
      - no-new-privileges:true
    stop_grace_period: 30s
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
```

`NRM_HOST` must be `0.0.0.0` **inside** the container so Docker can forward traffic to it. Compose overrides the local `.env` host/port values accordingly. Host publication remains restricted to `127.0.0.1`. [Docker's service reference](https://docs.docker.com/reference/compose-file/services/) describes these Compose settings.

The container runs as UID/GID **10001**, with a read-only root filesystem and no persistent volumes. Sessions stay in memory and are recreated automatically after a restart. The image healthcheck calls `/health` every 30 seconds; it checks process liveness only and does not verify NRM login. An `unhealthy` status alone does not trigger Docker's restart policy; `unless-stopped` handles process exits and daemon restarts.

After changing credentials or the API key, recreate the container to load the new environment:

```bash
docker compose up -d --force-recreate
```

### Add it to an existing Compose stack

If the API folder is a subdirectory of another Compose project, use the following service in that project's Compose file. Adjust both paths to match your layout:

```yaml
services:
  nrm-netzanmeldung:
    image: nrm-netzanmeldung:0.1.0
    build:
      context: ./nrm-netzanmeldung
    env_file:
      - ./nrm-netzanmeldung/.env
    environment:
      NRM_HOST: 0.0.0.0
      NRM_PORT: "8080"
    expose:
      - "8080"
    restart: unless-stopped
    init: true
    read_only: true
    cap_drop: [ALL]
    security_opt: ["no-new-privileges:true"]
```

Other services on the same Compose network can call `http://nrm-netzanmeldung:8080/api/v1/installations` with the bearer key. `expose` does not publish a host port. Add a `ports` mapping if host access is needed, or route through the stack's existing HTTPS reverse proxy. A dependent service can use `depends_on: {nrm-netzanmeldung: {condition: service_healthy}}` to wait for process readiness. It still needs to handle upstream NRM errors when making requests.

### Build or run the image directly

```bash
docker build -t nrm-netzanmeldung:0.1.0 .
docker run --detach --name nrm-netzanmeldung \
  --env-file .env \
  --env NRM_HOST=0.0.0.0 --env NRM_PORT=8080 \
  --publish 127.0.0.1:8080:8080 \
  --read-only --cap-drop ALL --security-opt no-new-privileges:true \
  --restart unless-stopped --init \
  nrm-netzanmeldung:0.1.0
```

For direct `docker run`, use a separate env file with unquoted `KEY=value` lines: Docker Engine's `--env-file` retains literal quote characters, whereas Compose's dotenv parser removes surrounding quotes. The existing supplied password does not require quoting. No image has been pushed to a registry; `nrm-netzanmeldung:0.1.0` is a local image tag. To deploy on another machine, build there or tag/push it to your own registry, then use `image:` with that registry reference. Never bake credentials into the image or pass them as build arguments.

## Calling the endpoint

### `GET /api/v1/installations`

Fetch a fresh list from NRM using the server's configured account. The service reuses its authentication session, not previously fetched installation data. No request body or query parameters are needed.

Header:

```http
Authorization: Bearer YOUR_NETZPORTAL_API_KEY
```

Example with curl (the environment variable is your service key, not the NRM password):

```bash
curl --fail-with-body \
  -H "Authorization: Bearer ${NETZPORTAL_API_KEY}" \
  http://127.0.0.1:8080/api/v1/installations
```

The `.env` file is loaded by the service; it does not automatically export variables into your terminal. This Python example loads the local configuration and calls the running service without printing the key:

```python
import httpx
from nrm_api.config import Settings

settings = Settings.from_env()
response = httpx.get(
    "http://127.0.0.1:8080/api/v1/installations",
    headers={"Authorization": f"Bearer {settings.api_key}"},
    timeout=240,
)
response.raise_for_status()
for installation in response.json()["installations"]:
    print(installation["application_number"], installation["status"])
```

A cold request involves several upstream HTTP exchanges. `NRM_TIMEOUT_SECONDS` applies to each request, not to the entire login-and-list operation; API callers should allow sufficient overall time.

### Example response

The following record is **synthetic** and contains no real customer data:

```json
{
  "source": "NRM Netzportal / Meine NRM / Bestellungen / Alle",
  "retrieved_at": "2026-11-02T12:00:00Z",
  "total": 1,
  "installations": [
    {
      "id": "12345",
      "application_number": "12345",
      "order_id": "10000",
      "order_number": "10000",
      "order_product_number": "10001",
      "product_id": "56",
      "product_name": "Anmeldung Photovoltaikanlagen nach VDE 4105",
      "request_type": "Netzeinspeisung",
      "request_type_name": "Netzeinspeisung",
      "status_code": "Zur_Korrektur",
      "status": "Zur Korrektur",
      "submitted_on": "2026-10-06",
      "location": "12345 Beispielstadt\nMusterstraße 5",
      "applicant": "Erika Beispiel\n12345 Beispielstadt Andere Straße 12",
      "connection_taker": "",
      "division": "Strom",
      "is_open": true,
      "is_closed": false,
      "is_assigned": false,
      "unread_comments_count": 1
    }
  ]
}
```

| Field | Meaning |
|---|---|
| `id` | Unique application/order-product ID, serialized as a string |
| `application_number` | NRM `requestNumber`, the Antragsnummer displayed in the portal |
| `order_id`, `order_number` | Parent order identifiers; these can differ from the application number |
| `order_product_number` | Separate NRM order-product number |
| `product_id`, `product_name` | Product/catalog identity and label, including version text supplied by NRM |
| `request_type`, `request_type_name` | Upstream request type code and name |
| `status_code` | Raw upstream status code |
| `status` | Upstream status name with underscores replaced by spaces; no invented status translation |
| `submitted_on` | Portal order date normalized from `DD.MM.YYYY` to ISO `YYYY-MM-DD`; null when blank |
| `location` | Installation address, preserving upstream line breaks |
| `applicant` | Applicant name and postal address as supplied by NRM; can differ from the installation address |
| `connection_taker` | Upstream Anschlussnehmer text, empty if absent |
| `division` | Utility text, such as Strom |
| `is_open`, `is_closed`, `is_assigned` | Upstream application flags |
| `unread_comments_count` | Number of unread comments; reading this list does not mark comments as read |
| `retrieved_at` | UTC timestamp after the successful retrieval |
| `total` | Number of application entries returned, not number of unique sites |

Addresses stay as upstream text to avoid guessing how streets, house numbers, and applicant names should be split. Empty textual fields are returned as empty strings. The service preserves NRM's ordering.

### Other endpoints

| Method / path | Authentication | Purpose |
|---|---|---|
| `GET /health` | None | Service liveness/version; does not check NRM |
| `GET /docs` | None | Interactive API documentation |
| `GET /redoc` | None | Alternative schema documentation |
| `GET /openapi.json` | None | Machine-readable API contract |

An exported contract is also included as `openapi.json` in this folder. It contains no credentials or customer records.

### Errors

| HTTP status | Meaning |
|---|---|
| `401` | Missing or invalid service bearer key; NRM is not contacted |
| `502` | NRM sign-in failed, interaction is required, a renewed session was rejected, or the upstream response format changed |
| `503` | NRM/network unavailable, NRM rate-limited the request, or NRM returned a server error |
| `504` | An individual upstream request timed out |

Upstream errors use a stable envelope:

```json
{
  "error": {
    "code": "nrm_authentication_failed",
    "message": "NRM sign-in failed or requires an interactive step. Check the server credentials."
  }
}
```

Error codes include `upstream_error`, `nrm_authentication_failed`, `nrm_session_expired`, `nrm_unavailable`, and `nrm_timeout`. API-key errors use FastAPI's `{"detail": "A valid API bearer key is required."}` format and include `WWW-Authenticate: Bearer`.

Raw upstream bodies, passwords, tokens, assertions, and customer data are not included in error messages. Missing/malformed order collections fail instead of being misreported as a successful empty list.

## Configuration

| Variable | Required/default | Meaning |
|---|---|---|
| `NRM_USERNAME` | Required | NRM account username |
| `NRM_PASSWORD` | Required | Existing NRM password |
| `NETZPORTAL_API_KEY` | Required, minimum 32 characters | Separate secret used by callers of this API |
| `NRM_HOST` | `127.0.0.1` | Listen address when started via `nrm-api` / `python -m nrm_api` |
| `NRM_PORT` | `8080` | Listen port |
| `NRM_TIMEOUT_SECONDS` | `30`, allowed 1–120 | Timeout per upstream HTTP exchange |

Process environment variables override `.env`. Changing credentials or the API key requires restarting the service. The hosts and upstream operation names are fixed in the adapter to keep credential routing and scope explicit.

## How it works

1. On the first authenticated request, GET the portal's `/authentication/saml/Keycloak?appName=Kundenmarktplatz&mode=default` entry point.
2. Follow the normal redirect to NRM's Keycloak login host, preserving the temporary cookies and hidden form fields.
3. Submit the configured username/password only to the expected Keycloak authentication path.
4. Submit the returned SAML assertion only to the expected NRM portal callback.
5. Parse the Simplifier token and expiry from the callback text, without executing JavaScript.
6. Use `User.getCurrentUser` to verify the authenticated username and obtain its email.
7. Call `ITIZ_KUN_Kundenapp.listOrdersForUser` through `/client/1.0/executeBO`, with `tabKey=all`, `languageKey=deDE`, the portal hostname, the authenticated account email, and `offset=0`.
8. Map the returned `allOrderProducts` array into the public response schema.

NRM's session token and cookies stay in process memory. The service renews the session before its reported expiry, with a 60-second margin. An upstream 401/403 invalidates the session and triggers at most one reauthentication/retry. A process restart simply signs in again on demand. No NRM session tokens are written to disk.

A lock serializes upstream operations and prevents concurrent login races within one worker. This is intended initially for modest automation traffic and one account. Multiple workers each own their own session; no distributed session store or rate limiter is included.

Only two upstream read operations are implemented: `User.getCurrentUser` and `ITIZ_KUN_Kundenapp.listOrdersForUser`. There is no generic proxy endpoint and no application-edit, submit, cancel, comment-post, document-upload, or cart endpoint.

## Deployment and unattended operation

The implementation runs independently and requires no user action for the currently observed password-based login flow. A running process with the configured secrets can serve scheduled jobs or another application.

By default the service is **local only**. This task does not publish a public endpoint, provision a host, or configure automatic startup after reboot. For a persistent deployment, install it on a server, supply secrets through that server's secret management, and supervise `nrm-api` with the platform's process manager. Put a TLS reverse proxy in front of it for access beyond the local machine and retain bearer authentication. Avoid logging authorization headers and customer response bodies. Keep `.env` out of source control, container build contexts, and shared bundles.

For direct ASGI deployment, the app import is `nrm_api.app:app`; Uvicorn command-line flags control its host/port in that mode:

```bash
uvicorn nrm_api.app:app --host 127.0.0.1 --port 8080 --no-access-log
```

The service uses normal TLS validation and restricts the login redirect/form destinations to the two observed NRM HTTPS origins. It does not bypass MFA, CAPTCHA, password-expiry, or consent screens. If NRM introduces a required interactive step, the endpoint returns an authentication error; unattended operation would then require a supported authentication solution or an adapter update.

## Coverage and known limitations

- Verified against the production portal on **2 November 2026** with the supplied account. The live endpoint returned the same three application numbers observed in the portal: **55816, 55753, 55751**.
- This is an application inventory for one configured account. No cross-account/administrator access or multi-tenant routing is implemented.
- The adapter uses the portal's observed `all` response. Testing offsets 1 and 3 returned the same current list as offset 0; an upstream pagination contract or maximum result size was not established. This version does not claim to enumerate an undisclosed server cap. Large-account pagination must be verified before relying on this for a much larger account.
- No individual form details, certificates, documents, comments content, cart drafts, or writes are included in version 0.1.0.
- German labels are retained; dates and IDs are normalized as documented.
- Portal backend methods, SAML callback format, or permissions can change. Schema/authentication failures are explicit rather than silently falling back to browser scraping.
- Per-request timeouts exist; there is no global operation deadline, automatic polling, result cache, background synchronization, or persistence database.
- API docs and liveness are public to callers who can reach the service. Customer inventory requires the bearer key. Rotate the key and restart if it is disclosed.

## Verification

Run offline automated tests:

```bash
python -m pytest -q
```

The suite covers the full simulated HTTP SAML exchange, credential destination restrictions, read-operation allowlisting, all-entry mapping including closed applications, address distinction, dates, session reuse/expiry, bounded 401/403 renewal, API-key protection, timeout sanitization, malformed schemas, duplicate IDs, and empty accounts. It uses synthetic fixtures and does not contact NRM.

Docker verification: the Compose definition was validated locally. A container build/run could not be performed in this session because Docker Desktop was not running and access to start it was not approved. The image therefore still needs its first build and container smoke test on a running Docker host.

The implementation was also tested live through the FastAPI endpoint with a fresh independent HTTP login, then a second request reusing its session. Both returned HTTP 200 and the three expected application numbers. An unauthorized request returned HTTP 401. No applications or cart entries were edited or submitted by this API verification.

## Project layout

```text
nrm-netzanmeldung/
├── README.md
├── pyproject.toml
├── Dockerfile             # non-root runtime image and healthcheck
├── compose.yaml           # standalone Compose service
├── openapi.json
├── .env.example
├── .env                  # local secret, Git-ignored; do not share
├── .gitignore
├── .dockerignore
├── nrm_api/
│   ├── __init__.py
│   ├── __main__.py        # CLI startup
│   ├── app.py             # HTTP API, authorization, lifecycle
│   ├── client.py          # SAML session and read-only NRM adapter
│   ├── config.py          # environment configuration
│   ├── errors.py          # sanitized error contracts
│   └── models.py          # public response schema
└── tests/
    └── test_api.py        # synthetic offline integration tests
```

## Future increments

The adapter and API layers are separated so future steps can add individual application details, document listing/downloads, comment retrieval, and other explicitly selected workflows. Physical-site aggregation and technical equipment inventory should be separate contracts from the application list. Write operations will require their own validation and explicit design; they are not exposed in this release.
