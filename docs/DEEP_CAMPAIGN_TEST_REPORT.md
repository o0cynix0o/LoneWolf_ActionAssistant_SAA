# Deep Campaign Test Report

Internal-testing evidence for Books 1-12. All automated campaigns used a
temporary save, state, and book workspace; no player save was read or changed.

## Campaign Matrix

| Difficulty | Permadeath | Result |
| --- | --- | --- |
| Story | Not available | Completed Books 1-12 at Book 12, section 350 |
| Easy | Off | Completed Books 1-12 at Book 12, section 350 |
| Easy | On | Completed Books 1-12 at Book 12, section 350 |
| Normal | Off | Completed Books 1-12 at Book 12, section 350 |
| Normal | On | Completed Books 1-12 at Book 12, section 350 |
| Hard | Off | Completed Books 1-12 at Book 12, section 350 |
| Hard | On | Completed Books 1-12 at Book 12, section 350 |
| Veteran | Off | Completed Books 1-12 at Book 12, section 350 |
| Veteran | On | Completed Books 1-12 at Book 12, section 350 |

Each campaign used the normal book-to-book handoff, completed the Book 6-12
Action Chart setup, and included isolated save/load checkpoints.

## Branch Coverage

- All 6,912 explicit player-choice links parsed from the installed Project Aon
  HTML were present in the corresponding reader payload. Footnotes, answers,
  and cross-references were excluded from this assertion because they are not
  player choices.
- All 315 configured one-step Random Number Table sections returned a defined
  result for digits 0-9 under both a minimal Action Chart and a fully equipped
  Action Chart: 6,300 result evaluations.
- All 2,100 possible input sequences for the three staged RNT checks were
  exercised. This includes the Book 1 marsh, Book 5 guard surprise, and Book 6
  archery tournament checks.
- A high-stat victory pass resolved all 452 configured combat presets. Book 12
  section 195 deliberately leads to the source-defined terminal section 318
  after victory, and is not a combat-route failure.
- Alternative combat coverage passed for 68 evades, 4 defeat routes, 8 wounded
  routes, 9 comparison outcomes, 3 survival routes, 11 timeout routes, 19
  fast-win routes, 17 slow-win routes, 2 threshold routes, 2 roll-specific
  routes, and the safe and fatal Javek venom outcomes.
- Source-terminal deaths were verified with permadeath enabled at every
  supported difficulty for all 57 newly catalogued Book 9-12 terminal sections.

## Corrections Found During Testing

- Added Book 9-12 terminal-death automation so permadeath consistently locks a
  dead run instead of leaving later-book deaths reader-directed.
- Restored omitted explicit choices in Books 7 and 8.
- Completed 23 unambiguous Book 6-7 RNT rules, removed two stale non-RNT roll
  entries, and corrected four source-inaccurate modifiers.
- Completed the Book 6 section 340 archery-tournament final route.
- Corrected Book 8 section 287: its two Vordaks route to section 79 on victory
  and do not carry the unrelated six-round deadline from section 13.

## Remaining Manual Testing

The automated work verifies configured rules and all source-visible choice
targets. Human exploratory play is still valuable for reader clarity, wording,
and intentional choices that depend on unmodeled puzzle answers or player
judgment; it should not be treated as a substitute for the source-rule checks
recorded above.
