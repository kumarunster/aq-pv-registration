#!/usr/bin/env bash
# Legt eine Kratos-Identity an oder setzt das Passwort einer bestehenden.
#
#   bash create_identity.sh <email> <passwort> [name] [admin|installer] [firma]
#
# Kratos-Admin-API wird ueber Docker aufgerufen (aus dem Docker-Netz heraus),
# das Passwort hash't Kratos selbst. NIEMALS Credentials direkt in der DB setzen!
set -euo pipefail

# Debug: DEBUG=1 bash create_account.sh ...  zeigt jeden ausgefuehrten Befehl.
# NA_KRATOS_CONTAINER: Name des Kratos-Containers (Standard: na-kratos).

EMAIL="${1:?Aufruf: create_identity.sh <email> <passwort> [name] [admin|installer] [firma]}"
PASSWORD="${2:?Passwort fehlt}"
NAME="${3:-}"
ROLE="${4:-admin}"
COMPANY="${5:-}"

if [ "${#PASSWORD}" -lt 8 ]; then
  echo "Passwort muss mindestens 8 Zeichen haben." >&2
  exit 1
fi
if [ "$ROLE" != "admin" ] && [ "$ROLE" != "installer" ]; then
  echo "Rolle muss admin oder installer sein." >&2
  exit 1
fi

COMPOSE_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$COMPOSE_DIR"
KRATOS_CONTAINER="${NA_KRATOS_CONTAINER:-na-kratos}"
DEBUG="${DEBUG:-0}"
if [ "${DEBUG}" = "1" ]; then
  # Vollständiger Trace: zeigt jeden ausgeführten Bash-Befehl (inkl. docker run)
  set -x
fi

debug() {
  if [ "${DEBUG}" = "1" ]; then
    echo "DEBUG: $*" >&2
  fi
}

kratos_container() {
  local c
  c="$(docker ps --format '{{.Names}}' | grep -E "^${KRATOS_CONTAINER}$" | head -1)"
  if [ -z "$c" ]; then
    c="$(docker ps -a --format '{{.Names}}' | grep -E "^${KRATOS_CONTAINER}$" | head -1)"
  fi
  if [ -z "$c" ]; then
    echo "Kein Kratos-Container mit Namen '${KRATOS_CONTAINER}' gefunden. Laufende Container:" >&2
    docker ps --format '{{.Names}}' >&2
    echo "Setze NA_KRATOS_CONTAINER auf den korrekten Namen und versuche erneut." >&2
    exit 1
  fi
  if ! docker ps -q --filter "name=^${c}$" | grep -q .; then
    echo "Kratos-Container '${c}' laeuft nicht (Status: $(docker inspect -f '{{.State.Status}}' "$c" 2>/dev/null || echo unbekannt))." >&2
    echo "Starte ihn mit: docker compose -f docker-compose.yml up -d na-kratos" >&2
    exit 1
  fi
  KRATOS_CONTAINER="$c"
  debug "Kratos-Container: ${KRATOS_CONTAINER}"
  # IP des Kratos-Containers im eigenen Netzwerk (zuverlaessiger als localhost)
  KRATOS_IP="$(docker inspect --format '{{range $name, $net := .NetworkSettings.Networks}}{{$net.IPAddress}}{{"\n"}}{{end}}' "$c" 2>/dev/null | grep -E '^[0-9]+\.' | head -1)"
  if [ -n "$KRATOS_IP" ]; then
    KRATOS_HOST="$KRATOS_IP"
  else
    KRATOS_HOST="localhost"
  fi
  debug "Kratos-Host: ${KRATOS_HOST}"
}

curl_json() {
  local method="$1" url="$2" data="${3:-}"
  kratos_container
  url="${url/localhost/${KRATOS_HOST}}"
  debug "METHOD=${method} URL=${url} NETWORK=container:${KRATOS_CONTAINER}"
  if [ -n "$data" ]; then
    debug "docker run --rm -i --network container:${KRATOS_CONTAINER} curlimages/curl:latest -fsS -X ${method} ${url} -H 'Content-Type: application/json' --data-binary @-"
    printf '%s' "$data" | docker run --rm -i --network "container:${KRATOS_CONTAINER}" \
      curlimages/curl:latest -fsS -X "$method" \
      "$url" -H "Content-Type: application/json" --data-binary @-
  else
    debug "docker run --rm --network container:${KRATOS_CONTAINER} curlimages/curl:latest -fsS -X ${method} ${url}"
    docker run --rm --network "container:${KRATOS_CONTAINER}" \
      curlimages/curl:latest -fsS -X "$method" "$url"
  fi
}

WORKDIR="$(mktemp -d "${COMPOSE_DIR}/.na-ident-XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Suche Identity: $EMAIL"
curl_json GET "http://localhost:4434/admin/identities?per_page=250" 1>"$WORKDIR/all.json" 2>"$WORKDIR/curl.err" || {
  echo "Fehler beim Abrufen der Identities:" >&2
  cat "$WORKDIR/curl.err" >&2
  exit 1
}

IDENT_ID="$(EMAIL_TARGET="$EMAIL" python3 - "$WORKDIR/all.json" <<'EOF'
import json, os, sys
target = os.environ["EMAIL_TARGET"]
for ident in json.load(open(sys.argv[1])):
    if ident.get("traits", {}).get("email") == target:
        print(ident["id"])
        break
EOF
)"

if [ -n "$IDENT_ID" ]; then
  echo "Bestehende Identity gefunden: $IDENT_ID"
  echo "Setze neues Passwort ..."

  curl_json GET "http://localhost:4434/admin/identities/$IDENT_ID" 1>"$WORKDIR/current.json" 2>"$WORKDIR/curl.err" || {
    echo "Fehler beim Lesen der Identity:" >&2
    cat "$WORKDIR/curl.err" >&2
    exit 1
  }

  NEW_PASSWORD="$PASSWORD" python3 - "$WORKDIR/current.json" > "$WORKDIR/payload.json" <<'EOF'
import json, os, sys
d = json.load(open(sys.argv[1]))
d["credentials"] = {"password": {"config": {"password": os.environ["NEW_PASSWORD"]}}}
print(json.dumps(d))
EOF

  response="$(curl_json PUT "http://localhost:4434/admin/identities/$IDENT_ID" "$(cat "$WORKDIR/payload.json")")" || {
    echo "Fehlgeschlagen:" >&2
    exit 1
  }
else
  echo "Keine Identity gefunden - lege neu an: $EMAIL"
  python3 - "$EMAIL" "$PASSWORD" "$NAME" "$ROLE" "$COMPANY" > "$WORKDIR/payload.json" <<'PY'
import json, sys
email, password, name, role, company = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5]
traits = {"email": email, "name": name}
if role == "installer":
    traits["company"] = company or name
print(json.dumps({
    "schema_id": role,
    "traits": traits,
    "credentials": {"password": {"config": {"password": password}}},
}))
PY

  response="$(curl_json POST "http://localhost:4434/admin/identities" "$(cat "$WORKDIR/payload.json")")" || {
    echo "Fehlgeschlagen:" >&2
    exit 1
  }
fi

printf '%s' "$response" | python3 -c '
import json, sys
try:
    d = json.load(sys.stdin)
    print("Fertig.")
    print("  ID   :", d.get("id"))
    print("  Mail :", d.get("traits", {}).get("email"))
    print("  Rolle:", d.get("schema_id"))
except Exception:
    print(sys.stdin.read())
'
