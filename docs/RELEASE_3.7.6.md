# Lone Wolf Action Assistant 3.7.6

Version 3.7.6 is an internal-testing usability release focused on book
transitions, trustworthy choice guidance, readable campaign tools, and a more
cohesive Campaign interface.

## Player-facing changes

- Completed books now lead into a two-step onboarding screen. Read the next
  book's full **Story So Far**, complete its carried Action Chart setup, and
  then begin Section 1.
- Book-transition Gold and Weaponskill results use one-shot **Roll 0-9** cards.
  The result is saved across refreshes and cannot be rerolled for a preferred
  outcome.
- Equipment setup blocks progress when a new weapon would exceed the two-weapon
  limit and identifies the replacement that must be selected.
- Story routes now use the live Action Chart to highlight satisfied discipline,
  item, Special Item, money, arrow, rank, lore-circle, and section-roll
  requirements. Optional refusal routes remain neutral.
- Directional item matching allows a two-space Rope to satisfy a shorter Rope
  requirement without allowing the shorter Rope to satisfy the longer one.
- The Campaign includes a spoiler-safe compendium for encountered items,
  monsters, people, and places, with known effects, statistics, discovery
  counts, and achievement progress.
- **At a glance** now includes a collapsible Section Activity summary instead
  of redundant quick-action buttons.
- Completed combat is presented as a battle timeline with printed outcome text,
  combatants, and valid recovery actions. Round controls disappear when the
  fight is over.
- The Console provides Companion Rail and Focus Dock layouts, a larger terminal,
  centered content, and clearer navigation back to Tools.
- A Campaign-only setting can hide the resume/current-objective banner. Hidden
  means removed from layout: metrics and tabs move into the vacated space.
- The Campaign music card uses balanced spacing while preserving every playback
  control.

## Reliability and validation

- Either-or discipline gates and Random Number route gates now use the correct
  live requirements.
- Temporary cheat/test changes are isolated from normal campaign state.
- Choice, transition, inventory, compendium, combat, Console, settings, and
  Campaign-layout behavior all have regression coverage.

## Verification

- Complete source regression suite and source self-test.
- Frozen Windows executable self-test and visible installed-window launch.
- Inno Setup installer build and version-resource verification.
- Versioned Docker image rebuild, container recreation, and live HTTP/UI check.
- Installer, checksums, and release guide published with the tagged release.

