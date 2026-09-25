# Running Lone Wolf Action Assistant in Docker

The desktop build is a native Windows window (pywebview/WebView2). The container
runs the **same app as a local web server** and you use it from a **browser** at
`http://localhost:8797/`. This is handy for updating on the fly without
rebuilding the installer.

## Requirements

- Docker + Docker Compose (Docker Desktop on Windows/macOS is fine).

## First run

```bash
docker compose up -d
```

Then open **http://localhost:8797/** in a browser.

Books and saves live in `./docker-data/` (created on first run) and persist
across restarts, rebuilds, and updates:

- **Books:** put your Project Aon book folders under
  `./docker-data/books/lw/<folder>/` (e.g. `./docker-data/books/lw/01fftd/`).
  Each folder needs at least `title.htm` and `sect1.htm`.
- **Saves / preferences:** written under
  `./docker-data/Lone Wolf Action Assistant/`.

> The container reads the app's rules data from the repo's tracked `data/`
> folder (via the bind-mounted source). `docker-data/` is only your books and
> saves, and is git-ignored.

## Update on the fly

The working tree is bind-mounted into the container, so:

- **Front-end changes** (`assistant.html`, `index.html`, `assets/…`) show up on
  a browser refresh — no restart needed.
- **Python changes** (`app_server.py`, `lonewolf_redux.py`, `ws_server.py`, …)
  take effect after:

  ```bash
  docker compose restart lonewolf
  ```

  No PyInstaller, no installer — just a fast restart.

## Everyday commands

```bash
docker compose up -d            # start (detached)
docker compose logs -f lonewolf # follow output
docker compose restart lonewolf # apply Python changes
docker compose down             # stop and remove the container
docker compose up -d --build    # rebuild the image (only needed if the
                                # runtime dependency in the Dockerfile changes)
```

## Ports

| Port | Purpose |
| --- | --- |
| 8797 | Web app (HTTP) — open this in a browser |
| 8798 | Console / CLI (WebSocket) |

## Notes and limits

- **This machine only.** The app enforces a localhost-only guard, so it is
  intended to be opened at `http://localhost:8797/` on the same machine. Reaching
  it from another device would require relaxing that guard into an allowlist.
- **No native window.** The pywebview desktop window is Windows-only and is not
  part of the container; the browser is the interface here.
- The container installs only the `websockets` runtime dependency; the
  Windows-only `pywebview`/`pywinpty` and the `pyinstaller` build tool are not
  installed.
