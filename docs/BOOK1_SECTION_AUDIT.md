# Book 1 Section Audit

Status: complete on 2026-08-07.

This review compares the installed Project Aon `Flight from the Dark` source pages
(`sect1.htm` through `sect350.htm`) with the Book 1 route-flow and simple-automation
data. It examines both player-choice availability and mandatory state changes.

## Coverage

- 350 of 350 numbered sections parsed.
- 556 source links found; 555 distinct recorded routes. Section 21 intentionally links
  to Section 189 twice at different stages of the same marsh roll sequence.
- 33 explicit discipline, item, or gold-gated choices found; all are represented by
  route-check data.
- All mandatory numeric END, Combat Skill, and Gold changes have automation coverage.

## Review Rules

- A route is gated only when the book explicitly requires a recorded discipline, item,
  Gold amount, rank, or prior state.
- Ordinary decisions, including a choice to fight while unarmed, remain available.
- Random tables, staged rolls, combat thresholds, and forced continuations are resolved
  by their dedicated controls rather than presented as freely selectable routes.
- Optional loot remains player-controlled. A full inventory should lead to an exchange
  or discard decision, not make a valid item disappear.
- Narrative-only details without a later rules consequence, such as temporarily taking
  the Prince's horse or borrowing the surgeon's cloak, are not recorded as campaign
  state.

## Confirmed Correction

Section 320 states that a Kraan claw attack costs 2 ENDURANCE. The source had no
corresponding automation entry, so `data/book1-simple-automations.json` now deducts
2 END and `testing/test_saa_smoke.py` protects that behavior.

## Next Implementation Step

The audited route data can now drive the Choices panel: show eligible choices by
default, let players reveal unavailable choices with their reason, and retain the
unaltered Project Aon text in the reader.
