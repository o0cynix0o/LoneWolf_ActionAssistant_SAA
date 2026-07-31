#!/usr/bin/env python3
"""HTTP app server for the Lone Wolf web assistant."""

from __future__ import annotations

import argparse
import contextlib
import io
import json
import mimetypes
import os
import secrets
import sys
import threading
import zipfile
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse, urlsplit

import lonewolf_redux
import book_manager
from cheat_session import CheatSession
from runtime_paths import PATHS


STATIC_ROOT = PATHS.resource_root
UI_PREFERENCES_FILE = PATHS.ui_preferences
SAVE_SLOT_DIR = PATHS.saves / "slots"
SAVE_SLOT_COUNT = 6
STATE_LOCK = threading.RLock()

# The server binds to loopback, but a browser page or a DNS-rebinding host can
# still reach it. Requests are only honored when they look like they came from
# the local desktop UI itself.
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1", "::1"}
CHEAT_SESSION = CheatSession()


def request_hostname(value: str | None) -> str | None:
    """Return the lowercased hostname from a Host/Origin header value."""
    if not value:
        return None
    parsed = urlsplit(value if "://" in value else "//" + value)
    return (parsed.hostname or "").lower() or None


def confine_save_path(raw: object, *, allow_index: bool = False) -> str:
    """Confine a client-supplied save path to the saves directory.

    The local CLI lets a user reference any path they type, but the HTTP API is
    reachable by web content, so a path arriving in an action payload must
    resolve inside PATHS.saves. Pure catalog indices (used by the web Load
    buttons) are passed through unchanged.
    """
    text = str(raw or "").strip().strip('"')
    if not text:
        return ""
    if allow_index and text.isdigit():
        return text
    base = PATHS.saves.resolve()
    candidate = Path(text)
    candidate = candidate if candidate.is_absolute() else base / candidate
    resolved = candidate.resolve()
    try:
        resolved.relative_to(base)
    except ValueError as exc:
        raise ValueError("Save path must stay inside the saves folder.") from exc
    return str(resolved)
ASSISTANT = lonewolf_redux.LoneWolfReduxAssistant(
    save_dir=PATHS.saves,
    data_dir=PATHS.resource_data,
    state_data_dir=PATHS.user_data,
    books_dir=PATHS.books_lw,
    cheat_provider=CHEAT_SESSION,
)
LAST_OUTPUT = ""

UI_PREFERENCE_KEYS = {
    "lonewolf_redux.top.layout.v1",
    "lonewolf_redux.top.sizes.v1",
    "lonewolf_redux.sheet.layout.v1",
    "lonewolf_redux.sheet.sizes.v1",
    "lonewolf_redux.appearance.titleBanner.v1",
    "lonewolf_redux.appearance.coverArt.v1",
    "lonewolf_redux.appearance.theme.v1",
    "lonewolf_redux.reader.styleEnabled.v1",
    "lonewolf_redux.reader.theme.v1",
}
UI_PREFERENCE_PREFIXES = (
    "lonewolf_redux.cards.layout.",
    "lonewolf_redux.cards.size.",
    "lonewolf_redux.cards.dimensions.",
    "lonewolf_redux.cards.closed.",
    "lonewolf_redux.cards.collapsed.",
    "lonewolf_redux.cards.labels.",
    "lonewolf_redux.appearance.",
    "lonewolf_redux.reader.",
)


def capture_output(func) -> str:
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        func()
    return buffer.getvalue().strip()


def load_last_save() -> None:
    loaded_save = False
    try:
        if ASSISTANT.last_save_file.exists():
            path = ASSISTANT.last_save_file.read_text(encoding="utf-8").strip()
            if path and Path(path).exists():
                ASSISTANT.load_game(path, quiet=True)
                loaded_save = True
    except Exception:
        pass
    if loaded_save:
        return

    try:
        if lonewolf_redux.CURRENT_POSITION_FILE.exists():
            position = json.loads(lonewolf_redux.CURRENT_POSITION_FILE.read_text(encoding="utf-8"))
            book_number = int(position.get("book") or 1)
            section = int(position.get("section") or 1)
            if book_number in lonewolf_redux.BOOKS:
                max_section = lonewolf_redux.BOOKS[book_number]["MaxSection"]
                section = section if 1 <= section <= max_section else 1
                ASSISTANT.character["BookNumber"] = book_number
                ASSISTANT.state["CurrentSection"] = section
                ASSISTANT.record_section_visit()
    except Exception:
        pass


def public_save_entries() -> list[dict]:
    entries = []
    for entry in ASSISTANT.catalog_saves():
        clean = dict(entry)
        clean["Path"] = str(clean["Path"])
        entries.append(clean)
    return entries


def save_slot_path(slot: int) -> Path:
    slot = max(1, min(SAVE_SLOT_COUNT, int(slot or 1)))
    return SAVE_SLOT_DIR / f"slot-{slot}.json"


def save_slot_entry(slot: int) -> dict:
    path = save_slot_path(slot)
    entry = {
        "Slot": slot,
        "Occupied": path.exists(),
        "Path": str(path),
        "Name": f"Slot {slot}",
        "BookNumber": "",
        "BookTitle": "",
        "Section": "",
        "Endurance": "",
        "GoldCrowns": "",
        "Modified": "",
    }
    if not path.exists():
        return entry
    entry["Modified"] = datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        character = data.get("Character", {}) if isinstance(data, dict) else {}
        inventory = data.get("Inventory", {}) if isinstance(data, dict) else {}
        book_number = int(character.get("BookNumber", 1))
        entry.update(
            {
                "Name": character.get("Name") or f"Slot {slot}",
                "BookNumber": book_number,
                "BookTitle": lonewolf_redux.book_title(book_number),
                "Section": int(data.get("CurrentSection", 1)),
                "Endurance": f"{character.get('EnduranceCurrent', '?')}/{character.get('EnduranceMax', '?')}",
                "GoldCrowns": inventory.get("GoldCrowns", "?"),
            }
        )
    except Exception:
        entry["BookTitle"] = "Unreadable save"
    return entry


def public_save_slots() -> list[dict]:
    return [save_slot_entry(slot) for slot in range(1, SAVE_SLOT_COUNT + 1)]


def save_to_slot(slot: int) -> str:
    slot = max(1, min(SAVE_SLOT_COUNT, int(slot or 1)))
    path = save_slot_path(slot)
    ASSISTANT.save_game(str(path), quiet=True)
    return f"Saved to slot {slot}."


def load_from_slot(slot: int) -> str:
    slot = max(1, min(SAVE_SLOT_COUNT, int(slot or 1)))
    path = save_slot_path(slot)
    if not path.exists():
        return f"Save slot {slot} is empty."
    return capture_output(lambda: ASSISTANT.load_game(str(path)))


def clear_save_slot(slot: int) -> str:
    slot = max(1, min(SAVE_SLOT_COUNT, int(slot or 1)))
    path = save_slot_path(slot)
    if path.exists():
        path.unlink()
        return f"Cleared save slot {slot}."
    return f"Save slot {slot} is already empty."


def truthy(value) -> bool:
    if isinstance(value, bool):
        return value
    return str(value or "").strip().lower() in {"1", "true", "yes", "on"}


def is_ui_preference_key(key: str) -> bool:
    return key in UI_PREFERENCE_KEYS or key.startswith(UI_PREFERENCE_PREFIXES)


def load_ui_preferences() -> dict:
    try:
        data = json.loads(UI_PREFERENCES_FILE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"version": 1, "values": {}}
    values = data.get("values") if isinstance(data, dict) else {}
    if not isinstance(values, dict):
        values = {}
    clean = {
        str(key): str(value)
        for key, value in values.items()
        if is_ui_preference_key(str(key)) and len(str(value)) <= 50000
    }
    return {"version": 1, "values": clean}


def save_ui_preferences(payload: dict) -> dict:
    values = payload.get("values") if isinstance(payload, dict) else {}
    if not isinstance(values, dict):
        values = {}
    clean = {
        str(key): str(value)
        for key, value in values.items()
        if is_ui_preference_key(str(key)) and len(str(value)) <= 50000
    }
    data = {"version": 1, "values": clean}
    UI_PREFERENCES_FILE.parent.mkdir(parents=True, exist_ok=True)
    UI_PREFERENCES_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def export_save_bytes() -> tuple[str, bytes]:
    ASSISTANT.sync_achievements(save=False)
    ASSISTANT.write_current_position()
    name = lonewolf_redux.safe_file_name(
        f"{ASSISTANT.character.get('Name') or 'Lone Wolf'}-book{ASSISTANT.character.get('BookNumber') or 1}"
    )
    return f"{name}.json", json.dumps(ASSISTANT.state, indent=2).encode("utf-8")


def backup_saves_bytes() -> tuple[str, bytes]:
    ASSISTANT.save_game(quiet=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(ASSISTANT.save_dir.glob("*.json")):
            archive.write(path, f"saves/{path.name}")
        if UI_PREFERENCES_FILE.exists():
            archive.write(UI_PREFERENCES_FILE, "data/ui-preferences.json")
    return f"LoneWolfRedux-saves-{stamp}.zip", buffer.getvalue()


def import_save_payload(payload: dict) -> str:
    raw = str(payload.get("raw") or "").strip()
    if not raw:
        raise ValueError("No save data supplied.")
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError("Save import must be a JSON object.")
    imported = lonewolf_redux.normalize_state(data)
    ASSISTANT.state = imported
    ASSISTANT.settings["SavePath"] = ""
    ASSISTANT.record_section_visit()
    ASSISTANT.ensure_current_section_checkpoint()
    ASSISTANT.sync_achievements(save=False)
    ASSISTANT.write_current_position()
    if truthy(payload.get("save", True)):
        ASSISTANT.save_game(quiet=True)
    return (
        f"Imported save for {ASSISTANT.character.get('Name') or 'Lone Wolf'}, "
        f"Book {ASSISTANT.character.get('BookNumber')}, section {ASSISTANT.state.get('CurrentSection')}."
    )


def state_payload(message: str = "", achievement_unlocks: list[dict] | None = None) -> dict:
    new_unlocks = ASSISTANT.sync_achievements(save=False)
    if new_unlocks:
        ASSISTANT.save_game(quiet=True)
    state = json.loads(json.dumps(ASSISTANT.state))
    state["Character"]["EnduranceCurrent"] = ASSISTANT.effective_endurance_current()
    state["Character"]["EnduranceMax"] = ASSISTANT.effective_endurance_max()
    state["Character"]["CombatSkillCurrent"] = ASSISTANT.effective_combat_skill()
    state["Character"]["KaiDisciplines"] = ASSISTANT.effective_disciplines()
    state["Combat"] = ASSISTANT.combat_status_payload()
    for key in ("HasHerbPouch", "HerbPouchItems"):
        state.get("Inventory", {}).pop(key, None)
    for checkpoint in lonewolf_redux.as_list(state.get("Automation", {}).get("SectionCheckpoints")):
        if isinstance(checkpoint, dict):
            checkpoint.pop("Snapshot", None)
    return {
        "books": lonewolf_redux.BOOKS,
        "state": state,
        "sectionFlow": ASSISTANT.current_section_flow_payload(),
        "death": ASSISTANT.death_recovery_payload(),
        "bookComplete": ASSISTANT.book_completion_payload(),
        "achievements": ASSISTANT.achievement_payload(),
        "achievementUnlocks": achievement_unlocks or [],
        "saves": public_save_entries(),
        "saveSlots": public_save_slots(),
        "uiPreferences": load_ui_preferences(),
        "paths": {
            "SaveDir": str(ASSISTANT.save_dir),
            "DataDir": str(ASSISTANT.data_dir),
            "UiPreferences": str(UI_PREFERENCES_FILE),
        },
        "message": message,
        "lastOutput": LAST_OUTPUT,
    }


def book_files_payload() -> dict:
    books = []
    for number, meta in sorted(lonewolf_redux.BOOKS.items()):
        folder = str(meta.get("Folder") or "")
        root = PATHS.books_lw / folder
        title_file = root / "title.htm"
        first_section = root / "sect1.htm"
        books.append(
            {
                "BookNumber": number,
                "Title": meta.get("Title"),
                "Folder": folder,
                "Installed": title_file.exists() and first_section.exists(),
                "ExpectedTitleFile": str(title_file),
                "ExpectedFirstSection": str(first_section),
            }
        )
    return {
        "Installed": all(book["Installed"] for book in books),
        "Books": books,
        "InstallGuide": "/install-books.html",
    }


def book_folder_names() -> tuple[str, ...]:
    return tuple(str(meta.get("Folder") or "") for meta in lonewolf_redux.BOOKS.values())


def handle_native_books(payload: dict) -> dict:
    action = str(payload.get("action") or "").strip()
    if action == "open":
        return {"ok": True, "path": book_manager.open_books_folder()}

    # File dialogs are created only on demand. Keeping tkinter out of the
    # pywebview JavaScript bridge avoids a pythonnet/WinForms startup deadlock.
    import tkinter as tk
    from tkinter import filedialog

    root = tk.Tk()
    root.withdraw()
    root.attributes("-topmost", True)
    try:
        if action == "folder":
            selected = filedialog.askdirectory(title="Select extracted Project Aon books")
            sources = [selected] if selected else []
        elif action == "zips":
            sources = list(
                filedialog.askopenfilenames(
                    title="Select Project Aon ZIP files",
                    filetypes=(("ZIP archives", "*.zip"),),
                )
            )
        else:
            raise ValueError(f"Unknown book action: {action}")
    finally:
        root.destroy()

    if not sources:
        return {"ok": False, "cancelled": True}
    result = book_manager.import_books(sources, book_folder_names())
    return {"ok": True, **result}


def apply_new_game(payload: dict) -> str:
    name = str(payload.get("name") or "Lone Wolf").strip() or "Lone Wolf"
    book_number = int(payload.get("bookNumber") or 1)
    disciplines = payload.get("kaiDisciplines")
    if book_number == 1 and truthy(payload.get("autoGenerate")):
        disciplines = auto_generated_kai_disciplines()
    elif not isinstance(disciplines, list):
        disciplines = lonewolf_redux.KAI_DISCIPLINES[:5]

    if book_number == 5:
        ASSISTANT.state = lonewolf_redux.create_book5_character_state(
            name=name,
            kai_disciplines=disciplines,
            section=int(payload.get("section") or 1),
            combat_skill_roll=payload.get("combatSkillRoll"),
            endurance_roll=payload.get("enduranceRoll"),
            gold_roll=payload.get("goldRoll"),
            weaponskill_roll=payload.get("weaponskillRoll"),
            equipment_choices=payload.get("equipmentChoices") or payload.get("armouryChoices"),
            weapon_exchanges=payload.get("weaponExchanges"),
            safekeeping_special_items=payload.get("safekeepingSpecialItems"),
        )
    elif book_number == 4:
        ASSISTANT.state = lonewolf_redux.create_book4_character_state(
            name=name,
            kai_disciplines=disciplines,
            section=int(payload.get("section") or 1),
            combat_skill_roll=payload.get("combatSkillRoll"),
            endurance_roll=payload.get("enduranceRoll"),
            gold_roll=payload.get("goldRoll"),
            weaponskill_roll=payload.get("weaponskillRoll"),
            equipment_choices=payload.get("equipmentChoices") or payload.get("armouryChoices"),
            weapon_exchanges=payload.get("weaponExchanges"),
        )
    elif book_number == 3:
        ASSISTANT.state = lonewolf_redux.create_book3_character_state(
            name=name,
            kai_disciplines=disciplines,
            section=int(payload.get("section") or 1),
            combat_skill_roll=payload.get("combatSkillRoll"),
            endurance_roll=payload.get("enduranceRoll"),
            gold_roll=payload.get("goldRoll"),
            weaponskill_roll=payload.get("weaponskillRoll"),
            equipment_choices=payload.get("equipmentChoices") or payload.get("armouryChoices"),
            weapon_exchanges=payload.get("weaponExchanges"),
        )
    elif book_number == 2:
        ASSISTANT.state = lonewolf_redux.create_book2_character_state(
            name=name,
            kai_disciplines=disciplines,
            section=int(payload.get("section") or 1),
            combat_skill_roll=payload.get("combatSkillRoll"),
            endurance_roll=payload.get("enduranceRoll"),
            gold_roll=payload.get("goldRoll"),
            weaponskill_roll=payload.get("weaponskillRoll"),
            armoury_choices=payload.get("armouryChoices"),
            weapon_exchanges=payload.get("weaponExchanges"),
        )
    else:
        ASSISTANT.state = lonewolf_redux.create_book1_character_state(
            name=name,
            kai_disciplines=disciplines,
            section=int(payload.get("section") or 1),
            combat_skill_roll=payload.get("combatSkillRoll"),
            endurance_roll=payload.get("enduranceRoll"),
            gold_roll=payload.get("goldRoll"),
            starting_find_roll=payload.get("startingFindRoll"),
            weaponskill_roll=payload.get("weaponskillRoll"),
        )
    ASSISTANT.record_section_visit()
    ASSISTANT.save_section_checkpoint("ready")
    ASSISTANT.write_current_position()
    ASSISTANT.autosave()
    return f"Created {name}, Book {book_number}."


def _creation_draft_roll(rolls: dict, key: str) -> int:
    """Return a supplied Book 1 creation digit, or securely generate one."""
    raw = rolls.get(key)
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return secrets.randbelow(10)
    if isinstance(raw, bool):
        raise ValueError(f"{key} must be a number from 0 to 9.")
    if isinstance(raw, float) and not raw.is_integer():
        raise ValueError(f"{key} must be a number from 0 to 9.")
    try:
        value = int(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{key} must be a number from 0 to 9.") from exc
    if not 0 <= value <= 9:
        raise ValueError(f"{key} must be a number from 0 to 9.")
    return value


def auto_generated_kai_disciplines() -> list[str]:
    """Choose five distinct Book 1 disciplines with the system RNG."""
    return secrets.SystemRandom().sample(lonewolf_redux.KAI_DISCIPLINES, k=5)


def create_book1_creation_draft(payload: dict) -> dict:
    """Build a Book 1 character-creation preview without changing a campaign.

    The web client may pass prior rolls back in ``rolls`` while asking for the
    next one.  Omitted rolls use ``secrets`` so the creation screen's dice are
    generated by the app rather than by browser JavaScript.
    """
    try:
        book_number = int(payload.get("bookNumber") or 1)
    except (TypeError, ValueError) as exc:
        raise ValueError("Creation drafts currently support Book 1 only.") from exc
    if book_number != 1:
        raise ValueError("Creation drafts currently support Book 1 only.")

    rolls = payload.get("rolls")
    if rolls is None:
        rolls = {}
    if not isinstance(rolls, dict):
        raise ValueError("Creation draft rolls must be an object.")

    combat_skill_roll = _creation_draft_roll(rolls, "combatSkillRoll")
    endurance_roll = _creation_draft_roll(rolls, "enduranceRoll")
    gold_roll = _creation_draft_roll(rolls, "goldRoll")
    starting_find_roll = _creation_draft_roll(rolls, "startingFindRoll")
    starting_find = lonewolf_redux.book1_starting_find_for_roll(starting_find_roll)

    endurance_base = 20 + endurance_roll
    endurance = endurance_base + int(starting_find.get("EnduranceBonus") or 0)
    gold_crowns = min(50, gold_roll + int(starting_find.get("Gold") or 0))
    draft = {
        "bookNumber": 1,
        "combatSkillRoll": combat_skill_roll,
        "enduranceRoll": endurance_roll,
        "goldRoll": gold_roll,
        "startingFindRoll": starting_find_roll,
        "combatSkill": 10 + combat_skill_roll,
        "enduranceBase": endurance_base,
        "endurance": endurance,
        "goldCrowns": gold_crowns,
        "startingFind": starting_find,
    }
    if truthy(payload.get("includeWeaponskill")):
        weaponskill_roll = _creation_draft_roll(rolls, "weaponskillRoll")
        draft["weaponskillRoll"] = weaponskill_roll
        draft["weaponskillWeapon"] = lonewolf_redux.weaponskill_weapon_for_roll(weaponskill_roll)
    if truthy(payload.get("autoGenerate")):
        draft["kaiDisciplines"] = auto_generated_kai_disciplines()
    return draft


def handle_action(payload: dict) -> str:
    action = str(payload.get("action") or "").strip()
    if not action:
        return "No action supplied."

    if action == "new":
        return apply_new_game(payload)
    if action == "set_position":
        book = payload.get("book")
        section = int(payload.get("section") or 1)
        if book:
            return capture_output(lambda: ASSISTANT.set_book(int(book), section))
        return capture_output(lambda: ASSISTANT.set_section(section))
    if action == "apply_automation":
        return capture_output(lambda: ASSISTANT.apply_current_section_automation())
    if action == "roll":
        raw = payload.get("raw")
        raw_roll = int(raw) if str(raw or "").strip() else None
        result = ASSISTANT.roll_current_section(raw_roll)
        route = result.get("Route")
        route_text = f" -> section {route}" if route else ""
        stage_text = f" | {result['StageLabel']}" if result.get("StageLabel") else ""
        outcome_text = f" | {result['Outcome']}" if result.get("Outcome") else ""
        messages = [f"Roll {result['Raw']} total {result['Total']}{stage_text}{outcome_text}{route_text}"]
        for message in result.get("ActionMessages") or []:
            messages.append(str(message))
        return "\n".join(messages)
    if action == "route":
        return capture_output(lambda: ASSISTANT.follow_route(int(payload.get("section") or 1)))
    if action == "flow_loot":
        return capture_output(lambda: ASSISTANT.apply_flow_loot(str(payload.get("id") or "")))
    if action == "cartwheel":
        raw = payload.get("raw")
        raw_roll = int(raw) if str(raw or "").strip() else None
        return capture_output(
            lambda: ASSISTANT.play_cartwheel(
                payload.get("bet"),
                payload.get("stake"),
                raw_roll,
                payload.get("useToken", True),
            )
        )
    if action == "portholes":
        return capture_output(
            lambda: ASSISTANT.play_portholes(
                payload.get("p1a"),
                payload.get("p1b"),
                payload.get("p2a"),
                payload.get("p2b"),
                payload.get("lwa"),
                payload.get("lwb"),
            )
        )
    if action == "gold_distraction":
        raw = payload.get("raw")
        raw_roll = int(raw) if str(raw or "").strip() else None
        return capture_output(lambda: ASSISTANT.play_gold_distraction(payload.get("amount"), raw_roll))
    if action == "healing":
        return capture_output(lambda: ASSISTANT.apply_healing())
    if action == "section_loss":
        return capture_output(
            lambda: ASSISTANT.apply_section_loss(
                str(payload.get("id") or ""),
                str(payload.get("type") or ""),
                str(payload.get("item") or payload.get("slot") or ""),
            )
        )
    if action == "status_flag":
        return capture_output(lambda: ASSISTANT.set_status_flag(str(payload.get("key") or ""), payload.get("value")))
    if action == "section_combat_start":
        return capture_output(lambda: ASSISTANT.start_section_combat(str(payload.get("id") or "")))
    if action == "adjust":
        stat = str(payload.get("stat") or "")
        mode = str(payload.get("mode") or "delta")
        value = int(payload.get("value") or 0)
        token = ["x", "set", str(value)] if mode == "set" else ["x", str(value)]
        if stat == "end":
            return capture_output(lambda: ASSISTANT.adjust_endurance(token))
        if stat == "cs":
            return capture_output(lambda: ASSISTANT.adjust_combat_skill(token))
        if stat == "gold":
            return capture_output(lambda: ASSISTANT.adjust_gold_crowns(token))
    if action == "add_item":
        return capture_output(lambda: ASSISTANT.add_item(["add", str(payload.get("type") or ""), str(payload.get("item") or "")]))
    if action == "drop_item":
        return capture_output(lambda: ASSISTANT.drop_item(["drop", str(payload.get("type") or ""), str(payload.get("item") or "")]))
    if action == "use_item":
        return capture_output(lambda: ASSISTANT.use_item(str(payload.get("type") or ""), str(payload.get("item") or "")))
    if action == "karmo_side_effect":
        raw = payload.get("raw")
        raw_roll = int(raw) if str(raw or "").strip() else None
        return capture_output(lambda: ASSISTANT.apply_karmo_side_effect(raw_roll))
    if action == "karmo_finish":
        return capture_output(lambda: ASSISTANT.finish_karmo_potion())
    if action == "death_recovery":
        return capture_output(lambda: ASSISTANT.restore_death_checkpoint(str(payload.get("mode") or "repeat")))
    if action == "meal":
        tokens = ["meal", "missed"] if payload.get("missed") else ["meal"]
        return capture_output(lambda: ASSISTANT.meal_command(tokens))
    if action == "power":
        return "Kai Disciplines can only be changed during character creation or a book transition."
    if action == "assign_weaponskill":
        return capture_output(lambda: ASSISTANT.assign_missing_weaponskill_weapon(payload.get("roll")))
    if action == "note":
        return capture_output(lambda: ASSISTANT.note_command(["note", str(payload.get("text") or "")]))
    if action == "save":
        target = confine_save_path(payload.get("path"))
        return capture_output(lambda: ASSISTANT.save_game(target))
    if action == "load":
        target = confine_save_path(payload.get("path"), allow_index=True)
        return capture_output(lambda: ASSISTANT.load_game(target))
    if action == "save_slot":
        return save_to_slot(int(payload.get("slot") or 1))
    if action == "load_slot":
        return load_from_slot(int(payload.get("slot") or 1))
    if action == "clear_slot":
        return clear_save_slot(int(payload.get("slot") or 1))
    if action == "reload_last_save":
        load_last_save()
        return "Reloaded the latest save from disk."
    if action == "import_save":
        return import_save_payload(payload)
    if action == "complete_book":
        def complete() -> None:
            summary = ASSISTANT.ensure_book_completed(save=True)
            print(f"Book {summary['BookNumber']} complete: {summary['BookTitle']}.")
        return capture_output(complete)
    if action == "continue_book":
        return capture_output(
            lambda: ASSISTANT.continue_completed_book(
                kai_discipline=str(payload.get("kaiDiscipline") or ""),
                weaponskill_roll=payload.get("weaponskillRoll"),
                book2_gold_roll=payload.get("goldRoll"),
                book2_armoury_choices=payload.get("armouryChoices"),
                book2_weapon_exchanges=payload.get("weaponExchanges"),
                book3_gold_roll=payload.get("goldRoll"),
                book3_equipment_choices=payload.get("equipmentChoices") or payload.get("armouryChoices"),
                book3_weapon_exchanges=payload.get("weaponExchanges"),
                book4_gold_roll=payload.get("goldRoll"),
                book4_equipment_choices=payload.get("equipmentChoices") or payload.get("armouryChoices"),
                book4_weapon_exchanges=payload.get("weaponExchanges"),
                book5_gold_roll=payload.get("goldRoll"),
                book5_equipment_choices=payload.get("equipmentChoices") or payload.get("armouryChoices"),
                book5_weapon_exchanges=payload.get("weaponExchanges"),
                book5_safekeeping_special_items=payload.get("safekeepingSpecialItems"),
            )
        )
    if action == "repeat_book":
        return capture_output(lambda: ASSISTANT.repeat_completed_book())
    if action == "combat_start":
        name = str(payload.get("name") or "Enemy")
        cs = int(payload.get("cs") or 10)
        end = int(payload.get("endurance") or 10)
        def start() -> None:
            ASSISTANT.start_combat(["combat", "start", name, str(cs), str(end)])
            if ASSISTANT.combat.get("Active"):
                if "activeWeapon" in payload:
                    ASSISTANT.set_combat_weapon(str(payload.get("activeWeapon") or ""), save=False)
                ASSISTANT.combat["Modifier"] = int(payload.get("modifier") or 0)
                ASSISTANT.combat["CanEvade"] = truthy(payload.get("canEvade"))
                ASSISTANT.combat["EvadeAfterRounds"] = max(0, int(payload.get("evadeAfterRounds") or 0))
                victory_route = payload.get("victoryRoute")
                evade_route = payload.get("evadeRoute")
                ASSISTANT.combat["VictoryRoute"] = int(victory_route) if str(victory_route or "").strip() else None
                ASSISTANT.combat["EvadeRoute"] = int(evade_route) if str(evade_route or "").strip() else None
                ASSISTANT.autosave()
        return capture_output(start)
    if action == "combat_round":
        if "activeWeapon" in payload:
            ASSISTANT.set_combat_weapon(str(payload.get("activeWeapon") or ""), save=False)
        tokens = ["combat", "evade" if payload.get("evade") else "round"]
        if payload.get("roll") not in (None, ""):
            tokens.append(str(payload.get("roll")))
        return capture_output(lambda: ASSISTANT.combat_round(tokens, evade=bool(payload.get("evade"))))
    if action == "combat_auto":
        return capture_output(lambda: ASSISTANT.resolve_combat_to_outcome())
    if action == "combat_evade":
        if "activeWeapon" in payload:
            ASSISTANT.set_combat_weapon(str(payload.get("activeWeapon") or ""), save=False)
        tokens = ["combat", "evade"]
        if payload.get("roll") not in (None, ""):
            tokens.append(str(payload.get("roll")))
        return capture_output(lambda: ASSISTANT.evade_combat(tokens))
    if action == "combat_weapon":
        return capture_output(lambda: ASSISTANT.set_combat_weapon(str(payload.get("activeWeapon") or "")))
    if action == "combat_stop":
        return capture_output(lambda: ASSISTANT.stop_combat())
    if action == "autosave":
        ASSISTANT.settings["AutoSave"] = True
        ASSISTANT.save_game(quiet=True)
        return "Autosave is always on."

    return f"Unknown action: {action}"


class LoneWolfReduxHandler(BaseHTTPRequestHandler):
    server_version = "LoneWolfReduxHTTP/0.1"

    def log_message(self, format: str, *args) -> None:  # noqa: A003
        return

    def host_header_is_local(self) -> bool:
        # An absent Host (bare HTTP/1.0) is allowed; a present Host must be local
        # so a DNS-rebinding page (Host: attacker.example -> 127.0.0.1) is
        # rejected before it can reach any endpoint.
        host = request_hostname(self.headers.get("Host"))
        return host is None or host in LOCAL_HOSTNAMES

    def reject(self, message: str) -> None:
        # Drain any request body before replying so keep-alive stays in sync and
        # the caller reliably reads the 403 instead of a reset connection.
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            length = 0
        if length > 0:
            try:
                self.rfile.read(length)
            except OSError:
                pass
        self.send_json({"error": message}, HTTPStatus.FORBIDDEN)

    def send_json(self, data: dict, status: int = 200) -> None:
        body = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_download(self, filename: str, data: bytes, content_type: str) -> None:
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self) -> None:  # noqa: N802
        if not self.host_header_is_local():
            self.reject("Requests must originate from localhost.")
            return
        parsed = urlparse(self.path)
        if parsed.path == "/api/state":
            with STATE_LOCK:
                self.send_json(state_payload())
            return
        if parsed.path == "/api/saves":
            with STATE_LOCK:
                self.send_json({"saves": public_save_entries()})
            return
        if parsed.path == "/api/save-slots":
            with STATE_LOCK:
                self.send_json({"slots": public_save_slots()})
            return
        if parsed.path == "/api/ui-preferences":
            with STATE_LOCK:
                self.send_json(load_ui_preferences())
            return
        if parsed.path == "/api/book-files":
            self.send_json(book_files_payload())
            return
        if parsed.path == "/api/export-save":
            with STATE_LOCK:
                filename, data = export_save_bytes()
                self.send_download(filename, data, "application/json; charset=utf-8")
            return
        if parsed.path == "/api/backup-saves":
            with STATE_LOCK:
                filename, data = backup_saves_bytes()
                self.send_download(filename, data, "application/zip")
            return
        if parsed.path == "/current-position.json":
            try:
                data = json.loads(PATHS.current_position.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}
            self.send_json(data)
            return
        self.serve_static(parsed.path)

    def do_POST(self) -> None:  # noqa: N802
        if not self.host_header_is_local():
            self.reject("Requests must originate from localhost.")
            return
        # A cross-site page can POST to loopback, so require a same-origin
        # request. Demanding application/json also forces a CORS preflight for
        # any cross-origin attempt, which the Origin check then rejects.
        origin = self.headers.get("Origin")
        if origin is not None and request_hostname(origin) not in LOCAL_HOSTNAMES:
            self.reject("Cross-origin requests are not allowed.")
            return
        content_type = (self.headers.get("Content-Type") or "").split(";", 1)[0].strip().lower()
        if content_type != "application/json":
            self.reject("Requests must use application/json.")
            return
        parsed = urlparse(self.path)
        if parsed.path not in {"/api/action", "/api/ui-preferences", "/api/native-books", "/api/internal/session-cheats"}:
            self.send_json({"error": "Not found"}, HTTPStatus.NOT_FOUND)
            return
        length = int(self.headers.get("Content-Length") or 0)
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except json.JSONDecodeError:
            self.send_json({"error": "Invalid JSON"}, HTTPStatus.BAD_REQUEST)
            return
        if parsed.path == "/api/internal/session-cheats":
            supplied = self.headers.get("X-LoneWolf-Session") or ""
            if not secrets.compare_digest(supplied, CHEAT_SESSION.token):
                self.send_json({"error": "Invalid desktop session token."}, HTTPStatus.FORBIDDEN)
                return
            with STATE_LOCK:
                self.send_json(CHEAT_SESSION.handle(payload))
            return
        if parsed.path == "/api/ui-preferences":
            with STATE_LOCK:
                self.send_json(save_ui_preferences(payload))
            return
        if parsed.path == "/api/native-books":
            try:
                self.send_json(handle_native_books(payload))
            except Exception as exc:
                self.send_json({"ok": False, "error": str(exc)}, HTTPStatus.BAD_REQUEST)
            return

        global LAST_OUTPUT
        with STATE_LOCK:
            try:
                action_name = str(payload.get("action") or "").strip()
                if action_name == "creation_draft":
                    # A creation preview intentionally does not touch the active
                    # campaign, autosave, achievements, or last-action output.
                    self.send_json({"creationDraft": create_book1_creation_draft(payload)})
                    return
                before_unlocks = ASSISTANT.achievement_unlocked_ids()
                cheat_resources = ASSISTANT.cheat_resource_snapshot()
                if action_name == "shutdown":
                    ASSISTANT.save_game(quiet=True)
                    message = "Lone Wolf assistant server is shutting down."
                    LAST_OUTPUT = message
                    self.send_json(state_payload(message=message))
                    threading.Thread(target=self.server.shutdown, daemon=True).start()
                    return
                message = handle_action(payload)
                ASSISTANT.finalize_cheat_resources(cheat_resources)
                ASSISTANT.sync_achievements(save=False)
                after_unlocks = [
                    entry
                    for entry in lonewolf_redux.as_list(ASSISTANT.achievement_state().get("Unlocked"))
                    if isinstance(entry, dict) and str(entry.get("Id") or "") not in before_unlocks
                ]
                if after_unlocks:
                    ASSISTANT.save_game(quiet=True)
                if action_name in {"load", "save", "autosave", "load_slot", "save_slot", "clear_slot"}:
                    after_unlocks = []
                LAST_OUTPUT = message
                self.send_json(state_payload(message=message, achievement_unlocks=after_unlocks))
            except Exception as exc:
                LAST_OUTPUT = str(exc)
                self.send_json({"error": str(exc), **state_payload(message=str(exc))}, HTTPStatus.BAD_REQUEST)

    def serve_static(self, raw_path: str) -> None:
        relative = unquote(raw_path.lstrip("/")) or "index.html"
        if relative == "books" or relative.startswith("books/"):
            base = PATHS.books
            book_relative = relative.removeprefix("books").lstrip("/")
            target = (base / book_relative).resolve()
        else:
            base = STATIC_ROOT
            target = (base / relative).resolve()
        try:
            target.relative_to(base)
        except ValueError:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if target.is_dir():
            target = target / "index.html"
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return

        content_type = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        data = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


def create_server(host: str = "127.0.0.1", port: int = 8797) -> ThreadingHTTPServer:
    """Create a configured HTTP server. Port 0 requests a free OS port."""
    PATHS.ensure_writable()
    load_last_save()
    return ThreadingHTTPServer((host, port), LoneWolfReduxHandler)


def start_server(
    host: str = "127.0.0.1", port: int = 8797
) -> tuple[ThreadingHTTPServer, threading.Thread]:
    """Start the HTTP server on a daemon thread and return both handles."""
    server = create_server(host, port)
    thread = threading.Thread(
        target=server.serve_forever,
        name="lonewolf-http",
        daemon=True,
    )
    thread.start()
    return server, thread


def stop_server(server: ThreadingHTTPServer, thread: threading.Thread | None = None) -> None:
    """Persist state and stop a running HTTP server."""
    with STATE_LOCK:
        try:
            ASSISTANT.save_game(quiet=True)
        except Exception:
            pass
    server.shutdown()
    server.server_close()
    if thread and thread.is_alive():
        thread.join(timeout=5)


def main() -> int:
    parser = argparse.ArgumentParser(description="Lone Wolf web app server")
    parser.add_argument("--host", default="localhost")
    parser.add_argument(
        "--port",
        type=int,
        default=int(os.environ.get("LONEWOLF_REDUX_HTTP_PORT", "8797")),
    )
    args = parser.parse_args()

    server = create_server(args.host, args.port)
    actual_port = int(server.server_address[1])
    print(f"Lone Wolf web app: http://{args.host}:{actual_port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
