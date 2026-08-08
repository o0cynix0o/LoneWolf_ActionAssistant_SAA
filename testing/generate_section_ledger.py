#!/usr/bin/env python3
"""Create compact, prose-free Project Aon section ledgers for a book series.

The application never bundles the licensed Project Aon books. This tool reads a
local player/source installation and writes only section numbers, player-choice
targets, incoming counts, and broad audit tags used to plan automation work.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class SectionPageParser(HTMLParser):
    """Extract a numbered section, choice links, and plain text for tagging."""

    def __init__(self) -> None:
        super().__init__()
        self._in_heading = False
        self._choice_depth = 0
        self.heading_parts: list[str] = []
        self.choice_targets: list[int] = []
        self.text_parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "h3":
            self._in_heading = True
        elif tag == "p" and "choice" in str(attributes.get("class") or "").split():
            self._choice_depth += 1
        elif tag == "a" and self._choice_depth:
            match = re.fullmatch(r"sect(\d+)\.htm", str(attributes.get("href") or ""), re.I)
            if match:
                self.choice_targets.append(int(match.group(1)))

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3":
            self._in_heading = False
        elif tag == "p" and self._choice_depth:
            self._choice_depth -= 1

    def handle_data(self, data: str) -> None:
        text = data.strip()
        if not text:
            return
        if self._in_heading:
            self.heading_parts.append(text)
        self.text_parts.append(text)

    @property
    def section(self) -> int | None:
        try:
            return int("".join(self.heading_parts))
        except ValueError:
            return None

    @property
    def text(self) -> str:
        return " ".join(self.text_parts)


def audit_tags(text: str, route_count: int) -> list[str]:
    """Classify possible work without storing any licensed text."""
    lowered = text.lower()
    tags: list[str] = []
    if route_count == 0:
        tags.append("terminal")
    elif route_count == 1:
        tags.append("single_route")
    if "random number table" in lowered:
        tags.append("random_number")
    if "combat skill" in lowered or "combat results table" in lowered:
        tags.append("combat_or_stat")
    if "endurance" in lowered:
        tags.append("endurance")
    if "meal" in lowered:
        tags.append("meal")
    if "if you have" in lowered or "if you possess" in lowered or "if you are carrying" in lowered:
        tags.append("conditional")
    if "special item" in lowered or "backpack item" in lowered or "gold crown" in lowered:
        tags.append("inventory_or_gold")
    return tags or ["source_link"]


def build_book_ledger(book_number: int, folder: Path) -> tuple[dict[str, Any], Counter[str]]:
    parsed: dict[int, SectionPageParser] = {}
    incoming: Counter[int] = Counter()
    for page in folder.glob("sect*.htm"):
        parser = SectionPageParser()
        parser.feed(page.read_text(encoding="utf-8", errors="ignore"))
        section = parser.section
        if section is None:
            continue
        parsed[section] = parser
        incoming.update(parser.choice_targets)

    entries: dict[str, Any] = {}
    tags: Counter[str] = Counter()
    for section in sorted(parsed):
        parser = parsed[section]
        routes = [{"Section": target} for target in parser.choice_targets]
        classification = audit_tags(parser.text, len(routes))
        tags.update(classification)
        entries[str(section)] = {
            "auditStatus": "source-link-baseline",
            "classification": classification,
            "sourceRouteCount": len(routes),
            "sourceRoutes": routes,
            "incomingRouteCount": int(incoming[section]),
        }
    expected_sections = set(range(1, max(parsed, default=0) + 1))
    if set(parsed) != expected_sections:
        raise ValueError(
            f"Book {book_number} has a non-contiguous section range in {folder}: "
            f"found {len(entries)} sections through {max(parsed, default=0)}."
        )
    return {str(book_number): entries}, tags


def parse_book_spec(value: str) -> tuple[int, str]:
    number, separator, folder = value.partition(":")
    if not separator or not number.isdigit() or not folder:
        raise argparse.ArgumentTypeError("Book specification must be NUMBER:FOLDER.")
    return int(number), folder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--book", action="append", required=True, type=parse_book_spec)
    args = parser.parse_args()

    args.output_dir.mkdir(parents=True, exist_ok=True)
    for book_number, folder_name in args.book:
        source = args.source_root / folder_name
        if not source.is_dir():
            raise FileNotFoundError(f"Book {book_number} source folder is missing: {source}")
        ledger, tags = build_book_ledger(book_number, source)
        destination = args.output_dir / f"book{book_number}-section-flows.json"
        destination.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
        print(f"Book {book_number}: {len(ledger[str(book_number)])} sections -> {destination.name}")
        print("  " + ", ".join(f"{name}={count}" for name, count in sorted(tags.items())))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
