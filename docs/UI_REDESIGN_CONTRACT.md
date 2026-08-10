# Production UI Redesign Contract

This document turns the static studies in `design-prototypes/` into the visual
contract for the production application. It is deliberately separate from
campaign logic: a page may change layout, but it may not create a new session,
rewrite saves, or change a book rule.

## Canonical Screens

| Production surface | Visual reference | Primary job |
| --- | --- | --- |
| Library | `design-prototypes/library-command.html` | Resume and select campaigns; manage books. |
| Campaign | `design-prototypes/campaign-desk.html` | Normal play with reader and Action Chart together. |
| Reader | `design-prototypes/reader-first.html` | Text-first alternate view of the same campaign. |
| Tools and Console | `design-prototypes/tools.html` | Full assistant workspace and keyboard-driven commands. |

## Shared System

All rebuilt screens use `assets/css/lw-ui-foundation.css` and its semantic
classes. Runtime themes still supply the base colors through the existing
`--lw-*` variables. The shared roles are:

- Cyan: selected or primary context.
- Green: live, valid, or currently reading state.
- Gold: book or game emphasis.
- Muted gray: inactive, unavailable, or supporting detail.
- Red: destructive actions only.

Panels use a 6px radius, one border weight, and one internal spacing system.
Buttons are command controls, not decorative cards. Each production screen
uses the same top navigation and campaign-status chip.

## State Rules

- `Start Current Campaign` always opens the saved book and saved section.
- Campaign, Reader, Tools, and Console share one server-backed campaign state.
- Reader is a presentation mode, never a second save format.
- Existing game rules, automation, combat, inventory, achievements, and saves
  remain owned by the current Python engine and frontend action handlers.

## Status Vocabulary

Use only these player-facing book states: `Reading`, `Ready to play`,
`Installed`, `Testing`, `Locked`, and `Completed`. A status must state the
book's actual availability; it cannot be used as a decorative label.

## Chunk Gates

Each implementation chunk is accepted only after its production route matches
the canonical screen at desktop and phone width, the affected controls work,
and a screenshot is captured under `docs/ui-baseline/` or a later comparison
directory. Packaging and a public release happen only after the final
cross-screen regression pass.
