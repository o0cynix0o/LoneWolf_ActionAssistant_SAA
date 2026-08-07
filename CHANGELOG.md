# Changelog

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
