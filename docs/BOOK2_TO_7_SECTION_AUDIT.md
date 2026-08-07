# Books 2-7 Section Audit

## Scope and method

This audit reviewed every installed numbered section in the local Project Aon
sources for Books 2 through 7: 2,150 sections in total (Books 2-4 and 6-7
have 350 sections each; Book 5 has 400).  The scan compared each source
choice and explicit numeric instruction with the committed section-flow and
simple-automation data, then read every unmatched numeric candidate in its
source context before changing behavior.

`sect152.htm` in Book 6 contains an unescaped ampersand in a shop sign.  The
tolerant source scan still reviewed its ordinary two-choice content; it is not
a rules or automation defect.

## Route baseline

| Book | Source sections | Source choice links | Stored source-route links | Explicit gated choices without `routeChecks` |
| --- | ---: | ---: | ---: | ---: |
| 2 - Fire on the Water | 350 | 576 | 576 | 6 of 70 |
| 3 - The Caverns of Kalte | 350 | 605 | 603 | 113 of 115 |
| 4 - The Chasm of Doom | 350 | 568 | 568 | 23 of 76 |
| 5 - Shadow on the Sand | 400 | 680 | 682 | 95 of 109 |
| 6 - The Kingdoms of Terror | 350 | 586 | 24 | 86 of 86 |
| 7 - Castle Death | 350 | 638 | 10 | 127 of 127 |

The stored-route count is a source-link baseline, not a count of rendered
choices.  Books 6 and 7 deliberately use focused hand-authored flow entries
for their tested interactions and obtain the remaining reader links from the
installed source at runtime.  The `routeChecks` column isolates the distinct
future work needed to hide unavailable narrative choices based on disciplines,
items, rank, gold, and prior visits.  It does not mean those routes are absent
from the reader.

## Verified automation additions

| Book | Section | Source instruction | Assistant behavior |
| --- | ---: | --- | --- |
| 2 | 290 | Replace poisoned food with another Meal or lose 3 END. | Uses one Backpack Meal; otherwise loses 3 END. Hunting does not substitute. |
| 6 | 298 / 26 | A Jakan imposes -2 CS during the tournament; a 0 in the final breaks it and routes to 335. | Records the Jakan tournament state, applies the temporary final-combat modifier, and routes a 0 to 335 only for that state. |
| 7 | 53 | Lose 5 END from the bat swarm. | Deducts 5 END. |
| 7 | 250 | The Lorestone restores current END to its original total. | Restores END to its current maximum. |
| 7 | 267 | Pocket the Lorestone and restore END to its original total. | Adds the Lorestone of Herdos as a Special Item and restores END to its current maximum. |

## Candidates read and deliberately not changed

- Book 2 sections 79 and 242 describe the Sommerswerd's persistent combat
  rules.  Those rules already belong to the combat engine and are not
  one-time section-stat changes.
- Book 7 section 180 says Psi-surge avoids a deduction during the preceding
  non-combat use of the discipline; it is not an additional standalone loss
  to apply on entering section 180.
- Book 6 section 152 is malformed HTML only; its source text creates no
  mandatory numeric or inventory effect.
- No unmodeled mandatory numeric effect survived contextual review in Books
  3, 4, or 5.

## Verification

`testing/test_saa_smoke.py` contains focused regression coverage for the new
Book 2 meal behavior, Book 6 Jakan modifier and zero-roll route, and Book 7
bat-swarm and Lorestone effects.  Run the complete suite with:

```powershell
python -m unittest discover -s testing -p "test_*.py" -v
```

## Follow-up: player-choice filtering

The audit confirms that the next high-value feature is a dedicated route-check
backfill, not additional blind automation.  Books 6 and 7 especially need
their source conditions transcribed into structured `routeChecks` before the
UI can safely hide choices that a player cannot take.  That work should be
done book by book with fixture tests for every mapped discipline, item, gold,
rank, and visited-section condition.
