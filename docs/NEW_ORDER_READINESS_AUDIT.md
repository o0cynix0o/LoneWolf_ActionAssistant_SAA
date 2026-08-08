# New Order Readiness Audit

## Scope

The locally available New Order source set contains Books 21-29. The source
HTML is player-supplied and remains outside this repository; the committed
audit data contains only derived section numbers, links, and broad rule
signals.

## Source Baseline

| Book | Title | Folder | Sections | Printed links |
| --- | --- | --- | ---: | ---: |
| 21 | Voyage of the Moonstone | `21votm` | 350 | 532 |
| 22 | The Buccaneers of Shadaki | `22tbos` | 350 | 529 |
| 23 | Mydnight's Hero | `23mh` | 350 | 521 |
| 24 | Rune War | `24rw` | 350 | 544 |
| 25 | Trail of the Wolf | `25totw` | 350 | 559 |
| 26 | The Fall of Blood Mountain | `26tfobm` | 350 | 582 |
| 27 | Vampirium | `27v` | 350 | 549 |
| 28 | The Hunger of Sejanoz | `28thos` | 300 | 448 |
| 29 | The Storms of Chai | `29tsoc` | 350 | 544 |
| Total |  |  | 3,100 | 4,808 |

Book 28 is intentionally recorded as a 300-section book. The ledger generator
now validates that a source has a contiguous numbered range rather than
assuming every book ends at section 350.

## Current Boundary

This is a source-readiness milestone only. The app does not yet expose the New
Order books as playable: its dedicated 16-discipline Action Chart, Kai Weapon,
entry equipment, currency, campaign transfer, per-section automation, and
achievements still require the same verified implementation pass used for the
Grand Master series. Books 30-32 are not locally installed and therefore are
not included in this audit.
