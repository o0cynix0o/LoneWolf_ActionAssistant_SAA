# Soundtrack Design Contract

## Purpose

The soundtrack is optional background music for a Lone Wolf campaign. It is a
single player shared by Library, Campaign, Reader, Tools, and Console. It must
never change campaign state, interrupt a combat action, or obscure the book
text. The bundled source files remain the approved MP3 masters in `music/`.

This document defines the behavior before the player and packaged assets are
implemented. Licensing evidence and the attribution ledger live in
`music/MUSIC_LICENSE_AUDIT.md`.

## Player Contract

### Default behavior

- Music is off on a fresh install. Nothing starts unexpectedly.
- The first explicit Play action is the user gesture that permits playback.
- The player begins with the selected track, playlist, and volume. It loops or
  advances according to the selected playback mode.
- Campaign state, book choice availability, saves, combat, and automation do
  not depend on music. A playback failure is non-fatal and visible only in the
  player status.
- The selected playlist, shuffle/repeat preference, volume, and enabled state
  are application preferences. They use the same local-plus-`/api/ui-preferences`
  pattern as theme and surface preferences.

### Navigation and persistence

- Campaign, Reader, Tools, and Console all operate on the same live save and
  expose the same player state.
- Before a document navigation, the player records the source track, elapsed
  position, queue order, and whether it was playing in session storage.
- On the next page, the controller restores the selected track and seek
  position. It attempts to resume only after a prior in-app Play gesture; if
  the webview denies autoplay, the compact player presents a clear Resume
  action instead of silently failing.
- The transition between separate HTML documents can have a brief audible
  pause. The current architecture cannot guarantee a gapless transition between
  `index.html` and `assistant.html` without a much larger persistent-shell
  rewrite. The chosen contract is reliable resume, not fake continuity.
- The player pauses when the app window is closed. On the next launch it
  remembers the user's music preferences but does not automatically begin
  playing.

### Playback modes

- `Playlist`: advance through the selected mood group in its listed order.
- `Shuffle`: choose a non-repeating next item from the selected mood group.
- `Repeat track`: repeat the current item.
- `Repeat playlist`: continue from the first item after the last item.
- `Off`: stop playback and preserve the selected playlist for later.

## Mood Playlists

The playlist names describe atmosphere, not rules. A section, combat, or book
never forces a track change in version one. The player stays under the user's
control; automatic mood scoring can be considered later after real play
testing.

| Playlist | Intended moments | Initial tracks |
| --- | --- | --- |
| `Journey` | Reading, travel, ordinary exploration | Lord of the Land; Magic Forest; River Flute; Shores of Avalon; Medieval Ambient; Mystic Medieval Ambient |
| `Tavern and Rest` | Towns, pauses, recovery, between-session reading | Medieval City/Tavern Ambient; River Flute; Lord of the Land; Medieval Ambient |
| `Ancient Mysteries` | Kai lore, ruins, divination, strange places | Mystic Force; Magic Forest; Mystic Medieval Ambient; Mystic Fantasy Orchestral; Orchestral Medieval Ambient |
| `Dark Roads` | Danger, Darklords, infiltration, hostile terrain | Firesong; Shamanistic; Rites; Ritual; Fantasy Medieval Epic; Mountain Knight/Castle |
| `All Approved Tracks` | Long sessions where the player wants variety | Every ledger-approved track, shuffled by default |

The manifest must use the human-readable names above and keep the source
filenames internal. Each manifest entry will include the attribution identifier
from the audit ledger, artist, source, mood groups, duration, and a package-safe
relative asset path.

## UI Surfaces

### Compact player

Every main page receives the same compact control in the shared app shell:

- Track title and current playlist.
- Play/Pause, Previous, Next, and a volume/mute control.
- A small status label: `Off`, `Playing`, `Paused`, `Resume available`, or a
  plain-language error.
- A link or button opening the full Music panel in Tools.

The compact control is deliberately secondary to campaign navigation. It uses
the established action-ribbon visual treatment, remains keyboard accessible,
and keeps its text visible in both Borderless and Bordered surface styles.

### Campaign and Reader

- Campaign shows the compact player in the right-hand utility area, beside
  Roll, Combat, Map, and Save, without displacing choices or recovery actions.
- Reader shows the compact player in the companion rail beneath Campaign
  information. Reader controls do not alter the book iframe styling.
- Both surfaces open the same Tools Music panel for queue and credits.

### Tools Music panel

The full panel lives under Tools, alongside existing Settings and campaign
tools. It contains:

- On/Off and volume controls.
- Playlist selector, track selector, shuffle, repeat, and transport controls.
- Now playing title, elapsed time, and a compact queue.
- The source/artist/license credit for the current item and a link to the
  bundled attribution notice.
- A concise explanation that the music is optional background audio.

No download, export, copy-file, or raw asset-path controls are exposed.

## Storage Keys

The final key names will be added to both `assets/js/lw-settings.js` and
`app_server.py`'s allowlist:

| Preference | Proposed key | Default |
| --- | --- | --- |
| Enabled | `lonewolf_redux.music.enabled.v1` | `off` |
| Volume | `lonewolf_redux.music.volume.v1` | `0.35` |
| Playlist | `lonewolf_redux.music.playlist.v1` | `journey` |
| Shuffle | `lonewolf_redux.music.shuffle.v1` | `off` |
| Repeat mode | `lonewolf_redux.music.repeat.v1` | `playlist` |

Transient session state is separate from preferences:

- `lonewolf_redux.music.session.v1`: current manifest ID, seek position, queue
  order, and the last known playing state.

It is intentionally session-only so a later app launch does not start music
without a fresh Play action.

## Accessibility and Failure Handling

- All transport controls have labels, visible focus states, and keyboard access.
- Volume is capped to the browser's standard `0..1` range and starts at 35%.
- The engine reports a missing asset, decoding failure, or autoplay block in the
  compact player and Tools panel without affecting the campaign.
- Changing themes or surface style immediately restyles the player through the
  shared design tokens.

## Scope Boundary

Phase 3 adds the music manifest, credits, packaging rules, and local asset
staging. Phase 4 adds the actual controller and compact controls. Version one
does not include combat-driven music, per-book soundtracks, crossfades, or a
gapless native audio service.
