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

All 174 printed combat encounters now load the source Combat Skill and
ENDURANCE values in the assistant. The catalogue also includes 145 plain
victory routes and 10 plain evade routes. It intentionally does not infer the
remaining special-fight mechanics, such as immunity, timed modifiers,
alternate victory routes, round limits, or post-combat rewards.

| Book | Combat encounters | Clear victory routes | Clear evade routes |
| --- | ---: | ---: | ---: |
| 9 | 38 | 33 | 8 |
| 10 | 40 | 29 | 0 |
| 11 | 37 | 31 | 0 |
| 12 | 59 | 52 | 2 |

## Books 9-12: Random Number Table Rules

The assistant now maps all 116 clear Random Number Table rules. These cover
source-defined route ranges, discipline, Lore-circle, rank, rope, and
Weaponmastery modifiers, plus unambiguous ENDURANCE recovery and loss rolls.
The rules engine now also supports modifiers based on the total number of
Magnakai Disciplines and the count above the initial three.

| Book | Source player RNT rolls | Automated | Reader-directed |
| --- | ---: | ---: | ---: |
| 9 | 20 | 20 | 0 |
| 10 | 27 | 27 | 0 |
| 11 | 29 | 29 | 0 |
| 12 | 40 | 40 | 0 |

Book 10 Section 128 now asks which carried weapon is used before applying its
source modifiers. Book 10 Section 218 is a play-or-leave dice-game panel that
records every stake and payout. Book 12 Section 145 offers a kept Dose of
Adgana; its chosen combat use applies the first-use or repeat-use CS bonus,
consumes the dose, and performs the source addiction check after combat.

The Book 10 source contains 27 player RNT instructions. The earlier 26-count
ledger omitted Section 218's two-player dice game; the installed Project Aon
source is the authoritative count.

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
| 12 | 7 | 0 | 7 |

Examples include Book 9's Psychic Ring and Iron Key, Book 10's Bullwhip and
Death Knight supplies, Book 11's Ironheart Broadsword and Obsidian Seal, and
Book 12's mission items. The pass also removes the named Rope, Sabito,
Bullwhip, Bow, and Crystal Explosive where the source explicitly consumes or
loses them.

The following cases remain reader-directed: losses tied to an exact Action
Chart slot when the underlying list has changed, weapon destruction tied to
the weapon actually used, quantity choices, confiscation and later recovery,
and special item powers that depend on a specific route or item interaction.
Those require more route-history detail than a safe generic inventory mutation.

## Books 9-12: First Special-Equipment Rules Pass

The assistant now treats Ironheart Broadsword and Helshezag as selectable
combat weapons. Ironheart supplies its printed +8 COMBAT SKILL bonus; Helshezag
supplies +5 normally, +7 against a Darklord, and applies its permanent
one-ENDURANCE drain in every combat round after the first. Book 12's Bronin
Vest and Silver Bracers apply their printed permanent stat increases when kept.

The pass also records the Silver Rod's destruction in Book 11 Section 191,
the Golden Amulet's loss in Book 12 Section 121, Helshezag as optional loot,
and the Book 12 Section 247 two-round unarmed and third-round evasion rule.
It adds the two printed special combats that the prior catalogue count missed:
Book 11 Section 204 and Book 12 Section 133.

## Books 9-12: Combat And Campaign Outcomes

All recorded later-Magnakai special combat presets now have regression
coverage for their route and timing behavior. This includes Book 9's eight
evade routes, Book 11 Section 204's immunity and Ironheart Broadsword case,
and Book 12's immediate-evade and forced-unarmed encounters.

The Book 8-to-12 handoff is also exercised as one campaign flow. Across every
supported handoff, when a new field issue would exceed the two-Weapon or
eight-item Backpack capacity, the transition setup lets the player explicitly
leave selected carried items behind before the issue is applied. Those choices
are recorded in the next book's setup; no transition silently clears the
Backpack. Book 12 now resolves to the stable supported-campaign end state.

## Internal Testing Boundary

Books 9-12 are now internal testing paths. They offer fresh Magnakai setup,
campaign continuation, reader navigation, saves, inventory, and manual combat
tools. Their section baselines are a prerequisite for the next implementation
pass, which must map and test, for every required case:

1. Magnakai advancement and each book's printed entry equipment rules.
2. Conditional choices for disciplines, special items, prior events, and route state.
3. Remaining combat-result exceptions, route-specific special-item powers, conditional item changes, and the remaining conditional random-number effects.
4. Book completion and the next-book transfer rules.

This keeps the assistant honest: the campaign spine is testable now, while
unmapped per-section rules remain manual until they have been verified.
