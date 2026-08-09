# Canonical Release Policy

`LoneWolf_ActionAssistant_SAA` is the only supported release source. Build and
distribute the desktop application only through `build.ps1` and the generated
Inno Setup installer. It owns the desktop shell, managed book import, save
locations, API, and the V3 save schema.

## Legacy repositories

- `C:\Scripts\Lone Wolf` is the original PowerShell implementation. Retain it
  as a read-only gameplay and save-migration reference; do not publish its
  launchers as current releases.
- `C:\Scripts\LoneWolf_ActionAssistant_Redux` is the browser-era Python
  implementation. Retain it as a read-only behavior and asset-import reference;
  do not ship `launch_lonewolf_redux.py` or `Launch-LoneWolfRedux.ps1` as a
  parallel product.

No legacy directory is deleted by this policy. Their saves, modules, and reader
assets remain available for compatibility work until V3 parity tests cover the
corresponding behavior.

## Supported campaign boundary

V3 imports and normalizes V1/V2/V3 JSON saves. Books 1-29 are the current
internal-testing support boundary: Kai 1-5, Magnakai 6-12, Grand Master 13-20,
and New Order 21-29. Each series provides its verified fresh-start contract;
the first three series also provide their normal intra-series campaign handoffs.
Book 20 is intentionally a campaign endpoint because New Order begins a
different character.

Reader HTML remains player supplied and is imported into the managed V3 books
location; it is never included in the installer.

## Release gate

Before removing any legacy launch path from a user workflow, verify the V3
desktop installer, save import/export fixtures, installed reader navigation, and
the affected Book 1-29 regression tests. Keep the old folders as references until
that gate is documented as complete.
