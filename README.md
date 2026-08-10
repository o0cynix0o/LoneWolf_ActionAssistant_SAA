# Lone Wolf Action Assistant 3.5.2 Internal Testing

Lone Wolf Action Assistant is a standalone Windows desktop play aid for the
*Lone Wolf* gamebooks. It is a digital Action Chart, reader companion, and
campaign tracker: install the app, import your own Project Aon HTML books, and
play in one desktop window without installing Python or starting a browser
server yourself.

**Internal-testing release:** [download the current Windows installer](https://github.com/o0cynix0o/LoneWolf_ActionAssistant_SAA/releases/latest).

Version: **3.5.2 Internal Testing**

## What You Can Play

Books 1-29 are playable internal-testing campaigns:

| Series | Books | Support |
| --- | --- | --- |
| Kai | 1-5 | Character creation, campaign handoff, reader routes, inventory, combat, rolls, endings, saves, and achievements |
| Magnakai | 6-12 | Fresh Magnakai setup or campaign handoff, disciplines, reader routes, inventory, combat, rolls, endings, saves, and achievements |
| Grand Master | 13-20 | Fresh Grand Master setup or Book 12 campaign handoff, Grand Master disciplines, expanded Backpack, reader routes, inventory, source-derived RNT, combat, and direct mandatory-effect catalogues, saves, and campaign achievements. |
| New Order | 21-29 | Fresh New Order setup and Book-to-book continuation, 16 disciplines, Kai Weapon, equipment, reader routes, source-derived RNT, combat, and direct mandatory-effect catalogues, saves, and campaign achievements. |

Books 30-32 do not have Project Aon-style HTML editions. They require a
separate licensed-source and conversion path before this HTML-based importer
can audit or support them.

The assistant records source-verified route gates, section effects, combat
exceptions, item events, Random Number Table results, achievements, and book
completion. It leaves choices that need personal judgment or an unmodeled puzzle
answer in the reader, where they belong.

## Start Here

1. Install the release from the link above.
2. Open **Install Books** in the app.
3. Import your own standard Project Aon ZIP files or extracted book folders.
4. Start Book 1, continue a completed campaign, or choose a supported fresh
   Magnakai, Grand Master, or New Order setup.

Book files are not included in this repository, installer, or release assets.
The importer expects a valid folder containing at least `title.htm` and
`sect1.htm` for one of these Project Aon folder names:

```text
01fftd  02fotw  03tcok  04tcod  05sots  06tkot
07cd    08tjoh  09tcof  10tdot  11tpot  12tmod  13tplor 14tcok
15tdc   16tlov  17tdoi  18dotd  19wb    20tcon
21votm  22tbos  23mh    24rw    25totw  26tfobm 27v 28thos 29tsoc
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
- [Kai and Magnakai campaign testing report](docs/DEEP_CAMPAIGN_TEST_REPORT.md)
- [Grand Master readiness audit](docs/GRAND_MASTER_READINESS_AUDIT.md)
- [Grand Master campaign testing report](docs/GRAND_MASTER_CAMPAIGN_TEST_REPORT.md)
- [New Order readiness audit](docs/NEW_ORDER_READINESS_AUDIT.md)
- [New Order campaign testing report](docs/NEW_ORDER_CAMPAIGN_TEST_REPORT.md)

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
