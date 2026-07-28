# Lone Wolf Action Assistant 3.1.4

Lone Wolf Action Assistant is a standalone Windows desktop play aid for the *Lone Wolf* gamebooks. It preserves the established HTML interface and embedded command-line terminal while packaging the application, Python runtime, and dependencies into one fast-launch application folder with a single normal EXE to start it.

Version: **3.1.4**

Current game support: **Book 1 playable release candidate; Books 2–5 playable helper/onboarding builds.**

## Book files are not included

This project does not redistribute Project Aon book HTML files. Players supply their own standard Project Aon HTML editions for personal use.

Books can be imported during installation or later from the app's **Install Books** page. The importer accepts Project Aon ZIP files and extracted book folders, validates them, and copies them into managed storage.

Expected folder names include:

```text
01fftd
02fotw
03tcok
04tcod
05sots
```

Each valid folder must contain at least `title.htm` and `sect1.htm`.

Project Aon license: <https://www.projectaon.org/en/Main/License>

## Desktop architecture

- `saa_main.py` starts the desktop window and internal services.
- `app_server.py` serves the existing UI and game API.
- `ws_server.py` bridges the embedded terminal through WinPTY.
- `lonewolf_redux.py` contains the game assistant and original CLI.
- `runtime_paths.py` separates packaged resources, shared books, and private player state.
- `book_manager.py` validates and imports user-supplied books.

The application starts at `index.html`. Internal ports default to 8797 and 8798, with automatic free-port fallback.

## Storage

- Application resources are bundled and read-only.
- Saves, preferences, logs, and current position are private to each player under `%LOCALAPPDATA%\Lone Wolf Action Assistant`.
- A current-user installation stores books under that user's Local AppData.
- An all-users installation stores shared books under `%PROGRAMDATA%\Lone Wolf Action Assistant`.

Uninstall does not intentionally remove books or player saves.

## Build

```powershell
.\build.ps1
```

Artifacts:

```text
dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant.exe
installer\output\Lone Wolf Action Assistant Setup.exe
```

See [Building](docs/BUILDING.md) for prerequisites, tests, and release checks.

## Player guide

See [User Guide](docs/USER_GUIDE.md) for installation, WebView2, book import, storage, upgrades, and the embedded terminal.

## Licensing and trademarks

Project Aon book files are not part of this repository or its build artifacts. See `NOTICE.md` and the Project Aon license before distributing anything derived from their material.
