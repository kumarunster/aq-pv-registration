#!/usr/bin/env python3
"""Kratos-Login-End2End (DEV): Flow -> CSRF aus ui.nodes -> Login -> whoami.

Referenz-Verhalten aus Zeiterfassung: der csrf_token liegt DIREKT in
ui.nodes des Login-Flows. Der Flow-Details-Endpunkt gibt 403 (in dieser
Kratos-Version). Kein Cookie-Jar-Komponententest – der Token aus ui.nodes
ist der, den Kratos erwartet.
"""
import json, subprocess, tempfile, os

BASE = "http://localhost:8092"
JAR = tempfile.mktemp()

def curl(args):
    hf, bf = tempfile.mktemp(), tempfile.mktemp()
    subprocess.run(["curl", "-s", "-D", hf, "-o", bf, *args], capture_output=True)
    h, b = open(hf).read(), open(bf).read()
    os.unlink(hf); os.unlink(bf)
    return h, b

# 1) Login-Flow holen (CSRF liegt in ui.nodes)
h, b = curl([f"{BASE}/kratos/self-service/login/browser?redirect_to={BASE}/admin/",
             "-H", "Accept: application/json", "-c", JAR, "-b", JAR])
d = json.loads(b)
flow = d["id"]
csrf = next((n["attributes"]["value"] for n in d.get("ui", {}).get("nodes", [])
             if n.get("attributes", {}).get("name") == "csrf_token"), "")
print("flow ok" if flow else "FLOW NICHT GEFUNDEN")
print("csrf ok" if csrf else "CSRF NICHT GEFUNDEN")

# 2) Login POST (mit demselben Jar, damit der Set-Cookie aus Flow und
#    der Session-Cookie aus Login zusammenpassen)
payload = json.dumps({"method": "password", "identifier": "admin@amelanq.com",
                      "password": "Admin1234!", "csrf_token": csrf})
h, b = curl([f"{BASE}/kratos/self-service/login?flow={flow}",
             "-X", "POST", "-H", "Content-Type: application/json",
             "-b", JAR, "-c", JAR, "-d", payload])
print("login:", h.splitlines()[0])
if '"session"' in b or '"identity"' in b:
    print("LOGIN OK")
    h2, b2 = curl([f"{BASE}/kratos/sessions/whoami", "-b", JAR])
    print("whoami:", h2.splitlines()[0], b2[:250])
else:
    try:
        msg = [m.get("text") for m in json.loads(b).get("ui", {}).get("messages", [])
               if m.get("type") == "error"]
    except Exception:
        msg = [b[:300]]
    print("LOGIN FAILED:", msg)
os.unlink(JAR)
