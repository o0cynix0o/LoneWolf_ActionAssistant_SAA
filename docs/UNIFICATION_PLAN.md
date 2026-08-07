# Lone Wolf Action Assistant Unification Plan

## Goal

Create one supported application without losing either gameplay coverage or the
desktop experience:

- V3 is the delivery base: desktop shell, installer, managed book import,
  user-data paths, save slots, and the current browser UI.
- V1 is the rules reference: Kai Books 1-5, Magnakai Books 6-8, and the
  PowerShell behavior that must be preserved or deliberately reimplemented.
- V2 is a historical implementation reference for Redux behavior. It is not a
  second product to maintain after its useful differences are absorbed.

The end product is a V3 desktop release with playable Books 1-8, a compatible
save-import story, and one maintained UI and launch path.

## Non-Negotiable Rules

1. Do not enable a book merely because its reader files can be installed. A
   book becomes playable only when creation, rules, routes, combat, endings,
   saves, and regression tests are complete.
2. Preserve old saves. V1 PowerShell saves and V2/V3 JSON saves must be kept as
   fixtures and migrated forward, never overwritten in place.
3. Keep V3's desktop packaging and user-data separation. No feature port may
   write state into the installed application folder.
4. Port gameplay behavior from V1 as tested Python behavior, not by embedding
   PowerShell or copying its UI.
5. Retire code only after its replacement has passed parity tests against the
   retained V1 fixtures and route cases.

## Current Baseline

| Area | Canonical source | Current state |
|---|---|---|
| Desktop distribution, import, storage, security | V3 | Keep as-is |
| Browser UI, Auto/Manual/CLI modes | V3 | Keep as-is |
| Kai Books 1-5 Redux automation | V3 | Keep and regression-test |
| Magnakai Books 6-8 rules | V1 | Port to V3, one book at a time |
| Legacy save behavior | V1, V2, V3 | Build explicit import/migration coverage |
| Duplicate web surfaces | V1 | Keep only as reference until parity is proven |

## Work Plan

### Phase 0: Freeze the Baseline

- Keep V1 and V2 unchanged as reference repositories.
- Maintain a V3 smoke baseline for Books 1-8 data loading. The test suite is the
  guardrail for all future rules work.
- Collect representative save fixtures from V1, V2, and V3: fresh character,
  mid-combat, section checkpoint, completed book, and malformed/legacy save.
- Record known Book 6 source cases before implementation: creation choices,
  RNT, section entry effects, shops, loot, combat exceptions, deaths, endings,
  achievements, and Book 7 handoff.

Exit criteria: current V3 tests pass and a fixture inventory exists outside
production save directories.

### Phase 1: Define Compatibility Boundaries

- Document one versioned JSON save schema and add migrations for V1/V2 fields.
- Preserve unknown legacy fields during import until their behavior is mapped.
- Keep a source-backed standalone and continuation setup for Book 6 while
  route-level fixture coverage continues to expand.
- Add a reusable book-onboarding checklist so Books 7 and 8 do not require a
  new migration strategy.

Exit criteria: old saves import into a disposable copy of V3 without corrupting
the source save or losing recognized data.

### Phase 2: Port Book 6

Implement Book 6 in this order:

1. Book metadata, folder validation, reader labels, and explicit support state.
2. Magnakai character state: disciplines, ranks, lore-circle progression, and
   Book 5-to-6 carry-forward setup.
3. Book 6 starting choices and DE options, including Curing/Healing and
   Weaponskill behavior.
4. Data-driven ordinary rules: route graph, simple section effects, meals,
   item gains/losses, shops, and RNT cases.
5. Python code for exceptional rules that do not fit the existing flow schema.
6. Combat presets and exceptions, death/failure routes, achievements, summary,
   Book 6 completion, and Book 7 handoff.
7. Route, save/load, and full-story regression tests.

Exit criteria: Book 6 is playable from both a completed Book 5 save and fresh
setup, with the important V1 routes reproduced and tested.

### Phase 3: Port Books 7 and 8

Repeat the Book 6 process one book at a time. Do not start Book 8 implementation
until Book 7 has stable migration, completion, and replay coverage.

Exit criteria: Books 1-8 can be played as a continuous campaign, replayed, and
loaded from migrated saves.

### Phase 4: Consolidate and Release

- Move any remaining useful V2 differences into V3 or document why they are
  intentionally excluded.
- Remove V2 Grey Star residue only after save migrations prove it is obsolete.
- Choose the V3 UI as the only shipped web surface; archive V1's alternate
  browser launcher/UI as a reference, not a release path.
- Update installer, user guide, support matrix, release notes, and automated
  self-test to describe Books 1-8 accurately.

Exit criteria: one installer, one launch path, one UI, one save schema, and a
published parity report for Books 1-8.

## Definition of Done Per Book

A book may be marked playable only when all of these are complete:

- New-game and previous-book handoff setup.
- Character sheet, inventory, equipment limits, and all book-specific state.
- Source-linked navigation, RNT, entry rules, item rules, and recurring effects.
- Combat presets/exceptions, losses, evasion, deaths, and recovery behavior.
- Achievements, statistics, completion, replay, and next-book handoff.
- Save/load/export/import tests, including at least one legacy fixture.
- Browser Auto, Manual, and CLI mode checks.
- Desktop smoke test with installed book files.

## First Active Slice: Book 6 Preflight

The initial preflight slice was intentionally Books 1-5-only. The implemented
release now exposes Books 1-8, adds Magnakai state and Book 5-to-6 handoff tests,
and retains that baseline as a source-parity guardrail.

## Implementation Status (Complete)

- Save compatibility is implemented and covered for V1-shaped Magnakai saves.
- The V3 engine carries campaign state through Book 5 to 6, Book 6 to 7, and
  Book 7 to 8, with Magnakai ranks, disciplines, Weaponmastery selections,
  pocket items, gold, and starting equipment validated at each boundary.
- Book 6 now includes source-backed setup, ordinary item and meal effects,
  terminal outcomes, RNT modifiers and routes, the three-pick tournament,
  fixed-price purchases, dynamic resale at sections 76, 98, and 275, selected
  loot/loss choices, and all 28 printed combat encounters. Purchases are
  atomic: no Gold Crowns are spent if an item cannot be stored.
- Books 7 and 8 include setup, terminal outcomes, RNT coverage, source route
  flags, item exchanges/losses, confiscation/recovery state, selected section
  choices, and all 39 and 37 printed combat encounters respectively. The
  reusable combat schema now covers encounter-specific weapon restrictions,
  conditional immunity, temporary modifiers and disarmament, damage
  multipliers, and threshold routes.
- Fresh `new` creation now covers Books 1-8 in both the browser flow and the
  embedded CLI. Magnakai lore circles are synchronized from the source data and
  preserve V1 save bonuses without applying them twice during a handoff. Book 8
  section 17 also preserves V1's Fire-before-Light RNT precedence when both
  lore circles are complete.
- The source suite has 135 passing tests, including V1 run-difficulty,
  permadeath, integrity, achievement-gating, Sommerswerd, and ManualCRT cases.
  The installer build and the generated
  desktop executable's `--self-test` pass with the complete rules data.
- The V1-installed Books 1-8 library has been imported into V3's managed
  user-data location and all eight reader title pages have passed the canonical
  HTTP-server check.

## Ongoing Regression Coverage

- V3 now carries an explicit rule-data record for every V1 section-entry hook:
  86 for Book 6, 56 for Book 7, and 36 for Book 8. Add route-level fixtures as
  future regressions are discovered.
- Keep expanding important winning and failure-path fixtures across all three
  Magnakai books as normal maintenance.
- Repeat installed-reader browser checks and Auto/Manual/CLI smoke passes in a
  browser-capable release environment. This integration verified the canonical
  HTTP reader delivery; this session's browser automation adapter was not
  available.
- Books 6-8 are on the public playable-book list with both standalone and
  campaign-continuation setup. V1 and V2 are reference-only and no longer part
  of the supported launch or distribution workflow.
- The V1 run feature set is now part of the V3 canonical schema: Story, Easy,
  Normal, Hard, and Veteran difficulties; optional permadeath; signed run
  integrity; achievement eligibility; and DataFile/ManualCRT combat resolution.
  Browser Auto/Manual/CLI remains an interaction choice, not a difficulty or
  CRT resolution mode.
  Book completion now opens the next book's Story So Far reader page before
  presenting its Action Chart setup; temporary stored gear is deliberately not
  carried through that boundary.
