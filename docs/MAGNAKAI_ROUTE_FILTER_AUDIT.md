# Magnakai Route Filter Audit

## Scope

Books 6-12 read their installed Project Aon choice text at runtime. The
assistant attaches a condition only when the source wording maps directly to
state that the Action Chart already stores. The same availability result is
used to disable a reader route and to reject an attempted `follow_route`
call, so a disabled choice cannot be bypassed through the assistant controls.

## Verified Live Coverage

| Book | Explicit gated source routes |
| --- | ---: |
| 6 | 50 |
| 7 | 79 |
| 8 | 66 |
| 9 | 60 |
| 10 | 72 |
| 11 | 71 |
| 12 | 82 |
| **Total** | **480** |

The runtime parser covers explicit Magnakai Discipline and rank gates,
Lore-circles, stated Arrow counts, named carried items, item alternatives,
and Book 6's recorded Riverboat Ticket purchase. Compound source wording
retains its printed structure: for example, a route that allows either
`Pathsmanship and Scion-kai rank` or `Animal Control` requires the complete
first branch or the complete alternative branch.

## Deliberate Reader-Directed Cases

The assistant does not infer a condition for text that cannot be established
from the current save without guessing. This includes references such as
"this skill", prior-adventure history, optional intentions, combat outcomes,
and Random Number Table results. Those choices remain visible in the reader
instead of being silently removed.
