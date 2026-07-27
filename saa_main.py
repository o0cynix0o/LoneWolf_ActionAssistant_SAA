#!/usr/bin/env python3
"""Desktop entry point for Lone Wolf Action Assistant v3."""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import sys
import time
import urllib.request

import app_server
import book_manager
import lonewolf_redux
from runtime_paths import PATHS
from ws_server import WebSocketService


APP_TITLE = "Lone Wolf Action Assistant"
DEFAULT_HTTP_PORT = 8797
DEFAULT_WS_PORT = 8798


def _lifecycle_log(message: str) -> None:
    """Record desktop lifecycle failures and shutdown progress."""
    try:
        PATHS.logs.mkdir(parents=True, exist_ok=True)
        with (PATHS.logs / "desktop.log").open("a", encoding="utf-8") as handle:
            handle.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}\n")
    except OSError:
        pass


def _book_folders() -> tuple[str, ...]:
    return tuple(str(meta.get("Folder") or "") for meta in lonewolf_redux.BOOKS.values())


def _attach_parent_console(kernel32=None) -> bool:
    """Attach a windowed frozen process to the console created by WinPTY."""
    try:
        if kernel32 is None:
            kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        get_console_window = kernel32.GetConsoleWindow
        get_console_window.restype = ctypes.c_void_p
        attach_console = kernel32.AttachConsole
        attach_console.argtypes = [ctypes.c_uint]
        attach_console.restype = ctypes.c_int
        if get_console_window():
            return True
        return bool(attach_console(0xFFFFFFFF))  # ATTACH_PARENT_PROCESS
    except (AttributeError, OSError):
        return False


def _prepare_cli_stdio() -> bool:
    """Attach Python streams to the WinPTY console for a windowed EXE."""
    if os.name != "nt" or not getattr(sys, "frozen", False):
        return True
    if not _attach_parent_console():
        _lifecycle_log(f"CLI console attachment failed: Windows error {ctypes.get_last_error()}")
    try:
        sys.stdin = open("CONIN$", "r", encoding="utf-8", errors="replace")
        sys.stdout = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
        sys.stderr = open("CONOUT$", "w", encoding="utf-8", errors="replace", buffering=1)
        return True
    except OSError as exc:
        _lifecycle_log(f"CLI console streams could not be opened: {exc}")
        return False


def _start_http(preferred_port: int):
    try:
        return app_server.start_server(port=preferred_port)
    except OSError:
        return app_server.start_server(port=0)


def _start_websocket(preferred_port: int) -> WebSocketService:
    try:
        return WebSocketService(port=preferred_port).start()
    except RuntimeError:
        return WebSocketService(port=0).start()


def _wait_for_http(url: str, timeout: float = 10.0) -> None:
    deadline = time.monotonic() + timeout
    last_error: BaseException | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(f"{url}/api/state", timeout=1) as response:
                if response.status == 200:
                    return
        except BaseException as exc:
            last_error = exc
            time.sleep(0.05)
    raise RuntimeError(f"HTTP service did not become ready: {last_error}")


def run_self_test() -> int:
    """Smoke-test packaged resources and both listening services."""
    http_server = None
    http_thread = None
    websocket = None
    try:
        PATHS.ensure_writable()
        required = (
            PATHS.resource_root / "index.html",
            PATHS.resource_root / "assistant.html",
            PATHS.resource_root / "assets" / "images" / "series-sigil-wolf-mask.png",
            PATHS.resource_data / "crt.json",
        )
        missing = [str(path) for path in required if not path.is_file()]
        if missing:
            raise RuntimeError(f"Missing packaged resources: {missing}")

        http_server, http_thread = _start_http(0)
        http_port = int(http_server.server_address[1])
        websocket = _start_websocket(0)
        base_url = f"http://127.0.0.1:{http_port}"
        _wait_for_http(base_url)
        with urllib.request.urlopen(f"{base_url}/api/book-files", timeout=3) as response:
            payload = json.load(response)
        if "Books" not in payload:
            raise RuntimeError("Book-files API returned an invalid response.")
        with urllib.request.urlopen(
            f"{base_url}/assets/images/series-sigil-wolf-mask.png",
            timeout=3,
        ) as response:
            sigil_type = response.headers.get_content_type()
            sigil_signature = response.read(8)
        if sigil_type != "image/png" or sigil_signature != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("Series sigil asset was not served as a valid PNG.")
        result = {
            "ok": True,
            "httpPort": http_port,
            "wsPort": websocket.port,
            "resourceRoot": str(PATHS.resource_root),
            "userRoot": str(PATHS.user_root),
            "booksRoot": str(PATHS.books),
        }
        if sys.stdout is not None:
            try:
                print(json.dumps(result, indent=2))
            except OSError:
                pass
        return 0
    finally:
        if websocket is not None:
            websocket.stop()
        if http_server is not None:
            app_server.stop_server(http_server, http_thread)


def run_desktop() -> int:
    try:
        import webview
    except ImportError as exc:
        raise RuntimeError("pywebview is required to run the desktop application.") from exc

    PATHS.ensure_writable()
    http_server = None
    http_thread = None
    websocket = None
    try:
        _lifecycle_log("desktop startup begin")
        http_server, http_thread = _start_http(DEFAULT_HTTP_PORT)
        http_port = int(http_server.server_address[1])
        websocket = _start_websocket(DEFAULT_WS_PORT)
        base_url = f"http://127.0.0.1:{http_port}"
        _wait_for_http(base_url)

        window = webview.create_window(
            APP_TITLE,
            f"{base_url}/index.html?wsPort={websocket.port}",
            width=1440,
            height=960,
            min_size=(1000, 700),
        )

        webview.start(debug=os.environ.get("LONEWOLF_SAA_DEBUG") == "1")
        _lifecycle_log("webview event loop returned")
        return 0
    except Exception as exc:
        _lifecycle_log(f"desktop failure: {type(exc).__name__}: {exc}")
        raise
    finally:
        if websocket is not None:
            _lifecycle_log("stopping websocket")
            websocket.stop()
        if http_server is not None:
            _lifecycle_log("stopping http")
            app_server.stop_server(http_server, http_thread)
        _lifecycle_log("desktop shutdown complete")


def main() -> int:
    if getattr(sys, "frozen", False):
        # PyInstaller's windowed bootloader exposes placeholder streams that
        # can raise during interpreter shutdown. CLI mode replaces them below.
        sys.stdout = None
        sys.stderr = None

    # WinPTY launches the same frozen EXE in this mode. Remove the dispatcher
    # flag so the existing CLI parser receives only its own arguments.
    if "--cli" in sys.argv[1:]:
        sys.argv.remove("--cli")
        if not _prepare_cli_stdio():
            return 1
        lonewolf_redux.main()
        return 0

    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument(
        "--import-books",
        action="append",
        default=[],
        metavar="PATH",
        help="Import an extracted book folder or Project Aon ZIP and exit",
    )
    args = parser.parse_args()
    if args.self_test or os.environ.get("LONEWOLF_SAA_SELF_TEST") == "1":
        return run_self_test()
    if args.import_books:
        result = book_manager.import_books(args.import_books, _book_folders())
        print(json.dumps(result, indent=2))
        return 0
    return run_desktop()


if __name__ == "__main__":
    exit_code = main()
    if getattr(sys, "frozen", False):
        # pythonnet can leave CLR bookkeeping threads alive after pywebview has
        # closed. All app-owned services are already stopped by run_desktop's
        # finally block, so finish the frozen process without waiting on them.
        os._exit(exit_code)
    raise SystemExit(exit_code)
