#!/usr/bin/env bash
# Kratos-Login-End2End-Test (DEV, http://localhost:8092)
# Ein Cookie-Jar fuer die gesamte Kette.
set -euo pipefail
BASE="http://localhost:8092"
JAR=$(mktemp)
HDR=$(mktemp)
BODY=$(mktemp)
trap 'rm -f "$JAR" "$HDR" "$BODY"' EXIT

# 1) Login-Flow holen (setzt CSRF-Cookie, liefert Flow-JSON)
curl -s -D "$HDR" -o "$BODY" -c "$JAR" -b "$JAR" \
  -H 'Accept: application/json' \
  "$BASE/kratos/self-service/login/browser?redirect_to=$BASE/admin/"
FLOW=$(python3 -c "import json;print(json.load(open('$BODY'))['id'])")
echo "flow: $FLOW"
echo "cookies: $(grep -v '^#' $JAR | awk '{print $6}')"

# 2) CSRF aus Cookie-Jar (csrf_token_<flow>)
CSRF=$(grep "csrf_token" "$JAR" | awk '{print $7}')
echo "csrf: ${CSRF:***"

# 3) Login POST
curl -s -D "$HDR" -o "$BODY" -c "$JAR" -b "$JAR" -X POST \
  -H 'Content-Type: application/json' \
  -d "{\"method\":\"password\",\"identifier\":\"admin@amelanq.com\",\"password\":\"Admin1234!\",\"csrf_token\":\"$CSRF\"}" \
  "$BASE/kratos/self-service/login?flow=$FLOW"
echo "login: $(head -1 $HDR)"

# 4) whoami mit dem Session-Cookie
curl -s -D "$HDR" -o "$BODY" -b "$JAR" "$BASE/kratos/sessions/whoami"
echo "whoami: $(head -1 $HDR)"
head -c 300 "$BODY"; echo
