# Handoff: Frozen CLI terminal typing repair

**Status:** RESOLVED in 3.5.1. This document is retained as the investigation
record for the former WinPTY redraw defect.
**Author:** Claude (Opus 4.8) session, 2026-07-31. Handing off to Codex.
**Historical branch:** `hidden-cli-cheats-3.1.7` (unmerged exploratory work).

## Resolution

The packaged desktop app no longer launches its CLI through WinPTY. In 3.5.1,
the frozen desktop process starts its `--cli` child through inherited standard
pipes and marks the child to restore those pipe streams. The browser provides
the line editor: immediate local echo, Backspace, Enter, and a 100-command
Up/Down history. Source runs retain their ConPTY path.

This removes the WinPTY screen-scrape redraw stream that caused delayed echo,
incorrect Backspace rendering, and unusable arrow keys. Validation used the
real frozen executable both directly through pipes and through the real local
WebSocket bridge, with a prompt, `help`, and `exit` exchange completing cleanly.

---

## 1. Symptom (user's exact words)

In the embedded CLI terminal (the xterm.js panel), **typing is broken**:

- "typing is delayed — a character pressed doesn't show up till the next is pressed."
- "backspace doesn't work / re-adds deleted characters" and later "backspace is writing on the screen."
- "up/down arrows aren't working."
- "letters are doubled."
- "you have to press enter a few times till what you typed on the screen shows what you typed."
- The **commands themselves execute correctly** ("the cheats do work when typed out correctly") — it is purely the **input echo / line editing display** that is broken.

## 2. CRITICAL SCOPING FACT (confirmed by user at end of session)

**The typing is ALSO broken in 3.1.6, before the cheat menu landed.** So this is **NOT a regression** from the cheat/CLI work (`#24`, `#25`, cheat commits). It is a **long-standing defect in the frozen build's WinPTY ↔ xterm.js terminal path.** The typing "was always broken like this" in the packaged app.

Corollary: the original **from-source** web app (`LoneWolf_ActionAssistant_Redux`) worked fine because it runs the WebSocket bridge under **ConPTY** (see below). The defect is specific to the **frozen/packaged** build.

---

## 3. Architecture of the terminal path

The embedded terminal is xterm.js in the page, bridged over a WebSocket to a Windows pseudo-terminal running the game CLI.

| Piece | File | Notes |
|---|---|---|
| xterm.js terminal (client) | `assistant.html` (~line 2991, `startCliTerminal` / `cliTerminal = new Terminal({...})`) | xterm@5.3.0 + fit addon, loaded from CDN. Single `onData` handler sends keystrokes to the socket; incoming socket messages are `term.write()`-n. No local echo. |
| WebSocket bridge (server) | `ws_server.py` | `terminal_session_winpty()` spawns the CLI under a Windows PTY via `pywinpty` and pumps bytes both ways. Ports: HTTP 8797, WS 8798. |
| PTY backend selection | `ws_server.py:120` | `backend = winpty.Backend.WinPTY if getattr(sys,"frozen",False) else None`. **Frozen → WinPTY. From source → None → ConPTY** (pywinpty default on Win11). |
| Enter normalization | `ws_server.py:46` `normalize_winpty_input()` | Rewrites a lone `\r` → `\r\n` (see finding #4). |
| CLI child process | `saa_main.py:212` (`--cli` dispatch) → `lonewolf_redux.py:main()` | The frozen windowed EXE relaunches **itself** with `--cli` under the PTY. |
| Child stdio setup | `saa_main.py:57` `_prepare_cli_stdio()` | For the frozen build it does `AttachConsole(ATTACH_PARENT_PROCESS)` then opens `CONIN$`/`CONOUT$` (buffering=1). This is a **WinPTY-shaped** trick — it only works because WinPTY gives the child a real (hidden) parent console to attach to. |
| Game command loop | `lonewolf_redux.py:8739` (`run()`) | Plain `input("CHEAT> " if ... else "LW> ")`. All input is line-based (`input()`); no raw single-key input anywhere. |

Frozen packaging: PyInstaller `--windowed` (GUI subsystem) onedir build; the SAME exe is the GUI app and, via `--cli`, the terminal child. The CLI helper used to be a separate `saa_cli.py` exe but was **merged into `--cli` under WinPTY** (commit `73dfdb4`) specifically to avoid a popup console window in the windowed build.

---

## 4. What I established (with evidence)

All probes were run headlessly against the **real frozen EXE** (`dist/Lone Wolf Action Assistant/Lone Wolf Action Assistant.exe`) spawned via pywinpty, mirroring `ws_server.py`. Probe scripts were transient (in `%TEMP%`); the reusable test harness is in `testing/termcheck/` (see §7).

1. **The frozen windowed EXE cannot use ConPTY.** A GUI-subsystem process gets **no console** under a ConPTY pseudoconsole: `GetConsoleWindow()` → 0, `AttachConsole(ATTACH_PARENT_PROCESS)` → fails with err 6 (`ERROR_INVALID_HANDLE`), `GetStdHandle(STD_*)` → 0. So `_prepare_cli_stdio()`'s attach trick fails and the terminal is **dead** (0 bytes) under ConPTY. This is why the build was forced onto WinPTY. Verified with tiny windowed PyInstaller test exes.

2. **WinPTY works but uses a screen-scrape / line-repaint echo protocol.** For each keystroke WinPTY emits either a full-line repaint (`\x1b[?25l` hide, `\r`, rewrite whole line e.g. `LW> ab`, `\x1b[0K` erase-to-EOL, `\x1b[?25h` show) or an incremental `X\x1b[0K`. It also uses absolute column moves (`\x1b[<n>G`). ConPTY, by contrast, does simple char echo — which xterm renders trivially and correctly.

3. **At the BYTE level, WinPTY's echo and backspace are CORRECT and reasonably prompt.** Typing `abc` then Backspace produced `...LW> ab\x1b[0K...` (the `c` correctly removed and the line repainted). **Both `\x7f` (DEL) and `\x08` (BS) are handled identically and correctly by WinPTY** — so a DEL→BS input translation is NOT the fix (I tested it; no difference).

4. **`normalize_winpty_input` (`\r`→`\r\n`) is actually NEEDED, do not revert it.** I tested sending a lone `\r` vs `\r\n` for Enter into the frozen CLI: lone `\r` did **not** reliably submit the line / lagged; `\r\n` submits promptly. (This matches why commit `#24` added it.)

5. **The breakage is in how xterm.js RENDERS the WinPTY repaint stream — and it is independent of the xterm display options I tried.** I built a 4-panel side-by-side comparison page (real WinPTY + real frozen CLI) toggling `convertEol` (true/false) × `windowsPty:{backend:'winpty'}` (present/absent). The user reported that **all four eventually exhibit the same breakage** (initially one looked OK, but on further use "they ALL are doing the same thing"). So `convertEol` / `windowsPty` are **not** the lever.

6. **Leading hypothesis for the root cause:** xterm's screen model and WinPTY's screen model **diverge on line width / wrapping**, especially after the first multi-line command output. WinPTY repaints the prompt line by doing `\r` (CR to col 0 of the *current* row) + rewrite + `\x1b[0K`. That only lands correctly if xterm's current cursor row/width matches WinPTY's. The PTY is spawned at a fixed size (`ws_server.py`: `INIT_COLS=120, INIT_ROWS=30`) and xterm sends a resize on connect; if xterm's actual width ≠ PTY width, wide output (e.g. the `help` table, ~74 cols) wraps differently, xterm's row count drifts ahead of WinPTY's, and every subsequent line-repaint (including per-keystroke echo and backspace repaint) paints on the wrong row → "doesn't show until next char", "backspace writes on screen", "press enter several times". This is consistent with "first command fine, everything after broken." **NOTE: not fully proven** — I could not observe xterm's actual rendering headlessly (need a browser). Worth validating (see §6) but I believe the durable fix (below) sidesteps it entirely regardless.

7. **Plain pipes are not a drop-in transport.** Spawning the frozen EXE with `subprocess.PIPE` stdio produced **0 bytes**, because `_prepare_cli_stdio()` requires a console. A pipe-based transport needs the child stdio reworked too (see fix).

---

## 5. Implemented fix (highest confidence, durable)

**Move line editing + echo into the browser (local echo) and stop relying on the PTY's cooked-mode echo entirely.** Output rendering already works (command output like the `help` table displays fine) — only the *input/echo* path is broken. Local echo removes the entire class of WinPTY-screen-model-divergence bugs because the input line is drawn by our own JS, never by WinPTY's repaint stream. This approach was implemented in 3.5.1 using inherited standard pipes for the frozen child.

Concretely:

1. **Client (`assistant.html`):** Implement a small local line editor on the CLI xterm:
   - Maintain a JS input buffer for the current line.
   - `onData`: printable chars → append to buffer AND `term.write(ch)` (instant echo); Backspace (`\x7f`) → pop buffer + `term.write('\b \b')`; Enter (`\r`) → `term.write('\r\n')`, send `buffer + '\n'` to the socket, clear buffer; optionally Up/Down → command history (keep an array; the user explicitly wanted arrows to work); Ctrl+C → send `\x03`.
   - Do **not** echo bytes that the child echoes back (see step 3 — child must not echo).
   - Keep writing all socket→term output as today (that part is fine).
2. **Transport (`ws_server.py`):** Send the child **completed lines over a pipe** (no PTY), OR keep a PTY but put the child console in **no-echo, no-line-edit (raw) mode** so it doesn't emit the scrape-repaint stream. The pipe route is cleaner. Use a pipe transport on Windows for the frozen build.
3. **Child stdio (`saa_main.py:_prepare_cli_stdio`):** For the pipe transport, wire `sys.stdin/stdout/stderr` to the **inherited pipe fds** instead of `AttachConsole`+`CONOUT$`. When spawned with `STARTF_USESTDHANDLES` + inheritable pipe handles, even a GUI-subsystem child gets valid std handles; reconstruct Python streams via `msvcrt.open_osfhandle(GetStdHandle(...), ...)` → `os.fdopen(...)`. **Make stdout flush eagerly** (write-through / flush after each write) — with line buffering the no-newline prompt `"LW> "` won't flush. Verify with a tiny windowed PyInstaller exe first (the pattern is in the transient probes; recreate quickly).
4. **`lonewolf_redux.py`:** No logic change needed (all input is `input()` line-based), but ensure prompts flush (covered by step 3). Confirm nothing depends on TTY-only behavior.

Why this over the alternatives: it is deterministic, testable piece-by-piece, and the echo is instant by construction (no PTY in the echo path), so lag/backspace/arrow problems cannot recur.

## 5b. Alternatives (if you prefer not to rewrite the input path)

- **Console-subsystem CLI helper under ConPTY.** Split the CLI back out into a **separate console-subsystem EXE** (not `--windowed`) and have the windowed GUI app spawn it under **ConPTY**. A console app attached to a ConPTY pseudoconsole runs **headless (no popup window)** and gives clean, simple char echo that xterm renders correctly — this is effectively what the working from-source build does. Cost: reintroduces a second exe (previously merged away in `73dfdb4`) and a `.spec`/installer change. I could not fully validate ConPTY headlessly because ConPTY's init handshake (`\x1b[c` primary-DA request) expects the terminal to reply, which a real xterm does but my probe did not — so a live browser test is needed. **This is the closest to "just make it work like the source build."**
- **Width/wrap sync (smallest change, uncertain).** Make the PTY size exactly track xterm's cols and guarantee the resize is applied before any output, and confirm xterm width == PTY width at all times. If hypothesis §4.6 is correct this may fix it with no architecture change. Cheap to try but unproven, and doesn't address WinPTY's fragile repaint model in general.

---

## 6. How to reproduce / validate quickly

A standalone side-by-side test harness is checked in at **`testing/termcheck/`**:

- `testing/termcheck/bridge.py` — starts an HTTP server (127.0.0.1:**8899**) serving the compare page, and a WebSocket bridge (127.0.0.1:**8900**) that spawns the **real frozen EXE `--cli` under WinPTY** per connection.
- `testing/termcheck/termcheck.html` — four xterm panels (A/B/C/D) with different `convertEol`/`windowsPty` combos, all pointed at the bridge.

Run: `.venv\Scripts\python.exe testing\termcheck\bridge.py`, then open `http://127.0.0.1:8899/termcheck.html` in Edge/Chrome and type in each panel. (Requires the frozen EXE to exist in `dist/` and the app NOT running, so the exe isn't file-locked.) Extend this page to prototype the **local-echo** editor from §5.1 without rebuilding the whole app — that's the fastest way to prove the fix before touching the real app.

To rebuild the app after a fix: `.\build.ps1` (needs `uv`, ImageMagick `magick`, PyInstaller, Inno Setup — all present on this box). **The app must be closed** or PyInstaller's clean step fails with `PermissionError` on `_internal\clr_loader\...\ClrLoader.dll` (the running exe locks it).

---

## 7. Branch / commit state — and what to keep vs. reconsider

On `hidden-cli-cheats-3.1.7` (unpushed) I made two commits trying to fix this before we learned it's pre-3.1.6:

- **`79c6650`** — reverted commit `#25`'s `convertEol:false` back to `convertEol:true` (restores the LF→CRLF staircase fix). **Keep** — `convertEol:true` is correct.
- **`7816e60`** — plumbs the real PTY backend from the app to the page (`saa_main.py` URL param `ptyBackend` → `index.html` localStorage → `assistant.html`), applying `windowsPty:{backend:'winpty'}` only for the WinPTY build, `convertEol:true` always. This is *harmless and arguably correct*, but per finding §5 it is **not sufficient** — it does not fix the typing. Keep or fold into the real fix as you like.

These do **not** fix the reported problem. They also updated a smoke test (`testing/test_saa_smoke.py::FrozenCliTests`). Do **not** revert `normalize_winpty_input` (finding §4.4). The `dist/` EXE currently reflects `7816e60`.

Nothing is pushed; other machines/builds are unaffected.

---

## 8. One-paragraph summary for whoever picks this up

The packaged (frozen, `--windowed`) desktop app runs its CLI in a WinPTY pseudo-terminal because a GUI-subsystem exe can't attach to ConPTY (proven). WinPTY echoes typed input by screen-scraping its hidden console and emitting per-keystroke full-line repaints (`\r` + rewrite + erase-to-EOL + cursor hide/show + absolute column moves). At the byte level this is correct, but xterm.js renders it wrong — most likely because xterm's width/wrap/row state diverges from WinPTY's after the first wide multi-line output — producing one-keystroke-lagged echo, backspace that writes instead of deletes, dead arrows, and needing multiple Enters. No `convertEol`/`windowsPty` xterm option fixes it. This is a long-standing frozen-build defect (present in 3.1.6, pre-cheat-menu), not a regression. The recommended durable fix is to do local echo + line editing in the browser and feed the child completed lines over a pipe (requires reworking the child's `--cli` stdio in `saa_main.py` off the `AttachConsole`+`CONOUT$` path, and eager stdout flushing); the cleanest "make it like the working source build" alternative is a separate console-subsystem CLI helper exe driven under ConPTY (headless, clean echo). A live side-by-side test harness is in `testing/termcheck/`.
