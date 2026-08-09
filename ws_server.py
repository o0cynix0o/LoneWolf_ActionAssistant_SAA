#!/usr/bin/env python3
"""
WebSocket terminal bridge for the Lone Wolf Action Assistant Redux.

The browser sends raw terminal input to this server. The server starts
lonewolf_redux.py and streams terminal output back to xterm.js.
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import urlsplit

from websockets.asyncio.server import serve
from runtime_paths import PATHS

try:
    import winpty  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    winpty = None

if os.name != "nt":
    import fcntl
    import pty
    import struct
    import termios


SCRIPT_DIR = PATHS.resource_root
ASSISTANT_SCRIPT = SCRIPT_DIR / "lonewolf_redux.py"
WS_HOST = "localhost"
WS_PORT = int(os.environ.get("LONEWOLF_REDUX_WS_PORT", "8798"))
INIT_COLS = 120
INIT_ROWS = 30
PIPE_CLI_ENV = "LONEWOLF_SAA_PIPE_CLI"

LOCAL_WS_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}


def normalize_winpty_input(text: str) -> str:
    """Translate xterm's standalone Enter event for WinPTY.

    xterm.js emits ordinary typing one WebSocket message at a time and emits
    Enter as a standalone carriage return.  WinPTY echoes that carriage return
    but does not submit the line unless it receives the complete CRLF sequence.
    Preserve every other input sequence verbatim so Backspace, pasted text, and
    terminal control sequences retain their normal behavior.
    """
    return "\r\n" if text == "\r" else text


def origin_is_local(origin: str | None) -> bool:
    """Return True when a handshake Origin is safe to accept.

    A browser always sends Origin on a WebSocket handshake, so a missing Origin
    means a non-browser client (e.g. the packaged CLI worker) and is allowed. A
    present Origin must resolve to loopback so a page on another site cannot
    open the embedded terminal against this bridge.
    """
    if not origin:
        return True
    parsed = urlsplit(origin if "://" in origin else "//" + origin)
    return (parsed.hostname or "").lower() in LOCAL_WS_HOSTNAMES


def build_command() -> list[str]:
    last_save_txt = PATHS.user_data / "last-save.txt"
    load_args: list[str] = []
    try:
        if last_save_txt.exists():
            save_path = last_save_txt.read_text(encoding="utf-8").strip()
            if save_path and Path(save_path).exists():
                load_args = ["--load", save_path]
    except Exception:
        pass
    shared_args = [
        "--save-dir",
        str(PATHS.saves),
        "--data-dir",
        str(PATHS.resource_data),
        "--state-data-dir",
        str(PATHS.user_data),
        "--books-dir",
        str(PATHS.books_lw),
    ] + load_args
    if getattr(sys, "frozen", False):
        # The desktop EXE is windowed, so relaunching it with --cli under WinPTY
        # runs the embedded terminal from the same frozen binary without opening
        # a visible Windows Terminal tab and without a separate console EXE.
        return [sys.executable, "--cli"] + shared_args
    return [sys.executable, "-u", str(ASSISTANT_SCRIPT)] + shared_args


def pipe_cli_environment() -> dict[str, str]:
    """Mark a frozen CLI child so it keeps the standard pipes supplied by us."""
    environment = dict(os.environ)
    environment[PIPE_CLI_ENV] = "1"
    return environment


async def terminal_session(websocket):
    origin = websocket.request.headers.get("Origin")
    if not origin_is_local(origin):
        await websocket.close(code=1008, reason="cross-origin request rejected")
        return
    command = build_command()
    if os.name == "nt" and getattr(sys, "frozen", False):
        # A pipe-backed CLI avoids WinPTY's screen-scrape echo stream. The
        # browser owns line editing and sends complete lines to this process.
        await terminal_session_pipes(websocket, command, env=pipe_cli_environment())
    elif os.name == "nt" and winpty is not None:
        await terminal_session_winpty(websocket, command)
    elif os.name != "nt":
        await terminal_session_posix_pty(websocket, command)
    else:
        await terminal_session_pipes(websocket, command)


async def terminal_session_winpty(websocket, command: list[str]) -> None:
    loop = asyncio.get_running_loop()
    try:
        # The main EXE remains a windowed application. Its --cli entry point
        # attaches to WinPTY's hidden console, which keeps the embedded xterm
        # stream alive without opening a separate console window or terminal.
        backend = winpty.Backend.WinPTY if getattr(sys, "frozen", False) else None
        pty_proc = winpty.PtyProcess.spawn(
            command,
            dimensions=(INIT_ROWS, INIT_COLS),
            cwd=str(PATHS.user_root),
            backend=backend,
        )
    except Exception as exc:
        await websocket.send(f"\r\nERROR: could not start Python assistant - {exc}\r\n")
        return

    out_queue: asyncio.Queue[str | None] = asyncio.Queue()
    stop_reader = threading.Event()

    def reader_thread() -> None:
        while not stop_reader.is_set():
            try:
                data = pty_proc.read(4096)
                if data:
                    asyncio.run_coroutine_threadsafe(out_queue.put(data), loop)
                elif not pty_proc.isalive():
                    break
            except (EOFError, OSError):
                break
            except Exception:
                break
        asyncio.run_coroutine_threadsafe(out_queue.put(None), loop)

    reader = threading.Thread(target=reader_thread, daemon=True)
    reader.start()

    async def pump_out() -> None:
        while True:
            data = await out_queue.get()
            if data is None:
                break
            try:
                await websocket.send(data)
            except Exception:
                break

    async def pump_in() -> None:
        try:
            async for msg in websocket:
                text = msg if isinstance(msg, str) else msg.decode("utf-8", errors="replace")
                if text.startswith("\x00"):
                    try:
                        obj = json.loads(text[1:])
                        if obj.get("type") == "resize":
                            rows = max(1, int(obj.get("rows", INIT_ROWS)))
                            cols = max(1, int(obj.get("cols", INIT_COLS)))
                            pty_proc.setwinsize(rows, cols)
                    except Exception:
                        pass
                else:
                    pty_proc.write(normalize_winpty_input(text))
        except Exception:
            pass

    out_task = asyncio.create_task(pump_out())
    in_task = asyncio.create_task(pump_in())
    await asyncio.wait([out_task, in_task], return_when=asyncio.FIRST_COMPLETED)

    stop_reader.set()
    out_task.cancel()
    in_task.cancel()
    await asyncio.gather(out_task, in_task, return_exceptions=True)

    try:
        pty_proc.terminate(force=True)
    except Exception:
        pass


def set_posix_pty_size(fd: int, rows: int, cols: int) -> None:
    if os.name == "nt":
        return
    winsize = struct.pack("HHHH", rows, cols, 0, 0)
    fcntl.ioctl(fd, termios.TIOCSWINSZ, winsize)


async def terminal_session_posix_pty(websocket, command: list[str]) -> None:
    loop = asyncio.get_running_loop()
    master_fd, slave_fd = pty.openpty()
    set_posix_pty_size(master_fd, INIT_ROWS, INIT_COLS)

    proc = subprocess.Popen(
        command,
        stdin=slave_fd,
        stdout=slave_fd,
        stderr=slave_fd,
        cwd=str(PATHS.user_root),
        close_fds=True,
    )
    os.close(slave_fd)

    out_queue: asyncio.Queue[str | None] = asyncio.Queue()
    stop_reader = threading.Event()

    def reader_thread() -> None:
        while not stop_reader.is_set():
            try:
                data = os.read(master_fd, 4096)
                if data:
                    text = data.decode("utf-8", errors="replace")
                    asyncio.run_coroutine_threadsafe(out_queue.put(text), loop)
                elif proc.poll() is not None:
                    break
            except OSError:
                break
        asyncio.run_coroutine_threadsafe(out_queue.put(None), loop)

    reader = threading.Thread(target=reader_thread, daemon=True)
    reader.start()

    async def pump_out() -> None:
        while True:
            data = await out_queue.get()
            if data is None:
                break
            try:
                await websocket.send(data)
            except Exception:
                break

    async def pump_in() -> None:
        try:
            async for msg in websocket:
                text = msg if isinstance(msg, str) else msg.decode("utf-8", errors="replace")
                if text.startswith("\x00"):
                    try:
                        obj = json.loads(text[1:])
                        if obj.get("type") == "resize":
                            rows = max(1, int(obj.get("rows", INIT_ROWS)))
                            cols = max(1, int(obj.get("cols", INIT_COLS)))
                            set_posix_pty_size(master_fd, rows, cols)
                    except Exception:
                        pass
                else:
                    os.write(master_fd, text.encode("utf-8", errors="replace"))
        except Exception:
            pass

    out_task = asyncio.create_task(pump_out())
    in_task = asyncio.create_task(pump_in())
    await asyncio.wait([out_task, in_task], return_when=asyncio.FIRST_COMPLETED)

    stop_reader.set()
    out_task.cancel()
    in_task.cancel()
    await asyncio.gather(out_task, in_task, return_exceptions=True)
    if proc.poll() is None:
        proc.terminate()
    try:
        os.close(master_fd)
    except OSError:
        pass


async def terminal_session_pipes(
    websocket, command: list[str], *, env: dict[str, str] | None = None
) -> None:
    try:
        proc = await asyncio.create_subprocess_exec(
            *command,
            cwd=str(PATHS.user_root),
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
            env=env,
        )
    except Exception as exc:
        await websocket.send(f"\r\nERROR: could not start Python assistant - {exc}\r\n")
        return

    async def pump_out() -> None:
        assert proc.stdout is not None
        while True:
            data = await proc.stdout.read(4096)
            if not data:
                break
            try:
                await websocket.send(data.decode("utf-8", errors="replace"))
            except Exception:
                break

    async def pump_in() -> None:
        assert proc.stdin is not None
        try:
            async for msg in websocket:
                text = msg if isinstance(msg, str) else msg.decode("utf-8", errors="replace")
                if text.startswith("\x00"):
                    continue
                proc.stdin.write(text.encode("utf-8", errors="replace"))
                await proc.stdin.drain()
        except Exception:
            pass

    out_task = asyncio.create_task(pump_out())
    in_task = asyncio.create_task(pump_in())
    await asyncio.wait([out_task, in_task], return_when=asyncio.FIRST_COMPLETED)
    out_task.cancel()
    in_task.cancel()
    await asyncio.gather(out_task, in_task, return_exceptions=True)
    if proc.stdin is not None:
        proc.stdin.close()
        try:
            await proc.stdin.wait_closed()
        except (BrokenPipeError, ConnectionResetError):
            pass
    if proc.returncode is None:
        proc.terminate()
    try:
        await asyncio.wait_for(proc.wait(), timeout=5)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()


def write_current_position() -> None:
    try:
        last_save_txt = PATHS.user_data / "last-save.txt"
        if not last_save_txt.exists():
            return
        save_path = last_save_txt.read_text(encoding="utf-8").strip()
        if not save_path or not Path(save_path).exists():
            return
        with Path(save_path).open("r", encoding="utf-8") as handle:
            data = json.load(handle)
        book_num = int(data.get("Character", {}).get("BookNumber", 0))
        section = int(data.get("CurrentSection", 0))
        if book_num > 0 and section > 0:
            pos_file = PATHS.current_position
            pos_file.write_text(json.dumps({"book": book_num, "section": section}), encoding="utf-8")
            print(f"Position: Book {book_num}, Section {section}", flush=True)
    except Exception as exc:
        print(f"Could not read save position: {exc}", flush=True)


class WebSocketService:
    """Own a WebSocket server, event loop, and daemon thread."""

    def __init__(self, host: str = "127.0.0.1", port: int = 8798) -> None:
        self.host = host
        self.requested_port = port
        self.port = 0
        self.thread: threading.Thread | None = None
        self.loop: asyncio.AbstractEventLoop | None = None
        self._stop_event: asyncio.Event | None = None
        self._ready = threading.Event()
        self._error: BaseException | None = None

    async def _run(self) -> None:
        self._stop_event = asyncio.Event()
        try:
            async with serve(terminal_session, self.host, self.requested_port) as server:
                sockets = server.sockets or []
                if not sockets:
                    raise RuntimeError("WebSocket server did not create a listening socket.")
                self.port = int(sockets[0].getsockname()[1])
                self._ready.set()
                await self._stop_event.wait()
        except BaseException as exc:
            self._error = exc
            self._ready.set()

    def start(self, timeout: float = 10.0) -> "WebSocketService":
        PATHS.ensure_writable()
        write_current_position()

        def runner() -> None:
            self.loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.loop)
            try:
                self.loop.run_until_complete(self._run())
            finally:
                self.loop.run_until_complete(self.loop.shutdown_asyncgens())
                self.loop.close()

        self.thread = threading.Thread(target=runner, name="lonewolf-websocket", daemon=True)
        self.thread.start()
        if not self._ready.wait(timeout):
            raise TimeoutError("Timed out while starting the WebSocket server.")
        if self._error is not None:
            raise RuntimeError(f"Could not start WebSocket server: {self._error}") from self._error
        return self

    def stop(self) -> None:
        if self.loop and self._stop_event and self.loop.is_running():
            self.loop.call_soon_threadsafe(self._stop_event.set)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)


async def main() -> None:
    write_current_position()
    print(f"Lone Wolf WebSocket server: ws://{WS_HOST}:{WS_PORT}", flush=True)
    async with serve(terminal_session, WS_HOST, WS_PORT):
        await asyncio.Future()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nWebSocket server stopped.")
