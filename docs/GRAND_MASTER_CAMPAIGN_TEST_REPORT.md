# Grand Master Campaign Test Report

## Scope

This regression pass uses temporary save, state, and reader workspaces. It
does not read or change player data.

## Campaign Matrix

The Book 13-20 campaign spine completes under each supported difficulty and
combat mode:

| Difficulty | Permadeath | CRT modes |
| --- | --- | --- |
| Story | Off (forced by the rules) | DataFile, Manual CRT |
| Easy | Off and On | DataFile, Manual CRT |
| Normal | Off and On | DataFile, Manual CRT |
| Hard | Off and On | DataFile, Manual CRT |
| Veteran | Off and On | DataFile, Manual CRT |

This is 18 completed campaign-handoff runs. Each run begins at Book 13,
follows the normal Book 13-20 continuation flow, opens the next book before
setup, chooses the required Grand Master Discipline and Grand Weaponmastery
weapon, and supplies explicit Backpack or weapon drops whenever the next
field issue needs room.

Every run saves and reloads at Book 16. The resumed run retains its
difficulty, permadeath setting, and CRT mode before continuing through Book
20. Book 20 now closes the Grand Master run with `Run.Status` set to
`Completed` and deliberately offers no direct Book 21 continuation, because
the New Order begins a distinct character campaign.

## Combat Coverage

All 306 configured Grand Master combat presets across Books 13-20 start and
resolve one round in both DataFile and Manual CRT modes (612 first-round
checks). The fixture uses a fully equipped high-rank Action Chart to exercise
the supported encounter setup without depending on a specific story route.

## Remaining Boundary

This verifies the campaign spine, supported combat presets, saved run state,
and difficulty modes. Reader-directed puzzles, optional rewards, and source
rules that need a player judgment remain intentional exploratory-play work;
they are not claimed as automated routes.
