# Choice eligibility hints

The campaign reader can compare explicit route requirements in the installed
book text with the current Action Chart. The presentation deliberately uses
three states:

- **Green:** the recorded Action Chart satisfies the route requirement.
- **Grey/dashed:** the recorded Action Chart cannot satisfy the requirement.
- **Neutral:** the route is an unrestricted player decision. This includes an
  optional refusal after an eligible item-use route.

The **Settings > Appearance > Campaign Guidance** control can hide or show
these hints. Hiding them changes only the presentation; route validation and
the underlying game rules remain active. Hints are shown by default.

## Repeatable source audit

`testing/audit_route_conditions.py` scans numbered sections in every supplied
book and exercises the same route-condition parser used by the application.
Run it once for each installed source directory:

```powershell
.\.venv\Scripts\python.exe testing\audit_route_conditions.py `
  --source-root docker-data\books\lw `
  --book 1:docker-data\books\lw\01fftd `
  --book 2:docker-data\books\lw\02fotw `
  --output testing\route-condition-audit.json
```

Add further `--book NUMBER:PATH` arguments for the remaining installed books.
The checked-in report contains only coordinates, condition types, counts, and
hashes. It intentionally omits licensed story prose. Use `--show-unresolved`
for a local, transient review of ambiguous wording; do not commit that output.

An unresolved record is a review flag, not an assertion that a route is
broken. The parser stays conservative where prose depends on earlier-story
history, random-table results, or wording that cannot be safely reduced to an
Action Chart test.

## Directional item substitutes

The two-slot Rope and Long Rope can satisfy an ordinary **Rope** requirement;
they can always handle the shorter crossing or climb. An ordinary one-slot
Rope cannot satisfy a route that explicitly requires **Rope (2 spaces)** or a
Long Rope. The items retain their printed names and slot costs in inventory.
