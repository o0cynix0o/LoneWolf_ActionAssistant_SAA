# New Order Campaign Test Report

## Scope

This regression pass uses temporary save, state, and reader workspaces. It
does not read or change player data.

## Campaign Matrix

The Book 21-29 campaign spine completes under each supported difficulty and
combat mode:

| Difficulty | Permadeath | CRT modes |
| --- | --- | --- |
| Story | Off (forced by the rules) | DataFile, Manual CRT |
| Easy | Off and On | DataFile, Manual CRT |
| Normal | Off and On | DataFile, Manual CRT |
| Hard | Off and On | DataFile, Manual CRT |
| Veteran | Off and On | DataFile, Manual CRT |

This is 18 completed campaign-handoff runs. Each run starts at Book 21,
opens each next book before setup, selects the required new New Order
Discipline and Grand Weaponmastery weapon, and explicitly leaves behind any
carried Backpack or weapon entries needed to receive the next five-item field
issue.

Every run saves and reloads at Book 25. The resumed run retains its
difficulty, permadeath setting, and CRT mode before advancing through Book
29. Book 29 closes the New Order run with `Run.Status` set to `Completed`.

## Combat Coverage

All 265 configured New Order combat presets across Books 21-29 start and
resolve one round in both DataFile and Manual CRT modes (530 first-round
checks). The fixture uses a fully equipped high-rank Action Chart to exercise
the supported encounter setup without depending on a specific story route.

## Remaining Boundary

This verifies the campaign spine, supported combat presets, saved run state,
and difficulty modes. Reader-directed puzzles, optional rewards, and source
rules that need a player judgment remain intentional exploratory-play work;
they are not claimed as automated routes.
