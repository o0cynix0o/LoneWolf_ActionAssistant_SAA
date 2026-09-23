# Lone Wolf UI redesign prototypes

These are isolated, static design studies. They intentionally do not call the
application API or mutate campaign state.

For the implementation-level redesign contract, see
[Unified UI Implementation Guide](../docs/UNIFIED_UI_IMPLEMENTATION_GUIDE.md).

- `index.html` compares the four directions.
- `campaign-desk.html` is the compact, tool-forward direction.
- `combat-mode.html` is the encounter-first combat-state direction.
- `reader-first.html` gives the book and current choice centre stage.
- `library-command.html` is the campaign-library direction.

Run `python -m http.server 8766` from the repository root, then open
`http://localhost:8766/design-prototypes/`.
