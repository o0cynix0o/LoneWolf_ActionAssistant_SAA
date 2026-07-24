# CODEX BRIEF — Package Lone Wolf Action Assistant as a standalone Windows desktop app

## Repo / paths
- **Current web app (source of truth):** `C:\Scripts\LoneWolf_ActionAssistant_Redux`
- **New standalone app (build here):** `C:\Scripts\LoneWolf_ActionAssistant_SAA`
- **Repo:** https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA

## Goal
Turn the existing local web app into a standalone Windows desktop app that runs in its **own window** (no browser, no manual server start) and **looks exactly like it does today**. Ship it as a Windows installer that bundles the Python runtime and all libraries — target PCs need **nothing** installed. Do **not** bundle the licensed book files; the user supplies those (see *Licensed content*).

## Current architecture (reuse it — don't rewrite the UI)
- `app_server.py` — Python stdlib `http.server` (`ThreadingHTTPServer`), default port **8797**, serves the HTML UI (`assistant.html` ~223 KB, `index.html`, `library.html`, `install-books.html`) and assets.
- `ws_server.py` — `websockets` server (port **8798**) + `pywinpty`, an embedded CLI/terminal bridge.
- `launch_lonewolf_redux.py` — starts both servers, then `webbrowser.open(localhost:8797)`.
- Content in `books\`; state in `current-position.json`, `saves\`, `data\`.
- Deps: `websockets>=12`, `pywinpty` (Windows).

## Approach — wrap the existing web UI in a native window with pywebview
Chosen deliberately over a Tkinter rebuild: the UI is a large, interactive HTML/JS app with a live websocket terminal. pywebview renders the **same** HTML/JS in a native OS window, so it looks identical with minimal risk. A Tkinter rewrite would be a huge re-implementation and would not match.

1. Add **pywebview**. Create one entry script (e.g. `saa_main.py`) that:
   - Starts the HTTP server and the websocket server **in-process on background (daemon) threads** — do **NOT** spawn `sys.executable app_server.py` as subprocesses (that breaks under a PyInstaller onefile build). Refactor `app_server.py` / `ws_server.py` to expose a `start()` callable on a thread (`ThreadingHTTPServer.serve_forever` in a thread; run the websockets asyncio server in its own thread + event loop).
   - Picks ports (keep 8797/8798, but handle "port in use" by selecting a free port and passing it to the UI).
   - Opens a pywebview window pointing at `http://localhost:<http_port>` — renders the exact same UI.
   - On window close, shuts the servers down and exits cleanly.
2. Keep ALL existing HTML/CSS/JS as-is — that's what preserves the look.

## Packaging (PyInstaller — one self-contained windowed EXE)
```
python -m PyInstaller --onefile --noconsole --name "Lone Wolf Action Assistant" ^
  --icon "logo.ico" --add-data "logo.ico;." ^
  --add-data "assistant.html;." --add-data "index.html;." --add-data "library.html;." ^
  --add-data "install-books.html;." --add-data "assets;assets" ^
  --collect-all pywebview --collect-all websockets --collect-all winpty ^
  saa_main.py
```
Notes:
- Bundle the HTML/asset files with `--add-data` so the server serves them from inside the EXE (resolve paths via `sys._MEIPASS` at runtime).
- `--collect-all` for **pywebview**, **websockets**, and **pywinpty** (winpty ships native binaries — verify the terminal works in the frozen build).
- **Do NOT** bundle `books\` (licensed) or user state (`saves\`, `data\`, `current-position.json`).
- pywebview on Windows uses the **Microsoft Edge WebView2 runtime** — present on current Win11; plan to ensure/deploy the WebView2 Evergreen runtime on older/managed PCs.

## Writable data + paths
- Make paths relative to the EXE location; but when installed to Program Files (read-only for standard users) **redirect writable data** — `saves\`, `data\`, `current-position.json`, logs — to a user-writable location, e.g. `C:\Users\Public\Lone Wolf Action Assistant\` (or `%LOCALAPPDATA%`). Auto-create + self-heal on launch.

## Licensed content (the book files) — NOT bundled
- Installer creates an **empty** books folder in the writable location, e.g. `C:\Users\Public\Lone Wolf Action Assistant\books\`. Ship NO book files.
- The app loads books from there. The existing install-books flow / library page should point at this folder. If no books are present, show the existing "install books" guidance rather than erroring.
- Keep books out of the repo and all build artifacts. Uninstall must leave user `books\` and `saves\` intact.

## Installer (Inno Setup `.iss`)
- Install the EXE (+ icon, + docs) to `C:\Program Files\Lone Wolf Action Assistant`.
- Create writable data + empty books folders under `C:\Users\Public\Lone Wolf Action Assistant\`.
- Desktop + Start-menu shortcuts (all-users/Public desktop). Requires admin. Silent install (`/VERYSILENT /NORESTART`). Add/Remove Programs uninstaller. Fixed App ID + version so newer installers upgrade in place. Uninstall leaves user books/saves intact.
- Compile with `ISCC.exe` → `Lone Wolf Action Assistant Setup.exe`.

## Test
Run the frozen EXE on a clean PC (no Python): window opens and looks identical to the web version, the embedded terminal works, books load from the user folder, saves persist to the writable location. Add a headless/self-test env-var path to smoke-test packaging.

## Deliverables
1. `saa_main.py` (server-threads + pywebview window) and any refactor of `app_server.py` / `ws_server.py` to run in-process.
2. Exact PyInstaller command/spec for these deps (excluding books).
3. Inno Setup `.iss` (empty books folder; leaves user data on uninstall).
4. Build + test instructions and a user note on adding book files.

## Gotchas / lessons (from a prior app packaged the same way)
- Self-contained means everything to RUN is inside the EXE — verify on a machine with no Python. A runtime failure of a native library means a missing `--collect-all`.
- Program Files is read-only for standard users → binaries there, data + content in Public/user profile.
- Unsigned EXEs trigger SmartScreen ("unknown publisher"): fine internally (More info → Run anyway), or code-sign / deploy via a trusted channel for fleet rollout.
- Don't run the app "as administrator" for everyday use — elevated windows block some behavior (e.g. drag-and-drop from Explorer).
