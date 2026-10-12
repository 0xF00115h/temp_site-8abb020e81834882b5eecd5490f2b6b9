#!/usr/bin/env python3
import json, os, secrets, tempfile
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "public"
DATA = PUBLIC / "inspection.json"
TOKEN = os.environ.get("BRIDGE_TOKEN", "")
HOST = os.environ.get("HOST", "0.0.0.0")
PORT = int(os.environ.get("PORT", "8080"))
MAX_BYTES = int(os.environ.get("MAX_BYTES", str(2 * 1024 * 1024)))

class Handler(BaseHTTPRequestHandler):
    server_version = "CardspaceTempBridge/0.1"

    def _json(self, code, obj):
        body = json.dumps(obj, separators=(",", ":")).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _send_file(self, path, content_type):
        if not path.exists():
            self._json(404, {"ok": False, "error": "not_found"})
            return
        body = path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        p = urlparse(self.path).path
        if p == "/health":
            self._json(200, {"ok": True, "service": "temp_site", "version": "0.1"})
        elif p == "/inspection.json":
            self._send_file(DATA, "application/json; charset=utf-8")
        elif p in ("/", "/index.html"):
            self._send_file(PUBLIC / "index.html", "text/html; charset=utf-8")
        else:
            self._json(404, {"ok": False, "error": "not_found"})

    def do_PUT(self):
        if urlparse(self.path).path != "/api/inspection":
            self._json(404, {"ok": False, "error": "not_found"}); return
        if not TOKEN:
            self._json(503, {"ok": False, "error": "bridge_token_not_configured"}); return
        auth = self.headers.get("Authorization", "")
        expected = f"Bearer {TOKEN}"
        if not secrets.compare_digest(auth, expected):
            self._json(401, {"ok": False, "error": "unauthorized"}); return
        try:
            n = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            self._json(400, {"ok": False, "error": "bad_content_length"}); return
        if n <= 0 or n > MAX_BYTES:
            self._json(413, {"ok": False, "error": "invalid_size", "max_bytes": MAX_BYTES}); return
        body = self.rfile.read(n)
        try:
            parsed = json.loads(body)
        except Exception:
            self._json(400, {"ok": False, "error": "invalid_json"}); return
        PUBLIC.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(prefix="inspection.", suffix=".tmp", dir=PUBLIC)
        try:
            with os.fdopen(fd, "wb") as f:
                f.write(json.dumps(parsed, indent=2, ensure_ascii=False).encode("utf-8"))
                f.write(b"\n")
                f.flush(); os.fsync(f.fileno())
            os.replace(tmp, DATA)
        finally:
            if os.path.exists(tmp): os.unlink(tmp)
        self._json(200, {"ok": True, "bytes": len(body)})

    def log_message(self, fmt, *args):
        print(f"{self.address_string()} - {fmt % args}")

if __name__ == "__main__":
    PUBLIC.mkdir(parents=True, exist_ok=True)
    if not DATA.exists():
        DATA.write_text('{"ok":false,"status":"no inspection published yet"}\n')
    print(f"temp_site listening on http://{HOST}:{PORT}")
    ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
