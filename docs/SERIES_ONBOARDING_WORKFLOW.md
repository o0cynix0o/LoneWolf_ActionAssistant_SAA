# Series Onboarding Workflow

This is the repeatable workflow for adding a new Lone Wolf series while the
app is in internal testing. It keeps the player-owned book files separate from
the application and makes every automated rule traceable to a numbered source
section and regression test.

## 1. Source Inventory

1. Locate the official standard multi-page HTML folders.
2. Verify `title.htm`, `sect1.htm`, and all numbered sections are present.
3. Add only book metadata, folder names, titles, and supported range to the
   app catalog.
4. Verify import, reader navigation, library cards, and installer links.

## 2. Campaign Entry Contract

1. Read the book's action-chart, equipment, rules, discipline, and rank pages.
2. Record every fresh-start and prior-series carryover rule as structured data.
3. Make overflow decisions explicit in the UI; never silently delete carried
   items.
4. Add unit tests for a fresh start and the previous-book handoff before
   enabling the series in the library.

## 3. Whole-Book Ledger

1. Generate a prose-free record for every section: outgoing printed links,
   incoming count, and broad rule signals.
2. Fail the generator if a book does not contain all expected section numbers.
3. Commit the ledger and source-audit index so audit coverage is measurable
   without shipping licensed text.

## 4. Verified Rules Passes

Process each candidate class in numbered-section order:

1. Random Number Table checks: raw roll, modifiers, ranges, effects, and route.
2. Mandatory section effects: ENDURANCE, meals, gold, and unavoidable item use.
3. Combat catalogue: enemy statistics, victory/evade routes, and exceptions.
4. Conditional choices: disciplines, rank, carried items, prior route state,
   and selected equipment.
5. Optional loot and forced losses: offer player choices where the book gives a
   choice; automate only unambiguous destinations and quantities.
6. Achievements: add only events that are directly observable in saved state.

Each verified batch must have a targeted regression test. A candidate remains
reader-directed until its trigger and outcome are both unambiguous.

## 5. Campaign And Route Testing

1. Test fresh starts at every supported book.
2. Test every inter-book handoff, including full Backpack and two-Weapon cases.
3. Exercise RNT low/high boundaries, discipline modifiers, and item gates.
4. Run story, easy, normal, and hard configurations; run permadeath separately.
5. Preserve a concise report of executed routes, expected endings, and any
   reader-directed cases that remain.

## 6. Publish Gate

1. Run the full smoke suite.
2. Run the packaging build and launch the packaged desktop shell.
3. Update README, user guide, wiki, strategy guides, changelog, and release
   notes with the actual support boundary.
4. Commit and push each coherent tested milestone; create a release only after
   the final package and campaign tests pass.

## Working Principle

The assistant may accelerate extraction, indexing, and test generation, but it
does not turn a keyword hit into a game rule by assumption. The book reader is
the fallback source of truth until a section has a verified structured rule.
