# Release 3.7.0 Internal Testing

## Scope

This release adds optional licensed background music to the Windows desktop
application. The soundtrack is off by default and has no campaign, combat,
save, route, or automation behavior. Players can start it from the Campaign
Player card or Reader companion controls, then manage playlists, shuffle,
repeat, volume, queue position, and credits in Tools.

The installer includes the approved audio assets and `THIRD_PARTY_MUSIC.md`.
It does not expose downloads, exports, or raw asset paths. Project Aon books
remain player supplied and are not included in the installer or release asset.

## Validation

- Full source suite: 229 tests passed.
- Source application `--self-test`: passed.
- Frozen application `--self-test`: passed.
- Inno Setup installer build: passed.
- Every packaged soundtrack asset matches its approved SHA-256 manifest entry.

## Installer Integrity

| Asset | SHA-256 | Size |
| --- | --- | --- |
| `Lone Wolf Action Assistant Setup.exe` | `2dbb70f018381f072a903ff28b120912b60e43b13d41517d0a10fba377494497` | 172,615,351 bytes |

Project Aon books remain player supplied and are not included in the installer
or release asset.
