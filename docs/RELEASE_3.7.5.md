# Lone Wolf Action Assistant 3.7.5

Version 3.7.5 is an internal-testing maintenance release focused on reliable
campaign replacement, automatic discipline bookkeeping, actionable inventory
feedback, and clearer connection status.

## Player-facing changes

- Starting a replacement campaign always begins with a clean session-cheat
  state and the new character's legal Action Chart values.
- Kai Healing in Books 1-5 is applied automatically when entering an eligible
  non-combat section. It is reported in Section Activity and is never presented
  as a story choice.
- Section loot that does not fit remains visible with a specific capacity
  explanation and a **Manage Inventory** action.
- The native Console route now starts its WebSocket terminal correctly and
  reports a failed connection after six seconds instead of remaining at
  **Connecting** indefinitely.
- Inventory panel headings no longer repeat the pre-Book-8 carrying-limit note.
- The Campaign background-player heading has more vertical room.

## Reliability

- New-campaign creation clears active cheats, runtime overrides, achievement
  locks, and developer snapshots before the replacement state is installed.
- Abandoned browser static/download requests no longer produce noisy broken-pipe
  stack traces in the local server.
- Regression tests cover automatic Healing, cheat reset, blocked weapon loot,
  console timeout cleanup, concise inventory headings, and release metadata.

## Verification

- Completed a visible Book 1 test campaign from character creation through
  section 350.
- Verified automatic Healing in the running campaign and the absence of a
  Healing control in Choices.
- Built and self-tested the Windows frozen application and installer.
- Rebuilt and restarted the Docker image on ports 8797-8798.
