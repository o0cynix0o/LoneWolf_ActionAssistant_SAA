# Books 9-12 Completion Plan

## Purpose

Books 9-12 are installed, structurally reviewed, and playable for internal
testing. This plan closes the remaining automation and verification work
without guessing at source rules. A rule is complete only when its source
condition, player-facing behavior, state mutation, and regression test agree.

## Phase 1: Conditional Random Number Rules

**Goal:** resolve the remaining reader-directed random-number rules.

- Create an evidence ledger listing each section, its source dependency, and
  the required state representation.
- Add explicit state for the active weapon, missile/bow modifier, consumed
  item, and other prerequisites only where the source requires it.
- Automate each rule, preserving a clear manual fallback only when a player
  decision genuinely cannot be inferred.
- Add a focused test for every new rule and update the readiness audit.

**Exit criteria:** no known RNT rule in Books 9-12 remains reader-directed
solely because the app lacks a representable condition.

### Phase 1 Evidence Ledger

| Group | Sections | Status |
| --- | --- | --- |
| Direct discipline/stat rules | 9:347, 10:166, 10:203, 12:172 | Automated and regression-tested. |
| Missile or bow bonus | 10:70, 10:96, 10:293, 11:76, 11:151, 11:193, 11:284, 11:322, 11:333, 12:99, 12:107, 12:135, 12:186, 12:324 | Automated with the source-verified Weaponmastery-with-Bow +3 bonus; Book 12:324 also recognizes Huntmastery at Archmaster rank. |
| Active weapon selection | 10:128 | Requires a non-combat active-weapon selection. |
| Item slot loss | 9:201 | Requires ordered loss handling and fallback from Special Items to Backpack Items. |
| Stateful player choice | 10:218, 12:145 | Requires dice-game state and prior Adgana-use history respectively. |

## Phase 2: Conditional Reader Choices

**Goal:** make conditional choices trustworthy and understandable.

- Normalize condition types for disciplines, items, quantities, prior events,
  ranks, and route state.
- Mark unavailable choices in the reader with the reason; do not silently
  remove normal player decisions.
- Enable eligible choices automatically as save state changes.
- Test both eligible and ineligible states for every new condition class.

**Exit criteria:** a player can see which choices are unavailable and why,
and cannot accidentally follow a route the current Action Chart forbids.

### Phase 2 Progress

- The reader and route endpoint now share the same availability decision, so
  an unavailable route is both disabled in the UI and rejected by the rules
  engine.
- The source reader recognizes explicit Magnakai Discipline, rank,
  Lore-circle, named carried-item, and stated Arrow-count gates. It gives the
  player the specific missing requirement instead of silently hiding the
  choice.
- Flow data can also attach explicit `condition` and `blockedReason` fields to
  an individual source route for audited gold, quantity, prior-event, and
  special-item gates.
- Wording that cannot safely be represented yet, including prior-adventure
  history and context-sensitive item use, intentionally remains a normal
  reader choice until its route state is audited in Phase 3.

## Phase 3: Inventory and Special-Item Rules

**Goal:** complete source-verified equipment state changes.

- Automate exchanges, prompted losses, confiscation and recovery, item
  quantities, and weapon-specific destruction.
- Implement remaining route-specific special-item powers only where source
  wording provides an unambiguous trigger and effect.
- Preserve inventory order and item provenance where a later section depends
  on an exact item or slot.

**Exit criteria:** all known Books 9-12 inventory mutations have an explicit,
tested model or a documented player-choice prompt.

## Phase 4: Combat and Campaign Outcomes

**Goal:** finish non-standard combat and the campaign spine.

- Audit the remaining special combat results: timed effects, immunity,
  restricted weapons, forced unarmed rounds, round limits, evasions,
  post-combat effects, and alternate routes.
- Implement Book 9 to 10, 10 to 11, and 11 to 12 transfer rules.
- Implement Book 12 completion as a stable series-end state until Book 13 is
  added.

**Exit criteria:** every printed combat has its essential special behavior
represented, and every book ending has a deterministic next step.

## Phase 5: Campaign Verification

**Goal:** validate actual player workflows, not just data files.

- Run at least one successful campaign route and one failure/alternate route
  through Books 6-12.
- Exercise manual, automatic, and CLI game modes where they change behavior.
- Verify save/load, signed-save validation, inventory ordering, combat resume,
  death/permadeath, and book handoff at meaningful checkpoints.
- Turn every discovered defect into a regression test before closing it.

**Exit criteria:** the complete supported campaign can be played, saved,
loaded, and resumed without state loss or unexplained manual corrections.

## Phase 6: Release Readiness

**Goal:** deliver a reproducible public build only after the above phases.

- Perform the final reader and setup UX pass.
- Update the user guide, changelog, readiness audit, and release notes.
- Run the full test suite, frozen executable self-test, and installer smoke
  test from a clean output directory.
- Commit and push final source, then create a GitHub tag and public release
  only after explicit release approval.

**Exit criteria:** tests and package checks pass, documentation matches the
application, and the public release is deliberately approved.

## Work Order

1. Phase 1 blocks Phase 2 because condition-aware reader choices depend on
   the same save-state primitives.
2. Phases 2 and 3 can proceed together once those primitives exist.
3. Phase 4 follows their rule model, then Phase 5 verifies it end to end.
4. Phase 6 is the release gate, not a substitute for testing.
