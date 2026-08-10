# Changelog

## 3.5.4 - Internal Testing

- Completed the production UI pass begun in 3.5.3: Library Command now
  foregrounds the saved campaign and its active series, Campaign has a clear
  current-book context, Reader is a focused companion view, and Tools is a
  dedicated full-width workspace.
- Added a compact Campaign/Reader Console drawer backed by the same live save
  and terminal session model as the full Console route.
- Kept the original reader, Action Chart, combat, inventory, automation,
  achievements, saves, game modes, and 29-book campaign rules intact beneath
  the shared presentation layer.

## 3.5.3 - Internal Testing

- Unified the Library, Campaign, Reader, Tools, Console, Settings, and book
  installation surfaces behind one shared navigation and visual foundation.
- Made **Start Current Campaign** the primary Library action and marked the
  saved book as **Reading**, including its current section.
- Added Campaign, Reader, and Tools presentation routes over the same save:
  Campaign keeps reader and assistant together, Reader prioritizes book text,
  and Tools expands the assistant workspace.
- Exposed the embedded CLI as the Console route and guarded Settings rendering
  until the active campaign state has loaded.

## 3.5.2 - Internal Testing

- Enforced the published twelve-Special-Item carrying limit from Book 8 onward.
  Pocket-carried Special Items share that limit, while Books 1-7 retain their
  original no-limit rule.
- Added Special Item capacity to the inventory displays, exposed pocket-carried
  items, and allowed either kind of Special Item to be left behind during book
  transitions before new equipment is issued.

## 3.5.1 - Internal Testing

- Released the completed Books 13-29 direct-effect, route-filter, campaign,
  and combat-preset work that landed after the 3.5.0 package.
- Replaced the frozen embedded CLI's WinPTY redraw/echo path with a pipe-backed
  CLI and browser-side line editing, including local backspace and command
  history handling.
- Hardened atomic autosaves against brief Windows antivirus or indexing locks
  without permitting partial-save writes.
- Rebuilt the package and refreshed the release checksum from the exact
  installer asset.

## 3.5.0 - Internal Testing

- Added source-derived combat catalogues for all 306 directly represented Grand
  Master encounters in Books 13-20, including standard evasion, timed combat,
  round-limit, one-round-comparison, rank, discipline, and item-bonus rules.
- Added complete Grand Master standalone save/load regression coverage for
  Books 13-20 and corrected the support documentation to reflect the existing
  all-series RNT catalogues.
- Added guarded direct mandatory-effect automation across Grand Master and New
  Order Books 13-29, while preserving player-owned rewards, exchanges, and
  chosen losses as reader-visible decisions.
- Verified the Grand Master and New Order campaign spines across every
  difficulty, valid permadeath setting, and CRT mode. The regression matrix
  covers 18 handoff runs per series, Book 16 and Book 25 save/load checkpoints,
  all 306 Grand Master combat presets, and all 265 New Order combat presets.
- Corrected Book 20 completion to close the Grand Master run rather than offer
  a false direct handoff to the distinct New Order character campaign.

## 3.4.9 - Internal Testing

- Completed the source-verified RNT and combat catalogue pass for New Order
  Books 21-29, including rank-aware modifiers, timed fights, and printed
  route outcomes through Book 29.
- Added full-series New Order achievement regression coverage and release
  validation for the completed 21-29 testing campaign.

## 3.4.8 - Internal Testing

- Added Books 13-20 as Grand Master internal-testing campaigns, including
  fresh starts, Book 12 handoff, Grand Master disciplines, explicit overflow
  choices, campaign achievements, and the full Book 13 RNT pass.
- Added complete source-link and rule-signal ledgers for all Grand Master
  sections and the locally available New Order Books 21-29.
- Documented the reusable series-onboarding workflow and corrected Book 28's
  actual 300-section range in the audit tools.

## 3.4.7 - Internal Testing

- Completed a deep Books 1-12 campaign, route, random-number, and combat
  verification pass; see `docs/DEEP_CAMPAIGN_TEST_REPORT.md` for coverage.
- Added source-verified terminal deaths for Books 9-12 and restored omitted
  player choices in Books 7 and 8.
- Completed Book 6-7 RNT routing, including Book 6's archery tournament, and
  corrected source-inaccurate roll modifiers.
- Corrected the Book 8 Section 287 Vordak combat so it has no false time limit
  and routes to Section 79 after both enemies are defeated.

## 3.4.6 - Internal Testing

- Completed an isolated source-link campaign from Book 1 through Book 12,
  including Book 6 and Book 10 save/reload checkpoints, the Book 8 Psi-surge
  Vordak encounter, and the stable Book 12 ending.
- Added Book 7-12 final-section completion rules and story achievements so each
  completed Magnakai book records its campaign handoff correctly.
- Blocked section routes that are only available after the current combat has
  resolved, preventing fights such as Book 1 Section 255 from being bypassed.
- Updated the player and build documentation to show Books 1-12 as playable
  internal-testing campaigns.

## 3.4.5 - Internal Testing

- Added source-verified combat handling for the Ironheart Broadsword, Helshezag, the Bronin Vest, Silver Bracers, Silver Rod, Golden Amulet, and Korlinium-scabbard encounter.
- Added the previously omitted Book 11 Section 204 and Book 12 Section 133 printed combats, correcting the audited Book 9-12 catalogue total to 174.
- Helshezag now grants its printed Combat Skill bonus and applies its permanent one-ENDURANCE cost from the second combat round onward.

## 3.4.4 - Internal Testing

- Added 34 source-verified optional item pickups, a prompted Book 9 Weapon loss, and 21 mandatory item gains or losses across Books 9-12.
- Added direct inventory handling for explicit awards, consumed or lost named items, fixed-position Backpack losses, and the Book 12 Crystal Explosive objective.
- Kept special-item combat powers, position-dependent losses, and prior-route-dependent inventory changes reader-directed until their dependencies are modeled.

## 3.4.3 - Internal Testing

- Added 94 source-verified Book 9-12 Random Number Table rules, covering roll routes, rank and discipline modifiers, and clear ENDURANCE effects.
- Added support for source checks that add one point per Magnakai Discipline, including the later-book "above three" variation.
- Left 21 RNT cases reader-directed where the printed result depends on an active weapon, unspecified missile bonus, or prior item-use history.

## 3.4.2 - Internal Testing

- Added the complete source Combat Skill and ENDURANCE catalogue for all 172 Book 9-12 combat encounters.
- Added 141 clear victory routes and 9 clear evade routes; fights with special outcome wording remain reader-directed until their individual rules are verified.

## 3.4.1 - Internal Testing

- Added 117 source-verified mandatory section effects across Books 9-12: unavoidable ENDURANCE losses, required meals, full recovery events, and the Book 12 Bow loss.
- Preserved the printed Book 11 Section 74 exception: Huntmastery cannot replace that required meal.
- Added regression coverage for representative effects in every newly testable book.

## 3.4.0 - Internal Testing

- Enabled Books 9-12 as internal testing campaigns with reader navigation, saves, manual tools, fresh Magnakai setup, and campaign handoffs.
- Implemented Books 9 and 10 five-item entries, Book 11's retained-equipment continuation and six-item standalone setup, and Book 12's six-item entry with its cold-weather kit.
- Kept the Books 9-12 source-link baseline data as the work queue for the remaining section automation pass.

## 3.3.0 - 2026-08-07

- Completed the Book 8 source review and promoted The Jungle of Horrors to the playable testing path.
- Added Book 8 mandatory section effects for the gate guard, disturbed rest, monastery meal, Fireseed blast, and needle-spine injuries.
- Added the official Book 9-12 folder metadata, import validation, install-page links, and complete per-section source-link baselines.
- Kept Books 9-12 deliberately unavailable as playable campaigns until their conditional routes, combat, equipment transfers, and automation are reviewed.

## 3.2.0 - 2026-08-07

- Completed the source-first Books 2-7 section audit and recorded the coverage in `docs/BOOK2_TO_7_SECTION_AUDIT.md`.
- Automated Book 2 Section 290's poisoned-food meal replacement.
- Added the Book 6 Jakan tournament penalty and its zero-roll break route without changing the Kalte bow behavior.
- Added Book 7 Section 53's bat-swarm injury and Sections 250/267 Lorestone recovery effects.

## 3.1.9 - 2026-08-07

- Completed the Book 1 section audit for availability rules and automation opportunities.
- Added the missing mandatory 2 ENDURANCE loss at Section 320 after the Kraan claw attack.

## 3.1.8 - 2026-08-07

- Fixed the Book 6+ Disciplines tab to lead with the Magnakai Action Chart and the current Magnakai Disciplines.
- Kept the original Kai Disciplines visible below as legacy disciplines, with Weaponmastery weapons and Magnakai rank shown clearly.

## 3.1.7 — Unreleased

- Added internal session-scoped QA and diagnostic support for playtesting.

## 3.1.6 — 2026-07-31

- Added bottom-right resize grips to eligible Quick Actions and active-tab cards for live, free width-and-height resizing within their existing section.
- Added practical minimum dimensions, section-width clamping, and internal scrolling so compact custom cards keep every control accessible without overlapping neighboring cards.
- Added an **Auto Size** card-menu option alongside the existing Small, Medium, and Large presets.
- Saved custom dimensions per Windows player, card, and tab in UI preferences, with cancellation restoring the previous dimensions without saving.

## 3.1.5 — 2026-07-28

- Added square drag handles to the Quick Actions and active-tab cards so players can reorder them on the existing grid without allowing cards to overlap or leave their section.
- Kept each tab's card order independent and stored layout changes in per-player UI preferences rather than campaign saves.
- Kept the Book/Section/END/Gold/CS summary and bottom status bar static, and made the Tabs row collapse-only.
- Preserved the card menu's arrow controls as a keyboard and touch-friendly reorder option, including access by clicking the new drag handle.
- Removed the obsolete native HTML drag system so it cannot compete with the constrained pointer-based card sorter.

## 3.1.4 — 2026-07-27

- Made game saves crash-safe by writing each save to a temporary file and atomically replacing the previous one, so an interrupted autosave can no longer corrupt a campaign.
- Recovered gracefully from an unreadable or corrupt save file instead of failing to load.
- Confined save and load paths from the web interface to the managed saves folder, rejecting attempts to read or write elsewhere on disk.
- Restricted the local web API to same-origin requests from the desktop app, closing a path that let other web pages drive the assistant in the background.
- Restricted the embedded terminal bridge to same-origin connections so other web pages cannot open a session against it.
- Recovered gracefully from a missing or malformed Combat Results Table instead of crashing a combat round.
- Removed duplicate and unknown Kai Disciplines when loading a save so rank counts and discipline-based combat checks stay accurate.
- Hardened an internal list helper so it can no longer accidentally edit stored game data in place, removing a class of latent bookkeeping bug.
- Removed the unused Willpower, Magick, and Magical Staff systems carried over from the Grey Star fork, fixing a crash that could occur when using the Book 2 Karmo Potion.
- Removed the redundant "Nobles" currency, which only ever mirrored Gold Crowns, while still migrating older saves that stored gold under it.
- Simplified the desktop package to a single executable: the embedded terminal now runs from the main application instead of a separate command-line program.
- Fixed the frozen single-executable terminal worker so it attaches to WinPTY's parent console before reopening its input and output streams, allowing the embedded REPL to start without a separate console window (issue #12).
- Changed Small dashboard cards to a compact 220-pixel width and allowed Drop Item rows to wrap instead of overflowing the card (issue #13).
- Made the embedded CLI return to the latest output when the player types, and made text panels shrink to fit narrow terminals without growing wider than the established layout (issue #14).
- Replaced the four temporary series-divider symbols with the approved angular wolf-mask sigil; Kai, Magnakai, Grand Master, and New Order share the same theme-aware mark until their individual designs are revisited (issue #15).
- Corrected the distribution notice for the owner-cleared cover and title artwork and included `NOTICE.md` in both the one-folder build and installed application (issue #16).

## 3.1.3 — 2026-07-24

- Changed Small cards from proportional columns into compact 170-by-150-pixel tiles where content permits.
- Reflowed statistic controls on Small cards into two deliberate rows, with the Set field and button on the second row.
- Kept long card content visible by allowing compact tiles to grow vertically without horizontal clipping.

## 3.1.2 — 2026-07-24

- Fixed dashboard card sizing so Small is one-third width, Medium is one-half width, and Large uses the full available width.
- Preserved those proportions in narrow desktop layouts while falling back to full-width cards on phone-sized windows.
- Removed nonfunctional Size controls from the tab bar.

## 3.1.1 — 2026-07-24

- Added clear **Start New Campaign** entry points in the Reader panel and Flight from the Dark book details.
- Opening that route now takes the player directly to Book 1 character creation, including for players who normally use the embedded CLI.
- Protected existing campaigns: setup does not change a save until the final creation action, warns before replacing real progress, and offers a return to the current campaign.

## 3.1.0 — 2026-07-24

- Added Book 1 Quick Start and Guided Character Creation, including stat rolls, Kai Discipline selection, Weaponskill, and starting-find rolls.
- Fixed Project Aon ZIP import support alongside extracted-book import.
- Fixed desktop startup so the application uses a windowed executable without spawning a blank Windows Terminal tab; the embedded CLI remains available through its dedicated worker.
- Updated the home-page title treatment with a series-aware, theme-aware Kai wolf-eye-and-claw sigil without changing the library layout.
- Added source smoke coverage for character-creation drafts and packaging behavior.
