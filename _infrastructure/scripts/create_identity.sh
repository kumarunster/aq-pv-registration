#!/usr/bin/env bash
# Legt eine Kratos-Identity an oder setzt das Passwort einer bestehenden.
#
#   bash create_identity.sh <email> <passwort> <name> <admin|installer> [firma]
#
# admin:     Traits = email + name
# installer: Traits = email + name + company (Pflichtfeld, 5. Argument)
#
# Das Skript legt nur die Kratos-Identity + das Passwort an. Es macht keinen
# Oathkeeper-Grant, keine Session und keinen Login. Existiert die E-Mail
# schon, wird das Passwort der bestehenden Identity aktualisiert (Schema wird
# nicht gewechselt).
set -euo pipefail

EMAIL="${1:?Aufruf: create_identity.sh <email> <passwort> <name> <admin|installer> [firma]}"
PASSWORD="${2:?Passwort fehlt}"
NAME="${3:?Name fehlt}"
ROLE="${4:?Rolle fehlt (admin|installer)}"
COMPANY="${5:-}"

if [ "${#PASSWORD}" -lt 8 ]; then
  echo "Passwort muss mindestens 8 Zeichen haben." >&2
  exit 1
fi
if [ "$ROLE" != "admin" ] && [ "$ROLE" != "installer" ]; then
  echo "Rolle muss admin oder installer sein." >&2
  exit 1
fi
if [ "$ROLE" = "installer" ] && [ -z "$COMPANY" ]; then
  echo "Installer-Identity braucht das 5. Argument: Firmenname." >&2
  exit 1
fi

CONTAINER="${NA_KRATOS_CONTAINER:-na-kratos}"

if ! docker ps --format '{{.Names}}' | grep -qx "$CONTAINER"; then
  echo "Kratos-Container '$CONTAINER' laeuft nicht." >&2
  exit 1
fi

curl_json() {
  local method="$1" url="$2" data="${3:-}"
  if [ -n "$data" ]; then
    printf '%s' "$data" | docker run --rm -i --network "container:${CONTAINER}" \
      curlimages/curl:latest -fsS -X "$method" \
      "$url" -H "Content-Type: application/json" --data-binary @-
  else
    docker run --rm --network "container:${CONTAINER}" \
      curlimages/curl:latest -fsS -X "$method" "$url"
  fi
}

WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

echo "Suche Identity: $EMAIL"
if ! curl_json GET "http://localhost:4434/admin/identities?per_page=250" > "$WORKDIR/all.json" 2>&1; then
  echo "Fehler beim Abrufen der Identities:" >&2
  cat "$WORKDIR/all.json" >&2
  exit 1
fi

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
  echo "Setze neues Passwort (Schema bleibt unveraendert) ..."

  if ! curl_json GET "http://localhost:4434/admin/identities/$IDENT_ID" > "$WORKDIR/current.json" 2>&1; then
    echo "Fehler beim Lesen der Identity:" >&2
    cat "$WORKDIR/current.json" >&2
    exit 1
  fi

  if ! NEW_PASSWORD="$PASSWORD" python3 - "$WORKDIR/current.json" > "$WORKDIR/payload.json" <<'EOF'
import json, os, sys
d = json.load(open(sys.argv[1]))
d["credentials"] = {"password": {"config": {"password": os.environ["NEW_PASSWORD"]}}}
print(json.dumps(d))
EOF
  then
    echo "Payload-Fehler" >&2
    exit 1
  fi

  if ! curl_json PUT "http://localhost:4434/admin/identities/$IDENT_ID" "$(cat "$WORKDIR/payload.json")" >/dev/null 2>&1; then
    echo "Passwort-Update fehlgeschlagen:" >&2
    exit 1
  fi
  echo "OK: Passwort fuer $EMAIL aktualisiert."
else
  echo "Keine Identity gefunden - lege neu an: $EMAIL ($ROLE)"
  EMAIL_ARG="$EMAIL" NAME_ARG="$NAME" ROLE_ARG="$ROLE" COMPANY_ARG="$COMPANY" PASSWORD_ARG="$PASSWORD" \
    python3 - > "$WORKDIR/payload.json" <<'EOF'
import json, os
email = os.environ["EMAIL_ARG"]
name = os.environ["NAME_ARG"]
role = os.environ["ROLE_ARG"]
company = os.environ["COMPANY_ARG"]
password = os.environ["PASSWORD_ARG"]
traits = {"email": email, "name": name}
if role == "installer":
    traits["company"] = company
payload = {
    "schema_id": role,
    "traits": traits,
    "credentials": {"password": {"config": {"password": password}}},
}
print(json.dumps(payload))
EOF

  if ! curl_json POST "http://localhost:4434/admin/identities" "$(cat "$WORKDIR/payload.json")" >/dev/null 2>&1; then
    echo "Identity-Anlage fehlgeschlagen (409 = E-Mail existiert schon in anderem Schema?)" >&2
    exit 1
  fi
  echo "OK: Identity $EMAIL ($ROLE) angelegt."
fi
