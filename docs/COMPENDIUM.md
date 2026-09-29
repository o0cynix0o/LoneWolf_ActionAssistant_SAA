# Compendium

The Tools workspace includes a spoiler-aware Compendium with five views:
Items, Bestiary, People, Places, and Achievements.

Discovery is derived from the existing campaign save. Items unlock from carried
and historical inventory records, creatures unlock from active and completed
combat records, and people and places unlock when their source sections have
been visited. Unknown entries display without their names or details. An item's
later use remains separately hidden until the relevant section is visited or
the player explicitly reveals it.

Inventory rows include an `i` control with a short mechanical summary and a
link to the full entry. The control supports keyboard focus, Escape, and an
outside click to close.

## Rebuilding the catalog

The generated `data/compendium.json` covers the installed 29-book source set.
It stores names, statistics, mechanics, and source references, but not copied
story prose. Rebuild it after changing audited section-flow data or reviewed
facts:

```powershell
python testing/build_compendium_catalog.py
```

CI or a local verification run can detect a stale generated file without
rewriting it:

```powershell
python testing/build_compendium_catalog.py --check
```

Human-reviewed summaries and mechanics belong in
`data/compendium-overrides.json`. This keeps extracted names separate from
verified gameplay claims and gives uncertain or spoiler-sensitive facts an
explicit review point.
