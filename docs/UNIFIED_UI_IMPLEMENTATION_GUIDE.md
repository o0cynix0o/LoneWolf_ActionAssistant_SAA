# Unified UI Implementation Guide

## Purpose

This document turns the static studies in [design-prototypes](../design-prototypes/)
into an implementation contract. It is written for an agent taking over the
redesign. Follow the visual and interaction rules here, but keep the existing
campaign engine, save format, book importer, automation catalogues, and CLI
backend intact.

The studies are deliberately static. Their Book 6 / section 219 data is sample
content used to demonstrate hierarchy. In production, every visible value must
come from the live campaign state.

## Product Model

Lone Wolf is one campaign with several useful views, not several applications.

| Surface | Job | Must share |
| --- | --- | --- |
| Library | Choose, inspect, import, or resume books | Active campaign and current book status |
| Campaign | Normal play with text and assistant together | Section, choices, vitals, inventory, combat, saves |
| Reader | Text-first alternative play mode | The exact same section and campaign state as Campaign |
| Tools | Full assistant workspace | The exact same live state as Campaign and Reader |
| Console | Keyboard-first control | The same saved campaign and command history |
| Settings | Preferences and run configuration | Existing settings storage and active run |
| Book Manager | Import and inspect local book files | Existing native import API and book-file status API |

Never create a Reader-only campaign, a separate Tools save, or a duplicate
state object for a view. Navigation changes presentation; it does not start a
new run. The main promise is: **leave a view, return later, and find the same
book and same section.**

## Global Shell

Every production view should inherit the shared shell from `common.css`.

### Top bar

The sticky top bar contains three groups, in this order:

1. **Brand:** wolf-mask mark plus `Lone Wolf`; it always returns to Library.
2. **Primary navigation:** Library, Campaign, Reader, Tools. Console may be a
   top-level destination when there is room; Settings belongs under Tools.
3. **Campaign chip:** a small live-state indicator, such as `Book 6 · section
   219` or `Reading Book 6`. It is not a button and must never imply a second
   campaign exists.

The active route uses `aria-current="page"`, the accent text color, and the
raised selected background. On small screens hide the brand wordmark and the
campaign chip before hiding navigation; the nav becomes horizontally scrollable.

### Tokens and typography

Use named design roles, not hard-coded component colors:

| Role | Token | Use |
| --- | --- | --- |
| Canvas | `--canvas` | Page background |
| Surface / raised surface | `--surface`, `--surface-raised` | Panels and selected controls |
| Borders | `--border`, `--border-strong` | Structure, focus, selected controls |
| Ink / muted / quiet | `--ink`, `--muted`, `--quiet` | Main, supporting, inactive text |
| Accent | `--accent` | Heading and interactive emphasis |
| Gold | `--gold` | Eyebrows and book/game emphasis |
| Green | `--green` | Live, reading, valid, or complete state |
| Danger | `--danger` | Destructive actions only |

Use Georgia or the configured serif stack for headings and book titles. Use
Segoe UI/Arial or the configured sans stack for all controls, labels, and data.
Letter spacing is normal except small uppercase eyebrows. Do not introduce
gradients, decorative light blobs, oversized marketing hero text, or a second
palette that fights the active theme.

### Shared components

- **Page:** maximum width 1480px; 40px desktop outer gutters and 24px mobile
  gutters; 28px top / 56px bottom desktop spacing.
- **Panel:** dark surface, one 1px border, 7px radius. A titled panel uses a
  14x16px header and a 16px body separated by a border.
- **Primary button:** pale cyan fill with dark text. Use it only for the one
  obvious next action on a surface, normally `Start Current Campaign`.
- **Secondary button:** transparent dark surface, cyan outline/text. Use it
  for navigation and non-destructive commands.
- **Ghost button:** transparent border until hover. Use for low-risk secondary
  actions such as `View book details`, not for a primary command.
- **Status badge:** compact outlined pill. `Reading` is green; `Ready` is
  gold; queued/locked is quiet gray; destructive status is never a badge.
- **Metric:** compact label/value cell. Labels are uppercase small sans text;
  values use the accent color. Do not present vitals as large dashboard tiles.
- **Toast:** bottom-right, green-bordered confirmation for a completed action;
  it must not obscure a choice or require dismissal for normal play.

Buttons that are unavailable should be disabled with a concise reason exposed
through a tooltip or nearby description. Do not remove ordinary book choices
simply because a discipline gate is unavailable; keep the wording in the reader
and mark/explain the requirement where the assistant can do so safely.

## Design Study Index

`design-prototypes/index.html` is a comparison page, not a production route.
It establishes three principles:

1. The active campaign is the anchor for every view.
2. `Start Current Campaign` means open the saved book and saved section. It
   must never start a fresh Book 1 campaign.
3. Campaign Desk, Reader First, Library Command, and Tools are complementary
   shapes of the same product, not competing redesigns.

The three study cards each have a cover, status, concise rationale, and one
primary navigation action. Reuse this comparison structure only for internal
design review; do not ship it as an extra user-facing home page.

## Library Command

`library-command.html` defines the Library/home-screen hierarchy.

### Elements

1. **Library heading:** eyebrow `Your campaign library`, a short title, and a
   one-sentence explanation that books retain their real play state.
2. **Current campaign card:** shows `Reading`, current book title, current
   section/progress, and a full-width primary `Start Current Campaign` button.
   This is the only primary CTA in the Library header.
3. **Series navigation:** Kai, Magnakai, Grand Master, and New Order. Each
   row has a series name and concise state summary. The current series is
   visually selected.
4. **Book shelf:** cover cards grouped by active series. Each card shows book
   number, title, state, and a small state description. The current book has a
   green border and reading state. Later/locked books may be muted, but retain
   a readable title and purpose.
5. **Book details rail:** selected-book cover, state, series, progress, current
   section, campaign save state, assistant readiness, and actions. This is a
   detail view, not a second primary navigation system.
6. **Library management panel:** imports and testing belong near the collection
   rather than on an unrelated page. Production may link to a dedicated Book
   Manager, but the wording and visual relationship must remain clear.

### Behavior

- Default to the active campaign's series; show Kai when no campaign exists.
- Selecting another book to browse must not overwrite the current campaign.
- Opening the current campaign always routes to its saved position.
- Installed, playable/testing, ready, completed, reading, and locked are
  distinct facts. Do not label an installed source file `Playable` unless the
  app's book support metadata says it is playable.
- Book cards are repeated items and may be cards. Page sections themselves
  should remain unframed or be single panels, never cards nested inside cards.

### Responsive rules

- Desktop: 220px series rail, flexible shelf, 345px detail rail.
- At about 1100px: keep series rail and shelf; move details below the shelf.
- At about 760px: stack heading, rails, and shelf; series navigation becomes a
  horizontal scrolling list; book shelf becomes two columns.

## Campaign Desk

`campaign-desk.html` is the normal play layout. It is dense by intention, but
the story and next legal action remain the center of gravity.

### Elements

1. **Campaign rail:** cover, reading status, current title/series, full-width
   `Start Current Campaign`, then a compact sequence of books in the current
   series. The active row is green; future rows show installed/ready state.
2. **Workspace header:** `Current campaign` eyebrow, `Continue your journey`
   heading, a direct sentence about resuming the saved section, and a prominent
   section number aligned to the right.
3. **Metric row:** Endurance, Combat Skill, Gold, and current game mode. These
   answer the player’s immediate questions without opening the Action Chart.
4. **Task tabs:** Story, Action Chart, Inventory, Combat, Notes. Tabs switch
   workspace context; their active state is visible and keyboard accessible.
5. **Story panel:** book/section label, `Current section` badge, readable story
   copy, and the legal choices. A choice contains the player-facing text plus a
   small destination. Do not separate choices from their accompanying book
   text during normal play.
6. **At a glance rail:** last action, known disciplines, compact inventory
   summary, and four quick tool buttons: Roll, Combat, Map, Save.

### Behavior

- The story panel reflects the current reader section. Choices advance the
  same state the assistant uses.
- The action rail must not preempt the reader's wording. It supplements it.
- Quick tools open/perform established assistant actions; they must not invent
  alternate combat, inventory, or save flows.
- `Start Current Campaign` is a recovery/resume action; when already in the
  campaign it may refresh or focus the saved current section, but never creates
  a new character.

### Responsive rules

- Wide desktop: three columns, with book context on the left and quick tools
  on the right.
- Around 1100px: two columns; the right rail moves below the main workspace.
- Around 760px: one column. Preserve story, choices, and metrics before moving
  secondary activity and quick tools below them.

## Reader First

`reader-first.html` is an alternate play mode for people who want book text to
be dominant. It is not a stripped-down or disconnected campaign view.

### Elements

1. **Reader heading:** `Reading · Book N`, book title, section-aware subtitle,
   and Previous / Start Current Campaign / Next Section navigation.
2. **Reading surface:** a calm, light paper-like page inside the dark app. It
   has a section kicker, title, generous serif prose, horizontal rule, and
   large text-based book choices. It may adopt reader theme settings, but must
   preserve local Project Aon content and avoid rewriting its text.
3. **Campaign companion:** current vitals and difficulty, with a reading badge.
4. **Assistant companion:** Roll 0-9, Combat, Inventory, and Action Chart.
5. **Choice check:** number of routes plus an explanation of known requirements
   or availability. This informs choices; it does not replace reader wording.
6. **Reading tools:** Story So Far, Map, Notes, and Settings.

### Behavior

- Reader uses the exact same section, rolls, inventory, combat, automation,
  notes, achievements, and saves as Campaign.
- The light reading surface is a controlled reading treatment, not a new
  application theme. The surrounding shell continues to honor user settings.
- Choices remain full-width, legible, and in book order. A discipline-required
  choice should remain visible but communicate its availability clearly.

### Responsive rules

- Desktop: fluid reader column and roughly 314px companion rail.
- Below about 900px: stack companion panels below the reading surface.
- Below about 600px: reduce reading padding; allow top reader controls to
  scroll horizontally rather than wrapping into unstable rows.

## Tools Workspace

`tools.html` defines the full assistant destination. It is for focused
bookkeeping and testing, not a dumping ground for every control at once.

### Elements

1. **Tools heading:** campaign-assistant eyebrow, one-sentence purpose, and
   persistent current campaign context.
2. **Tool navigation:** vertical named controls with short descriptions:
   Action Chart, Inventory, Combat, Random Number Table, and Notes/Saves. The
   production list may also include Disciplines, Sections, Achievements, and
   Settings when they already exist.
3. **Current-campaign summary:** title/section, Reading badge, four metrics,
   and compact discipline/combat-mode context tokens.
4. **Quick roll:** a discrete Random Number Table surface showing the latest
   result and an obvious `Roll 0-9` action.
5. **Active tool panel:** one detailed view at a time. Action Chart uses small
   rows; Inventory groups weapons/backpack/special items/meals; Combat shows
   current enemy/recent fight/ratio; Notes/Saves shows campaign memory and
   checkpoint data.

### Behavior

- Tool navigation changes the detailed panel without losing state or moving the
  player away from the active campaign.
- A roll records the existing RNT result in the current campaign and confirms
  it with a toast. Do not generate a display-only roll.
- Inventory reordering, drop actions, combat rounds, save/load, achievements,
  game modes, and CLI commands must continue to use the existing backend and
  validation rules.
- Console is a full Tools variant: hide the regular tool navigation only when
  it would distract from the terminal, but keep current campaign context and a
  return route to regular Tools.

### Responsive rules

- Desktop: 260px tool navigation plus flexible content; summary has a flexible
  campaign panel and 300px quick-roll panel.
- Below about 850px: stack content; tool navigation becomes a horizontally
  scrolling strip with stable button widths.
- Below about 520px: Action Chart and Combat detail grids become one column.

## Settings And Book Manager

Settings is a Tools view, not a separate modal that can fall out of sync with
the rest of the application. Group Game Modes, appearance/theme, reader style,
save slots, layout reset, and closed-card recovery in clearly titled panels.
Keep the existing persistence API and let a theme update every surface.

Book Manager is a Library-adjacent utility. It contains:

- a collection summary such as `29/29 installed`;
- native `Import ZIP Files`, `Import Extracted Folder`, and `Open Managed
  Books Folder` actions;
- a live list of all supported books from the book-file API;
- per-book Installed / Not installed state, series label, Project Aon link,
  and Library return link;
- a concise managed-folder explanation, not a wall of raw paths.

Book import never changes an active campaign. It only updates local managed
book files and the availability display.

## Implementation Sequence

1. Install shared tokens and global shell without touching game logic.
2. Build Library as the campaign home and make `Start Current Campaign`
   unambiguous.
3. Build Campaign Desk over the existing reader and assistant renderers.
4. Add Reader First as a presentation switch over the same state.
5. Add Tools navigation and Console presentation over existing tool/CLI logic.
6. Consolidate Settings and Book Manager; remove duplicate settings markup.
7. Test every route with Book 1, a Book 5-to-6 handoff, Book 6/7 play,
   Grand Master, New Order, game modes, permadeath, save/load, CLI, import,
   inventory limits, combat, maps, achievements, and phone-width layouts.

## Acceptance Checklist

- [ ] All visible book/section/vital data comes from live state, not prototype
  sample data.
- [ ] Start Current Campaign opens the saved book and section in every view.
- [ ] Campaign, Reader, Tools, and Console alter one shared campaign state.
- [ ] Status names reflect real metadata: reading, installed, ready/testing,
  completed, and locked are not interchangeable.
- [ ] Theme preferences apply consistently to Library, Campaign, Reader,
  Tools, Settings, and Book Manager.
- [ ] Existing reader text and book choices remain authoritative and readable.
- [ ] Existing automation, combat, saves, achievements, CLI, and import APIs
  remain intact.
- [ ] Layout has no horizontal page overflow at desktop and phone widths.
- [ ] Keyboard focus, button names, tooltips, disabled reasons, and active-nav
  state are accessible.
- [ ] Static design studies remain clearly labeled as studies and are never
  mistaken for a second playable app.
