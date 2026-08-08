#!/usr/bin/env python3
"""Generate prose-free combat presets from local Project Aon section HTML."""

from __future__ import annotations

import argparse
import json
import re
from html import unescape
from pathlib import Path
from typing import Any


COMBAT_PATTERN = re.compile(r'<p class="combat">(.*?)</p>', re.IGNORECASE | re.DOTALL)
STAT_PATTERN = re.compile(r"COMBAT\s*SKILL\s*(\d+)\s*ENDURANCE\s*(\d+)", re.IGNORECASE)
ROUTE_PATTERN = re.compile(r"(?:if you win|if you defeat).*?<a href=\"sect(\d+)\.htm\"", re.IGNORECASE | re.DOTALL)


def plain_text(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", unescape(value)).replace("\xa0", " ").split())


def section_preset(page: Path, book_number: int) -> tuple[int, dict[str, Any]] | None:
    section_match = re.search(r"sect(\d+)$", page.stem, re.IGNORECASE)
    if not section_match:
        return None
    raw = page.read_text(encoding="utf-8", errors="ignore")
    match = COMBAT_PATTERN.search(raw)
    if match is None:
        return None
    combat_text = plain_text(match.group(1))
    stats = STAT_PATTERN.search(combat_text)
    if stats is None:
        return None
    name = combat_text[: stats.start()].rstrip(": ")
    section = int(section_match.group(1))
    preset: dict[str, Any] = {
        "id": f"book{book_number}-{section}",
        "enemies": [{"name": name, "cs": int(stats.group(1)), "endurance": int(stats.group(2))}],
    }
    after = raw[match.end() :]
    route = ROUTE_PATTERN.search(after)
    if route:
        preset["victoryRoute"] = int(route.group(1))
    return section, {"combat": [preset]}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=int, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    entries: dict[str, Any] = {}
    for page in sorted(args.source.glob("sect*.htm"), key=lambda value: int(re.search(r"\d+", value.stem).group())):
        result = section_preset(page, args.book)
        if result is not None:
            section, preset = result
            entries[str(section)] = preset
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({str(args.book): entries}, indent=2) + "\n", encoding="utf-8")
    print(f"Book {args.book}: wrote {len(entries)} combat presets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
