# Handoff — v3.1.4 hardening + Grey Star residue removal

Prepared for the next agent (Codex) to pick up. Everything below is **done in
source and committed** on branch `harden-save-and-api-3.1.4`. The package now
builds and the collapsed terminal has been proven in the frozen app. The
installed-app smoke test and release/publish steps remain.

## State at handoff

- Branch: `harden-save-and-api-3.1.4` (branched from `main`; pushed to origin).
- Version bumped to **3.1.4** everywhere (README, docs, installer `.iss`,
  `version_info.txt`, CHANGELOG). `version_info_cli.txt` was deleted (see CLI note).
- Tests: `python -m unittest testing.test_saa_smoke` → **36/36 pass**.
- Packaged self-test from source: `python saa_main.py --self-test` → OK.
- Git identity for this repo is set `--local` to Daniel Watson <o0cynix0o@gmail.com>.
- The 3.1.4 application EXE and installer build successfully.
- The real packaged UI terminal has been validated end-to-end: Index → Open
  Reader → Assistant menu → CLI, `help`, `sheet`, `quit`, and Reconnect all
  work. The CLI process is the same main EXE with `--cli`, owns no visible
  window, and does not start `WindowsTerminal.exe` or `wt.exe`.

## What changed this session (commit-by-commit)

1. `5fe1164` Save durability (atomic temp-file + `os.replace`), graceful
   corrupt-save load, save/load path confinement to the saves folder, and a
   localhost `Host` + same-origin `Origin` + `application/json` gate on the HTTP API.
2. `9363213` WebSocket terminal bridge rejects cross-origin handshakes; CRT
   loader/lookup degrade gracefully instead of `KeyError`; Kai Disciplines are
   deduped/validated on load.
3. `630ba48` `as_list()` now returns a fresh list (no aliasing of stored state).
4. `257a537` **Removed the dead Grey Star Willpower / Lesser+Higher Magicks /
   Magical Staff system** (never used by any Lone Wolf book — 0 hits in
   `data/*.json`). This also **fixed a latent crash**: the Book-2 Karmo Potion
   read `WillpowerCurrent`, which is popped off Lone Wolf characters → `KeyError`.
   Karmo now doubles Endurance only, matching the rules.
5. `a8d039d` **Removed the `Nobles` currency** — it was a pure 1:1 mirror of
   `GoldCrowns`. The load-time migration for older saves that stored gold under
   `Nobles` is **kept** (see `normalize_state`). Behavior is unchanged.
6. `73dfdb4` **Collapsed the separate `CLI.exe` into the main EXE.** The embedded
   terminal now relaunches the same windowed binary with `--cli` under WinPTY
   (`ws_server.build_command`). Deleted `saa_cli.py` and `version_info_cli.txt`;
   removed the extra PyInstaller step from `build.ps1`.
7. `aea78a3` Commented the intentional combat route order; deduped the four
   identical `apply_bookN_gold_roll` funcs into `apply_book_gold_roll` (per-book
   names kept as aliases — no caller changes); changelog.
8. `8d9749b` Fixed the frozen single-EXE CLI discovered during packaged
   validation. The windowed PyInstaller process now attaches to WinPTY's parent
   console before reopening `CONIN$`/`CONOUT$`; failure exits cleanly instead of
   displaying an unhandled-exception dialog. Added frozen CLI regression tests.
   GitHub issue #12 tracks the defect and remains open until the fix reaches
   `main`.

## Decisions already made — do NOT silently reverse these

- **Combat tie-break:** when Lone Wolf and the enemy both reach 0 ENDURANCE in
  the same round, it resolves as Lone Wolf's **defeat**, not a victory. This is
  intentional and now documented in `route_after_combat_round`.
- **Nobles removal is behavior-neutral** and the legacy save-migration was kept
  on purpose. Do not remove that migration or you will zero out old saves' gold.
- **Single EXE:** there is intentionally no separate CLI executable anymore.

## What Codex should do next

1. **Smoke-test** the installed app: window opens, books import, saves persist to
   `%LOCALAPPDATA%\Lone Wolf Action Assistant`, combat runs, no console tab flashes.
2. **Merge / release:** open a PR from `harden-save-and-api-3.1.4` into `main`,
   or fast-forward `main`; then package and publish.
3. **Release checklist note:** `docs/PUBLIC_RELEASE_CHECKLIST.md`, referenced
   in the original handoff, does not exist in this repository, either remote
   branch, or reachable history. The tracked release checks are under
   **Release checks** in `docs/BUILDING.md`; confirm that list before publishing.

## Still open (not done — by design)

These numbers are internal audit item labels from the original review, **not
current GitHub issue numbers**.

- **#10 God-class / module split** (`lonewolf_redux.py` is ~8.4k lines with a
  ~6k-line class mixing engine/persistence/CLI/data). Deferred to its own
  dedicated, well-tested pass — too risky to bundle with the above.
- **#2** The `shutdown` API action is unauthenticated beyond the same-origin
  gate (now effectively neutralized). Optional to harden further.
- **#13** The smoke tests string-match against `assistant.html` (brittle by
  design — they are tripwires for accidental UI-contract changes).

## Verify quickly

```powershell
python -m unittest testing.test_saa_smoke      # 36 pass
python saa_main.py --self-test                 # {"ok": true, ...}
```
