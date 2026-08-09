# New Order Automation Record

This began as a source-derived implementation queue. The listed phases are now
complete: the source audit, implementation, focused tests, and full regression
run agree. Counts are candidate signals, not promises that every occurrence
requires a separate rule.

| Phase | Books | RNT | Combat | Status |
| --- | --- | ---: | ---: | --- |
| 2 | 21-23 | 108 | 65 | Complete: entry, Kai Weapon rules, inventory, and achievement paths |
| 3 | 24-26 | 150 | 121 | Complete: rank/discipline conditions, meals, and transfers |
| 4 | 27-29 | 117 | 79 | Complete: Book 29 combat coverage and Book 28's 300-section range |

For every book, review and classify each candidate in these categories:

- Random Number Table routing, modifiers, and effects.
- Combat loading, exceptions, immunity, evasion, and victory routes.
- ENDURANCE, meal, Gold, item, and Backpack changes.
- Conditional choices based on disciplines, Kai Weapons, carried items, and
  previous campaign state.
- Endings, transfer preparation, and achievements.

Automation must not silently choose a player-owned loss, equipment exchange,
or optional use of a power. Those remain explicit choices in the application.

The completed campaign and combat regression matrix is recorded in
`docs/NEW_ORDER_CAMPAIGN_TEST_REPORT.md`.
