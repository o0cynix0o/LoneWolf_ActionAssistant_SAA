#!/usr/bin/env python3
"""Headless server entrypoint for the containerized Lone Wolf web app.

Runs the HTTP app server and the WebSocket terminal server with no desktop
window, so the app can run in a container and be used from a browser at
http://localhost:8797/. Paths are taken from the environment (see the
Dockerfile / docker-compose.yml), which is how books and saves are redirected
to a mounted volume.
"""

from __future__ import annotations

import json
import os

import app_server
from runtime_paths import PATHS
from ws_server import WebSocketService


def _configure_cheats(base_url: str) -> None:
    """Let the CLI worker reach the same cheat session; non-fatal if it can't."""
    try:
        cheat_url = f"{base_url}/api/internal/session-cheats"
        os.environ["LONEWOLF_SAA_CHEAT_URL"] = cheat_url
        os.environ["LONEWOLF_SAA_CHEAT_TOKEN"] = app_server.CHEAT_SESSION.token
        cheat_file = PATHS.user_data / "cheat-session.json"
        cheat_file.parent.mkdir(parents=True, exist_ok=True)
        cheat_file.write_text(
            json.dumps({"url": cheat_url, "token": app_server.CHEAT_SESSION.token}),
            encoding="utf-8",
        )
        os.environ["LONEWOLF_SAA_CHEAT_FILE"] = str(cheat_file)
    except OSError:
        pass


def main() -> int:
    http_host = os.environ.get("LONEWOLF_SAA_HTTP_HOST", "0.0.0.0")
    http_port = int(os.environ.get("LONEWOLF_REDUX_HTTP_PORT", "8797"))
    ws_host = os.environ.get("LONEWOLF_SAA_WS_HOST", "0.0.0.0")
    ws_port = int(os.environ.get("LONEWOLF_REDUX_WS_PORT", "8798"))

    PATHS.ensure_writable()
    _configure_cheats(f"http://127.0.0.1:{http_port}")

    websocket = WebSocketService(host=ws_host, port=ws_port).start()
    print(f"Lone Wolf WebSocket: ws://{ws_host}:{websocket.port}", flush=True)

    http_server = app_server.create_server(http_host, http_port)
    print(
        f"Lone Wolf web app listening on http://{http_host}:{http_port}/ "
        f"(open http://localhost:{http_port}/ in your browser)",
        flush=True,
    )
    try:
        http_server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        websocket.stop()
        http_server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
