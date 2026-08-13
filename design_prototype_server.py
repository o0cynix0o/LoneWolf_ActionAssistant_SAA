"""Serve the local design studies without browser caching during iteration."""

from __future__ import annotations

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


class PrototypeHandler(SimpleHTTPRequestHandler):
    def end_headers(self) -> None:
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


def main() -> None:
    root = Path(__file__).resolve().parent
    handler = partial(PrototypeHandler, directory=str(root))
    with ThreadingHTTPServer(("127.0.0.1", 8766), handler) as server:
        server.serve_forever()


if __name__ == "__main__":
    main()
