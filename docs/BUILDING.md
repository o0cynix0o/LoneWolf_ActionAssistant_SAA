# Building Lone Wolf Action Assistant 3.4.6 Internal Testing

## Requirements

- Windows 10 or Windows 11, x64
- `uv` (the build script creates an isolated CPython 3.13 environment)
- ImageMagick (`magick.exe`)
- Inno Setup 6 (`ISCC.exe`)
- Internet access when downloading Python dependencies and the WebView2 Evergreen Bootstrapper

Project Aon book files are neither required nor permitted in the source tree or build artifacts.

## Complete build

Open PowerShell in the repository root:

```powershell
.\build.ps1
```

The script:

1. Creates/reuses `.venv` with CPython 3.13 and installs `requirements.txt`.
2. Regenerates the multi-resolution `logo.ico`.
3. Builds the fast-launch one-folder application with `LoneWolf_ActionAssistant.spec`.
4. Runs the frozen service/resource self-test.
5. Downloads Microsoft's WebView2 Evergreen Bootstrapper when needed.
6. Compiles the Inno Setup installer.

Outputs:

```text
dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant.exe
installer\output\Lone Wolf Action Assistant Setup.exe
```

To build only the application:

```powershell
.\build.ps1 -SkipInstaller
```

## Tests

Run source tests:

```powershell
$env:PYTHONPATH = $PWD
python -m unittest discover -s testing -v
python .\saa_main.py --self-test
```

Run the frozen self-test:

```powershell
& '.\dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant.exe' --self-test
if ($LASTEXITCODE -ne 0) { throw 'Frozen self-test failed.' }
```

The embedded CLI must also be tested through WinPTY in the frozen build. A normal subprocess is not equivalent because the packaged desktop executable uses a console-capable bootloader that only exposes its CLI streams when attached to a terminal.

## Storage model

- Read-only application resources: bundled alongside the application EXE.
- Per-player saves, preferences, current position, and logs: `%LOCALAPPDATA%\Lone Wolf Action Assistant`.
- Current-user books: `%LOCALAPPDATA%\Lone Wolf Action Assistant\books`.
- All-users books: `%PROGRAMDATA%\Lone Wolf Action Assistant\books`.

The installer records the selected books location in the current installation scope's registry. The app also accepts `LONEWOLF_SAA_BOOKS_DIR` for controlled testing or portable overrides.

## Release checks

Before distributing:

1. Confirm `git status` contains no `books`, saves, logs, or WebView2 bootstrapper.
2. Run all source tests and the frozen self-test.
3. Confirm the frozen desktop window opens at the home page.
4. Confirm the frozen embedded terminal accepts input and exits cleanly.
5. Test current-user installation without elevation.
6. Test all-users installation with elevation.
7. Test missing-WebView2 behavior.
8. Test folder and ZIP book imports.
9. Test upgrade over the previous 3.x installer.
10. Confirm uninstall leaves books and per-user saves intact.
11. Test the final installer on a clean Windows machine without Python.
