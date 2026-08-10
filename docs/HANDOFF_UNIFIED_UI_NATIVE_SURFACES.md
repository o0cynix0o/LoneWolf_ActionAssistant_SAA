# Handoff: Native Unified-UI Surfaces + Console Cheat-Session Fix

**Branch:** `unified-ui-native-surfaces` (branched from `main`)
**State:** committed locally in `6002ba0`, `78cce6a`, and `8aa43de`; the working tree was clean when this handoff was refreshed. The branch is ahead of `main` but has no remote tracking branch, so it has not been pushed, merged, or released.
**Author context:** continued from the Unified UI redesign. See `docs/UNIFIED_UI_IMPLEMENTATION_GUIDE.md` and `docs/UI_REDESIGN_CONTRACT.md` for the visual contract, and `design-prototypes/{campaign-desk,reader-first,tools,library-command}.html` for the target layouts.

---

## Why this work happened

The earlier "unified UI" pass **reskinned the legacy assistant DOM per surface with CSS** but never rebuilt the play surfaces to their prototypes. Concretely, `assistant.html`'s single `<main>` was the old three-pane assistant (reader `<iframe>` + dense tools rail) with a `lw-campaign-desk` class bolted on. Every prototype signature element (native story panel, metric row, tab bar, choice buttons, "At a glance" rail, Reader paper surface, Tools nav/quick-roll/active-tool) was **absent**. Campaign was just the surface the user happened to screenshot; Reader/Tools/Console had the same root cause.

This branch rebuilds all four play surfaces (Campaign / Reader / Tools / Console) as **native** layouts driven by live `app.state`, reusing the existing engine (no game-logic/save/API changes). It also fixes a **pre-existing** Console crash unrelated to the UI (cheat-session token handoff).

---

## Files changed (6)

| File | Change |
| --- | --- |
| `assistant.html` | New `<main>` markup + a native-surface JS module + `render()` routing. |
| `assets/css/lw-campaign.css` | Shared native base + Campaign Desk layout (rewritten). |
| `assets/css/lw-reader-tools.css` | Reader First + Tools/Console layout (rewritten). |
| `cheat_session.py` | Console crash-proofing + fresh-token file support. |
| `saa_main.py` | Publishes live cheat url+token to a file for the CLI. |
| `docs/HANDOFF_UNIFIED_UI_NATIVE_SURFACES.md` | This implementation and verification handoff. |

---

## UI implementation (assistant.html)

**Architecture decision:** one shared workspace DOM, surface fixed per page load via `?surface=` (set by `assets/js/lw-shell.js boot()`). The native module owns rendering; the legacy card/drag layer (`decorateInterfaceCards`) and top-dashboard are **bypassed** on native surfaces.

- **Markup:** `<main class="workspace lw-native" id="workspace">` contains sibling surface roots — `#campaignRail` + `#campaignMain` (`#campaignHead`/`#campaignMetrics`/`#campaignTabbar`/`#storyPanel`/`#campaignToolMount`) + `#campaignGlance`; `#readerRoot` (`#readerHead`/`#readerSurface`) + `#readerCompanion`; `#toolsRoot` (`#toolsHead`/`#toolsNavigation`/`#toolsSummary`/`#toolsQuickRoll`/`#toolsActiveMount`). All legacy singleton IDs are retained (hidden in `.lw-legacy-hidden`) for null-safety of legacy renderers. `#book-frame` now lives inside `#frontMatterOverlay` (used only for Map / Story-so-far).
- **Native module** (search `NATIVE PROTOTYPE SURFACES` in `assistant.html`): key functions —
  - `parseSectionDocument(doc, bookNumber)` / `fetchSection` / `renderStoryInto(target, variant)` — fetch the real Project Aon `sectN.htm` (via existing `bookUrl`), parse `.maintext`, render prose + illustrations **verbatim**, lift `p.choice` into choice buttons. Choices dispatch the existing `action({action:'route'|'set_position'})` — same engine as before.
  - `renderCampaignSurface` / `renderReaderSurface` / `renderToolsSurface(f)` and helpers (`renderCampaignHead/Metrics/Tabbar/Glance`, `renderReaderHead/CompanionNative`, `renderToolsHead/Summary/QuickRoll`).
  - `renderNativeSurface(flags)` — the orchestrator called from `render()`. It **asserts `body.lw-shell-assistant lw-surface-<surface>` itself** (defensive against the deferred shell script racing the first render). Handles death/book-setup/book-complete as a full-width takeover (`body.lw-native-takeover`, `#view` re-homed to `#workspace`).
  - `mountView(target)` re-homes the `#view` singleton into the active surface's mount (Campaign non-story tab → `#campaignToolMount`; Tools → `#toolsActiveMount`). Tool tabs reuse `renderSheet/renderInventory/renderCombat/renderNotes` unchanged.
  - Event delegation (bound once via `window.__lwNativeBound`) handles `data-story-route`/`data-story-jump`, `data-campaign-tab`, `data-reader-prev/next`, `data-open-map`, `data-open-tssf`, `data-frontmatter-close`. Existing handlers still own `data-roll`, `data-save-current`, `data-rail-current/book`, `data-view`.
- **`render()`** was modified to route native surfaces through `renderNativeSurface(...)` and skip the legacy quick-panel/tabs/`decorateInterfaceCards` path (kept as a fallback for non-native surfaces only).

## CSS

Both files target the new classes using `--lw-ui-*` role tokens (theme-safe). Notable rules with rationale:
- `body.lw-shell-assistant { overflow-y:auto; height:auto }` + `.workspace.lw-native { overflow:visible; height:auto }` — **overrides the legacy `body/​.workspace { height:100vh; overflow:hidden }`** so the native document scrolls (legacy scrolled inside panes). Console keeps a tall terminal via `.lw-console-active .lw-active-tool { min-height:72vh }`.
- `.lw-campaign-main { grid-template-columns: minmax(0,1fr) }` — stops the implicit grid track from sizing to max-content and overflowing the column.
- `.lw-native h1,h2,h3 { white-space:normal !important; text-transform:none !important }` — overrides the legacy `h1 { white-space:nowrap; text-transform:uppercase }` so titles wrap and stay prototype mixed-case.
- `.lw-frontmatter-overlay` uses `display:none` + `:not([hidden]){display:grid}` + `[hidden]{display:none !important}` — **the original bug** was `display:grid` on the class, which overrode the `hidden` attribute and left the overlay covering every surface with a dead Close button.
- `.lw-reading-surface h2 { color:#182c30 !important }` — dark, readable on the cream paper (was washed-out accent).
- Tools: `.lw-tools-content { align-items:stretch }` + `.lw-quick-roll` has no fixed height, so Quick Roll matches the summary panel height.
- Breakpoints: Campaign collapses the rail ~1180px and stacks ~820px; Tools nav becomes a scroll strip ~850px.

---

## Console cheat-session fix (backend — separate concern)

**Symptom:** opening Console crashed the CLI with `HTTP Error 403: Forbidden` (`saa_main → lonewolf_redux.main → cheat_session.provider_from_environment → RemoteCheatClient.refresh → urllib`).

**Root cause:** `app_server.CHEAT_SESSION` mints a fresh token per server start; `saa_main.py` publishes it via env; `app_server.py:~982` 403s any non-matching token. The CLI worker was sending a **stale token** (restart/zombie handoff), and `RemoteCheatClient.__init__` calling `refresh()` made that 403 **fatal**.

**Fix:**
- `cheat_session.py`: `RemoteCheatClient._request` now catches all network/HTTP errors and degrades to last-known status (never raises) — a cheat-sync hiccup can never kill the CLI. `provider_from_environment` prefers a fresh live-token **file** (`LONEWOLF_SAA_CHEAT_FILE`) over the env snapshot and falls back to a local `CheatSession()`.
- `saa_main.py` `run_desktop`: writes `{url, token}` to `%LOCALAPPDATA%\Lone Wolf Action Assistant\data\cheat-session.json` on startup, sets `LONEWOLF_SAA_CHEAT_FILE`, and deletes it on exit. The CLI reads the current server's token even if env is stale.

Verified by `CheatSessionTests.test_remote_client_survives_a_stale_token_and_prefers_live_token_file`: a wrong token does not crash the remote client, and a current token file takes precedence over a stale environment token.

---

## Build / run reality (IMPORTANT)

The app the user runs is the **PyInstaller onedir build** at `dist\Lone Wolf Action Assistant\Lone Wolf Action Assistant.exe`. It serves **files baked into `_internal/` at build time** — editing repo source does **not** change an already-built exe. Every source change (UI or Python) requires a rebuild.

- Rebuild: `powershell -ExecutionPolicy Bypass -File build.ps1` (add `-SkipInstaller -SkipWebView2Download` for a faster exe-only build). **Close the running app first** — PyInstaller can't overwrite the locked `.exe`.
- Last rebuild here (exit 0) produced the exe + `installer\output\Lone Wolf Action Assistant Setup.exe`, both containing this branch's changes (bundled `assistant.html` = 404,995 bytes with native code present).

---

## Verification status

- **Done (source and automated verification):** all four native surface roots and their renderer routing are covered by the smoke suite; Campaign uses the real story mount, choices route through `action()`, and the Console stale-token regression has an automated test. The source build and installer created on 2026-08-10 contain the native `assistant.html` module.
- **Not done — needs the GUI / real save:** end-to-end check in the built desktop exe against the **actual Book 6 §219 Magnakai save** (the scratch server was Book 1 §1); Console open in the packaged exe post-rebuild; screenshots into `docs/ui-checkpoints/`. The in-app browser used for verification reports `innerWidth 0` and won't composite, so pixel/screenshot capture must be done in the real app.

## Remaining work for Codex

1. Launch the freshly built exe; confirm Campaign/Reader/Tools/Console at the live Book 6 §219 save; capture fresh screenshots to `docs/ui-checkpoints/`.
2. Run the acceptance checklist in `docs/UNIFIED_UI_IMPLEMENTATION_GUIDE.md` across Book 1, a Book 5→6 handoff, Grand Master, New Order, permadeath, save/load, import, combat, achievements.
3. Commit the verification updates, push `unified-ui-native-surfaces`, merge it into `main`, and publish only after the desktop checks pass.
4. Confirm `dist/` and `installer/output/` are not staged.

## Known caveats

- `!important` is used to beat legacy internal `<style>` rules for heading `white-space`/`text-transform` and the reader `h2` color; keep if touching headings.
- Native surfaces intentionally **do not** call `decorateInterfaceCards` (no draggable cards) — don't reintroduce it for these surfaces.
- `#view` is a single re-homed node; only one native surface is active per page load, so this is safe. Death/setup/complete screens still write to `#view` and are shown full-width via `lw-native-takeover`.
- Reader Previous/Next are best-effort (history-based / single-choice); not a full navigation model.
