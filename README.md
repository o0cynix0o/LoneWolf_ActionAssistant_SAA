# Lone Wolf Action Assistant 3.4.7 Internal Testing

Lone Wolf Action Assistant is a standalone Windows desktop play aid for the
*Lone Wolf* gamebooks. It is a digital Action Chart, reader companion, and
campaign tracker: install the app, import your own Project Aon HTML books, and
play in one desktop window without installing Python or starting a browser
server yourself.

**Internal-testing release:** [download the current Windows installer](https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/releases/latest).

Version: **3.4.7 Internal Testing**

## What You Can Play

Books 1-12 are playable internal-testing campaigns:

| Series | Books | Support |
| --- | --- | --- |
| Kai | 1-5 | Character creation, campaign handoff, reader routes, inventory, combat, rolls, endings, saves, and achievements |
| Magnakai | 6-12 | Fresh Magnakai setup or campaign handoff, disciplines, reader routes, inventory, combat, rolls, endings, saves, and achievements |

The assistant records source-verified route gates, section effects, combat
exceptions, item events, Random Number Table results, achievements, and book
completion. It leaves choices that need personal judgment or an unmodeled puzzle
answer in the reader, where they belong.

## Start Here

1. Install the release from the link above.
2. Open **Install Books** in the app.
3. Import your own standard Project Aon ZIP files or extracted book folders.
4. Start Book 1, continue a completed campaign, or choose a supported fresh
   Magnakai setup.

Book files are not included in this repository, installer, or release assets.
The importer expects a valid folder containing at least `title.htm` and
`sect1.htm` for one of these Project Aon folder names:

```text
01fftd  02fotw  03tcok  04tcod  05sots  06tkot
07cd    08tjoh  09tcof  10tdot  11tpot  12tmod
```

## Play Your Way

- **Auto Mode** applies available section helpers and keeps the Action Chart in
  sync as you play.
- **Manual Mode** keeps the sheet, inventory, saves, and achievements while you
  choose when to apply the book's bookkeeping.
- **CLI Mode** opens the embedded keyboard-first terminal against the same local
  save.
- **Story, Easy, Normal, Hard, and Veteran** set campaign difficulty. Optional
  permadeath is available outside Story mode, and combat can use automatic or
  manual CRT resolution.

When a book ends, the next book opens on **Story So Far** before its setup. Gear
does not cross a book boundary merely because it was once carried: an item only
remains when the book text returns or preserves it.

## Documentation

- [Wiki home](https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/wiki)
- [Getting started](https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/wiki/Getting-Started)
- [Game modes and difficulty](https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/wiki/Game-Modes)
- [Book support matrix](https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/wiki/Book-Support-Matrix)
- [Strategy guides](https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/wiki/Strategy-Guide)
- [Campaign testing report](docs/DEEP_CAMPAIGN_TEST_REPORT.md)

## Storage And Privacy

- Application resources are bundled and read-only.
- Saves, preferences, logs, and current position are private to each Windows
  player under `%LOCALAPPDATA%\Lone Wolf Action Assistant`.
- A current-user install stores books under that user's Local AppData; an
  all-users install uses shared ProgramData book storage.
- Uninstall does not intentionally remove books or player saves.

## Building From Source

```powershell
.\build.ps1
```

The build creates the frozen desktop application and Inno Setup installer, then
runs the frozen self-test. See [Building](docs/BUILDING.md) for prerequisites
and release checks.

## Licensing And Trademarks

Project Aon book files are not part of this project or its build artifacts. See
[NOTICE.md](NOTICE.md) and the [Project Aon license](https://www.projectaon.org/en/Main/License)
before distributing any material derived from the books.
