# Action Report - 2026-08-07

## Executive Summary

This was the full unification and campaign-readiness workday for Lone Wolf
Action Assistant. The standalone SAA application was established as the one
supported product, absorbing the useful V1 PowerShell rules and V2 Redux
behavior while retaining SAA's desktop launcher, managed storage, installer,
and browser-based interface. The scope grew from Magnakai Books 6-8 into a
source-backed, internally tested Books 1-12 campaign, then concluded with the
3.4.7 installer release and a complete player wiki refresh.

The SAA repository received 22 commits today, from `877213a` through
`c608684`: 39 tracked files changed, with 29,927 insertions and 419 deletions.
The separately versioned wiki received 28 published Markdown pages in commit
`8a15acd`. No player save was opened, edited, or used for the automated test
runs.

## Scope And Delivery Decision

- Audited the three sibling implementations and wrote the source-backed
  [feature parity report](FEATURE_PARITY_REPORT.md) and
  [unification plan](UNIFICATION_PLAN.md).
- Chose SAA/V3 as the canonical product and release source. V1 PowerShell and
  V2 Redux remain read-only behavior/reference implementations, not parallel
  products to ship or maintain.
- Kept the desktop shell, PyInstaller build, Inno Setup installer, managed book
  import, user-data separation, save migration, and the Redux HTML interface.
- Brought V1-compatible rules into the Python/SAA implementation rather than
  embedding or launching PowerShell from the released application.

The original parity analysis, including the feature matrix and source evidence,
is retained in [FEATURE_PARITY_REPORT.md](FEATURE_PARITY_REPORT.md). The
design constraints, per-book definition of done, and original phased plan are
retained in [UNIFICATION_PLAN.md](UNIFICATION_PLAN.md).

## Player Experience And Feature Unification

### Core Run Rules

- Restored the five V1-style difficulty levels: Story, Easy, Normal, Hard, and
  Veteran.
- Added optional permadeath for eligible difficulties; Story remains a
  non-permadeath mode.
- Kept interaction style separate from rules difficulty: browser Auto, Manual,
  and embedded CLI remain interface choices, while DataFile and ManualCRT are
  combat-resolution choices.
- Added V3 save signing/integrity metadata and preserved V1/V2-shaped save
  migration support.
- Restored achievement eligibility gates for story, combat, exploration, and
  challenge runs, including difficulty, permadeath, and integrity conditions.

### Dashboard, Character Sheet, And Navigation

- Made the Game Modes state visible and changeable from the dashboard.
- Corrected Book 6+ character-sheet presentation so the current Magnakai
  Action Chart and Magnakai Disciplines are shown first, with legacy Kai
  Disciplines retained below for context.
- Updated known-discipline treatment so acquired disciplines are readable in
  the active theme.
- Preserved player-controlled inventory ordering and added the compact drag
  handle interaction requested for inventory rows.
- Ensured the Sommerswerd is ordered as the leading carried weapon when the
  character owns it.
- Corrected the Current/open-current-section action so it resumes the active
  campaign section instead of starting Book 1 at section 1.
- Reworked series navigation to follow the active series: Magnakai play shows
  the Magnakai book range, with unready books visibly disabled rather than
  cluttering the selection bar with finished Kai books.
- Updated the library and book-detail states so Books 6 and 7 are presented as
  testable books rather than stale "Coming" placeholders.

### Book Transitions And Entry Flow

- Reworked book completion so the next book opens first on its `Story So Far`
  reader page; its Action Chart/entry choices follow there rather than being
  presented at the end of the previous book without their source context.
- Added explanatory labels/tooltips for Book 6 entry choices, including the
  DE (Discipline Experience) options.
- Retained only the equipment the next book explicitly permits. Equipment does
  not automatically persist just because it appeared in a prior book.
- Where a transition requires freeing Backpack capacity, the player chooses
  what to leave behind; the application no longer clears the Backpack as a
  blanket operation.
- Implemented and tested later-Magnakai handoffs, completion states, and
  relevant story achievements through Book 12.

### Conditional Reader Guidance

- Added condition-aware reader route presentation for rules that depend on a
  discipline, carried item, or other modeled state.
- Continued to preserve player agency: inaccessible rules are surfaced through
  the app's condition knowledge rather than replacing the book text or forcing
  an unrelated route.
- Audited every section in Books 1-7 for wording, access conditions, direct
  effects, and automation opportunities. The source records are in
  [BOOK1_SECTION_AUDIT.md](BOOK1_SECTION_AUDIT.md) and
  [BOOK2_TO_7_SECTION_AUDIT.md](BOOK2_TO_7_SECTION_AUDIT.md).

## Book Coverage And Rule Automation

### Books 1-8

- Completed the Book 1 audit and automated the mandatory Kraan claw injury at
  section 320.
- Completed the Books 2-7 review and added verified rules including Book 2's
  poisoned-food replacement, Book 6 tournament handling, Book 7 bat-swarm
  damage, and Book 7 Lorestone recovery.
- Promoted Book 8 from preparation into the supported testing campaign and
  automated its clear mandatory injuries, meals, Fireseed effect, and recovery
  behavior.
- Completed the V1-to-SAA Magnakai port for Books 6-8: fresh setup, campaign
  continuation, disciplines/ranks/lore circles, shops and resale, item gains
  and losses, meals, Random Number Table rules, combat exceptions, terminal
  outcomes, achievements, and book-to-book setup.
- Completed Book 6-7 Random Number Table corrections, including the Book 6
  staged archery tournament final route. Removed stale entries and corrected
  source-inaccurate modifiers found during deep testing.
- Restored source-visible choices missing from Books 7 and 8 and corrected
  Book 8 section 287: the Vordak encounter routes to section 79 after both
  enemies are defeated and has no six-round deadline.

### Books 9-12

- Added official folder metadata, import validation, install-page links,
  reader navigation, saves, new-game setup, and campaign handoffs for Books
  9-12.
- Created a source-link and automation ledger for all 350 sections of each of
  Books 9-12. The baseline and review details live in
  [BOOK8_TO_12_READINESS_AUDIT.md](BOOK8_TO_12_READINESS_AUDIT.md) and
  [BOOK9_TO_12_COMPLETION_PLAN.md](BOOK9_TO_12_COMPLETION_PLAN.md).
- Added 117 source-verified direct mandatory effects across Books 9-12,
  including ENDURANCE losses, required meals, recovery, and the Book 12 Bow
  loss. Book 11 section 74 deliberately preserves the printed rule that
  Huntmastery cannot substitute for its required meal.
- Added the full printed combat baseline: 174 later-Magnakai encounters,
  source Combat Skill/ENDURANCE values, ordinary victory routes, and ordinary
  evade routes.
- Added all 116 clear Book 9-12 Random Number Table rules, including route
  ranges, rank/discipline/lore/weapon modifiers, recovery/loss effects,
  Book 10's selected weapon check, its optional dice game, and Book 12's Dose
  of Adgana behavior.
- Added source-verified item gains, losses, optional pickups, item-position
  handling, the Book 9 ordered pickpocket theft, Book 12 Crystal Explosive
  state, and later-book special-equipment effects.
- Added condition-aware routes, remaining stateful rules, final-section
  completion, and story achievements through the Book 12 ending.
- Added all 57 catalogued source-terminal deaths for Books 9-12 so a
  permadeath run consistently locks on death rather than leaving a terminal
  outcome reader-directed.

## Campaign And Regression Testing

### Automated Campaign Pass

The final deep test pass is recorded in
[DEEP_CAMPAIGN_TEST_REPORT.md](DEEP_CAMPAIGN_TEST_REPORT.md). It used temporary
save, state, and book workspaces and left player data untouched.

| Test area | Completed coverage |
| --- | --- |
| Full campaign | Book 1 through Book 12, ending at Book 12 section 350 |
| Difficulty | Story; Easy, Normal, Hard, and Veteran with permadeath both off and on |
| Book handoff | Normal campaign transitions and Book 6-12 Action Chart setup |
| Save/load | Isolated checkpoints, including Book 6 and Book 10 |
| Reader choices | 6,912 explicit player-choice links present in reader payloads |
| RNT | 315 one-step rules x 10 digits x 2 Action Chart profiles = 6,300 evaluations |
| Staged RNT | All 2,100 input sequences for Book 1 marsh, Book 5 guard surprise, and Book 6 tournament |
| Combat | 452 configured presets resolved in high-stat victory coverage |
| Alternate combat | 68 evades, 4 defeats, 8 wounded, 9 comparison, 3 survival, 11 timeout, 19 fast-win, 17 slow-win, 2 threshold, 2 roll-specific, and both Javek venom outcomes |
| Terminal deaths | 57 Books 9-12 deaths checked at every supported difficulty with permadeath enabled |

The final source test suite passed **178 of 178 tests**. The report retains the
one proper boundary of automated testing: human exploratory play remains useful
for reader clarity, puzzle answers, and intentionally discretionary choices
that cannot be safely inferred as deterministic rules.

### Defects Found And Corrected During The Pass

- Later-book source-terminal deaths could leave a permadeath run reader-led;
  terminal-death automation now closes those runs consistently.
- Explicit source choices were absent in selected Book 7 and Book 8 reader
  routes; those choices are restored.
- Book 6-7 had incomplete/stale RNT mappings and four incorrect modifiers;
  these were corrected against the installed source.
- Book 6 section 340's three-stage archery tournament did not finish its final
  route; it now does.
- Book 8 section 287 inherited an unrelated combat time limit; the false limit
  was removed and the correct post-victory destination was restored.

## Packaging, Release, And Distribution

- Prepared the 3.4.6 internal test build during the later-Magnakai automation
  phase, then produced the validated **3.4.7 Internal Testing** release after
  the deep campaign pass.
- Updated version metadata, changelog, build guide, user guide, installer
  script, and the desktop release checks for 3.4.7.
- Built the standalone application and Inno Setup installer from the canonical
  SAA repository. The release remains a single normal Windows application
  launch path, with no Python installation or browser server required for the
  player.
- Published tag `v3.4.7` at commit `9eed201` and the installer release on
  GitHub: <https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/releases/tag/v3.4.7>.
- Kept Project Aon books external to the repository, installer, and release
  assets; players import their own official HTML files through the managed
  install flow.

## Documentation And Wiki Publication

### Repository Documentation

- Rewrote the root [README](../README.md) for the current desktop release,
  Books 1-12 testing status, installation/import, play modes, handoffs,
  storage, and build process.
- Maintained the source audit reports, readiness ledger, completion plan,
  canonical-release guide, user guide, build guide, and deep campaign report.
- The README and user guide now describe SAA as the supported standalone
  application rather than directing players toward legacy V1/V2 launch paths.

### GitHub Wiki

- Migrated the current player-facing Redux wiki material into the SAA wiki and
  updated it for SAA 3.4.7.
- Published 28 Markdown pages in wiki commit `8a15acd`, including installation,
  modes, campaign/saves, combat, inventory, achievements, FAQ, command
  reference, book-support matrix, and release guidance.
- Added a central strategy-guide index, an achievement-completion guide, a
  full-campaign story-run guide, and Book 1-12 strategy-guide pages. The
  walkthrough-oriented organization was informed by the reviewed Lone Wolf
  walkthrough-category layout, without copying its prose.
- Checked every local wiki link after publication: **0 missing local links**.
- Published wiki: <https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/wiki>.

## Commit Ledger

| Commit | Delivered work |
| --- | --- |
| `877213a` | Initial V3 feature unification through Magnakai testing; parity report and plan |
| `aeccaba` | Magnakai Disciplines visible in Book 6 sheets |
| `14576fd` | Book 1 audit and Kraan injury automation |
| `857de00` | Books 2-7 section audit and verified automations |
| `f1bed0f` | Books 8-12 source preparation and test baseline |
| `b88343c` | Books 9-12 internal-testing campaign support |
| `6573921` | Books 9-12 direct mandatory effects |
| `20861cf` | Books 9-12 printed combat catalogue |
| `6be75ef` | Books 9-12 RNT rules |
| `e1471ac` | Books 9-12 audited item events |
| `bd88da7` | Later-Magnakai special equipment rules |
| `33e8475` | Later-Magnakai RNT completion |
| `8b003b9` | Condition-aware reader routes |
| `9aca404` | Book 9 ordered pickpocket theft |
| `6c186c5` | Remaining later-Magnakai stateful rules |
| `5c5dce7` | Later-Magnakai campaign handoffs |
| `4446bae` | Player-selected Backpack carry-over choices |
| `6f46863` | Magnakai campaign verification |
| `4584130` | Magnakai endings and guard-combat routes |
| `8c596d1` | 3.4.6 internal test-build preparation |
| `9eed201` | 3.4.7 deep campaign test pass and release corrections |
| `c608684` | Player README refresh for standalone campaign support |

The wiki publication is separate from the application repository: `8a15acd`
published the complete Books 1-12 player wiki.

## Verification And Current State

- SAA application repository is clean on `main` and pushed through
  `c608684`.
- SAA wiki repository is clean on `master` and pushed through `8a15acd`.
- `v3.4.7` resolves to `9eed201`.
- The targeted release-metadata regression passed after the README refresh.
- The local wiki link check reported zero missing links.
- The current published product is **3.4.7 Internal Testing**, not a claim of
  final public-completion status.

## Remaining Work

Nothing blocks the internal-testing release or Books 1-12 campaign play. The
remaining work is ongoing quality work, not an uncompleted feature handoff:

- Continue human exploratory play across alternative reader/puzzle routes for
  clarity, wording, and player-choice ergonomics.
- Add narrowly targeted regression fixtures whenever a previously unmodeled
  source exception is found.
- Repeat installed-reader browser checks and Auto/Manual/CLI smoke checks in a
  browser-capable release environment when one is available.
- Keep V1 and V2 as source references until their remaining historical value is
  exhausted; do not revive them as separately distributed applications.

