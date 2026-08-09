#!/usr/bin/env python3
"""Extract conservative, prose-free direct ENDURANCE effects from source HTML.

This generator deliberately handles only exact, unconditional numeric losses
and recoveries outside Random Number Table and combat sections. Conditional,
optional, combat, and player-choice rules remain for the source review pass.
"""

from __future__ import annotations

import argparse
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "fifteen": 15,
    "twenty": 20,
}
NUMBER_PATTERN = "|".join(NUMBER_WORDS)
ENDURANCE_PATTERN = re.compile(
    rf"\b(?P<verb>lose|suffer|restore|regain|recover)\s+"
    rf"(?P<value>\d+|{NUMBER_PATTERN})\s+ENDURANCE(?:\s+points?)?\b",
    re.IGNORECASE,
)
MEAL_PATTERN = re.compile(
    rf"\bmust(?:\s+now)?\s+eat\s+(?:(?P<count>a|an|\d+|{NUMBER_PATTERN})\s+)?"
    rf"Meals?\s+or\s+lose\s+(?P<loss>\d+|{NUMBER_PATTERN})\s+"
    rf"ENDURANCE(?:\s+points?)?\b",
    re.IGNORECASE,
)
GOLD_PATTERN = re.compile(
    rf"\b(?:erase|deduct)\s+(?P<value>\d+|{NUMBER_PATTERN})\s+Gold Crowns?\b",
    re.IGNORECASE,
)
ALL_GOLD_PATTERN = re.compile(
    r"\berase\s+all\s+(?:of\s+)?(?:your\s+)?Gold Crowns?\b",
    re.IGNORECASE,
)
UNSAFE_CONTEXT_PATTERN = re.compile(
    r"\b(if|unless|may|can|choose|option|random number table|combat|fight|attack|"
    r"for each|per round)\b",
    re.IGNORECASE,
)


class ParagraphParser(HTMLParser):
    """Collect plain paragraph text and its class without retaining book prose."""

    def __init__(self) -> None:
        super().__init__()
        self._in_paragraph = False
        self._classes = ""
        self._parts: list[str] = []
        self.paragraphs: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "p":
            self._in_paragraph = True
            self._classes = dict(attrs).get("class") or ""
            self._parts = []

    def handle_data(self, data: str) -> None:
        if self._in_paragraph:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag != "p" or not self._in_paragraph:
            return
        text = " ".join(" ".join(self._parts).split())
        self.paragraphs.append((self._classes, text))
        self._in_paragraph = False


def numeric_value(value: str) -> int:
    value = value.strip().lower()
    if value in {"a", "an"}:
        return 1
    return int(value) if value.isdigit() else NUMBER_WORDS[value]


def existing_rule_sections(data_root: Path, book_number: int) -> set[int]:
    """Exclude sections already represented by RNT or combat automation."""
    sections: set[int] = set()
    for path in data_root.glob("*-rnt-rules.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for section, entry in payload.get(str(book_number), {}).items():
            if isinstance(entry, dict) and ("roll" in entry or "rollSelection" in entry):
                sections.add(int(section))
    for path in data_root.glob(f"book{book_number}*-combat-section-flows.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        for section, entry in payload.get(str(book_number), {}).items():
            if isinstance(entry, dict) and entry.get("combat"):
                sections.add(int(section))
    return sections


def extract_book(book_number: int, source: Path, data_root: Path) -> dict[str, Any]:
    entries: dict[str, Any] = {}
    excluded_sections = existing_rule_sections(data_root, book_number)
    for page in source.glob("sect*.htm"):
        section_match = re.fullmatch(r"sect(\d+)", page.stem, re.IGNORECASE)
        if section_match is None:
            continue
        section = int(section_match.group(1))
        if section in excluded_sections:
            continue
        parser = ParagraphParser()
        parser.feed(page.read_text(encoding="utf-8", errors="ignore"))
        actions: list[dict[str, Any]] = []
        for classes, text in parser.paragraphs:
            if "choice" in classes.lower() or "combat" in classes.lower():
                continue
            meal_match = MEAL_PATTERN.search(text)
            if meal_match:
                count = numeric_value(meal_match.group("count") or "one")
                actions.append({
                    "type": "meal",
                    "count": count,
                    "mode": "all_or_loss",
                    "enduranceLoss": numeric_value(meal_match.group("loss")),
                    "huntingExempt": "grand huntmastery" in text.lower(),
                })
            if UNSAFE_CONTEXT_PATTERN.search(text):
                continue
            if ALL_GOLD_PATTERN.search(text):
                actions.append({"type": "stat", "stat": "gold", "mode": "set", "value": 0})
            else:
                for match in GOLD_PATTERN.finditer(text):
                    actions.append({
                        "type": "stat",
                        "stat": "gold",
                        "delta": -numeric_value(match.group("value")),
                    })
            for match in ENDURANCE_PATTERN.finditer(text):
                delta = numeric_value(match.group("value"))
                if match.group("verb").lower() in {"lose", "suffer"}:
                    delta *= -1
                actions.append({"type": "stat", "stat": "end", "delta": delta})
        if actions:
            end_actions = [
                action
                for action in actions
                if action["type"] == "stat" and action.get("stat") == "end"
            ]
            if not end_actions:
                summary = "Source-mandated meal."
            elif all(action["delta"] > 0 for action in end_actions):
                summary = "Source-mandated ENDURANCE recovery."
            else:
                summary = "Source-mandated ENDURANCE loss."
            entries[str(section)] = {
                "summary": summary,
                "actions": actions,
            }
    return {str(book_number): entries}


def parse_book_spec(value: str) -> tuple[int, str]:
    number, separator, folder = value.partition(":")
    if not separator or not number.isdigit() or not folder:
        raise argparse.ArgumentTypeError("Book specification must be NUMBER:FOLDER.")
    return int(number), folder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--data-root", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--book", action="append", required=True, type=parse_book_spec)
    args = parser.parse_args()

    payload: dict[str, Any] = {}
    for book_number, folder_name in args.book:
        source = args.source_root / folder_name
        if not source.is_dir():
            raise FileNotFoundError(f"Book {book_number} source folder is missing: {source}")
        book_payload = extract_book(book_number, source, args.data_root)
        payload.update(book_payload)
        print(f"Book {book_number}: {len(book_payload[str(book_number)])} direct-effect entries")
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
