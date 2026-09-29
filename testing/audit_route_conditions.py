#!/usr/bin/env python3
"""Audit Project Aon choice routes for Action Chart-aware highlighting.

The committed JSON report contains only book/section/route numbers and condition
types.  Use ``--show-unresolved`` for a local, transient display of source
phrasing that still needs manual classification; licensed prose is never copied
into the report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import tempfile
from collections import Counter
from html import unescape
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from lonewolf_redux import (  # noqa: E402
    GRAND_MASTER_DISCIPLINES,
    KAI_DISCIPLINES,
    MAGNAKAI_DISCIPLINES,
    NEW_ORDER_DISCIPLINES,
    LoneWolfReduxAssistant,
)


CHOICE_PATTERN = re.compile(
    r"<p\b[^>]*class=[\"'][^\"']*\bchoice\b[^\"']*[\"'][^>]*>(.*?)</p>",
    re.IGNORECASE | re.DOTALL,
)
ROUTE_PATTERN = re.compile(r"href=[\"']sect(\d+)\.htm", re.IGNORECASE)
TAG_PATTERN = re.compile(r"<[^>]+>")

DISCIPLINE_NAMES = tuple(
    sorted(
        set(KAI_DISCIPLINES + MAGNAKAI_DISCIPLINES + GRAND_MASTER_DISCIPLINES + NEW_ORDER_DISCIPLINES),
        key=len,
        reverse=True,
    )
)


def clean_choice(block: str) -> str:
    return re.sub(r"\s+", " ", unescape(TAG_PATTERN.sub("", block))).strip()


def condition_types(condition: Any) -> list[str]:
    if not isinstance(condition, dict):
        return []
    result = [str(condition.get("type") or "unknown")]
    for child in condition.get("conditions") or []:
        result.extend(condition_types(child))
    return result


def gate_categories(label: str) -> list[str]:
    """Classify only state-backed route gates relevant to choice hints."""
    lowered = label.lower()
    categories: list[str] = []
    if re.search(
        r"\b(?:\d+|one|two|three|four|five|six|seven|eight|nine|ten|no|all|enough|sufficient|any)\s+gold crowns?\b|"
        r"\b(?:no|enough|sufficient) money\b|\bcan(?:not|'t)? afford\b",
        lowered,
    ):
        categories.append("gold")
    if any(name.lower() in lowered for name in DISCIPLINE_NAMES) or re.search(
        r"\b(?:disciplines?|this skill|these skills|either skill|kai weapon)\b", lowered
    ):
        categories.append("discipline")
    if re.search(r"\b(?:rank of|rank|lore-circle|lore circle)\b", lowered):
        categories.append("rank_or_lore")
    if re.search(r"\b(?:endurance|combat skill)\b", lowered):
        categories.append("stat")
    if re.search(r"\b(?:ever|previously|already) (?:visited|encountered|met|been|purchased)\b", lowered):
        categories.append("history")

    random_branch = bool(re.search(r"\b(?:picked|chosen|random number|number (?:is|was))\b", lowered))
    status_history = bool(re.search(
        r"\bhave (?:been|reached|attained|achieved|completed|survived|lost|won|killed|applied|coated|visited|met|seen|arrived|travelled)\b",
        lowered,
    ))
    item_language = bool(re.search(
        r"\b(?:possess(?:es|ed)?|carrying|do not have|don't have|without|"
        r"neither of (?:these|the)|none of (?:these|the)|backpack items?|special items?)\b",
        lowered,
    ))
    simple_have_item = bool(re.match(
        r"^if (?:you )?(?:still )?have (?:a|an|the|some|any|another|at least|a minimum of)\b",
        lowered,
    ))
    if not random_branch and not status_history and (item_language or simple_have_item):
        categories.append("inventory")
    return sorted(set(categories))


def source_choices(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8", errors="ignore")
    choices: list[dict[str, Any]] = []
    for match in CHOICE_PATTERN.finditer(source):
        block = match.group(1)
        routes = [int(value) for value in ROUTE_PATTERN.findall(block)]
        if routes:
            choices.append({"label": clean_choice(block), "routes": routes})
    return choices


def audit_book(
    assistant: LoneWolfReduxAssistant,
    book_number: int,
    folder: Path,
    show_unresolved: bool,
) -> dict[str, Any]:
    recognized: list[dict[str, Any]] = []
    unresolved: list[dict[str, Any]] = []
    condition_counts: Counter[str] = Counter()

    for path in sorted(folder.glob("sect*.htm"), key=lambda item: int(re.search(r"\d+", item.stem).group())):
        section = int(re.search(r"\d+", path.stem).group())
        evaluated = {
            int(route["Section"]): route
            for route in assistant.section_source_route_payload(book_number, section)
            if isinstance(route, dict) and route.get("Section") is not None
        }
        for choice in source_choices(path):
            label = choice["label"]
            categories = gate_categories(label)
            for target in choice["routes"]:
                route = evaluated.get(target, {})
                condition = route.get("Condition")
                if isinstance(condition, dict):
                    types = condition_types(condition)
                    condition_counts.update(types)
                    recognized.append({
                        "section": section,
                        "target": target,
                        "conditionTypes": types,
                    })
                elif categories:
                    digest = hashlib.sha256(label.lower().encode("utf-8")).hexdigest()[:12]
                    unresolved.append({
                        "section": section,
                        "target": target,
                        "categories": categories,
                        "phraseHash": digest,
                    })
                    if show_unresolved:
                        print(f"Book {book_number}, section {section} -> {target}: {label}")

    return {
        "recognizedCount": len(recognized),
        "unresolvedCount": len(unresolved),
        "conditionCounts": dict(sorted(condition_counts.items())),
        "recognized": recognized,
        "unresolved": unresolved,
    }


def parse_book(value: str) -> tuple[int, str]:
    number, separator, folder = value.partition(":")
    if not separator or not number.isdigit() or not folder:
        raise argparse.ArgumentTypeError("Book specification must be NUMBER:FOLDER.")
    return int(number), folder


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", required=True, type=Path)
    parser.add_argument("--data-dir", default=ROOT / "data", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--book", action="append", required=True, type=parse_book)
    parser.add_argument("--show-unresolved", action="store_true")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory(prefix="lonewolf-route-audit-") as temporary:
        scratch = Path(temporary)
        assistant = LoneWolfReduxAssistant(
            save_dir=scratch / "saves",
            data_dir=args.data_dir,
            state_data_dir=scratch / "state",
            books_dir=args.source_root,
        )
        books: dict[str, Any] = {}
        for book_number, folder_name in args.book:
            folder = args.source_root / folder_name
            if not folder.is_dir():
                raise FileNotFoundError(folder)
            books[str(book_number)] = audit_book(
                assistant, book_number, folder, args.show_unresolved
            )

    payload = {
        "schemaVersion": 1,
        "purpose": "Action Chart-aware source-route audit; no licensed prose stored.",
        "books": books,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    for number, result in books.items():
        print(
            f"Book {number}: recognized={result['recognizedCount']}, "
            f"unresolved={result['unresolvedCount']}"
        )
    return 1 if any(book["unresolvedCount"] for book in books.values()) else 0


if __name__ == "__main__":
    raise SystemExit(main())
