"""Build the spoiler-aware Compendium catalog from audited app/source data.

The generated file contains names, mechanics, statistics, and source references;
it deliberately does not copy book prose. Reviewed facts live in
data/compendium-overrides.json so source extraction never invents lore.
"""

from __future__ import annotations

import argparse
import html
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
BOOKS = ROOT / "docker-data" / "books" / "lw"
OUT = DATA / "compendium.json"

BOOK_CATALOG = {
    1: ("Flight from the Dark", "01fftd"), 2: ("Fire on the Water", "02fotw"),
    3: ("The Caverns of Kalte", "03tcok"), 4: ("The Chasm of Doom", "04tcod"),
    5: ("Shadow on the Sand", "05sots"), 6: ("The Kingdoms of Terror", "06tkot"),
    7: ("Castle Death", "07cd"), 8: ("The Jungle of Horrors", "08tjoh"),
    9: ("The Cauldron of Fear", "09tcof"), 10: ("The Dungeons of Torgar", "10tdot"),
    11: ("The Prisoners of Time", "11tpot"), 12: ("The Masters of Darkness", "12tmod"),
    13: ("The Plague Lords of Ruel", "13tplor"), 14: ("The Captives of Kaag", "14tcok"),
    15: ("The Darke Crusade", "15tdc"), 16: ("The Legacy of Vashna", "16tlov"),
    17: ("The Deathlord of Ixia", "17tdoi"), 18: ("Dawn of the Dragons", "18dotd"),
    19: ("Wolf's Bane", "19wb"), 20: ("The Curse of Naar", "20tcon"),
    21: ("Voyage of the Moonstone", "21votm"), 22: ("The Buccaneers of Shadaki", "22tbos"),
    23: ("Mydnight's Hero", "23mh"), 24: ("Rune War", "24rw"),
    25: ("Trail of the Wolf", "25totw"), 26: ("The Fall of Blood Mountain", "26tfobm"),
    27: ("Vampirium", "27v"), 28: ("The Hunger of Sejanoz", "28thos"),
    29: ("The Storms of Chai", "29tsoc"),
}

ITEM_TYPES = {
    "add_item", "remove_item", "remove_matching_items", "item", "no_item",
    "item_history", "no_item_history", "item_count_gte", "item_count_lt",
}
PLACE_SUFFIXES = (
    "Abbey", "Bay", "Bridge", "Castle", "Cavern", "Caverns", "City", "Desert",
    "Forest", "Fortress", "Harbour", "Island", "Isle", "Kingdom", "Lake",
    "Monastery", "Mountains", "Palace", "Pass", "Port", "River", "Sea",
    "Swamp", "Temple", "Tower", "Valley", "Village", "Wood",
)
TITLE_PREFIXES = ("Baron", "Brother", "Captain", "Duke", "Emperor", "General", "King", "Lady", "Lord", "Marshal", "Prince", "Princess", "Queen", "Sister", "Zakhan")


def slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.casefold()).strip("-")


def clean_name(value: Any) -> str:
    value = html.unescape(str(value or ""))
    value = re.sub(r"\s+", " ", value).strip(" \t\r\n.,:;!?\"'")
    return value


def source_ref(book: int, section: int, role: str) -> dict[str, Any]:
    return {"book": book, "section": section, "role": role}


def load_flow_files() -> Iterable[tuple[int, dict[str, Any]]]:
    for path in sorted(DATA.glob("book*-section-flows.json")):
        match = re.match(r"book(\d+)-", path.name)
        if not match:
            continue
        book = int(match.group(1))
        payload = json.loads(path.read_text(encoding="utf-8"))
        root = payload.get(str(book), payload)
        yield book, root


def walk(value: Any) -> Iterable[dict[str, Any]]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk(child)


def add_ref(entry: dict[str, Any], ref: dict[str, Any]) -> None:
    refs = entry.setdefault("sourceRefs", [])
    if ref not in refs:
        refs.append(ref)


def extract_items_and_bestiary() -> tuple[dict[str, Any], dict[str, Any]]:
    items: dict[str, Any] = {}
    creatures: dict[str, Any] = {}
    for book, root in load_flow_files():
        for section_key, section_data in root.items():
            if not str(section_key).isdigit() or not isinstance(section_data, dict):
                continue
            section = int(section_key)
            for node in walk(section_data):
                kind = clean_name(node.get("type")).casefold()
                item_context = kind in ITEM_TYPES or "container" in node or "containers" in node
                if item_context:
                    names = [node.get("name"), *(node.get("names") or []), *(node.get("includeNames") or [])]
                    for raw in names:
                        name = clean_name(raw)
                        if not name or len(name) > 80:
                            continue
                        key = name.casefold()
                        entry = items.setdefault(key, {"id": slug(name), "name": name, "kind": "Inventory Item", "sourceRefs": []})
                        role = "acquired" if kind == "add_item" else ("used" if kind.startswith("remove") else "required")
                        add_ref(entry, source_ref(book, section, role))
            for combat in section_data.get("combat", []):
                enemies = list(combat.get("enemies") or [])
                if combat.get("enemy"):
                    enemies.append(combat["enemy"])
                for enemy in enemies:
                    name = clean_name(enemy.get("name"))
                    if not name:
                        continue
                    key = name.casefold()
                    entry = creatures.setdefault(key, {"id": slug(name), "name": name, "kind": "Enemy", "variants": [], "sourceRefs": []})
                    variant = {"book": book, "section": section, "combatSkill": enemy.get("cs"), "endurance": enemy.get("endurance")}
                    if variant not in entry["variants"]:
                        entry["variants"].append(variant)
                    add_ref(entry, source_ref(book, section, "encounter"))
    return items, creatures


def source_text(path: Path) -> str:
    raw = path.read_text(encoding="utf-8", errors="ignore")
    raw = re.sub(r"<head\b[^>]*>.*?</head>", " ", raw, flags=re.I | re.S)
    raw = re.sub(r"<(script|style)\b[^>]*>.*?</\1>", " ", raw, flags=re.I | re.S)
    return clean_name(re.sub(r"<[^>]+>", " ", raw))


def extract_people_and_places() -> tuple[dict[str, Any], dict[str, Any]]:
    people_hits: dict[str, set[tuple[int, int]]] = defaultdict(set)
    place_hits: dict[str, set[tuple[int, int]]] = defaultdict(set)
    title_pattern = re.compile(r"\b(" + "|".join(TITLE_PREFIXES) + r")\s+([A-Z][A-Za-z'’-]+(?:\s+(?:of\s+)?[A-Z][A-Za-z'’-]+){0,2})")
    suffix_pattern = re.compile(r"\b([A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+){0,2}\s+(?:" + "|".join(PLACE_SUFFIXES) + r"))\b")
    prefix_pattern = re.compile(r"\b((?:Lake|River|Mount|Port|Isle|Castle|Fortress|Palace|Temple|Tower|Forest)\s+[A-Z][A-Za-z'’-]+(?:\s+[A-Z][A-Za-z'’-]+){0,2})\b")
    for book, (_, folder) in BOOK_CATALOG.items():
        base = BOOKS / folder
        if not base.exists():
            continue
        for path in base.glob("sect*.htm"):
            match = re.search(r"sect(\d+)\.htm$", path.name, re.I)
            if not match:
                continue
            section = int(match.group(1))
            text = source_text(path)
            for found in title_pattern.finditer(text):
                name = clean_name(found.group(0))
                name = re.sub(r"[’']s?\b.*$", "", name).strip()
                if name.casefold() == "general store":
                    continue
                if len(name.split()) <= 5:
                    people_hits[name].add((book, section))
            for pattern in (suffix_pattern, prefix_pattern):
                for found in pattern.finditer(text):
                    name = clean_name(found.group(1))
                    if len(name.split()) <= 5:
                        place_hits[name].add((book, section))
    people = {}
    for name, refs in people_hits.items():
        if len(refs) < 2:
            continue
        people[name.casefold()] = {"id": slug(name), "name": name, "kind": name.split()[0], "sourceRefs": [source_ref(b, s, "encounter") for b, s in sorted(refs)]}
    places = {}
    for name, refs in place_hits.items():
        if len(refs) < 2 or "joe dever" in name.casefold():
            continue
        kind = next((part for part in name.split() if part in PLACE_SUFFIXES), name.split()[0])
        places[name.casefold()] = {"id": slug(name), "name": name, "kind": kind, "sourceRefs": [source_ref(b, s, "visited") for b, s in sorted(refs)]}
    return people, places


def apply_overrides(entries: dict[str, Any], overrides: dict[str, Any]) -> None:
    for key, override in overrides.items():
        normalized = key.casefold()
        entry = entries.setdefault(normalized, {"id": slug(override.get("name", key)), "name": override.get("name", key), "sourceRefs": []})
        existing_refs = entry.get("sourceRefs", [])
        entry.update(override)
        entry["id"] = entry.get("id") or slug(entry["name"])
        entry["sourceRefs"] = existing_refs + [ref for ref in override.get("sourceRefs", []) if ref not in existing_refs]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="Fail if the checked-in catalog is stale")
    args = parser.parse_args()
    items, creatures = extract_items_and_bestiary()
    people, places = extract_people_and_places()
    overrides = json.loads((DATA / "compendium-overrides.json").read_text(encoding="utf-8"))
    apply_overrides(items, overrides.get("items", {}))
    apply_overrides(people, overrides.get("people", {}))
    apply_overrides(places, overrides.get("places", {}))
    payload = {
        "schemaVersion": 1,
        "generatedFrom": {"books": len(BOOK_CATALOG), "sectionFiles": sum(1 for _, (_, folder) in BOOK_CATALOG.items() for _ in (BOOKS / folder).glob("sect*.htm"))},
        "categories": {
            "items": sorted(items.values(), key=lambda x: x["name"].casefold()),
            "bestiary": sorted(creatures.values(), key=lambda x: x["name"].casefold()),
            "people": sorted(people.values(), key=lambda x: x["name"].casefold()),
            "places": sorted(places.values(), key=lambda x: x["name"].casefold()),
        },
    }
    rendered = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.check:
        if not OUT.exists() or OUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("data/compendium.json is stale; run testing/build_compendium_catalog.py")
        return
    OUT.write_text(rendered, encoding="utf-8")
    counts = {key: len(value) for key, value in payload["categories"].items()}
    print(f"Wrote {OUT}: {counts}")


if __name__ == "__main__":
    main()
