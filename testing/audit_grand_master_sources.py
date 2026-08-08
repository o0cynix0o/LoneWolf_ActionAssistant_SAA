#!/usr/bin/env python3
"""Index source-rule candidates without copying book prose.

The generated JSON contains only book/section numbers and signal categories. It
is deliberately a planning and verification artefact, not a replacement for
the player-owned Project Aon HTML source used to make the audit.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from generate_section_ledger import SectionPageParser, parse_book_spec


SIGNALS = {
    "rnt": r"random number table",
    "endurance": r"endurance",
    "meal": r"\bmeals?\b",
    "gold": r"gold crowns?",
    "inventory": r"backpack item|special item|discard .*item|erase .*item|lose .*item",
    "discipline": r"grand (?:mastery|weaponmastery|huntmastery|pathsmanship|nexus)|kai-(?:surge|screen|alchemy)|animal mastery|deliverance|assimilance|telegnosis|magi-magic|astrology|herbmastery|elementalism|bardsmanship",
    "kai_weapon": r"kai weapon|spawnsmite|alema|magnara|sunstrike|kaistar|valiance|ulnarias|raumas|illuminatus|firefall",
}


def audit_book(book_number: int, folder: Path) -> dict[str, Any]:
    hits = {name: [] for name in (*SIGNALS, "combat")}
    found_sections: set[int] = set()
    for page in folder.glob("sect*.htm"):
        source_html = page.read_text(encoding="utf-8", errors="ignore")
        parser = SectionPageParser()
        parser.feed(source_html)
        section = parser.section
        if section is None:
            continue
        found_sections.add(section)
        if re.search(r'<p\s+class=["\'][^"\']*\bcombat\b', source_html, re.IGNORECASE):
            hits["combat"].append(section)
        for name, pattern in SIGNALS.items():
            if re.search(pattern, parser.text, re.IGNORECASE):
                hits[name].append(section)
    expected_sections = set(range(1, max(found_sections, default=0) + 1))
    if found_sections != expected_sections:
        raise ValueError(
            f"Book {book_number} does not contain a contiguous range from section 1 "
            f"through {max(found_sections, default=0)}."
        )
    return {
        "sectionCount": len(found_sections),
        "signals": {name: sorted(values) for name, values in hits.items()},
        "counts": {name: len(values) for name, values in hits.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--book", action="append", required=True, type=parse_book_spec)
    args = parser.parse_args()

    books: dict[str, Any] = {}
    for book_number, folder_name in args.book:
        source = args.source_root / folder_name
        if not source.is_dir():
            raise FileNotFoundError(f"Book {book_number} source folder is missing: {source}")
        books[str(book_number)] = audit_book(book_number, source)
    payload = {
        "schemaVersion": 1,
        "purpose": "Source-rule audit index; no licensed prose is stored.",
        "books": books,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for book_number, result in books.items():
        summary = ", ".join(f"{name}={count}" for name, count in result["counts"].items())
        print(f"Book {book_number}: {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
