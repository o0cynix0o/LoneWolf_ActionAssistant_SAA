# Release 3.5.2 Internal Testing

## Scope

This rules-correction release enforces the published Special Item carrying
limit. Books 1-7 retain their original no-limit rule. From Book 8 onward,
normal and pocket-carried Special Items share a maximum of twelve items.

The inventory displays the shared count, exposes Pocket Special Items, blocks
an over-limit gain without discarding anything, and lets a player explicitly
leave either kind of Special Item behind during a book transition.

## Validation

- Full source suite: 216 tests passed.
- Packaged executable `--self-test`: passed.
- Silent installer installation into an isolated temporary folder: passed.
- Installed executable `--self-test`: passed.

## Installer Integrity

| Asset | SHA-256 |
| --- | --- |
| `Lone.Wolf.Action.Assistant.Setup.exe` | `4d4f360c8c42cbac5878558c801b9fdfdcb3c3dc38aa827bfc54f6cdebcfae6c` |

The release uploads both the installer and its `SHA256SUMS.txt` companion.
Project Aon books remain user supplied and are not included in either asset.
