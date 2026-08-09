# Release 3.5.1 Internal Testing

## Scope

This release packages the completed Books 13-29 automation, campaign testing,
and documentation work that landed after the earlier 3.5.0 release. It also
replaces the frozen desktop CLI's WinPTY redraw path with pipe transport and
browser-side line editing.
It also retries the atomic save-file replacement when Windows briefly locks a
save during antivirus or indexing activity.

## Validation

- Full source suite: 212 tests passed.
- Frozen application `--self-test`: passed.
- Frozen CLI direct pipe exchange: prompt, `help`, and `exit` passed.
- Frozen CLI through the real local WebSocket bridge: prompt, `help`, and
  `exit` passed.
- Silent installer installation into an isolated temporary folder: passed.
- Installed executable `--self-test`: passed.

## Installer Integrity

| Asset | SHA-256 |
| --- | --- |
| `Lone.Wolf.Action.Assistant.Setup.exe` | `806987dae59771f62d02740ac741833a2bc2d3a35df6ee34d9e69118c878f4e0` |

The release uploads both the installer and its `SHA256SUMS.txt` companion.
Project Aon books remain user supplied and are not included in either asset.
