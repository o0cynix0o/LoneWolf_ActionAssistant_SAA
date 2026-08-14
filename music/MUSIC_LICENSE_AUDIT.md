# Music License Audit

Audit date: 2026-08-14

This folder contains candidate background music only. No MP3 in this folder is
included by the application or installer yet. A file may be packaged only when
its status is `approved-for-packaging`.

## Decision

The candidate music can support a background soundtrack, subject to the separate
conditions below. This record is a release-compliance audit, not legal advice.

- **Kevin MacLeod / Incompetech:** a Creative Commons attribution track needs
  exact track, creator, license version, license URL, and any change notice in
  the shipped credits.
- **Pixabay / DeusLower:** Pixabay permits use and adaptation but prohibits
  standalone distribution. The app must treat tracks as integrated background
  music: no download, export, copy, or raw-file-location feature.

## Evidence Findings

1. `Creative Commons Incomputech.txt` contains the literal placeholder
   `NAMEOFTRACKHERE`. It does not connect any named MP3 to a license.
2. The same note says CC BY 4.0, while several historical Kevin MacLeod releases
   for these titles are described as CC BY 3.0. The generic note cannot replace
   the original track license; all nine Kevin MacLeod candidates remain pending.
3. Five DeusLower names have matching Pixabay pages and are license-eligible
   after confirmation that the local download came from that page. Two still
   need their original track pages captured.

## Release Rules

- Ship only entries explicitly marked `approved-for-packaging`.
- Generate the in-app Music Credits and `THIRD_PARTY_MUSIC.md` from this audit.
- Preserve source URL, artist, license URL, verification date, size, and SHA-256
  hash for every shipped file.
- Record a format conversion or edit in the ledger and credits when required by
  the source license.

## License Sources

- Creative Commons Attribution 4.0: https://creativecommons.org/licenses/by/4.0/
- Incompetech licensing: https://incompetech.com/music/royalty-free/licenses/
- Pixabay Content License: https://pixabay.com/service/license-summary/

## Pixabay / DeusLower Candidates

| File | Source and status | SHA-256 |
|---|---|---|
| `deuslower-atmosphere-mystic-fantasy-orchestral-music-335263.mp3` | [Atmosphere mystic fantasy orchestral music](https://pixabay.com/music/mystery-atmosphere-mystic-fantasy-orchestral-music-335263/), DeusLower, source-verified-license-eligible | `cd27a5003cd560cfd50ce9aace3146ac310e259df04d6957648b6833c8867091` |
| `deuslower-fantasy-medieval-epic-music-239599.mp3` | [Fantasy Medieval Epic Music](https://pixabay.com/music/main-title-fantasy-medieval-epic-music-239599/), DeusLower, source-verified-license-eligible | `abcc804f811ac9734283c818fee60432226e476300056b210b4f5811f46bf258` |
| `deuslower-medieval-ambient-236809.mp3` | [Medieval Ambient](https://pixabay.com/music/ambient-medieval-ambient-236809/), DeusLower, source-verified-license-eligible | `30d585bacc7e9d6a9c6b067381ee67b2861acd7e62f57e3a4f01be66e2f6d4d2` |
| `deuslower-medieval-citytavern-ambient-235876.mp3` | [Medieval city/tavern ambient](https://pixabay.com/music/folk-medieval-citytavern-ambient-235876/), DeusLower, source-verified-license-eligible | `c90b21b6a0d6f2c9c8b59fb808360c9e36b07d9e553e6cb4734ee247330d78fb` |
| `deuslower-mountain-knight-castle-medieval-fantasy-orchestral-music-264986.mp3` | [Mountain Knight Castle](https://pixabay.com/music/modern-classical-mountain-knight-castle-medieval-fantasy-orchestral-music-264986/), DeusLower, source-verified-license-eligible | `af6dab45e9e61ba1bbdd67c908e20a9278b558b801c35a3c32e574d3c012a485` |
| `deuslower-mystic-medieval-ambient-music-337783.mp3` | DeusLower claimed by filename, **pending original Pixabay URL** | `b16b1fb7f1638b3c6a5402bd7432a9328c223f5420ae2696e005039ff655ec14` |
| `deuslower-orchestral-medieval-ambient-428004.mp3` | DeusLower claimed by filename, **pending original Pixabay URL** | `cb0e6600ee1aa397e41c7e90c0a86016e708005eee1a4c0c514cbefb97d7b993` |

All seven are subject to the Pixabay Content License. Before packaging, record
the original download/source evidence for the local hash and set the final
status to `approved-for-packaging`.

## Incompetech / Kevin MacLeod Candidates

| File | Status | SHA-256 |
|---|---|---|
| `Firesong.mp3` | Kevin MacLeod claimed; **pending original source and exact CC license version** | `00cb022c3b89c50e7853c628751fa71b6920983c2fd1225063d745c3a7352927` |
| `Lord of the Land.mp3` | Kevin MacLeod claimed; **pending original source and exact CC license version** | `47ce185fdc1f2e5514566307d652d6cb62a06bed47ea730e28214d3cedc2f948` |
| `Magic Forest.mp3` | Kevin MacLeod claimed; historical references say CC BY 3.0; **pending source confirmation** | `0e8f92a3dfb5e71398502478d6d3be14b705b0dfc0afabccf5831bc741592f55` |
| `Mystic Force.mp3` | Kevin MacLeod claimed; historical references say CC BY 3.0; **pending source confirmation** | `6aadb4a305d906e69514047219d3d69afae5f218e50ddf66164674c69893bb9b` |
| `Rites.mp3` | Kevin MacLeod claimed; **pending original source and exact CC license version** | `269fbc51c8866b674e557ca570671b8ca5658c62965ba9b69853dd210c372646` |
| `Ritual.mp3` | Kevin MacLeod claimed; historical references say CC BY 3.0; **pending source confirmation** | `2dfdfede2f491f3991f8264577f250dc6abf63dd7c7dd3cd751d41b57b995283` |
| `River Flute.mp3` | Kevin MacLeod claimed; **pending original source and exact CC license version** | `a634cacde2883fb83b161e15b3489c3d7b43180e49aa3428345d28b0b5a20feb` |
| `Shamanistic.mp3` | Kevin MacLeod claimed; historical references say CC BY 3.0; **pending source confirmation** | `69265f2089672b2b798e0e3bb8f5d79d1b5af7a479aff4cdfb19658311be7910` |
| `Shores of Avalon.mp3` | Kevin MacLeod claimed; historical references say CC BY 3.0; **pending source confirmation** | `7b64a71c4a03992baff41becd57dd6790566a79373a6fba7534201fdd42c74c4` |

## Inventory Summary

| Group | Files | Bytes | Current outcome |
|---|---:|---:|---|
| Kevin MacLeod / Incompetech candidates | 9 | 106,676,624 | Pending original track evidence |
| DeusLower / Pixabay candidates | 7 | 43,735,186 | Five source-verified; two need URLs |
| Total | 16 | 150,411,810 | Nothing approved for packaging |
