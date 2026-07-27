#!/usr/bin/env python3
"""
Lone Wolf Action Assistant Redux.

This is the Python rules and state engine for the Lone Wolf Action Assistant
Redux rebuild.
"""

from __future__ import annotations

import argparse
import html
import json
import os
import random
import re
import sys
import textwrap
from datetime import datetime
from pathlib import Path
from typing import Any

from runtime_paths import PATHS


ROOT = Path(__file__).resolve().parent
DEFAULT_SAVE_DIR = PATHS.saves
DEFAULT_DATA_DIR = PATHS.resource_data
DEFAULT_STATE_DATA_DIR = PATHS.user_data
DEFAULT_BOOKS_DIR = PATHS.books_lw
CURRENT_POSITION_FILE = PATHS.current_position
ERROR_LOG_FILE = PATHS.logs / "lonewolf_redux-error.log"
SCREEN_WIDTH = 74
SECTION_AUTOMATION_GLOB = "book*-simple-automations.json"
SECTION_FLOW_GLOB = "book*-section-flows.json"
ROUTE_CHECK_GLOB = "book*-route-checks.json"
ACHIEVEMENT_SCHEMA_VERSION = 1
LEGACY_PLAYER_LOSS_KEYS = ("Gray" + "StarLoss",)

ANSI_COLORS = {
    "Black": "30",
    "DarkBlue": "34",
    "DarkGreen": "32",
    "DarkCyan": "36",
    "DarkRed": "31",
    "DarkMagenta": "35",
    "DarkYellow": "33",
    "Gray": "37",
    "DarkGray": "90",
    "Blue": "94",
    "Green": "92",
    "Cyan": "96",
    "Red": "91",
    "Magenta": "95",
    "Yellow": "93",
    "White": "97",
}

SCREEN_ACCENTS = {
    "sheet": "Cyan",
    "inventory": "DarkYellow",
    "disciplines": "Magenta",
    "sections": "Cyan",
    "combat": "Red",
    "death": "Red",
    "loot": "DarkYellow",
    "choices": "DarkYellow",
    "notes": "Cyan",
    "stats": "Cyan",
    "campaign": "Green",
}

_ANSI_SUPPORT: bool | None = None

BOOKS = {
    1: {"Title": "Flight from the Dark", "Folder": "01fftd", "MaxSection": 350},
    2: {"Title": "Fire on the Water", "Folder": "02fotw", "MaxSection": 350},
    3: {"Title": "The Caverns of Kalte", "Folder": "03tcok", "MaxSection": 350},
    4: {"Title": "The Chasm of Doom", "Folder": "04tcod", "MaxSection": 350},
    5: {"Title": "Shadow on the Sand", "Folder": "05sots", "MaxSection": 400},
}

KAI_DISCIPLINES = [
    "Camouflage",
    "Hunting",
    "Sixth Sense",
    "Tracking",
    "Healing",
    "Weaponskill",
    "Mindshield",
    "Mindblast",
    "Animal Kinship",
    "Mind Over Matter",
]

WEAPONSKILL_MAP = {
    0: "Dagger",
    1: "Spear",
    2: "Mace",
    3: "Short Sword",
    4: "Warhammer",
    5: "Sword",
    6: "Axe",
    7: "Sword",
    8: "Quarterstaff",
    9: "Broadsword",
}

BOOK1_STARTING_FIND = {
    0: {"Type": "weapon", "Name": "Broadsword", "Quantity": 1, "Gold": 0, "EnduranceBonus": 0},
    1: {"Type": "weapon", "Name": "Sword", "Quantity": 1, "Gold": 0, "EnduranceBonus": 0},
    2: {"Type": "special", "Name": "Helmet", "Quantity": 1, "Gold": 0, "EnduranceBonus": 2},
    3: {"Type": "backpack", "Name": "Meal", "Quantity": 2, "Gold": 0, "EnduranceBonus": 0},
    4: {"Type": "special", "Name": "Chainmail Waistcoat", "Quantity": 1, "Gold": 0, "EnduranceBonus": 4},
    5: {"Type": "weapon", "Name": "Mace", "Quantity": 1, "Gold": 0, "EnduranceBonus": 0},
    6: {"Type": "backpack", "Name": "Healing Potion", "Quantity": 1, "Gold": 0, "EnduranceBonus": 0},
    7: {"Type": "weapon", "Name": "Quarterstaff", "Quantity": 1, "Gold": 0, "EnduranceBonus": 0},
    8: {"Type": "weapon", "Name": "Spear", "Quantity": 1, "Gold": 0, "EnduranceBonus": 0},
    9: {"Type": "gold", "Name": "12 Gold Crowns", "Quantity": 0, "Gold": 12, "EnduranceBonus": 0},
}

BOOK2_ARMOURY_OPTIONS = {
    "sword": {"Label": "Sword", "Items": [("weapon", "Sword")]},
    "short-sword": {"Label": "Short Sword", "Items": [("weapon", "Short Sword")]},
    "two-meals": {"Label": "Two Meals", "Items": [("backpack", "Meal"), ("backpack", "Meal")]},
    "chainmail-waistcoat": {
        "Label": "Chainmail Waistcoat",
        "Items": [("special", "Chainmail Waistcoat")],
        "EnduranceBonus": 4,
    },
    "mace": {"Label": "Mace", "Items": [("weapon", "Mace")]},
    "healing-potion": {"Label": "Healing Potion", "Items": [("backpack", "Healing Potion")]},
    "quarterstaff": {"Label": "Quarterstaff", "Items": [("weapon", "Quarterstaff")]},
    "spear": {"Label": "Spear", "Items": [("weapon", "Spear")]},
    "shield": {"Label": "Shield", "Items": [("special", "Shield")]},
    "broadsword": {"Label": "Broadsword", "Items": [("weapon", "Broadsword")]},
}

BOOK3_EQUIPMENT_OPTIONS = {
    "sword": {"Label": "Sword", "Items": [("weapon", "Sword")]},
    "short-sword": {"Label": "Short Sword", "Items": [("weapon", "Short Sword")]},
    "padded-leather-waistcoat": {
        "Label": "Padded Leather Waistcoat",
        "Items": [("special", "Padded Leather Waistcoat")],
        "EnduranceBonus": 2,
    },
    "spear": {"Label": "Spear", "Items": [("weapon", "Spear")]},
    "mace": {"Label": "Mace", "Items": [("weapon", "Mace")]},
    "warhammer": {"Label": "Warhammer", "Items": [("weapon", "Warhammer")]},
    "axe": {"Label": "Axe", "Items": [("weapon", "Axe")]},
    "potion-of-laumspur": {
        "Label": "Potion of Laumspur",
        "Items": [("backpack", "Potion of Laumspur (+4 END)")],
    },
    "quarterstaff": {"Label": "Quarterstaff", "Items": [("weapon", "Quarterstaff")]},
    "special-rations": {"Label": "Special Rations", "Items": [("backpack", "Meal")]},
    "broadsword": {"Label": "Broadsword", "Items": [("weapon", "Broadsword")]},
}

BOOK4_EQUIPMENT_OPTIONS = {
    "warhammer": {"Label": "Warhammer", "Items": [("weapon", "Warhammer")]},
    "dagger": {"Label": "Dagger", "Items": [("weapon", "Dagger")]},
    "two-potions-of-laumspur": {
        "Label": "2 Potions of Laumspur",
        "Items": [
            ("backpack", "Potion of Laumspur (+4 END)"),
            ("backpack", "Potion of Laumspur (+4 END)"),
        ],
    },
    "sword": {"Label": "Sword", "Items": [("weapon", "Sword")]},
    "spear": {"Label": "Spear", "Items": [("weapon", "Spear")]},
    "five-special-rations": {
        "Label": "5 Special Rations",
        "Items": [("backpack", "Meal")] * 5,
    },
    "mace": {"Label": "Mace", "Items": [("weapon", "Mace")]},
    "chainmail-waistcoat": {
        "Label": "Chainmail Waistcoat",
        "Items": [("special", "Chainmail Waistcoat")],
        "EnduranceBonus": 4,
    },
    "shield": {"Label": "Shield", "Items": [("special", "Shield")]},
}

BOOK5_EQUIPMENT_OPTIONS = {
    "dagger": {"Label": "Dagger", "Items": [("weapon", "Dagger")]},
    "potion-of-laumspur": {
        "Label": "Potion of Laumspur",
        "Items": [("backpack", "Potion of Laumspur (+4 END)")],
    },
    "sword": {"Label": "Sword", "Items": [("weapon", "Sword")]},
    "spear": {"Label": "Spear", "Items": [("weapon", "Spear")]},
    "two-special-rations": {
        "Label": "2 Special Rations",
        "Items": [("backpack", "Meal"), ("backpack", "Meal")],
    },
    "mace": {"Label": "Mace", "Items": [("weapon", "Mace")]},
    "shield": {"Label": "Shield", "Items": [("special", "Shield")]},
}

KAI_RANKS = [
    (10, "Kai Master"),
    (9, "Savant"),
    (8, "Warmarn"),
    (7, "Guardian"),
    (6, "Aspirant"),
    (5, "Initiate"),
]

# Legacy constants are kept only so older save/transition code can normalize without
# raising NameError. Book 1 character creation and UI use KAI_DISCIPLINES instead.
LESSER_MAGICKS: list[str] = []
HIGHER_MAGICKS: list[str] = []

LONE_WOLF_BOOK1_ACHIEVEMENTS = [
    {
        "Id": "lw1_complete",
        "Name": "Flight from the Dark",
        "BookNumber": 1,
        "Category": "Story",
        "Description": "Complete Book 1.",
    },
    {
        "Id": "lw1_reach_holmgard",
        "Name": "To The King's Citadel",
        "BookNumber": 1,
        "Category": "Story",
        "Description": "Reach section 350.",
    },
    {
        "Id": "lw1_clean_story_route",
        "Name": "Messenger To The King",
        "BookNumber": 1,
        "Category": "Route",
        "Description": "Complete the checked story route to Holmgard.",
    },
    {
        "Id": "lw1_first_blood",
        "Name": "First Blood",
        "BookNumber": 1,
        "Category": "Combat",
        "Description": "Win your first recorded Book 1 combat.",
    },
    {
        "Id": "lw1_gourgaz_victory",
        "Name": "Gourgaz Slayer",
        "BookNumber": 1,
        "Category": "Combat",
        "Description": "Win the recorded section 255 combat.",
    },
    {
        "Id": "lw1_princes_sword",
        "Name": "Prince's Sword",
        "BookNumber": 1,
        "Category": "Item",
        "Description": "Take the Prince's Sword.",
    },
    {
        "Id": "lw1_vordak_gem_backlash",
        "Name": "Dark Gem Burn",
        "BookNumber": 1,
        "Category": "Danger",
        "Description": "Reach the dark-gem backlash outcome.",
    },
    {
        "Id": "lw1_vordak_gem_failure",
        "Name": "Too Late To Turn Back",
        "BookNumber": 1,
        "Category": "Failure",
        "Description": "Record the dark-gem failure outcome.",
    },
    {
        "Id": "lw1_capture_escape",
        "Name": "Captive No More",
        "BookNumber": 1,
        "Category": "Route",
        "Description": "Escape from captivity.",
    },
    {
        "Id": "lw1_capture_death",
        "Name": "No Way Out",
        "BookNumber": 1,
        "Category": "Failure",
        "Description": "Record the captive-death outcome.",
    },
    {
        "Id": "lw1_paid_ferry",
        "Name": "Paid Passage",
        "BookNumber": 1,
        "Category": "Resource",
        "Description": "Use the paid ferry route.",
    },
    {
        "Id": "lw1_caravan_fare",
        "Name": "Caravan Fare",
        "BookNumber": 1,
        "Category": "Resource",
        "Description": "Use the caravan fare route.",
    },
    {
        "Id": "lw1_backpack_lost",
        "Name": "Travel Light",
        "BookNumber": 1,
        "Category": "Inventory",
        "Description": "Reach a checked gear-loss section.",
    },
    {
        "Id": "lw1_marsh_escape",
        "Name": "Out Of The Morass",
        "BookNumber": 1,
        "Category": "Random",
        "Description": "Survive the marsh-roll branch.",
    },
    {
        "Id": "lw1_crystal_star_pendant",
        "Name": "Crystal Star Pendant",
        "BookNumber": 1,
        "Category": "Item",
        "Description": "Take the Crystal Star Pendant.",
    },
    {
        "Id": "lw1_long_road",
        "Name": "Long Road to Holmgard",
        "BookNumber": 1,
        "Category": "Exploration",
        "Description": "Visit 75 or more unique Book 1 sections.",
    },
]

LONE_WOLF_BOOK2_ACHIEVEMENTS = [
    {
        "Id": "lw2_complete",
        "Name": "Fire on the Water",
        "BookNumber": 2,
        "Category": "Story",
        "Description": "Complete Book 2.",
    },
    {
        "Id": "lw2_reach_hammerdal",
        "Name": "The Hammerdal Road",
        "BookNumber": 2,
        "Category": "Story",
        "Description": "Reach Hammerdal.",
    },
    {
        "Id": "lw2_claim_sommerswerd",
        "Name": "The Sun-Sword Returns",
        "BookNumber": 2,
        "Category": "Item",
        "Description": "Claim the Sommerswerd.",
    },
    {
        "Id": "lw2_magic_spear",
        "Name": "Borrowed Thunder",
        "BookNumber": 2,
        "Category": "Item",
        "Description": "Take the Magic Spear.",
    },
    {
        "Id": "lw2_helghast_victory",
        "Name": "Helghast Breaker",
        "BookNumber": 2,
        "Category": "Combat",
        "Description": "Win a recorded Book 2 Helghast combat.",
    },
    {
        "Id": "lw2_arm_wrestling_win",
        "Name": "Table Manners",
        "BookNumber": 2,
        "Category": "Resource",
        "Description": "Win the tavern arm-wrestling purse.",
    },
    {
        "Id": "lw2_survive_green_sceptre",
        "Name": "Shipwrecked But Moving",
        "BookNumber": 2,
        "Category": "Danger",
        "Description": "Survive the Green Sceptre disaster route.",
    },
    {
        "Id": "lw2_red_pass",
        "Name": "Red Pass, Green Light",
        "BookNumber": 2,
        "Category": "Route",
        "Description": "Secure harbour access in Port Bax.",
    },
    {
        "Id": "lw2_deadly_documents",
        "Name": "Paper Trail",
        "BookNumber": 2,
        "Category": "Failure",
        "Description": "Record the forged access-papers death.",
    },
    {
        "Id": "lw2_long_road",
        "Name": "Across The Lastlands",
        "BookNumber": 2,
        "Category": "Exploration",
        "Description": "Visit 90 or more unique Book 2 sections.",
    },
]

LONE_WOLF_BOOK3_ACHIEVEMENTS = [
    {
        "Id": "lw3_complete",
        "Name": "The Caverns of Kalte",
        "BookNumber": 3,
        "Category": "Story",
        "Description": "Complete Book 3.",
    },
    {
        "Id": "lw3_capture_vonotar",
        "Name": "Traitor in Chains",
        "BookNumber": 3,
        "Category": "Story",
        "Description": "Bring Vonotar back from Kalte.",
    },
    {
        "Id": "lw3_mission_failed",
        "Name": "Cold Comfort",
        "BookNumber": 3,
        "Category": "Failure",
        "Description": "Record the Book 3 mission-failure ending.",
    },
    {
        "Id": "lw3_firesphere",
        "Name": "Warm Hands, Clear Head",
        "BookNumber": 3,
        "Category": "Item",
        "Description": "Take the Firesphere.",
    },
    {
        "Id": "lw3_silver_helm",
        "Name": "Helm of Ikaya",
        "BookNumber": 3,
        "Category": "Item",
        "Description": "Take the Silver Helm.",
    },
    {
        "Id": "lw3_baknar_oil",
        "Name": "Field-Proven Ointment",
        "BookNumber": 3,
        "Category": "Item",
        "Description": "Take Baknar Oil.",
    },
    {
        "Id": "lw3_crystal_frostwyrm",
        "Name": "Frostwyrm Breaker",
        "BookNumber": 3,
        "Category": "Combat",
        "Description": "Win the recorded Crystal Frostwyrm combat.",
    },
    {
        "Id": "lw3_long_road",
        "Name": "Across the Ice",
        "BookNumber": 3,
        "Category": "Exploration",
        "Description": "Visit 90 or more unique Book 3 sections.",
    },
]

LONE_WOLF_BOOK4_ACHIEVEMENTS = [
    {
        "Id": "lw4_complete",
        "Name": "The Chasm of Doom",
        "BookNumber": 4,
        "Category": "Story",
        "Description": "Complete Book 4.",
    },
    {
        "Id": "lw4_dagger_vashna",
        "Name": "Dagger of Vashna",
        "BookNumber": 4,
        "Category": "Item",
        "Description": "Carry forward the Dagger of Vashna.",
    },
    {
        "Id": "lw4_onyx_medallion",
        "Name": "Black Stone, Bright Idea",
        "BookNumber": 4,
        "Category": "Item",
        "Description": "Take the Onyx Medallion.",
    },
    {
        "Id": "lw4_mine_treasure",
        "Name": "Mine-Cart Accounting",
        "BookNumber": 4,
        "Category": "Item",
        "Description": "Recover the Maaken mine treasure cache.",
    },
    {
        "Id": "lw4_barraka_victory",
        "Name": "Cult Breaker",
        "BookNumber": 4,
        "Category": "Combat",
        "Description": "Win a recorded Barraka combat.",
    },
    {
        "Id": "lw4_holy_water",
        "Name": "Bottle Service",
        "BookNumber": 4,
        "Category": "Item",
        "Description": "Take a Flask of Holy Water.",
    },
    {
        "Id": "lw4_bad_key",
        "Name": "Iron Key, Bad Feeling",
        "BookNumber": 4,
        "Category": "Danger",
        "Description": "Take the dangerous Iron Key.",
    },
    {
        "Id": "lw4_long_road",
        "Name": "Ruanon Investigator",
        "BookNumber": 4,
        "Category": "Exploration",
        "Description": "Visit 90 or more unique Book 4 sections.",
    },
]

LONE_WOLF_BOOK5_ACHIEVEMENTS = [
    {
        "Id": "lw5_complete",
        "Name": "Shadow on the Sand",
        "BookNumber": 5,
        "Category": "Story",
        "Description": "Complete Book 5.",
    },
    {
        "Id": "lw5_book_magnakai",
        "Name": "Book of the Magnakai",
        "BookNumber": 5,
        "Category": "Story",
        "Description": "Claim the Book of the Magnakai.",
    },
    {
        "Id": "lw5_kai_master",
        "Name": "Kai Master",
        "BookNumber": 5,
        "Category": "Story",
        "Description": "Complete the Kai series and become a Kai Master.",
    },
    {
        "Id": "lw5_black_sash",
        "Name": "Dressed for Barrakeesh",
        "BookNumber": 5,
        "Category": "Item",
        "Description": "Buy the Black Sash.",
    },
    {
        "Id": "lw5_recover_gear",
        "Name": "Nothing Missing. Probably.",
        "BookNumber": 5,
        "Category": "Inventory",
        "Description": "Recover confiscated gear in the palace.",
    },
    {
        "Id": "lw5_jewelled_mace",
        "Name": "Diplomatic Weight",
        "BookNumber": 5,
        "Category": "Item",
        "Description": "Take the Jewelled Mace.",
    },
    {
        "Id": "lw5_itikar_rider",
        "Name": "Updraft Negotiations",
        "BookNumber": 5,
        "Category": "Combat",
        "Description": "Win a recorded Itikar combat.",
    },
    {
        "Id": "lw5_long_road",
        "Name": "Across Vassagonia",
        "BookNumber": 5,
        "Category": "Exploration",
        "Description": "Visit 100 or more unique Book 5 sections.",
    },
]

LONE_WOLF_ACHIEVEMENTS = (
    LONE_WOLF_BOOK1_ACHIEVEMENTS
    + LONE_WOLF_BOOK2_ACHIEVEMENTS
    + LONE_WOLF_BOOK3_ACHIEVEMENTS
    + LONE_WOLF_BOOK4_ACHIEVEMENTS
    + LONE_WOLF_BOOK5_ACHIEVEMENTS
)

LW1_STORY_ROUTE = [
    1,
    141,
    56,
    222,
    252,
    70,
    157,
    30,
    261,
    264,
    6,
    200,
    168,
    64,
    16,
    192,
    171,
    303,
    237,
    265,
    142,
    135,
    223,
    75,
    163,
    321,
    273,
    51,
    288,
    129,
    3,
    196,
    332,
    350,
]

LW1_GEAR_LOSS_SECTIONS = {174, 258, 294}
LW2_GREEN_SCEPTRE_SECTIONS = {78, 141, 337}


def default_inventory() -> dict[str, Any]:
    return {
        "Weapons": ["Axe"],
        "BackpackItems": ["Meal"],
        "SpecialItems": ["Map of Sommerlund"],
        "GoldCrowns": 0,
        "HasBackpack": True,
        "HasHerbPouch": False,
        "HerbPouchItems": [],
        "Nobles": 0,
    }


def default_achievements() -> dict[str, Any]:
    return {
        "SchemaVersion": ACHIEVEMENT_SCHEMA_VERSION,
        "Unlocked": [],
        "Recent": [],
    }


def default_automation() -> dict[str, Any]:
    return {
        "Enabled": True,
        "AppliedVisitEffects": [],
        "Journal": [],
        "Flags": {
            "weaponsAvailable": True,
            "backpackAvailable": True,
            "backpackItemsAvailable": True,
            "specialItemsAvailable": True,
            "litTorch": False,
        },
        "Stored": {},
        "LastRoll": None,
        "AppliedRollEffects": [],
        "AppliedHealing": [],
        "AppliedLossChoices": [],
        "AppliedRouteActions": [],
        "AppliedLoot": [],
        "ItemHistory": [],
        "StagedRolls": {},
        "Ending": None,
        "DeathState": {"Active": False},
        "DeathHistory": [],
        "SectionCheckpoints": [],
    }


def default_state() -> dict[str, Any]:
    return {
        "Version": "0.2.0",
        "RuleSet": "Lone Wolf",
        "CurrentSection": 1,
        "SectionHistory": [
            {"BookNumber": 1, "BookTitle": "Flight from the Dark", "Section": 1}
        ],
        "CurrentBookStats": {
            "BookNumber": 1,
            "BookTitle": "Flight from the Dark",
            "StartSection": 1,
            "LastSection": 1,
            "SectionsVisited": 1,
            "VisitedSections": [1],
        },
        "BookHistory": [],
        "Character": {
            "Name": "Lone Wolf",
            "BookNumber": 1,
            "CombatSkillBase": 10,
            "CombatSkillCurrent": 10,
            "EnduranceBase": 20,
            "EnduranceMax": 20,
            "EnduranceCurrent": 20,
            "KaiDisciplines": [],
            "WeaponskillWeapon": "",
            "CreationRolls": {},
            "LesserMagicks": [],
            "HigherMagicks": [],
            "CompletedBooks": [],
            "Notes": [],
        },
        "Inventory": default_inventory(),
        "Combat": {
            "Active": False,
            "EnemyName": "",
            "EnemyCombatSkill": 0,
            "EnemyEnduranceMax": 0,
            "EnemyEnduranceCurrent": 0,
            "Modifier": 0,
            "ActiveWeapon": "",
            "UseStaff": False,
            "ForceUnarmed": False,
            "IgnorePlayerLossIfEnemyLossGreater": False,
            "StaffWillpower": 0,
            "EnemyImmune": False,
            "CanEvade": False,
            "EvadeAfterRounds": 0,
            "VictoryRoute": None,
            "DefeatRoute": None,
            "DefeatEnduranceMinimum": None,
            "EvadeRoute": None,
            "FlawlessVictoryRoute": None,
            "WoundedVictoryRoute": None,
            "RoundLimit": 0,
            "SurvivalRoute": None,
            "RoundExceededRoute": None,
            "PlayerLossRoute": None,
            "OneRoundComparisonRoutes": {},
            "PlayerLossRandomCheck": {},
            "OxygenSafeRounds": 0,
            "WinWithinRounds": 0,
            "WinWithinRoute": None,
            "TooLateRoute": None,
            "PostRoundWpThreshold": None,
            "PerRoundActions": [],
            "TimedModifiers": [],
            "AppliedConditionalModifierLabels": [],
            "IgnorePlayerLossRounds": 0,
            "IgnoreEnemyLossRounds": 0,
            "CombatRollRoutes": {},
            "FixedPlayerCombatSkill": None,
            "RequiredWeapon": "",
            "EnemyQueue": [],
            "EnemyIndex": 0,
            "SectionCombatId": "",
            "VictoryChoices": [],
            "AfterVictoryActions": [],
            "DoubleEnemyLoss": False,
            "DoubleEnemyLossWithSommerswerd": False,
            "RestorePlayerEnduranceAfterCombat": False,
            "RestoreHalfPlayerEnduranceLossAfterCombat": False,
            "StoredPlayerEnduranceBeforeCombat": None,
            "Outcome": "",
            "StartedSection": 1,
            "Log": [],
        },
        "CombatHistory": [],
        "Achievements": default_achievements(),
        "Settings": {
            "SavePath": "",
            "AutoSave": True,
            "PreferredCombatWeapon": "",
        },
        "Automation": default_automation(),
    }


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def json_clone(value: Any) -> Any:
    return json.loads(json.dumps(value))


def migrate_legacy_branding(value: Any) -> Any:
    if not isinstance(value, str):
        return value
    compact_old_names = ("Gary" + "Star", "Gray" + "Star")
    spaced_old_names = ("Gary" + " Star", "Gray" + " Star")
    for name in compact_old_names:
        value = value.replace(name, "LoneWolfRedux")
    for name in spaced_old_names:
        value = value.replace(name, "Lone Wolf")
    return (
        value.replace("Lone Wolf the Wizard", "Flight from the Dark")
    )


def normalize_state(state: dict[str, Any]) -> dict[str, Any]:
    base = default_state()

    for key, value in base.items():
        state.setdefault(key, value)

    for section in ("Character", "Inventory", "Combat", "Settings", "Automation", "Achievements"):
        if not isinstance(state.get(section), dict):
            state[section] = base[section]
    if not isinstance(state.get("CurrentBookStats"), dict):
        state["CurrentBookStats"] = base["CurrentBookStats"]
    state["BookHistory"] = as_list(state.get("BookHistory"))

    for key, value in base["Character"].items():
        state["Character"].setdefault(key, value)
    state["RuleSet"] = migrate_legacy_branding(state.get("RuleSet")) or base["RuleSet"]
    state["Character"]["Name"] = migrate_legacy_branding(state["Character"].get("Name")) or base["Character"]["Name"]
    state["Character"]["KaiDisciplines"] = [
        item
        for item in as_list(state["Character"].get("KaiDisciplines"))
        if item in KAI_DISCIPLINES
    ]
    if state["Character"].get("WeaponskillWeapon") not in set(WEAPONSKILL_MAP.values()):
        state["Character"]["WeaponskillWeapon"] = ""
    for key, value in base["Inventory"].items():
        state["Inventory"].setdefault(key, value)
    legacy_nobles = int(state["Inventory"].get("Nobles") or 0)
    if not int(state["Inventory"].get("GoldCrowns") or 0) and legacy_nobles:
        state["Inventory"]["GoldCrowns"] = legacy_nobles
    state["Inventory"]["GoldCrowns"] = max(0, min(50, int(state["Inventory"].get("GoldCrowns") or 0)))
    state["Inventory"]["Nobles"] = int(state["Inventory"]["GoldCrowns"])
    state["Inventory"]["HasBackpack"] = bool(state["Inventory"].get("HasBackpack", True))
    for key, value in base["Combat"].items():
        state["Combat"].setdefault(key, value)
    for key, value in base["Settings"].items():
        state["Settings"].setdefault(key, value)
    state["Settings"]["AutoSave"] = True
    for key, value in base["Achievements"].items():
        state["Achievements"].setdefault(key, value)
    state["Achievements"]["SchemaVersion"] = ACHIEVEMENT_SCHEMA_VERSION
    for key, value in base["Automation"].items():
        state["Automation"].setdefault(key, value)
    if not isinstance(state["Automation"].get("Flags"), dict):
        state["Automation"]["Flags"] = dict(base["Automation"]["Flags"])
    if not isinstance(state["Automation"].get("Stored"), dict):
        state["Automation"]["Stored"] = {}
    if not isinstance(state["Automation"].get("StagedRolls"), dict):
        state["Automation"]["StagedRolls"] = {}
    if state["Automation"].get("LastRoll") is not None and not isinstance(state["Automation"].get("LastRoll"), dict):
        state["Automation"]["LastRoll"] = None
    if not isinstance(state["Automation"].get("DeathState"), dict):
        state["Automation"]["DeathState"] = {"Active": False}
    state["Automation"]["DeathState"].setdefault("Active", False)
    for key, value in base["Automation"]["Flags"].items():
        state["Automation"]["Flags"].setdefault(key, value)

    for path in [
        ("Character", "LesserMagicks"),
        ("Character", "HigherMagicks"),
        ("Character", "KaiDisciplines"),
        ("Character", "CompletedBooks"),
        ("Character", "Notes"),
        ("Inventory", "Weapons"),
        ("Inventory", "BackpackItems"),
        ("Inventory", "SpecialItems"),
        ("Inventory", "HerbPouchItems"),
        ("Combat", "Log"),
        ("Combat", "PerRoundActions"),
        ("Combat", "TimedModifiers"),
        ("Combat", "AppliedConditionalModifierLabels"),
        ("Combat", "EnemyQueue"),
        ("Combat", "VictoryChoices"),
        ("Combat", "AfterVictoryActions"),
        ("CurrentBookStats", "VisitedSections"),
        ("Achievements", "Unlocked"),
        ("Achievements", "Recent"),
        ("Automation", "AppliedVisitEffects"),
        ("Automation", "AppliedRollEffects"),
        ("Automation", "AppliedHealing"),
        ("Automation", "AppliedLossChoices"),
        ("Automation", "AppliedRouteActions"),
        ("Automation", "AppliedLoot"),
        ("Automation", "ItemHistory"),
        ("Automation", "Journal"),
        ("Automation", "DeathHistory"),
        ("Automation", "SectionCheckpoints"),
    ]:
        state[path[0]][path[1]] = as_list(state[path[0]].get(path[1]))

    state["CombatHistory"] = as_list(state.get("CombatHistory"))
    for round_entry in as_list(state["Combat"].get("Log")):
        if isinstance(round_entry, dict) and "LoneWolfReduxLoss" not in round_entry:
            for legacy_key in LEGACY_PLAYER_LOSS_KEYS:
                if legacy_key in round_entry:
                    round_entry["LoneWolfReduxLoss"] = round_entry[legacy_key]
                    break
    for combat_entry in state["CombatHistory"]:
        if not isinstance(combat_entry, dict):
            continue
        for round_entry in as_list(combat_entry.get("Log")):
            if isinstance(round_entry, dict) and "LoneWolfReduxLoss" not in round_entry:
                for legacy_key in LEGACY_PLAYER_LOSS_KEYS:
                    if legacy_key in round_entry:
                        round_entry["LoneWolfReduxLoss"] = round_entry[legacy_key]
                        break

    flags = state["Automation"]["Flags"]
    stored = state["Automation"]["Stored"]
    if "staffAvailable" in flags and "weaponsAvailable" not in flags:
        flags["weaponsAvailable"] = bool(flags.get("staffAvailable", True))
    staff_unavailable = not bool(flags.get("weaponsAvailable", True))
    backpack_unavailable = (
        not bool(flags.get("backpackAvailable", True))
        or not bool(flags.get("backpackItemsAvailable", True))
    )
    special_unavailable = not bool(flags.get("specialItemsAvailable", True))
    if staff_unavailable or backpack_unavailable or special_unavailable:
        equipment = stored.get("confiscatedEquipment")
        if not isinstance(equipment, dict):
            equipment = {}

        active_weapons = as_list(state["Inventory"].get("Weapons"))
        active_backpack = as_list(state["Inventory"].get("BackpackItems"))
        active_special = as_list(state["Inventory"].get("SpecialItems"))
        stored_weapons = as_list(equipment.get("Weapons"))
        stored_backpack = as_list(equipment.get("BackpackItems"))
        stored_special = as_list(equipment.get("SpecialItems"))

        if staff_unavailable:
            for item in active_weapons:
                if item not in stored_weapons:
                    stored_weapons.append(item)
            state["Inventory"]["Weapons"] = []
        if backpack_unavailable:
            legacy_backpack = as_list(stored.get("confiscatedBackpackItems"))
            if not stored_backpack:
                stored_backpack = legacy_backpack or active_backpack
            state["Inventory"]["BackpackItems"] = []
        if special_unavailable:
            for item in active_special:
                if item not in stored_special:
                    stored_special.append(item)
            state["Inventory"]["SpecialItems"] = []

        if stored_weapons or stored_backpack or stored_special:
            equipment["Weapons"] = stored_weapons
            equipment["BackpackItems"] = stored_backpack
            equipment["SpecialItems"] = stored_special
            stored["confiscatedEquipment"] = equipment
            stored["confiscatedBackpackItems"] = stored_backpack

    state["SectionHistory"] = as_list(state.get("SectionHistory"))
    for entry in state["SectionHistory"]:
        if isinstance(entry, dict):
            entry["BookTitle"] = migrate_legacy_branding(entry.get("BookTitle"))
    if not state["SectionHistory"]:
        book_number = int(state["Character"].get("BookNumber", 1))
        book = BOOKS.get(book_number, BOOKS[1])
        state["SectionHistory"] = [
            {
                "BookNumber": book_number,
                "BookTitle": book["Title"],
                "Section": int(state.get("CurrentSection", 1)),
            }
        ]

    stats = state["CurrentBookStats"]
    book_number = int(state["Character"].get("BookNumber", 1))
    book = BOOKS.get(book_number, BOOKS[1])
    stats.setdefault("BookNumber", book_number)
    stats.setdefault("BookTitle", book["Title"])
    stats["BookTitle"] = migrate_legacy_branding(stats.get("BookTitle")) or book["Title"]
    if "CharacterName" in stats:
        stats["CharacterName"] = migrate_legacy_branding(stats.get("CharacterName"))
    for summary in state["BookHistory"]:
        if isinstance(summary, dict):
            summary["BookTitle"] = migrate_legacy_branding(summary.get("BookTitle"))
            summary["CharacterName"] = migrate_legacy_branding(summary.get("CharacterName"))
    stats.setdefault("StartSection", int(state.get("CurrentSection", 1)))
    stats.setdefault("LastSection", int(state.get("CurrentSection", 1)))
    stats.setdefault("SectionsVisited", len(as_list(stats.get("VisitedSections"))))
    stats.setdefault("StartingEnduranceMax", int(state["Character"].get("EnduranceMax") or 0))
    stats.setdefault("StartingGoldCrowns", int(state["Inventory"].get("GoldCrowns") or 0))

    return state


def random_digit() -> int:
    return random.randint(0, 9)


def coerce_random_digit(value: Any | None = None) -> int:
    if value is None or str(value).strip() == "":
        return random_digit()
    return max(0, min(9, int(value)))


def clean_kai_disciplines(values: Any) -> list[str]:
    selected: list[str] = []
    for item in as_list(values):
        name = str(item or "").strip()
        exact = [discipline for discipline in KAI_DISCIPLINES if discipline.lower() == name.lower()]
        if exact and exact[0] not in selected:
            selected.append(exact[0])
    return selected


def weaponskill_weapon_for_roll(roll: int) -> str:
    return WEAPONSKILL_MAP[coerce_random_digit(roll)]


def book1_starting_find_for_roll(roll: int) -> dict[str, Any]:
    return dict(BOOK1_STARTING_FIND[coerce_random_digit(roll)])


def normalized_choice_key(value: Any) -> str:
    text = str(value or "").strip().lower()
    text = text.replace("&", "and")
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-")


def clean_book2_armoury_choices(values: Any) -> list[str]:
    selected: list[str] = []
    label_map = {
        normalized_choice_key(option.get("Label")): key
        for key, option in BOOK2_ARMOURY_OPTIONS.items()
    }
    for raw in as_list(values):
        key = normalized_choice_key(raw)
        key = label_map.get(key, key)
        if key in BOOK2_ARMOURY_OPTIONS and key not in selected:
            selected.append(key)
    if len(selected) != 2:
        raise ValueError("Book 2 armoury setup requires exactly two different choices.")
    return selected


def clean_book3_equipment_choices(values: Any) -> list[str]:
    selected: list[str] = []
    label_map = {
        normalized_choice_key(option.get("Label")): key
        for key, option in BOOK3_EQUIPMENT_OPTIONS.items()
    }
    for raw in as_list(values):
        key = normalized_choice_key(raw)
        key = label_map.get(key, key)
        if key in BOOK3_EQUIPMENT_OPTIONS and key not in selected:
            selected.append(key)
    if len(selected) != 2:
        raise ValueError("Book 3 equipment setup requires exactly two different choices.")
    return selected


def clean_book4_equipment_choices(values: Any) -> list[str]:
    selected: list[str] = []
    label_map = {
        normalized_choice_key(option.get("Label")): key
        for key, option in BOOK4_EQUIPMENT_OPTIONS.items()
    }
    for raw in as_list(values):
        key = normalized_choice_key(raw)
        key = label_map.get(key, key)
        if key in BOOK4_EQUIPMENT_OPTIONS and key not in selected:
            selected.append(key)
    if len(selected) != 6:
        raise ValueError("Book 4 equipment setup requires exactly six different choices.")
    return selected


def clean_book5_equipment_choices(values: Any) -> list[str]:
    selected: list[str] = []
    label_map = {
        normalized_choice_key(option.get("Label")): key
        for key, option in BOOK5_EQUIPMENT_OPTIONS.items()
    }
    for raw in as_list(values):
        key = normalized_choice_key(raw)
        key = label_map.get(key, key)
        if key in BOOK5_EQUIPMENT_OPTIONS and key not in selected:
            selected.append(key)
    if len(selected) > 4:
        raise ValueError("Book 5 equipment setup allows up to four different choices.")
    return selected


def book2_armoury_labels(choice_ids: Any) -> list[str]:
    labels: list[str] = []
    for choice_id in as_list(choice_ids):
        option = BOOK2_ARMOURY_OPTIONS.get(str(choice_id))
        if option:
            labels.append(str(option["Label"]))
    return labels


def book3_equipment_labels(choice_ids: Any) -> list[str]:
    labels: list[str] = []
    for choice_id in as_list(choice_ids):
        option = BOOK3_EQUIPMENT_OPTIONS.get(str(choice_id))
        if option:
            labels.append(str(option["Label"]))
    return labels


def book4_equipment_labels(choice_ids: Any) -> list[str]:
    labels: list[str] = []
    for choice_id in as_list(choice_ids):
        option = BOOK4_EQUIPMENT_OPTIONS.get(str(choice_id))
        if option:
            labels.append(str(option["Label"]))
    return labels


def book5_equipment_labels(choice_ids: Any) -> list[str]:
    labels: list[str] = []
    for choice_id in as_list(choice_ids):
        option = BOOK5_EQUIPMENT_OPTIONS.get(str(choice_id))
        if option:
            labels.append(str(option["Label"]))
    return labels


def add_unique_item(items: Any, item: str) -> list[Any]:
    current = as_list(items)
    if item not in current:
        current.append(item)
    return current


def kai_rank_for_disciplines(disciplines: Any) -> tuple[int, str]:
    count = len(clean_kai_disciplines(disciplines))
    for threshold, name in KAI_RANKS:
        if count >= threshold:
            return count, name
    return count, "Novice"


def kai_rank_meets(disciplines: Any, rank_name: str) -> bool:
    requested = str(rank_name or "").strip().lower()
    thresholds = {name.lower(): threshold for threshold, name in KAI_RANKS}
    required = thresholds.get(requested)
    if required is None:
        try:
            required = int(requested)
        except ValueError:
            return False
    return len(clean_kai_disciplines(disciplines)) >= required


def apply_book2_gold_roll(inventory: dict[str, Any], gold_roll: Any | None) -> tuple[int, int, int, int]:
    roll = coerce_random_digit(gold_roll)
    before = int(inventory.get("GoldCrowns") or 0)
    gain = 10 + roll
    after = min(50, before + gain)
    inventory["GoldCrowns"] = after
    inventory["Nobles"] = after
    return roll, before, gain, after


def apply_book3_gold_roll(inventory: dict[str, Any], gold_roll: Any | None) -> tuple[int, int, int, int]:
    roll = coerce_random_digit(gold_roll)
    before = int(inventory.get("GoldCrowns") or 0)
    gain = 10 + roll
    after = min(50, before + gain)
    inventory["GoldCrowns"] = after
    inventory["Nobles"] = after
    return roll, before, gain, after


def apply_book4_gold_roll(inventory: dict[str, Any], gold_roll: Any | None) -> tuple[int, int, int, int]:
    roll = coerce_random_digit(gold_roll)
    before = int(inventory.get("GoldCrowns") or 0)
    gain = 10 + roll
    after = min(50, before + gain)
    inventory["GoldCrowns"] = after
    inventory["Nobles"] = after
    return roll, before, gain, after


def apply_book5_gold_roll(inventory: dict[str, Any], gold_roll: Any | None) -> tuple[int, int, int, int]:
    roll = coerce_random_digit(gold_roll)
    before = int(inventory.get("GoldCrowns") or 0)
    gain = 10 + roll
    after = min(50, before + gain)
    inventory["GoldCrowns"] = after
    inventory["Nobles"] = after
    return roll, before, gain, after


def apply_book2_armoury_to_state(
    state: dict[str, Any],
    choices: Any,
    weapon_exchanges: Any = None,
) -> list[str]:
    choice_ids = clean_book2_armoury_choices(choices)
    exchanges = [str(item).strip() for item in as_list(weapon_exchanges) if str(item).strip()]
    exchange_index = 0
    messages: list[str] = []
    inventory = state["Inventory"]
    character = state["Character"]

    for choice_id in choice_ids:
        option = BOOK2_ARMOURY_OPTIONS[choice_id]
        label = str(option["Label"])
        option_added_special = False
        messages.append(f"Armoury choice: {label}")

        for container, item in as_list(option.get("Items")):
            if container == "weapon":
                weapons = as_list(inventory.get("Weapons"))
                if len(weapons) >= 2:
                    exchanged = ""
                    while exchange_index < len(exchanges):
                        candidate = exchanges[exchange_index]
                        exchange_index += 1
                        removed, weapons = remove_first_matching(weapons, candidate)
                        if removed:
                            exchanged = candidate
                            break
                    if not exchanged and len(weapons) >= 2:
                        raise ValueError(
                            f"Taking {item} needs a Weapon exchange because the Weapon limit is 2."
                        )
                    if exchanged:
                        messages.append(f"Exchanged Weapon: {exchanged} -> {item}")
                weapons.append(item)
                inventory["Weapons"] = weapons
                continue

            if container == "backpack":
                backpack_items = as_list(inventory.get("BackpackItems"))
                if len(backpack_items) >= 8:
                    raise ValueError(
                        f"Taking {item} needs Backpack space because the Backpack limit is 8."
                    )
                backpack_items.append(item)
                inventory["BackpackItems"] = backpack_items
                inventory["HasBackpack"] = True
                state["Automation"]["Flags"]["backpackAvailable"] = True
                state["Automation"]["Flags"]["backpackItemsAvailable"] = True
                continue

            if container == "special":
                before = as_list(inventory.get("SpecialItems"))
                option_added_special = item not in before
                inventory["SpecialItems"] = add_unique_item(before, item)

        endurance_bonus = int(option.get("EnduranceBonus") or 0)
        if endurance_bonus:
            if option_added_special and not bool(
                character.setdefault("Book2Setup", {}).get("ChainmailApplied")
            ):
                character["EnduranceMax"] = int(character["EnduranceMax"]) + endurance_bonus
                character["EnduranceCurrent"] = int(character["EnduranceCurrent"]) + endurance_bonus
                character["Book2Setup"]["ChainmailApplied"] = True
                messages.append(f"Chainmail Waistcoat: END +{endurance_bonus}")
            else:
                messages.append("Chainmail Waistcoat already recorded; no extra END bonus.")

    return messages


def apply_book3_equipment_to_state(
    state: dict[str, Any],
    choices: Any,
    weapon_exchanges: Any = None,
) -> list[str]:
    choice_ids = clean_book3_equipment_choices(choices)
    exchanges = [str(item).strip() for item in as_list(weapon_exchanges) if str(item).strip()]
    exchange_index = 0
    messages: list[str] = []
    inventory = state["Inventory"]
    character = state["Character"]

    for choice_id in choice_ids:
        option = BOOK3_EQUIPMENT_OPTIONS[choice_id]
        label = str(option["Label"])
        option_added_special = False
        messages.append(f"Equipment choice: {label}")

        for container, item in as_list(option.get("Items")):
            if container == "weapon":
                weapons = as_list(inventory.get("Weapons"))
                if len(weapons) >= 2:
                    exchanged = ""
                    while exchange_index < len(exchanges):
                        candidate = exchanges[exchange_index]
                        exchange_index += 1
                        removed, weapons = remove_first_matching(weapons, candidate)
                        if removed:
                            exchanged = candidate
                            break
                    if not exchanged and len(weapons) >= 2:
                        raise ValueError(
                            f"Taking {item} needs a Weapon exchange because the Weapon limit is 2."
                        )
                    if exchanged:
                        messages.append(f"Exchanged Weapon: {exchanged} -> {item}")
                weapons.append(item)
                inventory["Weapons"] = weapons
                continue

            if container == "backpack":
                backpack_items = as_list(inventory.get("BackpackItems"))
                if len(backpack_items) >= 8:
                    raise ValueError(
                        f"Taking {item} needs Backpack space because the Backpack limit is 8."
                    )
                backpack_items.append(item)
                inventory["BackpackItems"] = backpack_items
                inventory["HasBackpack"] = True
                state["Automation"]["Flags"]["backpackAvailable"] = True
                state["Automation"]["Flags"]["backpackItemsAvailable"] = True
                continue

            if container == "special":
                before = as_list(inventory.get("SpecialItems"))
                option_added_special = item not in before
                inventory["SpecialItems"] = add_unique_item(before, item)

        endurance_bonus = int(option.get("EnduranceBonus") or 0)
        setup = character.setdefault("Book3Setup", {})
        applied_key = f"{choice_id}Applied"
        if endurance_bonus:
            if option_added_special and not bool(setup.get(applied_key)):
                character["EnduranceMax"] = int(character["EnduranceMax"]) + endurance_bonus
                character["EnduranceCurrent"] = int(character["EnduranceCurrent"]) + endurance_bonus
                setup[applied_key] = True
                messages.append(f"{label}: END +{endurance_bonus}")
            else:
                messages.append(f"{label} already recorded; no extra END bonus.")

    return messages


def apply_book4_equipment_to_state(
    state: dict[str, Any],
    choices: Any,
    weapon_exchanges: Any = None,
) -> list[str]:
    choice_ids = clean_book4_equipment_choices(choices)
    exchanges = [str(item).strip() for item in as_list(weapon_exchanges) if str(item).strip()]
    exchange_index = 0
    messages: list[str] = []
    inventory = state["Inventory"]
    character = state["Character"]

    for choice_id in choice_ids:
        option = BOOK4_EQUIPMENT_OPTIONS[choice_id]
        label = str(option["Label"])
        option_added_special = False
        messages.append(f"Equipment choice: {label}")

        for container, item in as_list(option.get("Items")):
            if container == "weapon":
                weapons = as_list(inventory.get("Weapons"))
                if len(weapons) >= 2:
                    exchanged = ""
                    while exchange_index < len(exchanges):
                        candidate = exchanges[exchange_index]
                        exchange_index += 1
                        removed, weapons = remove_first_matching(weapons, candidate)
                        if removed:
                            exchanged = candidate
                            break
                    if not exchanged and len(weapons) >= 2:
                        raise ValueError(
                            f"Taking {item} needs a Weapon exchange because the Weapon limit is 2."
                        )
                    if exchanged:
                        messages.append(f"Exchanged Weapon: {exchanged} -> {item}")
                weapons.append(item)
                inventory["Weapons"] = weapons
                continue

            if container == "backpack":
                backpack_items = as_list(inventory.get("BackpackItems"))
                if len(backpack_items) >= 8:
                    raise ValueError(
                        f"Taking {item} needs Backpack space because the Backpack limit is 8."
                    )
                backpack_items.append(item)
                inventory["BackpackItems"] = backpack_items
                inventory["HasBackpack"] = True
                state["Automation"]["Flags"]["backpackAvailable"] = True
                state["Automation"]["Flags"]["backpackItemsAvailable"] = True
                continue

            if container == "special":
                before = as_list(inventory.get("SpecialItems"))
                option_added_special = item not in before
                inventory["SpecialItems"] = add_unique_item(before, item)

        endurance_bonus = int(option.get("EnduranceBonus") or 0)
        setup = character.setdefault("Book4Setup", {})
        applied_key = f"{choice_id}Applied"
        if endurance_bonus:
            if option_added_special and not bool(setup.get(applied_key)):
                character["EnduranceMax"] = int(character["EnduranceMax"]) + endurance_bonus
                character["EnduranceCurrent"] = int(character["EnduranceCurrent"]) + endurance_bonus
                setup[applied_key] = True
                messages.append(f"{label}: END +{endurance_bonus}")
            else:
                messages.append(f"{label} already recorded; no extra END bonus.")

    return messages


def apply_book5_equipment_to_state(
    state: dict[str, Any],
    choices: Any,
    weapon_exchanges: Any = None,
) -> list[str]:
    choice_ids = clean_book5_equipment_choices(choices)
    exchanges = [str(item).strip() for item in as_list(weapon_exchanges) if str(item).strip()]
    exchange_index = 0
    messages: list[str] = []
    inventory = state["Inventory"]

    for choice_id in choice_ids:
        option = BOOK5_EQUIPMENT_OPTIONS[choice_id]
        label = str(option["Label"])
        messages.append(f"Equipment choice: {label}")

        for container, item in as_list(option.get("Items")):
            if container == "weapon":
                weapons = as_list(inventory.get("Weapons"))
                if len(weapons) >= 2:
                    exchanged = ""
                    while exchange_index < len(exchanges):
                        candidate = exchanges[exchange_index]
                        exchange_index += 1
                        removed, weapons = remove_first_matching(weapons, candidate)
                        if removed:
                            exchanged = candidate
                            break
                    if not exchanged and len(weapons) >= 2:
                        raise ValueError(
                            f"Taking {item} needs a Weapon exchange because the Weapon limit is 2."
                        )
                    if exchanged:
                        messages.append(f"Exchanged Weapon: {exchanged} -> {item}")
                weapons.append(item)
                inventory["Weapons"] = weapons
                continue

            if container == "backpack":
                backpack_items = as_list(inventory.get("BackpackItems"))
                if len(backpack_items) >= 8:
                    raise ValueError(
                        f"Taking {item} needs Backpack space because the Backpack limit is 8."
                    )
                backpack_items.append(item)
                inventory["BackpackItems"] = backpack_items
                inventory["HasBackpack"] = True
                state["Automation"]["Flags"]["backpackAvailable"] = True
                state["Automation"]["Flags"]["backpackItemsAvailable"] = True
                continue

            if container == "special":
                inventory["SpecialItems"] = add_unique_item(inventory.get("SpecialItems"), item)

    return messages


def ensure_book2_mandatory_items(inventory: dict[str, Any]) -> None:
    inventory["SpecialItems"] = add_unique_item(inventory.get("SpecialItems"), "Map of Sommerlund")
    inventory["SpecialItems"] = add_unique_item(inventory.get("SpecialItems"), "Seal of Hammerdal")


def ensure_book3_mandatory_state(state: dict[str, Any]) -> None:
    inventory = state["Inventory"]
    automation = state["Automation"]
    inventory["SpecialItems"] = add_unique_item(inventory.get("SpecialItems"), "Map of Kalte")
    flags = automation.setdefault("Flags", {})
    flags["book3WinterGear"] = True
    flags["winterBoots"] = True
    flags["winterTunic"] = True
    flags["furLinedCloak"] = True
    flags["mittens"] = True
    flags["kalteHuntingSuppressed"] = True


def ensure_book4_mandatory_state(state: dict[str, Any]) -> None:
    inventory = state["Inventory"]
    automation = state["Automation"]
    inventory["SpecialItems"] = add_unique_item(inventory.get("SpecialItems"), "Map of the Southlands")
    inventory["SpecialItems"] = add_unique_item(inventory.get("SpecialItems"), "Badge of Rank")
    flags = automation.setdefault("Flags", {})
    flags["book4BadgeOfRank"] = True
    flags.setdefault("book4WildlandsHuntingSuppressed", False)


def ensure_book5_mandatory_state(state: dict[str, Any]) -> None:
    inventory = state["Inventory"]
    automation = state["Automation"]
    inventory["SpecialItems"] = add_unique_item(inventory.get("SpecialItems"), "Map of Vassagonia")
    flags = automation.setdefault("Flags", {})
    flags["book5MapOfVassagonia"] = True
    flags.setdefault("book5DesertHuntingSuppressed", False)
    flags.setdefault("book5BloodPoisoningActive", False)
    flags.setdefault("book5SommerswerdLost", False)
    flags["specialItemsAvailable"] = True


def move_special_items_to_safekeeping(
    state: dict[str, Any],
    choices: Any,
    *,
    place: str = "Kai Monastery",
    book_number: int | None = None,
) -> list[str]:
    requested = [str(item).strip() for item in as_list(choices) if str(item).strip()]
    if not requested:
        return []

    inventory = state["Inventory"]
    stored = state["Automation"].setdefault("Stored", {})
    safekeeping = as_list(stored.get("safekeepingSpecialItems"))
    raw_records = stored.get("safekeepingRecords")
    records = [json_clone(item) for item in raw_records if isinstance(item, dict)] if isinstance(raw_records, list) else []
    active = as_list(inventory.get("SpecialItems"))
    place_label = str(place or "Safekeeping").strip() or "Safekeeping"
    messages: list[str] = []

    for requested_item in requested:
        match_index = next(
            (
                index
                for index, item in enumerate(active)
                if str(item).strip().lower() == requested_item.lower()
            ),
            None,
        )
        if match_index is None:
            if requested_item in safekeeping:
                messages.append(f"Safekeeping already held: {requested_item}")
                if not any(
                    str(record.get("Item", "")).strip().lower() == requested_item.lower()
                    for record in records
                ):
                    records.append(
                        {
                            "Item": requested_item,
                            "Place": place_label,
                            "BookNumber": int(book_number or state.get("Character", {}).get("BookNumber") or 0),
                        }
                    )
            else:
                messages.append(f"Safekeeping skipped: {requested_item} was not carried")
            continue
        item = active.pop(match_index)
        if item not in safekeeping:
            safekeeping.append(item)
        if not any(
            str(record.get("Item", "")).strip().lower() == str(item).strip().lower()
            for record in records
        ):
            records.append(
                {
                    "Item": item,
                    "Place": place_label,
                    "BookNumber": int(book_number or state.get("Character", {}).get("BookNumber") or 0),
                }
            )
        messages.append(f"Safekeeping: {item} ({place_label})")

    inventory["SpecialItems"] = active
    stored["safekeepingSpecialItems"] = safekeeping
    stored["safekeepingRecords"] = records
    return messages


def create_book1_character_state(
    *,
    name: str = "Lone Wolf",
    kai_disciplines: Any = None,
    section: int = 1,
    combat_skill_roll: Any | None = None,
    endurance_roll: Any | None = None,
    gold_roll: Any | None = None,
    starting_find_roll: Any | None = None,
    weaponskill_roll: Any | None = None,
) -> dict[str, Any]:
    disciplines = clean_kai_disciplines(kai_disciplines)
    if len(disciplines) != 5:
        raise ValueError("Book 1 requires exactly five Kai Disciplines.")

    cs_roll = coerce_random_digit(combat_skill_roll)
    end_roll = coerce_random_digit(endurance_roll)
    crowns_roll = coerce_random_digit(gold_roll)
    find_roll = coerce_random_digit(starting_find_roll)
    find = book1_starting_find_for_roll(find_roll)

    state = normalize_state(default_state())
    state["RuleSet"] = "Lone Wolf Kai"
    state["CurrentSection"] = max(1, min(BOOKS[1]["MaxSection"], int(section or 1)))

    character = state["Character"]
    character["Name"] = str(name or "Lone Wolf").strip() or "Lone Wolf"
    character["BookNumber"] = 1
    character["CombatSkillBase"] = 10 + cs_roll
    character["CombatSkillCurrent"] = 10 + cs_roll
    character["EnduranceBase"] = 20 + end_roll
    character["EnduranceMax"] = 20 + end_roll
    character["EnduranceCurrent"] = 20 + end_roll
    character["KaiDisciplines"] = disciplines
    character["WeaponskillWeapon"] = ""
    character["LesserMagicks"] = []
    character["HigherMagicks"] = []
    character.pop("WillpowerBase", None)
    character.pop("WillpowerCurrent", None)

    if "Weaponskill" in disciplines:
        ws_roll = coerce_random_digit(weaponskill_roll)
        character["WeaponskillWeapon"] = weaponskill_weapon_for_roll(ws_roll)
    else:
        ws_roll = None

    inventory = state["Inventory"]
    inventory["Weapons"] = ["Axe"]
    inventory["BackpackItems"] = ["Meal"]
    inventory["SpecialItems"] = ["Map of Sommerlund"]
    inventory["GoldCrowns"] = crowns_roll
    inventory["Nobles"] = crowns_roll
    inventory["HasBackpack"] = True
    inventory["HasHerbPouch"] = False
    inventory["HerbPouchItems"] = []

    item_type = str(find.get("Type") or "")
    for _ in range(int(find.get("Quantity") or 0)):
        if item_type == "weapon":
            inventory["Weapons"].append(str(find["Name"]))
        elif item_type == "backpack":
            inventory["BackpackItems"].append(str(find["Name"]))
        elif item_type == "special":
            inventory["SpecialItems"].append(str(find["Name"]))
    if item_type == "gold":
        inventory["GoldCrowns"] = min(50, int(inventory["GoldCrowns"]) + int(find.get("Gold") or 0))
        inventory["Nobles"] = inventory["GoldCrowns"]

    endurance_bonus = int(find.get("EnduranceBonus") or 0)
    if endurance_bonus:
        character["EnduranceMax"] += endurance_bonus
        character["EnduranceCurrent"] += endurance_bonus

    character["CreationRolls"] = {
        "CombatSkill": cs_roll,
        "Endurance": end_roll,
        "GoldCrowns": crowns_roll,
        "StartingFind": find_roll,
        "Weaponskill": ws_roll,
        "StartingFindName": str(find.get("Name") or ""),
    }

    state["SectionHistory"] = []
    state["CurrentBookStats"] = {
        "BookNumber": 1,
        "BookTitle": BOOKS[1]["Title"],
        "StartSection": int(state["CurrentSection"]),
        "LastSection": int(state["CurrentSection"]),
        "SectionsVisited": 0,
        "VisitedSections": [],
        "StartingEnduranceMax": int(character["EnduranceMax"]),
        "StartingGoldCrowns": int(inventory["GoldCrowns"]),
    }
    return normalize_state(state)


def create_book2_character_state(
    *,
    name: str = "Lone Wolf",
    kai_disciplines: Any = None,
    section: int = 1,
    combat_skill_roll: Any | None = None,
    endurance_roll: Any | None = None,
    gold_roll: Any | None = None,
    weaponskill_roll: Any | None = None,
    armoury_choices: Any = None,
    weapon_exchanges: Any = None,
) -> dict[str, Any]:
    disciplines = clean_kai_disciplines(kai_disciplines)
    if len(disciplines) != 5:
        raise ValueError("Standalone Book 2 requires exactly five Kai Disciplines.")

    choice_ids = clean_book2_armoury_choices(armoury_choices)
    cs_roll = coerce_random_digit(combat_skill_roll)
    end_roll = coerce_random_digit(endurance_roll)

    state = normalize_state(default_state())
    state["RuleSet"] = "Lone Wolf Kai"
    state["CurrentSection"] = max(1, min(BOOKS[2]["MaxSection"], int(section or 1)))

    character = state["Character"]
    character["Name"] = str(name or "Lone Wolf").strip() or "Lone Wolf"
    character["BookNumber"] = 2
    character["CombatSkillBase"] = 10 + cs_roll
    character["CombatSkillCurrent"] = 10 + cs_roll
    character["EnduranceBase"] = 20 + end_roll
    character["EnduranceMax"] = 20 + end_roll
    character["EnduranceCurrent"] = 20 + end_roll
    character["KaiDisciplines"] = disciplines
    character["WeaponskillWeapon"] = ""
    character["LesserMagicks"] = []
    character["HigherMagicks"] = []
    character["Book2Setup"] = {"Mode": "standalone", "ArmouryChoices": choice_ids}
    character.pop("WillpowerBase", None)
    character.pop("WillpowerCurrent", None)

    if "Weaponskill" in disciplines:
        ws_roll = coerce_random_digit(weaponskill_roll)
        character["WeaponskillWeapon"] = weaponskill_weapon_for_roll(ws_roll)
    else:
        ws_roll = None

    inventory = state["Inventory"]
    inventory["Weapons"] = []
    inventory["BackpackItems"] = []
    inventory["SpecialItems"] = []
    inventory["GoldCrowns"] = 0
    inventory["Nobles"] = 0
    inventory["HasBackpack"] = True
    inventory["HasHerbPouch"] = False
    inventory["HerbPouchItems"] = []
    ensure_book2_mandatory_items(inventory)

    gold_digit, before_gold, gold_gain, after_gold = apply_book2_gold_roll(inventory, gold_roll)
    setup_messages = apply_book2_armoury_to_state(state, choice_ids, weapon_exchanges)

    character["CreationRolls"] = {
        "CombatSkill": cs_roll,
        "Endurance": end_roll,
        "Weaponskill": ws_roll,
        "Book2Gold": gold_digit,
        "Book2GoldGain": gold_gain,
        "Book2GoldBefore": before_gold,
        "Book2GoldAfter": after_gold,
        "Book2Armoury": choice_ids,
    }
    character["Book2Setup"]["Messages"] = setup_messages

    state["SectionHistory"] = []
    state["CurrentBookStats"] = {
        "BookNumber": 2,
        "BookTitle": BOOKS[2]["Title"],
        "StartSection": int(state["CurrentSection"]),
        "LastSection": int(state["CurrentSection"]),
        "SectionsVisited": 0,
        "VisitedSections": [],
        "StartingEnduranceMax": int(character["EnduranceMax"]),
        "StartingGoldCrowns": int(inventory["GoldCrowns"]),
        "Book2GoldRoll": gold_digit,
        "Book2ArmouryChoices": book2_armoury_labels(choice_ids),
    }
    return normalize_state(state)


def create_book3_character_state(
    *,
    name: str = "Lone Wolf",
    kai_disciplines: Any = None,
    section: int = 1,
    combat_skill_roll: Any | None = None,
    endurance_roll: Any | None = None,
    gold_roll: Any | None = None,
    weaponskill_roll: Any | None = None,
    equipment_choices: Any = None,
    weapon_exchanges: Any = None,
) -> dict[str, Any]:
    disciplines = clean_kai_disciplines(kai_disciplines)
    if len(disciplines) != 5:
        raise ValueError("Standalone Book 3 requires exactly five Kai Disciplines.")

    choice_ids = clean_book3_equipment_choices(equipment_choices)
    cs_roll = coerce_random_digit(combat_skill_roll)
    end_roll = coerce_random_digit(endurance_roll)

    state = normalize_state(default_state())
    state["RuleSet"] = "Lone Wolf Kai"
    state["CurrentSection"] = max(1, min(BOOKS[3]["MaxSection"], int(section or 1)))

    character = state["Character"]
    character["Name"] = str(name or "Lone Wolf").strip() or "Lone Wolf"
    character["BookNumber"] = 3
    character["CombatSkillBase"] = 10 + cs_roll
    character["CombatSkillCurrent"] = 10 + cs_roll
    character["EnduranceBase"] = 20 + end_roll
    character["EnduranceMax"] = 20 + end_roll
    character["EnduranceCurrent"] = 20 + end_roll
    character["KaiDisciplines"] = disciplines
    character["WeaponskillWeapon"] = ""
    character["LesserMagicks"] = []
    character["HigherMagicks"] = []
    character["Book3Setup"] = {"Mode": "standalone", "EquipmentChoices": choice_ids}
    character.pop("WillpowerBase", None)
    character.pop("WillpowerCurrent", None)

    if "Weaponskill" in disciplines:
        ws_roll = coerce_random_digit(weaponskill_roll)
        character["WeaponskillWeapon"] = weaponskill_weapon_for_roll(ws_roll)
    else:
        ws_roll = None

    inventory = state["Inventory"]
    inventory["Weapons"] = []
    inventory["BackpackItems"] = []
    inventory["SpecialItems"] = []
    inventory["GoldCrowns"] = 0
    inventory["Nobles"] = 0
    inventory["HasBackpack"] = True
    inventory["HasHerbPouch"] = False
    inventory["HerbPouchItems"] = []
    ensure_book3_mandatory_state(state)

    gold_digit, before_gold, gold_gain, after_gold = apply_book3_gold_roll(inventory, gold_roll)
    setup_messages = apply_book3_equipment_to_state(state, choice_ids, weapon_exchanges)

    character["CreationRolls"] = {
        "CombatSkill": cs_roll,
        "Endurance": end_roll,
        "Weaponskill": ws_roll,
        "Book3Gold": gold_digit,
        "Book3GoldGain": gold_gain,
        "Book3GoldBefore": before_gold,
        "Book3GoldAfter": after_gold,
        "Book3Equipment": choice_ids,
    }
    character["Book3Setup"]["Messages"] = setup_messages

    state["SectionHistory"] = []
    state["CurrentBookStats"] = {
        "BookNumber": 3,
        "BookTitle": BOOKS[3]["Title"],
        "StartSection": int(state["CurrentSection"]),
        "LastSection": int(state["CurrentSection"]),
        "SectionsVisited": 0,
        "VisitedSections": [],
        "StartingEnduranceMax": int(character["EnduranceMax"]),
        "StartingGoldCrowns": int(inventory["GoldCrowns"]),
        "Book3GoldRoll": gold_digit,
        "Book3EquipmentChoices": book3_equipment_labels(choice_ids),
    }
    return normalize_state(state)


def create_book4_character_state(
    *,
    name: str = "Lone Wolf",
    kai_disciplines: Any = None,
    section: int = 1,
    combat_skill_roll: Any | None = None,
    endurance_roll: Any | None = None,
    gold_roll: Any | None = None,
    weaponskill_roll: Any | None = None,
    equipment_choices: Any = None,
    weapon_exchanges: Any = None,
) -> dict[str, Any]:
    disciplines = clean_kai_disciplines(kai_disciplines)
    if len(disciplines) != 5:
        raise ValueError("Standalone Book 4 requires exactly five Kai Disciplines.")

    choice_ids = clean_book4_equipment_choices(equipment_choices)
    cs_roll = coerce_random_digit(combat_skill_roll)
    end_roll = coerce_random_digit(endurance_roll)

    state = normalize_state(default_state())
    state["RuleSet"] = "Lone Wolf Kai"
    state["CurrentSection"] = max(1, min(BOOKS[4]["MaxSection"], int(section or 1)))

    character = state["Character"]
    character["Name"] = str(name or "Lone Wolf").strip() or "Lone Wolf"
    character["BookNumber"] = 4
    character["CombatSkillBase"] = 10 + cs_roll
    character["CombatSkillCurrent"] = 10 + cs_roll
    character["EnduranceBase"] = 20 + end_roll
    character["EnduranceMax"] = 20 + end_roll
    character["EnduranceCurrent"] = 20 + end_roll
    character["KaiDisciplines"] = disciplines
    character["WeaponskillWeapon"] = ""
    character["LesserMagicks"] = []
    character["HigherMagicks"] = []
    character["Book4Setup"] = {"Mode": "standalone", "EquipmentChoices": choice_ids}
    character.pop("WillpowerBase", None)
    character.pop("WillpowerCurrent", None)

    if "Weaponskill" in disciplines:
        ws_roll = coerce_random_digit(weaponskill_roll)
        character["WeaponskillWeapon"] = weaponskill_weapon_for_roll(ws_roll)
    else:
        ws_roll = None

    inventory = state["Inventory"]
    inventory["Weapons"] = []
    inventory["BackpackItems"] = []
    inventory["SpecialItems"] = []
    inventory["GoldCrowns"] = 0
    inventory["Nobles"] = 0
    inventory["HasBackpack"] = True
    inventory["HasHerbPouch"] = False
    inventory["HerbPouchItems"] = []
    ensure_book4_mandatory_state(state)

    gold_digit, before_gold, gold_gain, after_gold = apply_book4_gold_roll(inventory, gold_roll)
    setup_messages = apply_book4_equipment_to_state(state, choice_ids, weapon_exchanges)

    character["CreationRolls"] = {
        "CombatSkill": cs_roll,
        "Endurance": end_roll,
        "Weaponskill": ws_roll,
        "Book4Gold": gold_digit,
        "Book4GoldGain": gold_gain,
        "Book4GoldBefore": before_gold,
        "Book4GoldAfter": after_gold,
        "Book4Equipment": choice_ids,
    }
    character["Book4Setup"]["Messages"] = setup_messages

    state["SectionHistory"] = []
    state["CurrentBookStats"] = {
        "BookNumber": 4,
        "BookTitle": BOOKS[4]["Title"],
        "StartSection": int(state["CurrentSection"]),
        "LastSection": int(state["CurrentSection"]),
        "SectionsVisited": 0,
        "VisitedSections": [],
        "StartingEnduranceMax": int(character["EnduranceMax"]),
        "StartingGoldCrowns": int(inventory["GoldCrowns"]),
        "Book4GoldRoll": gold_digit,
        "Book4EquipmentChoices": book4_equipment_labels(choice_ids),
    }
    return normalize_state(state)


def create_book5_character_state(
    *,
    name: str = "Lone Wolf",
    kai_disciplines: Any = None,
    section: int = 1,
    combat_skill_roll: Any | None = None,
    endurance_roll: Any | None = None,
    gold_roll: Any | None = None,
    weaponskill_roll: Any | None = None,
    equipment_choices: Any = None,
    weapon_exchanges: Any = None,
    safekeeping_special_items: Any = None,
) -> dict[str, Any]:
    disciplines = clean_kai_disciplines(kai_disciplines)
    if len(disciplines) != 5:
        raise ValueError("Standalone Book 5 requires exactly five Kai Disciplines.")

    choice_ids = clean_book5_equipment_choices(equipment_choices)
    cs_roll = coerce_random_digit(combat_skill_roll)
    end_roll = coerce_random_digit(endurance_roll)

    state = normalize_state(default_state())
    state["RuleSet"] = "Lone Wolf Kai"
    state["CurrentSection"] = max(1, min(BOOKS[5]["MaxSection"], int(section or 1)))

    character = state["Character"]
    character["Name"] = str(name or "Lone Wolf").strip() or "Lone Wolf"
    character["BookNumber"] = 5
    character["CombatSkillBase"] = 10 + cs_roll
    character["CombatSkillCurrent"] = 10 + cs_roll
    character["EnduranceBase"] = 20 + end_roll
    character["EnduranceMax"] = 20 + end_roll
    character["EnduranceCurrent"] = 20 + end_roll
    character["KaiDisciplines"] = disciplines
    character["WeaponskillWeapon"] = ""
    character["LesserMagicks"] = []
    character["HigherMagicks"] = []
    character["Book5Setup"] = {
        "Mode": "standalone",
        "EquipmentChoices": choice_ids,
        "SafekeepingSpecialItems": as_list(safekeeping_special_items),
    }
    character.pop("WillpowerBase", None)
    character.pop("WillpowerCurrent", None)

    if "Weaponskill" in disciplines:
        ws_roll = coerce_random_digit(weaponskill_roll)
        character["WeaponskillWeapon"] = weaponskill_weapon_for_roll(ws_roll)
    else:
        ws_roll = None

    inventory = state["Inventory"]
    inventory["Weapons"] = []
    inventory["BackpackItems"] = []
    inventory["SpecialItems"] = []
    inventory["GoldCrowns"] = 0
    inventory["Nobles"] = 0
    inventory["HasBackpack"] = True
    inventory["HasHerbPouch"] = False
    inventory["HerbPouchItems"] = []
    ensure_book5_mandatory_state(state)

    gold_digit, before_gold, gold_gain, after_gold = apply_book5_gold_roll(inventory, gold_roll)
    setup_messages = apply_book5_equipment_to_state(state, choice_ids, weapon_exchanges)
    setup_messages.extend(
        move_special_items_to_safekeeping(
            state,
            safekeeping_special_items,
            place="Kai Monastery",
            book_number=5,
        )
    )

    character["CreationRolls"] = {
        "CombatSkill": cs_roll,
        "Endurance": end_roll,
        "Weaponskill": ws_roll,
        "Book5Gold": gold_digit,
        "Book5GoldGain": gold_gain,
        "Book5GoldBefore": before_gold,
        "Book5GoldAfter": after_gold,
        "Book5Equipment": choice_ids,
    }
    character["Book5Setup"]["Messages"] = setup_messages
    character["Book5Setup"]["SafekeepingSpecialItems"] = as_list(
        state["Automation"].get("Stored", {}).get("safekeepingSpecialItems")
    )
    character["Book5Setup"]["SafekeepingRecords"] = json_clone(
        state["Automation"].get("Stored", {}).get("safekeepingRecords", [])
    )

    state["SectionHistory"] = []
    state["CurrentBookStats"] = {
        "BookNumber": 5,
        "BookTitle": BOOKS[5]["Title"],
        "StartSection": int(state["CurrentSection"]),
        "LastSection": int(state["CurrentSection"]),
        "SectionsVisited": 0,
        "VisitedSections": [],
        "StartingEnduranceMax": int(character["EnduranceMax"]),
        "StartingGoldCrowns": int(inventory["GoldCrowns"]),
        "Book5GoldRoll": gold_digit,
        "Book5EquipmentChoices": book5_equipment_labels(choice_ids),
        "Book5SafekeepingSpecialItems": as_list(
            state["Automation"].get("Stored", {}).get("safekeepingSpecialItems")
        ),
        "Book5SafekeepingRecords": json_clone(
            state["Automation"].get("Stored", {}).get("safekeepingRecords", [])
        ),
    }
    return normalize_state(state)


def format_list(items: Any) -> str:
    values = [str(item) for item in as_list(items) if str(item).strip()]
    return ", ".join(values) if values else "None"


def item_slot_cost(item: Any) -> int:
    if isinstance(item, dict):
        try:
            return max(1, int(item.get("SlotCost") or item.get("slotCost") or 1))
        except (TypeError, ValueError):
            return 1
    text = str(item or "")
    match = re.search(r"\((\d+)\s+spaces?\)", text, flags=re.IGNORECASE)
    if match:
        return max(1, int(match.group(1)))
    return 1


def item_slot_total(items: Any) -> int:
    return sum(item_slot_cost(item) for item in as_list(items))


def safe_file_name(name: str) -> str:
    return re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", name)


def book_title(book_number: int) -> str:
    return BOOKS.get(int(book_number), BOOKS[1])["Title"]


def terminal_supports_ansi() -> bool:
    global _ANSI_SUPPORT
    if _ANSI_SUPPORT is not None:
        return _ANSI_SUPPORT
    if os.environ.get("NO_COLOR") or os.environ.get("LONEWOLF_REDUX_NO_COLOR"):
        _ANSI_SUPPORT = False
        return _ANSI_SUPPORT
    forced = str(os.environ.get("LONEWOLF_REDUX_COLOR") or "").strip().lower()
    if forced in {"1", "true", "yes", "on"}:
        _ANSI_SUPPORT = True
        return _ANSI_SUPPORT
    if not sys.stdout.isatty():
        _ANSI_SUPPORT = False
        return _ANSI_SUPPORT
    if os.name != "nt":
        _ANSI_SUPPORT = True
        return _ANSI_SUPPORT
    _ANSI_SUPPORT = bool(
        os.environ.get("WT_SESSION")
        or str(os.environ.get("TERM_PROGRAM") or "").lower() == "vscode"
        or os.environ.get("ANSICON")
        or str(os.environ.get("ConEmuANSI") or "").upper() == "ON"
    )
    return _ANSI_SUPPORT


def color_text(text: Any, color: str = "") -> str:
    value = "" if text is None else str(text)
    if not color or not terminal_supports_ansi():
        return value
    code = ANSI_COLORS.get(color)
    if not code:
        return value
    return f"\033[{code}m{value}\033[0m"


def write_line(text: Any = "", color: str = "") -> None:
    print(color_text(text, color))


def write_segments(segments: list[tuple[Any, str]]) -> None:
    if not terminal_supports_ansi():
        print("".join("" if text is None else str(text) for text, _ in segments))
        return
    print("".join(color_text(text, color) for text, color in segments))


def format_signed(value: int) -> str:
    return f"+{value}" if int(value) >= 0 else str(value)


def endurance_color(current: Any, maximum: Any) -> str:
    try:
        current_int = int(current)
        maximum_int = max(1, int(maximum))
    except (TypeError, ValueError):
        return "Gray"
    ratio = current_int / maximum_int
    if current_int <= 0:
        return "Red"
    if ratio <= 0.25:
        return "Red"
    if ratio <= 0.5:
        return "Yellow"
    return "Green"


def clip_text(text: Any, width: int) -> str:
    value = "" if text is None else str(text)
    if width <= 0:
        return ""
    if len(value) <= width:
        return value
    if width <= 3:
        return value[:width]
    return value[: width - 3] + "..."


def panel_header(title: str, width: int = SCREEN_WIDTH, accent: str = "Cyan") -> None:
    usable = max(12, width - 2)
    label = f" {title.upper()} "
    label = clip_text(label, usable)
    left = (usable - len(label)) // 2
    right = usable - len(label) - left
    print("")
    write_line("+" + ("-" * left) + label + ("-" * right) + "+", accent)


def panel_footer(width: int = SCREEN_WIDTH) -> None:
    write_line("+" + ("-" * max(12, width - 2)) + "+", "DarkGray")


def panel_text(text: str, width: int = SCREEN_WIDTH, indent: int = 2, color: str = "Gray") -> None:
    inner = max(12, width - 4)
    available = max(8, inner - indent)
    lines = textwrap.wrap(str(text), width=available) or [""]
    for line in lines:
        content = (" " * indent) + line
        write_segments(
            [
                ("| ", "DarkGray"),
                (clip_text(content, inner).ljust(inner), color),
                (" |", "DarkGray"),
            ]
        )


def panel_row(
    label: str,
    value: Any,
    width: int = SCREEN_WIDTH,
    label_width: int = 18,
    value_color: str = "Gray",
    label_color: str = "DarkYellow",
) -> None:
    inner = max(12, width - 4)
    prefix = f"{label:<{label_width}}: "
    value_width = max(0, inner - len(prefix))
    write_segments(
        [
            ("| ", "DarkGray"),
            (prefix, label_color),
            (clip_text(value, value_width).ljust(value_width), value_color),
            (" |", "DarkGray"),
        ]
    )


def panel_pair_row(
    left_label: str,
    left_value: Any,
    right_label: str,
    right_value: Any,
    width: int = SCREEN_WIDTH,
    label_width: int = 13,
    left_color: str = "Gray",
    right_color: str = "Gray",
    label_color: str = "DarkYellow",
) -> None:
    inner = max(12, width - 4)
    gap = "  "
    half = (inner - len(gap)) // 2
    left_prefix = f"{left_label:<{label_width}}: "
    right_prefix = f"{right_label:<{label_width}}: "
    right_width = inner - len(gap) - half
    left_value_width = max(0, half - len(left_prefix))
    right_value_width = max(0, right_width - len(right_prefix))
    write_segments(
        [
            ("| ", "DarkGray"),
            (left_prefix, label_color),
            (clip_text(left_value, left_value_width).ljust(left_value_width), left_color),
            (gap, "DarkGray"),
            (right_prefix, label_color),
            (clip_text(right_value, right_value_width).ljust(right_value_width), right_color),
            (" |", "DarkGray"),
        ]
    )


def capacity_text(items: Any, maximum: int) -> str:
    return f"{item_slot_total(items)}/{maximum}"


def read_int(prompt: str, default: int, minimum: int | None = None, maximum: int | None = None) -> int:
    while True:
        raw = input(f"{prompt} [{default}]: ").strip()
        if not raw:
            return default
        try:
            value = int(raw)
        except ValueError:
            print("Enter a number.")
            continue
        if minimum is not None and value < minimum:
            print(f"Enter a number >= {minimum}.")
            continue
        if maximum is not None and value > maximum:
            print(f"Enter a number <= {maximum}.")
            continue
        return value


def read_yes_no(prompt: str, default: bool = True) -> bool:
    suffix = "Y/n" if default else "y/N"
    while True:
        raw = input(f"{prompt} ({suffix}): ").strip().lower()
        if not raw:
            return default
        if raw in {"y", "yes"}:
            return True
        if raw in {"n", "no"}:
            return False
        print("Enter y or n.")


def write_info(message: str) -> None:
    write_segments([("[INFO] ", "Cyan"), (message, "Gray")])


def write_warn(message: str) -> None:
    write_segments([("[WARN] ", "Yellow"), (message, "Gray")])


def write_error(message: str) -> None:
    write_segments([("[ERROR] ", "Red"), (message, "Gray")])


def rest_of_line(tokens: list[str], start_index: int) -> str:
    if len(tokens) <= start_index:
        return ""
    return " ".join(tokens[start_index:])


def remove_first_matching(items: Any, name: str) -> tuple[bool, list[Any]]:
    removed = False
    result: list[Any] = []
    for item in as_list(items):
        if not removed and str(item).lower() == name.lower():
            removed = True
            continue
        result.append(item)
    return removed, result


class LoneWolfReduxAssistant:
    def __init__(
        self,
        save_dir: Path = DEFAULT_SAVE_DIR,
        data_dir: Path = DEFAULT_DATA_DIR,
        state_data_dir: Path = DEFAULT_STATE_DATA_DIR,
        books_dir: Path = DEFAULT_BOOKS_DIR,
    ) -> None:
        self.save_dir = save_dir
        # data_dir is read-only application reference data. Runtime state is
        # deliberately separate so a frozen app never writes into Program Files
        # or PyInstaller's temporary extraction directory.
        self.data_dir = data_dir
        self.state_data_dir = state_data_dir
        self.books_dir = books_dir
        self.last_save_file = self.state_data_dir / "last-save.txt"
        self.state = normalize_state(default_state())
        self.crt: dict[str, Any] | None = None
        self.section_automation: dict[str, Any] = {}
        self.section_flows: dict[str, Any] = {}
        self.ensure_dirs()
        self.load_crt()
        self.load_section_automation()
        self.load_section_flows()

    @property
    def character(self) -> dict[str, Any]:
        return self.state["Character"]

    @property
    def inventory(self) -> dict[str, Any]:
        return self.state["Inventory"]

    @property
    def combat(self) -> dict[str, Any]:
        return self.state["Combat"]

    @property
    def settings(self) -> dict[str, Any]:
        return self.state["Settings"]

    @property
    def automation(self) -> dict[str, Any]:
        return self.state["Automation"]

    @property
    def automation_flags(self) -> dict[str, Any]:
        return self.automation["Flags"]

    def ensure_dirs(self) -> None:
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.state_data_dir.mkdir(parents=True, exist_ok=True)
        self.books_dir.mkdir(parents=True, exist_ok=True)
        ERROR_LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    def load_crt(self) -> None:
        crt_path = self.data_dir / "crt.json"
        if not crt_path.exists():
            print(f"Combat Results Table not found at {crt_path}.")
            self.crt = None
            return
        with crt_path.open("r", encoding="utf-8") as handle:
            self.crt = json.load(handle)

    def load_book_data_collection(self, pattern: str, label: str) -> dict[str, Any]:
        combined: dict[str, Any] = {}
        try:
            for path in sorted(self.data_dir.glob(pattern)):
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if not isinstance(data, dict):
                    continue
                for book_number, entries in data.items():
                    if isinstance(entries, dict):
                        combined.setdefault(str(book_number), {}).update(entries)
        except Exception as exc:  # pragma: no cover - defensive logging
            with ERROR_LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(f"{label} load error: {exc}\n")
            return {}
        return combined

    def load_section_automation(self) -> None:
        self.section_automation = self.load_book_data_collection(
            SECTION_AUTOMATION_GLOB, "Section automation"
        )

    def merge_section_flow_data(self, base: dict[str, Any], extra: dict[str, Any]) -> dict[str, Any]:
        merged = json.loads(json.dumps(base))
        for book_number, entries in extra.items():
            if not isinstance(entries, dict):
                continue
            book_entries = merged.setdefault(str(book_number), {})
            for section, value in entries.items():
                if not isinstance(value, dict):
                    continue
                current = book_entries.setdefault(str(section), {})
                if not isinstance(current, dict):
                    current = {}
                    book_entries[str(section)] = current
                for key, extra_value in value.items():
                    if key == "routeChecks" and isinstance(extra_value, list):
                        current[key] = as_list(current.get(key)) + extra_value
                    else:
                        current[key] = extra_value
        return merged

    def load_section_flows(self) -> None:
        section_flows = self.load_book_data_collection(SECTION_FLOW_GLOB, "Section flow")
        route_checks = self.load_book_data_collection(ROUTE_CHECK_GLOB, "Route check")
        self.section_flows = self.merge_section_flow_data(section_flows, route_checks)

    def write_current_position(self) -> None:
        try:
            data = {
                "book": int(self.character["BookNumber"]),
                "section": int(self.state["CurrentSection"]),
            }
            CURRENT_POSITION_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - defensive logging
            with ERROR_LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(f"Current position error: {exc}\n")

    def record_section_visit(self) -> bool:
        book_number = int(self.character["BookNumber"])
        section = int(self.state["CurrentSection"])
        book = BOOKS.get(book_number, BOOKS[1])
        entry = {"BookNumber": book_number, "BookTitle": book["Title"], "Section": section}

        history = as_list(self.state.get("SectionHistory"))
        appended = False
        if not history or int(history[-1].get("BookNumber", 0)) != book_number or int(history[-1].get("Section", 0)) != section:
            history.append(entry)
            appended = True
        self.state["SectionHistory"] = history[-200:]

        stats = self.state.get("CurrentBookStats")
        if not isinstance(stats, dict) or int(stats.get("BookNumber", 0)) != book_number:
            stats = {
                "BookNumber": book_number,
                "BookTitle": book["Title"],
                "StartSection": section,
                "LastSection": section,
                "SectionsVisited": 1,
                "VisitedSections": [section],
                "StartingEnduranceMax": int(self.character["EnduranceMax"]),
                "StartingGoldCrowns": int(self.inventory.get("GoldCrowns") or 0),
            }
        visited = [int(item) for item in as_list(stats.get("VisitedSections")) if str(item).strip()]
        if section not in visited:
            visited.append(section)
        stats["BookNumber"] = book_number
        stats["BookTitle"] = book["Title"]
        stats["LastSection"] = section
        stats["VisitedSections"] = visited
        stats["SectionsVisited"] = len(visited)
        stats.setdefault("StartSection", visited[0] if visited else section)
        stats.setdefault("StartingEnduranceMax", int(self.character["EnduranceMax"]))
        stats.setdefault("StartingGoldCrowns", int(self.inventory.get("GoldCrowns") or 0))
        self.state["CurrentBookStats"] = stats
        return appended

    def combat_entries_for_book(self, book_number: int) -> list[dict[str, Any]]:
        return [
            entry
            for entry in as_list(self.state.get("CombatHistory"))
            if isinstance(entry, dict) and int(entry.get("BookNumber") or 0) == int(book_number)
        ]

    def combat_summary_for_book(self, book_number: int) -> dict[str, Any]:
        entries = self.combat_entries_for_book(book_number)
        outcomes = [str(entry.get("Outcome") or "").lower() for entry in entries]
        rounds_fought = 0
        highest_enemy_cs = 0
        highest_enemy_end = 0
        for entry in entries:
            rounds = int(entry.get("RoundCount") or len(as_list(entry.get("Rounds"))))
            rounds_fought += rounds
            highest_enemy_cs = max(highest_enemy_cs, int(entry.get("EnemyCombatSkill") or 0))
            highest_enemy_end = max(highest_enemy_end, int(entry.get("EnemyEnduranceMax") or 0))
        return {
            "CombatCount": len(entries),
            "Victories": sum(1 for outcome in outcomes if outcome == "victory"),
            "Defeats": sum(1 for outcome in outcomes if outcome == "defeat"),
            "Evades": sum(1 for outcome in outcomes if outcome == "evaded"),
            "Survived": sum(1 for outcome in outcomes if outcome == "survived"),
            "Completed": sum(1 for outcome in outcomes if outcome == "completed"),
            "TimedOut": sum(1 for outcome in outcomes if outcome == "timed out"),
            "RoundsFought": rounds_fought,
            "HighestEnemyCombatSkillFaced": highest_enemy_cs,
            "HighestEnemyEnduranceFaced": highest_enemy_end,
        }

    def combat_player_loss_for_book(self, book_number: int) -> int:
        total = 0
        for entry in self.combat_entries_for_book(book_number):
            for round_entry in as_list(entry.get("Rounds")):
                if isinstance(round_entry, dict):
                    total += int(round_entry.get("PlayerLoss") or round_entry.get("LoneWolfReduxLoss") or 0)
        if self.combat.get("Active") and int(self.character.get("BookNumber") or 0) == int(book_number):
            total += self.combat_player_loss_total()
        return total

    def death_count_for_book(self, book_number: int) -> int:
        return sum(
            1
            for entry in as_list(self.automation.get("DeathHistory"))
            if isinstance(entry, dict) and int(entry.get("BookNumber") or 0) == int(book_number)
        )

    def book_summary(self, book_number: int | None = None) -> dict[str, Any]:
        book_number = int(book_number or self.character["BookNumber"])
        book = BOOKS.get(book_number, BOOKS[1])
        stats = self.state.get("CurrentBookStats", {})
        if not isinstance(stats, dict) or int(stats.get("BookNumber") or 0) != book_number:
            visits = [
                int(item.get("Section"))
                for item in as_list(self.state.get("SectionHistory"))
                if isinstance(item, dict)
                and int(item.get("BookNumber") or 0) == book_number
                and str(item.get("Section") or "").strip()
            ]
            stats = {
                "BookNumber": book_number,
                "BookTitle": book["Title"],
                "StartSection": visits[0] if visits else 1,
                "LastSection": visits[-1] if visits else int(self.state.get("CurrentSection") or 1),
                "VisitedSections": list(dict.fromkeys(visits)),
            }

        visited = [int(item) for item in as_list(stats.get("VisitedSections")) if str(item).strip()]
        combat = self.combat_summary_for_book(book_number)
        if isinstance(self.state.get("CurrentBookStats"), dict) and int(self.state["CurrentBookStats"].get("BookNumber") or 0) == book_number:
            self.state["CurrentBookStats"].update(combat)
            self.state["CurrentBookStats"]["DeathCount"] = self.death_count_for_book(book_number)
        inventory = json_clone(self.inventory)
        summary = {
            "BookNumber": book_number,
            "BookTitle": book["Title"],
            "CharacterName": str(self.character.get("Name") or "Lone Wolf"),
            "CompletedAt": datetime.now().isoformat(timespec="seconds"),
            "StartSection": int(stats.get("StartSection") or (visited[0] if visited else 1)),
            "LastSection": int(stats.get("LastSection") or self.state.get("CurrentSection") or 1),
            "SectionsVisited": int(stats.get("SectionsVisited") or len(visited)),
            "UniqueSectionsVisited": len(visited),
            "VisitedSections": visited,
            "EnduranceCurrent": int(self.character["EnduranceCurrent"]),
            "EnduranceMax": int(self.character["EnduranceMax"]),
            "CombatSkill": int(self.character["CombatSkillCurrent"]),
            "KaiDisciplines": as_list(self.character.get("KaiDisciplines")),
            "WeaponskillWeapon": str(self.character.get("WeaponskillWeapon") or ""),
            "GoldCrowns": int(self.inventory.get("GoldCrowns") or 0),
            "Weapons": as_list(inventory.get("Weapons")),
            "BackpackItems": as_list(inventory.get("BackpackItems")),
            "SpecialItems": as_list(inventory.get("SpecialItems")),
            "NotesCount": len(as_list(self.character.get("Notes"))),
            "DeathCount": self.death_count_for_book(book_number),
        }
        summary.update(combat)
        return summary

    def ensure_book_completed(self, book_number: int | None = None, *, save: bool = False) -> dict[str, Any]:
        book_number = int(book_number or self.character["BookNumber"])
        completed = sorted({int(item) for item in as_list(self.character["CompletedBooks"])} | {book_number})
        self.character["CompletedBooks"] = completed

        history = [entry for entry in as_list(self.state.get("BookHistory")) if isinstance(entry, dict)]
        summary = self.book_summary(book_number)
        replaced = False
        for index, entry in enumerate(history):
            if int(entry.get("BookNumber") or 0) == book_number:
                history[index] = summary
                replaced = True
                break
        if not replaced:
            history.append(summary)
        self.state["BookHistory"] = history
        self.automation["Ending"] = {"BookNumber": book_number, "Section": int(self.state["CurrentSection"]), "Type": "success"}
        if save:
            self.write_current_position()
            self.autosave()
        return summary

    def book_completion_payload(self) -> dict[str, Any]:
        ending = self.automation.get("Ending")
        active = isinstance(ending, dict) and str(ending.get("Type") or "").lower() == "success"
        book_number = int(ending.get("BookNumber") or self.character["BookNumber"]) if active else int(self.character["BookNumber"])
        if not active:
            return {"Active": False}

        summary = None
        for entry in as_list(self.state.get("BookHistory")):
            if isinstance(entry, dict) and int(entry.get("BookNumber") or 0) == book_number:
                summary = json_clone(entry)
                break
        if summary is None:
            summary = self.book_summary(book_number)

        next_book = book_number + 1 if book_number < max(BOOKS) else None
        missing_kai = [item for item in KAI_DISCIPLINES if item not in as_list(self.character.get("KaiDisciplines"))]
        return {
            "Active": True,
            "Summary": summary,
            "NextBookNumber": next_book,
            "NextBookTitle": BOOKS[next_book]["Title"] if next_book else "",
            "CanContinue": next_book is not None,
            "KaiDisciplineChoices": missing_kai,
        }

    def achievement_state(self) -> dict[str, Any]:
        state = self.state.get("Achievements")
        if not isinstance(state, dict):
            state = default_achievements()
            self.state["Achievements"] = state
        state.setdefault("SchemaVersion", ACHIEVEMENT_SCHEMA_VERSION)
        state["SchemaVersion"] = ACHIEVEMENT_SCHEMA_VERSION
        state["Unlocked"] = as_list(state.get("Unlocked"))
        state["Recent"] = as_list(state.get("Recent"))
        return state

    def achievement_definitions(self) -> list[dict[str, Any]]:
        return json_clone(LONE_WOLF_ACHIEVEMENTS)

    def achievement_unlocked_ids(self) -> set[str]:
        unlocked_ids: set[str] = set()
        for entry in as_list(self.achievement_state().get("Unlocked")):
            if isinstance(entry, dict) and str(entry.get("Id") or "").strip():
                unlocked_ids.add(str(entry["Id"]))
        return unlocked_ids

    def summaries_for_book(self, book_number: int) -> list[dict[str, Any]]:
        return [
            entry
            for entry in as_list(self.state.get("BookHistory"))
            if isinstance(entry, dict) and int(entry.get("BookNumber") or 0) == int(book_number)
        ]

    def sections_for_book(self, book_number: int) -> set[int]:
        book_number = int(book_number)
        sections: list[int] = []
        for summary in self.summaries_for_book(book_number):
            sections.extend(
                int(item)
                for item in as_list(summary.get("VisitedSections"))
                if str(item).strip()
            )
        current_stats = self.state.get("CurrentBookStats")
        if isinstance(current_stats, dict) and int(current_stats.get("BookNumber") or 0) == book_number:
            sections.extend(
                int(item)
                for item in as_list(current_stats.get("VisitedSections"))
                if str(item).strip()
            )
        for entry in as_list(self.state.get("SectionHistory")):
            if (
                isinstance(entry, dict)
                and int(entry.get("BookNumber") or 0) == book_number
                and str(entry.get("Section") or "").strip()
            ):
                sections.append(int(entry["Section"]))
        return set(sections)

    def items_seen_for_book(self, book_number: int) -> set[str]:
        book_number = int(book_number)
        items: list[str] = []
        for summary in self.summaries_for_book(book_number):
            for key in ("Weapons", "BackpackItems", "SpecialItems", "HerbPouchItems"):
                items.extend(str(item) for item in as_list(summary.get(key)) if str(item).strip())
        for entry in as_list(self.automation.get("ItemHistory")):
            if not isinstance(entry, dict) or int(entry.get("BookNumber") or 0) != book_number:
                continue
            name = str(entry.get("Name") or "").strip()
            if name:
                items.append(name)
        if int(self.character.get("BookNumber") or 0) == book_number:
            for key in ("Weapons", "BackpackItems", "SpecialItems", "HerbPouchItems"):
                items.extend(str(item) for item in as_list(self.inventory.get(key)) if str(item).strip())
        return {item.lower() for item in items}

    def death_history_has_section(self, book_number: int, section: int) -> bool:
        return any(
            isinstance(entry, dict)
            and int(entry.get("BookNumber") or 0) == int(book_number)
            and int(entry.get("Section") or 0) == int(section)
            for entry in as_list(self.automation.get("DeathHistory"))
        )

    def has_route_transition(self, book_number: int, source: int, target: int) -> bool:
        source = int(source)
        target = int(target)
        for entry in as_list(self.automation.get("Journal")):
            if (
                isinstance(entry, dict)
                and str(entry.get("Kind") or "").lower() == "route"
                and int(entry.get("BookNumber") or 0) == int(book_number)
                and int(entry.get("Section") or 0) == source
                and int(entry.get("TargetSection") or 0) == target
            ):
                return True

        ordered = [
            int(entry.get("Section"))
            for entry in as_list(self.state.get("SectionHistory"))
            if isinstance(entry, dict)
            and int(entry.get("BookNumber") or 0) == int(book_number)
            and str(entry.get("Section") or "").strip()
        ]
        return any(left == source and right == target for left, right in zip(ordered, ordered[1:]))

    def summary_metric_for_book(self, book_number: int, key: str) -> int:
        values: list[int] = []
        for summary in self.summaries_for_book(book_number):
            try:
                values.append(int(summary.get(key) or 0))
            except (TypeError, ValueError):
                continue
        current_stats = self.state.get("CurrentBookStats")
        if isinstance(current_stats, dict) and int(current_stats.get("BookNumber") or 0) == int(book_number):
            try:
                values.append(int(current_stats.get(key) or 0))
            except (TypeError, ValueError):
                pass
        return max(values or [0])

    def book_completed(self, book_number: int) -> bool:
        return int(book_number) in {
            int(item) for item in as_list(self.character.get("CompletedBooks")) if str(item).strip()
        }

    def has_sections(self, book_number: int, *sections: int) -> bool:
        visited = self.sections_for_book(book_number)
        return all(int(section) in visited for section in sections)

    def has_any_section(self, book_number: int, *sections: int) -> bool:
        visited = self.sections_for_book(book_number)
        return any(int(section) in visited for section in sections)

    def achievement_satisfied(self, definition: dict[str, Any]) -> bool:
        achievement_id = str(definition.get("Id") or "")
        book_number = int(definition.get("BookNumber") or self.character.get("BookNumber") or 1)
        sections = self.sections_for_book(book_number)
        summaries = self.summaries_for_book(book_number)
        items = self.items_seen_for_book(book_number)
        victories = [
            entry
            for entry in self.combat_entries_for_book(book_number)
            if str(entry.get("Outcome") or "").lower() == "victory"
        ]
        victory_count = max(len(victories), self.summary_metric_for_book(book_number, "Victories"))
        rounds_fought = max(
            self.combat_summary_for_book(book_number).get("RoundsFought", 0),
            self.summary_metric_for_book(book_number, "RoundsFought"),
        )
        death_count = max(self.death_count_for_book(book_number), self.summary_metric_for_book(book_number, "DeathCount"))

        if achievement_id == "lw1_complete":
            return self.book_completed(1)
        if achievement_id == "lw1_reach_holmgard":
            return 350 in sections or self.book_completed(1)
        if achievement_id == "lw1_clean_story_route":
            return all(section in sections for section in LW1_STORY_ROUTE)
        if achievement_id == "lw1_first_blood":
            return victory_count >= 1
        if achievement_id == "lw1_gourgaz_victory":
            return any(int(entry.get("Section") or 0) == 255 for entry in victories)
        if achievement_id == "lw1_princes_sword":
            return "prince's sword" in items
        if achievement_id == "lw1_vordak_gem_backlash":
            return 236 in sections
        if achievement_id == "lw1_vordak_gem_failure":
            return 292 in sections or self.death_history_has_section(1, 292)
        if achievement_id == "lw1_capture_escape":
            return self.has_sections(1, 162, 258)
        if achievement_id == "lw1_capture_death":
            return 127 in sections or self.death_history_has_section(1, 127)
        if achievement_id == "lw1_paid_ferry":
            return self.has_route_transition(1, 46, 246) or self.has_sections(1, 46, 246)
        if achievement_id == "lw1_caravan_fare":
            return self.has_route_transition(1, 12, 262) or self.has_sections(1, 12, 262)
        if achievement_id == "lw1_backpack_lost":
            return any(section in sections for section in LW1_GEAR_LOSS_SECTIONS)
        if achievement_id == "lw1_marsh_escape":
            return 21 in sections and self.has_any_section(1, 189, 312)
        if achievement_id == "lw1_crystal_star_pendant":
            return "crystal star pendant" in items
        if achievement_id == "lw1_long_road":
            return max(len(sections), self.summary_metric_for_book(1, "UniqueSectionsVisited")) >= 75
        if achievement_id == "lw2_complete":
            return self.book_completed(2)
        if achievement_id == "lw2_reach_hammerdal":
            return self.has_any_section(2, 196, 40, 97, 123, 242) or self.book_completed(2)
        if achievement_id == "lw2_claim_sommerswerd":
            return "sommerswerd" in items
        if achievement_id == "lw2_magic_spear":
            return "magic spear" in items
        if achievement_id == "lw2_helghast_victory":
            return any(
                "helghast" in str(entry.get("EnemyName") or "").lower()
                or int(entry.get("Section") or 0) in {5, 17, 106, 237, 332}
                for entry in victories
            )
        if achievement_id == "lw2_arm_wrestling_win":
            return 305 in sections
        if achievement_id == "lw2_survive_green_sceptre":
            return any(section in sections for section in LW2_GREEN_SCEPTRE_SECTIONS)
        if achievement_id == "lw2_red_pass":
            return "red pass" in items or 202 in sections
        if achievement_id == "lw2_deadly_documents":
            return 126 in sections or self.death_history_has_section(2, 126)
        if achievement_id == "lw2_long_road":
            return max(len(sections), self.summary_metric_for_book(2, "UniqueSectionsVisited")) >= 90
        if achievement_id == "lw3_complete":
            return self.book_completed(3)
        if achievement_id == "lw3_capture_vonotar":
            return 350 in sections or self.book_completed(3)
        if achievement_id == "lw3_mission_failed":
            return 61 in sections or self.death_history_has_section(3, 61)
        if achievement_id == "lw3_firesphere":
            return "firesphere" in items
        if achievement_id == "lw3_silver_helm":
            return "silver helm" in items
        if achievement_id == "lw3_baknar_oil":
            return "baknar oil" in items
        if achievement_id == "lw3_crystal_frostwyrm":
            return any(
                "crystal frostwyrm" in str(entry.get("EnemyName") or "").lower()
                or int(entry.get("Section") or 0) == 265
                for entry in victories
            )
        if achievement_id == "lw3_long_road":
            return max(len(sections), self.summary_metric_for_book(3, "UniqueSectionsVisited")) >= 90
        if achievement_id == "lw4_complete":
            return self.book_completed(4)
        if achievement_id == "lw4_dagger_vashna":
            return "dagger of vashna" in items
        if achievement_id == "lw4_onyx_medallion":
            return "onyx medallion" in items
        if achievement_id == "lw4_mine_treasure":
            return 302 in sections and (
                "flask of holy water" in items
                or "potion of alether (+2 cs)" in items
                or "potion of laumspur (+4 end)" in items
            )
        if achievement_id == "lw4_barraka_victory":
            return any(
                "barraka" in str(entry.get("EnemyName") or "").lower()
                or int(entry.get("Section") or 0) in {122, 325}
                for entry in victories
            )
        if achievement_id == "lw4_holy_water":
            return "flask of holy water" in items
        if achievement_id == "lw4_bad_key":
            return "iron key" in items
        if achievement_id == "lw4_long_road":
            return max(len(sections), self.summary_metric_for_book(4, "UniqueSectionsVisited")) >= 90
        if achievement_id == "lw5_complete":
            return self.book_completed(5)
        if achievement_id == "lw5_book_magnakai":
            return "book of the magnakai" in items
        if achievement_id == "lw5_kai_master":
            return self.book_completed(5) and "book of the magnakai" in items
        if achievement_id == "lw5_black_sash":
            return "black sash" in items
        if achievement_id == "lw5_recover_gear":
            return 14 in sections
        if achievement_id == "lw5_jewelled_mace":
            return "jewelled mace" in items
        if achievement_id == "lw5_itikar_rider":
            return any(
                "itikar" in str(entry.get("EnemyName") or "").lower()
                or int(entry.get("Section") or 0) in {240, 370}
                for entry in victories
            )
        if achievement_id == "lw5_long_road":
            return max(len(sections), self.summary_metric_for_book(5, "UniqueSectionsVisited")) >= 100

        return False

    def unlock_achievement(self, definition: dict[str, Any]) -> dict[str, Any]:
        unlocked_at = datetime.now().isoformat(timespec="seconds")
        entry = {
            "Id": definition["Id"],
            "Name": definition["Name"],
            "BookNumber": int(definition.get("BookNumber") or 0),
            "Category": definition.get("Category", ""),
            "UnlockedAt": unlocked_at,
        }
        state = self.achievement_state()
        state["Unlocked"] = as_list(state.get("Unlocked")) + [entry]
        recent = as_list(state.get("Recent")) + [entry]
        state["Recent"] = recent[-10:]
        return entry

    def sync_achievements(self, *, save: bool = False) -> list[dict[str, Any]]:
        state = self.achievement_state()
        state["Unlocked"] = [
            entry
            for entry in as_list(state.get("Unlocked"))
            if isinstance(entry, dict) and str(entry.get("Id") or "").strip()
        ]
        unlocked_ids = self.achievement_unlocked_ids()
        new_unlocks: list[dict[str, Any]] = []
        for definition in self.achievement_definitions():
            achievement_id = str(definition.get("Id") or "")
            if not achievement_id or achievement_id in unlocked_ids:
                continue
            if self.achievement_satisfied(definition):
                new_unlocks.append(self.unlock_achievement(definition))
                unlocked_ids.add(achievement_id)
        if save and new_unlocks:
            self.save_game(quiet=True)
        return new_unlocks

    def achievement_payload(self) -> dict[str, Any]:
        state = self.achievement_state()
        unlocked_by_id = {
            str(entry.get("Id")): entry
            for entry in as_list(state.get("Unlocked"))
            if isinstance(entry, dict) and str(entry.get("Id") or "").strip()
        }
        definitions = []
        by_book: dict[str, dict[str, int]] = {}
        for definition in self.achievement_definitions():
            book_number = int(definition.get("BookNumber") or 0)
            key = str(book_number or "general")
            by_book.setdefault(key, {"BookNumber": book_number, "Total": 0, "Unlocked": 0})
            by_book[key]["Total"] += 1
            entry = unlocked_by_id.get(str(definition.get("Id")))
            definition["Unlocked"] = entry is not None
            definition["UnlockedAt"] = entry.get("UnlockedAt", "") if entry else ""
            if entry:
                by_book[key]["Unlocked"] += 1
            definitions.append(definition)
        return {
            "SchemaVersion": ACHIEVEMENT_SCHEMA_VERSION,
            "UnlockedCount": len(unlocked_by_id),
            "TotalCount": len(definitions),
            "Unlocked": as_list(state.get("Unlocked")),
            "Recent": list(reversed(as_list(state.get("Recent")))),
            "Definitions": definitions,
            "ByBook": by_book,
        }

    def current_visit_key(self) -> str:
        book_number = int(self.character["BookNumber"])
        section = int(self.state["CurrentSection"])
        history_length = len(as_list(self.state.get("SectionHistory")))
        return f"{book_number}:{section}:{history_length}"

    def death_state(self) -> dict[str, Any]:
        state = self.automation.get("DeathState")
        if not isinstance(state, dict):
            state = {"Active": False}
            self.automation["DeathState"] = state
        state.setdefault("Active", False)
        return state

    def death_active(self) -> bool:
        return bool(self.death_state().get("Active"))

    def clear_death_state(self) -> None:
        self.automation["DeathState"] = {"Active": False}

    def clear_terminal_death_marker(self) -> None:
        ending = self.automation.get("Ending")
        if isinstance(ending, dict) and str(ending.get("Type") or "").lower() in {"death", "failure", "combat"}:
            self.automation["Ending"] = None

    def section_checkpoints(self) -> list[dict[str, Any]]:
        return [item for item in as_list(self.automation.get("SectionCheckpoints")) if isinstance(item, dict)]

    def checkpoint_snapshot(self) -> dict[str, Any]:
        snapshot = json_clone(self.state)
        automation = snapshot.setdefault("Automation", {})
        automation["SectionCheckpoints"] = []
        automation["DeathState"] = {"Active": False}
        automation["DeathHistory"] = []
        return snapshot

    def save_section_checkpoint(self, stage: str = "ready") -> None:
        if self.death_active():
            return
        book_number = int(self.character["BookNumber"])
        section = int(self.state["CurrentSection"])
        book = BOOKS.get(book_number, BOOKS[1])
        checkpoint = {
            "Key": self.current_visit_key(),
            "Stage": stage,
            "BookNumber": book_number,
            "BookTitle": book["Title"],
            "Section": section,
            "CapturedAt": datetime.now().isoformat(timespec="seconds"),
            "Snapshot": self.checkpoint_snapshot(),
        }

        checkpoints = self.section_checkpoints()
        if checkpoints and checkpoints[-1].get("Key") == checkpoint["Key"]:
            checkpoints[-1] = checkpoint
        else:
            checkpoints.append(checkpoint)
        self.automation["SectionCheckpoints"] = checkpoints[-100:]

    def ensure_current_section_checkpoint(self) -> None:
        if self.death_active():
            return
        checkpoints = self.section_checkpoints()
        if not checkpoints:
            self.save_section_checkpoint("ready")

    def checkpoint_summary(self, checkpoint: dict[str, Any] | None) -> dict[str, Any] | None:
        if not isinstance(checkpoint, dict):
            return None
        return {
            "BookNumber": checkpoint.get("BookNumber"),
            "BookTitle": checkpoint.get("BookTitle") or book_title(int(checkpoint.get("BookNumber") or 1)),
            "Section": checkpoint.get("Section"),
            "CapturedAt": checkpoint.get("CapturedAt", ""),
            "Stage": checkpoint.get("Stage", ""),
        }

    def death_recovery_payload(self) -> dict[str, Any]:
        death = json_clone(self.death_state())
        checkpoints = self.section_checkpoints()
        repeat = checkpoints[-1] if checkpoints else None
        rewind = checkpoints[-2] if len(checkpoints) >= 2 else None
        repeat_stage = str(repeat.get("Stage") or "ready") if isinstance(repeat, dict) else ""
        death["Active"] = bool(death.get("Active"))
        death["CanRepeat"] = death["Active"] and repeat is not None and repeat_stage != "entry"
        death["CanRewind"] = death["Active"] and rewind is not None
        death["AvailableRewinds"] = max(0, len(checkpoints) - 1)
        death["RepeatTarget"] = self.checkpoint_summary(repeat)
        death["RewindTarget"] = self.checkpoint_summary(rewind)
        return death

    def register_death(self, death_type: str = "death", cause: str = "") -> None:
        if self.death_active():
            return
        kind = str(death_type or "death").lower()
        book_number = int(self.character["BookNumber"])
        section = int(self.state["CurrentSection"])
        book = BOOKS.get(book_number, BOOKS[1])
        if kind in {"death", "instant", "combat", "endurance"}:
            self.character["EnduranceCurrent"] = max(0, int(self.character["EnduranceCurrent"]))
            if kind != "combat":
                self.character["EnduranceCurrent"] = 0

        label = "Failure" if kind == "failure" else ("Combat" if kind == "combat" else "Death")
        if not cause:
            cause = f"Section {section} ended the run."
        entry = {
            "Active": True,
            "Type": label,
            "Cause": cause,
            "BookNumber": book_number,
            "BookTitle": book["Title"],
            "Section": section,
            "RecordedAt": datetime.now().isoformat(timespec="seconds"),
            "CharacterName": str(self.character.get("Name") or "Lone Wolf"),
            "EnduranceCurrent": int(self.character["EnduranceCurrent"]),
            "EnduranceMax": int(self.character["EnduranceMax"]),
            "CombatSkill": int(self.character["CombatSkillCurrent"]),
            "GoldCrowns": int(self.inventory.get("GoldCrowns") or 0),
        }
        recovery = self.death_recovery_payload()
        entry["CanRepeat"] = bool(recovery.get("CanRepeat"))
        entry["CanRewind"] = bool(recovery.get("CanRewind"))
        entry["AvailableRewinds"] = int(recovery.get("AvailableRewinds") or 0)
        self.automation["DeathState"] = entry

        history = as_list(self.automation.get("DeathHistory"))
        history_entry = dict(entry)
        history_entry.pop("Active", None)
        self.automation["DeathHistory"] = (history + [history_entry])[-100:]

    def restore_death_checkpoint(self, mode: str = "repeat") -> None:
        if not self.death_active():
            print("No active death or failed mission to recover from.")
            return

        mode = str(mode or "repeat").lower()
        checkpoints = self.section_checkpoints()
        if not checkpoints:
            print("No recovery checkpoint is available.")
            return

        if mode == "rewind":
            if len(checkpoints) < 2:
                print("No previous section checkpoint is available.")
                return
            target_index = len(checkpoints) - 2
            action_label = "Rewound"
        else:
            target_index = len(checkpoints) - 1
            action_label = "Repeated"

        target = checkpoints[target_index]
        if mode != "rewind" and str(target.get("Stage") or "ready") == "entry":
            print("Repeat is not available for this death; rewind to the previous section instead.")
            return
        snapshot = target.get("Snapshot")
        if isinstance(snapshot, str):
            restored = json.loads(snapshot)
        elif isinstance(snapshot, dict):
            restored = json_clone(snapshot)
        else:
            print("Recovery checkpoint is missing its saved state.")
            return

        save_path = str(self.settings.get("SavePath") or "")
        death_history = json_clone(as_list(self.automation.get("DeathHistory")))
        achievements = json_clone(self.achievement_state())
        remaining = json_clone(checkpoints[: target_index + 1])

        restored = normalize_state(restored)
        restored["Settings"]["SavePath"] = save_path
        restored["Settings"]["AutoSave"] = True
        restored["Achievements"] = achievements
        restored["Automation"]["SectionCheckpoints"] = remaining
        restored["Automation"]["DeathHistory"] = death_history
        restored["Automation"]["DeathState"] = {"Active": False}

        self.state = normalize_state(restored)
        self.write_current_position()
        self.autosave()
        print(f"{action_label} to Book {self.character['BookNumber']}, section {self.state['CurrentSection']}.")

    def section_automation_entry(self, book_number: int, section: int) -> dict[str, Any] | None:
        book_entries = self.section_automation.get(str(book_number), {})
        entry = book_entries.get(str(section))
        return entry if isinstance(entry, dict) else None

    def current_section_automation_entry(self) -> dict[str, Any] | None:
        return self.section_automation_entry(
            int(self.character["BookNumber"]), int(self.state["CurrentSection"])
        )

    def section_flow_entry(self, book_number: int, section: int) -> dict[str, Any] | None:
        book_entries = self.section_flows.get(str(book_number), {})
        entry = book_entries.get(str(section))
        return entry if isinstance(entry, dict) else None

    def current_section_flow_entry(self) -> dict[str, Any] | None:
        return self.section_flow_entry(
            int(self.character["BookNumber"]), int(self.state["CurrentSection"])
        )

    def container_key(self, container: str) -> str | None:
        mapping = {
            "weapon": "Weapons",
            "weapons": "Weapons",
            "backpack": "BackpackItems",
            "backpackitems": "BackpackItems",
            "special": "SpecialItems",
            "specialitems": "SpecialItems",
            "herb": "HerbPouchItems",
            "herbpouch": "HerbPouchItems",
            "herbpouchitems": "HerbPouchItems",
        }
        return mapping.get(str(container).replace("_", "").lower())

    def automation_containers(self, names: Any = None) -> list[str]:
        if not names:
            return ["BackpackItems", "HerbPouchItems", "SpecialItems", "Weapons"]
        result: list[str] = []
        for name in as_list(names):
            key = self.container_key(str(name))
            if key and key not in result:
                result.append(key)
        return result

    def item_matches(self, item: Any, name: str, match_mode: str = "exact") -> bool:
        item_text = str(item).lower()
        name_text = str(name).lower()
        if match_mode == "contains":
            return name_text in item_text
        return item_text == name_text

    def remove_inventory_items(
        self,
        name: str,
        count: int = 1,
        containers: Any = None,
        match_mode: str = "exact",
    ) -> int:
        remaining = max(0, int(count))
        removed_count = 0
        for key in self.automation_containers(containers):
            items = as_list(self.inventory.get(key))
            kept: list[Any] = []
            for item in items:
                if remaining > 0 and self.item_matches(item, name, match_mode):
                    removed_count += 1
                    remaining -= 1
                    continue
                kept.append(item)
            self.inventory[key] = kept
            if remaining <= 0:
                break
        return removed_count

    def record_item_seen(self, name: str, container: str) -> None:
        name = str(name or "").strip()
        if not name:
            return
        entry = {
            "BookNumber": int(self.character["BookNumber"]),
            "Section": int(self.state["CurrentSection"]),
            "Name": name,
            "Container": str(container or ""),
            "RecordedAt": datetime.now().isoformat(timespec="seconds"),
        }
        history = as_list(self.automation.get("ItemHistory"))
        self.automation["ItemHistory"] = (history + [entry])[-500:]

    def add_inventory_item(self, container: str, item: str) -> bool:
        key = self.container_key(container)
        if key == "HerbPouchItems" and not self.inventory.get("HasHerbPouch"):
            key = "BackpackItems"
        if not key:
            return False

        if key == "BackpackItems" and not bool(self.automation_flags.get("backpackAvailable", True)):
            return False
        if key == "Weapons" and len(as_list(self.inventory["Weapons"])) >= 2:
            return False
        if key == "BackpackItems" and item_slot_total(self.inventory["BackpackItems"]) + item_slot_cost(item) > 8:
            return False
        if key == "HerbPouchItems" and item_slot_total(self.inventory["HerbPouchItems"]) + item_slot_cost(item) > 8:
            return False
        if key == "SpecialItems" and item in as_list(self.inventory["SpecialItems"]):
            return True

        self.inventory[key] = as_list(self.inventory[key]) + [item]
        if key == "Weapons":
            self.automation_flags["weaponsAvailable"] = True
        if key == "BackpackItems":
            self.inventory["HasBackpack"] = True
            self.automation_flags["backpackAvailable"] = True
            self.automation_flags["backpackItemsAvailable"] = True
        return True

    def add_flexible_storage_item(self, item: str) -> bool:
        if self.inventory.get("HasHerbPouch") and self.add_inventory_item("herb", item):
            return True
        return self.add_inventory_item("backpack", item)

    def count_items(self, name: str, containers: Any = None, match_mode: str = "exact") -> int:
        total = 0
        for key in self.automation_containers(containers):
            total += sum(1 for item in as_list(self.inventory.get(key)) if self.item_matches(item, name, match_mode))
        return total

    def has_item(self, name: str, containers: Any = None, match_mode: str = "exact") -> bool:
        return self.count_items(name, containers, match_mode) > 0

    def has_item_history(self, name: str, containers: Any = None, match_mode: str = "exact") -> bool:
        if self.has_item(name, containers, match_mode):
            return True
        container_keys = set(self.automation_containers(containers)) if containers else set()
        for entry in as_list(self.automation.get("ItemHistory")):
            if not isinstance(entry, dict):
                continue
            if container_keys:
                key = self.container_key(str(entry.get("Container") or ""))
                if key not in container_keys:
                    continue
            if self.item_matches(entry.get("Name", ""), name, match_mode):
                return True
        for summary in as_list(self.state.get("BookHistory")):
            if not isinstance(summary, dict):
                continue
            for key in ("Weapons", "BackpackItems", "SpecialItems"):
                if container_keys and key not in container_keys:
                    continue
                for item in as_list(summary.get(key)):
                    if self.item_matches(item, name, match_mode):
                        return True
        return False

    def has_power(self, name: str) -> bool:
        return name in as_list(self.character.get("KaiDisciplines"))

    def section_source_routes(self, book_number: int | None = None, section: int | None = None) -> list[int]:
        book_number = int(book_number or self.character["BookNumber"])
        section = int(section or self.state["CurrentSection"])
        book = BOOKS.get(book_number, BOOKS[1])
        section_path = self.books_dir / book["Folder"] / f"sect{section}.htm"
        if not section_path.exists():
            return []
        try:
            text = section_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []
        routes: list[int] = []
        for match in re.finditer(r'href=["\']sect(\d+)\.htm', text, flags=re.IGNORECASE):
            target = int(match.group(1))
            if target not in routes:
                routes.append(target)
        return routes

    def section_source_route_payload(
        self, book_number: int | None = None, section: int | None = None
    ) -> list[dict[str, Any]]:
        book_number = int(book_number or self.character["BookNumber"])
        section = int(section or self.state["CurrentSection"])
        book = BOOKS.get(book_number, BOOKS[1])
        section_path = self.books_dir / book["Folder"] / f"sect{section}.htm"
        if not section_path.exists():
            return []
        try:
            source = section_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return []

        choices: list[dict[str, Any]] = []
        seen: set[int] = set()
        choice_pattern = re.compile(
            r"<p\b[^>]*class=[\"'][^\"']*\bchoice\b[^\"']*[\"'][^>]*>(.*?)</p>",
            flags=re.IGNORECASE | re.DOTALL,
        )
        route_pattern = re.compile(r"href=[\"']sect(\d+)\.htm", flags=re.IGNORECASE)
        for choice_match in choice_pattern.finditer(source):
            block = choice_match.group(1)
            label = html.unescape(re.sub(r"<[^>]+>", "", block))
            label = re.sub(r"\s+", " ", label).strip()
            for route_match in route_pattern.finditer(block):
                target = int(route_match.group(1))
                if target in seen:
                    continue
                seen.add(target)
                choices.append({"Section": target, "Label": label or f"Go to {target}"})

        if choices:
            return choices
        return self.route_button_payload(self.section_source_routes(book_number, section))

    def route_button_payload(self, routes: Any = None) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for route in as_list(routes):
            try:
                section = int(route)
            except (TypeError, ValueError):
                continue
            result.append({"Section": section, "Label": f"Go to {section}"})
        return result

    def flow_source_route_payload(self, entry: dict[str, Any] | None) -> list[dict[str, Any]]:
        if not isinstance(entry, dict):
            return []
        raw_routes = entry.get("sourceRoutes")
        if raw_routes is None:
            raw_routes = entry.get("routes")

        result: list[dict[str, Any]] = []
        seen: set[int] = set()
        for route in as_list(raw_routes):
            if isinstance(route, dict):
                raw_section = route.get("Section", route.get("section"))
                raw_label = route.get("Label", route.get("label"))
            else:
                raw_section = route
                raw_label = ""
            try:
                section = int(raw_section)
            except (TypeError, ValueError):
                continue
            if section in seen:
                continue
            seen.add(section)
            payload = {"Section": section, "Label": str(raw_label or f"Go to {section}")}
            if isinstance(route, dict):
                actions = route.get("Actions", route.get("actions"))
                if actions is not None:
                    payload["Actions"] = as_list(actions)
                effect_label = route.get("EffectLabel", route.get("effectLabel"))
                if effect_label:
                    payload["EffectLabel"] = str(effect_label)
            result.append(payload)
        return result

    def merge_route_labels(
        self,
        audited_routes: list[dict[str, Any]],
        source_routes: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        source_by_section: dict[int, dict[str, Any]] = {}
        for route in source_routes:
            if not isinstance(route, dict):
                continue
            try:
                source_by_section[int(route.get("Section"))] = route
            except (TypeError, ValueError):
                continue

        merged: list[dict[str, Any]] = []
        for route in audited_routes:
            try:
                section = int(route.get("Section"))
            except (TypeError, ValueError):
                continue
            payload = dict(route)
            source = source_by_section.get(section, {})
            if source.get("Label"):
                payload["Label"] = str(source["Label"])
            payload["Audited"] = True
            merged.append(payload)
        return merged

    def route_payload_for_target(self, target: int) -> dict[str, Any] | None:
        entry = self.current_section_flow_entry() or {}
        for route in self.flow_source_route_payload(entry):
            if int(route.get("Section") or 0) == int(target):
                return route
        return None

    def apply_route_actions(self, target: int) -> list[str]:
        route = self.route_payload_for_target(target)
        if not isinstance(route, dict):
            return []
        actions = [action for action in as_list(route.get("Actions")) if isinstance(action, dict)]
        if not actions:
            return []
        if not bool(self.automation.get("Enabled", True)):
            return ["Route effects skipped because automation is disabled."]

        key = f"{self.current_visit_key()}:route:{int(target)}"
        applied = as_list(self.automation.get("AppliedRouteActions"))
        if key in applied:
            return ["Route effects already applied for this section visit."]

        messages: list[str] = []
        for action in actions:
            message = self.apply_automation_action(action)
            if message:
                messages.append(message)

        if messages:
            applied.append(key)
            self.automation["AppliedRouteActions"] = applied[-500:]
            journal = as_list(self.automation.get("Journal"))
            journal.append(
                {
                    "Kind": "route",
                    "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                    "VisitKey": self.current_visit_key(),
                    "BookNumber": int(self.character["BookNumber"]),
                    "Section": int(self.state["CurrentSection"]),
                    "Summary": f"Route to section {int(target)}",
                    "Messages": messages,
                    "TargetSection": int(target),
                }
            )
            self.automation["Journal"] = journal[-100:]
        return messages

    def legal_route_targets_for_current_section(self) -> set[int]:
        book = BOOKS.get(int(self.character["BookNumber"]), BOOKS[1])
        section = int(self.state["CurrentSection"])
        entry = self.current_section_flow_entry() or {}
        routes = {
            int(route["Section"])
            for route in self.flow_source_route_payload(entry)
            if 1 <= int(route["Section"]) <= int(book["MaxSection"])
        }
        if not routes:
            routes.update(self.section_source_routes(int(self.character["BookNumber"]), section))
        return routes

    def follow_route(self, section: int) -> None:
        target = int(section)
        current = int(self.state["CurrentSection"])
        legal_routes = self.legal_route_targets_for_current_section()
        if legal_routes and target not in legal_routes:
            print(
                f"Section {target} is not a recorded route from section {current}. "
                "Use Set Position for manual jumps."
            )
            return
        for message in self.apply_route_actions(target):
            print(f"Route effect: {message}")
        self.set_section(target)

    def evaluate_flow_condition(self, condition: dict[str, Any] | None) -> bool:
        if not condition:
            return True
        kind = str(condition.get("type") or "").lower()
        if kind == "any":
            return any(
                self.evaluate_flow_condition(item)
                for item in as_list(condition.get("conditions"))
                if isinstance(item, dict)
            )
        if kind == "all":
            conditions = [item for item in as_list(condition.get("conditions")) if isinstance(item, dict)]
            return bool(conditions) and all(self.evaluate_flow_condition(item) for item in conditions)
        if kind == "power":
            return self.has_power(str(condition.get("name") or ""))
        if kind == "no_power":
            return not self.has_power(str(condition.get("name") or ""))
        if kind in {"kai_rank_gte", "rank_gte"}:
            return kai_rank_meets(self.character.get("KaiDisciplines"), str(condition.get("name") or condition.get("rank") or condition.get("value") or ""))
        if kind in {"discipline_count_gte", "kai_disciplines_gte"}:
            return len(clean_kai_disciplines(self.character.get("KaiDisciplines"))) >= int(condition.get("value") or 0)
        if kind == "item":
            return self.has_item(
                str(condition.get("name") or ""),
                condition.get("containers"),
                str(condition.get("match") or "exact"),
            )
        if kind == "item_history":
            return self.has_item_history(
                str(condition.get("name") or ""),
                condition.get("containers"),
                str(condition.get("match") or "exact"),
            )
        if kind == "no_item_history":
            return not self.has_item_history(
                str(condition.get("name") or ""),
                condition.get("containers"),
                str(condition.get("match") or "exact"),
            )
        if kind == "no_item":
            return not self.has_item(
                str(condition.get("name") or ""),
                condition.get("containers"),
                str(condition.get("match") or "exact"),
            )
        if kind in {"fought_enemy", "enemy_history"}:
            target = str(condition.get("name") or "").strip().lower()
            return bool(target) and any(
                target in str(entry.get("EnemyName") or "").strip().lower()
                for entry in as_list(self.state.get("CombatHistory"))
                if isinstance(entry, dict)
            )
        if kind == "flag":
            return self.automation_flags.get(str(condition.get("key") or "")) == condition.get("value", True)
        if kind == "no_flag":
            return self.automation_flags.get(str(condition.get("key") or "")) != condition.get("value", True)
        if kind in {"active_weaponskill_weapon", "weaponskill_active_weapon"}:
            return self.active_weapon_matches_weaponskill()
        if kind == "wp_gt":
            return int(self.character["WillpowerCurrent"]) > int(condition.get("value") or 0)
        if kind == "wp_gte":
            return int(self.character["WillpowerCurrent"]) >= int(condition.get("value") or 0)
        if kind == "end_lt":
            return int(self.character["EnduranceCurrent"]) < int(condition.get("value") or 0)
        if kind == "end_gte":
            return int(self.character["EnduranceCurrent"]) >= int(condition.get("value") or 0)
        if kind == "staff_available":
            return self.has_available_staff()
        return False

    def active_weapon_matches_weaponskill(self) -> bool:
        if not self.has_power("Weaponskill"):
            return False
        skill = str(self.character.get("WeaponskillWeapon") or "").strip().lower()
        if not skill:
            return False
        active = str(self.combat.get("ActiveWeapon") or "").strip()
        if not active:
            active = str(self.settings.get("PreferredCombatWeapon") or "").strip()
        if not active:
            active = self.default_combat_weapon()
        active_key = active.lower()
        if active_key == "magic spear":
            active_key = "spear"
        elif active_key in {"sommerswerd", "bone sword"}:
            active_key = "sword"
        return active_key == skill

    def route_check_stat_value(self, stat: str) -> int:
        key = str(stat or "").replace("_", "").replace(" ", "").lower()
        if key in {"wp", "willpower"}:
            return int(self.character["WillpowerCurrent"])
        if key in {"end", "endurance"}:
            return int(self.character["EnduranceCurrent"])
        if key in {"cs", "combatskill"}:
            return int(self.character["CombatSkillCurrent"])
        if key in {"gold", "goldcrowns", "crowns", "nobles"}:
            return int(self.inventory.get("GoldCrowns") or self.inventory.get("Nobles") or 0)
        return 0

    def evaluate_route_check_formula(self, formula: dict[str, Any] | None) -> int | None:
        if not isinstance(formula, dict):
            return None
        total = int(formula.get("base") or 0)
        for term in as_list(formula.get("terms")):
            if not isinstance(term, dict):
                continue
            if not self.evaluate_flow_condition(term.get("condition")):
                continue
            multiplier = int(term.get("multiplier", 1) or 1)
            if term.get("stat"):
                value = self.route_check_stat_value(str(term.get("stat") or ""))
            else:
                value = int(term.get("value") or 0)
            total += value * multiplier
        return total

    def route_check_test_label(self, outcome: dict[str, Any]) -> str:
        if outcome.get("testLabel"):
            return str(outcome.get("testLabel") or "")
        if outcome.get("default"):
            return "otherwise"
        if outcome.get("conditions"):
            return "conditions met"
        test = str(outcome.get("test") or "range").lower()
        if test == "range":
            minimum = outcome.get("min", -999)
            maximum = outcome.get("max", 999)
            if int(minimum) <= -999:
                return f"<= {maximum}"
            if int(maximum) >= 999:
                return f">= {minimum}"
            return f"{minimum}-{maximum}"
        if test == "gt":
            return f"> {outcome.get('value')}"
        if test == "gte":
            return f">= {outcome.get('value')}"
        if test == "lt":
            return f"< {outcome.get('value')}"
        if test == "lte":
            return f"<= {outcome.get('value')}"
        if test == "eq":
            return f"= {outcome.get('value')}"
        return str(outcome.get("label") or "result")

    def route_check_outcome_matches(self, outcome: dict[str, Any], value: int | None) -> bool:
        conditions = [condition for condition in as_list(outcome.get("conditions")) if isinstance(condition, dict)]
        if conditions and not all(self.evaluate_flow_condition(condition) for condition in conditions):
            return False
        if outcome.get("default"):
            return True
        if value is None:
            return bool(conditions)
        test = str(outcome.get("test") or "range").lower()
        if test == "range":
            return int(outcome.get("min", -999)) <= value <= int(outcome.get("max", 999))
        if test == "gt":
            return value > int(outcome.get("value") or 0)
        if test == "gte":
            return value >= int(outcome.get("value") or 0)
        if test == "lt":
            return value < int(outcome.get("value") or 0)
        if test == "lte":
            return value <= int(outcome.get("value") or 0)
        if test == "eq":
            return value == int(outcome.get("value") or 0)
        return False

    def evaluate_route_checks(
        self,
        flow: dict[str, Any],
        automation_payload: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        checks: list[dict[str, Any]] = []
        automation_payload = automation_payload or self.current_section_automation_payload()
        automation_ready = not bool(automation_payload.get("Summary")) or bool(automation_payload.get("Applied"))

        for check in as_list(flow.get("routeChecks")):
            if not isinstance(check, dict):
                continue
            requires_automation = bool(check.get("requiresAutomationApplied"))
            ready = not requires_automation or automation_ready
            value = self.evaluate_route_check_formula(check.get("formula")) if ready else None
            outcomes: list[dict[str, Any]] = []
            matched_outcome: dict[str, Any] | None = None
            for outcome in as_list(check.get("outcomes")):
                if not isinstance(outcome, dict):
                    continue
                matched = ready and matched_outcome is None and self.route_check_outcome_matches(outcome, value)
                payload = {
                    "Label": str(outcome.get("label") or ""),
                    "ChoiceLabel": str(outcome.get("choiceLabel") or ""),
                    "Route": int(outcome.get("route")) if outcome.get("route") is not None else None,
                    "Matched": matched,
                    "Test": self.route_check_test_label(outcome),
                }
                outcomes.append(payload)
                if matched:
                    matched_outcome = payload

            checks.append(
                {
                    "Id": str(check.get("id") or ""),
                    "Label": str(check.get("label") or "Route check"),
                    "Summary": str(check.get("summary") or ""),
                    "Formula": str((check.get("formula") or {}).get("label") or ""),
                    "Value": value,
                    "Ready": ready,
                    "BlockedReason": (
                        str(check.get("blockedReason") or "Apply the entry effect first, then recheck the route.")
                        if not ready
                        else ""
                    ),
                    "Outcomes": outcomes,
                    "MatchedOutcome": matched_outcome,
                }
            )
        return checks

    def evaluate_roll_flow(self, flow: dict[str, Any], raw_roll: int | None = None) -> dict[str, Any]:
        roll = flow.get("roll") if isinstance(flow.get("roll"), dict) else {}
        if not roll:
            return {}
        raw = random_digit() if raw_roll is None else int(raw_roll)
        raw = max(0, min(9, raw))
        modifiers: list[dict[str, Any]] = []
        total = 10 if raw == 0 and bool(roll.get("zeroAsTen")) else raw
        for modifier in as_list(roll.get("modifiers")):
            if not isinstance(modifier, dict):
                continue
            applies = self.evaluate_flow_condition(modifier.get("condition"))
            if applies and modifier.get("valueFrom"):
                value_from = str(modifier.get("valueFrom") or "").lower()
                if value_from in {"end", "endurance"}:
                    value = int(self.character["EnduranceCurrent"])
                elif value_from in {"wp", "willpower"}:
                    value = int(self.character["WillpowerCurrent"])
                elif value_from in {"cs", "combat_skill", "combat skill"}:
                    value = int(self.character["CombatSkillCurrent"])
                else:
                    value = 0
            else:
                value = int(modifier.get("value") or 0) if applies else 0
            total += value
            modifiers.append(
                {
                    "Label": modifier.get("label", "Modifier"),
                    "Value": value,
                    "Applies": applies,
                }
            )
        route = None
        label = ""
        matched_actions: list[dict[str, Any]] = []
        for outcome in as_list(roll.get("outcomes")):
            if not isinstance(outcome, dict):
                continue
            test = str(outcome.get("test") or "range").lower()
            matched = False
            if test == "range":
                matched = int(outcome.get("min", -999)) <= total <= int(outcome.get("max", 999))
            elif test == "even":
                matched = raw % 2 == 0
            elif test == "odd":
                matched = raw % 2 == 1
            elif test == "values":
                matched = raw in [int(value) for value in as_list(outcome.get("values"))]
            elif test in {"lte_stat", "le_stat", "total_lte_stat"}:
                matched = total <= self.route_check_stat_value(str(outcome.get("stat") or ""))
            elif test in {"lt_stat", "total_lt_stat"}:
                matched = total < self.route_check_stat_value(str(outcome.get("stat") or ""))
            elif test in {"gte_stat", "ge_stat", "total_gte_stat"}:
                matched = total >= self.route_check_stat_value(str(outcome.get("stat") or ""))
            elif test in {"gt_stat", "total_gt_stat"}:
                matched = total > self.route_check_stat_value(str(outcome.get("stat") or ""))
            if matched:
                route = int(outcome.get("route")) if outcome.get("route") is not None else None
                label = str(outcome.get("label") or "")
                matched_actions = [
                    action for action in as_list(outcome.get("actions")) if isinstance(action, dict)
                ]
                ending = str(outcome.get("ending") or "")
                if ending:
                    matched_actions.append(
                        {
                            "type": "ending",
                            "ending": ending,
                            "cause": str(outcome.get("cause") or f"Section {self.state['CurrentSection']} ended the run."),
                        }
                    )
                break
        return {
            "Section": int(self.state["CurrentSection"]),
            "Raw": raw,
            "Total": total,
            "Modifiers": modifiers,
            "Route": route,
            "Outcome": label,
            "Summary": roll.get("summary", ""),
            "Actions": json_clone(matched_actions),
        }

    def staged_roll_entry(self, flow: dict[str, Any] | None = None) -> dict[str, Any] | None:
        entry = flow if isinstance(flow, dict) else (self.current_section_flow_entry() or {})
        staged = entry.get("stagedRoll") if isinstance(entry, dict) else None
        return staged if isinstance(staged, dict) else None

    def staged_roll_store(self) -> dict[str, Any]:
        store = self.automation.get("StagedRolls")
        if not isinstance(store, dict):
            store = {}
            self.automation["StagedRolls"] = store
        return store

    def staged_roll_key(self, staged: dict[str, Any]) -> str:
        roll_id = str(staged.get("id") or "staged-roll")
        return f"{self.current_visit_key()}:{roll_id}"

    def staged_roll_stages(self, staged: dict[str, Any]) -> list[dict[str, Any]]:
        return [stage for stage in as_list(staged.get("stages")) if isinstance(stage, dict)]

    def staged_roll_stage(self, staged: dict[str, Any], stage_id: str) -> dict[str, Any] | None:
        for stage in self.staged_roll_stages(staged):
            if str(stage.get("id") or "") == str(stage_id):
                return stage
        stages = self.staged_roll_stages(staged)
        return stages[0] if stages else None

    def default_staged_roll_state(self, staged: dict[str, Any]) -> dict[str, Any]:
        first = self.staged_roll_stage(staged, "")
        return {
            "Id": str(staged.get("id") or "staged-roll"),
            "Stage": str(first.get("id") or "stage-1") if first else "",
            "Complete": False,
            "History": [],
            "LastResult": None,
        }

    def staged_roll_state(self, staged: dict[str, Any]) -> dict[str, Any]:
        store = self.staged_roll_store()
        key = self.staged_roll_key(staged)
        state = store.get(key)
        if not isinstance(state, dict):
            state = self.default_staged_roll_state(staged)
            store[key] = state
        state.setdefault("History", [])
        state.setdefault("Complete", False)
        return state

    def evaluate_staged_roll_modifiers(
        self, stage: dict[str, Any], raw: int
    ) -> tuple[int, list[dict[str, Any]]]:
        total = 10 if raw == 0 and bool(stage.get("zeroAsTen")) else raw
        modifiers: list[dict[str, Any]] = []
        for modifier in as_list(stage.get("modifiers")):
            if not isinstance(modifier, dict):
                continue
            applies = self.evaluate_flow_condition(modifier.get("condition"))
            value = int(modifier.get("value") or 0) if applies else 0
            total += value
            modifiers.append(
                {
                    "Label": modifier.get("label", "Modifier"),
                    "Value": value,
                    "Applies": applies,
                }
            )
        return total, modifiers

    def evaluate_staged_roll_outcome(
        self, stage: dict[str, Any], raw: int, total: int | None = None, history: list[Any] | None = None
    ) -> dict[str, Any]:
        value = raw if total is None else int(total)
        prior = [item for item in as_list(history) if isinstance(item, dict)]
        for outcome in as_list(stage.get("outcomes")):
            if not isinstance(outcome, dict):
                continue
            test = str(outcome.get("test") or "range").lower()
            matched = False
            if test == "range":
                matched = int(outcome.get("min", -999)) <= value <= int(outcome.get("max", 999))
            elif test == "values":
                matched = value in [int(item) for item in as_list(outcome.get("values"))]
            elif test == "even":
                matched = value % 2 == 0
            elif test == "odd":
                matched = value % 2 == 1
            elif test in {"lt_history", "gt_history", "eq_history"}:
                compare_stage = str(outcome.get("stage") or outcome.get("compareStage") or "")
                compare = None
                for item in reversed(prior):
                    if compare_stage and str(item.get("Stage") or "") != compare_stage:
                        continue
                    compare = int(item.get("Total", item.get("Raw", 0)) or 0)
                    break
                if compare is not None:
                    if test == "lt_history":
                        matched = value < compare
                    elif test == "gt_history":
                        matched = value > compare
                    else:
                        matched = value == compare
            if matched:
                return outcome
        return {}

    def roll_staged_current_section(
        self, flow: dict[str, Any], raw_roll: int | None = None
    ) -> dict[str, Any]:
        staged = self.staged_roll_entry(flow)
        if not staged:
            return {}
        state = self.staged_roll_state(staged)
        if bool(state.get("Complete")) and isinstance(state.get("LastResult"), dict):
            result = json_clone(state["LastResult"])
            result["Actions"] = []
            result["AlreadyComplete"] = True
            return result

        raw = random_digit() if raw_roll is None else max(0, min(9, int(raw_roll)))
        stage = self.staged_roll_stage(staged, str(state.get("Stage") or ""))
        if not stage:
            return {
                "Section": int(self.state["CurrentSection"]),
                "Raw": raw,
                "Total": raw,
                "Modifiers": [],
                "Route": None,
                "Outcome": "No staged roll stage configured",
                "Summary": str(staged.get("summary") or "Staged roll"),
                "Actions": [],
                "Staged": True,
                "Complete": True,
            }

        total, modifiers = self.evaluate_staged_roll_modifiers(stage, raw)
        history = as_list(state.get("History"))
        outcome = self.evaluate_staged_roll_outcome(stage, raw, total, history)
        route = int(outcome.get("route")) if outcome.get("route") is not None else None
        next_stage = str(outcome.get("nextStage") or "")
        ending = str(outcome.get("ending") or "")
        actions = [action for action in as_list(outcome.get("actions")) if isinstance(action, dict)]
        if ending:
            actions.append(
                {
                    "type": "ending",
                    "ending": ending,
                    "cause": str(outcome.get("cause") or f"Section {self.state['CurrentSection']} ended the run."),
                }
            )

        result = {
            "Section": int(self.state["CurrentSection"]),
            "Raw": raw,
            "Total": total,
            "Modifiers": modifiers,
            "Route": route,
            "Outcome": str(outcome.get("label") or ""),
            "Summary": str(staged.get("summary") or "Staged roll"),
            "Actions": json_clone(actions),
            "Staged": True,
            "Stage": str(stage.get("id") or ""),
            "StageLabel": str(stage.get("label") or stage.get("id") or "Stage"),
            "NextStage": next_stage,
            "Complete": bool(route or ending or not next_stage),
            "Ending": ending,
        }

        history.append(
            {
                "Stage": result["Stage"],
                "StageLabel": result["StageLabel"],
                "Raw": raw,
                "Total": total,
                "Modifiers": modifiers,
                "Outcome": result["Outcome"],
                "Route": route,
                "NextStage": next_stage,
                "Ending": ending,
            }
        )
        state["History"] = history[-10:]
        if next_stage and not route and not ending:
            state["Stage"] = next_stage
            state["Complete"] = False
        else:
            state["Complete"] = True
        state["LastResult"] = json_clone(result)
        self.staged_roll_store()[self.staged_roll_key(staged)] = state
        return result

    def current_staged_roll_payload(self, entry: dict[str, Any] | None = None) -> dict[str, Any]:
        staged = self.staged_roll_entry(entry)
        if not staged:
            return {}
        state = self.staged_roll_state(staged)
        stage = self.staged_roll_stage(staged, str(state.get("Stage") or ""))
        return {
            "Id": str(staged.get("id") or ""),
            "Summary": str(staged.get("summary") or ""),
            "Stage": str(stage.get("id") or "") if stage else "",
            "StageLabel": str(stage.get("label") or stage.get("id") or "") if stage else "",
            "Complete": bool(state.get("Complete")),
            "History": as_list(state.get("History")),
            "LastResult": json_clone(state.get("LastResult")) if isinstance(state.get("LastResult"), dict) else None,
        }

    def apply_roll_outcome_actions(self, result: dict[str, Any]) -> list[str]:
        actions = [action for action in as_list(result.get("Actions")) if isinstance(action, dict)]
        if not actions:
            return []
        if not bool(self.automation.get("Enabled", True)):
            return ["Roll outcome effects skipped because automation is disabled."]

        key = f"{self.current_visit_key()}:roll-effects"
        applied = as_list(self.automation.get("AppliedRollEffects"))
        if key in applied:
            return ["Roll outcome effects already applied for this visit."]

        messages: list[str] = []
        for action in actions:
            resolved_action = dict(action)
            delta_from = str(resolved_action.get("deltaFrom") or "").lower()
            if delta_from in {"roll_total", "total"}:
                delta = int(result.get("Total") or 0) * int(resolved_action.get("multiplier") or 1)
                if resolved_action.get("minDelta") is not None:
                    delta = max(delta, int(resolved_action.get("minDelta") or 0))
                if resolved_action.get("maxDelta") is not None:
                    delta = min(delta, int(resolved_action.get("maxDelta") or 0))
                resolved_action["delta"] = delta
            elif delta_from in {"roll_raw", "raw"}:
                delta = int(result.get("Raw") or 0) * int(resolved_action.get("multiplier") or 1)
                if resolved_action.get("minDelta") is not None:
                    delta = max(delta, int(resolved_action.get("minDelta") or 0))
                if resolved_action.get("maxDelta") is not None:
                    delta = min(delta, int(resolved_action.get("maxDelta") or 0))
                resolved_action["delta"] = delta
            message = self.apply_automation_action(resolved_action)
            if message:
                messages.append(message)

        if messages:
            applied.append(key)
            self.automation["AppliedRollEffects"] = applied[-500:]
            journal = as_list(self.automation.get("Journal"))
            journal.append(
                {
                    "Kind": "roll",
                    "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                    "VisitKey": self.current_visit_key(),
                    "BookNumber": int(self.character["BookNumber"]),
                    "Section": int(self.state["CurrentSection"]),
                    "Summary": result.get("Summary", "Roll outcome effects"),
                    "Messages": messages,
                    "Roll": {
                        "Raw": result.get("Raw"),
                        "Total": result.get("Total"),
                        "Outcome": result.get("Outcome"),
                        "Route": result.get("Route"),
                    },
                }
            )
            self.automation["Journal"] = journal[-100:]
        return messages

    def roll_current_section(self, raw_roll: int | None = None) -> dict[str, Any]:
        flow = self.current_section_flow_entry() or {}
        if isinstance(flow.get("stagedRoll"), dict):
            result = self.roll_staged_current_section(flow, raw_roll)
        elif not isinstance(flow.get("roll"), dict):
            raw = random_digit() if raw_roll is None else max(0, min(9, int(raw_roll)))
            result = {
                "Section": int(self.state["CurrentSection"]),
                "Raw": raw,
                "Total": raw,
                "Modifiers": [],
                "Route": None,
                "Outcome": "Generic random digit",
                "Summary": "Generic roll 0-9",
                "Actions": [],
            }
        else:
            result = self.evaluate_roll_flow(flow, raw_roll)
        result["BookNumber"] = int(self.character["BookNumber"])
        result["RolledAt"] = datetime.now().isoformat(timespec="seconds")
        action_messages = self.apply_roll_outcome_actions(result)
        if result.get("AlreadyComplete"):
            action_messages = ["Staged roll already complete for this section visit."] + action_messages
        result["ActionMessages"] = action_messages
        result["ActionsApplied"] = bool(
            action_messages
            and not action_messages[0].startswith(
                ("Roll outcome effects", "Staged roll already complete")
            )
        )
        self.automation["LastRoll"] = result
        self.autosave()
        return result

    def cartwheel_session_key(self) -> str:
        return f"cartwheelWinnings:{self.current_visit_key()}"

    def current_cartwheel_payload(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        game = entry.get("cartwheel") if isinstance(entry, dict) else None
        if not isinstance(game, dict):
            return None
        stored = self.automation.get("Stored")
        if not isinstance(stored, dict):
            stored = {}
            self.automation["Stored"] = stored
        session_key = self.cartwheel_session_key()
        win_limit = max(0, int(game.get("winLimit") or 40))
        table_winnings = max(0, int(stored.get(session_key) or 0))
        token_flag = str(game.get("freeTokenFlag") or "book2CartwheelFreeTokenUsed")
        token_value = max(0, int(game.get("freeTokenValue") or 0))
        free_token_available = token_value > 0 and not bool(self.automation_flags.get(token_flag))
        gold = int(self.inventory.get("GoldCrowns") or 0)
        last_result = stored.get(f"{session_key}:last")
        if not isinstance(last_result, dict) or last_result.get("VisitKey") != self.current_visit_key():
            last_result = None
        return {
            "Available": True,
            "Id": str(game.get("id") or "cartwheel"),
            "Label": str(game.get("label") or "Play Cartwheel"),
            "Summary": str(game.get("summary") or ""),
            "WinLimit": win_limit,
            "TableWinnings": min(table_winnings, win_limit),
            "RemainingWinnings": max(0, win_limit - table_winnings),
            "ExactMultiplier": max(0, int(game.get("exactMultiplier") or 8)),
            "AdjacentMultiplier": max(0, int(game.get("adjacentMultiplier") or 5)),
            "FreeTokenAvailable": free_token_available,
            "FreeTokenValue": token_value,
            "MaxStake": gold + (token_value if free_token_available else 0),
            "LastResult": json_clone(last_result) if last_result else None,
        }

    def gold_distraction_session_key(self) -> str:
        return f"goldDistraction:{self.current_visit_key()}"

    def portholes_session_key(self) -> str:
        return f"portholes:{self.current_visit_key()}"

    def current_portholes_payload(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        game = entry.get("portholes") if isinstance(entry, dict) else None
        if not isinstance(game, dict):
            return None
        stored = self.automation.get("Stored")
        if not isinstance(stored, dict):
            stored = {}
            self.automation["Stored"] = stored
        session_key = self.portholes_session_key()
        last_result = stored.get(f"{session_key}:last")
        if not isinstance(last_result, dict) or last_result.get("VisitKey") != self.current_visit_key():
            last_result = None
        stake = max(1, int(game.get("stake") or 3))
        gold = int(self.inventory.get("GoldCrowns") or 0)
        return {
            "Available": True,
            "Id": str(game.get("id") or "portholes"),
            "Label": str(game.get("label") or "Play Portholes"),
            "Summary": str(game.get("summary") or ""),
            "Stake": stake,
            "WinAmount": max(0, int(game.get("winAmount") or 6)),
            "CanPlay": gold >= stake,
            "Gold": gold,
            "LastResult": json_clone(last_result) if last_result else None,
        }

    def current_gold_distraction_payload(self, entry: dict[str, Any]) -> dict[str, Any] | None:
        game = entry.get("goldDistraction") if isinstance(entry, dict) else None
        if not isinstance(game, dict):
            return None
        stored = self.automation.get("Stored")
        if not isinstance(stored, dict):
            stored = {}
            self.automation["Stored"] = stored
        session_key = self.gold_distraction_session_key()
        last_result = stored.get(f"{session_key}:last")
        if not isinstance(last_result, dict) or last_result.get("VisitKey") != self.current_visit_key():
            last_result = None
        return {
            "Available": True,
            "Id": str(game.get("id") or "gold-distraction"),
            "Label": str(game.get("label") or "Throw Gold Crowns"),
            "Summary": str(game.get("summary") or ""),
            "MaxThrow": int(self.inventory.get("GoldCrowns") or 0),
            "SuccessRoute": int(game.get("successRoute") or 0),
            "FailureRoute": int(game.get("failureRoute") or 0),
            "ZeroAsTen": bool(game.get("zeroAsTen", False)),
            "LastResult": json_clone(last_result) if last_result else None,
        }

    def play_gold_distraction(self, amount: Any, raw_roll: Any | None = None) -> dict[str, Any] | None:
        entry = self.current_section_flow_entry() or {}
        game = entry.get("goldDistraction") if isinstance(entry, dict) else None
        if not isinstance(game, dict):
            print("Gold distraction is not available in this section.")
            return None

        try:
            thrown = int(amount)
        except (TypeError, ValueError):
            print("Gold distraction needs the number of Gold Crowns to throw.")
            return None
        if thrown < 1:
            print("Throw at least 1 Gold Crown.")
            return None

        gold_before = int(self.inventory.get("GoldCrowns") or 0)
        if thrown > gold_before:
            print(f"You only have {gold_before} Gold Crowns to throw.")
            return None

        raw = coerce_random_digit(raw_roll)
        total = 10 if raw == 0 and bool(game.get("zeroAsTen", False)) else raw
        success = total <= thrown
        route = int(game.get("successRoute") if success else game.get("failureRoute") or 0)
        outcome = "Guard distracted" if success else "Guard not fooled"

        self.inventory["GoldCrowns"] = max(0, gold_before - thrown)
        self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])

        stored = self.automation.get("Stored")
        if not isinstance(stored, dict):
            stored = {}
            self.automation["Stored"] = stored
        session_key = self.gold_distraction_session_key()
        result = {
            "Game": "Gold Distraction",
            "VisitKey": self.current_visit_key(),
            "Thrown": thrown,
            "Raw": raw,
            "Total": total,
            "Outcome": outcome,
            "Route": route,
            "Success": success,
            "GoldBefore": gold_before,
            "GoldAfter": int(self.inventory.get("GoldCrowns") or 0),
        }
        stored[f"{session_key}:last"] = result
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "gold_distraction",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "BookNumber": int(self.character["BookNumber"]),
                "Section": int(self.state["CurrentSection"]),
                "VisitKey": self.current_visit_key(),
                "Summary": outcome,
                "Result": json_clone(result),
            }
        )
        self.automation["Journal"] = journal[-100:]

        print(f"Gold distraction: threw {thrown}, roll {raw} total {total} - {outcome}.")
        print(f"Gold Crowns {gold_before}->{self.inventory['GoldCrowns']}")
        if route:
            print(f"Route: section {route}.")
            self.set_section(route)
        else:
            self.autosave()
        return result

    def play_portholes(
        self,
        player1_die1: Any | None = None,
        player1_die2: Any | None = None,
        player2_die1: Any | None = None,
        player2_die2: Any | None = None,
        lone_wolf_die1: Any | None = None,
        lone_wolf_die2: Any | None = None,
    ) -> dict[str, Any] | None:
        entry = self.current_section_flow_entry() or {}
        game = entry.get("portholes") if isinstance(entry, dict) else None
        if not isinstance(game, dict):
            print("Portholes is not available in this section.")
            return None

        stake = max(1, int(game.get("stake") or 3))
        win_amount = max(0, int(game.get("winAmount") or 6))
        gold_before = int(self.inventory.get("GoldCrowns") or 0)
        if gold_before < stake:
            print(f"Portholes needs {stake} Gold Crowns to stake, but only {gold_before} are carried.")
            return None

        def roll_pair(first: Any | None, second: Any | None) -> dict[str, Any]:
            die1 = coerce_random_digit(first)
            die2 = coerce_random_digit(second)
            return {"Die1": die1, "Die2": die2, "Total": die1 + die2, "Portholes": die1 == 0 and die2 == 0}

        player1 = roll_pair(player1_die1, player1_die2)
        player2 = roll_pair(player2_die1, player2_die2)
        lone_wolf = roll_pair(lone_wolf_die1, lone_wolf_die2)
        other_portholes = bool(player1["Portholes"] or player2["Portholes"])

        if lone_wolf["Portholes"] and not other_portholes:
            outcome = "Lone Wolf calls Portholes"
            gold_delta = win_amount
        elif other_portholes:
            outcome = "Another player calls Portholes"
            gold_delta = -stake
        elif int(lone_wolf["Total"]) > max(int(player1["Total"]), int(player2["Total"])):
            outcome = "Lone Wolf has the highest total"
            gold_delta = win_amount
        elif int(player1["Total"]) > int(lone_wolf["Total"]) or int(player2["Total"]) > int(lone_wolf["Total"]):
            outcome = "Another player beats Lone Wolf"
            gold_delta = -stake
        else:
            outcome = "Tie; stake returned"
            gold_delta = 0

        self.inventory["GoldCrowns"] = max(0, min(50, gold_before + gold_delta))
        self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])

        stored = self.automation.get("Stored")
        if not isinstance(stored, dict):
            stored = {}
            self.automation["Stored"] = stored
        session_key = self.portholes_session_key()
        result = {
            "Game": "Portholes",
            "VisitKey": self.current_visit_key(),
            "Player1": player1,
            "Player2": player2,
            "LoneWolf": lone_wolf,
            "Outcome": outcome,
            "GoldDelta": int(self.inventory["GoldCrowns"]) - gold_before,
            "GoldBefore": gold_before,
            "GoldAfter": int(self.inventory["GoldCrowns"]),
            "Stake": stake,
            "WinAmount": win_amount,
        }
        stored[f"{session_key}:last"] = result
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "portholes",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "BookNumber": int(self.character["BookNumber"]),
                "Section": int(self.state["CurrentSection"]),
                "VisitKey": self.current_visit_key(),
                "Summary": f"Portholes {outcome}",
                "Result": json_clone(result),
            }
        )
        self.automation["Journal"] = journal[-100:]
        self.autosave()

        print(
            "Portholes: "
            f"P1 {player1['Die1']}+{player1['Die2']}={player1['Total']}, "
            f"P2 {player2['Die1']}+{player2['Die2']}={player2['Total']}, "
            f"Lone Wolf {lone_wolf['Die1']}+{lone_wolf['Die2']}={lone_wolf['Total']} - {outcome}."
        )
        print(f"Gold Crowns {gold_before}->{self.inventory['GoldCrowns']}")
        return result

    def play_cartwheel(
        self,
        bet_number: Any,
        stake: Any,
        raw_roll: Any | None = None,
        use_free_token: Any = True,
    ) -> dict[str, Any] | None:
        entry = self.current_section_flow_entry() or {}
        game = entry.get("cartwheel") if isinstance(entry, dict) else None
        if not isinstance(game, dict):
            print("Cartwheel is not available in this section.")
            return None

        try:
            bet = max(0, min(9, int(bet_number)))
            wager = int(stake)
        except (TypeError, ValueError):
            print("Cartwheel needs a bet number and stake.")
            return None
        if wager < 1:
            print("Cartwheel stake must be at least 1 Gold Crown.")
            return None

        roll = coerce_random_digit(raw_roll)
        win_limit = max(0, int(game.get("winLimit") or 40))
        exact_multiplier = max(0, int(game.get("exactMultiplier") or 8))
        adjacent_multiplier = max(0, int(game.get("adjacentMultiplier") or 5))
        token_flag = str(game.get("freeTokenFlag") or "book2CartwheelFreeTokenUsed")
        token_value = max(0, int(game.get("freeTokenValue") or 0))
        token_available = token_value > 0 and not bool(self.automation_flags.get(token_flag))
        use_token_text = str(use_free_token).strip().lower()
        use_token = use_free_token is True or use_token_text not in {"", "0", "false", "no", "off"}
        token_used = use_token and token_available
        token_credit = min(wager, token_value) if token_used else 0
        gold_staked = max(0, wager - token_credit)
        gold_before = int(self.inventory.get("GoldCrowns") or 0)
        if gold_staked > gold_before:
            print(
                f"Cartwheel stake {wager} needs {gold_staked} Gold Crowns, "
                f"but only {gold_before} are carried."
            )
            return None

        if token_used:
            self.automation_flags[token_flag] = True

        clockwise = (roll - bet) % 10
        if roll == bet:
            outcome = "Exact hit"
            multiplier = exact_multiplier
        elif clockwise in {1, 9}:
            outcome = "Adjacent hit"
            multiplier = adjacent_multiplier
        else:
            outcome = "Miss"
            multiplier = 0

        stored = self.automation.get("Stored")
        if not isinstance(stored, dict):
            stored = {}
            self.automation["Stored"] = stored
        session_key = self.cartwheel_session_key()
        winnings_before = max(0, int(stored.get(session_key) or 0))
        payout = 0
        gold_delta = 0
        cap_note = ""

        if multiplier:
            requested = wager * multiplier
            remaining = max(0, win_limit - winnings_before)
            payout = min(requested, remaining)
            before_add = int(self.inventory.get("GoldCrowns") or 0)
            self.inventory["GoldCrowns"] = max(0, min(50, before_add + payout))
            self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])
            gold_delta = int(self.inventory["GoldCrowns"]) - before_add
            if payout < requested:
                cap_note = f"Cartwheel table limit capped payout at {payout}."
            if gold_delta < payout:
                cap_note = (cap_note + " " if cap_note else "") + "Gold carry limit capped carried winnings."
        else:
            if gold_staked:
                self.inventory["GoldCrowns"] = max(0, gold_before - gold_staked)
                self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])
            gold_delta = int(self.inventory.get("GoldCrowns") or 0) - gold_before

        winnings_after = min(win_limit, winnings_before + max(0, gold_delta))
        stored[session_key] = winnings_after
        result = {
            "Game": "Cartwheel",
            "VisitKey": self.current_visit_key(),
            "Bet": bet,
            "Stake": wager,
            "Roll": roll,
            "Outcome": outcome,
            "Multiplier": multiplier,
            "Payout": payout,
            "GoldDelta": gold_delta,
            "GoldBefore": gold_before,
            "GoldAfter": int(self.inventory.get("GoldCrowns") or 0),
            "GoldStaked": gold_staked,
            "TokenUsed": token_used,
            "TableWinningsBefore": winnings_before,
            "TableWinningsAfter": winnings_after,
            "WinLimit": win_limit,
            "Note": cap_note,
        }
        stored[f"{session_key}:last"] = result
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "cartwheel",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "BookNumber": int(self.character["BookNumber"]),
                "Section": int(self.state["CurrentSection"]),
                "VisitKey": self.current_visit_key(),
                "Summary": f"Cartwheel {outcome}",
                "Result": json_clone(result),
            }
        )
        self.automation["Journal"] = journal[-100:]
        self.autosave()

        print(f"Cartwheel: bet {bet}, stake {wager}, roll {roll} - {outcome}.")
        if token_used:
            print(f"Free silver token used for {token_credit} of the stake.")
        if multiplier:
            print(f"Payout {payout} Gold Crowns; table winnings {winnings_before}->{winnings_after}.")
        else:
            print(f"Lost {gold_staked} Gold Crowns.")
        if cap_note:
            print(cap_note)
        print(f"Gold Crowns {gold_before}->{self.inventory['GoldCrowns']}")
        return result

    def current_section_automation_payload(self) -> dict[str, Any]:
        book_number = int(self.character["BookNumber"])
        section = int(self.state["CurrentSection"])
        entry = self.section_automation_entry(book_number, section) or {}
        if not entry:
            return {"Summary": "", "Actions": [], "Applied": False, "Messages": []}

        visit_key = self.current_visit_key()
        applied = visit_key in as_list(self.automation.get("AppliedVisitEffects"))
        journal_entry = None
        for item in reversed(as_list(self.automation.get("Journal"))):
            if (
                isinstance(item, dict)
                and item.get("VisitKey") == visit_key
                and str(item.get("Kind") or "section") == "section"
            ):
                journal_entry = item
                break

        return {
            "Summary": str(entry.get("summary") or ""),
            "Actions": as_list(entry.get("actions")),
            "Applied": applied,
            "AppliedAt": str(journal_entry.get("AppliedAt") or "") if journal_entry else "",
            "Messages": as_list(journal_entry.get("Messages")) if journal_entry else [],
        }

    def healing_visit_key(self) -> str:
        return f"{self.current_visit_key()}:healing"

    def current_healing_payload(self) -> dict[str, Any]:
        current = int(self.character["EnduranceCurrent"])
        maximum = int(self.character["EnduranceMax"])
        applied = self.healing_visit_key() in as_list(self.automation.get("AppliedHealing"))
        combat_present = bool(self.flow_combat_entries())

        blocked_reason = ""
        if not self.has_power("Healing"):
            blocked_reason = "Healing is not one of your Kai Disciplines."
        elif self.death_active():
            blocked_reason = "Healing is unavailable during death recovery."
        elif combat_present:
            blocked_reason = "This section has combat; apply Healing only in non-combat sections."
        elif current >= maximum:
            blocked_reason = "Endurance is already at maximum."
        elif applied:
            blocked_reason = "Healing already applied for this section visit."

        return {
            "Available": self.has_power("Healing"),
            "Ready": blocked_reason == "",
            "Applied": applied,
            "BlockedReason": blocked_reason,
            "CurrentEndurance": current,
            "MaximumEndurance": maximum,
            "Amount": 1,
            "Summary": "Kai Healing restores 1 END in an eligible non-combat section.",
        }

    def apply_healing(self) -> None:
        payload = self.current_healing_payload()
        if not bool(payload.get("Ready")):
            reason = str(payload.get("BlockedReason") or "Healing is not available.")
            print(f"Healing not available: {reason}")
            return

        message = self.change_endurance(1)
        applied = as_list(self.automation.get("AppliedHealing"))
        applied.append(self.healing_visit_key())
        self.automation["AppliedHealing"] = applied[-500:]
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "healing",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "VisitKey": self.current_visit_key(),
                "BookNumber": int(self.character["BookNumber"]),
                "Section": int(self.state["CurrentSection"]),
                "Summary": "Kai Healing",
                "Messages": [message],
            }
        )
        self.automation["Journal"] = journal[-100:]
        self.autosave()
        print(f"Healing: {message}")

    def loss_choice_entries(self, entry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        flow = entry if isinstance(entry, dict) else (self.current_section_flow_entry() or {})
        return [choice for choice in as_list(flow.get("lossChoices")) if isinstance(choice, dict)]

    def flow_loot_key(self, option_id: str) -> str:
        return f"{self.current_visit_key()}:loot:{option_id}"

    def is_flow_loot_applied(self, option: dict[str, Any]) -> bool:
        if bool(option.get("repeatable")):
            return False
        option_id = str(option.get("id") or "")
        return self.flow_loot_key(option_id) in as_list(self.automation.get("AppliedLoot"))

    def current_flow_loot_payload(self, entry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        flow = entry if isinstance(entry, dict) else (self.current_section_flow_entry() or {})
        payload: list[dict[str, Any]] = []
        for option in as_list(flow.get("loot")):
            if not isinstance(option, dict):
                continue
            option_id = str(option.get("id") or "")
            option_payload = json_clone(option)
            option_payload["Applied"] = self.is_flow_loot_applied(option)
            option_payload["Ready"] = bool(option_id) and not bool(option_payload["Applied"])
            option_payload["Repeatable"] = bool(option.get("repeatable"))
            payload.append(option_payload)
        return payload

    def loss_choice_candidates(self, choice: dict[str, Any]) -> tuple[list[dict[str, Any]], str]:
        excluded_names = {
            str(item).strip().lower()
            for item in as_list(choice.get("excludeNames"))
            if str(item).strip()
        }

        def candidates_for(containers: Any) -> list[dict[str, Any]]:
            candidates: list[dict[str, Any]] = []
            for key in self.automation_containers(containers):
                if key == "BackpackItems" and not bool(self.automation_flags.get("backpackAvailable", True)):
                    continue
                if key == "Weapons" and not bool(self.automation_flags.get("weaponsAvailable", True)):
                    continue
                item_type = self.inventory_type_from_key(key)
                if not item_type:
                    continue
                for index, item in enumerate(as_list(self.inventory.get(key)), 1):
                    if str(item).strip().lower() in excluded_names:
                        continue
                    candidates.append(
                        {
                            "Type": item_type,
                            "Key": key,
                            "Slot": index,
                            "Item": str(item),
                        }
                    )
            return candidates

        primary = candidates_for(choice.get("containers"))
        if primary:
            return primary, "primary"
        if choice.get("fallbackContainers"):
            fallback = candidates_for(choice.get("fallbackContainers"))
            if fallback:
                return fallback, "fallback"
        return [], ""

    def loss_choice_payload(self, choice: dict[str, Any]) -> dict[str, Any]:
        choice_id = str(choice.get("id") or "")
        applied_key = f"{self.current_visit_key()}:{choice_id}"
        applied = applied_key in as_list(self.automation.get("AppliedLossChoices"))
        candidates, source = self.loss_choice_candidates(choice)
        replacement = choice.get("replacement") if isinstance(choice.get("replacement"), dict) else {}
        choice_kind = "exchange" if replacement else "loss"
        blocked_reason = ""
        if applied:
            blocked_reason = "Loss choice already applied for this section visit."
        elif not candidates:
            blocked_reason = f"No eligible carried item is available for this {choice_kind}."

        return {
            "Id": choice_id,
            "Label": str(choice.get("label") or choice_id),
            "Summary": str(choice.get("summary") or ""),
            "Ready": blocked_reason == "",
            "Applied": applied,
            "BlockedReason": blocked_reason,
            "Source": source,
            "Candidates": candidates,
            "Replacement": {
                "Container": str(replacement.get("container") or ""),
                "Name": str(replacement.get("name") or ""),
            } if replacement else None,
        }

    def current_loss_choices_payload(self, entry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        return [self.loss_choice_payload(choice) for choice in self.loss_choice_entries(entry)]

    def resolve_loss_candidate(
        self, candidates: list[dict[str, Any]], item_type: str, selection: str
    ) -> dict[str, Any] | None:
        resolved_type = self.resolve_inventory_type(item_type)
        if not resolved_type:
            return None
        typed = [candidate for candidate in candidates if candidate.get("Type") == resolved_type]
        if not typed:
            return None
        text = str(selection or "").strip()
        if text.isdigit():
            slot = int(text)
            matches = [candidate for candidate in typed if int(candidate.get("Slot") or 0) == slot]
            return matches[0] if matches else None
        exact = [candidate for candidate in typed if str(candidate.get("Item") or "").lower() == text.lower()]
        if exact:
            return exact[0]
        prefix = [candidate for candidate in typed if str(candidate.get("Item") or "").lower().startswith(text.lower())]
        return prefix[0] if len(prefix) == 1 else None

    def apply_section_loss(self, choice_id: str, item_type: str, selection: str) -> None:
        entries = self.loss_choice_entries()
        choice = next((item for item in entries if str(item.get("id") or "") == str(choice_id)), None)
        if choice is None:
            print("Loss choice not found for this section.")
            return

        payload = self.loss_choice_payload(choice)
        if not bool(payload.get("Ready")):
            print(f"Loss choice not available: {payload.get('BlockedReason')}")
            return

        candidate = self.resolve_loss_candidate(as_list(payload.get("Candidates")), item_type, selection)
        if candidate is None:
            print(f"Item not eligible for this loss: {selection}")
            return

        removed = self.remove_inventory_item_by_index(str(candidate["Key"]), int(candidate["Slot"]) - 1)
        if not removed:
            print(f"Item not found: {selection}")
            return

        messages = [f"removed {removed}"]
        replacement = choice.get("replacement") if isinstance(choice.get("replacement"), dict) else {}
        replacement_name = str(replacement.get("name") or "")
        if replacement_name:
            replacement_container = str(replacement.get("container") or candidate.get("Type") or "")
            if self.add_inventory_item(replacement_container, replacement_name):
                messages.append(f"added {replacement_name}")
            else:
                messages.append(f"could not add {replacement_name}")

        applied = as_list(self.automation.get("AppliedLossChoices"))
        applied_key = f"{self.current_visit_key()}:{choice_id}"
        applied.append(applied_key)
        self.automation["AppliedLossChoices"] = applied[-500:]
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "loss",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "VisitKey": self.current_visit_key(),
                "BookNumber": int(self.character["BookNumber"]),
                "Section": int(self.state["CurrentSection"]),
                "Summary": str(choice.get("summary") or choice_id),
                "Messages": messages,
            }
        )
        self.automation["Journal"] = journal[-100:]
        self.autosave()
        print(f"Loss choice: {'; '.join(messages)}")

    def current_section_flow_payload(self) -> dict[str, Any]:
        book_number = int(self.character["BookNumber"])
        section = int(self.state["CurrentSection"])
        entry = self.current_section_flow_entry() or {}
        audited_routes = self.flow_source_route_payload(entry)
        source_routes = self.section_source_route_payload(book_number, section)
        if audited_routes:
            display_routes = self.merge_route_labels(audited_routes, source_routes)
        else:
            display_routes = source_routes or self.route_button_payload(
                self.section_source_routes(book_number, section)
            )
        last_roll = self.automation.get("LastRoll")
        if not (
            isinstance(last_roll, dict)
            and int(last_roll.get("BookNumber", 0)) == book_number
            and int(last_roll.get("Section", 0)) == section
        ):
            last_roll = None
        automation = self.current_section_automation_payload()
        return {
            "BookNumber": book_number,
            "Section": section,
            "Entry": entry,
            "SourceRoutes": display_routes,
            "RouteAudit": {
                "Status": str(entry.get("auditStatus") or ""),
                "Classification": as_list(entry.get("classification")),
                "SourceRouteCount": int(entry.get("sourceRouteCount") or len(display_routes)),
                "IncomingRouteCount": int(entry.get("incomingRouteCount") or 0),
            },
            "LastRoll": last_roll,
            "RouteChecks": self.evaluate_route_checks(entry, automation),
            "StagedRoll": self.current_staged_roll_payload(entry),
            "Cartwheel": self.current_cartwheel_payload(entry),
            "Portholes": self.current_portholes_payload(entry),
            "GoldDistraction": self.current_gold_distraction_payload(entry),
            "Healing": self.current_healing_payload(),
            "LossChoices": self.current_loss_choices_payload(entry),
            "Loot": self.current_flow_loot_payload(entry),
            "Automation": automation,
        }

    def store_unavailable_gear(self) -> str:
        stored = self.automation["Stored"]
        equipment = stored.get("confiscatedEquipment")
        if not isinstance(equipment, dict):
            equipment = {}

        current_weapons = as_list(self.inventory.get("Weapons"))
        current_backpack = as_list(self.inventory.get("BackpackItems"))
        current_special = as_list(self.inventory.get("SpecialItems"))
        current_gold = int(self.inventory.get("GoldCrowns") or 0)
        stored_weapons = as_list(equipment.get("Weapons"))
        stored_backpack = as_list(equipment.get("BackpackItems"))
        stored_special = as_list(equipment.get("SpecialItems"))

        for item in current_weapons:
            if item not in stored_weapons:
                stored_weapons.append(item)

        if current_backpack:
            stored_backpack.extend(current_backpack)
        elif not stored_backpack:
            stored_backpack = as_list(stored.get("confiscatedBackpackItems"))

        for item in current_special:
            if item not in stored_special:
                stored_special.append(item)

        equipment["Weapons"] = stored_weapons
        equipment["BackpackItems"] = stored_backpack
        equipment["SpecialItems"] = stored_special
        if current_gold or "GoldCrowns" not in equipment:
            equipment["GoldCrowns"] = current_gold
        equipment["StoredAt"] = {
            "BookNumber": int(self.character["BookNumber"]),
            "Section": int(self.state["CurrentSection"]),
        }
        stored["confiscatedEquipment"] = equipment
        stored["confiscatedBackpackItems"] = stored_backpack

        self.inventory["Weapons"] = []
        self.inventory["BackpackItems"] = []
        self.inventory["SpecialItems"] = []
        self.inventory["GoldCrowns"] = 0
        self.inventory["Nobles"] = 0
        self.automation_flags["weaponsAvailable"] = False
        self.automation_flags["backpackAvailable"] = False
        self.automation_flags["backpackItemsAvailable"] = False
        self.automation_flags["specialItemsAvailable"] = False

        parts = []
        if stored_weapons:
            parts.append(format_list(stored_weapons))
        parts.append(f"{len(stored_backpack)} Backpack Item(s) stored")
        if stored_special:
            parts.append(f"{len(stored_special)} Special Item(s) stored")
        parts.append(f"{int(equipment.get('GoldCrowns') or 0)} Gold Crowns stored")
        return "gear stored: " + "; ".join(parts)

    def restore_unavailable_gear(self) -> str:
        stored = self.automation["Stored"]
        equipment = stored.pop("confiscatedEquipment", {})
        if not isinstance(equipment, dict):
            equipment = {}

        stored_weapons = as_list(equipment.get("Weapons"))
        stored_backpack = as_list(equipment.get("BackpackItems"))
        stored_special = as_list(equipment.get("SpecialItems"))
        stored_gold = int(equipment.get("GoldCrowns") or 0)
        legacy_backpack = as_list(stored.pop("confiscatedBackpackItems", []))
        if not stored_backpack:
            stored_backpack = legacy_backpack

        current_weapons = as_list(self.inventory.get("Weapons"))
        for item in stored_weapons:
            if item not in current_weapons:
                current_weapons.append(item)
        self.inventory["Weapons"] = current_weapons

        current_backpack = as_list(self.inventory.get("BackpackItems"))
        self.inventory["BackpackItems"] = stored_backpack + current_backpack

        current_special = as_list(self.inventory.get("SpecialItems"))
        for item in stored_special:
            if item not in current_special:
                current_special.append(item)
        self.inventory["SpecialItems"] = current_special

        before_gold = int(self.inventory.get("GoldCrowns") or 0)
        self.inventory["GoldCrowns"] = max(0, min(50, before_gold + stored_gold))
        self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])

        self.automation_flags["weaponsAvailable"] = True
        self.automation_flags["backpackAvailable"] = True
        self.automation_flags["backpackItemsAvailable"] = True
        self.automation_flags["specialItemsAvailable"] = True

        restored = []
        if stored_weapons:
            restored.append(format_list(stored_weapons))
        restored.append(f"{len(stored_backpack)} Backpack Item(s)")
        if stored_special:
            restored.append(f"{len(stored_special)} Special Item(s)")
        if stored_gold:
            restored.append(f"{stored_gold} Gold Crown(s)")
        return "gear restored: " + "; ".join(restored)

    def has_unavailable_gear_stored(self) -> bool:
        stored = self.automation.get("Stored")
        if not isinstance(stored, dict):
            return False
        equipment = stored.get("confiscatedEquipment")
        if isinstance(equipment, dict):
            for key in ("Weapons", "BackpackItems", "SpecialItems"):
                if as_list(equipment.get(key)):
                    return True
            if int(equipment.get("GoldCrowns") or 0) > 0:
                return True
        return bool(as_list(stored.get("confiscatedBackpackItems")))

    def restore_stored_gear_for_book_transition(self) -> str:
        if not self.has_unavailable_gear_stored():
            return ""
        return self.restore_unavailable_gear()

    def store_unavailable_weapons(self) -> str:
        stored = self.automation["Stored"]
        current_weapons = as_list(self.inventory.get("Weapons"))
        stored_weapons = as_list(stored.get("confiscatedWeapons"))
        for item in current_weapons:
            if item not in stored_weapons:
                stored_weapons.append(item)
        stored["confiscatedWeapons"] = stored_weapons
        self.inventory["Weapons"] = []
        self.automation_flags["weaponsAvailable"] = False
        return f"weapons stored: {format_list(stored_weapons)}"

    def restore_unavailable_weapons(self) -> str:
        stored = self.automation["Stored"]
        stored_weapons = as_list(stored.pop("confiscatedWeapons", []))
        current_weapons = as_list(self.inventory.get("Weapons"))
        for item in stored_weapons:
            if item not in current_weapons:
                current_weapons.append(item)
        self.inventory["Weapons"] = current_weapons
        self.automation_flags["weaponsAvailable"] = True
        return f"weapons restored: {format_list(stored_weapons)}"

    def store_unavailable_backpack_items(self) -> str:
        stored = self.automation["Stored"]
        current_backpack = as_list(self.inventory.get("BackpackItems"))
        stored_backpack = as_list(stored.get("stashedBackpackItems"))
        if current_backpack:
            stored_backpack.extend(current_backpack)
        stored["stashedBackpackItems"] = stored_backpack
        self.inventory["BackpackItems"] = []
        self.automation_flags["backpackAvailable"] = False
        self.automation_flags["backpackItemsAvailable"] = False
        return f"backpack stashed: {len(stored_backpack)} Backpack Item(s)"

    def restore_unavailable_backpack_items(self) -> str:
        stored = self.automation["Stored"]
        stored_backpack = as_list(stored.pop("stashedBackpackItems", []))
        current_backpack = as_list(self.inventory.get("BackpackItems"))
        self.inventory["BackpackItems"] = stored_backpack + current_backpack
        self.automation_flags["backpackAvailable"] = True
        self.automation_flags["backpackItemsAvailable"] = True
        return f"backpack restored: {len(stored_backpack)} Backpack Item(s)"

    def discard_backpack(self) -> str:
        discarded = as_list(self.inventory.get("BackpackItems"))
        self.inventory["BackpackItems"] = []
        self.inventory["HasBackpack"] = False
        self.automation_flags["backpackAvailable"] = False
        self.automation_flags["backpackItemsAvailable"] = False
        return f"backpack discarded: {len(discarded)} Backpack Item(s) removed"

    def set_backpack_available(self, available: bool) -> str:
        self.inventory["HasBackpack"] = bool(available)
        self.automation_flags["backpackAvailable"] = bool(available)
        self.automation_flags["backpackItemsAvailable"] = bool(available)
        return f"backpackAvailable={bool(available)}"

    def discard_weapons(self) -> str:
        count = len(as_list(self.inventory.get("Weapons")))
        self.inventory["Weapons"] = []
        self.automation_flags["weaponsAvailable"] = False
        return f"weapons discarded: {count}"

    def clear_backpack_items(self) -> str:
        count = len(as_list(self.inventory.get("BackpackItems")))
        self.inventory["BackpackItems"] = []
        return f"Backpack Items discarded: {count}"

    def discard_gear(self) -> str:
        weapon_count = len(as_list(self.inventory.get("Weapons")))
        backpack_count = len(as_list(self.inventory.get("BackpackItems")))
        self.inventory["Weapons"] = []
        self.inventory["BackpackItems"] = []
        self.inventory["HasBackpack"] = False
        self.automation_flags["weaponsAvailable"] = False
        self.automation_flags["backpackAvailable"] = False
        self.automation_flags["backpackItemsAvailable"] = False
        return f"gear discarded: {weapon_count} Weapon(s); {backpack_count} Backpack Item(s)"

    def clear_special_items(self) -> str:
        count = len(as_list(self.inventory.get("SpecialItems")))
        self.inventory["SpecialItems"] = []
        return f"Special Items discarded: {count}"

    def start_book5_blood_poisoning(self) -> str:
        self.automation_flags["book5BloodPoisoningActive"] = True
        self.automation["Stored"]["book5BloodPoisoningStartedVisit"] = self.current_visit_key()
        return "book5BloodPoisoningActive=True"

    def restore_sommerswerd_if_book5_lost(self) -> str:
        if not bool(self.automation_flags.get("book5SommerswerdLost")):
            return "Sommerswerd recovery not needed"
        if not self.has_item("Sommerswerd", ["special"], "exact"):
            self.inventory["SpecialItems"] = add_unique_item(
                self.inventory.get("SpecialItems"), "Sommerswerd"
            )
        self.automation_flags["book5SommerswerdLost"] = False
        return "Sommerswerd recovered"

    def complete_book5_kai_master_training(self) -> str:
        completed = {int(item) for item in as_list(self.character.get("CompletedBooks"))}
        disciplines = clean_kai_disciplines(self.character.get("KaiDisciplines"))
        missing = [item for item in KAI_DISCIPLINES if item not in disciplines]
        if {1, 2, 3, 4}.issubset(completed) and len(missing) == 1:
            disciplines.append(missing[0])
            self.character["KaiDisciplines"] = disciplines
            self.automation_flags["book5KaiMaster"] = True
            return f"Kai Master: learned {missing[0]}"
        if len(missing) == 0:
            self.automation_flags["book5KaiMaster"] = True
            return "Kai Master already recorded"
        return "Kai Master upgrade deferred"

    def remove_chainmail_waistcoat(self) -> str:
        removed = self.remove_inventory_items("Chainmail Waistcoat", 1, ["special"])
        before_max = int(self.character["EnduranceMax"])
        before_current = int(self.character["EnduranceCurrent"])
        if removed and bool(self.character.get("Book2Setup", {}).get("ChainmailApplied")):
            self.character["EnduranceMax"] = max(0, before_max - 4)
            self.character["EnduranceCurrent"] = min(
                before_current, int(self.character["EnduranceMax"])
            )
            self.character.setdefault("Book2Setup", {})["ChainmailApplied"] = False
            return (
                "removed Chainmail Waistcoat; "
                f"END max {before_max}->{self.character['EnduranceMax']}"
            )
        return f"removed {removed} Chainmail Waistcoat"

    def has_available_staff(self) -> bool:
        return False

    def available_combat_weapons(self, include_jewelled_dagger: bool = True) -> list[str]:
        weapons: list[str] = []
        for item in as_list(self.inventory.get("Weapons")):
            name = str(item)
            if name not in weapons:
                weapons.append(name)
        special_weapon_items = {
            "sommerswerd": "Sommerswerd",
            "magic spear": "Magic Spear",
            "bone sword": "Bone Sword",
        }
        for item in as_list(self.inventory.get("SpecialItems")):
            key = str(item).strip().lower()
            name = special_weapon_items.get(key)
            if name and name not in weapons:
                weapons.append(name)
        return weapons

    def default_combat_weapon(self) -> str:
        weapons = self.available_combat_weapons(include_jewelled_dagger=False)
        if "Sommerswerd" in weapons:
            return "Sommerswerd"
        return weapons[0] if weapons else ""

    def preferred_combat_weapon(self) -> str:
        previous = str(self.settings.get("PreferredCombatWeapon") or "").strip()
        if previous and previous in self.available_combat_weapons(include_jewelled_dagger=False):
            return previous
        return self.default_combat_weapon()

    def remember_combat_weapon(self, weapon: str) -> None:
        value = str(weapon or "").strip()
        if value:
            self.settings["PreferredCombatWeapon"] = value

    def resolve_combat_weapon(self, weapon: str) -> str | None:
        value = str(weapon or "").strip()
        if not value or value.lower() in {"none", "unarmed"}:
            return ""
        choices = self.available_combat_weapons()
        exact = [item for item in choices if item.lower() == value.lower()]
        if exact:
            return exact[0]
        prefix = [item for item in choices if item.lower().startswith(value.lower())]
        if len(prefix) == 1:
            return prefix[0]
        return None

    def combat_active_weapon(self) -> str:
        if bool(self.combat.get("ForceUnarmed")):
            self.combat["ActiveWeapon"] = ""
            self.combat["UseStaff"] = False
            return ""
        active = str(self.combat.get("ActiveWeapon") or "").strip()
        if active in self.available_combat_weapons():
            return active
        fallback = self.default_combat_weapon()
        self.combat["ActiveWeapon"] = fallback
        if fallback != "Wizard's Staff":
            self.combat["UseStaff"] = False
        return fallback

    def set_combat_weapon(self, weapon: str, *, save: bool = True) -> bool:
        resolved = self.resolve_combat_weapon(weapon)
        if resolved is None:
            print(f"Combat weapon not available: {weapon}")
            return False
        self.combat["ForceUnarmed"] = False
        self.combat["ActiveWeapon"] = resolved
        self.combat["UseStaff"] = False
        self.remember_combat_weapon(resolved)
        if save:
            self.autosave()
            print(f"Combat weapon: {resolved or 'Unarmed'}")
        return True

    def combat_uses_magical_staff(self) -> bool:
        return False

    def combat_weapon_modifier_and_notes(self) -> tuple[int, list[str]]:
        active = self.combat_active_weapon()
        if not active:
            return -4, ["No weapon: -4 CS"]

        modifier = 0
        notes = [f"Weapon: {active}"]
        active_key = active.lower()
        weaponskill_weapon = str(self.character.get("WeaponskillWeapon") or "").lower()
        if active_key == "sommerswerd":
            sword_skills = {"sword", "short sword", "broadsword"}
            bonus = 10 if "Weaponskill" in as_list(self.character.get("KaiDisciplines")) and weaponskill_weapon in sword_skills else 8
            modifier += bonus
            notes.append(f"Sommerswerd: +{bonus} CS")
        elif active_key == "magic spear":
            if "Weaponskill" in as_list(self.character.get("KaiDisciplines")) and weaponskill_weapon == "spear":
                modifier += 2
                notes.append("Weaponskill (Spear): +2 CS")
        elif active_key == "bone sword":
            if int(self.character.get("BookNumber") or 0) == 3:
                modifier += 1
                notes.append("Bone Sword: +1 CS in Kalte")
        elif (
            "Weaponskill" in as_list(self.character.get("KaiDisciplines"))
            and active_key == weaponskill_weapon
        ):
            modifier += 2
            notes.append(f"Weaponskill ({active}): +2 CS")
        if self.has_item("Shield", ["special"]):
            modifier += 2
            notes.append("Shield: +2 CS")
        if "Mindblast" in as_list(self.character.get("KaiDisciplines")) and not bool(self.combat.get("EnemyImmune")):
            modifier += 2
            notes.append("Mindblast: +2 CS")
        return modifier, notes

    def change_endurance(self, delta: int) -> str:
        before = int(self.character["EnduranceCurrent"])
        next_value = before + int(delta)
        if delta > 0:
            next_value = min(next_value, int(self.character["EnduranceMax"]))
        self.character["EnduranceCurrent"] = max(0, next_value)
        after = int(self.character["EnduranceCurrent"])
        return f"END {before}->{after}"

    def change_willpower(self, delta: int, allow_negative: bool = False) -> str:
        before = int(self.character["WillpowerCurrent"])
        next_value = before + int(delta)
        if not allow_negative:
            next_value = max(0, next_value)
        self.character["WillpowerCurrent"] = next_value
        return f"WP {before}->{next_value}"

    def change_gold_crowns(self, delta: int) -> str:
        before = int(self.inventory.get("GoldCrowns") or 0)
        self.inventory["GoldCrowns"] = max(0, min(50, before + int(delta)))
        self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])
        return f"Gold Crowns {before}->{self.inventory['GoldCrowns']}"

    def change_nobles(self, delta: int) -> str:
        return self.change_gold_crowns(delta)

    def apply_automation_stat(self, action: dict[str, Any]) -> str:
        stat = str(action.get("stat") or "").lower()
        mode = str(action.get("mode") or "delta").lower()
        if stat in {"wp", "willpower"}:
            before = int(self.character["WillpowerCurrent"])
            if mode == "set":
                self.character["WillpowerCurrent"] = int(action.get("value") or 0)
                return f"WP {before}->{self.character['WillpowerCurrent']}"
            if mode == "half_recover_floor":
                gain = before // 2
                self.character["WillpowerCurrent"] = before + gain
                return f"WP {before}->{self.character['WillpowerCurrent']}"
            return self.change_willpower(
                int(action.get("delta") or 0), bool(action.get("allowNegative"))
            )
        if stat in {"end", "endurance"}:
            if mode == "set":
                before = int(self.character["EnduranceCurrent"])
                value = max(0, min(int(action.get("value") or 0), int(self.character["EnduranceMax"])))
                self.character["EnduranceCurrent"] = value
                return f"END {before}->{value}"
            if mode in {"restore_max", "restoremax", "full_recover"}:
                before = int(self.character["EnduranceCurrent"])
                self.character["EnduranceCurrent"] = int(self.character["EnduranceMax"])
                return f"END {before}->{self.character['EnduranceCurrent']}"
            if mode == "half_recover_floor":
                gain = int(self.character["EnduranceCurrent"]) // 2
                return self.change_endurance(gain)
            if mode == "restore_missing_half_floor":
                missing = max(0, int(self.character["EnduranceMax"]) - int(self.character["EnduranceCurrent"]))
                return self.change_endurance(missing // 2)
            if mode == "restore_combat_loss_half_floor":
                loss = self.combat_player_loss_for_book(int(self.character["BookNumber"]))
                message = self.change_endurance(loss // 2)
                return f"{message}; combat END loss {loss}"
            if mode == "half_loss_floor":
                loss = int(self.character["EnduranceCurrent"]) // 2
                return self.change_endurance(-loss)
            return self.change_endurance(int(action.get("delta") or 0))
        if stat in {"cs", "combat_skill", "combat skill"}:
            before = int(self.character["CombatSkillCurrent"])
            if mode == "set":
                self.character["CombatSkillCurrent"] = int(action.get("value") or 0)
            else:
                self.character["CombatSkillCurrent"] = before + int(action.get("delta") or 0)
            if bool(action.get("permanent")):
                self.character["CombatSkillBase"] = int(self.character["CombatSkillBase"]) + (
                    self.character["CombatSkillCurrent"] - before
                )
            return f"CS {before}->{self.character['CombatSkillCurrent']}"
        if stat in {"gold", "goldcrowns", "crowns", "nobles"}:
            before = int(self.inventory.get("GoldCrowns") or 0)
            if action.get("storeAs"):
                self.automation["Stored"][str(action["storeAs"])] = before
            if mode == "set":
                self.inventory["GoldCrowns"] = max(0, min(50, int(action.get("value") or 0)))
                self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])
                return f"Gold Crowns {before}->{self.inventory['GoldCrowns']}"
            return self.change_gold_crowns(int(action.get("delta") or 0))
        return "unknown stat action"

    def apply_automation_meal(self, action: dict[str, Any]) -> str:
        suppressed_flags = [
            str(flag)
            for flag in as_list(action.get("huntingSuppressedFlags"))
            if str(flag).strip()
        ]
        hunting_suppressed = bool(action.get("huntingSuppressed")) or any(
            bool(self.automation_flags.get(flag)) for flag in suppressed_flags
        )
        if bool(action.get("huntingExempt")) and self.has_power("Hunting") and not hunting_suppressed:
            available = self.count_items("Meal", ["backpack"])
            return f"Hunting: no Meal needed; Meals unchanged at {available}"
        count = max(0, int(action.get("count") or 1))
        mode = str(action.get("mode") or "per_missing")
        available = self.count_items("Meal", ["backpack"])

        if mode == "all_or_loss":
            laumspur_available = self.count_items("Laumspur", ["backpack"])
            if available + laumspur_available >= count:
                meals_removed = self.remove_inventory_items("Meal", min(count, available), ["backpack"])
                laumspur_needed = count - meals_removed
                laumspur_removed = self.remove_inventory_items(
                    "Laumspur", laumspur_needed, ["backpack"]
                )
                parts = []
                if meals_removed:
                    parts.append(f"Meals {available}->{available - meals_removed}")
                if laumspur_removed:
                    parts.append(
                        f"Laumspur {laumspur_available}->{laumspur_available - laumspur_removed}"
                    )
                    parts.append(self.change_endurance(3 * laumspur_removed))
                return "; ".join(parts) if parts else f"Meals {available}->{available}"
            loss = int(action.get("enduranceLoss") or 0)
            return f"missing {count} Meals; {self.change_endurance(-loss)}"

        removed = self.remove_inventory_items("Meal", min(count, available), ["backpack"])
        missing = max(0, count - removed)
        parts = [f"Meals {available}->{available - removed}"]
        if missing:
            loss = int(action.get("enduranceLossPerMissing") or action.get("enduranceLoss") or 0)
            parts.append(self.change_endurance(-(loss * missing)))
        return "; ".join(parts)

    def apply_automation_meal_or_gold(self, action: dict[str, Any]) -> str:
        meal_count = max(1, int(action.get("count") or 1))
        gold_cost = max(0, int(action.get("goldCost") or 0))
        available = self.count_items("Meal", ["backpack"])
        if available >= meal_count:
            removed = self.remove_inventory_items("Meal", meal_count, ["backpack"])
            return f"Meals {available}->{available - removed}"
        before_gold = int(self.inventory.get("GoldCrowns") or 0)
        if before_gold >= gold_cost:
            return self.change_gold_crowns(-gold_cost)
        loss = int(action.get("enduranceLoss") or 0)
        if loss:
            return f"no Meal or Gold; {self.change_endurance(-loss)}"
        return f"no Meal or Gold available; follow the book route"

    def apply_automation_action(self, action: dict[str, Any]) -> str:
        if isinstance(action.get("condition"), dict) and not self.evaluate_flow_condition(action.get("condition")):
            return ""
        action_type = str(action.get("type") or "").lower()
        if action_type == "stat":
            return self.apply_automation_stat(action)
        if action_type == "meal":
            return self.apply_automation_meal(action)
        if action_type == "meal_or_gold":
            return self.apply_automation_meal_or_gold(action)
        if action_type == "remove_item":
            name = str(action.get("name") or "")
            removed = self.remove_inventory_items(
                name,
                int(action.get("count") or 1),
                action.get("containers"),
                str(action.get("match") or "exact"),
            )
            return f"removed {removed} {name}"
        if action_type == "add_item":
            name = str(action.get("name") or "")
            container = str(action.get("container") or "backpack")
            if container == "herb_or_backpack":
                added = self.add_flexible_storage_item(name)
            else:
                added = self.add_inventory_item(container, name)
            if added:
                self.record_item_seen(name, container)
            return f"added {name}" if added else f"could not add {name}"
        if action_type == "flag":
            key = str(action.get("key") or "")
            self.automation_flags[key] = action.get("value")
            return f"{key}={action.get('value')}"
        if action_type == "restore_stored_nobles":
            key = str(action.get("key") or "stolenGoldCrowns")
            stored = int(self.automation["Stored"].pop(key, 0) or 0)
            extra = int(action.get("extra") or 0)
            before = int(self.inventory.get("GoldCrowns") or 0)
            self.inventory["GoldCrowns"] = max(0, min(50, before + stored + extra))
            self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])
            return f"Gold Crowns {before}->{self.inventory['GoldCrowns']}"
        if action_type == "gear":
            available = bool(action.get("available"))
            if available:
                return self.restore_unavailable_gear()
            return self.store_unavailable_gear()
        if action_type == "weapons":
            available = bool(action.get("available"))
            if available:
                return self.restore_unavailable_weapons()
            return self.store_unavailable_weapons()
        if action_type == "backpack_stash":
            available = bool(action.get("available"))
            if available:
                return self.restore_unavailable_backpack_items()
            return self.store_unavailable_backpack_items()
        if action_type == "backpack":
            if bool(action.get("available", True)):
                return self.set_backpack_available(True)
            return self.discard_backpack()
        if action_type == "discard_weapons":
            return self.discard_weapons()
        if action_type == "discard_backpack_items":
            return self.clear_backpack_items()
        if action_type == "discard_gear":
            return self.discard_gear()
        if action_type == "discard_special_items":
            return self.clear_special_items()
        if action_type == "book5_limbdeath":
            return self.start_book5_blood_poisoning()
        if action_type == "restore_sommerswerd_if_lost":
            return self.restore_sommerswerd_if_book5_lost()
        if action_type == "book5_kai_master":
            return self.complete_book5_kai_master_training()
        if action_type == "remove_chainmail":
            return self.remove_chainmail_waistcoat()
        if action_type == "ending":
            ending = str(action.get("ending") or "death")
            book_number = int(self.character["BookNumber"])
            section = int(self.state["CurrentSection"])
            self.automation["Ending"] = {
                "BookNumber": book_number,
                "Section": section,
                "Type": ending,
            }
            if ending.lower() in {"death", "failure"}:
                cause = str(action.get("cause") or f"Section {section} is a terminal {ending}.")
                self.register_death(ending, cause)
            complete_book = action.get("completeBook")
            if complete_book is not None:
                completed = sorted(
                    {int(item) for item in as_list(self.character["CompletedBooks"])}
                    | {int(complete_book)}
                )
                self.character["CompletedBooks"] = completed
                if ending.lower() == "success":
                    self.ensure_book_completed(int(complete_book))
            return f"ending={ending}"
        return f"unknown automation action: {action_type}"

    def apply_flow_loot(self, option_id: str) -> None:
        flow = self.current_section_flow_entry() or {}
        options = [option for option in as_list(flow.get("loot")) if isinstance(option, dict)]
        option = next((item for item in options if str(item.get("id") or "") == option_id), None)
        if option is None:
            print("Loot option not found for this section.")
            return
        if self.is_flow_loot_applied(option):
            print(f"Loot already taken: {option.get('label') or option_id}")
            return
        messages = []
        for action in as_list(option.get("actions")):
            if isinstance(action, dict):
                message = self.apply_automation_action(action)
                if message:
                    messages.append(message)
        if not messages:
            print("Loot option has no actions.")
            return
        succeeded = any(
            not message.startswith("could not ")
            and not message.startswith("unknown automation action")
            for message in messages
        )
        if not succeeded:
            print(f"Loot not applied: {option.get('label') or option_id}")
            for message in messages:
                print(message)
            return
        if not bool(option.get("repeatable")):
            applied = as_list(self.automation.get("AppliedLoot"))
            applied.append(self.flow_loot_key(option_id))
            self.automation["AppliedLoot"] = applied[-500:]
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "loot",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "VisitKey": self.current_visit_key(),
                "BookNumber": int(self.character["BookNumber"]),
                "Section": int(self.state["CurrentSection"]),
                "Summary": str(option.get("label") or option_id),
                "Messages": messages,
            }
        )
        self.automation["Journal"] = journal[-100:]
        self.autosave()
        print(f"Loot: {option.get('label') or option_id}")
        for message in messages:
            print(message)

    def flow_loot_options(self) -> list[dict[str, Any]]:
        return [
            option
            for option in self.current_flow_loot_payload()
            if isinstance(option, dict) and bool(option.get("Ready"))
        ]

    def show_loot_screen(self) -> None:
        options = self.flow_loot_options()
        panel_header("Section Loot", accent=SCREEN_ACCENTS["loot"])
        panel_pair_row(
            "Book",
            f"{self.character['BookNumber']}. {book_title(int(self.character['BookNumber']))}",
            "Section",
            self.state["CurrentSection"],
            left_color="White",
            right_color="White",
        )
        panel_row("Inventory", self.inventory_capacity_line(), label_width=12)
        if not options:
            panel_text("No audited loot options are recorded for this section.", color="DarkGray")
        else:
            for index, option in enumerate(options, 1):
                option_id = str(option.get("id") or index)
                label = str(option.get("label") or option_id)
                panel_row(f"{index}. {option_id}", label, label_width=18, value_color="White")
        panel_footer()
        self.show_helpful_commands("loot")

    def resolve_loot_selection(self, selection: str) -> dict[str, Any] | None:
        text = str(selection or "").strip()
        options = self.flow_loot_options()
        if not text:
            return None
        if text.isdigit():
            index = int(text) - 1
            if 0 <= index < len(options):
                return options[index]
        exact = [option for option in options if str(option.get("id") or "").lower() == text.lower()]
        if exact:
            return exact[0]
        prefix = [
            option
            for option in options
            if str(option.get("id") or "").lower().startswith(text.lower())
            or str(option.get("label") or "").lower().startswith(text.lower())
        ]
        if len(prefix) == 1:
            return prefix[0]
        return None

    def loot_command(self, tokens: list[str]) -> None:
        options = self.flow_loot_options()
        if not options:
            self.show_loot_screen()
            return

        if len(tokens) >= 2:
            selection = rest_of_line(tokens, 1).strip()
            if selection.lower() == "all":
                for option in options:
                    self.apply_flow_loot(str(option.get("id") or ""))
                return
            option = self.resolve_loot_selection(selection)
            if not option:
                write_warn(f"Loot option not found: {selection}")
                self.show_loot_screen()
                return
            self.apply_flow_loot(str(option.get("id") or ""))
            return

        while True:
            self.show_loot_screen()
            raw = input("Loot choice [0 done, D drop, all]: ").strip()
            if not raw or raw == "0":
                write_info("Loot picker closed.")
                return
            if raw.lower() == "d":
                self.interactive_drop_item()
                continue
            if raw.lower() == "all":
                for option in options:
                    self.apply_flow_loot(str(option.get("id") or ""))
                return
            option = self.resolve_loot_selection(raw)
            if not option:
                write_warn("Choose a listed number, D to drop, all, or 0 when you are done.")
                continue
            self.apply_flow_loot(str(option.get("id") or ""))
            return

    def show_choices_screen(self) -> None:
        flow = self.current_section_flow_payload()
        routes = [route for route in as_list(flow.get("SourceRoutes")) if isinstance(route, dict)]
        entry = flow.get("Entry") if isinstance(flow.get("Entry"), dict) else {}
        panel_header("Section Choices", accent=SCREEN_ACCENTS["choices"])
        panel_pair_row(
            "Book",
            f"{self.character['BookNumber']}. {book_title(int(self.character['BookNumber']))}",
            "Section",
            self.state["CurrentSection"],
            left_color="White",
            right_color="White",
        )
        if not routes:
            panel_text("No section routes were found in the local book HTML.", color="DarkGray")
        else:
            for index, route in enumerate(routes, 1):
                target = route.get("Section")
                label = str(route.get("Label") or f"Go to {target}")
                panel_row(f"{index}. {target}", label, label_width=10, value_color="White")
        panel_footer()

        route_checks = [check for check in as_list(flow.get("RouteChecks")) if isinstance(check, dict)]
        if route_checks:
            panel_header("Route Checks", accent="Cyan")
            for check in route_checks:
                label = str(check.get("Label") or "Route check")
                if not bool(check.get("Ready", True)):
                    panel_row("Wait", f"{label}: {check.get('BlockedReason')}", label_width=12, value_color="Yellow")
                    continue
                value = check.get("Value")
                formula = str(check.get("Formula") or check.get("Summary") or "")
                panel_row("Check", f"{label}: {formula} = {value}", label_width=12, value_color="White")
                matched = check.get("MatchedOutcome") if isinstance(check.get("MatchedOutcome"), dict) else {}
                if matched:
                    route = matched.get("Route")
                    route_text = f" -> section {route}" if route else ""
                    panel_row("Result", f"{matched.get('Test')}: {matched.get('Label')}{route_text}", label_width=12, value_color="White")
            panel_footer()

        if isinstance(entry.get("roll"), dict):
            roll = entry.get("roll") or {}
            panel_header("Roll Helper", accent="Magenta")
            panel_row("Summary", roll.get("summary", "Roll 0-9"), label_width=12)
            last_roll = flow.get("LastRoll")
            if isinstance(last_roll, dict):
                route = last_roll.get("Route")
                panel_pair_row("Last Raw", last_roll.get("Raw"), "Total", last_roll.get("Total"))
                panel_row("Outcome", last_roll.get("Outcome") or "None", label_width=12)
                if route:
                    panel_row("Route", f"section {route}", label_width=12, value_color="White")
            panel_footer()

        combat_entries = self.flow_combat_entries()
        if combat_entries:
            panel_header("Combat Presets", accent=SCREEN_ACCENTS["combat"])
            for index, preset in enumerate(combat_entries, 1):
                enemies = [enemy for enemy in as_list(preset.get("enemies") or preset.get("enemy")) if isinstance(enemy, dict)]
                first = enemies[0] if enemies else {}
                label = str(preset.get("label") or first.get("name") or preset.get("id") or f"Combat {index}")
                stats = ""
                if first:
                    stats = f"CS {first.get('cs', '?')} END {first.get('endurance', first.get('end', '?'))}"
                panel_row(f"{index}. {preset.get('id', '')}", f"{label} {stats}".strip(), label_width=18, value_color="White")
            panel_footer()

        healing = flow.get("Healing") if isinstance(flow.get("Healing"), dict) else {}
        if bool(healing.get("Available")):
            panel_header("Kai Healing", accent="Green")
            status = "ready" if healing.get("Ready") else ("applied" if healing.get("Applied") else "wait")
            detail = healing.get("Summary") if healing.get("Ready") else healing.get("BlockedReason")
            panel_row(status, detail or "Healing not available.", label_width=12)
            panel_footer()

        loss_choices = [choice for choice in as_list(flow.get("LossChoices")) if isinstance(choice, dict)]
        if loss_choices:
            panel_header("Choose Inventory Change", accent=SCREEN_ACCENTS["inventory"])
            for choice in loss_choices:
                label = str(choice.get("Label") or choice.get("Id") or "Loss choice")
                replacement = choice.get("Replacement") if isinstance(choice.get("Replacement"), dict) else {}
                replacement_name = str(replacement.get("Name") or "")
                if not bool(choice.get("Ready")):
                    panel_row("Wait", f"{label}: {choice.get('BlockedReason')}", label_width=12)
                    continue
                panel_row("Choice", f"{label}: {choice.get('Summary')}", label_width=12)
                for candidate in as_list(choice.get("Candidates")):
                    if isinstance(candidate, dict):
                        item_type = str(candidate.get("Type") or "")
                        detail = str(candidate.get("Item") or "")
                        if replacement_name:
                            detail = f"{detail} -> {replacement_name}"
                        panel_row(
                            f"{item_type} {candidate.get('Slot')}",
                            detail,
                            label_width=14,
                        )
            panel_footer()

        if self.flow_loot_options():
            self.show_loot_screen()
        else:
            self.show_helpful_commands("choices")

    def show_death_screen(self) -> None:
        death = self.death_recovery_payload()
        if not bool(death.get("Active")):
            panel_header("Death", accent=SCREEN_ACCENTS["death"])
            panel_text("No active death or failed mission is waiting for recovery.", color="DarkGray")
            panel_footer()
            self.show_helpful_commands("sheet")
            return

        cause = str(death.get("Cause") or "A fatal choice ended this path.")
        panel_header(str(death.get("Type") or "Death"), accent=SCREEN_ACCENTS["death"])
        panel_pair_row("Character", death.get("CharacterName", self.character.get("Name")), "Book / Section", f"{death.get('BookNumber')} / {death.get('Section')}", left_color="White", right_color="Gray")
        panel_pair_row("Endurance", f"{death.get('EnduranceCurrent')} / {death.get('EnduranceMax')}", "Gold Crowns", death.get("GoldCrowns", 0), left_color=endurance_color(death.get("EnduranceCurrent"), death.get("EnduranceMax")), right_color="Yellow")
        panel_row("Cause", cause, label_width=12)
        panel_footer()

        panel_header("Recovery", accent="DarkYellow")
        repeat = death.get("RepeatTarget") if isinstance(death.get("RepeatTarget"), dict) else None
        rewind = death.get("RewindTarget") if isinstance(death.get("RewindTarget"), dict) else None
        if bool(death.get("CanRepeat")) and repeat:
            panel_row("repeat", f"retry Book {repeat.get('BookNumber')}, section {repeat.get('Section')}", label_width=12, value_color="Green")
        else:
            panel_row("repeat", "not available for this death", label_width=12, value_color="DarkGray")
        if bool(death.get("CanRewind")) and rewind:
            panel_row("rewind", f"return to Book {rewind.get('BookNumber')}, section {rewind.get('Section')}", label_width=12, value_color="Yellow")
        else:
            panel_row("rewind", "no previous checkpoint", label_width=12, value_color="DarkGray")
        panel_text("Repeat restores the state from when this section was ready. Rewind returns to the previous section checkpoint.", color="Gray")
        panel_footer()
        self.show_helpful_commands("death")

    def consumable_item_effect(self, item: str) -> dict[str, Any] | None:
        text = str(item).lower()
        if "senara potion" in text:
            return {"stat": "wp", "delta": 5, "label": "Senara Potion"}
        if "senara bud" in text:
            return {"stat": "wp", "delta": 1, "label": "Senara Bud"}
        if "karmo potion" in text:
            return {"stat": "karmo", "label": "Karmo Potion", "addEmptyVial": True}
        if "potion of healing" in text or "healing potion" in text:
            return {"stat": "end", "delta": 4, "label": "Potion of Healing"}
        if "rendalim" in text:
            return {"stat": "end", "delta": 6, "label": "Potion of Rendalim's Elixir"}
        if "potion of invulnerability" in text:
            return {
                "stat": "flag",
                "key": "invulnerabilityActive",
                "value": True,
                "label": "Potion of Invulnerability",
                "addEmptyVial": True,
            }
        if "potion of alether" in text or "alether" in text:
            delta = 4 if "+4" in text or "distilled" in text else 2
            return {"stat": "cs", "delta": delta, "label": "Potion of Alether"}
        if "baknar oil" in text:
            return {
                "stat": "flag",
                "key": "baknarOilApplied",
                "value": True,
                "label": "Baknar Oil",
            }
        if "tarama seed" in text:
            return {
                "stat": "flag",
                "key": "taramaSeedReady",
                "value": True,
                "label": "Tarama Seed",
            }
        if "laumspur" in text:
            if "red" in text:
                return {"stat": "end", "delta": 4, "label": "Red Laumspur", "curesBloodPoisoning": True}
            if "small" in text:
                return {"stat": "end", "delta": 2, "label": "Small Vial of Laumspur", "curesBloodPoisoning": True}
            if "+6" in text:
                return {"stat": "end", "delta": 6, "label": "Potion of Laumspur", "curesBloodPoisoning": True}
            if "+5" in text or "potent" in text:
                return {"stat": "end", "delta": 5, "label": "Potent Laumspur Potion", "curesBloodPoisoning": True}
            if "+4" in text:
                return {"stat": "end", "delta": 4, "label": "Potion of Laumspur", "curesBloodPoisoning": True}
            if "potion" in text:
                return {"stat": "end", "delta": 3, "label": "Potion of Laumspur", "curesBloodPoisoning": True}
            return {"stat": "end", "delta": 3, "label": "Laumspur", "curesBloodPoisoning": True}
        if "oede" in text:
            return {"stat": "end", "delta": 10, "label": "Oede Herb", "curesBloodPoisoning": True}
        return None

    def use_item(self, item_type: str, item: str) -> None:
        mapping = {
            "backpack": "BackpackItems",
        }
        resolved_type = self.resolve_inventory_type(item_type) or str(item_type).lower()
        key = mapping.get(resolved_type)
        if not key:
            print("Only Backpack consumables can be used here.")
            return

        index, resolved_item = self.resolve_inventory_selection(key, item)
        if index is None or resolved_item is None:
            print(f"Item not found: {item}")
            return

        effect = self.consumable_item_effect(resolved_item)
        if not effect:
            print(f"No configured use action for: {resolved_item}")
            return

        if effect["stat"] == "karmo" and bool(self.automation_flags.get("karmoPotionActive")):
            print("Karmo Potion is already active. Finish the current Karmo effect before using another.")
            return

        items = as_list(self.inventory[key])
        items.pop(index)
        self.inventory[key] = items

        if effect["stat"] == "end":
            message = self.change_endurance(int(effect["delta"]))
        elif effect["stat"] == "wp":
            message = self.change_willpower(int(effect["delta"]), allow_negative=False)
        elif effect["stat"] == "cs":
            before = int(self.character["CombatSkillCurrent"])
            self.character["CombatSkillCurrent"] = before + int(effect["delta"])
            message = f"CS {before}->{self.character['CombatSkillCurrent']}"
        elif effect["stat"] == "flag":
            key_name = str(effect.get("key") or "")
            self.automation_flags[key_name] = effect.get("value", True)
            if effect.get("addEmptyVial"):
                self.add_flexible_storage_item("Empty Vial")
            message = f"{key_name}={effect.get('value', True)}"
        elif effect["stat"] == "karmo":
            before_end = int(self.character["EnduranceCurrent"])
            before_wp = int(self.character["WillpowerCurrent"])
            self.character["EnduranceCurrent"] = max(0, before_end * 2)
            self.character["WillpowerCurrent"] = before_wp * 2
            self.automation_flags["karmoPotionActive"] = True
            self.automation_flags["karmoSideEffectPending"] = True
            self.automation_flags["karmoSideEffectApplied"] = False
            self.automation["Stored"]["karmoPotionUse"] = {
                "EnduranceBefore": before_end,
                "WillpowerBefore": before_wp,
                "UsedAtBook": int(self.character["BookNumber"]),
                "UsedAtSection": int(self.state["CurrentSection"]),
            }
            if effect.get("addEmptyVial"):
                self.add_flexible_storage_item("Empty Vial")
            message = (
                f"END {before_end}->{self.character['EnduranceCurrent']}; "
                f"WP {before_wp}->{self.character['WillpowerCurrent']}; "
                "apply the section 45 side-effect roll before or after finishing Karmo"
            )
        else:
            message = "unknown effect"
        if effect.get("curesBloodPoisoning") and bool(
            self.automation_flags.get("book5BloodPoisoningActive")
        ):
            self.automation_flags["book5BloodPoisoningActive"] = False
            message = f"{message}; Limbdeath/blood poisoning cured"
        self.autosave()
        print(f"Used {effect['label']}: {message}")

    def apply_karmo_side_effect(self, raw_roll: int | None = None) -> None:
        if not bool(self.automation_flags.get("karmoSideEffectPending")):
            print("No pending Karmo side effect.")
            return
        if raw_roll is None:
            last_roll = self.automation.get("LastRoll")
            if not isinstance(last_roll, dict) or int(last_roll.get("BookNumber") or 0) != 2 or int(last_roll.get("Section") or 0) != 45:
                print("Roll section 45 first, then apply the Karmo side effect.")
                return
            raw_roll = int(last_roll.get("Raw") or 0)
        raw_roll = max(0, min(9, int(raw_roll)))
        message = self.change_endurance(-raw_roll)
        self.automation_flags["karmoSideEffectPending"] = False
        self.automation_flags["karmoSideEffectApplied"] = True
        self.automation["Stored"]["karmoSideEffectRoll"] = raw_roll
        self.autosave()
        print(f"Karmo side effect: roll {raw_roll}; {message}")

    def finish_karmo_potion(self) -> None:
        if not bool(self.automation_flags.get("karmoPotionActive")):
            print("Karmo Potion is not active.")
            return
        before_end = int(self.character["EnduranceCurrent"])
        before_wp = int(self.character["WillpowerCurrent"])
        self.character["EnduranceCurrent"] = max(0, before_end // 2)
        self.character["WillpowerCurrent"] = before_wp // 2
        self.automation_flags["karmoPotionActive"] = False
        self.autosave()
        print(
            "Karmo finished: "
            f"END {before_end}->{self.character['EnduranceCurrent']}; "
            f"WP {before_wp}->{self.character['WillpowerCurrent']}"
        )

    def use_item_command(self, tokens: list[str]) -> None:
        if len(tokens) < 2:
            panel_header("Use Item", accent=SCREEN_ACCENTS["inventory"])
            panel_text("Use consumables from the Backpack. Enter a numbered slot or item name.", color="Gray")
            panel_footer()
            self.show_inventory_slots("Backpack", self.inventory["BackpackItems"], 8)
            item_type = input("Container [backpack]: ").strip() or "backpack"
            item = input("Slot or item to use: ").strip()
            if not item:
                write_info("Use cancelled.")
                return
            self.use_item(item_type, item)
            return

        if len(tokens) >= 3 and self.resolve_inventory_type(tokens[1]) in {"backpack"}:
            self.use_item(tokens[1], rest_of_line(tokens, 2))
            return

        # Convenience: "use 2" means Backpack slot 2, and "use laumspur" searches the Backpack first.
        selection = rest_of_line(tokens, 1)
        backpack_index, backpack_item = self.resolve_inventory_selection("BackpackItems", selection)
        if backpack_index is not None and backpack_item is not None:
            self.use_item("backpack", selection)
            return
        print(f"Item not found: {selection}")

    def set_status_flag(self, key: str, value: Any) -> None:
        if isinstance(value, str):
            value = value.strip().lower()
            if value in {"true", "yes", "on", "1"}:
                value = True
            elif value in {"false", "no", "off", "0"}:
                value = False
        self.automation_flags[key] = value
        self.autosave()
        print(f"{key}={value}")

    def pay_willpower_cost(self, cost: int, mode: str = "negative") -> None:
        cost = max(0, int(cost))
        before_wp = int(self.character["WillpowerCurrent"])
        before_end = int(self.character["EnduranceCurrent"])
        if mode == "endurance_for_missing":
            spendable = min(max(before_wp, 0), cost)
            missing = cost - spendable
            self.character["WillpowerCurrent"] = before_wp - spendable
            self.character["EnduranceCurrent"] = max(0, before_end - (missing * 2))
            print(
                f"WP cost {cost}: WP {before_wp}->{self.character['WillpowerCurrent']}; "
                f"END {before_end}->{self.character['EnduranceCurrent']}"
            )
        else:
            self.character["WillpowerCurrent"] = before_wp - cost
            print(f"WP cost {cost}: WP {before_wp}->{self.character['WillpowerCurrent']}")
        self.autosave()

    def apply_section_automation(
        self, *, force: bool = False, visit_changed: bool = True
    ) -> list[str]:
        if not bool(self.automation.get("Enabled", True)):
            return []
        if not force and not visit_changed:
            return []

        book_number = int(self.character["BookNumber"])
        section = int(self.state["CurrentSection"])
        entry = self.section_automation_entry(book_number, section)
        if not entry:
            return []

        visit_key = self.current_visit_key()
        applied = as_list(self.automation.get("AppliedVisitEffects"))
        if visit_key in applied:
            messages = [f"Section {section} automation already applied for this visit."]
            status = self.current_section_automation_payload()
            summary = status.get("Summary")
            if summary:
                messages.append(f"Automation: {summary}")
            for message in as_list(status.get("Messages")):
                messages.append(f"Previous result: {message}")
            return messages

        messages: list[str] = []
        flow_entry = self.section_flow_entry(book_number, section) or {}
        manual_wp_cost = isinstance(flow_entry.get("wpCost"), dict)
        for action in as_list(entry.get("actions")):
            if isinstance(action, dict):
                if (
                    manual_wp_cost
                    and str(action.get("type") or "").lower() == "stat"
                    and str(action.get("stat") or "").lower() in {"wp", "willpower"}
                    and int(action.get("delta") or 0) < 0
                ):
                    messages.append("WP cost awaits section choice")
                    continue
                message = self.apply_automation_action(action)
                if message:
                    messages.append(message)

        if not messages:
            return []

        applied.append(visit_key)
        self.automation["AppliedVisitEffects"] = applied[-500:]
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "section",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "VisitKey": visit_key,
                "BookNumber": book_number,
                "Section": section,
                "Summary": entry.get("summary", ""),
                "Messages": messages,
            }
        )
        self.automation["Journal"] = journal[-100:]
        return [f"Automation: {entry.get('summary', f'Section {section} effects')}"] + messages

    def apply_current_section_automation(self) -> None:
        messages = self.apply_section_automation(force=True, visit_changed=True)
        if messages:
            for message in messages:
                print(message)
            self.write_current_position()
            self.autosave()
            return
        print("No simple automation for this section.")

    def apply_global_section_effects(self, *, visit_changed: bool) -> list[str]:
        if not visit_changed or not bool(self.automation.get("Enabled", True)):
            return []
        book_number = int(self.character.get("BookNumber") or 1)
        if book_number != 5 or not bool(self.automation_flags.get("book5BloodPoisoningActive")):
            return []

        visit_key = self.current_visit_key()
        start_key = str(self.automation["Stored"].get("book5BloodPoisoningStartedVisit") or "")
        applied_key = f"{visit_key}:global:book5BloodPoisoning"
        applied = as_list(self.automation.get("AppliedVisitEffects"))
        if visit_key == start_key or applied_key in applied:
            return []

        message = self.change_endurance(-2)
        applied.append(applied_key)
        self.automation["AppliedVisitEffects"] = applied[-500:]
        journal = as_list(self.automation.get("Journal"))
        journal.append(
            {
                "Kind": "section",
                "AppliedAt": datetime.now().isoformat(timespec="seconds"),
                "VisitKey": visit_key,
                "BookNumber": book_number,
                "Section": int(self.state["CurrentSection"]),
                "Summary": "Limbdeath blood poisoning",
                "Messages": [message],
            }
        )
        self.automation["Journal"] = journal[-100:]
        messages = [f"Automation: Limbdeath blood poisoning", message]
        if int(self.character["EnduranceCurrent"]) <= 0:
            self.register_death("failure", "Limbdeath blood poisoning ended the mission.")
        return messages

    def catalog_saves(self) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        for path in sorted(self.save_dir.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            entry: dict[str, Any] = {
                "Path": path,
                "Name": path.stem,
                "BookNumber": "?",
                "BookTitle": "",
                "Section": "?",
                "Endurance": "?",
                "GoldCrowns": "?",
                "Modified": datetime.fromtimestamp(path.stat().st_mtime).strftime("%Y-%m-%d %H:%M"),
            }
            try:
                with path.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                character = data.get("Character", {})
                inventory = data.get("Inventory", {})
                book_number = int(character.get("BookNumber", 1))
                entry.update(
                    {
                        "Name": character.get("Name") or path.stem,
                        "BookNumber": book_number,
                        "BookTitle": book_title(book_number),
                        "Section": int(data.get("CurrentSection", 1)),
                        "Endurance": f"{character.get('EnduranceCurrent', '?')}/{character.get('EnduranceMax', '?')}",
                        "GoldCrowns": inventory.get("GoldCrowns", inventory.get("Nobles", "?")),
                    }
                )
            except Exception:
                entry["BookTitle"] = "Unreadable save"
            entries.append(entry)
        return entries

    def show_banner(self) -> None:
        panel_header("Lone Wolf Action Assistant Redux", accent="Cyan")
        panel_pair_row("Rules", "Lone Wolf Kai", "Engine", "Python")
        panel_pair_row("Books", "Book 1", "Saves", str(self.save_dir))
        panel_footer()

    def show_helpful_commands(self, screen: str = "sheet") -> None:
        rows_by_screen = {
            "welcome": [
                ("load", "open save catalog"),
                ("new", "create Lone Wolf"),
                ("sheet", "show action chart"),
                ("help", "show commands"),
            ],
            "sheet": [
                ("section <n>", "advance current section"),
                ("choices", "show book links from this section"),
                ("loot", "open section loot picker"),
                ("inv", "inventory screen"),
                ("disciplines", "Kai Disciplines"),
            ],
            "inventory": [
                ("add <type> <item>", "add an item"),
                ("drop", "remove by numbered slot"),
                ("use", "use a Backpack item"),
                ("meal", "consume one Meal"),
            ],
            "disciplines": [
                ("new", "choose Disciplines at character creation"),
                ("complete", "use the book completion flow for the next Discipline"),
                ("combat", "combat status"),
                ("sheet", "return to action chart"),
            ],
            "sections": [
                ("section <n>", "set current section"),
                ("book <n> <sec>", "set book and section"),
                ("choices", "show available routes"),
                ("history", "recent section path"),
            ],
            "load": [
                ("load <number>", "load save by list number"),
                ("load <path>", "load save by path"),
                ("new", "create character"),
                ("quit", "exit"),
            ],
            "combat": [
                ("combat round [roll]", "resolve a round"),
                ("combat evade [roll]", "evade one round"),
                ("combat weapon <name>", "change active weapon"),
                ("combat stop", "end combat tracking"),
            ],
            "death": [
                ("repeat", "retry the section from entry-ready state"),
                ("rewind", "return to the previous section"),
                ("load", "open save catalog"),
                ("new", "start over"),
            ],
            "loot": [
                ("loot <number>", "take a listed loot option"),
                ("loot all", "apply every listed option"),
                ("drop", "make room by slot"),
                ("inv", "review inventory"),
            ],
            "choices": [
                ("section <n>", "go to the numbered section"),
                ("go <n>", "same as section <n>"),
                ("roll", "roll 0-9 when the text asks"),
                ("sheet", "return to action chart"),
            ],
        }
        rows = rows_by_screen.get(screen, rows_by_screen["sheet"])
        panel_header("Helpful Commands", accent="DarkYellow")
        for label, value in rows:
            panel_row(label, value, label_width=20, label_color="DarkYellow")
        panel_footer()

    def show_welcome_screen(self) -> None:
        self.show_banner()
        panel_header("Welcome", accent="Cyan")
        panel_pair_row("load", "open a save", "new", "create character", label_width=8)
        panel_pair_row("sheet", "action chart", "help", "commands", label_width=8)
        panel_footer()

        panel_header("Quick Start", accent="DarkYellow")
        panel_text("1. Load a save or create a new Lone Wolf character.")
        panel_text("2. Use sheet, inv, disciplines, sections, notes, stats, and campaign to review state.")
        panel_text("3. Use section <n> as you read. Web book links also update this state.")
        panel_footer()
        self.show_helpful_commands("welcome")

    def show_load_screen(self) -> list[dict[str, Any]]:
        entries = self.catalog_saves()
        panel_header("Save Catalog", accent="Cyan")
        if not entries:
            panel_text(f"No saves found in {self.save_dir}.")
        else:
            for index, entry in enumerate(entries, 1):
                panel_row(
                    f"{index}. {entry['Name']}",
                    f"Book {entry['BookNumber']} sec {entry['Section']} | END {entry['Endurance']} | Gold {entry['GoldCrowns']}",
                    label_width=20,
                )
                panel_row("Modified", entry["Modified"], label_width=20)
        panel_footer()
        self.show_helpful_commands("load")
        return entries

    def resolve_load_selection(self, path_text: str, entries: list[dict[str, Any]] | None = None) -> Path | None:
        selection = path_text.strip().strip('"')
        if not selection:
            return None
        if selection.isdigit():
            catalog = entries if entries is not None else self.catalog_saves()
            index = int(selection)
            if 1 <= index <= len(catalog):
                return Path(catalog[index - 1]["Path"])
        path = Path(selection)
        return path if path.is_absolute() else self.save_dir / path

    def resolve_save_path(self, path_text: str = "") -> Path:
        if path_text.strip():
            path = Path(path_text.strip().strip('"'))
            return path if path.is_absolute() else self.save_dir / path
        current = str(self.settings.get("SavePath", "")).strip()
        if current:
            return Path(current)
        name = safe_file_name(f"{self.character['Name']}-book{self.character['BookNumber']}")
        return self.save_dir / f"{name}.json"

    def save_game(self, path_text: str = "", quiet: bool = False) -> bool:
        path = self.resolve_save_path(path_text)
        path.parent.mkdir(parents=True, exist_ok=True)
        self.settings["SavePath"] = str(path)
        self.sync_achievements(save=False)
        # Autosave fires after every combat round and section change, so write to
        # a sibling temp file and atomically replace the target. An interrupted
        # write then leaves the previous save intact instead of a truncated,
        # unloadable file.
        temp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}")
        try:
            with temp_path.open("w", encoding="utf-8") as handle:
                json.dump(self.state, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temp_path, path)
        finally:
            if temp_path.exists():
                temp_path.unlink(missing_ok=True)
        self.last_save_file.write_text(str(path), encoding="utf-8")
        self.write_current_position()
        if not quiet:
            print(f"Saved: {path}")
        return True

    def load_game(self, path_text: str = "", quiet: bool = False) -> bool:
        if path_text.strip():
            path = self.resolve_load_selection(path_text)
            if path is None:
                print(f"Save not found: {path_text}")
                return False
        elif quiet and self.last_save_file.exists():
            path = Path(self.last_save_file.read_text(encoding="utf-8").strip())
        else:
            catalog = self.show_load_screen()
            if not catalog:
                return False
            selection = input("Load save number or path [1]: ").strip() or "1"
            path = self.resolve_load_selection(selection, catalog)
            if path is None:
                print(f"Save not found: {selection}")
                return False

        if not path.exists():
            print(f"Save not found: {path}")
            return False

        try:
            with path.open("r", encoding="utf-8") as handle:
                loaded = json.load(handle)
        except (OSError, json.JSONDecodeError) as exc:
            print(f"Could not read save (file may be corrupt): {path} ({exc})")
            return False
        self.state = normalize_state(loaded)
        self.settings["SavePath"] = str(path)
        repair_messages = self.repair_loaded_combat_routes()
        self.last_save_file.write_text(str(path), encoding="utf-8")
        self.record_section_visit()
        self.ensure_current_section_checkpoint()
        self.sync_achievements(save=False)
        self.write_current_position()
        if repair_messages:
            self.save_game(quiet=True)
        if not quiet:
            print(f"Loaded: {path}")
            for message in repair_messages:
                print(f"Save repair: {message}")
            self.show_sheet()
        return True

    def autosave(self) -> None:
        self.settings["AutoSave"] = True
        self.save_game(quiet=True)

    def select_powers(
        self,
        available: list[str],
        target_count: int,
        existing: list[str] | None = None,
        label: str = "power",
    ) -> list[str]:
        target_count = min(target_count, len(available))
        result: list[str] = []
        for item in existing or []:
            if item in available and item not in result:
                result.append(item)

        while len(result) < target_count:
            remaining = [item for item in available if item not in result]
            print("")
            print(f"Choose {label} {len(result) + 1} of {target_count}:")
            for index, item in enumerate(remaining, 1):
                print(f"  {index}. {item}")
            choice = read_int("Selection", 1, 1, len(remaining))
            selected = remaining[choice - 1]
            if selected not in result:
                result.append(selected)
        return result

    def resolve_power_name(self, name: str, kind: str = "Any") -> str | None:
        pool = list(KAI_DISCIPLINES)

        exact = [item for item in pool if item.lower() == name.lower()]
        if len(exact) == 1:
            return exact[0]
        prefix = [item for item in pool if item.lower().startswith(name.lower())]
        if len(prefix) == 1:
            return prefix[0]
        return None

    def ensure_herb_pouch(self) -> None:
        self.inventory["HasHerbPouch"] = False
        self.inventory["HerbPouchItems"] = []

    def add_special_item(self, item: str) -> None:
        if item not in as_list(self.inventory["SpecialItems"]):
            self.inventory["SpecialItems"] = as_list(self.inventory["SpecialItems"]) + [item]

    def start_new_game(self) -> None:
        print("")
        print("New Lone Wolf Book 1 character")

        name = input("Name [Lone Wolf]: ").strip()
        disciplines = self.select_powers(KAI_DISCIPLINES, 5, label="Kai Discipline")
        self.state = create_book1_character_state(
            name=name or "Lone Wolf",
            kai_disciplines=disciplines,
        )
        self.record_section_visit()
        self.write_current_position()
        self.save_section_checkpoint("ready")
        rolls = self.character.get("CreationRolls", {})
        print(
            f"Rolled CS {self.character['CombatSkillCurrent']}. "
            f"END {self.character['EnduranceCurrent']}. "
            f"Gold Crowns {self.inventory['GoldCrowns']}."
        )
        if self.character.get("WeaponskillWeapon"):
            print(
                f"Weaponskill roll: {rolls.get('Weaponskill')} -> "
                f"{self.character['WeaponskillWeapon']}"
            )
        print(
            f"Starting equipment roll: {rolls.get('StartingFind')} -> "
            f"{rolls.get('StartingFindName')}"
        )
        self.show_sheet()

    def show_help(self) -> None:
        panels = [
            (
                "Navigation",
                [
                    ("sheet", "main action chart and live state"),
                    ("inv", "inventory slots and containers"),
                    ("disciplines", "Kai Disciplines"),
                    ("sections", "current section and path history"),
                    ("choices", "current section links, roll help, combat presets, and loot"),
                    ("notes", "saved reminders"),
                    ("stats", "current-book numbers"),
                    ("campaign", "whole-run overview"),
                    ("history", "recent sections and combat"),
                    ("death", "active death and recovery options"),
                ],
            ),
            (
                "Play And Inventory",
                [
                    ("section <n>", "move to the section you are reading"),
                    ("book <n> [section]", "set current book, optionally section"),
                    ("roll", "roll a random digit, 0-9"),
                    ("end/cs/gold +/-n", "adjust Endurance, Combat Skill, or Gold Crowns"),
                    ("meal / meal missed", "consume a Meal or take starvation loss"),
                    ("add / drop", "add items or remove them by name/slot"),
                    ("use <item|slot>", "use Backpack consumables"),
                    ("loot [number|all]", "apply audited loot in the current section"),
                    ("gold +/-n", "adjust Gold Crowns"),
                    ("note <text>", "add a short reminder"),
                ],
            ),
            (
                "Combat",
                [
                    ("combat start <name> <cs> <end>", "start tracked combat"),
                    ("combat round [roll]", "resolve a combat round"),
                    ("combat evade [roll]", "resolve one evasion round"),
                    ("combat weapon <name>", "choose the active weapon"),
                    ("combat mod <n>", "temporary Combat Skill modifier"),
                    ("combat status|stop", "review or stop current combat"),
                ],
            ),
            (
                "Run",
                [
                    ("new", "create a new Lone Wolf character"),
                    ("load [number|path]", "open save catalog or load directly"),
                    ("save [path]", "write current save"),
                    ("complete", "finish current book and transition"),
                    ("repeat", "after death, retry the failed section"),
                    ("rewind", "after death, restore the previous section"),
                    ("autosave", "write the current always-on autosave"),
                    ("quit", "leave the app"),
                ],
            ),
        ]
        for title, rows in panels:
            panel_header(title, accent=SCREEN_ACCENTS.get(title.lower(), "Cyan"))
            for label, value in rows:
                panel_row(label, value, label_width=24)
            panel_footer()
        self.show_helpful_commands("welcome")

    def show_sheet(self) -> None:
        book = BOOKS.get(int(self.character["BookNumber"]), BOOKS[1])
        self.show_banner()
        panel_header("Action Chart", accent=SCREEN_ACCENTS["sheet"])
        panel_row("Name", self.character["Name"])
        panel_pair_row("Book", f"{self.character['BookNumber']}. {book['Title']}", "Section", self.state["CurrentSection"])
        panel_pair_row("Combat Skill", f"{self.character['CombatSkillCurrent']} (base {self.character['CombatSkillBase']})", "Endurance", f"{self.character['EnduranceCurrent']}/{self.character['EnduranceMax']}", left_color="Cyan", right_color=endurance_color(self.character["EnduranceCurrent"], self.character["EnduranceMax"]))
        panel_pair_row("Gold Crowns", self.inventory.get("GoldCrowns", 0), "Meals", as_list(self.inventory["BackpackItems"]).count("Meal"), left_color="Yellow", right_color="DarkYellow")
        panel_pair_row("Completed", format_list(self.character["CompletedBooks"]), "Autosave", "On")
        if str(self.settings.get("SavePath", "")).strip():
            panel_row("Save", self.settings["SavePath"])
        panel_footer()

        panel_header("Kai Disciplines", accent=SCREEN_ACCENTS["disciplines"])
        panel_row("Known", format_list(self.character["KaiDisciplines"]))
        rank_count, rank_name = kai_rank_for_disciplines(self.character.get("KaiDisciplines"))
        panel_row("Kai Rank", f"{rank_name} ({rank_count} disciplines)")
        if self.character.get("WeaponskillWeapon"):
            panel_row("Weaponskill", self.character["WeaponskillWeapon"])
        panel_footer()

        panel_header("Inventory Summary", accent=SCREEN_ACCENTS["inventory"])
        backpack_status = (
            "unavailable"
            if not bool(self.automation_flags.get("backpackAvailable", True))
            else capacity_text(self.inventory["BackpackItems"], 8)
        )
        panel_pair_row("Weapons", capacity_text(self.inventory["Weapons"], 2), "Backpack", backpack_status)
        panel_pair_row("Special Items", str(len(as_list(self.inventory["SpecialItems"]))), "Gold Crowns", self.inventory.get("GoldCrowns", 0))
        panel_row("Ready Weapon", as_list(self.inventory["Weapons"])[0] if as_list(self.inventory["Weapons"]) else "None")
        panel_footer()
        self.show_helpful_commands("sheet")

    def show_inventory_screen(self) -> None:
        panel_header("Inventory", accent=SCREEN_ACCENTS["inventory"])
        panel_pair_row("Gold Crowns", self.inventory.get("GoldCrowns", 0), "Weapons", capacity_text(self.inventory["Weapons"], 2))
        panel_pair_row("Backpack", capacity_text(self.inventory["BackpackItems"], 8), "Special Items", str(len(as_list(self.inventory["SpecialItems"]))))
        panel_row("Meals", as_list(self.inventory["BackpackItems"]).count("Meal"))
        panel_footer()
        self.show_inventory_slots("Weapons", self.inventory["Weapons"], 2)
        self.show_inventory_slots("Backpack", self.inventory["BackpackItems"], 8)
        self.show_inventory_slots("Special Items", self.inventory["SpecialItems"], None)
        self.show_stored_gear()
        self.show_helpful_commands("inventory")

    def show_stored_gear(self) -> None:
        stored = self.automation["Stored"]
        equipment = stored.get("confiscatedEquipment")
        if not isinstance(equipment, dict):
            equipment = {}
        weapons = as_list(equipment.get("Weapons"))
        backpack = as_list(equipment.get("BackpackItems")) or as_list(
            stored.get("confiscatedBackpackItems")
        )
        special = as_list(equipment.get("SpecialItems"))
        gold = int(equipment.get("GoldCrowns") or 0)
        safekeeping = as_list(stored.get("safekeepingSpecialItems"))
        raw_records = stored.get("safekeepingRecords")
        safekeeping_records = raw_records if isinstance(raw_records, list) else []
        safekeeping_places = []
        for record in safekeeping_records:
            if not isinstance(record, dict):
                continue
            item = str(record.get("Item") or "").strip()
            place = str(record.get("Place") or "Safekeeping").strip()
            if item:
                safekeeping_places.append(f"{item} at {place}")
        gear_unavailable = (
            not bool(self.automation_flags.get("weaponsAvailable", True))
            or not bool(self.automation_flags.get("backpackAvailable", True))
            or not bool(self.automation_flags.get("backpackItemsAvailable", True))
            or not bool(self.automation_flags.get("specialItemsAvailable", True))
        )
        if not gear_unavailable and not weapons and not backpack and not special and not gold and not safekeeping:
            return
        panel_header("Stored Gear", accent="DarkYellow")
        panel_row("Status", "unavailable" if gear_unavailable else "recorded")
        panel_row("Weapons", format_list(weapons))
        panel_row("Backpack Items", format_list(backpack))
        panel_row("Special Items", format_list(special))
        panel_row("Gold Crowns", gold)
        panel_row("Safekeeping", format_list(safekeeping))
        if safekeeping_places:
            panel_row("Places", format_list(safekeeping_places))
        panel_footer()

    def show_inventory_slots(self, title: str, items: Any, capacity: int | None) -> None:
        values = as_list(items)
        suffix = f" {len(values)}/{capacity}" if capacity else f" {len(values)}"
        accent = "DarkYellow" if title in {"Weapons", "Backpack", "Special Items"} else "Magenta"
        panel_header(title + suffix, accent=accent)
        slot_count = capacity if capacity is not None else max(len(values), 1)
        for index in range(slot_count):
            value = values[index] if index < len(values) else "(empty)"
            panel_row(str(index + 1), value, label_width=4)
        panel_footer()

    def show_powers(self) -> None:
        self.show_disciplines_screen()

    def show_disciplines_screen(self) -> None:
        known = as_list(self.character.get("KaiDisciplines"))
        rank_count, rank_name = kai_rank_for_disciplines(known)
        panel_header("Kai Disciplines", accent=SCREEN_ACCENTS["disciplines"])
        panel_row("Known", f"{len(known)}/5")
        panel_row("Kai Rank", f"{rank_name} ({rank_count} disciplines)")
        panel_row("Weaponskill", self.character.get("WeaponskillWeapon") or "None")
        panel_footer()

        panel_header("Discipline List", accent=SCREEN_ACCENTS["disciplines"])
        for name in KAI_DISCIPLINES:
            marker = "known" if name in known else "available"
            panel_row(name, marker, label_width=18)
        panel_footer()
        self.show_helpful_commands("disciplines")

    def show_sections_screen(self) -> None:
        book_number = int(self.character["BookNumber"])
        book = BOOKS.get(book_number, BOOKS[1])
        stats = self.state.get("CurrentBookStats", {})
        history = as_list(self.state.get("SectionHistory"))[-10:]
        panel_header("Sections", accent=SCREEN_ACCENTS["sections"])
        panel_pair_row("Book", f"{book_number}. {book['Title']}", "Current", self.state["CurrentSection"])
        panel_pair_row("Range", f"1-{book['MaxSection']}", "Unique Seen", stats.get("SectionsVisited", 0))
        panel_row("Start Section", stats.get("StartSection", self.state["CurrentSection"]))
        panel_footer()

        panel_header("Recent Path", accent="DarkYellow")
        if not history:
            panel_text("No section path recorded yet.")
        else:
            for item in history:
                panel_row(
                    f"Book {item.get('BookNumber', '?')}",
                    f"{item.get('BookTitle', '')} :: Section {item.get('Section', '?')}",
                    label_width=10,
                )
        panel_footer()
        self.show_helpful_commands("sections")

    def show_notes_screen(self) -> None:
        notes = as_list(self.character["Notes"])
        panel_header("Notes", accent=SCREEN_ACCENTS["notes"])
        if not notes:
            panel_text("No notes yet. Use note <text> to add one.")
        else:
            for index, note in enumerate(notes, 1):
                panel_row(str(index), note, label_width=4)
        panel_footer()
        panel_header("Summary", accent="DarkYellow")
        panel_row("Total Notes", len(notes))
        panel_footer()

    def show_stats_screen(self) -> None:
        stats = self.state.get("CurrentBookStats", {})
        combat_log = as_list(self.combat.get("Log"))
        panel_header("Current Book Stats", accent=SCREEN_ACCENTS["stats"])
        panel_row("Book", f"{stats.get('BookNumber', self.character['BookNumber'])}. {stats.get('BookTitle', book_title(int(self.character['BookNumber'])))}")
        panel_pair_row("Start Section", stats.get("StartSection", 1), "Last Section", stats.get("LastSection", self.state["CurrentSection"]))
        panel_pair_row("Unique Sections", stats.get("SectionsVisited", 0), "Combat Rounds", len(combat_log))
        panel_pair_row("END", f"{self.character['EnduranceCurrent']}/{self.character['EnduranceMax']}", "Gold Crowns", self.inventory.get("GoldCrowns", 0))
        panel_footer()
        self.show_helpful_commands("sheet")

    def show_campaign_screen(self) -> None:
        completed = [int(item) for item in as_list(self.character["CompletedBooks"]) if str(item).strip()]
        panel_header("Campaign", accent=SCREEN_ACCENTS["campaign"])
        for number in sorted(BOOKS):
            status = "current" if number == int(self.character["BookNumber"]) else ("complete" if number in completed else "not started")
            panel_row(f"Book {number}", f"{BOOKS[number]['Title']} :: {status}", label_width=10)
        panel_footer()
        panel_header("Run Summary", accent="DarkYellow")
        panel_pair_row("Completed", format_list(completed), "Current Section", self.state["CurrentSection"])
        panel_pair_row("Notes", len(as_list(self.character["Notes"])), "Recent Path", len(as_list(self.state.get("SectionHistory"))))
        panel_footer()

    def show_history_screen(self) -> None:
        self.show_sections_screen()
        log = as_list(self.combat.get("Log"))[-8:]
        panel_header("Recent Combat", accent=SCREEN_ACCENTS["combat"])
        if not log:
            panel_text("No combat rounds recorded in the active fight.")
        else:
            for entry in log:
                player_loss = entry.get("PlayerLoss", entry.get("LoneWolfReduxLoss", "?"))
                panel_row(
                    f"Roll {entry.get('Roll', '?')}",
                    f"Ratio {entry.get('Ratio', '?')} | enemy -{entry.get('EnemyLoss', '?')} | Lone Wolf -{player_loss}",
                    label_width=10,
                )
        panel_footer()

    def set_section(self, section: int) -> None:
        book = BOOKS.get(int(self.character["BookNumber"]), BOOKS[1])
        if section < 1 or section > book["MaxSection"]:
            print(f"Book {self.character['BookNumber']} sections are 1-{book['MaxSection']}.")
            return
        if self.death_active():
            self.clear_death_state()
            self.clear_terminal_death_marker()
        self.state["CurrentSection"] = section
        visit_changed = self.record_section_visit()
        checkpoint_needed = (
            visit_changed
            or not self.section_checkpoints()
            or self.section_checkpoints()[-1].get("Key") != self.current_visit_key()
        )
        if checkpoint_needed:
            self.save_section_checkpoint("entry")
        automation_messages = self.apply_section_automation(visit_changed=visit_changed)
        automation_messages.extend(self.apply_global_section_effects(visit_changed=visit_changed))
        if checkpoint_needed and not self.death_active():
            self.save_section_checkpoint("ready")
        self.write_current_position()
        self.autosave()
        print(f"Current section: {section}")
        for message in automation_messages:
            print(message)
        if self.death_active():
            self.show_death_screen()

    def set_book(self, book_number: int, section: int | None = None) -> None:
        book = BOOKS.get(book_number)
        if not book:
            print("Book must be 1-5.")
            return

        next_section = int(self.state["CurrentSection"]) if section is None else int(section)
        if next_section < 1 or next_section > book["MaxSection"]:
            next_section = 1

        self.character["BookNumber"] = book_number
        if self.death_active():
            self.clear_death_state()
            self.clear_terminal_death_marker()
        self.state["CurrentSection"] = next_section
        visit_changed = self.record_section_visit()
        checkpoint_needed = (
            visit_changed
            or not self.section_checkpoints()
            or self.section_checkpoints()[-1].get("Key") != self.current_visit_key()
        )
        if checkpoint_needed:
            self.save_section_checkpoint("entry")
        automation_messages = self.apply_section_automation(visit_changed=visit_changed)
        automation_messages.extend(self.apply_global_section_effects(visit_changed=visit_changed))
        if checkpoint_needed and not self.death_active():
            self.save_section_checkpoint("ready")
        self.write_current_position()
        self.autosave()
        print(f"Current book: {book_number}. {book['Title']}; section {next_section}")
        for message in automation_messages:
            print(message)
        if self.death_active():
            self.show_death_screen()

    def number_change(self, tokens: list[str]) -> tuple[str, int] | None:
        if len(tokens) < 2:
            return None
        if tokens[1].lower() == "set":
            if len(tokens) < 3:
                return None
            try:
                return "set", int(tokens[2])
            except ValueError:
                return None
        try:
            return "delta", int(tokens[1])
        except ValueError:
            return None

    def adjust_willpower(self, tokens: list[str]) -> None:
        change = self.number_change(tokens)
        if not change:
            print("Use: wp +/-n or wp set <n>")
            return
        mode, value = change
        self.character["WillpowerCurrent"] = value if mode == "set" else self.character["WillpowerCurrent"] + value
        self.autosave()
        print(f"Willpower: {self.character['WillpowerCurrent']}")

    def adjust_endurance(self, tokens: list[str]) -> None:
        change = self.number_change(tokens)
        if not change:
            print("Use: end +/-n or end set <n>")
            return
        mode, value = change
        if mode == "set":
            self.character["EnduranceCurrent"] = max(0, value)
        else:
            next_value = self.character["EnduranceCurrent"] + value
            if value > 0:
                next_value = min(next_value, self.character["EnduranceMax"])
            self.character["EnduranceCurrent"] = max(0, next_value)
        self.autosave()
        print(f"Endurance: {self.character['EnduranceCurrent']}/{self.character['EnduranceMax']}")

    def adjust_combat_skill(self, tokens: list[str]) -> None:
        change = self.number_change(tokens)
        if not change:
            print("Use: cs +/-n or cs set <n>")
            return
        mode, value = change
        self.character["CombatSkillCurrent"] = (
            value if mode == "set" else self.character["CombatSkillCurrent"] + value
        )
        self.autosave()
        print(f"Combat Skill: {self.character['CombatSkillCurrent']}")

    def adjust_nobles(self, tokens: list[str]) -> None:
        change = self.number_change(tokens)
        if not change:
            print("Use: gold +/-n or gold set <n>")
            return
        mode, value = change
        if mode == "set":
            self.inventory["GoldCrowns"] = max(0, min(50, value))
        else:
            self.inventory["GoldCrowns"] = max(0, min(50, int(self.inventory.get("GoldCrowns") or 0) + value))
        self.inventory["Nobles"] = int(self.inventory["GoldCrowns"])
        self.autosave()
        print(f"Gold Crowns: {self.inventory['GoldCrowns']}")

    def meal_command(self, tokens: list[str]) -> None:
        if len(tokens) > 1 and tokens[1].lower() == "missed":
            self.character["EnduranceCurrent"] = max(0, self.character["EnduranceCurrent"] - 3)
            self.autosave()
            print(
                f"Missed meal: -3 END. "
                f"Endurance: {self.character['EnduranceCurrent']}/{self.character['EnduranceMax']}"
            )
            return
        removed, items = remove_first_matching(self.inventory["BackpackItems"], "Meal")
        if not removed:
            print("No Meal in backpack. Use 'meal missed' if the book requires one.")
            return
        self.inventory["BackpackItems"] = items
        self.autosave()
        print(f"Consumed one Meal. Backpack: {format_list(items)}")

    def inventory_type_choices(self) -> dict[str, dict[str, Any]]:
        return {
            "weapon": {"key": "Weapons", "label": "Weapons", "capacity": 2},
            "backpack": {"key": "BackpackItems", "label": "Backpack", "capacity": 8},
            "special": {"key": "SpecialItems", "label": "Special Items", "capacity": None},
        }

    def resolve_inventory_type(self, value: str) -> str | None:
        text = str(value or "").strip().lower().replace("_", "").replace("-", "")
        aliases = {
            "w": "weapon",
            "weapon": "weapon",
            "weapons": "weapon",
            "b": "backpack",
            "bp": "backpack",
            "pack": "backpack",
            "backpack": "backpack",
            "backpackitems": "backpack",
            "s": "special",
            "special": "special",
            "specials": "special",
            "specialitems": "special",
        }
        return aliases.get(text)

    def inventory_type_spec(self, item_type: str) -> dict[str, Any] | None:
        resolved = self.resolve_inventory_type(item_type)
        if not resolved:
            return None
        return self.inventory_type_choices()[resolved]

    def inventory_type_from_key(self, key: str) -> str:
        reverse = {
            "Weapons": "weapon",
            "BackpackItems": "backpack",
            "SpecialItems": "special",
        }
        return reverse.get(key, "")

    def inventory_capacity_line(self) -> str:
        backpack = "unavailable" if not bool(self.automation_flags.get("backpackAvailable", True)) else capacity_text(self.inventory["BackpackItems"], 8)
        return (
            f"Weapons {capacity_text(self.inventory['Weapons'], 2)} | "
            f"Backpack {backpack} | "
            f"Special {len(as_list(self.inventory['SpecialItems']))}"
        )

    def resolve_inventory_selection(self, key: str, selection: str) -> tuple[int | None, str | None]:
        items = as_list(self.inventory.get(key))
        text = str(selection or "").strip()
        if not text:
            return None, None
        if text.isdigit():
            index = int(text) - 1
            if 0 <= index < len(items):
                return index, str(items[index])
            return None, None
        exact = [index for index, item in enumerate(items) if str(item).lower() == text.lower()]
        if exact:
            index = exact[0]
            return index, str(items[index])
        prefix = [index for index, item in enumerate(items) if str(item).lower().startswith(text.lower())]
        if len(prefix) == 1:
            index = prefix[0]
            return index, str(items[index])
        return None, None

    def remove_inventory_item_by_index(self, key: str, index: int) -> str | None:
        items = as_list(self.inventory.get(key))
        if index < 0 or index >= len(items):
            return None
        item = str(items.pop(index))
        self.inventory[key] = items
        return item

    def show_inventory_type_slots(self, item_type: str) -> None:
        spec = self.inventory_type_spec(item_type)
        if not spec:
            write_warn("Type must be weapon, backpack, or special.")
            return
        self.show_inventory_slots(str(spec["label"]), self.inventory.get(str(spec["key"])), spec.get("capacity"))

    def interactive_drop_item(self, item_type: str = "") -> None:
        resolved = self.resolve_inventory_type(item_type)
        if not resolved:
            panel_header("Drop Item", accent=SCREEN_ACCENTS["inventory"])
            panel_text("Choose a container to remove from.", color="Gray")
            for index, key in enumerate(["weapon", "backpack", "special"], 1):
                spec = self.inventory_type_choices()[key]
                panel_row(str(index), spec["label"], label_width=4)
            panel_footer()
            raw = input("Container (weapon/backpack/special): ").strip()
            resolved = self.resolve_inventory_type(raw)
        if not resolved:
            write_warn("Type must be weapon, backpack, or special.")
            return

        spec = self.inventory_type_choices()[resolved]
        key = str(spec["key"])
        self.show_inventory_type_slots(resolved)
        items = as_list(self.inventory.get(key))
        if not items:
            write_warn(f"No {spec['label']} items to remove.")
            return
        raw = input(f"{spec['label']} slot or item to drop [0 cancel]: ").strip()
        if raw in {"", "0"}:
            write_info("Drop cancelled.")
            return
        index, item = self.resolve_inventory_selection(key, raw)
        if index is None or item is None:
            write_warn("That item was not found.")
            return
        removed = self.remove_inventory_item_by_index(key, index)
        self.autosave()
        write_info(f"Dropped: {removed}")

    def add_item(self, tokens: list[str]) -> None:
        if len(tokens) < 3:
            print("Use: add <weapon|backpack|special> <item>")
            return
        item_type = tokens[1].lower()
        item = rest_of_line(tokens, 2)
        if item_type == "weapon":
            if len(as_list(self.inventory["Weapons"])) >= 2:
                print("Weapon limit is 2. Drop a weapon first.")
                return
            self.inventory["Weapons"] = as_list(self.inventory["Weapons"]) + [item]
        elif item_type == "backpack":
            if not bool(self.automation_flags.get("backpackAvailable", True)):
                print("Backpack is not currently available.")
                return
            if item_slot_total(self.inventory["BackpackItems"]) + item_slot_cost(item) > 8:
                print("Backpack limit is 8 items. Drop an item first.")
                return
            self.inventory["BackpackItems"] = as_list(self.inventory["BackpackItems"]) + [item]
        elif item_type == "special":
            self.inventory["SpecialItems"] = as_list(self.inventory["SpecialItems"]) + [item]
        else:
            print(f"Unknown item type: {item_type}")
            return
        self.autosave()
        print(f"Added: {item}")

    def drop_item(self, tokens: list[str]) -> None:
        if len(tokens) < 2:
            self.interactive_drop_item()
            return
        spec = self.inventory_type_spec(tokens[1])
        if not spec:
            print(f"Unknown item type: {tokens[1]}")
            return
        if len(tokens) < 3:
            self.interactive_drop_item(tokens[1])
            return
        key = str(spec["key"])
        selection = rest_of_line(tokens, 2)
        index, item = self.resolve_inventory_selection(key, selection)
        if index is None or item is None:
            print(f"Item not found: {selection}")
            return
        removed_item = self.remove_inventory_item_by_index(key, index)
        self.autosave()
        print(f"Dropped: {removed_item}")

    def power_command(self, tokens: list[str]) -> None:
        self.show_powers()
        print("Kai Disciplines can only be changed during character creation or a book transition.")

    def assign_missing_weaponskill_weapon(self, roll: Any | None = None, *, save: bool = True) -> bool:
        if "Weaponskill" not in as_list(self.character.get("KaiDisciplines")):
            print("Weaponskill is not one of your Kai Disciplines.")
            return False
        if str(self.character.get("WeaponskillWeapon") or "").strip():
            print(f"Weaponskill weapon already set: {self.character['WeaponskillWeapon']}")
            return False
        digit = coerce_random_digit(roll)
        weapon = weaponskill_weapon_for_roll(digit)
        self.character["WeaponskillWeapon"] = weapon
        self.character.setdefault("CreationRolls", {})["Weaponskill"] = digit
        if save:
            self.autosave()
        print(f"Weaponskill roll {digit}: {weapon}")
        return True

    def combat_round_count(self) -> int:
        return len(as_list(self.combat.get("Log")))

    def combat_effective_enemy_combat_skill(self) -> int:
        return int(self.combat["EnemyCombatSkill"])

    def combat_status_payload(self) -> dict[str, Any]:
        self.sync_active_combat_with_section_preset()
        payload = json.loads(json.dumps(self.combat))
        payload["PlayerEnduranceCurrent"] = int(self.character["EnduranceCurrent"])
        payload["PlayerEnduranceMax"] = int(self.character["EnduranceMax"])
        payload["PlayerEnduranceLabel"] = "END"
        payload["RoundCount"] = self.combat_round_count()
        payload["AvailableWeapons"] = self.available_combat_weapons()
        payload["ActiveWeapon"] = self.combat_active_weapon() if self.combat.get("Active") else self.default_combat_weapon()

        notes: list[str] = []
        if self.combat.get("Active"):
            player_cs = self.combat_skill_for_round()
            enemy_cs = self.combat_effective_enemy_combat_skill()
            payload["PlayerCombatSkill"] = player_cs
            payload["EnemyCombatSkillEffective"] = enemy_cs
            payload["CombatRatio"] = player_cs - enemy_cs
            if int(self.combat.get("Modifier") or 0):
                notes.append(f"Combat Skill modifier {int(self.combat['Modifier']):+d}")
            timed = self.combat_timed_modifier_for_round()
            if timed:
                notes.append(f"Timed modifier this round {timed:+d}")
            if bool(self.combat.get("EnemyImmune")):
                notes.append("Enemy immune to Mindblast")
            if self.combat.get("FixedPlayerCombatSkill") is not None:
                notes.append(f"Fixed combat skill {int(self.combat['FixedPlayerCombatSkill'])}")
            if int(self.combat.get("RoundLimit") or 0):
                notes.append(f"Round limit {int(self.combat['RoundLimit'])}")
            if bool(self.combat.get("IgnorePlayerLossIfEnemyLossGreater")):
                notes.append("Ignore Lone Wolf END loss when enemy loss is higher.")
            if int(self.combat.get("IgnorePlayerLossRounds") or 0):
                notes.append(f"Ignore Lone Wolf END loss for {int(self.combat['IgnorePlayerLossRounds'])} round(s)")
            if int(self.combat.get("IgnoreEnemyLossRounds") or 0):
                notes.append(f"Ignore enemy END loss for {int(self.combat['IgnoreEnemyLossRounds'])} round(s)")
            if isinstance(self.combat.get("CombatRollRoutes"), dict) and self.combat.get("CombatRollRoutes"):
                route_text = ", ".join(
                    f"{roll}->{route}" for roll, route in sorted(self.combat["CombatRollRoutes"].items())
                )
                notes.append(f"Combat roll route: {route_text}")
            if isinstance(self.combat.get("PlayerLossRandomCheck"), dict) and self.combat.get(
                "PlayerLossRandomCheck"
            ):
                notes.append(str(self.combat["PlayerLossRandomCheck"].get("summary") or "Special check after END loss."))
            if str(self.combat.get("RequiredWeapon") or "").strip():
                notes.append(f"Only {self.combat['RequiredWeapon']} can wound this enemy.")
            notes.extend(
                str(label)
                for label in as_list(self.combat.get("AppliedConditionalModifierLabels"))
                if str(label)
            )
            victory_choices = as_list(self.combat.get("VictoryChoices"))
            if victory_choices:
                notes.append(f"Victory choices: sections {', '.join(str(route) for route in victory_choices)}")
            _, weapon_notes = self.combat_weapon_modifier_and_notes()
            notes.extend(weapon_notes)
            if bool(self.combat.get("CanEvade")):
                after_rounds = int(self.combat.get("EvadeAfterRounds") or 0)
                notes.append("Evade available" if after_rounds <= 0 else f"Evade after round {after_rounds}")
        else:
            payload["PlayerCombatSkill"] = int(self.character["CombatSkillCurrent"])
            payload["EnemyCombatSkillEffective"] = int(self.combat.get("EnemyCombatSkill") or 0)
            payload["CombatRatio"] = None
        payload["CombatNotes"] = notes
        return payload

    def current_combat_archive_entry(self, outcome: str) -> dict[str, Any]:
        player_cs = self.combat_skill_for_round() if self.combat.get("Active") else int(
            self.character["CombatSkillCurrent"]
        )
        enemy_cs = self.combat_effective_enemy_combat_skill()
        return {
            "ResolvedAt": datetime.now().isoformat(timespec="seconds"),
            "Outcome": outcome,
            "BookNumber": int(self.character["BookNumber"]),
            "Section": int(self.combat.get("StartedSection") or self.state["CurrentSection"]),
            "EnemyName": self.combat.get("EnemyName", ""),
            "EnemyCombatSkill": int(self.combat.get("EnemyCombatSkill") or 0),
            "EnemyEnduranceMax": int(self.combat.get("EnemyEnduranceMax") or 0),
            "EnemyEnduranceCurrent": int(self.combat.get("EnemyEnduranceCurrent") or 0),
            "PlayerCombatSkill": player_cs,
            "CombatRatio": player_cs - enemy_cs,
            "ActiveWeapon": self.combat_active_weapon() or "Unarmed",
            "PlayerEnduranceCurrent": int(self.character["EnduranceCurrent"]),
            "PlayerEnduranceMax": int(self.character["EnduranceMax"]),
            "Rounds": as_list(self.combat.get("Log")),
            "RoundCount": self.combat_round_count(),
            "VictoryRoute": self.combat.get("VictoryRoute"),
            "EvadeRoute": self.combat.get("EvadeRoute"),
        }

    def archive_current_combat(self, outcome: str) -> None:
        if not self.combat.get("EnemyName"):
            return
        entry = self.current_combat_archive_entry(outcome)
        history = as_list(self.state.get("CombatHistory"))
        self.state["CombatHistory"] = (history + [entry])[-100:]
        self.combat["Outcome"] = outcome

    def combat_timed_modifier_for_round(self, round_number: int | None = None) -> int:
        round_number = round_number or (self.combat_round_count() + 1)
        total = 0
        for modifier in as_list(self.combat.get("TimedModifiers")):
            if not isinstance(modifier, dict):
                continue
            if isinstance(modifier.get("condition"), dict) and not self.evaluate_flow_condition(
                modifier.get("condition")
            ):
                continue
            start = int(modifier.get("startRound") or 1)
            end = int(modifier.get("endRound") or start)
            if start <= round_number <= end:
                total += int(modifier.get("modifier") or 0)
        return total

    def evaluated_combat_preset_modifier(self, preset: dict[str, Any]) -> tuple[int, list[str]]:
        total = int(preset.get("modifier") or 0)
        labels: list[str] = []
        for modifier in as_list(preset.get("conditionalModifiers")):
            if not isinstance(modifier, dict):
                continue
            if isinstance(modifier.get("condition"), dict) and not self.evaluate_flow_condition(
                modifier.get("condition")
            ):
                continue
            value = int(modifier.get("modifier") or 0)
            total += value
            label = str(modifier.get("label") or "Conditional modifier")
            labels.append(f"{label}: {value:+d} CS")
        return total, labels

    def combat_skill_for_round(self, round_number: int | None = None) -> int:
        self.sync_active_combat_with_section_preset()
        fixed = self.combat.get("FixedPlayerCombatSkill")
        if fixed is not None:
            return int(fixed) + int(self.combat.get("Modifier") or 0) + self.combat_timed_modifier_for_round(round_number)

        cs = (
            int(self.character["CombatSkillCurrent"])
            + int(self.combat.get("Modifier") or 0)
            + self.combat_timed_modifier_for_round(round_number)
        )
        weapon_modifier, _ = self.combat_weapon_modifier_and_notes()
        cs += weapon_modifier
        return cs

    def get_crt_result(self, ratio: int, roll: int) -> tuple[int, Any, Any]:
        if not self.crt:
            raise RuntimeError("Combat Results Table is not loaded.")
        columns = sorted(int(key) for key in self.crt.keys())
        if ratio < columns[0]:
            column = columns[0]
        elif ratio > columns[-1]:
            column = columns[-1]
        elif ratio in columns:
            column = ratio
        else:
            column = max(value for value in columns if value <= ratio)
        entry = self.crt[str(column)][str(roll)]
        return column, entry["EnemyLoss"], entry["PlayerLoss"]

    def loss_value(self, raw: Any, current: int) -> int:
        if str(raw) == "K":
            return current
        try:
            return int(raw)
        except (TypeError, ValueError):
            return 0

    def flow_combat_entries_for_entry(self, flow: dict[str, Any] | None) -> list[dict[str, Any]]:
        flow = flow or {}
        return [entry for entry in as_list(flow.get("combat")) if isinstance(entry, dict)]

    def flow_combat_entries(self) -> list[dict[str, Any]]:
        return self.flow_combat_entries_for_entry(self.current_section_flow_entry())

    def start_section_combat(self, combat_id: str = "") -> None:
        entries = self.flow_combat_entries()
        if combat_id:
            entries = [entry for entry in entries if str(entry.get("id") or "") == combat_id]
        if not entries:
            print("No section combat preset for this section.")
            return
        preset = entries[0]
        enemies = [enemy for enemy in as_list(preset.get("enemies") or preset.get("enemy")) if isinstance(enemy, dict)]
        if not enemies:
            print("Section combat preset has no enemy.")
            return

        messages: list[str] = []
        for action in as_list(preset.get("preActions")):
            if isinstance(action, dict):
                message = self.apply_automation_action(action)
                if message:
                    messages.append(message)

        first = enemies[0]
        name = str(first.get("name") or preset.get("name") or "Enemy")
        cs = int(first.get("cs") or preset.get("cs") or 10)
        endurance = int(first.get("endurance") or first.get("end") or preset.get("endurance") or 10)
        self.start_combat(["combat", "start", name, str(cs), str(endurance)])

        fixed_cs = preset.get("fixedPlayerCombatSkill")
        if fixed_cs == "wp_plus_end":
            fixed_cs = int(self.character["EnduranceCurrent"])
        elif fixed_cs == "current":
            fixed_cs = int(self.character["CombatSkillCurrent"])
        elif fixed_cs is not None:
            fixed_cs = int(fixed_cs)

        modifier, modifier_labels = self.evaluated_combat_preset_modifier(preset)
        oxygen_safe_rounds = 0
        if bool(preset.get("oxygenSafeRoundsFromRoll")):
            last_roll = self.automation.get("LastRoll")
            raw_roll = None
            if (
                isinstance(last_roll, dict)
                and int(last_roll.get("BookNumber") or 0) == int(self.character["BookNumber"])
                and int(last_roll.get("Section") or 0) == int(self.state["CurrentSection"])
            ):
                raw_roll = int(last_roll.get("Raw") or 0)
            else:
                raw_roll = random_digit()
                messages.append(f"Oxygen roll {raw_roll} used for underwater endurance.")
            oxygen_safe_rounds = 10 if raw_roll == 0 else raw_roll
            if self.has_power("Mind Over Matter"):
                oxygen_safe_rounds += int(preset.get("oxygenMindOverMatterBonus") or 2)
                messages.append("Mind Over Matter: +2 underwater rounds")
            messages.append(f"Underwater endurance: {oxygen_safe_rounds} combat round(s)")
        self.combat.update(
            {
                "Modifier": modifier,
                "UseStaff": False,
                "ForceUnarmed": bool(preset.get("forceUnarmed", False)),
                "EnemyImmune": bool(preset.get("enemyImmune", False)),
                "IgnorePlayerLossIfEnemyLossGreater": bool(
                    preset.get("ignorePlayerLossIfEnemyLossGreater", False)
                ),
                "CanEvade": bool(preset.get("canEvade", False)),
                "EvadeAfterRounds": max(0, int(preset.get("evadeAfterRounds") or 0)),
                "VictoryRoute": preset.get("victoryRoute"),
                "DefeatRoute": preset.get("defeatRoute"),
                "DefeatEnduranceMinimum": preset.get("defeatEnduranceMinimum"),
                "EvadeRoute": preset.get("evadeRoute"),
                "FlawlessVictoryRoute": preset.get("flawlessVictoryRoute"),
                "WoundedVictoryRoute": preset.get("woundedVictoryRoute"),
                "RoundLimit": max(0, int(preset.get("roundLimit") or 0)),
                "SurvivalRoute": preset.get("survivalRoute"),
                "RoundExceededRoute": preset.get("roundExceededRoute"),
                "PlayerLossRoute": preset.get("playerLossRoute"),
                "OneRoundComparisonRoutes": preset.get("oneRoundComparisonRoutes")
                if isinstance(preset.get("oneRoundComparisonRoutes"), dict)
                else {},
                "PlayerLossRandomCheck": preset.get("playerLossRandomCheck")
                if isinstance(preset.get("playerLossRandomCheck"), dict)
                else {},
                "OxygenSafeRounds": oxygen_safe_rounds,
                "WinWithinRounds": max(0, int(preset.get("winWithinRounds") or 0)),
                "WinWithinRoute": preset.get("winWithinRoute"),
                "TooLateRoute": preset.get("tooLateRoute"),
                "PostRoundWpThreshold": None,
                "PerRoundActions": as_list(preset.get("perRoundActions")),
                "TimedModifiers": as_list(preset.get("timedModifiers")),
                "AppliedConditionalModifierLabels": modifier_labels,
                "IgnorePlayerLossRounds": max(0, int(preset.get("ignorePlayerLossRounds") or 0)),
                "IgnoreEnemyLossRounds": max(0, int(preset.get("ignoreEnemyLossRounds") or 0)),
                "CombatRollRoutes": preset.get("combatRollRoutes")
                if isinstance(preset.get("combatRollRoutes"), dict)
                else {},
                "DoubleEnemyLoss": bool(preset.get("doubleEnemyLoss", False)),
                "DoubleEnemyLossWithSommerswerd": bool(preset.get("doubleEnemyLossWithSommerswerd", False)),
                "RestorePlayerEnduranceAfterCombat": bool(preset.get("restorePlayerEnduranceAfterCombat", False)),
                "RestoreHalfPlayerEnduranceLossAfterCombat": bool(
                    preset.get("restoreHalfPlayerEnduranceLossAfterCombat", False)
                ),
                "StoredPlayerEnduranceBeforeCombat": int(self.character["EnduranceCurrent"])
                if bool(preset.get("restorePlayerEnduranceAfterCombat", False))
                or bool(preset.get("restoreHalfPlayerEnduranceLossAfterCombat", False))
                else None,
                "FixedPlayerCombatSkill": fixed_cs,
                "RequiredWeapon": str(preset.get("requiredWeapon") or ""),
                "EnemyQueue": enemies,
                "EnemyIndex": 0,
                "SectionCombatId": str(preset.get("id") or ""),
                "VictoryChoices": as_list(preset.get("victoryChoices")),
                "AfterVictoryActions": as_list(preset.get("afterVictoryActions")),
            }
        )
        if fixed_cs is not None:
            self.combat["UseStaff"] = False
        if self.combat.get("ForceUnarmed"):
            self.combat["ActiveWeapon"] = ""
            self.combat["UseStaff"] = False
        elif preset.get("activeWeapon"):
            resolved_weapon = self.resolve_combat_weapon(str(preset.get("activeWeapon") or ""))
            if resolved_weapon is not None:
                self.combat["ActiveWeapon"] = resolved_weapon
                self.combat["UseStaff"] = False
        self.remember_combat_weapon(self.combat_active_weapon())
        for message in messages:
            print(message)
        print(f"Section combat loaded: {preset.get('label') or name}")
        self.autosave()

    def advance_enemy_queue(self) -> bool:
        queue = [enemy for enemy in as_list(self.combat.get("EnemyQueue")) if isinstance(enemy, dict)]
        index = int(self.combat.get("EnemyIndex") or 0) + 1
        if index >= len(queue):
            return False
        enemy = queue[index]
        self.combat["EnemyIndex"] = index
        self.combat["EnemyName"] = str(enemy.get("name") or f"Enemy {index + 1}")
        self.combat["EnemyCombatSkill"] = int(enemy.get("cs") or 10)
        enemy_end = int(enemy.get("endurance") or enemy.get("end") or 10)
        self.combat["EnemyEnduranceMax"] = enemy_end
        self.combat["EnemyEnduranceCurrent"] = enemy_end
        print(
            f"Next enemy: {self.combat['EnemyName']} "
            f"CS {self.combat['EnemyCombatSkill']} END {enemy_end}"
        )
        return True

    def apply_combat_per_round_actions(self) -> list[str]:
        messages: list[str] = []
        for action in as_list(self.combat.get("PerRoundActions")):
            if isinstance(action, dict):
                action_type = str(action.get("type") or "").lower()
                if action_type in {"combat_enemy_damage", "enemy_damage"}:
                    before = int(self.combat.get("EnemyEnduranceCurrent") or 0)
                    delta = int(action.get("delta") or 0)
                    after = max(0, before + delta)
                    self.combat["EnemyEnduranceCurrent"] = after
                    label = str(action.get("label") or "section effect")
                    messages.append(f"{label}: enemy END {before}->{after}")
                    continue
                message = self.apply_automation_action(action)
                if message:
                    messages.append(message)
        oxygen_safe_rounds = int(self.combat.get("OxygenSafeRounds") or 0)
        if oxygen_safe_rounds and self.combat_round_count() > oxygen_safe_rounds:
            messages.append(f"Oxygen loss after round {oxygen_safe_rounds}: {self.change_endurance(-2)}")
        return messages

    def combat_player_loss_total(self) -> int:
        total = 0
        for round_entry in as_list(self.combat.get("Log")):
            if isinstance(round_entry, dict):
                total += int(round_entry.get("PlayerLoss") or round_entry.get("LoneWolfReduxLoss") or 0)
        return total

    def combat_rounds_from_entry(self, entry: dict[str, Any]) -> list[dict[str, Any]]:
        return [
            round_entry
            for round_entry in as_list(entry.get("Rounds") or entry.get("Log"))
            if isinstance(round_entry, dict)
        ]

    def combat_player_loss_total_from_entry(self, entry: dict[str, Any]) -> int:
        return sum(
            int(round_entry.get("PlayerLoss") or round_entry.get("LoneWolfReduxLoss") or 0)
            for round_entry in self.combat_rounds_from_entry(entry)
        )

    def combat_round_count_from_entry(self, entry: dict[str, Any]) -> int:
        return int(entry.get("RoundCount") or len(self.combat_rounds_from_entry(entry)))

    def combat_entry_matches_preset(self, entry: dict[str, Any], preset: dict[str, Any]) -> bool:
        preset_id = str(preset.get("id") or "")
        entry_id = str(entry.get("SectionCombatId") or "")
        if preset_id and entry_id and preset_id == entry_id:
            return True
        enemies = [
            enemy for enemy in as_list(preset.get("enemies") or preset.get("enemy"))
            if isinstance(enemy, dict)
        ]
        if len(enemies) != 1:
            return False
        enemy = enemies[0]
        return (
            str(enemy.get("name") or preset.get("label") or "").strip().lower()
            == str(entry.get("EnemyName") or "").strip().lower()
            and int(enemy.get("cs") or 0) == int(entry.get("EnemyCombatSkill") or 0)
            and int(enemy.get("endurance") or enemy.get("end") or 0)
            == int(entry.get("EnemyEnduranceMax") or 0)
        )

    def combat_preset_for_entry(self, book_number: int, entry: dict[str, Any]) -> dict[str, Any] | None:
        section = int(entry.get("StartedSection") or entry.get("Section") or 0)
        if not section:
            return None
        flow = self.section_flow_entry(book_number, section) or {}
        for preset in self.flow_combat_entries_for_entry(flow):
            if self.combat_entry_matches_preset(entry, preset):
                return preset
        return None

    def expected_combat_route_from_preset(self, preset: dict[str, Any], entry: dict[str, Any]) -> int | None:
        outcome = str(entry.get("Outcome") or "").strip().lower()
        rounds = self.combat_rounds_from_entry(entry)
        round_count = self.combat_round_count_from_entry(entry)
        if outcome == "victory":
            route = preset.get("victoryRoute")
            player_loss_total = self.combat_player_loss_total_from_entry(entry)
            if player_loss_total > 0 and preset.get("woundedVictoryRoute"):
                route = preset.get("woundedVictoryRoute")
            elif player_loss_total <= 0 and preset.get("flawlessVictoryRoute"):
                route = preset.get("flawlessVictoryRoute")
            win_within = int(preset.get("winWithinRounds") or 0)
            if win_within:
                route = preset.get("winWithinRoute") if round_count <= win_within else preset.get("tooLateRoute")
            return int(route) if route else None
        if outcome == "evaded":
            route = preset.get("evadeRoute")
            return int(route) if route else None
        if outcome == "defeat":
            route = preset.get("defeatRoute")
            return int(route) if route else None
        if outcome == "survived":
            route = preset.get("survivalRoute")
            return int(route) if route else None
        if outcome == "timed out":
            route = preset.get("roundExceededRoute")
            return int(route) if route else None
        if outcome == "completed" and isinstance(preset.get("oneRoundComparisonRoutes"), dict) and rounds:
            last_round = rounds[-1]
            player_loss = int(last_round.get("PlayerLoss") or last_round.get("LoneWolfReduxLoss") or 0)
            enemy_loss = int(last_round.get("EnemyLoss") or 0)
            routes = preset.get("oneRoundComparisonRoutes")
            if player_loss > enemy_loss:
                route = routes.get("playerLossGreater")
            elif enemy_loss > player_loss:
                route = routes.get("enemyLossGreater")
            else:
                route = routes.get("equal")
            return int(route) if route else None
        if outcome == "special route" and isinstance(preset.get("combatRollRoutes"), dict) and rounds:
            roll = str(rounds[-1].get("Roll"))
            route = preset.get("combatRollRoutes", {}).get(roll)
            return int(route) if route else None
        return None

    def repair_combat_entry_routes_from_preset(self, entry: dict[str, Any], preset: dict[str, Any]) -> bool:
        changed = False
        field_pairs = (
            ("VictoryRoute", "victoryRoute"),
            ("DefeatRoute", "defeatRoute"),
            ("EvadeRoute", "evadeRoute"),
            ("FlawlessVictoryRoute", "flawlessVictoryRoute"),
            ("WoundedVictoryRoute", "woundedVictoryRoute"),
            ("PlayerLossRoute", "playerLossRoute"),
            ("WinWithinRoute", "winWithinRoute"),
            ("TooLateRoute", "tooLateRoute"),
            ("SurvivalRoute", "survivalRoute"),
            ("RoundExceededRoute", "roundExceededRoute"),
        )
        for state_key, preset_key in field_pairs:
            if preset_key not in preset:
                if entry.get(state_key) not in (None, "", {}):
                    entry[state_key] = None
                    changed = True
                continue
            value = preset.get(preset_key)
            if value is not None and entry.get(state_key) != value:
                entry[state_key] = value
                changed = True
        if preset.get("id") and not str(entry.get("SectionCombatId") or ""):
            entry["SectionCombatId"] = str(preset.get("id") or "")
            changed = True
        return changed

    def repair_loaded_combat_routes(self) -> list[str]:
        messages: list[str] = []
        book_number = int(self.character.get("BookNumber") or 1)

        current_combat = self.combat
        if isinstance(current_combat, dict):
            preset = self.combat_preset_for_entry(book_number, current_combat)
            if preset:
                old_final_route = current_combat.get("VictoryRoute")
                expected_route = self.expected_combat_route_from_preset(preset, current_combat)
                if self.repair_combat_entry_routes_from_preset(current_combat, preset):
                    messages.append(
                        f"current combat route repaired for section "
                        f"{current_combat.get('StartedSection') or current_combat.get('Section')}"
                    )
                if (
                    expected_route
                    and old_final_route
                    and int(old_final_route) != int(expected_route)
                    and int(self.state.get("CurrentSection") or 0) == int(old_final_route)
                    and not bool(current_combat.get("Active"))
                ):
                    before = int(self.state.get("CurrentSection") or 0)
                    self.state["CurrentSection"] = int(expected_route)
                    messages.append(f"current section repaired {before}->{expected_route}")

        repaired_history = 0
        for entry in as_list(self.state.get("CombatHistory")):
            if not isinstance(entry, dict):
                continue
            preset = self.combat_preset_for_entry(int(entry.get("BookNumber") or book_number), entry)
            if preset and self.repair_combat_entry_routes_from_preset(entry, preset):
                repaired_history += 1
        if repaired_history:
            messages.append(f"combat history route repairs: {repaired_history}")
        return messages

    def restore_player_endurance_after_combat_effects(self) -> None:
        stored = self.combat.get("StoredPlayerEnduranceBeforeCombat")
        if stored is None:
            return
        maximum = int(self.character["EnduranceMax"])
        if bool(self.combat.get("RestorePlayerEnduranceAfterCombat")):
            self.character["EnduranceCurrent"] = max(0, min(int(stored), maximum))
            return
        if bool(self.combat.get("RestoreHalfPlayerEnduranceLossAfterCombat")):
            gain = self.combat_player_loss_total() // 2
            if gain > 0:
                self.character["EnduranceCurrent"] = max(
                    0,
                    min(
                        int(stored),
                        int(self.character["EnduranceCurrent"]) + gain,
                        maximum,
                    ),
                )

    def active_combat_matches_preset(self, preset: dict[str, Any]) -> bool:
        enemies = [enemy for enemy in as_list(preset.get("enemies") or preset.get("enemy")) if isinstance(enemy, dict)]
        if len(enemies) != 1:
            return False
        enemy = enemies[0]
        return (
            str(enemy.get("name") or preset.get("label") or "").strip().lower()
            == str(self.combat.get("EnemyName") or "").strip().lower()
            and int(enemy.get("cs") or 0) == int(self.combat.get("EnemyCombatSkill") or 0)
            and int(enemy.get("endurance") or enemy.get("end") or 0) == int(self.combat.get("EnemyEnduranceMax") or 0)
        )

    def sync_active_combat_with_section_preset(self) -> bool:
        if not self.combat.get("Active"):
            return False
        book_number = int(self.character.get("BookNumber") or 1)
        section = int(self.combat.get("StartedSection") or self.state.get("CurrentSection") or 1)
        entry = self.section_flow_entry(book_number, section) or {}
        for preset in self.flow_combat_entries_for_entry(entry):
            if not self.active_combat_matches_preset(preset):
                continue

            changed = False
            for key, source_key, default in (
                ("EnemyImmune", "enemyImmune", False),
                ("DoubleEnemyLoss", "doubleEnemyLoss", False),
                ("DoubleEnemyLossWithSommerswerd", "doubleEnemyLossWithSommerswerd", False),
                ("IgnorePlayerLossIfEnemyLossGreater", "ignorePlayerLossIfEnemyLossGreater", False),
                ("RestorePlayerEnduranceAfterCombat", "restorePlayerEnduranceAfterCombat", False),
                (
                    "RestoreHalfPlayerEnduranceLossAfterCombat",
                    "restoreHalfPlayerEnduranceLossAfterCombat",
                    False,
                ),
                ("CanEvade", "canEvade", False),
            ):
                value = bool(preset.get(source_key, default))
                if bool(self.combat.get(key)) != value:
                    self.combat[key] = value
                    changed = True

            numeric_fields = (
                ("EvadeAfterRounds", "evadeAfterRounds"),
                ("IgnorePlayerLossRounds", "ignorePlayerLossRounds"),
                ("IgnoreEnemyLossRounds", "ignoreEnemyLossRounds"),
                ("RoundLimit", "roundLimit"),
                ("WinWithinRounds", "winWithinRounds"),
                ("OxygenSafeRounds", "oxygenSafeRounds"),
            )
            for key, source_key in numeric_fields:
                value = max(0, int(preset.get(source_key) or 0))
                if int(self.combat.get(key) or 0) != value:
                    self.combat[key] = value
                    changed = True

            for key, source_key in (
                ("VictoryRoute", "victoryRoute"),
                ("DefeatRoute", "defeatRoute"),
                ("EvadeRoute", "evadeRoute"),
                ("SurvivalRoute", "survivalRoute"),
                ("RoundExceededRoute", "roundExceededRoute"),
                ("PlayerLossRoute", "playerLossRoute"),
                ("WinWithinRoute", "winWithinRoute"),
                ("TooLateRoute", "tooLateRoute"),
                ("RequiredWeapon", "requiredWeapon"),
            ):
                value = preset.get(source_key)
                if value is not None and self.combat.get(key) != value:
                    self.combat[key] = value
                    changed = True

            if preset.get("perRoundActions") and not as_list(self.combat.get("PerRoundActions")):
                self.combat["PerRoundActions"] = as_list(preset.get("perRoundActions"))
                changed = True
            if preset.get("timedModifiers") and not as_list(self.combat.get("TimedModifiers")):
                self.combat["TimedModifiers"] = as_list(preset.get("timedModifiers"))
                changed = True
            if isinstance(preset.get("oneRoundComparisonRoutes"), dict) and self.combat.get(
                "OneRoundComparisonRoutes"
            ) != preset.get("oneRoundComparisonRoutes"):
                self.combat["OneRoundComparisonRoutes"] = preset.get("oneRoundComparisonRoutes")
                changed = True
            if isinstance(preset.get("playerLossRandomCheck"), dict) and self.combat.get(
                "PlayerLossRandomCheck"
            ) != preset.get("playerLossRandomCheck"):
                self.combat["PlayerLossRandomCheck"] = preset.get("playerLossRandomCheck")
                changed = True
            if isinstance(preset.get("combatRollRoutes"), dict) and self.combat.get(
                "CombatRollRoutes"
            ) != preset.get("combatRollRoutes"):
                self.combat["CombatRollRoutes"] = preset.get("combatRollRoutes")
                changed = True
            if preset.get("id") and not str(self.combat.get("SectionCombatId") or ""):
                self.combat["SectionCombatId"] = str(preset.get("id") or "")
                changed = True

            if changed and bool(self.settings.get("AutoSave", True)):
                self.autosave()
            return changed
        return False

    def route_after_combat_round(self) -> bool:
        self.sync_active_combat_with_section_preset()
        round_count = self.combat_round_count()
        threshold = self.combat.get("PostRoundWpThreshold")
        if isinstance(threshold, dict) and round_count >= int(threshold.get("round") or 1):
            route = int(threshold.get("ltRoute") or threshold.get("gteRoute") or 0)
            self.archive_current_combat("Completed")
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            print(f"Post-round route: section {route}.")
            if route:
                self.set_section(route)
            return True

        if int(self.character["EnduranceCurrent"]) <= 0:
            print("Lone Wolf has fallen.")
            enemy_name = str(self.combat.get("EnemyName") or "the enemy")
            self.archive_current_combat("Defeat")
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            defeat_route = self.combat.get("DefeatRoute")
            if defeat_route:
                minimum = self.combat.get("DefeatEnduranceMinimum")
                if minimum is not None:
                    self.character["EnduranceCurrent"] = max(
                        int(self.character["EnduranceCurrent"]), int(minimum)
                    )
                print(f"Defeat route: section {defeat_route}.")
                self.set_section(int(defeat_route))
                return True
            self.register_death("combat", f"Defeated by {enemy_name}.")
            self.autosave()
            self.show_death_screen()
            return True

        player_loss_route = self.combat.get("PlayerLossRoute")
        if player_loss_route and self.combat_player_loss_total() > 0:
            self.archive_current_combat("Wounded")
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            print(f"Wounded route: section {player_loss_route}.")
            self.set_section(int(player_loss_route))
            return True

        comparison_routes = self.combat.get("OneRoundComparisonRoutes")
        if isinstance(comparison_routes, dict) and comparison_routes and round_count >= 1:
            last_round = as_list(self.combat.get("Log"))[-1]
            player_loss = int(last_round.get("PlayerLoss") or last_round.get("LoneWolfReduxLoss") or 0)
            enemy_loss = int(last_round.get("EnemyLoss") or 0)
            if player_loss > enemy_loss:
                route = comparison_routes.get("playerLossGreater")
                label = "Player loss greater"
            elif enemy_loss > player_loss:
                route = comparison_routes.get("enemyLossGreater")
                label = "Enemy loss greater"
            else:
                route = comparison_routes.get("equal")
                label = "Equal losses"
            self.archive_current_combat("Completed")
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            if route:
                print(f"{label} route: section {route}.")
                self.set_section(int(route))
                return True
            self.autosave()
            return True

        limit = int(self.combat.get("RoundLimit") or 0)
        if limit and self.combat.get("SurvivalRoute") and round_count >= limit:
            route = self.combat.get("SurvivalRoute")
            self.archive_current_combat("Survived")
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            print(f"Survived route: section {route}.")
            self.set_section(int(route))
            return True

        if int(self.combat["EnemyEnduranceCurrent"]) <= 0:
            if self.advance_enemy_queue():
                self.autosave()
                return True
            print("Enemy defeated.")
            for action in as_list(self.combat.get("AfterVictoryActions")):
                if isinstance(action, dict):
                    message = self.apply_automation_action(action)
                    if message:
                        print(message)
            self.archive_current_combat("Victory")
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            route = self.combat.get("VictoryRoute")
            player_loss_total = self.combat_player_loss_total()
            if player_loss_total > 0 and self.combat.get("WoundedVictoryRoute"):
                route = self.combat.get("WoundedVictoryRoute")
            elif player_loss_total <= 0 and self.combat.get("FlawlessVictoryRoute"):
                route = self.combat.get("FlawlessVictoryRoute")
            win_within = int(self.combat.get("WinWithinRounds") or 0)
            if win_within:
                route = self.combat.get("WinWithinRoute") if round_count <= win_within else self.combat.get("TooLateRoute")
            if route:
                print(f"Victory route: section {route}.")
                self.set_section(int(route))
                return True
            self.autosave()
            return True

        if limit and round_count >= limit:
            route = self.combat.get("RoundExceededRoute")
            outcome = "Timed Out"
            self.archive_current_combat(outcome)
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            if route:
                print(f"{outcome} route: section {route}.")
                self.set_section(int(route))
                return True
            self.autosave()
            return True
        return False

    def start_combat(self, tokens: list[str]) -> None:
        name = ""
        enemy_cs = 0
        enemy_end = 0
        if len(tokens) >= 5:
            try:
                enemy_cs = int(tokens[-2])
                enemy_end = int(tokens[-1])
                name = " ".join(tokens[2:-2])
            except ValueError:
                name = ""

        if not name:
            name = input("Enemy name: ").strip()
            enemy_cs = read_int("Enemy Combat Skill", 10, 0, 99)
            enemy_end = read_int("Enemy Endurance", 10, 1, 999)

        active_weapon = self.preferred_combat_weapon()
        self.combat.update(
            {
                "Active": True,
                "EnemyName": name,
                "EnemyCombatSkill": enemy_cs,
                "EnemyEnduranceMax": enemy_end,
                "EnemyEnduranceCurrent": enemy_end,
                "Modifier": 0,
                "ActiveWeapon": active_weapon,
                "UseStaff": False,
                "ForceUnarmed": False,
                "IgnorePlayerLossIfEnemyLossGreater": False,
                "StaffWillpower": 0,
                "EnemyImmune": False,
                "CanEvade": False,
                "EvadeAfterRounds": 0,
                "VictoryRoute": None,
                "DefeatRoute": None,
                "DefeatEnduranceMinimum": None,
                "EvadeRoute": None,
                "FlawlessVictoryRoute": None,
                "WoundedVictoryRoute": None,
                "RoundLimit": 0,
                "SurvivalRoute": None,
                "RoundExceededRoute": None,
                "PlayerLossRoute": None,
                "OneRoundComparisonRoutes": {},
                "PlayerLossRandomCheck": {},
                "WinWithinRounds": 0,
                "WinWithinRoute": None,
                "TooLateRoute": None,
                "PostRoundWpThreshold": None,
                "PerRoundActions": [],
                "TimedModifiers": [],
                "AppliedConditionalModifierLabels": [],
                "IgnorePlayerLossRounds": 0,
                "IgnoreEnemyLossRounds": 0,
                "CombatRollRoutes": {},
                "DoubleEnemyLoss": False,
                "DoubleEnemyLossWithSommerswerd": False,
                "RestorePlayerEnduranceAfterCombat": False,
                "RestoreHalfPlayerEnduranceLossAfterCombat": False,
                "StoredPlayerEnduranceBeforeCombat": None,
                "FixedPlayerCombatSkill": None,
                "RequiredWeapon": "",
                "EnemyQueue": [],
                "EnemyIndex": 0,
                "SectionCombatId": "",
                "VictoryChoices": [],
                "AfterVictoryActions": [],
                "Outcome": "",
                "StartedSection": int(self.state["CurrentSection"]),
                "Log": [],
            }
        )
        self.remember_combat_weapon(active_weapon)
        weapon_modifier, weapon_notes = self.combat_weapon_modifier_and_notes()
        if weapon_modifier:
            print("; ".join(weapon_notes))
        print(f"Combat started: {name} CS {enemy_cs} END {enemy_end}")
        self.show_combat_status()

    def show_combat_status(self) -> None:
        if not self.combat.get("Active"):
            panel_header("Combat", accent=SCREEN_ACCENTS["combat"])
            panel_text("No active combat. Use combat start <name> <cs> <end>.")
            panel_footer()
            self.show_helpful_commands("combat")
            return
        player_cs = self.combat_skill_for_round()
        ratio = player_cs - int(self.combat["EnemyCombatSkill"])
        panel_header("Combat", accent=SCREEN_ACCENTS["combat"])
        panel_row("Enemy", self.combat["EnemyName"])
        panel_pair_row("Enemy CS", self.combat["EnemyCombatSkill"], "Enemy END", f"{self.combat['EnemyEnduranceCurrent']}/{self.combat['EnemyEnduranceMax']}")
        panel_pair_row("Lone Wolf CS", player_cs, "END", f"{self.character['EnduranceCurrent']}/{self.character['EnduranceMax']}", left_color="Cyan", right_color=endurance_color(self.character["EnduranceCurrent"], self.character["EnduranceMax"]))
        panel_pair_row("Ratio", ratio, "Weapon", self.combat_active_weapon() or "Unarmed", left_color="Yellow" if ratio < 0 else "Green", right_color="White")
        panel_row("Modifier", self.combat["Modifier"])
        panel_footer()
        self.show_helpful_commands("combat")

    def combat_round(self, tokens: list[str], evade: bool = False) -> None:
        if not self.combat.get("Active"):
            print("No active combat. Use 'combat start <name> <cs> <end>'.")
            return
        if not self.crt:
            print("Combat Results Table is not loaded.")
            return
        self.sync_active_combat_with_section_preset()

        arg_index = 2
        wp_spend = 0
        roll = -1
        use_staff = self.combat_uses_magical_staff()

        if use_staff:
            if len(tokens) > arg_index:
                try:
                    wp_spend = int(tokens[arg_index])
                    arg_index += 1
                except ValueError:
                    wp_spend = 0
            if wp_spend <= 0:
                wp_spend = max(1, int(self.combat["StaffWillpower"]))
            if wp_spend > int(self.character["WillpowerCurrent"]):
                print("Not enough Willpower; spending remaining WP instead.")
                wp_spend = int(self.character["WillpowerCurrent"])

        if len(tokens) > arg_index:
            try:
                roll = int(tokens[arg_index])
            except ValueError:
                roll = -1
        if roll < 0 or roll > 9:
            roll = random_digit()

        round_number = self.combat_round_count() + 1
        player_cs = self.combat_skill_for_round(round_number)
        ratio = player_cs - self.combat_effective_enemy_combat_skill()
        column, enemy_loss_raw, player_loss_raw = self.get_crt_result(ratio, roll)
        base_enemy_loss = self.loss_value(enemy_loss_raw, int(self.combat["EnemyEnduranceCurrent"]))
        player_loss = self.loss_value(player_loss_raw, int(self.character["EnduranceCurrent"]))
        ignored_player_loss = 0
        if round_number <= int(self.combat.get("IgnorePlayerLossRounds") or 0):
            ignored_player_loss = player_loss
            player_loss = 0
        enemy_loss = 0
        ignored_enemy_loss = 0
        required_weapon = str(self.combat.get("RequiredWeapon") or "").strip()
        active_weapon = self.combat_active_weapon()
        weapon_can_wound = not required_weapon or active_weapon.lower() == required_weapon.lower()

        if not evade and weapon_can_wound:
            multiplier = max(1, wp_spend) if use_staff else 1
            if bool(self.combat.get("DoubleEnemyLoss")):
                multiplier *= 2
            if bool(self.combat.get("DoubleEnemyLossWithSommerswerd")) and self.combat_active_weapon() == "Sommerswerd":
                multiplier *= 2
            enemy_loss = min(int(self.combat["EnemyEnduranceCurrent"]), base_enemy_loss * multiplier)

        if round_number <= int(self.combat.get("IgnoreEnemyLossRounds") or 0):
            ignored_enemy_loss = enemy_loss
            enemy_loss = 0

        if (
            not evade
            and bool(self.combat.get("IgnorePlayerLossIfEnemyLossGreater"))
            and enemy_loss > player_loss
        ):
            ignored_player_loss = player_loss
            player_loss = 0

        player_loss_random_check = self.combat.get("PlayerLossRandomCheck")
        special_roll: int | None = None
        special_death_cause = ""
        special_check_label = ""
        if (
            not evade
            and player_loss > 0
            and isinstance(player_loss_random_check, dict)
            and player_loss_random_check
        ):
            ignored_player_loss = player_loss
            player_loss = 0
            stored_roll = self.automation["Stored"].pop("combatSpecialRoll", None)
            try:
                special_roll = int(stored_roll)
            except (TypeError, ValueError):
                special_roll = random_digit()
            special_roll = max(0, min(9, special_roll))
            death_values = {
                int(value)
                for value in as_list(player_loss_random_check.get("deathValues"))
                if str(value).strip().lstrip("-").isdigit()
            }
            if special_roll in death_values:
                special_death_cause = str(
                    player_loss_random_check.get("deathCause") or "A special combat check ends the mission."
                )
                special_check_label = "death"
            else:
                special_check_label = str(player_loss_random_check.get("safeLabel") or "safe")

        self.combat["EnemyEnduranceCurrent"] = max(0, int(self.combat["EnemyEnduranceCurrent"]) - enemy_loss)
        self.character["EnduranceCurrent"] = max(0, int(self.character["EnduranceCurrent"]) - player_loss)
        round_entry = {
            "Round": round_number,
            "Roll": roll,
            "Ratio": ratio,
            "CRTColumn": column,
            "ActiveWeapon": self.combat_active_weapon() or "Unarmed",
            "EnemyLoss": enemy_loss,
            "IgnoredEnemyLoss": ignored_enemy_loss,
            "IgnoredPlayerLoss": ignored_player_loss,
            "LoneWolfReduxLoss": player_loss,
            "PlayerLoss": player_loss,
            "PlayerEnd": int(self.character["EnduranceCurrent"]),
            "EnemyEnd": int(self.combat["EnemyEnduranceCurrent"]),
            "Evade": evade,
        }
        if special_roll is not None:
            round_entry["SpecialRoll"] = special_roll
            round_entry["SpecialRollResult"] = special_check_label
        self.combat["Log"] = as_list(self.combat["Log"]) + [round_entry]

        print("")
        print(f"Roll {roll}, ratio {ratio} (CRT {column})")
        if not evade:
            print(f"Enemy loss: {enemy_loss}")
            if required_weapon and not weapon_can_wound:
                print(f"Only {required_weapon} can wound this enemy.")
        else:
            print("Evading: enemy loss ignored.")
        if ignored_enemy_loss:
            print(f"Enemy loss ignored by section rule: {ignored_enemy_loss}")
        if ignored_player_loss:
            print(f"Lone Wolf loss ignored by section rule: {ignored_player_loss}")
        if special_roll is not None:
            print(f"Special combat roll: {special_roll} ({special_check_label})")
        print(f"Lone Wolf loss: {player_loss}")
        print(f"Enemy END: {self.combat['EnemyEnduranceCurrent']}/{self.combat['EnemyEnduranceMax']}")
        print(
            f"Lone Wolf END: {self.character['EnduranceCurrent']}/"
            f"{self.character['EnduranceMax']}"
        )

        special_messages = self.apply_combat_per_round_actions()
        if special_messages and self.combat.get("Log"):
            self.combat["Log"][-1]["SpecialEffects"] = special_messages
            self.combat["Log"][-1]["FinalPlayerEnd"] = int(self.character["EnduranceCurrent"])

        for message in special_messages:
            print(message)
        if special_death_cause:
            self.archive_current_combat("Special Death")
            self.combat["Active"] = False
            self.register_death("combat", special_death_cause)
            self.autosave()
            self.show_death_screen()
            return
        combat_roll_routes = self.combat.get("CombatRollRoutes")
        if not evade and isinstance(combat_roll_routes, dict) and combat_roll_routes:
            route = combat_roll_routes.get(str(roll), combat_roll_routes.get(roll))
            if route:
                self.archive_current_combat("Special Route")
                self.restore_player_endurance_after_combat_effects()
                self.combat["Active"] = False
                print(f"Combat roll route: section {route}.")
                self.set_section(int(route))
                return
        if self.route_after_combat_round():
            return
        self.autosave()

    def resolve_combat_to_outcome(self, max_rounds: int = 100) -> None:
        if not self.combat.get("Active"):
            print("No active combat. Use 'combat start <name> <cs> <end>'.")
            return
        rounds = 0
        while self.combat.get("Active") and rounds < max_rounds:
            self.combat_round(["combat", "round"], evade=False)
            rounds += 1
        if self.combat.get("Active"):
            print(f"Stopped auto-resolve after {max_rounds} rounds; combat is still active.")
        else:
            print(f"Auto-resolve finished after {rounds} round(s).")
        self.autosave()

    def can_evade_combat_now(self) -> bool:
        if not bool(self.combat.get("CanEvade")):
            return False
        required_rounds = int(self.combat.get("EvadeAfterRounds") or 0)
        return self.combat_round_count() >= required_rounds

    def evade_combat(self, tokens: list[str] | None = None) -> None:
        if not self.combat.get("Active"):
            print("No active combat. Use 'combat start <name> <cs> <end>'.")
            return
        if not bool(self.combat.get("CanEvade")):
            print("Evade is not marked as available for this combat.")
            return
        required_rounds = int(self.combat.get("EvadeAfterRounds") or 0)
        if self.combat_round_count() < required_rounds:
            print(f"Evade is only available after round {required_rounds}.")
            return

        round_tokens = tokens if tokens is not None else ["combat", "evade"]
        self.combat_round(round_tokens, evade=True)
        if self.combat.get("Active"):
            self.archive_current_combat("Evaded")
            self.restore_player_endurance_after_combat_effects()
            self.combat["Active"] = False
            route = self.combat.get("EvadeRoute")
            print("Combat evaded.")
            if route:
                print(f"Evade route: section {route}.")
                self.set_section(int(route))
                return
            self.autosave()

    def stop_combat(self, outcome: str = "Stopped") -> None:
        if self.combat.get("Active"):
            self.archive_current_combat(outcome)
        self.combat["Active"] = False
        self.autosave()
        print("Combat stopped.")

    def combat_command(self, tokens: list[str]) -> None:
        if len(tokens) < 2:
            self.show_combat_status()
            return
        sub = tokens[1].lower()
        if sub == "start":
            self.start_combat(tokens)
        elif sub == "status":
            self.show_combat_status()
        elif sub == "round":
            self.combat_round(tokens)
        elif sub in {"auto", "resolve"}:
            self.resolve_combat_to_outcome()
        elif sub == "evade":
            self.evade_combat(tokens)
        elif sub == "stop":
            self.stop_combat()
        elif sub == "staff":
            print("Book 1 combat uses carried Weapons. Use: combat weapon <name|unarmed>")
        elif sub == "weapon":
            if len(tokens) < 3:
                print("Use: combat weapon <name|unarmed>")
                print("Available: " + format_list(self.available_combat_weapons()))
                return
            self.set_combat_weapon(rest_of_line(tokens, 2))
        elif sub == "mod":
            if len(tokens) < 3:
                print("Use: combat mod <n>")
                return
            try:
                self.combat["Modifier"] = int(tokens[2])
            except ValueError:
                print("Modifier must be a number.")
                return
            print(f"Combat modifier: {self.combat['Modifier']}")
        else:
            print("Unknown combat command. Use 'help'.")

    def complete_book(self) -> None:
        summary = self.ensure_book_completed(save=True)
        next_book = int(summary["BookNumber"]) + 1
        print(f"Book {summary['BookNumber']} complete: {summary['BookTitle']}.")
        if next_book in BOOKS:
            print(f"Use continue when ready to set up Book {next_book}: {BOOKS[next_book]['Title']}.")
        else:
            print("No later supported book is enabled yet.")

    def continue_completed_book(
        self,
        *,
        kai_discipline: str = "",
        weaponskill_roll: int | None = None,
        book2_gold_roll: int | None = None,
        book2_armoury_choices: Any = None,
        book2_weapon_exchanges: Any = None,
        book3_gold_roll: int | None = None,
        book3_equipment_choices: Any = None,
        book3_weapon_exchanges: Any = None,
        book4_gold_roll: int | None = None,
        book4_equipment_choices: Any = None,
        book4_weapon_exchanges: Any = None,
        book5_gold_roll: int | None = None,
        book5_equipment_choices: Any = None,
        book5_weapon_exchanges: Any = None,
        book5_safekeeping_special_items: Any = None,
        lesser_magick: str = "",
        higher_magicks: Any = None,
        willpower_roll: int | None = None,
    ) -> None:
        completion = self.book_completion_payload()
        if not completion.get("Active"):
            print("No completed book is ready to continue.")
            return

        summary = completion.get("Summary") if isinstance(completion.get("Summary"), dict) else {}
        current = int(summary.get("BookNumber") or self.character["BookNumber"])
        next_book = current + 1
        if next_book not in {2, 3, 4, 5}:
            print(f"Book {next_book} setup is not enabled yet.")
            return

        self.ensure_book_completed(current)
        existing_disciplines = clean_kai_disciplines(self.character.get("KaiDisciplines"))
        missing_disciplines = [item for item in KAI_DISCIPLINES if item not in existing_disciplines]
        selected_discipline = str(kai_discipline or "").strip()
        if selected_discipline not in missing_disciplines:
            raise ValueError(f"Continuing to Book {next_book} requires one new Kai Discipline.")

        if next_book == 2:
            choice_ids = clean_book2_armoury_choices(book2_armoury_choices)
        elif next_book == 3:
            choice_ids = clean_book3_equipment_choices(book3_equipment_choices)
        elif next_book == 4:
            choice_ids = clean_book4_equipment_choices(book4_equipment_choices)
        else:
            choice_ids = clean_book5_equipment_choices(book5_equipment_choices)
        messages: list[str] = []
        restored_gear_message = self.restore_stored_gear_for_book_transition()
        if restored_gear_message:
            messages.append(f"Recovered temporarily stored gear: {restored_gear_message}")

        self.character["BookNumber"] = next_book
        self.character["KaiDisciplines"] = existing_disciplines + [selected_discipline]
        self.state["CurrentSection"] = 1
        self.state["Combat"] = json_clone(default_state()["Combat"])
        self.state["Combat"]["StartedSection"] = 1
        self.clear_death_state()

        automation_enabled = bool(self.automation.get("Enabled", True))
        item_history = json_clone(as_list(self.automation.get("ItemHistory")))
        journal = json_clone(as_list(self.automation.get("Journal")))
        death_history = json_clone(as_list(self.automation.get("DeathHistory")))
        stored = json_clone(self.automation.get("Stored")) if isinstance(self.automation.get("Stored"), dict) else {}
        safekeeping_items = as_list(stored.get("safekeepingSpecialItems"))
        safekeeping_records = (
            json_clone(stored.get("safekeepingRecords"))
            if isinstance(stored.get("safekeepingRecords"), list)
            else []
        )
        self.state["Automation"] = default_automation()
        self.automation["Enabled"] = automation_enabled
        self.automation["ItemHistory"] = item_history
        self.automation["Journal"] = journal[-100:]
        self.automation["DeathHistory"] = death_history
        if safekeeping_items:
            self.automation["Stored"]["safekeepingSpecialItems"] = safekeeping_items
        if safekeeping_records:
            self.automation["Stored"]["safekeepingRecords"] = safekeeping_records

        messages.append(f"Added Kai Discipline: {selected_discipline}")
        weaponskill_digit: int | None = None
        weaponskill_weapon = ""
        if selected_discipline == "Weaponskill":
            weaponskill_digit = coerce_random_digit(weaponskill_roll)
            weaponskill_weapon = weaponskill_weapon_for_roll(weaponskill_digit)
            self.character["WeaponskillWeapon"] = weaponskill_weapon
            messages.append(f"Weaponskill roll {weaponskill_digit}: {weaponskill_weapon}")
        if next_book == 2:
            ensure_book2_mandatory_items(self.inventory)
            gold_digit, before_gold, gold_gain, after_gold = apply_book2_gold_roll(
                self.inventory, book2_gold_roll
            )
            setup_messages = apply_book2_armoury_to_state(
                self.state, choice_ids, book2_weapon_exchanges
            )
            setup_key = "Book2Setup"
            setup_choice_key = "ArmouryChoices"
            setup_label_key = "ArmouryLabels"
            roll_prefix = "Book2"
            choice_labels = book2_armoury_labels(choice_ids)
        elif next_book == 3:
            ensure_book3_mandatory_state(self.state)
            gold_digit, before_gold, gold_gain, after_gold = apply_book3_gold_roll(
                self.inventory, book3_gold_roll
            )
            setup_messages = apply_book3_equipment_to_state(
                self.state, choice_ids, book3_weapon_exchanges
            )
            setup_key = "Book3Setup"
            setup_choice_key = "EquipmentChoices"
            setup_label_key = "EquipmentLabels"
            roll_prefix = "Book3"
            choice_labels = book3_equipment_labels(choice_ids)
        elif next_book == 4:
            ensure_book4_mandatory_state(self.state)
            gold_digit, before_gold, gold_gain, after_gold = apply_book4_gold_roll(
                self.inventory, book4_gold_roll
            )
            setup_messages = apply_book4_equipment_to_state(
                self.state, choice_ids, book4_weapon_exchanges
            )
            setup_key = "Book4Setup"
            setup_choice_key = "EquipmentChoices"
            setup_label_key = "EquipmentLabels"
            roll_prefix = "Book4"
            choice_labels = book4_equipment_labels(choice_ids)
        else:
            ensure_book5_mandatory_state(self.state)
            gold_digit, before_gold, gold_gain, after_gold = apply_book5_gold_roll(
                self.inventory, book5_gold_roll
            )
            setup_messages = apply_book5_equipment_to_state(
                self.state, choice_ids, book5_weapon_exchanges
            )
            setup_messages.extend(
                move_special_items_to_safekeeping(
                    self.state,
                    book5_safekeeping_special_items,
                    place="Kai Monastery",
                    book_number=next_book,
                )
            )
            setup_key = "Book5Setup"
            setup_choice_key = "EquipmentChoices"
            setup_label_key = "EquipmentLabels"
            roll_prefix = "Book5"
            choice_labels = book5_equipment_labels(choice_ids)

        messages.append(f"Book {next_book} Gold roll {gold_digit}: +{gold_gain} Crowns")
        if after_gold < before_gold + gold_gain:
            messages.append(f"Gold cap: {before_gold}+{gold_gain} capped at 50")
        messages.extend(setup_messages)

        setup = {
            "Mode": "campaign",
            "ContinuedFromBook": current,
            "NewKaiDiscipline": selected_discipline,
            "GoldRoll": gold_digit,
            "GoldBefore": before_gold,
            "GoldGain": gold_gain,
            "GoldAfter": after_gold,
            setup_choice_key: choice_ids,
            setup_label_key: choice_labels,
        }
        if weaponskill_digit is not None:
            setup["WeaponskillRoll"] = weaponskill_digit
            setup["WeaponskillWeapon"] = weaponskill_weapon
        if next_book == 5:
            setup["SafekeepingSpecialItems"] = as_list(
                self.automation.get("Stored", {}).get("safekeepingSpecialItems")
            )
            setup["SafekeepingRecords"] = json_clone(
                self.automation.get("Stored", {}).get("safekeepingRecords", [])
            )
        existing_setup = self.character.get(setup_key)
        if isinstance(existing_setup, dict):
            for key, value in existing_setup.items():
                if str(key).endswith("Applied") and key not in setup:
                    setup[key] = value
        self.character[setup_key] = setup
        rolls = self.character.get("CreationRolls")
        if not isinstance(rolls, dict):
            rolls = {}
        rolls.update(
            {
                f"{roll_prefix}Gold": gold_digit,
                f"{roll_prefix}GoldGain": gold_gain,
                f"{roll_prefix}GoldBefore": before_gold,
                f"{roll_prefix}GoldAfter": after_gold,
                f"{roll_prefix}KaiDiscipline": selected_discipline,
            }
        )
        if weaponskill_digit is not None:
            rolls["Weaponskill"] = weaponskill_digit
            rolls[f"{roll_prefix}WeaponskillRoll"] = weaponskill_digit
            rolls[f"{roll_prefix}WeaponskillWeapon"] = weaponskill_weapon
        if next_book == 2:
            rolls["Book2Armoury"] = choice_ids
        elif next_book == 3:
            rolls["Book3Equipment"] = choice_ids
        elif next_book == 4:
            rolls["Book4Equipment"] = choice_ids
        else:
            rolls["Book5Equipment"] = choice_ids
        self.character["CreationRolls"] = rolls

        self.state["CurrentBookStats"] = {
            "BookNumber": next_book,
            "BookTitle": BOOKS[next_book]["Title"],
            "StartSection": 1,
            "LastSection": 1,
            "SectionsVisited": 0,
            "VisitedSections": [],
            "StartingEnduranceMax": int(self.character["EnduranceMax"]),
            "StartingGoldCrowns": int(self.inventory.get("GoldCrowns") or 0),
            f"Book{next_book}GoldRoll": gold_digit,
            "NewKaiDiscipline": selected_discipline,
        }
        if weaponskill_digit is not None:
            self.state["CurrentBookStats"]["WeaponskillRoll"] = weaponskill_digit
            self.state["CurrentBookStats"]["WeaponskillWeapon"] = weaponskill_weapon
        if next_book == 2:
            self.state["CurrentBookStats"]["Book2ArmouryChoices"] = choice_labels
        elif next_book == 3:
            self.state["CurrentBookStats"]["Book3EquipmentChoices"] = choice_labels
        elif next_book == 4:
            self.state["CurrentBookStats"]["Book4EquipmentChoices"] = choice_labels
        else:
            self.state["CurrentBookStats"]["Book5EquipmentChoices"] = choice_labels
            self.state["CurrentBookStats"]["Book5SafekeepingSpecialItems"] = as_list(
                self.automation.get("Stored", {}).get("safekeepingSpecialItems")
            )
            self.state["CurrentBookStats"]["Book5SafekeepingRecords"] = json_clone(
                self.automation.get("Stored", {}).get("safekeepingRecords", [])
            )
        self.automation["Ending"] = None
        self.record_section_visit()
        self.save_section_checkpoint("ready")
        self.write_current_position()
        self.autosave()
        print(f"Advanced to Book {next_book}: {BOOKS[next_book]['Title']}")
        for message in messages:
            print(message)

    def book_start_checkpoint(self, book_number: int) -> dict[str, Any] | None:
        checkpoints = [
            checkpoint
            for checkpoint in self.section_checkpoints()
            if int(checkpoint.get("BookNumber") or 0) == int(book_number)
            and int(checkpoint.get("Section") or 0) == 1
            and isinstance(checkpoint.get("Snapshot"), dict)
        ]
        return checkpoints[-1] if checkpoints else None

    def repeat_completed_book_from_start_checkpoint(self, book_number: int) -> bool:
        checkpoint = self.book_start_checkpoint(book_number)
        if not checkpoint:
            print(f"Book {book_number} start checkpoint is not available for repeat.")
            return False

        snapshot = checkpoint.get("Snapshot")
        if not isinstance(snapshot, dict):
            print(f"Book {book_number} start checkpoint is missing its saved state.")
            return False

        save_path = str(self.settings.get("SavePath") or "")
        achievements = json_clone(self.state.get("Achievements"))
        book_history = json_clone(as_list(self.state.get("BookHistory")))
        combat_history = json_clone(as_list(self.state.get("CombatHistory")))
        completed_books = sorted(
            {int(item) for item in as_list(self.character.get("CompletedBooks")) if str(item).strip()}
            | {book_number}
        )
        notes = json_clone(as_list(self.character.get("Notes")))
        settings = json_clone(self.state.get("Settings"))
        automation_enabled = bool(self.automation.get("Enabled", True))

        restored = normalize_state(json_clone(snapshot))
        restored["CurrentSection"] = 1
        restored["Character"]["CompletedBooks"] = completed_books
        restored["Character"]["Notes"] = notes
        restored["Character"]["EnduranceCurrent"] = int(restored["Character"]["EnduranceMax"])
        restored["Character"]["CombatSkillCurrent"] = int(restored["Character"]["CombatSkillBase"])
        restored["Combat"] = json_clone(default_state()["Combat"])
        restored["Combat"]["StartedSection"] = 1
        restored["SectionHistory"] = []
        restored["BookHistory"] = book_history
        restored["CombatHistory"] = combat_history
        restored["Achievements"] = achievements if isinstance(achievements, dict) else default_achievements()
        restored["Settings"] = settings if isinstance(settings, dict) else default_state()["Settings"]
        restored["Settings"]["SavePath"] = save_path
        restored["Settings"]["AutoSave"] = True
        repeat_stored = (
            json_clone(restored.get("Automation", {}).get("Stored"))
            if isinstance(restored.get("Automation", {}).get("Stored"), dict)
            else {}
        )
        restored["Automation"] = default_automation()
        restored["Automation"]["Enabled"] = automation_enabled
        safekeeping_items = as_list(repeat_stored.get("safekeepingSpecialItems"))
        safekeeping_records = repeat_stored.get("safekeepingRecords")
        if safekeeping_items:
            restored["Automation"]["Stored"]["safekeepingSpecialItems"] = safekeeping_items
        if isinstance(safekeeping_records, list) and safekeeping_records:
            restored["Automation"]["Stored"]["safekeepingRecords"] = json_clone(safekeeping_records)
        restored["CurrentBookStats"] = {
            "BookNumber": book_number,
            "BookTitle": BOOKS[book_number]["Title"],
            "StartSection": 1,
            "LastSection": 1,
            "SectionsVisited": 0,
            "VisitedSections": [],
            "StartingEnduranceMax": int(restored["Character"]["EnduranceMax"]),
            "StartingGoldCrowns": int(restored["Inventory"].get("GoldCrowns") or 0),
        }

        self.state = normalize_state(restored)
        self.record_section_visit()
        self.save_section_checkpoint("ready")
        self.write_current_position()
        self.autosave()
        print(
            f"Restarted Book {book_number}: {BOOKS[book_number]['Title']} "
            f"with END {self.character['EnduranceCurrent']}/{self.character['EnduranceMax']} "
            f"and CS {self.character['CombatSkillCurrent']}."
        )
        return True

    def repeat_completed_book(self) -> None:
        completion = self.book_completion_payload()
        if not completion.get("Active"):
            print("No completed book is ready to repeat.")
            return

        summary = completion.get("Summary") if isinstance(completion.get("Summary"), dict) else {}
        book_number = int(summary.get("BookNumber") or self.character["BookNumber"])
        self.ensure_book_completed(book_number)

        if book_number != 1:
            if self.repeat_completed_book_from_start_checkpoint(book_number):
                return
            print(f"Book {book_number} repeat is not enabled because no start checkpoint is available yet.")
            return

        def saved_digit(key: str, fallback: int) -> int:
            rolls = self.character.get("CreationRolls")
            raw = rolls.get(key) if isinstance(rolls, dict) else None
            try:
                value = int(raw)
            except (TypeError, ValueError):
                value = int(fallback)
            return max(0, min(9, value))

        def current_weaponskill_roll() -> int | None:
            rolls = self.character.get("CreationRolls")
            if isinstance(rolls, dict):
                raw = rolls.get("Weaponskill")
                if raw is not None:
                    try:
                        return max(0, min(9, int(raw)))
                    except (TypeError, ValueError):
                        pass
            current_weapon = str(self.character.get("WeaponskillWeapon") or "")
            for digit, weapon in WEAPONSKILL_MAP.items():
                if str(weapon).lower() == current_weapon.lower():
                    return int(digit)
            return None

        name = str(self.character.get("Name") or "Lone Wolf")
        kai_disciplines = as_list(self.character.get("KaiDisciplines"))
        completed_books = sorted({int(item) for item in as_list(self.character.get("CompletedBooks")) if str(item).strip()} | {1})
        notes = as_list(self.character.get("Notes"))
        achievements = json_clone(self.state.get("Achievements"))
        book_history = json_clone(as_list(self.state.get("BookHistory")))
        settings = json_clone(self.state.get("Settings"))
        automation_enabled = bool(self.automation.get("Enabled", True))

        combat_roll = saved_digit(
            "CombatSkill",
            int(self.character.get("CombatSkillBase") or self.character.get("CombatSkillCurrent") or 10) - 10,
        )
        endurance_roll = saved_digit(
            "Endurance",
            int(self.character.get("EnduranceBase") or self.character.get("EnduranceMax") or 20) - 20,
        )
        gold_roll = saved_digit("GoldCrowns", 0)
        starting_find_roll = saved_digit("StartingFind", 0)
        weaponskill_roll = current_weaponskill_roll()

        fresh = create_book1_character_state(
            name=name,
            kai_disciplines=kai_disciplines,
            combat_skill_roll=combat_roll,
            endurance_roll=endurance_roll,
            gold_roll=gold_roll,
            starting_find_roll=starting_find_roll,
            weaponskill_roll=weaponskill_roll,
        )

        self.state["CurrentSection"] = 1
        self.state["Character"] = fresh["Character"]
        self.state["Character"]["CompletedBooks"] = completed_books
        self.state["Character"]["Notes"] = notes
        self.state["Inventory"] = fresh["Inventory"]
        self.state["Combat"] = json_clone(default_state()["Combat"])
        self.state["SectionHistory"] = []
        self.state["BookHistory"] = book_history
        self.state["Achievements"] = achievements if isinstance(achievements, dict) else default_achievements()
        self.state["Settings"] = settings if isinstance(settings, dict) else default_state()["Settings"]
        self.state["Automation"] = default_automation()
        self.state["Automation"]["Enabled"] = automation_enabled
        self.state["CurrentBookStats"] = {
            "BookNumber": book_number,
            "BookTitle": BOOKS[book_number]["Title"],
            "StartSection": 1,
            "LastSection": 1,
            "SectionsVisited": 0,
            "VisitedSections": [],
            "StartingEnduranceMax": int(self.character["EnduranceMax"]),
            "StartingGoldCrowns": int(self.inventory.get("GoldCrowns") or 0),
        }
        self.record_section_visit()
        self.save_section_checkpoint("ready")
        self.write_current_position()
        self.autosave()
        print(
            f"Restarted Book {book_number}: {BOOKS[book_number]['Title']} "
            f"with END {self.character['EnduranceCurrent']}/{self.character['EnduranceMax']} "
            f"and CS {self.character['CombatSkillCurrent']}."
        )

    def note_command(self, tokens: list[str]) -> None:
        note = rest_of_line(tokens, 1)
        if not note:
            self.show_notes_screen()
            return
        self.character["Notes"] = as_list(self.character["Notes"]) + [note]
        self.autosave()
        print("Note added.")

    def invoke(self, line: str) -> bool:
        if "\x15" in line:
            line = line.rsplit("\x15", 1)[-1]
        if not line.strip():
            return True

        tokens = line.strip().split()
        command = tokens[0].lower()

        try:
            if command in {"help", "?"}:
                self.show_help()
            elif command == "new":
                self.start_new_game()
                self.autosave()
            elif command in {"sheet", "character", "chart", "action", "actionchart"}:
                self.show_sheet()
            elif command in {"inv", "inventory"}:
                self.show_inventory_screen()
            elif command in {"section", "goto"}:
                if len(tokens) < 2:
                    self.show_sections_screen()
                else:
                    self.set_section(int(tokens[1]))
            elif command == "go":
                if len(tokens) < 2:
                    self.show_choices_screen()
                else:
                    self.set_section(int(tokens[1]))
            elif command == "book":
                if len(tokens) < 2:
                    self.show_sections_screen()
                else:
                    section = int(tokens[2]) if len(tokens) > 2 else None
                    self.set_book(int(tokens[1]), section)
            elif command in {"sections", "current", "path"}:
                self.show_sections_screen()
            elif command in {"choices", "routes", "links"}:
                self.show_choices_screen()
            elif command in {"automation", "effects"}:
                self.apply_current_section_automation()
                if self.death_active():
                    self.show_death_screen()
            elif command == "loot":
                self.loot_command(tokens)
            elif command in {"healing", "heal"}:
                self.apply_healing()
            elif command == "loss":
                if len(tokens) < 4:
                    print("Use: loss <choice-id> <weapon|backpack> <slot-or-item>")
                    self.show_choices_screen()
                else:
                    self.apply_section_loss(tokens[1], tokens[2], rest_of_line(tokens, 3))
            elif command in {"roll", "random"}:
                result = self.roll_current_section()
                print(f"Random digit: {result['Raw']}")
                if result.get("Total") != result.get("Raw"):
                    print(f"Modified total: {result['Total']}")
                if result.get("Outcome"):
                    print(f"Outcome: {result['Outcome']}")
                if result.get("Route"):
                    print(f"Route: section {result['Route']}")
                for message in as_list(result.get("ActionMessages")):
                    print(message)
            elif command in {"wp", "will", "willpower"}:
                print("Book 1 does not use Willpower.")
            elif command in {"end", "endurance"}:
                self.adjust_endurance(tokens)
            elif command == "maxend":
                if len(tokens) < 2:
                    print("Use: maxend <n>")
                else:
                    value = int(tokens[1])
                    if value <= 0:
                        print("Maximum Endurance must be positive.")
                    else:
                        self.character["EnduranceMax"] = value
                        self.character["EnduranceCurrent"] = min(
                            self.character["EnduranceCurrent"], value
                        )
                        self.autosave()
                        print(f"Maximum Endurance: {value}")
            elif command in {"cs", "combatskill"}:
                self.adjust_combat_skill(tokens)
            elif command in {"gold", "crowns", "gc", "nobles"}:
                self.adjust_nobles(tokens)
            elif command == "meal":
                self.meal_command(tokens)
            elif command in {"eat"}:
                self.meal_command(["meal"] + tokens[1:])
            elif command == "add":
                self.add_item(tokens)
            elif command == "drop":
                self.drop_item(tokens)
            elif command == "use":
                self.use_item_command(tokens)
            elif command in {"powers", "magicks", "disciplines"}:
                self.show_powers()
            elif command in {"power", "magick", "discipline"}:
                self.power_command(tokens)
            elif command == "combat":
                self.combat_command(tokens)
                if self.death_active():
                    self.show_death_screen()
            elif command == "death":
                self.show_death_screen()
            elif command in {"repeat", "retry"}:
                self.restore_death_checkpoint("repeat")
            elif command in {"rewind", "recover"}:
                mode = tokens[1] if len(tokens) > 1 else "rewind"
                self.restore_death_checkpoint(mode)
            elif command == "complete":
                self.complete_book()
            elif command == "notes":
                self.show_notes_screen()
            elif command == "note":
                self.note_command(tokens)
            elif command == "stats":
                self.show_stats_screen()
            elif command == "campaign":
                self.show_campaign_screen()
            elif command == "history":
                self.show_history_screen()
            elif command == "save":
                self.save_game(rest_of_line(tokens, 1))
            elif command == "load":
                self.load_game(rest_of_line(tokens, 1))
            elif command == "autosave":
                self.settings["AutoSave"] = True
                self.save_game(quiet=True)
                print("Autosave is always on.")
            elif command in {"quit", "exit"}:
                return False
            else:
                print(f"Unknown command: {command}. Type 'help'.")
        except ValueError:
            print("That command needs a valid number.")
        except Exception as exc:
            print(f"Command error: {exc}")
            with ERROR_LOG_FILE.open("a", encoding="utf-8") as handle:
                handle.write(f"Command error: {exc}\n")
        return True

    def run(self, load_path: str = "") -> None:
        loaded = False
        if load_path:
            loaded = self.load_game(load_path, quiet=True)

        if loaded:
            self.show_sheet()
        else:
            self.show_welcome_screen()
            if self.catalog_saves():
                self.show_load_screen()

        while True:
            try:
                line = input("LW> ")
            except (EOFError, KeyboardInterrupt):
                print("")
                break
            if not self.invoke(line):
                break

        print("Good luck, Lone Wolf.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Lone Wolf Action Assistant Redux")
    parser.add_argument("--load", default="", help="Save file to load")
    parser.add_argument("--save-dir", default=str(DEFAULT_SAVE_DIR), help="Directory for save files")
    parser.add_argument("--data-dir", default=str(DEFAULT_DATA_DIR), help="Directory for bundled reference data")
    parser.add_argument("--state-data-dir", default=str(DEFAULT_STATE_DATA_DIR), help="Directory for writable state")
    parser.add_argument("--books-dir", default=str(DEFAULT_BOOKS_DIR), help="Directory containing Project Aon book folders")
    args = parser.parse_args()

    assistant = LoneWolfReduxAssistant(
        save_dir=Path(args.save_dir),
        data_dir=Path(args.data_dir),
        state_data_dir=Path(args.state_data_dir),
        books_dir=Path(args.books_dir),
    )
    assistant.run(load_path=args.load)


if __name__ == "__main__":
    main()
