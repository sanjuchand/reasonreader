"""Internal HTTP ingest for production. The Next image has no `uv`."""

from __future__ import annotations

import json
import os
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse

COPY_ID_RE = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    re.I,
)


def ingest_token() -> str:
    return os.environ.get("INGEST_TOKEN") or os.environ.get("SECRET_KEY") or ""


def authorized(header: str | None) -> bool:
    token = ingest_token()
    if not token:
        return False
    return (header or "") == f"Bearer {token}"


def parse_copy_id(body: bytes) -> str:
    payload = json.loads(body.decode("utf-8") or "{}")
    copy_id = str(payload.get("copyId") or payload.get("copy_id") or "").strip()
    if not COPY_ID_RE.match(copy_id):
        raise ValueError("Invalid copy id")
    return copy_id


class IngestHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args) -> None:
        print(f"ingest: {format % args}", flush=True)

    def _send(self, status: int, payload: dict) -> None:
        raw = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self) -> None:
        path = urlparse(self.path).path
        if path == "/health":
            self._send(200, {"ok": True})
            return
        self._send(404, {"detail": "Not found"})

    def do_POST(self) -> None:
        path = urlparse(self.path).path
        if path != "/ingest":
            self._send(404, {"detail": "Not found"})
            return
        if not authorized(self.headers.get("Authorization")):
            self._send(401, {"detail": "Not authenticated"})
            return
        length = int(self.headers.get("Content-Length") or "0")
        raw = self.rfile.read(length) if length else b"{}"
        try:
            copy_id = parse_copy_id(raw)
        except (ValueError, json.JSONDecodeError):
            self._send(400, {"detail": "Invalid copy id"})
            return
        try:
            from ingest.pipeline import ingest_copy

            result = ingest_copy(copy_id)
        except Exception as exc:
            self._send(500, {"detail": str(exc)[:500]})
            return
        self._send(200, result)


def serve(host: str = "0.0.0.0", port: int | None = None) -> None:
    bound = port or int(os.environ.get("INGEST_PORT") or "8090")
    server = ThreadingHTTPServer((host, bound), IngestHandler)
    print(f"ingest listening on {host}:{bound}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    serve()
