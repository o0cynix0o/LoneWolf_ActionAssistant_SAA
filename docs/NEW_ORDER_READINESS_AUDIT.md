# New Order Readiness Audit

## Scope

The local source set contains Books 21-29. The HTML remains outside this
repository; committed audit artefacts contain only derived section numbers,
links, and rule signals.

## Current Implementation

The application exposes Books 21-29 as the playable New Order campaign:
16-discipline Action Charts, Kai Weapons, starting equipment, book-to-book
continuation, reader routes, inventory, combat, saves, and baseline campaign
achievements are implemented. The remaining work is the source-verified,
per-section automation pass recorded in the companion backlog.

## Source Baseline

| Book | Folder | Sections | RNT | Combat | END | Meals | Gold | Inventory | Disciplines | Kai Weapon |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 21 | `21votm` | 350 | 30 | 23 | 92 | 28 | 56 | 30 | 87 | 5 |
| 22 | `22tbos` | 350 | 38 | 25 | 81 | 22 | 14 | 28 | 84 | 50 |
| 23 | `23mh` | 350 | 40 | 17 | 89 | 40 | 19 | 32 | 89 | 37 |
| 24 | `24rw` | 350 | 38 | 36 | 82 | 36 | 10 | 26 | 109 | 47 |
| 25 | `25totw` | 350 | 44 | 39 | 107 | 15 | 2 | 24 | 113 | 48 |
| 26 | `26tfobm` | 350 | 68 | 46 | 108 | 6 | 0 | 18 | 112 | 60 |
| 27 | `27v` | 350 | 60 | 11 | 80 | 12 | 14 | 18 | 99 | 41 |
| 28 | `28thos` | 300 | 31 | 27 | 72 | 17 | 2 | 12 | 69 | 35 |
| 29 | `29tsoc` | 350 | 26 | 41 | 115 | 18 | 42 | 39 | 78 | 47 |

Book 28 is intentionally a 300-section book. The ledger generator validates
each book's actual contiguous source range and does not assume 350 sections.

## Implemented Coverage

Books 21-23 now have source-verified Random Number Table coverage, including
conditional modifiers, mandatory effects, and player-selected optional spends.
Every source combat block is represented by an encounter preset with its
printed statistics and relevant timing, escape, or victory routing rules.
The clearest inventory changes are automated too: fixed losses follow the
printed list position, while optional rewards and purchases remain explicit
loot choices. New Order completion and exploration achievements are evaluated
for Books 21-29.

`data/book21to23-z-simple-automations.json` adds 137 source-derived direct
actions across 134 sections: 89 exact ENDURANCE changes, 43 Grand
Huntmastery-aware Meal requirements, and five compulsory Gold changes. The
shared `testing/generate_direct_effect_skeleton.py` tool derives this
prose-free catalogue from player-supplied HTML and deliberately excludes RNT,
combat, conditional, optional, and player-choice text. Existing hand-audited
item rules remain separate and are not replaced by the generated data.

`data/book24to26-z-simple-automations.json` extends the same guarded direct
effect pass to Books 24-26: 123 actions across 114 sections, consisting of
90 exact ENDURANCE changes and 33 Grand Huntmastery-aware Meal requirements.
There were no overlaps with the pre-existing simple automation catalogue.
The Book 24-26 RNT, combat, route, and inventory catalogues remain the
separate hand-audited data sets already used by the application.

`data/book27to29-z-simple-automations.json` completes this direct-effect
coverage for the New Order: 113 actions across 112 sections, consisting of
97 exact ENDURANCE changes, 14 Grand Huntmastery-aware Meal requirements,
and two compulsory Gold changes. There were no overlaps with the existing
simple automation data. This includes Book 28's 300-section source range;
the catalogue does not invent entries for sections that do not exist.

Optional rewards, equipment exchanges, chosen losses, puzzles, and contextual
route conditions remain visible in the reader. They need a player decision or
more context than a single deterministic section entry and are not silently
automated.

## Audit Artefacts

- `data/new-order-source-audit.json`: source-derived candidate sections.
- `data/book21-section-flows.json` through `data/book29-section-flows.json`:
  prose-free route and classification ledgers.
- `docs/NEW_ORDER_AUTOMATION_BACKLOG.md`: phased implementation queue.
- `docs/NEW_ORDER_CAMPAIGN_TEST_REPORT.md`: campaign, mode, save/load, and
  combat-preset regression coverage.

Books 30-32 remain outside this pipeline because compatible HTML source is not
available.
