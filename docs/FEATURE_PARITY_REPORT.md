# Three-Way Feature Parity Report

## Executive Summary

V3 is the canonical product because it retains the Redux browser experience
while adding the supported desktop shell, installer, managed user-data paths,
and legacy-save migration. V1 remains the authoritative rules reference for
Magnakai Books 6-8; its Book 6-8 setup, shops, and encounter exceptions have
been transferred into V3's data-driven campaign and standalone character setup. V2 and V3 share
the Redux Python core, but V3 has intentionally diverged in launch, storage,
packaging, save compatibility, later-book campaign handoffs, and the Magnakai
data overlays. V1 and V2 should be kept unchanged as references, not released
as parallel applications.

## Feature Matrix

| Feature | V1 PowerShell | V2 Redux web | V3 SAA canonical |
|---|---|---|---|
| Kai Books 1-5 campaign | ✅ | ✅ | ✅ |
| Magnakai Books 6-8 | ✅ source implementation | ⚠️ core/catalogue only | ✅ standalone and continuation campaign |
| Book readers/installable HTML | ✅ local `books` | ✅ web install page | ✅ managed import and desktop reader |
| Save/load and slots | ✅ PowerShell JSON | ✅ JSON slots/API | ✅ versioned V1/V2/V3 normalization and slots |
| Run difficulty | ✅ Story, Easy, Normal, Hard, Veteran | ❌ | ✅ five V1-compatible rulesets in new-run UI and CLI |
| Permadeath | ✅ optional except Story | ❌ | ✅ disables repeat/rewind recovery and records a dead run |
| Run integrity | ✅ signed PowerShell state | ❌ | ✅ V3 SHA-256 signing; legacy signatures are retained as unverified metadata |
| Achievement eligibility | ✅ difficulty-specific pools | ⚠️ achievements without V1 run gates | ✅ Story/Combat/Exploration/Challenge gates, including permadeath and integrity checks |
| Combat/RNT | ✅ ruleset modules | ✅ Redux CRT/RNT | ✅ Redux CRT/RNT plus 104 source-extracted Magnakai presets |
| CRT resolution mode | ✅ DataFile or ManualCRT | ⚠️ automatic CRT only | ✅ automatic DataFile CRT or manual loss recording, separately from UI play mode |
| Inventory, character sheet, action chart | ✅ console/web API | ✅ browser UI | ✅ browser UI and desktop shell |
| Book 6 dynamic resale | ✅ sections 76/98/275 | ❌ | ✅ live inventory sale UI |
| Book 5→6→7→8 handoff | ✅ | ⚠️ not release-complete | ✅ Magnakai carry-forward setup |
| Browser launch | ✅ PowerShell launches web stack | ✅ Python HTTP/WebSocket | ✅ retained browser surface under desktop host |
| Desktop packaging/installer | ⚠️ portable PowerShell release artifacts | ❌ | ➕ pywebview, PyInstaller, Inno Setup |
| Installed/user data separation | ❌ repo-local saves | ❌ repo-local saves | ➕ `runtime_paths.py` user-data root |
| Supported distribution | ❌ reference only | ❌ reference only | ✅ V3 only |

## Evidence and Divergence

- V1 loads discrete Magnakai Book 6-8 and combat modules from
  `lonewolf.ps1:44-48`. Its Book 6 DE Weaponskill option and source sale tables
  are implemented in `modules/rulesets/magnakai/book6.psm1:171-226` and
  `book6.psm1:375-496`; its encounter exceptions are in
  `modules/rulesets/magnakai/combat.psm1:201-1058`.
- V2 is a threaded HTTP server with repo-local save slots
  (`app_server.py:17-29`, `app_server.py:89-161`) and a Python launcher
  (`launch_lonewolf_redux.py:37`). It has no desktop host or installer path.
- V3 retains the same HTTP-facing Redux model but runs it inside pywebview
  (`saa_main.py:159-191`), resolves installer-safe resource and user locations
  (`runtime_paths.py:31`), and packages the one-folder build plus Inno installer
  (`build.ps1:41-67`, `LoneWolf_ActionAssistant.spec:19,65`).
- V3's generic combat schema is implemented in `lonewolf_redux.py:9232-9420`
  and supports conditional modifiers, temporary effects, enemy queues,
  restrictions, damage multipliers, and threshold routing. Source-derived
  Book 6-8 records are in `data/book6-section-flows.json`,
  `data/book7-section-flows.json`, and `data/book8-section-flows.json`.
- V3 exposes Books 6-8 in `BOOKS`; `create_magnakai_character_state` in
  `lonewolf_redux.py` applies V1-equivalent standalone rank, gold, fixed-item,
  and field-issue setup while the existing `prepare_book*_state` functions
  preserve campaign continuation.
- V3's V1-compatible run schema, legacy-signature migration, and signed payload
  are in `lonewolf_redux.py:977-1091`; gameplay loss, healing-cap, transition,
  and Sommerswerd rules are in `lonewolf_redux.py:3228-3264` and
  `lonewolf_redux.py:6420-6450`. The browser and embedded CLI select those run
  settings at `assistant.html:5141-5410` and `lonewolf_redux.py:7626-7640`.
- V3 records ManualCRT results through `lonewolf_redux.py:9232-9420` and
  `app_server.py:755-780`; it does not conflate that choice with the browser's
  existing Auto/Manual/CLI interaction modes.

## Regressions Closed and Remaining Scope

Closed in V3: V1-compatible Magnakai state and handoffs; V1/V2/V3 save
normalization; Book 6 fixed-price and dynamic shops; Books 6-8 printed combat
catalogues; key V1 encounter effects including temporary disarmament, immunity,
weapon restrictions, timed modifiers, damage multipliers, and threshold routes;
V1-equivalent lore-circle CS/END bonuses with legacy-save de-duplication and
Book 8 section 17's Fire-before-Light RNT precedence; and a data record for
every V1 Magnakai section-entry hook (86/56/36 for Books 6/7/8).

Also closed in V3: V1's five difficulty levels, Story/Easy endurance behavior,
Hard/Veteran healing and Sommerswerd restrictions, optional permadeath,
achievement-pool gating, V3-native tamper-evident saves, and selectable
DataFile/ManualCRT combat resolution. V3 explicitly preserves its separate
Auto/Manual/CLI interface choices.

Book handoff now preserves the reading order: the completion screen opens the
next book first, displays its Project Aon `tssf.htm` Story So Far page, and then
shows the setup choices. Temporary stored or safekept equipment is not restored
or transferred across that book boundary.

Remaining audit work is route-by-route fixture coverage for the few one-off source
mechanics outside normal combat and RNT handling. These are explicitly tracked in
`UNIFICATION_PLAN.md`; they do not block fresh or continued Books 6-8 setup.

## Recommendation

Ship and maintain only V3. Back-port nothing into V1/V2: preserve them as
read-only test/reference trees, keep their launchers out of release guidance,
and use V3's installer as the one distribution route. Complete the remaining
route fixtures and special target-point audit while retaining Books 6-8's public
standalone and continued starts, then retire the old launch paths from normal
user documentation.
