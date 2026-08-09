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
EVASION_PATTERN = re.compile(
    r"may (?:attempt to )?(?:evade|escape)(?: (?:this|the)? ?combat(?: with [^.]*?)?)?"
    r"(?: at any time)? after (?:the )?(?P<rounds>\w+) rounds? by turning to\s*(?P<route>\d+)",
    re.IGNORECASE,
)
TIMED_MODIFIER_PATTERN = re.compile(
    r"(?P<direction>reduce|increase) your COMBAT SKILL(?: score)? by (?P<value>\d+)"
    r"(?: points?)? for the first(?: (?P<rounds>\w+))? rounds?",
    re.IGNORECASE,
)
CONDITIONAL_TIMED_MODIFIER_PATTERN = re.compile(
    r"unless you possess (?:the Discipline of )?(?P<power>Grand [A-Za-z-]+)"
    r"(?: and have reached the rank of (?P<rank>Sun Knight) or higher)?[, ]+(?:you )?(?:must )?"
    r"reduce your COMBAT SKILL(?: score)? by (?P<value>\d+)(?: points?)?"
    r" for the first(?: (?P<rounds>\w+))? rounds?",
    re.IGNORECASE,
)
CONDITIONAL_DURATION_MODIFIER_PATTERN = re.compile(
    r"unless you possess (?:the Discipline of )?(?P<power>Grand [A-Za-z-]+)"
    r"(?: and have reached the rank of (?P<rank>Sun Knight) or higher)?[, ]+(?:you )?(?:must )?"
    r"reduce your COMBAT SKILL(?: score)? by (?P<value>\d+)(?: points?)?"
    r" for the duration of (?:this )?(?:combat|fight)",
    re.IGNORECASE,
)
CONDITIONAL_POSITIVE_MODIFIER_PATTERN = re.compile(
    r"if you possess (?P<thing>.+?)[, ]+you may add (?:a further )?(?P<value>\w+)"
    r"(?: \([^)]*\))? to your COMBAT SKILL(?: score)?"
    r"(?: for the duration of (?:this )?(?:[a-z-]+ )?(?:combat|fight))?",
    re.IGNORECASE,
)
DURATION_MODIFIER_PATTERN = re.compile(
    r"(?P<direction>reduce|increase) your COMBAT SKILL(?: score)? by (?P<value>\w+)(?: points?)?"
    r" for the duration of (?:this )?(?:[a-z-]+ )?(?:combat|fight)",
    re.IGNORECASE,
)
IGNORE_LOSS_PATTERN = re.compile(
    r"ignore any ENDURANCE(?: points?)? losses? you may sustain(?: during)?"
    r" the first(?: (?P<rounds>\w+))? rounds?",
    re.IGNORECASE,
)
WIN_WITHIN_PATTERN = re.compile(
    r"if you win(?: this| the)? (?:combat|fight) in (?P<rounds>\w+) rounds? or less, turn to\s*(?P<route>\d+)",
    re.IGNORECASE,
)
WIN_DURATION_PATTERN = re.compile(
    r"if you win and the (?:combat|fight) (?:takes|lasts) (?P<rounds>\w+) rounds? or less, turn to\s*(?P<route>\d+)",
    re.IGNORECASE,
)
WIN_TOO_LATE_PATTERN = re.compile(
    r"if you win(?: this| the)? (?:combat|fight) in (?P<rounds>\w+) rounds? or more, turn to\s*(?P<route>\d+)",
    re.IGNORECASE,
)
ONE_ROUND_COMPARISON_PATTERN = re.compile(
    r"fight this combat for one round.*?if (?P<first>.*?) turn to\s*(?P<first_route>\d+)"
    r".*?if (?P<second>.*?) turn to\s*(?P<second_route>\d+)",
    re.IGNORECASE,
)
TOO_LATE_PATTERN = re.compile(
    r"(?:start of the )?(?P<round>\w+) round.*?turn (?:immediately )?(?:to|instead to)\s*(?P<route>\d+)",
    re.IGNORECASE,
)
ROUND_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "seventh": 7, "eight": 8, "eighth": 8,
    "nine": 9, "ninth": 9, "ten": 10, "tenth": 10,
}
GRAND_MASTER_RANKS = {"sun knight": 6}


def plain_text(value: str) -> str:
    return " ".join(re.sub(r"<[^>]+>", " ", unescape(value)).replace("\xa0", " ").split())


def parse_round(value: str) -> int | None:
    value = value.strip().lower()
    if value.isdigit():
        return int(value)
    return ROUND_WORDS.get(value)


def add_standard_combat_rules(preset: dict[str, Any], combat_text: str) -> None:
    """Capture unambiguous combat clauses without copying source prose."""
    duration_match = DURATION_MODIFIER_PATTERN.search(combat_text)
    if duration_match:
        prefix = combat_text[max(0, duration_match.start() - 180) : duration_match.start()].lower()
        if "unless" not in prefix and "if you possess" not in prefix:
            value = parse_round(duration_match.group("value"))
            if value:
                preset["modifier"] = value if duration_match.group("direction").lower() == "increase" else -value

    conditional_duration_match = CONDITIONAL_DURATION_MODIFIER_PATTERN.search(combat_text)
    if conditional_duration_match:
        condition: dict[str, Any] = {
            "type": "no_power", "name": conditional_duration_match.group("power")
        }
        rank = GRAND_MASTER_RANKS.get((conditional_duration_match.group("rank") or "").lower())
        if rank:
            condition = {
                "type": "any",
                "conditions": [
                    condition,
                    {"type": "grand_master_rank_lt", "value": rank},
                ],
            }
        preset["conditionalModifiers"] = [{
            "modifier": -int(conditional_duration_match.group("value")),
            "label": "Grand Master combat requirement",
            "condition": condition,
        }]

    for positive_match in CONDITIONAL_POSITIVE_MODIFIER_PATTERN.finditer(combat_text):
        thing = re.sub(r"^(?:a|an|the)\s+", "", positive_match.group("thing").strip(), flags=re.IGNORECASE)
        value = parse_round(positive_match.group("value"))
        if not value or not thing:
            continue
        condition_type = "power" if thing.lower().endswith("mastery") else "item"
        condition: dict[str, Any] = {"type": condition_type, "name": thing}
        modifiers = preset.setdefault("conditionalModifiers", [])
        modifiers.append({
            "modifier": value,
            "label": thing,
            "condition": condition,
        })

    conditional_match = CONDITIONAL_TIMED_MODIFIER_PATTERN.search(combat_text)
    if conditional_match:
        rounds = parse_round(conditional_match.group("rounds") or "one")
        if rounds:
            condition: dict[str, Any] = {"type": "no_power", "name": conditional_match.group("power")}
            rank = GRAND_MASTER_RANKS.get((conditional_match.group("rank") or "").lower())
            if rank:
                condition = {
                    "type": "any",
                    "conditions": [
                        condition,
                        {"type": "grand_master_rank_lt", "value": rank},
                    ],
                }
            preset["timedModifiers"] = [{
                "modifier": -int(conditional_match.group("value")),
                "startRound": 1,
                "endRound": rounds,
                "condition": condition,
            }]

    timed_match = TIMED_MODIFIER_PATTERN.search(combat_text)
    if timed_match:
        prefix = combat_text[max(0, timed_match.start() - 180) : timed_match.start()].lower()
        # Conditional clauses need a structured condition; leave them for the
        # reviewer instead of incorrectly applying a penalty to every player.
        if "unless" not in prefix and "if you possess" not in prefix and not conditional_match:
            rounds = parse_round(timed_match.group("rounds") or "one")
            if rounds:
                value = int(timed_match.group("value"))
                if timed_match.group("direction").lower() == "reduce":
                    value *= -1
                preset["timedModifiers"] = [{"modifier": value, "startRound": 1, "endRound": rounds}]

    ignore_match = IGNORE_LOSS_PATTERN.search(combat_text)
    if ignore_match:
        rounds = parse_round(ignore_match.group("rounds") or "one")
        if rounds:
            preset["ignorePlayerLossRounds"] = rounds

    evade_match = EVASION_PATTERN.search(combat_text)
    if evade_match:
        rounds = parse_round(evade_match.group("rounds"))
        if rounds:
            preset["canEvade"] = True
            preset["evadeAfterRounds"] = rounds
            preset["evadeRoute"] = int(evade_match.group("route"))

    win_match = WIN_WITHIN_PATTERN.search(combat_text) or WIN_DURATION_PATTERN.search(combat_text)
    if win_match:
        rounds = parse_round(win_match.group("rounds"))
        if rounds:
            preset["winWithinRounds"] = rounds
            preset["winWithinRoute"] = int(win_match.group("route"))
            late_match = TOO_LATE_PATTERN.search(combat_text[win_match.end():])
            if late_match:
                route = int(late_match.group("route"))
                preset["tooLateRoute"] = route
                preset["roundLimit"] = rounds
                preset["roundExceededRoute"] = route
            else:
                late_match = WIN_TOO_LATE_PATTERN.search(combat_text[win_match.end():])
                if late_match:
                    route = int(late_match.group("route"))
                    preset["tooLateRoute"] = route

    comparison_match = ONE_ROUND_COMPARISON_PATTERN.search(combat_text)
    if comparison_match:
        first = comparison_match.group("first").lower()
        second = comparison_match.group("second").lower()
        first_route = int(comparison_match.group("first_route"))
        second_route = int(comparison_match.group("second_route"))
        if "equal or greater" in first and "enemy" in first and "greater" in second:
            preset["oneRoundComparisonRoutes"] = {
                "enemyLossGreater": first_route,
                "equal": first_route,
                "playerLossGreater": second_route,
            }
        elif "lose more" in first and "enemy" in first and "enemy loses more" in second:
            preset["oneRoundComparisonRoutes"] = {
                "playerLossGreater": first_route,
                "enemyLossGreater": second_route,
                "equal": second_route,
            }


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
    # The printed combat instructions immediately follow the combat paragraph.
    # Limit the scan so table-of-contents boilerplate cannot contribute rules.
    instruction_text = plain_text(raw[match.start() : min(len(raw), match.end() + 2000)])
    add_standard_combat_rules(preset, instruction_text)
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
