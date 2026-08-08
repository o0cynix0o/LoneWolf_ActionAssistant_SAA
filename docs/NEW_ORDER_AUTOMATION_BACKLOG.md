# New Order Automation Backlog

This is a source-derived implementation queue. Counts are candidate signals,
not promises that every occurrence requires a separate rule. Each book is
complete only after the source audit, implementation, focused tests, and full
regression run agree.

| Phase | Books | RNT | Combat | Primary review focus |
| --- | --- | ---: | ---: | --- |
| 2 | 21-23 | 108 | 29 | Entry, Kai Weapon rules, inventory, achievement paths |
| 3 | 24-26 | 150 | 17 | Rank/discipline conditions, meals, transfers |
| 4 | 27-29 | 117 | 61 | Combat-heavy Book 29 and Book 28's 300-section range |

For every book, review and classify each candidate in these categories:

- Random Number Table routing, modifiers, and effects.
- Combat loading, exceptions, immunity, evasion, and victory routes.
- ENDURANCE, meal, Gold, item, and Backpack changes.
- Conditional choices based on disciplines, Kai Weapons, carried items, and
  previous campaign state.
- Endings, transfer preparation, and achievements.

Automation must not silently choose a player-owned loss, equipment exchange,
or optional use of a power. Those remain explicit choices in the application.
