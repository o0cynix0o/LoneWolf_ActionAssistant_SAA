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

## Books 9-12: Direct Mandatory Effects

The first source-verified rules pass maps 117 effects that are mandatory once
the reader reaches the identified section. It deliberately excludes effects
whose availability depends on a prior route, a selected item, a discipline,
an RNT result, or a combat outcome.

| Book | Direct effects automated | Covered effect types |
| --- | ---: | --- |
| 9 | 28 | ENDURANCE loss, required meals, full recovery |
| 10 | 34 | ENDURANCE loss, required meals |
| 11 | 30 | ENDURANCE loss, required meals, recovery |
| 12 | 25 | ENDURANCE loss, required meals, recovery, lost Bow |

Meals use the normal Hunting/Huntmastery exemption only where the source
permits it. Book 11 Section 74 is explicitly mapped as an exception: the
printed rule requires a Meal or the ENDURANCE loss even when the player has
Huntmastery.

## Books 9-12: Base Combat Catalogue

All 172 printed combat encounters now load the source Combat Skill and
ENDURANCE values in the assistant. The catalogue also includes 141 plain
victory routes and 9 plain evade routes. It intentionally does not infer the
remaining special-fight mechanics, such as immunity, timed modifiers,
alternate victory routes, round limits, or post-combat rewards.

| Book | Combat encounters | Clear victory routes | Clear evade routes |
| --- | ---: | ---: | ---: |
| 9 | 38 | 33 | 8 |
| 10 | 40 | 29 | 0 |
| 11 | 36 | 30 | 0 |
| 12 | 58 | 51 | 1 |

## Books 9-12: Random Number Table Rules

The assistant now maps 94 clear Random Number Table rules. These cover
source-defined route ranges, discipline, Lore-circle, rank, rope, and
Weaponmastery modifiers, plus unambiguous ENDURANCE recovery and loss rolls.
The rules engine now also supports modifiers based on the total number of
Magnakai Disciplines and the count above the initial three.

| Book | Source player RNT rolls | Automated in this pass | Reader-directed |
| --- | ---: | ---: | ---: |
| 9 | 20 | 18 | 2 |
| 10 | 26 | 20 | 6 |
| 11 | 29 | 23 | 6 |
| 12 | 40 | 33 | 7 |

The 21 reader-directed rolls are preserved in the reader because their
printed outcome depends on a chosen active weapon, an unspecified missile or
bow bonus, or prior use of a particular item. They will be mapped only after
those dependencies are represented explicitly in the save and rules model.

## Books 9-12: First Inventory Rules Pass

This pass adds only item changes whose source wording establishes both the
item and its destination without requiring the assistant to infer a choice.
Optional pickups remain explicit loot buttons. Where the book requires the
player to choose a loss, the assistant presents a loss picker instead of
selecting an item itself.

| Book | Optional loot choices | Prompted losses | Mandatory item events |
| --- | ---: | ---: | ---: |
| 9 | 4 | 1 | 7 |
| 10 | 13 | 0 | 4 |
| 11 | 11 | 0 | 4 |
| 12 | 6 | 0 | 6 |

Examples include Book 9's Psychic Ring and Iron Key, Book 10's Bullwhip and
Death Knight supplies, Book 11's Ironheart Broadsword and Obsidian Seal, and
Book 12's mission items. The pass also removes the named Rope, Sabito,
Bullwhip, Bow, and Crystal Explosive where the source explicitly consumes or
loses them.

The following cases remain reader-directed: losses tied to an exact Action
Chart slot when the underlying list has changed, weapon destruction tied to
the weapon actually used, quantity choices, confiscation and later recovery,
and special item powers such as Helshezag, the Bronin Vest, and the Silver
Bracers. Those require stateful equipment effects or route history, not a
safe generic inventory mutation.

## Internal Testing Boundary

Books 9-12 are now internal testing paths. They offer fresh Magnakai setup,
campaign continuation, reader navigation, saves, inventory, and manual combat
tools. Their section baselines are a prerequisite for the next implementation
pass, which must map and test, for every required case:

1. Magnakai advancement and each book's printed entry equipment rules.
2. Conditional choices for disciplines, special items, prior events, and route state.
3. Combat-result exceptions, stateful special-item powers, remaining conditional item changes, and the remaining conditional random-number effects.
4. Book completion and the next-book transfer rules.

This keeps the assistant honest: the campaign spine is testable now, while
unmapped per-section rules remain manual until they have been verified.
