# Books 8-12 Readiness Audit

## Scope

This audit used the locally installed Project Aon standard multi-page HTML
sources. It records source structure and direct, unambiguous automation work;
it does not redistribute book text or make unreviewed rules playable.

## Book 8: The Jungle of Horrors

Book 8 was reviewed across all 350 sections and 559 printed section links.
The pre-existing testing path already covered its starting pass, known item
awards, route effects, meals, combat material, and Book 7 handoff. This pass
added the remaining clear mandatory effects found in the source review:

- Section 18: gate-guard spear injury, minus 2 ENDURANCE.
- Section 66: disturbed rest, minus 2 ENDURANCE.
- Section 78: required meal; without one, minus 3 ENDURANCE.
- Section 81: spend a Fireseed and take minus 12 ENDURANCE.
- Section 83: needle-spine injury, minus 5 ENDURANCE.
- Section 97: needle-spine injury, minus 1 ENDURANCE.

Book 8 is now exposed as a playable testing build. Its existing targeted source
tests and the new regression test cover the added effects.

## Books 9-12: Source Baselines

Every section in each of the following books has an entry in its
`bookN-section-flows.json` file. Each entry records its source link targets,
incoming-link count, and an automation-review classification without copying
the book's prose.

| Book | Title | Sections | Printed links | Conditional/gate candidates | Direct-effect candidates |
| --- | --- | ---: | ---: | ---: | ---: |
| 9 | The Cauldron of Fear | 350 | 566 | 89 | 58 |
| 10 | The Dungeons of Torgar | 350 | 533 | 104 | 60 |
| 11 | The Prisoners of Time | 350 | 530 | 117 | 65 |
| 12 | The Masters of Darkness | 350 | 516 | 131 | 61 |

The app now recognizes the folders `09tcof`, `10tdot`, `11tpot`, and `12tmod`.
It validates and imports their official HTML ZIPs or extracted folders.

## Internal Testing Boundary

Books 9-12 are now internal testing paths. They offer fresh Magnakai setup,
campaign continuation, reader navigation, saves, inventory, and manual combat
tools. Their section baselines are a prerequisite for the next implementation
pass, which must map and test, for every required case:

1. Magnakai advancement and each book's printed entry equipment rules.
2. Conditional choices for disciplines, special items, prior events, and route state.
3. Combat stats, combat-result exceptions, losses, gains, meals, and random-number effects.
4. Book completion and the next-book transfer rules.

This keeps the assistant honest: the campaign spine is testable now, while
unmapped per-section rules remain manual until they have been verified.
