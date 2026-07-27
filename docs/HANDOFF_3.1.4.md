# Handoff — v3.1.4 hardening + Grey Star residue removal

Prepared for the next agent (Codex) to pick up. The hardening work and frozen
terminal fix through GitHub issue #12 are committed on branch
`harden-save-and-api-3.1.4`, and that package was proven in the frozen app.
Approved follow-up fixes for GitHub issues #13 through #15 are now present in
source and the rebuilt 3.1.4 artifacts, committed as `3cd9a04` and `572bb35`.
Their source and frozen validation are complete. The installed-app smoke test
is now complete for the current-user path. The remaining platform-matrix checks
and release/publish steps are listed below.

## State at handoff

- Branch: `harden-save-and-api-3.1.4` (branched from `main`; pushed to origin).
- Version bumped to **3.1.4** everywhere (README, docs, installer `.iss`,
  `version_info.txt`, CHANGELOG). `version_info_cli.txt` was deleted (see CLI note).
- Current source validation: `python -m unittest testing.test_saa_smoke` →
  **41/41 pass** and `python saa_main.py --self-test` → OK.
- Git identity for this repo is set `--local` to Daniel Watson <o0cynix0o@gmail.com>.
- The canonical 3.1.4 application EXE and installer were rebuilt successfully
  with the issue #12–#15 fixes.
- Frozen CLI validation at 51 terminal columns rendered 50-character panels.
  The `inventory` command completed through the final `LW>` prompt,
  `scrollOnUserInput` kept the latest output in view, and the CLI worker owned
  no separate terminal window.
- Frozen UI validation measured Small cards at exactly 220 pixels with zero
  horizontal overflow, and Drop Item rows wrapped cleanly within the card.
- The approved wolf-mask sigil is shared temporarily by Kai, Magnakai, Grand
  Master, and New Order. Frozen WebView2 validation confirmed the same mask for
  books 1, 6, 13, and 21; it recolors with Kai Gold and Kalte Frost and remains
  centered without overflow at desktop, minimum-window, and mobile widths.
- The 26KB runtime mask is packaged and verified by the frozen self-test. The
  original generated design master and its provenance note remain under
  `design-assets` and are intentionally excluded from the runtime.
- The canonical rebuilt executable is
  `dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant.exe`. The older
  pre-fix executable that once existed directly under `dist` has been removed;
  do not recreate, validate, or release a bare EXE because the one-folder build
  requires its `_internal` directory.

## Installed-app validation — 2026-07-27

The 3.1.4 installer was installed in current-user mode to an isolated temporary
directory, with player data and managed books redirected to isolated paths.
The installed executable had the same SHA-256 as the canonical frozen build.

- The installed desktop window opened at `index.html` and its local HTTP
  service became ready.
- Both an extracted-folder import and a standard
  `en/xhtml/lw/<book-folder>` ZIP import completed successfully from synthetic
  book fixtures.
- A Book 1 character was created, a real Combat Results Table round defeated a
  test enemy, and the campaign was explicitly saved under the isolated
  `%LOCALAPPDATA%\Lone Wolf Action Assistant\saves` tree.
- After a graceful close and restart, the installed app restored the same
  character, combat history, save path, and imported-book status.
- The in-app frozen CLI connected, accepted `inventory`, rendered its Inventory
  panel, and returned to the `LW>` prompt. No new Windows Terminal process was
  created.
- Silent uninstall succeeded, removed its registration and shortcuts, and left
  the isolated imported books and player save intact. The entire test sandbox
  was then moved to the Recycle Bin.

This machine is not elevated and already has WebView2 and Python installed, so
the all-users/elevation path, genuinely missing-WebView2 path, upgrade from an
installed 3.1.3 package, and clean-Windows-without-Python path still require
separate environment coverage.

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
   GitHub issue #12 records the defect.
9. `3cd9a04` Changed Small dashboard cards to a readable 220-pixel compact
   width, wrapped Drop Item rows inside Small cards, followed live terminal
   input without disrupting deliberate scrollback, and made CLI text panels
   shrink to the current terminal width. Added regression coverage for GitHub
   issues #13 and #14.
10. `572bb35` Replaced the four temporary series-divider symbols with the
    approved angular wolf-mask sigil. All four series share the theme-aware mark
    for now; the original generated source is retained outside runtime assets,
    and the self-test now verifies the packaged mask over HTTP. GitHub issue #15
    records the change.

## Approved follow-ups validated and committed

- **GitHub issue #13:** Small dashboard cards now use a 220-pixel compact width.
  Drop Item rows can wrap within Small cards instead of overflowing or clipping
  their controls.
- **GitHub issue #14:** The embedded terminal returns to the latest output when
  the player types. CLI text panels derive their width from the current terminal
  and shrink when space is limited, while retaining the established maximum
  width on larger terminals.
- **GitHub issue #15:** Kai, Magnakai, Grand Master, and New Order temporarily
  share the approved wolf-mask sigil. Series-specific replacements are deferred
  until the project owner revisits the design.
- Source smoke tests, the source self-test, the rebuilt artifacts, and the
  focused frozen UI/CLI checks all pass.

## Decisions already made — do NOT silently reverse these

- **Combat tie-break:** when Lone Wolf and the enemy both reach 0 ENDURANCE in
  the same round, it resolves as Lone Wolf's **defeat**, not a victory. This is
  intentional and now documented in `route_after_combat_round`.
- **Nobles removal is behavior-neutral** and the legacy save-migration was kept
  on purpose. Do not remove that migration or you will zero out old saves' gold.
- **Single EXE:** there is intentionally no separate CLI executable anymore.
- **Shared series sigil:** do not reintroduce the rejected four-symbol set.
  Keep the approved wolf mask on all four series until the project owner asks
  to resume individual series designs.

## What Codex should do next

1. Complete the remaining platform-matrix checks called out under
   **Installed-app validation** when those environments are available.
2. **Merge / release:** open a PR from `harden-save-and-api-3.1.4` into `main`,
   or fast-forward `main`; then package and publish.
3. **Release checklist note:** `docs/PUBLIC_RELEASE_CHECKLIST.md`, referenced
   in the original handoff, does not exist in this repository, either remote
   branch, or reachable history. The tracked release checks are under
   **Release checks** in `docs/BUILDING.md`; confirm that list before publishing.

## Still open (not done — by design)

These numbers are internal audit item labels from the original review, **not
current GitHub issue numbers** and not the GitHub issues #12–#15 described
above.

- **#10 God-class / module split** (`lonewolf_redux.py` is ~8.4k lines with a
  ~6k-line class mixing engine/persistence/CLI/data). Deferred to its own
  dedicated, well-tested pass — too risky to bundle with the above.
- **#2** The `shutdown` API action is unauthenticated beyond the same-origin
  gate (now effectively neutralized). Optional to harden further.
- **#13** The smoke tests string-match against `assistant.html` (brittle by
  design — they are tripwires for accidental UI-contract changes).

## Verify quickly

```powershell
python -m unittest testing.test_saa_smoke      # 41 pass
python saa_main.py --self-test                 # {"ok": true, ...}
```
