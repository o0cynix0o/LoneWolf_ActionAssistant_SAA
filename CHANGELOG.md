# Changelog

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
