# Unified UI Acceptance Checklist — 3.7.1 Verification

**Date:** 2026-09-23
**Build:** 3.7.1 Internal Testing (exe FileVersion 3.7.1; installer compiled)
**Branch:** `unified-ui-native-surfaces`
**Checklist source:** [`docs/UNIFIED_UI_IMPLEMENTATION_GUIDE.md`](UNIFIED_UI_IMPLEMENTATION_GUIDE.md#acceptance-checklist)

## Method

- **Smoke suite:** `python -m unittest testing.test_saa_smoke` — **232 tests, OK** (automation, combat, saves, achievements, CLI, book import, release metadata).
- **Static inspection:** shipped markup/JS/CSS (`index.html`, `assistant.html`, `install-books.html`, `library.html`, `assets/js/lw-shell.js`, `assets/css/lw-ui-foundation.css`, `design-prototypes/`).
- **Live surfaces:** driven in a browser against an **isolated** `app_server` (scratch `LOCALAPPDATA`, real books via `LONEWOLF_SAA_BOOKS_DIR`) so the real campaign save was never touched. Fresh Book 1 campaign: END 20/20, CS 10, Gold 0.
- **Packaged build:** `--self-test` exit 0; Console CLI reached a clean prompt with live automation (Curing END 15→16) confirmed in the real desktop window.

## Results — all 10 pass

| # | Item | Result | Evidence |
|---|---|---|---|
| 1 | Visible book/section/vital data is live, not prototype samples | PASS | Campaign metrics rendered live END 20/20, CS 10, Gold 0 (server state), not the prototype's 24/32 · CS 14 · Gold 45 |
| 2 | Start Current Campaign opens the saved book and section in every view | PASS | Library `data-open-current-section`; Campaign/Reader `data-rail-current` → `syncBookToState`; `resume=1` links across surfaces |
| 3 | Campaign, Reader, Tools, Console alter one shared campaign state | PASS | A native choice routed §1 → §85 in `/api/state`; Reader then rendered §85; Console CLI applied Curing to the same save |
| 4 | Status names reflect real metadata (not interchangeable) | PASS | Status derived from `hasInstalledBookFiles` / `.testing` / `support` / `BookNumber`; Reading vs Testing distinct |
| 5 | Theme preferences apply consistently to all surfaces | PASS | All four production pages load `lw-appearance-early.js`; `--lw-ui-*` roles derive from base `--lw-*`, so a theme change propagates to Library, Campaign, Reader, Tools, Settings, Book Manager |
| 6 | Reader text and book choices remain authoritative and readable | PASS | Reader prose is verbatim from the raw Project Aon `sect85.htm`; dark, readable paper title |
| 7 | Automation, combat, saves, achievements, CLI, import APIs intact | PASS | 232 smoke tests OK; live CLI automation confirmed |
| 8 | No horizontal page overflow at desktop and phone widths | PASS | Page overflow 0 at 1280px and 390px across Campaign/Reader/Tools (tab bar / tool-nav scroll within their own containers by design) |
| 9 | Keyboard focus, button names, tooltips, disabled reasons, active-nav | PASS | `aria-current` on shell nav; 108 aria-label/title/disabled-reason instances in the assistant |
| 10 | Static design studies stay labeled and are never a second app | PASS | `design-prototypes/` labeled as studies/prototypes; no production file links to them |

## Caveats / scope

- **#7** — other-series rules paths (Book 5→6 handoff, Grand Master, New Order, permadeath, inventory limits, maps) are covered by the smoke suite, not manually re-driven in the UI; the live UI checks used a fresh Book 1 campaign.
- **#9** — the specified accessibility attributes are present; this was not a full screen-reader / focus-order audit.
- Live checks ran against an isolated scratch data directory; they do not reflect any specific saved campaign.
