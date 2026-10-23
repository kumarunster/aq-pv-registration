"""
WeasyPrint-Service: rendert HTML zu PDF.

Ein duenner HTTP-Server, der HTML (mit eingebetteten SVG-Vektoren)
in ein A4-PDF umwandelt. Wird vom Lageplan-Backend aufgerufen.
Port 8012 (intern, kein Host-Port-Mapping).
"""
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from weasyprint import HTML

PORT = 8012


class Handler(BaseHTTPRequestHandler):
    def _send(self, code: int, body: bytes, content_type: str):
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        # Health-Check
        if self.path == "/health":
            self._send(200, json.dumps({"status": "ok", "service": "weasyprint"}).encode(),
                       "application/json")
        else:
            self._send(404, b"not found", "text/plain")

    def do_POST(self):
        # Nur /render akzeptiert
        if self.path != "/render":
            self._send(404, b"not found", "text/plain")
            return

        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        try:
            payload = json.loads(raw)
            html = payload.get("html", "")
            if not html:
                self._send(400, json.dumps({"error": "missing html"}).encode(),
                           "application/json")
                return
            pdf_bytes = HTML(string=html).write_pdf()
            self._send(200, pdf_bytes, "application/pdf")
        except Exception as e:
            self._send(500, json.dumps({"error": str(e)}).encode(),
                       "application/json")

    def log_message(self, fmt, *args):
        # Weniger Log-Spam
        pass


if __name__ == "__main__":
    print(f"WeasyPrint-Service auf Port {PORT}", flush=True)
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
