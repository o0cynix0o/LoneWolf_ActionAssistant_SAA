#!/usr/bin/env python3
"""Generate prose-free Random Number Table route skeletons from local Aon HTML."""

from __future__ import annotations

import argparse
import json
import re
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


class SectionParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.section = 0
        self._heading = False
        self._paragraph: list[str] | None = None
        self._choice = False
        self.paragraphs: list[tuple[bool, str, list[int]]] = []
        self._routes: list[int] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attributes = dict(attrs)
        if tag == "h3":
            self._heading = True
        elif tag == "p":
            self._paragraph = []
            self._routes = []
            self._choice = "choice" in str(attributes.get("class") or "").split()
        elif tag == "a" and self._paragraph is not None:
            match = re.fullmatch(r"sect(\d+)\.htm", str(attributes.get("href") or ""), re.I)
            if match:
                self._routes.append(int(match.group(1)))

    def handle_endtag(self, tag: str) -> None:
        if tag == "h3":
            self._heading = False
        elif tag == "p" and self._paragraph is not None:
            text = " ".join(part for part in self._paragraph if part).strip()
            self.paragraphs.append((self._choice, text, self._routes))
            self._paragraph = None

    def handle_data(self, data: str) -> None:
        text = " ".join(unescape(data).split())
        if not text:
            return
        if self._heading and text.isdigit():
            self.section = int(text)
        if self._paragraph is not None:
            self._paragraph.append(text)


def parse_outcome(text: str, route: int) -> dict[str, Any] | None:
    lowered = text.lower().replace("–", "-")
    label = ""
    if "odd" in lowered:
        return {"test": "odd", "route": route, "label": "Odd"}
    if "even" in lowered:
        return {"test": "even", "route": route, "label": "Even"}
    match = re.search(r"(?:is|score is|total score is)(?: now)?\s+(\d+)\s+or\s+(\d+)", lowered)
    if match:
        lower, upper = map(int, match.groups())
        return {"min": lower, "max": upper, "route": route, "label": f"{lower}-{upper}"}
    match = re.search(r"(?:is|score is|total score is)(?: now)?\s+(\d+)\s*(?:-|to)\s*(\d+)", lowered)
    if match:
        lower, upper = map(int, match.groups())
        label = f"{lower}-{upper}"
    else:
        match = re.search(r"(?:is|score is|total score is)(?: now)?\s+(\d+)\s+or\s+(lower|less|higher|more)", lowered)
        if not match:
            match = re.search(r"(?:is|score is|total score is)(?: now)?\s+(\d+)", lowered)
            if not match:
                return None
            lower = upper = int(match.group(1))
            label = str(lower)
            return {"min": lower, "max": upper, "route": route, "label": label}
        value, direction = int(match.group(1)), match.group(2)
        lower, upper = (0, value) if direction in {"lower", "less"} else (value, 99)
        label = f"0-{value}" if lower == 0 else f"{value} or more"
    return {"min": lower, "max": upper, "route": route, "label": label}


def section_roll(page: Path) -> tuple[int, dict[str, Any]] | None:
    parser = SectionParser()
    parser.feed(page.read_text(encoding="utf-8", errors="ignore"))
    if not parser.section:
        return None
    roll_index = next(
        (index for index, (_, text, _) in enumerate(parser.paragraphs) if "random number table" in text.lower()),
        None,
    )
    if roll_index is None:
        return None
    outcomes: list[dict[str, Any]] = []
    for is_choice, text, routes in parser.paragraphs[roll_index + 1 :]:
        if not is_choice:
            continue
        for route in routes:
            outcome = parse_outcome(text, route)
            if outcome is not None:
                outcomes.append(outcome)
        if outcomes:
            continue
    if not outcomes:
        outcomes = [{"min": 0, "max": 9, "label": "Apply printed RNT result"}]
    return parser.section, {"roll": {"summary": "Source Random Number Table check.", "outcomes": outcomes}}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--book", type=int, required=True)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    entries: dict[str, Any] = {}
    for page in sorted(args.source.glob("sect*.htm"), key=lambda value: int(re.search(r"\d+", value.stem).group())):
        result = section_roll(page)
        if result is not None:
            section, entry = result
            entries[str(section)] = entry
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps({str(args.book): entries}, indent=2) + "\n", encoding="utf-8")
    print(f"Book {args.book}: wrote {len(entries)} RNT skeletons")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
