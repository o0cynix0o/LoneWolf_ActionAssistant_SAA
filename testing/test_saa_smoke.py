"""Standalone-app smoke tests that don't require licensed book content."""

from __future__ import annotations

import asyncio
import hashlib
import io
import json
import re
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

import app_server
import book_manager
import cheat_session
import lonewolf_redux
import saa_main
import ws_server


class BookImportTests(unittest.TestCase):
    def test_imports_valid_extracted_book(self) -> None:
        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as target_temp:
            source = Path(source_temp) / "books" / "lw" / "01fftd"
            source.mkdir(parents=True)
            (source / "title.htm").write_text("<title>Book 1</title>", encoding="utf-8")
            (source / "sect1.htm").write_text("<p>Section 1</p>", encoding="utf-8")

            result = book_manager.import_books(
                [Path(source_temp)],
                ["01fftd", "02fotw"],
                Path(target_temp),
            )

            self.assertEqual(result["Imported"], ["01fftd"])
            self.assertTrue((Path(target_temp) / "01fftd" / "sect1.htm").is_file())

    def test_rejects_zip_path_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as target_temp:
            archive = Path(source_temp) / "unsafe.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                bundle.writestr("../outside.txt", "unsafe")
            with self.assertRaisesRegex(ValueError, "Unsafe ZIP entry"):
                book_manager.import_books([archive], ["01fftd"], Path(target_temp))

    def test_imports_standard_project_aon_zip_layout(self) -> None:
        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as target_temp:
            archive = Path(source_temp) / "01fftd.zip"
            with zipfile.ZipFile(archive, "w") as bundle:
                root = "en/xhtml/lw/01fftd"
                bundle.writestr(f"{root}/title.htm", "<title>Book 1</title>")
                bundle.writestr(f"{root}/sect1.htm", "<p>Section 1</p>")

            result = book_manager.import_books([archive], ["01fftd"], Path(target_temp))

            self.assertEqual(result["Imported"], ["01fftd"])
            self.assertTrue((Path(target_temp) / "01fftd" / "sect1.htm").is_file())


class SupportedBookDataBaselineTests(unittest.TestCase):
    """Protect the complete supported-book baseline and its automation data."""

    def test_supported_books_have_loaded_automation_and_flow_data(self) -> None:
        expected_books = set(range(1, 30))
        self.assertEqual(set(lonewolf_redux.BOOKS), expected_books)

        root = Path(lonewolf_redux.__file__).resolve().parent
        for book_number in expected_books:
            self.assertTrue((root / "data" / f"book{book_number}-section-flows.json").is_file())
        for book_number in range(1, 13):
            self.assertTrue((root / "data" / f"book{book_number}-simple-automations.json").is_file())

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=root / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )

        self.assertTrue(set(range(1, 13)).issubset({int(key) for key in assistant.section_automation}))
        self.assertTrue(expected_books.issubset({int(key) for key in assistant.section_flows}))

    def test_magnakai_catalog_entries_remain_available_for_play_and_readers(self) -> None:
        self.assertEqual(
            [lonewolf_redux.book_metadata(number)["Folder"] for number in (6, 7, 8)],
            ["06tkot", "07cd", "08tjoh"],
        )

    def test_books9_to12_have_audited_import_metadata_and_source_baselines(self) -> None:
        audited_books = {
            9: "09tcof",
            10: "10tdot",
            11: "11tpot",
            12: "12tmod",
        }
        self.assertTrue(set(audited_books).issubset(lonewolf_redux.BOOKS))
        self.assertEqual(
            {number: lonewolf_redux.book_metadata(number)["Folder"] for number in audited_books},
            audited_books,
        )

        root = Path(lonewolf_redux.__file__).resolve().parent
        for book_number in audited_books:
            flow_path = root / "data" / f"book{book_number}-section-flows.json"
            automation_path = root / "data" / f"book{book_number}-simple-automations.json"
            flows = json.loads(flow_path.read_text(encoding="utf-8"))[str(book_number)]
            self.assertTrue(automation_path.is_file())
            self.assertEqual(set(flows), {str(section) for section in range(1, 351)})
            self.assertTrue(
                all(
                    flow["auditStatus"] in {"source-link-baseline", "source-verified-rnt"}
                    for flow in flows.values()
                )
            )

    def test_book8_completion_offers_the_book9_internal_testing_handoff(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 8
            assistant.ensure_book_completed()

        completion = assistant.book_completion_payload()
        self.assertEqual(completion["NextBookNumber"], 9)
        self.assertTrue(completion["CanContinue"])

    def test_later_magnakai_standalone_setups_follow_the_printed_entry_choices(self) -> None:
        mastered = ["Sword", "Bow", "Axe", "Mace", "Dagger", "Spear", "Quarterstaff", "Warhammer", "Broadsword"]
        cases = {
            9: ["sword", "bow", "quiver", "rope", "laumspur"],
            10: ["sword", "bow", "quiver", "rope", "alether"],
            11: ["sword", "bow", "quiver", "rope", "laumspur", "lantern"],
            12: ["sword", "bow", "quiver", "rope", "laumspur", "lantern"],
        }
        states = {}
        for book_number, choices in cases.items():
            rank = book_number - 3
            state = lonewolf_redux.create_magnakai_character_state(
                book_number=book_number,
                magnakai_disciplines=lonewolf_redux.MAGNAKAI_DISCIPLINES[:rank],
                weaponmastery_weapons=mastered[:rank],
                gold_roll=0,
                equipment_choices=choices,
            )
            self.assertEqual(state["Character"]["MagnakaiRank"], rank)
            self.assertEqual(state["CurrentSection"], 1)
            self.assertEqual(state["Inventory"]["GoldCrowns"], 10)
            states[book_number] = state

        self.assertIn("Eruan Pathfinder Tunic", states[11]["Inventory"]["SpecialItems"])
        self.assertIn("Kalkoth-hide Cape", states[12]["Inventory"]["SpecialItems"])

    def test_later_magnakai_campaign_handoffs_add_only_the_printed_entry_support(self) -> None:
        source = lonewolf_redux.default_state()
        source["Character"].update(
            {
                "BookNumber": 8,
                "MagnakaiDisciplines": [
                    "Weaponmastery", "Animal Control", "Curing", "Invisibility", "Huntmastery",
                ],
                "MagnakaiRank": 5,
                "WeaponmasteryWeapons": ["Sword", "Bow", "Axe", "Mace", "Dagger"],
            }
        )
        source["Inventory"].update(
            {
                "GoldCrowns": 20,
                "Weapons": [],
                "SpecialItems": ["Campaign Keepsake"],
                "BackpackItems": ["Meal"],
            }
        )
        book9 = lonewolf_redux.prepare_later_magnakai_state(
            source,
            book_number=9,
            magnakai_discipline="Pathsmanship",
            weaponmastery_weapon="Spear",
            gold_roll=0,
            equipment_choices=["sword", "bow", "quiver", "rope", "fireseeds"],
        )
        book10 = lonewolf_redux.prepare_later_magnakai_state(
            book9,
            book_number=10,
            magnakai_discipline="Divination",
            weaponmastery_weapon="Quarterstaff",
            gold_roll=0,
            equipment_choices=["quiver", "rope", "laumspur", "lantern", "alether"],
        )
        book11 = lonewolf_redux.prepare_later_magnakai_state(
            book10,
            book_number=11,
            magnakai_discipline="Psi-surge",
            weaponmastery_weapon="Warhammer",
            equipment_choices=[],
        )

        self.assertEqual(book9["Character"]["MagnakaiRank"], 6)
        self.assertEqual(book9["Inventory"]["GoldCrowns"], 30)
        self.assertIn("Campaign Keepsake", book9["Inventory"]["SpecialItems"])
        self.assertIn("Map of the Republic of Anari", book9["Inventory"]["SpecialItems"])
        self.assertEqual(book10["Inventory"]["GoldCrowns"], 40)
        self.assertEqual(book11["Character"]["MagnakaiRank"], 8)
        self.assertEqual(book11["Character"]["Book11Setup"]["EquipmentChoices"], [])

    def test_generic_campaign_dispatch_reaches_books8_and9(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )

            assistant.state["Character"].update(
                {
                    "BookNumber": 7,
                    "MagnakaiDisciplines": ["Animal Control", "Curing", "Invisibility", "Huntmastery"],
                    "MagnakaiRank": 4,
                    "WeaponmasteryWeapons": [],
                }
            )
            assistant.ensure_book_completed()
            assistant.continue_completed_book(
                book6_magnakai_disciplines="Pathsmanship", book6_equipment_choices=[]
            )
            self.assertEqual(assistant.character["BookNumber"], 8)
            assistant.ensure_book_completed()
            assistant.continue_completed_book(
                book6_magnakai_disciplines="Divination",
                book6_gold_roll=0,
                book6_equipment_choices=["quiver", "rope", "laumspur", "lantern", "meals"],
            )
            self.assertEqual(assistant.character["BookNumber"], 9)

    def test_new_order_standalone_and_continuation_preserve_the_action_chart(self) -> None:
        state = lonewolf_redux.create_new_order_character_state(
            book_number=21,
            new_order_disciplines=[
                "Grand Weaponmastery", "Animal Mastery", "Deliverance", "Astrology", "Herbmastery"
            ],
            grand_weaponmastery_weapons=["Sword"],
            kai_weapon_roll=3,
            combat_skill_roll=0,
            endurance_roll=0,
            gold_roll=0,
            equipment_choices=["quarterstaff", "quiver", "flute", "meals", "rope"],
        )
        self.assertEqual(state["RuleSet"], "New Order")
        self.assertEqual(state["Character"]["KaiWeapon"]["Name"], "Sunstrike")
        self.assertEqual(state["Character"]["NewOrderRank"], 5)

        advanced = lonewolf_redux.prepare_new_order_state(
            state,
            book_number=22,
            new_order_disciplines=["Elementalism"],
            grand_weaponmastery_weapons=["Axe"],
            gold_roll=0,
            equipment_choices=["bow", "quiver", "flute", "meals", "laumspur"],
        )
        self.assertEqual(advanced["Character"]["BookNumber"], 22)
        self.assertEqual(advanced["Character"]["NewOrderRank"], 6)
        self.assertEqual(advanced["Character"]["GrandWeaponmasteryWeapons"], ["Sword", "Axe"])
        self.assertEqual(advanced["Inventory"]["GoldCrowns"], 40)

    def test_every_new_order_standalone_setup_round_trips_through_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            for book_number in range(21, 30):
                discipline_count = 5 + (book_number - 21)
                mastery_count = 1 + (book_number - 21)
                options = lonewolf_redux.NEW_ORDER_EQUIPMENT_OPTIONS[book_number]
                equipment_choices = [
                    option_id
                    for option_id, option in options.items()
                    if not any(container == "weapon" for container, _ in option.get("Items", []))
                ][:5]
                state = lonewolf_redux.create_new_order_character_state(
                    book_number=book_number,
                    new_order_disciplines=lonewolf_redux.NEW_ORDER_DISCIPLINES[:discipline_count],
                    grand_weaponmastery_weapons=lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[:mastery_count],
                    kai_weapon_roll=4,
                    combat_skill_roll=0,
                    endurance_roll=0,
                    gold_roll=0,
                    equipment_choices=equipment_choices,
                )
                assistant = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                    state_data_dir=base / "state", books_dir=base / "books",
                )
                assistant.state = state
                save_path = base / f"book{book_number}.json"
                self.assertTrue(assistant.save_game(str(save_path), quiet=True))

                restored = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / "restored", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                    state_data_dir=base / "restored-state", books_dir=base / "books",
                )
                self.assertTrue(restored.load_game(str(save_path), quiet=True))
                self.assertEqual(restored.character["BookNumber"], book_number)
                self.assertEqual(restored.character["NewOrderRank"], discipline_count)
                self.assertEqual(
                    restored.character["GrandWeaponmasteryWeapons"],
                    lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[:mastery_count],
                )
                self.assertEqual(restored.character["KaiWeapon"]["Name"], "Kaistar")

    def test_every_grand_master_standalone_setup_round_trips_through_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            for book_number in range(13, 21):
                discipline_count = 4 + (book_number - 13)
                mastery_count = 2 + (book_number - 13)
                options = lonewolf_redux.GRAND_MASTER_EQUIPMENT_OPTIONS[book_number]
                non_weapon_choices = [
                    option_id
                    for option_id, option in options.items()
                    if not any(container == "weapon" for container, _ in option.get("Items", []))
                ]
                weapon_choices = [
                    option_id
                    for option_id, option in options.items()
                    if any(container == "weapon" for container, _ in option.get("Items", []))
                ]
                equipment_choices = (
                    non_weapon_choices + weapon_choices[:2]
                )[:lonewolf_redux.grand_master_field_issue_count(book_number)]
                state = lonewolf_redux.create_grand_master_character_state(
                    book_number=book_number,
                    grand_master_disciplines=lonewolf_redux.GRAND_MASTER_DISCIPLINES[:discipline_count],
                    grand_weaponmastery_weapons=lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[:mastery_count],
                    combat_skill_roll=0,
                    endurance_roll=0,
                    gold_roll=0,
                    equipment_choices=equipment_choices,
                )
                assistant = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                    state_data_dir=base / "state", books_dir=base / "books",
                )
                assistant.state = state
                save_path = base / f"grand-master-book{book_number}.json"
                self.assertTrue(assistant.save_game(str(save_path), quiet=True))

                restored = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / "restored", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                    state_data_dir=base / "restored-state", books_dir=base / "books",
                )
                self.assertTrue(restored.load_game(str(save_path), quiet=True))
                self.assertEqual(restored.character["BookNumber"], book_number)
                self.assertEqual(restored.character["GrandMasterRank"], discipline_count)
                self.assertEqual(
                    restored.character["GrandWeaponmasteryWeapons"],
                    lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[:mastery_count],
                )

    def test_full_backpack_can_be_trimmed_during_a_book2_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 1
            assistant.state["Inventory"]["BackpackItems"] = [f"Pack item {index}" for index in range(8)]
            assistant.ensure_book_completed()
            assistant.continue_completed_book(
                kai_discipline="Camouflage",
                book2_gold_roll=0,
                book2_armoury_choices=["two-meals", "healing-potion"],
                transition_drops=["backpack:0", "backpack:1", "backpack:2"],
            )

        self.assertEqual(assistant.character["BookNumber"], 2)
        self.assertEqual(len(assistant.inventory["BackpackItems"]), 8)
        self.assertEqual(assistant.character["Book2Setup"]["TransitionDrops"], [("backpack", 0), ("backpack", 1), ("backpack", 2)])

    def test_books6_to8_keep_a_full_backpack_until_the_player_selects_drops(self) -> None:
        state = lonewolf_redux.default_state()
        state["Character"].update({"BookNumber": 5, "MagnakaiDisciplines": [], "WeaponmasteryWeapons": []})
        state["Inventory"]["BackpackItems"] = [f"Pack item {index}" for index in range(8)]
        book6 = lonewolf_redux.prepare_book6_state(
            state,
            magnakai_disciplines=["Animal Control", "Curing", "Invisibility"],
            equipment_choices=["laumspur"],
            transition_drops=["backpack:0"],
        )
        book7 = lonewolf_redux.prepare_book7_state(
            book6, magnakai_discipline="Huntmastery", equipment_choices=["laumspur"],
            transition_drops=["backpack:0"],
        )
        book8 = lonewolf_redux.prepare_book8_state(
            book7, magnakai_discipline="Pathsmanship", equipment_choices=["laumspur"],
            transition_drops=["backpack:0"],
        )

        self.assertEqual(len(book6["Inventory"]["BackpackItems"]), 8)
        self.assertEqual(len(book7["Inventory"]["BackpackItems"]), 8)
        self.assertEqual(len(book8["Inventory"]["BackpackItems"]), 8)
        self.assertIn("Pack item 3", book8["Inventory"]["BackpackItems"])
        self.assertNotIn("Pack item 0", book6["Inventory"]["BackpackItems"])
        self.assertEqual(book8["Character"]["Book8Setup"]["TransitionDrops"], [("backpack", 0)])

    def test_later_magnakai_campaign_can_continue_through_book12_and_end_cleanly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"].update(
                {
                    "BookNumber": 8,
                    "MagnakaiDisciplines": [
                        "Weaponmastery", "Animal Control", "Curing", "Invisibility", "Huntmastery",
                    ],
                    "MagnakaiRank": 5,
                    "WeaponmasteryWeapons": ["Sword", "Bow", "Axe", "Mace", "Dagger"],
                }
            )
            assistant.state["Inventory"].update({"Weapons": ["Sword"], "SpecialItems": ["Campaign Keepsake"]})

            assistant.ensure_book_completed()
            self.assertEqual(assistant.open_next_book(), 9)
            assistant.continue_to_later_magnakai(
                book_number=9, magnakai_discipline="Pathsmanship", weaponmastery_weapon="Spear",
                gold_roll=0, equipment_choices=["quiver", "rope", "laumspur", "lantern", "meals"],
            )
            self.assertEqual((assistant.character["BookNumber"], assistant.character["MagnakaiRank"]), (9, 6))
            self.assertIn("Campaign Keepsake", assistant.inventory["SpecialItems"])

            assistant.ensure_book_completed()
            assistant.continue_to_later_magnakai(
                book_number=10, magnakai_discipline="Divination", weaponmastery_weapon="Quarterstaff",
                gold_roll=0, equipment_choices=["quiver", "rope", "laumspur", "lantern", "meals"],
                transition_drops=[f"backpack:{index}" for index in range(7)],
            )
            assistant.ensure_book_completed()
            assistant.continue_to_later_magnakai(
                book_number=11, magnakai_discipline="Psi-surge", weaponmastery_weapon="Warhammer",
                equipment_choices=[],
            )
            self.assertEqual(assistant.character["Book11Setup"]["EquipmentChoices"], [])

            assistant.ensure_book_completed()
            assistant.continue_to_later_magnakai(
                book_number=12, magnakai_discipline="Psi-screen", weaponmastery_weapon="Broadsword",
                gold_roll=0, equipment_choices=["quiver", "rope", "laumspur", "lantern", "meals", "dagger"],
                transition_drops=[f"backpack:{index}" for index in range(6)],
            )
            assistant.ensure_book_completed()
            completion = assistant.book_completion_payload()

        self.assertEqual((assistant.character["BookNumber"], assistant.character["MagnakaiRank"]), (12, 9))
        self.assertTrue(completion["CanContinue"])
        self.assertEqual(completion["NextBookNumber"], 13)
        self.assertEqual(assistant.run_state["Status"], "Active")

    def test_grand_master_creation_and_book12_handoff_preserve_source_rules(self) -> None:
        standalone = lonewolf_redux.create_grand_master_character_state(
            book_number=13,
            grand_master_disciplines=[
                "Grand Weaponmastery",
                "Grand Huntmastery",
                "Kai-surge",
                "Kai-alchemy",
            ],
            grand_weaponmastery_weapons=["Sword", "Bow"],
            combat_skill_roll=6,
            endurance_roll=7,
            gold_roll=4,
            equipment_choices=["quiver", "axe", "meals", "rope", "laumspur"],
        )
        self.assertEqual(standalone["Character"]["BookNumber"], 13)
        self.assertEqual(standalone["Character"]["GrandMasterRank"], 4)
        self.assertEqual(standalone["Inventory"]["BackpackCapacity"], 10)
        self.assertEqual(standalone["Character"]["CombatSkillBase"], 31)
        self.assertEqual(standalone["Character"]["EnduranceBase"], 37)
        self.assertIn("Map of the Dark Realm of Ruel", standalone["Inventory"]["SpecialItems"])

        book12_state = lonewolf_redux.default_state()
        book12_state["Character"].update(
            {
                "BookNumber": 12,
                "CombatSkillBase": 25,
                "EnduranceBase": 35,
                "CombatSkillCurrent": 25,
                "EnduranceCurrent": 35,
            }
        )
        book12_state["Inventory"].update(
            {
                "Weapons": ["Sword"],
                "BackpackItems": ["Meal"] * 8,
                "SpecialItems": ["Sommerswerd", "Map of the Stornlands"],
            }
        )
        book13_state = lonewolf_redux.prepare_grand_master_state(
            book12_state,
            book_number=13,
            grand_master_disciplines=[
                "Grand Weaponmastery",
                "Grand Huntmastery",
                "Kai-surge",
                "Kai-alchemy",
            ],
            grand_weaponmastery_weapons=["Sword", "Bow"],
            equipment_choices=["quiver", "axe", "meals", "rope", "laumspur"],
            gold_roll=4,
            transition_drops=["backpack:7", "backpack:6", "backpack:5", "backpack:4"],
        )
        self.assertEqual(book13_state["Inventory"]["Weapons"], ["Sword", "Axe"])
        self.assertEqual(book13_state["Inventory"]["BackpackCapacity"], 10)
        self.assertEqual(book13_state["Character"]["GrandWeaponmasteryWeapons"], ["Sword", "Bow"])

        book14_state = lonewolf_redux.prepare_grand_master_state(
            book13_state,
            book_number=14,
            grand_master_disciplines=["Animal Mastery"],
            grand_weaponmastery_weapons=["Axe"],
            equipment_choices=["quiver", "meals", "rope", "laumspur", "dagger"],
            gold_roll=5,
            transition_drops=[
                "weapon:1",
                "backpack:9",
                "backpack:8",
                "backpack:7",
                "backpack:6",
                "backpack:5",
                "backpack:4",
            ],
        )
        self.assertEqual(book14_state["Character"]["GrandMasterRank"], 5)
        self.assertEqual(book14_state["Character"]["CombatSkillBase"], 26)
        self.assertEqual(book14_state["Character"]["EnduranceBase"], 37)
        self.assertEqual(book14_state["Character"]["GrandWeaponmasteryWeapons"], ["Sword", "Bow", "Axe"])
        self.assertEqual(book14_state["Inventory"]["Weapons"], ["Sword", "Dagger"])

    def test_grand_master_campaign_spine_survives_all_modes_and_book_handoffs(self) -> None:
        configurations = [
            ("Story", False),
            ("Easy", False), ("Easy", True),
            ("Normal", False), ("Normal", True),
            ("Hard", False), ("Hard", True),
            ("Veteran", False), ("Veteran", True),
        ]

        def field_issue(book_number: int) -> list[str]:
            choices = ["quiver", "meals", "rope", "laumspur"]
            return (["sword"] + choices) if lonewolf_redux.grand_master_field_issue_count(book_number) == 5 else choices

        def transition_drops(assistant: lonewolf_redux.LoneWolfReduxAssistant, book_number: int, choices: list[str]) -> list[str]:
            options = lonewolf_redux.GRAND_MASTER_EQUIPMENT_OPTIONS[book_number]
            added_weapons = sum(
                1 for choice in choices for container, _item in options[choice]["Items"] if container == "weapon"
            )
            added_backpack_slots = sum(
                lonewolf_redux.item_slot_cost(item)
                for choice in choices
                for container, item in options[choice]["Items"]
                if container == "backpack"
            )
            weapon_drops = max(0, len(assistant.inventory["Weapons"]) + added_weapons - 2)
            backpack_drops = max(
                0,
                lonewolf_redux.item_slot_total(assistant.inventory["BackpackItems"])
                + added_backpack_slots
                - lonewolf_redux.backpack_capacity(assistant.inventory),
            )
            return (
                [f"weapon:{index}" for index in range(weapon_drops)]
                + [f"backpack:{index}" for index in range(backpack_drops)]
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = Path(lonewolf_redux.__file__).resolve().parent
            for difficulty, permadeath in configurations:
                for combat_mode in ("DataFile", "ManualCRT"):
                    label = f"{difficulty}-{permadeath}-{combat_mode}"
                    assistant = lonewolf_redux.LoneWolfReduxAssistant(
                        save_dir=base / label / "saves", data_dir=root / "data",
                        state_data_dir=base / label / "state", books_dir=base / label / "books",
                    )
                    assistant.state = lonewolf_redux.create_grand_master_character_state(
                        book_number=13,
                        grand_master_disciplines=lonewolf_redux.GRAND_MASTER_DISCIPLINES[:4],
                        grand_weaponmastery_weapons=lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[:2],
                        combat_skill_roll=0,
                        endurance_roll=0,
                        gold_roll=0,
                        equipment_choices=field_issue(13),
                    )
                    assistant.set_run_configuration(difficulty, permadeath, combat_mode)

                    with redirect_stdout(io.StringIO()):
                        assistant.set_section(125)
                        assistant.start_section_combat()
                        if combat_mode == "ManualCRT":
                            assistant.combat_round(["combat", "manual"], manual_losses=(1, 0))
                        else:
                            assistant.combat_round(["combat", "round", "0"])
                    self.assertTrue(assistant.combat["Active"], label)
                    with redirect_stdout(io.StringIO()):
                        assistant.stop_combat()

                    for book_number in range(13, 21):
                        if book_number == 16:
                            checkpoint = base / label / "book16.json"
                            self.assertTrue(assistant.save_game(str(checkpoint), quiet=True), label)
                            resumed = lonewolf_redux.LoneWolfReduxAssistant(
                                save_dir=base / label / "resumed-saves", data_dir=root / "data",
                                state_data_dir=base / label / "resumed-state", books_dir=base / label / "books",
                            )
                            self.assertTrue(resumed.load_game(str(checkpoint), quiet=True), label)
                            assistant = resumed
                            self.assertEqual(assistant.combat_mode(), combat_mode, label)
                            self.assertEqual(assistant.difficulty(), difficulty, label)
                            self.assertEqual(assistant.permadeath_enabled(), permadeath and difficulty != "Story", label)

                        assistant.ensure_book_completed(book_number)
                        completion = assistant.book_completion_payload()
                        if book_number == 20:
                            self.assertFalse(completion["CanContinue"], label)
                            self.assertEqual(assistant.run_state["Status"], "Completed", label)
                            continue

                        with redirect_stdout(io.StringIO()):
                            opened = assistant.open_next_book()
                        self.assertEqual(opened, book_number + 1, label)
                        next_book = book_number + 1
                        choices = field_issue(next_book)
                        with redirect_stdout(io.StringIO()):
                            assistant.continue_completed_book(
                                grand_master_disciplines=[lonewolf_redux.GRAND_MASTER_DISCIPLINES[next_book - 10]],
                                grand_weaponmastery_weapons=[lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[next_book - 12]],
                                book6_gold_roll=0,
                                book6_equipment_choices=choices,
                                transition_drops=transition_drops(assistant, next_book, choices),
                            )
                        self.assertEqual(assistant.character["BookNumber"], next_book, label)
                        self.assertEqual(assistant.state["CurrentSection"], 1, label)
                        self.assertLessEqual(len(assistant.inventory["Weapons"]), 2, label)
                        self.assertLessEqual(
                            lonewolf_redux.item_slot_total(assistant.inventory["BackpackItems"]),
                            lonewolf_redux.backpack_capacity(assistant.inventory),
                            label,
                        )

    def test_every_grand_master_combat_preset_starts_in_both_crt_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = Path(lonewolf_redux.__file__).resolve().parent
            for combat_mode in ("DataFile", "ManualCRT"):
                assistant = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / combat_mode / "saves", data_dir=root / "data",
                    state_data_dir=base / combat_mode / "state", books_dir=base / combat_mode / "books",
                )
                assistant.set_run_configuration("Veteran", True, combat_mode)
                assistant.autosave = lambda: None
                for book_number in range(13, 21):
                    combat_sections = [
                        int(section)
                        for section, flow in assistant.section_flows[str(book_number)].items()
                        if isinstance(flow, dict) and flow.get("combat")
                    ]
                    for section in combat_sections:
                        assistant.state = lonewolf_redux.normalize_state({
                            "Character": {
                                "BookNumber": book_number,
                                "CombatSkillCurrent": 99,
                                "EnduranceCurrent": 99,
                                "EnduranceMax": 99,
                                "GrandMasterRank": 11,
                                "GrandMasterDisciplines": lonewolf_redux.GRAND_MASTER_DISCIPLINES,
                                "GrandWeaponmasteryWeapons": lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS,
                            },
                            "Inventory": {
                                "Weapons": ["Sommerswerd", "Sword"],
                                "BackpackItems": ["Rope", "Lantern", "Meal"],
                                "SpecialItems": ["Dagger of Vashna", "Helshezag", "Sommerswerd"],
                            },
                            "CurrentSection": section,
                        })
                        assistant.set_run_configuration("Veteran", True, combat_mode)
                        with redirect_stdout(io.StringIO()):
                            assistant.start_section_combat()
                            self.assertTrue(assistant.combat["Active"], (combat_mode, book_number, section))
                            if combat_mode == "ManualCRT":
                                assistant.combat_round(["combat", "manual"], manual_losses=(1, 0))
                            else:
                                assistant.combat_round(["combat", "round", "0"])

    def test_new_order_campaign_spine_survives_all_modes_and_book_handoffs(self) -> None:
        configurations = [
            ("Story", False),
            ("Easy", False), ("Easy", True),
            ("Normal", False), ("Normal", True),
            ("Hard", False), ("Hard", True),
            ("Veteran", False), ("Veteran", True),
        ]

        def field_issue(book_number: int) -> list[str]:
            instrument = "lute" if book_number in {24, 25} else "flute"
            return ["quiver", instrument, "meals", "rope", "laumspur"]

        def transition_drops(assistant: lonewolf_redux.LoneWolfReduxAssistant, book_number: int, choices: list[str]) -> list[str]:
            options = lonewolf_redux.NEW_ORDER_EQUIPMENT_OPTIONS[book_number]
            added_weapons = sum(
                1 for choice in choices for container, _item in options[choice]["Items"] if container == "weapon"
            )
            added_backpack_slots = sum(
                lonewolf_redux.item_slot_cost(item)
                for choice in choices
                for container, item in options[choice]["Items"]
                if container == "backpack"
            )
            weapon_drops = max(0, len(assistant.inventory["Weapons"]) + added_weapons - 2)
            backpack_drops = max(
                0,
                lonewolf_redux.item_slot_total(assistant.inventory["BackpackItems"])
                + added_backpack_slots
                - lonewolf_redux.backpack_capacity(assistant.inventory),
            )
            return (
                [f"weapon:{index}" for index in range(weapon_drops)]
                + [f"backpack:{index}" for index in range(backpack_drops)]
            )

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = Path(lonewolf_redux.__file__).resolve().parent
            for difficulty, permadeath in configurations:
                for combat_mode in ("DataFile", "ManualCRT"):
                    label = f"{difficulty}-{permadeath}-{combat_mode}"
                    assistant = lonewolf_redux.LoneWolfReduxAssistant(
                        save_dir=base / label / "saves", data_dir=root / "data",
                        state_data_dir=base / label / "state", books_dir=base / label / "books",
                    )
                    assistant.state = lonewolf_redux.create_new_order_character_state(
                        book_number=21,
                        new_order_disciplines=lonewolf_redux.NEW_ORDER_DISCIPLINES[:5],
                        grand_weaponmastery_weapons=lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[:1],
                        kai_weapon_roll=0,
                        combat_skill_roll=0,
                        endurance_roll=0,
                        gold_roll=0,
                        equipment_choices=field_issue(21),
                    )
                    assistant.set_run_configuration(difficulty, permadeath, combat_mode)

                    for book_number in range(21, 30):
                        combat_sections = [
                            int(section)
                            for section, flow in assistant.section_flows[str(book_number)].items()
                            if isinstance(flow, dict) and flow.get("combat")
                        ]
                        with redirect_stdout(io.StringIO()):
                            assistant.set_section(combat_sections[0])
                            assistant.start_section_combat()
                            self.assertTrue(assistant.combat["Active"], label)
                            if combat_mode == "ManualCRT":
                                assistant.combat_round(["combat", "manual"], manual_losses=(1, 0))
                            else:
                                assistant.combat_round(["combat", "round", "0"])
                            assistant.stop_combat()

                        if book_number == 25:
                            checkpoint = base / label / "book25.json"
                            self.assertTrue(assistant.save_game(str(checkpoint), quiet=True), label)
                            resumed = lonewolf_redux.LoneWolfReduxAssistant(
                                save_dir=base / label / "resumed-saves", data_dir=root / "data",
                                state_data_dir=base / label / "resumed-state", books_dir=base / label / "books",
                            )
                            self.assertTrue(resumed.load_game(str(checkpoint), quiet=True), label)
                            assistant = resumed
                            self.assertEqual(assistant.combat_mode(), combat_mode, label)
                            self.assertEqual(assistant.difficulty(), difficulty, label)
                            self.assertEqual(assistant.permadeath_enabled(), permadeath and difficulty != "Story", label)

                        assistant.ensure_book_completed(book_number)
                        completion = assistant.book_completion_payload()
                        if book_number == 29:
                            self.assertFalse(completion["CanContinue"], label)
                            self.assertEqual(assistant.run_state["Status"], "Completed", label)
                            continue

                        with redirect_stdout(io.StringIO()):
                            opened = assistant.open_next_book()
                        self.assertEqual(opened, book_number + 1, label)
                        next_book = book_number + 1
                        choices = field_issue(next_book)
                        with redirect_stdout(io.StringIO()):
                            assistant.continue_completed_book(
                                new_order_disciplines=[lonewolf_redux.NEW_ORDER_DISCIPLINES[next_book - 17]],
                                grand_weaponmastery_weapons=[lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS[next_book - 21]],
                                book6_gold_roll=0,
                                book6_equipment_choices=choices,
                                transition_drops=transition_drops(assistant, next_book, choices),
                            )
                        self.assertEqual(assistant.character["BookNumber"], next_book, label)
                        self.assertEqual(assistant.state["CurrentSection"], 1, label)
                        self.assertEqual(assistant.character["NewOrderRank"], 5 + (next_book - 21), label)
                        self.assertLessEqual(len(assistant.inventory["Weapons"]), 2, label)
                        self.assertLessEqual(
                            lonewolf_redux.item_slot_total(assistant.inventory["BackpackItems"]),
                            lonewolf_redux.backpack_capacity(assistant.inventory),
                            label,
                        )

    def test_every_new_order_combat_preset_starts_in_both_crt_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = Path(lonewolf_redux.__file__).resolve().parent
            for combat_mode in ("DataFile", "ManualCRT"):
                assistant = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / combat_mode / "saves", data_dir=root / "data",
                    state_data_dir=base / combat_mode / "state", books_dir=base / combat_mode / "books",
                )
                assistant.set_run_configuration("Veteran", True, combat_mode)
                assistant.autosave = lambda: None
                for book_number in range(21, 30):
                    combat_sections = [
                        int(section)
                        for section, flow in assistant.section_flows[str(book_number)].items()
                        if isinstance(flow, dict) and flow.get("combat")
                    ]
                    for section in combat_sections:
                        kai_weapon = lonewolf_redux.kai_weapon_for_roll(0)
                        assistant.state = lonewolf_redux.normalize_state({
                            "Character": {
                                "BookNumber": book_number,
                                "CombatSkillCurrent": 99,
                                "EnduranceCurrent": 99,
                                "EnduranceMax": 99,
                                "NewOrderRank": len(lonewolf_redux.NEW_ORDER_DISCIPLINES),
                                "NewOrderDisciplines": lonewolf_redux.NEW_ORDER_DISCIPLINES,
                                "GrandMasterDisciplines": lonewolf_redux.GRAND_MASTER_DISCIPLINES,
                                "GrandWeaponmasteryWeapons": lonewolf_redux.GRAND_WEAPONMASTERY_WEAPONS,
                                "KaiWeapon": kai_weapon,
                            },
                            "Inventory": {
                                "Weapons": ["Sword", "Axe"],
                                "BackpackItems": ["Rope", "Lantern", "Meal"],
                                "SpecialItems": [f"Kai Weapon: {kai_weapon['Name']}", "Quiver"],
                                "QuiverArrows": 12,
                            },
                            "CurrentSection": section,
                        })
                        assistant.set_run_configuration("Veteran", True, combat_mode)
                        with redirect_stdout(io.StringIO()):
                            assistant.start_section_combat()
                            self.assertTrue(assistant.combat["Active"], (combat_mode, book_number, section))
                            if combat_mode == "ManualCRT":
                                assistant.combat_round(["combat", "manual"], manual_losses=(1, 0))
                            else:
                                assistant.combat_round(["combat", "round", "0"])

    def test_book13_rnt_rules_apply_grand_master_modifiers_and_roll_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"].update(
                {
                    "BookNumber": 13,
                    "GrandMasterDisciplines": [
                        "Grand Weaponmastery",
                        "Grand Huntmastery",
                        "Kai-surge",
                        "Kai-alchemy",
                    ],
                    "GrandWeaponmasteryWeapons": ["Bow", "Sword"],
                    "EnduranceCurrent": 30,
                    "EnduranceMax": 30,
                }
            )
            assistant.state["Inventory"].update(
                {"Weapons": ["Bow"], "SpecialItems": ["Sommerswerd"]}
            )

            assistant.set_section(104)
            bow_result = assistant.roll_current_section(3)
            self.assertEqual((bow_result["Total"], bow_result["Route"]), (6, 235))

            assistant.set_section(52)
            oxygen_result = assistant.roll_current_section(5)
            self.assertEqual((oxygen_result["Total"], oxygen_result["Route"]), (6, 246))
            self.assertEqual(assistant.character["EnduranceCurrent"], 24)

            assistant.set_section(81)
            assistant.set_roll_selection("book13-81-weapon", "Sommerswerd")
            weapon_result = assistant.roll_current_section(1)
            self.assertEqual((weapon_result["Total"], weapon_result["Route"]), (5, 248))

    def test_book14_rnt_rules_apply_source_modifiers_and_endurance_loss(self) -> None:
        state = lonewolf_redux.create_grand_master_character_state(
            book_number=14,
            grand_master_disciplines=[
                "Grand Weaponmastery", "Grand Huntmastery", "Kai-screen", "Kai-alchemy", "Assimilance"
            ],
            grand_weaponmastery_weapons=["Bow", "Sword", "Axe"],
            combat_skill_roll=0,
            endurance_roll=0,
            gold_roll=0,
            equipment_choices=["sword", "bow", "quiver", "rope", "laumspur"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = state
            assistant.set_section(19)
            self.assertEqual(assistant.roll_current_section(1)["Route"], 202)
            assistant.set_section(49)
            assistant.roll_current_section(0)
            self.assertEqual(assistant.character["EnduranceCurrent"], 29)
            assistant.set_section(73)
            self.assertEqual(assistant.roll_current_section(4)["Route"], 231)
            assistant.set_section(74)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 344)
            assistant.set_section(75)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 161)
            assistant.set_section(115)
            fatigue = assistant.roll_current_section(4)
            self.assertEqual((fatigue["Total"], fatigue["Route"]), (3, 100))
            self.assertEqual(assistant.character["EnduranceCurrent"], 26)
            assistant.set_section(136)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 16)
            assistant.set_section(164)
            self.assertEqual(assistant.roll_current_section(1)["Route"], 198)
            assistant.set_section(168)
            self.assertEqual(assistant.roll_current_section(2)["Route"], 262)
            assistant.set_section(177)
            self.assertEqual(assistant.roll_current_section(2)["Route"], 113)
            assistant.set_section(189)
            self.assertEqual(assistant.roll_current_section(4)["Route"], 58)
            assistant.set_section(227)
            self.assertEqual(assistant.roll_current_section(2)["Route"], 158)
            assistant.set_section(232)
            self.assertEqual(assistant.roll_current_section(3)["Route"], 112)
            assistant.set_section(254)
            fatigue = assistant.roll_current_section(0)
            self.assertEqual((fatigue["Total"], fatigue["Route"]), (0, 100))
            self.assertEqual(assistant.character["EnduranceCurrent"], 26)
            assistant.set_section(283)
            self.assertEqual(assistant.roll_current_section(2)["Route"], 262)
            self.assertEqual(assistant.character["EnduranceCurrent"], 23)
            assistant.set_section(284)
            attack = assistant.roll_current_section(2)
            self.assertEqual(attack["Total"], 3)
            self.assertEqual(assistant.character["EnduranceCurrent"], 20)
            assistant.set_section(335)
            self.assertEqual(assistant.roll_current_section(7)["Route"], 34)

    def test_book15_initial_rnt_rules_apply_source_modifiers_and_rank_rules(self) -> None:
        state = lonewolf_redux.create_grand_master_character_state(
            book_number=15,
            grand_master_disciplines=[
                "Animal Mastery", "Grand Huntmastery", "Assimilance", "Grand Pathsmanship", "Kai-screen", "Telegnosis"
            ],
            grand_weaponmastery_weapons=[],
            combat_skill_roll=0,
            endurance_roll=0,
            gold_roll=0,
            equipment_choices=["sword", "bow", "quiver", "rope", "laumspur"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = state
            assistant.set_section(31)
            self.assertEqual(assistant.roll_current_section(1)["Route"], 87)
            assistant.set_section(59)
            self.assertEqual(assistant.roll_current_section(3)["Route"], 268)
            assistant.set_section(70)
            self.assertEqual(assistant.roll_current_section(5)["Route"], 92)
            assistant.set_section(102)
            self.assertEqual(assistant.roll_current_section(2)["Route"], 119)
            assistant.inventory["SpecialItems"].append("Sommerswerd")
            assistant.set_section(238)
            assistant.set_roll_selection("book15-238-weapon", "Sommerswerd")
            self.assertEqual(assistant.roll_current_section(3)["Route"], 3)

    def test_book16_initial_rnt_rules_apply_rank_and_discipline_modifiers(self) -> None:
        state = lonewolf_redux.create_grand_master_character_state(
            book_number=16,
            grand_master_disciplines=[
                "Animal Mastery", "Grand Huntmastery", "Assimilance", "Grand Pathsmanship", "Kai-screen", "Telegnosis", "Kai-alchemy"
            ],
            grand_weaponmastery_weapons=[],
            combat_skill_roll=0,
            endurance_roll=0,
            gold_roll=0,
            equipment_choices=["sword", "bow", "quiver", "rope"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = state
            assistant.set_section(2)
            self.assertEqual(assistant.roll_current_section(7)["Route"], 211)
            assistant.set_section(15)
            self.assertEqual(assistant.roll_current_section(4)["Route"], 306)
            assistant.set_section(23)
            self.assertEqual(assistant.roll_current_section(5)["Route"], 125)

    def test_book16_roll_driven_backpack_losses_remain_player_selected(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 16, "EnduranceCurrent": 30, "EnduranceMax": 30},
                "Inventory": {"GoldCrowns": 20, "BackpackItems": ["Rope", "Torch", "Meal"]},
                "CurrentSection": 38,
            })
            choice = assistant.current_loss_choices_payload()[0]
            self.assertFalse(choice["Ready"])
            self.assertIn("Roll this section", choice["BlockedReason"])
            assistant.roll_current_section(2)
            choice = assistant.current_loss_choices_payload()[0]
            self.assertEqual((choice["RequiredCount"], choice["Remaining"]), (2, 2))
            assistant.apply_section_loss("book16-38-backpack", "backpack", "Rope")
            self.assertEqual(assistant.current_loss_choices_payload()[0]["Remaining"], 1)
            assistant.apply_section_loss("book16-38-backpack", "backpack", "Torch")
            self.assertTrue(assistant.current_loss_choices_payload()[0]["Applied"])
            self.assertEqual(assistant.inventory["BackpackItems"], ["Meal"])

    def test_book16_arrow_volley_empties_the_quiver_at_the_source_threshold(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 16}, "Inventory": {"QuiverArrows": 4}, "CurrentSection": 330,
            })
            result = assistant.roll_current_section(4)
            self.assertEqual(result["Route"], 268)
            self.assertEqual(assistant.inventory["QuiverArrows"], 0)

    def test_book16_cursed_water_routes_after_its_source_endurance_loss(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 16, "EnduranceCurrent": 25, "EnduranceMax": 30}, "CurrentSection": 121,
            })
            result = assistant.roll_current_section(5)
            self.assertEqual(result["Route"], 265)
            self.assertEqual(assistant.character["EnduranceCurrent"], 20)

    def test_book18_rnt_rules_apply_rank_items_and_source_injuries(self) -> None:
        state = lonewolf_redux.create_grand_master_character_state(
            book_number=18,
            grand_master_disciplines=[
                "Animal Mastery", "Grand Huntmastery", "Assimilance", "Grand Pathsmanship",
                "Kai-screen", "Telegnosis", "Kai-alchemy", "Deliverance", "Grand Nexus",
            ],
            grand_weaponmastery_weapons=[],
            combat_skill_roll=0,
            endurance_roll=0,
            gold_roll=0,
            equipment_choices=["sword", "bow", "quiver", "rope"],
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = state
            assistant.set_section(41)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 230)
            assistant.inventory["BackpackItems"].append("Sabito")
            assistant.set_section(163)
            self.assertEqual(assistant.roll_current_section(1)["Route"], 116)
            assistant.set_section(128)
            assistant.roll_current_section(0)
            self.assertEqual(assistant.character["EnduranceCurrent"], 30)
            assistant.set_section(296)
            assistant.roll_current_section(0)
            self.assertEqual(assistant.character["EnduranceCurrent"], 20)

    def test_book19_rnt_rules_apply_bladed_weapon_rank_and_injury_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {
                    "BookNumber": 19, "EnduranceCurrent": 30, "EnduranceMax": 30,
                    "GrandMasterRank": 10,
                    "GrandMasterDisciplines": ["Grand Nexus", "Grand Huntmastery", "Grand Pathsmanship"],
                },
                "Inventory": {"Weapons": ["Sword"]},
            })
            assistant.set_section(17)
            assistant.roll_current_section(1)
            self.assertEqual(assistant.character["EnduranceCurrent"], 30)
            assistant.set_section(69)
            self.assertEqual(assistant.roll_current_section(2)["Route"], 228)
            assistant.set_section(120)
            self.assertEqual(assistant.roll_current_section(4)["Route"], 59)

    def test_book21_optional_endurance_roll_bonus_is_player_selected_and_paid_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 21, "EnduranceCurrent": 30, "EnduranceMax": 30},
                "CurrentSection": 51,
            })
            blocked = assistant.roll_current_section(1)
            self.assertTrue(blocked["Blocked"])
            assistant.set_roll_selection("book21-51-endurance", "5")
            result = assistant.roll_current_section(1)
            self.assertEqual((result["Total"], result["Route"]), (6, 15))
            self.assertEqual(assistant.character["EnduranceCurrent"], 25)
            assistant.roll_current_section(1)
            self.assertEqual(assistant.character["EnduranceCurrent"], 25)

    def test_book22_rnt_rules_apply_parity_and_combined_source_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {
                    "BookNumber": 22, "EnduranceCurrent": 30, "EnduranceMax": 30,
                    "GrandMasterDisciplines": ["Grand Huntmastery", "Grand Nexus", "Assimilance"],
                },
            })
            assistant.set_section(12)
            assistant.roll_current_section(0)
            self.assertEqual(assistant.character["EnduranceCurrent"], 25)
            assistant.set_section(40)
            self.assertEqual(assistant.roll_current_section(3)["Route"], 135)
            self.assertEqual(assistant.character["EnduranceCurrent"], 23)
            assistant.set_section(202)
            assistant.roll_current_section(1)
            self.assertEqual(assistant.character["EnduranceCurrent"], 16)

    def test_book23_rnt_rules_handle_gold_choices_items_and_kai_screen(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {
                    "BookNumber": 23, "EnduranceCurrent": 30, "EnduranceMax": 30,
                    "GrandMasterDisciplines": ["Kai-screen"],
                },
                "Inventory": {"GoldCrowns": 10},
            })
            assistant.set_section(112)
            self.assertTrue(assistant.roll_current_section(2)["Blocked"])
            self.assertEqual(assistant.current_roll_selection_payload()["Options"][-1], "8")
            assistant.set_roll_selection("book23-112-gold", "4")
            self.assertEqual(assistant.roll_current_section(2)["Route"], 26)
            self.assertEqual(assistant.inventory["GoldCrowns"], 4)
            assistant.roll_current_section(2)
            self.assertEqual(assistant.inventory["GoldCrowns"], 4)

            assistant.set_section(124)
            meals_before = assistant.inventory["BackpackItems"].count("Meal")
            self.assertEqual(assistant.roll_current_section(0)["Route"], 35)
            self.assertEqual(assistant.inventory["BackpackItems"].count("Meal"), meals_before + 2)

            assistant.set_section(314)
            assistant.roll_current_section(1)
            self.assertEqual(assistant.character["EnduranceCurrent"], 28)

    def test_new_order_combat_catalogue_preserves_source_encounters_and_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            self.assertEqual(len([entry for entry in assistant.section_flows["21"].values() if entry.get("combat")]), 23)
            self.assertEqual(len([entry for entry in assistant.section_flows["22"].values() if entry.get("combat")]), 25)
            self.assertEqual(len([entry for entry in assistant.section_flows["23"].values() if entry.get("combat")]), 17)

            assistant.state["Character"].update({"BookNumber": 21, "CombatSkillCurrent": 20})
            assistant.state["Inventory"]["Weapons"] = ["Sword"]
            assistant.set_section(5)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["ForceUnarmedThroughRound"], 1)
            self.assertEqual(assistant.combat["VictoryRoute"], 340)
            assistant.set_section(31)
            assistant.start_section_combat()
            self.assertEqual((assistant.combat["WinWithinRounds"], assistant.combat["TooLateRoute"]), (4, 195))

            assistant.state["Character"].update({"BookNumber": 22, "GrandMasterDisciplines": []})
            assistant.set_section(67)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["Modifier"], -4)
            assistant.set_section(106)
            assistant.start_section_combat()
            self.assertEqual((assistant.combat["RoundLimit"], assistant.combat["SurvivalRoute"]), (2, 215))

            assistant.state["Character"]["BookNumber"] = 23
            assistant.set_section(60)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["OneRoundComparisonRoutes"], {"playerLossGreater": 40, "enemyLossGreater": 297, "equal": 143})
            assistant.set_section(25)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 20)
            self.assertEqual(assistant.combat_skill_for_round(4), 25)

    def test_grand_master_books13_to20_load_source_combat_catalogues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            self.assertEqual(len([entry for entry in assistant.section_flows["13"].values() if entry.get("combat")]), 51)
            self.assertEqual(len([entry for entry in assistant.section_flows["14"].values() if entry.get("combat")]), 41)
            self.assertEqual(len([entry for entry in assistant.section_flows["15"].values() if entry.get("combat")]), 34)
            self.assertEqual(len([entry for entry in assistant.section_flows["16"].values() if entry.get("combat")]), 36)
            self.assertEqual(len([entry for entry in assistant.section_flows["17"].values() if entry.get("combat")]), 52)
            self.assertEqual(len([entry for entry in assistant.section_flows["18"].values() if entry.get("combat")]), 34)
            self.assertEqual(len([entry for entry in assistant.section_flows["19"].values() if entry.get("combat")]), 32)
            self.assertEqual(len([entry for entry in assistant.section_flows["20"].values() if entry.get("combat")]), 26)

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 13, "CombatSkillCurrent": 30, "EnduranceCurrent": 40, "EnduranceMax": 40},
                "Inventory": {"Weapons": ["Sword"]},
            })
            assistant.set_section(125)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["EnemyCombatSkill"], 50)
            self.assertEqual(assistant.combat["EnemyEnduranceMax"], 50)
            self.assertEqual(assistant.combat["VictoryRoute"], 320)

            assistant.character["BookNumber"] = 14
            assistant.set_section(281)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["EnemyCombatSkill"], 48)
            self.assertEqual(assistant.combat["EnemyEnduranceMax"], 52)
            self.assertEqual(assistant.combat["VictoryRoute"], 50)

            assistant.character["BookNumber"] = 15
            assistant.set_section(44)
            assistant.start_section_combat()
            self.assertEqual((assistant.combat["WinWithinRounds"], assistant.combat["TooLateRoute"]), (6, 155))
            assistant.set_section(244)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 20)
            self.assertEqual(assistant.combat_skill_for_round(3), 30)

            assistant.character.update({"BookNumber": 16, "GrandMasterDisciplines": [], "GrandMasterRank": 5})
            assistant.set_section(11)
            assistant.start_section_combat()
            self.assertEqual((assistant.combat["EvadeAfterRounds"], assistant.combat["EvadeRoute"]), (4, 222))
            self.assertEqual(assistant.combat_skill_for_round(1), 25)
            assistant.set_section(39)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 25)
            self.assertEqual(assistant.combat_skill_for_round(4), 30)

            assistant.character.update({"BookNumber": 17, "GrandMasterDisciplines": [], "GrandMasterRank": 7})
            assistant.set_section(21)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 26)
            self.assertEqual((assistant.combat["EvadeAfterRounds"], assistant.combat["EvadeRoute"]), (4, 138))
            assistant.set_section(42)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 25)
            assistant.set_section(96)
            assistant.start_section_combat()
            self.assertEqual((assistant.combat["WinWithinRounds"], assistant.combat["TooLateRoute"]), (6, 213))
            assistant.set_section(310)
            assistant.start_section_combat()
            self.assertEqual((assistant.combat["EvadeAfterRounds"], assistant.combat["EvadeRoute"]), (3, 295))

            assistant.character["BookNumber"] = 18
            assistant.set_section(33)
            assistant.start_section_combat()
            self.assertEqual((assistant.combat["WinWithinRounds"], assistant.combat["TooLateRoute"]), (3, 160))
            assistant.set_section(278)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 26)

            assistant.character["BookNumber"] = 19
            assistant.set_section(75)
            assistant.start_section_combat()
            self.assertEqual(
                assistant.combat["OneRoundComparisonRoutes"],
                {"enemyLossGreater": 163, "equal": 163, "playerLossGreater": 221},
            )
            assistant.set_section(237)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 25)

            assistant.character.update({"BookNumber": 20, "GrandMasterDisciplines": ["Animal Mastery"]})
            assistant.set_section(24)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_skill_for_round(1), 32)
            assistant.set_section(121)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["VictoryRoute"], 29)

    def test_grand_master_direct_endurance_catalogue_applies_only_safe_source_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            expected_counts = {13: 38, 14: 32, 15: 30, 16: 35, 17: 39, 18: 37, 19: 38, 20: 44}
            self.assertEqual(
                {book: len(assistant.section_automation[str(book)]) for book in expected_counts},
                expected_counts,
            )

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 13, "EnduranceCurrent": 20, "EnduranceMax": 30},
            })
            assistant.set_section(10)
            self.assertEqual(assistant.character["EnduranceCurrent"], 23)
            assistant.apply_section_automation(force=False, visit_changed=False)
            self.assertEqual(assistant.character["EnduranceCurrent"], 23)

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 17, "EnduranceCurrent": 20, "EnduranceMax": 30},
            })
            assistant.set_section(11)
            self.assertEqual(assistant.character["EnduranceCurrent"], 18)

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 19, "EnduranceCurrent": 20, "EnduranceMax": 30},
            })
            assistant.set_section(216)
            self.assertEqual(assistant.character["EnduranceCurrent"], 28)

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 13, "EnduranceCurrent": 20, "EnduranceMax": 30},
                "Inventory": {"BackpackItems": ["Meal"]},
            })
            assistant.set_section(106)
            self.assertEqual(assistant.inventory["BackpackItems"], [])

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {
                    "BookNumber": 13, "EnduranceCurrent": 20, "EnduranceMax": 30,
                    "GrandMasterDisciplines": ["Grand Huntmastery"],
                },
                "Inventory": {"BackpackItems": ["Meal"]},
            })
            assistant.set_section(106)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Meal"])

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 14},
                "Inventory": {"GoldCrowns": 10, "BackpackItems": ["Rope", "Torch", "Tinderbox"]},
            })
            assistant.set_section(112)
            self.assertEqual(assistant.inventory["GoldCrowns"], 10)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Rope", "Torch"])

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 17},
                "Inventory": {"GoldCrowns": 10, "BackpackItems": ["Rope", "Torch", "Tinderbox"]},
            })
            assistant.set_section(63)
            self.assertEqual(assistant.inventory["GoldCrowns"], 0)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Tinderbox"])

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 20, "EnduranceCurrent": 20, "EnduranceMax": 30},
                "Inventory": {"GoldCrowns": 5},
            })
            assistant.set_section(103)
            self.assertEqual(assistant.character["EnduranceCurrent"], 14)
            self.assertEqual(assistant.inventory["GoldCrowns"], 3)

    def test_new_order_direct_effect_catalogue_applies_only_safe_source_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            expected_counts = {21: 52, 22: 42, 23: 57}
            self.assertEqual(
                {book: len(assistant.section_automation[str(book)]) for book in expected_counts},
                expected_counts,
            )

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 21, "EnduranceCurrent": 20, "EnduranceMax": 30},
            })
            assistant.set_section(112)
            self.assertEqual(assistant.character["EnduranceCurrent"], 17)

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 21},
                "Inventory": {"GoldCrowns": 5},
            })
            assistant.set_section(127)
            self.assertEqual(assistant.inventory["GoldCrowns"], 3)

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 22},
                "Inventory": {"BackpackItems": ["Meal"]},
            })
            assistant.set_section(101)
            self.assertEqual(assistant.inventory["BackpackItems"], [])

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {
                    "BookNumber": 23,
                    "NewOrderDisciplines": ["Grand Huntmastery"],
                },
                "Inventory": {"BackpackItems": ["Meal"]},
            })
            assistant.set_section(115)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Meal"])

    def test_new_order_books24_to26_direct_effect_catalogue_applies_safe_losses_and_meals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            expected_counts = {24: 39, 25: 37, 26: 38}
            self.assertEqual(
                {book: len(assistant.section_automation[str(book)]) for book in expected_counts},
                expected_counts,
            )

            for book_number, loss_section, meal_section in ((24, 8, 13), (25, 7, 83), (26, 3, 37)):
                assistant.state = lonewolf_redux.normalize_state({
                    "Character": {"BookNumber": book_number, "EnduranceCurrent": 20, "EnduranceMax": 30},
                })
                assistant.set_section(loss_section)
                self.assertLess(assistant.character["EnduranceCurrent"], 20)

                assistant.state = lonewolf_redux.normalize_state({
                    "Character": {
                        "BookNumber": book_number,
                        "NewOrderDisciplines": ["Grand Huntmastery"],
                    },
                    "Inventory": {"BackpackItems": ["Meal"]},
                })
                assistant.set_section(meal_section)
                self.assertEqual(assistant.inventory["BackpackItems"], ["Meal"])

    def test_new_order_books27_to29_direct_effect_catalogue_applies_safe_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            expected_counts = {27: 56, 28: 32, 29: 24}
            self.assertEqual(
                {book: len(assistant.section_automation[str(book)]) for book in expected_counts},
                expected_counts,
            )

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 27, "EnduranceCurrent": 20, "EnduranceMax": 30},
            })
            assistant.set_section(5)
            self.assertEqual(assistant.character["EnduranceCurrent"], 24)
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 27, "NewOrderDisciplines": ["Grand Huntmastery"]},
                "Inventory": {"BackpackItems": ["Meal"]},
            })
            assistant.set_section(20)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Meal"])

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 28, "EnduranceCurrent": 20, "EnduranceMax": 30},
            })
            assistant.set_section(21)
            self.assertEqual(assistant.character["EnduranceCurrent"], 15)
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 28, "NewOrderDisciplines": ["Grand Huntmastery"]},
                "Inventory": {"BackpackItems": ["Meal"]},
            })
            assistant.set_section(7)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Meal"])

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 29, "EnduranceCurrent": 20, "EnduranceMax": 30},
                "Inventory": {"GoldCrowns": 15},
            })
            assistant.set_section(29)
            self.assertEqual(assistant.character["EnduranceCurrent"], 15)
            assistant.set_section(33)
            self.assertEqual(assistant.inventory["GoldCrowns"], 5)

    def test_new_order_books21_to29_unlock_campaign_achievements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.set_run_configuration("Story", False, "DataFile")
            for book_number in range(21, 30):
                assistant.state["Character"]["BookNumber"] = book_number
                assistant.state["CurrentBookStats"] = {
                    "BookNumber": book_number,
                    "BookTitle": lonewolf_redux.BOOK_CATALOG[book_number]["Title"],
                    "StartSection": 1,
                    "LastSection": 90,
                    "SectionsVisited": 75,
                    "VisitedSections": list(range(1, 76)),
                }
                assistant.ensure_book_completed(book_number)

            story_unlocked = {entry["Id"] for entry in assistant.sync_achievements()}
            assistant.set_run_configuration("Normal", False, "DataFile")
            exploration_unlocked = {entry["Id"] for entry in assistant.sync_achievements()}

        expected_complete = {f"lw{book_number}_complete" for book_number in range(21, 30)}
        expected_long_road = {f"lw{book_number}_long_road" for book_number in range(21, 30)}
        self.assertTrue(expected_complete.issubset(story_unlocked))
        self.assertTrue(expected_long_road.issubset(exploration_unlocked))

    def test_book21_source_item_effects_keep_forced_losses_and_optional_loot_distinct(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 21},
                "Inventory": {"BackpackItems": ["Rope", "Torch", "Tinderbox"]},
            })
            assistant.set_section(30)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Torch", "Tinderbox"])
            assistant.set_section(233)
            self.assertEqual(assistant.inventory["BackpackItems"], ["Torch"])

            assistant.set_section(102)
            self.assertNotIn("Temujun's Ring", assistant.inventory["PocketSpecialItems"])
            assistant.apply_flow_loot("temujun-ring")
            self.assertIn("Temujun's Ring", assistant.inventory["PocketSpecialItems"])

    def test_books22_and23_source_item_choices_and_forced_changes_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 22},
                "Inventory": {"GoldCrowns": 10, "BackpackItems": ["Rope", "Torch", "Tinderbox"]},
            })
            assistant.set_section(21)
            assistant.apply_flow_loot("nhang-doll-10")
            self.assertEqual(assistant.inventory["GoldCrowns"], 0)
            self.assertIn("Nhang Doll", assistant.inventory["BackpackItems"])
            assistant.set_section(167)
            self.assertTrue({"Pouch of Seota Dust", "Talisman of Defiance", "Eye of Lhaz"}.issubset(assistant.inventory["PocketSpecialItems"]))

            assistant.state["Character"]["BookNumber"] = 23
            assistant.set_section(65)
            self.assertIn("Riverboat Ticket", assistant.inventory["PocketSpecialItems"])
            assistant.set_section(4)
            assistant.apply_flow_loot("cache-gold")
            self.assertEqual(assistant.inventory["GoldCrowns"], 10)

    def test_new_order_books24_to26_load_source_rnt_and_combat_catalogues(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            for book_number, rnt_count, combat_count in (
                (24, 38, 36), (25, 44, 39), (26, 68, 46),
                (27, 60, 11), (28, 31, 27), (29, 21, 41),
            ):
                flows = assistant.section_flows[str(book_number)]
                self.assertEqual(len([entry for entry in flows.values() if entry.get("roll")]), rnt_count)
                self.assertEqual(len([entry for entry in flows.values() if entry.get("combat")]), combat_count)

            assistant.state = lonewolf_redux.normalize_state({
                "Character": {
                    "BookNumber": 24, "NewOrderRank": 8,
                    "NewOrderDisciplines": ["Grand Huntmastery", "Grand Weaponmastery", "Animal Mastery"],
                    "GrandMasterDisciplines": ["Grand Huntmastery", "Grand Weaponmastery", "Animal Mastery"],
                    "GrandWeaponmasteryWeapons": ["Sword"],
                    "KaiWeapon": lonewolf_redux.kai_weapon_for_roll(3),
                },
                "Inventory": {"GoldCrowns": 8},
            })
            assistant.set_section(178)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 80)
            assistant.set_section(321)
            self.assertEqual(assistant.roll_current_section(5)["Route"], 306)
            assistant.set_section(328)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 32)

            assistant.state["Character"].update({"BookNumber": 25, "NewOrderRank": 8})
            assistant.set_section(47)
            self.assertEqual(assistant.roll_current_section(5)["Route"], 283)
            assistant.set_section(265)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["IgnoreEnemyLossRounds"], 1)
            self.assertEqual(assistant.combat["TimedPlayerLossMultipliers"], [
                {"multiplier": 2, "startRound": 1, "endRound": 1},
            ])

            assistant.state["Character"].update({
                "BookNumber": 26, "NewOrderRank": 10, "EnduranceCurrent": 25, "EnduranceMax": 30,
            })
            assistant.set_section(6)
            self.assertEqual(assistant.roll_current_section(3)["Route"], 97)
            assistant.set_section(192)
            self.assertEqual(assistant.roll_current_section(3)["Route"], 311)
            assistant.set_section(48)
            self.assertEqual(assistant.roll_current_section(1)["Route"], 220)
            self.assertEqual(assistant.character["EnduranceCurrent"], 23)
            assistant.set_section(127)
            assistant.start_section_combat()
            self.assertEqual(
                (assistant.combat["WinWithinRounds"], assistant.combat["WinWithinRoute"], assistant.combat["TooLateRoute"]),
                (4, 82, 236),
            )

            assistant.state["Character"].update({
                "BookNumber": 27, "NewOrderRank": 9, "EnduranceCurrent": 20,
            })
            assistant.set_section(56)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 161)
            assistant.set_section(37)
            assistant.start_section_combat()
            self.assertEqual(
                (assistant.combat["Modifier"], assistant.combat["WinWithinRounds"], assistant.combat["TooLateRoute"]),
                (2, 5, 105),
            )

            assistant.state["Character"].update({
                "BookNumber": 28, "EnduranceCurrent": 15, "GrandWeaponmasteryWeapons": ["Sword", "Bow"],
            })
            assistant.set_section(65)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 238)
            assistant.set_section(18)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["IgnoreEnemyLossRounds"], 2)

            assistant.state["Character"].update({"BookNumber": 29, "NewOrderRank": 9, "EnduranceCurrent": 25})
            assistant.set_section(234)
            self.assertEqual(assistant.roll_current_section(0)["Route"], 131)
            assistant.set_section(145)
            self.assertEqual(assistant.roll_current_section(9)["Route"], 162)
            self.assertEqual(assistant.character["EnduranceCurrent"], 18)
            assistant.set_section(265)
            assistant.start_section_combat()
            self.assertEqual(
                (assistant.combat["WinWithinRounds"], assistant.combat["WinWithinRoute"], assistant.combat["TooLateRoute"]),
                (3, 313, 49),
            )

    def test_books6_to20_achievements_unlock_from_recorded_campaign_progress(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.set_run_configuration("Story", False, "DataFile")

            for book_number in range(6, 21):
                visited = list(range(1, 91))
                assistant.state["Character"]["BookNumber"] = book_number
                assistant.state["CurrentBookStats"] = {
                    "BookNumber": book_number,
                    "BookTitle": lonewolf_redux.BOOK_CATALOG[book_number]["Title"],
                    "StartSection": 1,
                    "LastSection": 90,
                    "SectionsVisited": len(visited),
                    "VisitedSections": visited,
                }
                assistant.ensure_book_completed(book_number)

            story_unlocks = {entry["Id"] for entry in assistant.sync_achievements()}
            assistant.set_run_configuration("Normal", False, "DataFile")
            exploration_unlocks = {entry["Id"] for entry in assistant.sync_achievements()}
            expected_story = {f"lw{book_number}_complete" for book_number in range(6, 21)}
            expected_exploration = {f"lw{book_number}_long_road" for book_number in range(6, 21)}
            payload = assistant.achievement_payload()

        self.assertTrue(expected_story.issubset(story_unlocks))
        self.assertTrue(expected_exploration.issubset(exploration_unlocks))
        self.assertEqual(payload["SchemaVersion"], 2)
        for book_number in range(6, 21):
            self.assertEqual(payload["ByBook"][str(book_number)], {
                "BookNumber": book_number,
                "Total": 2,
                "Unlocked": 2,
            })

    def test_later_magnakai_combat_survives_signed_save_load_in_both_crt_modes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            root = Path(lonewolf_redux.__file__).resolve().parent
            for combat_mode in ("DataFile", "ManualCRT"):
                assistant = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / combat_mode / "saves",
                    data_dir=root / "data",
                    state_data_dir=base / combat_mode / "state",
                    books_dir=base / combat_mode / "books",
                )
                assistant.set_run_configuration("Normal", False, combat_mode)
                assistant.state["Character"].update(
                    {"BookNumber": 12, "CombatSkillCurrent": 30, "EnduranceCurrent": 100, "EnduranceMax": 100}
                )
                assistant.state["Inventory"].update(
                    {"Weapons": ["Dagger", "Sword"], "SpecialItems": ["Sommerswerd", "Map of the Darklands"]}
                )
                assistant.set_section(104)
                assistant.start_combat(["combat", "start", "Save Fixture", "30", "100"])
                assistant.set_combat_weapon("Dagger", save=False)
                if combat_mode == "ManualCRT":
                    assistant.combat_round(["combat", "manual"], manual_losses=(1, 1))
                else:
                    assistant.combat_round(["combat", "round", "0"])

                checkpoint = base / combat_mode / "active-combat.json"
                assistant.save_game(str(checkpoint), quiet=True)
                recorded_rounds = len(assistant.combat["Log"])

                resumed = lonewolf_redux.LoneWolfReduxAssistant(
                    save_dir=base / combat_mode / "resumed-saves",
                    data_dir=root / "data",
                    state_data_dir=base / combat_mode / "resumed-state",
                    books_dir=base / combat_mode / "books",
                )
                self.assertTrue(resumed.load_game(str(checkpoint), quiet=True))
                self.assertTrue(resumed.combat["Active"])
                self.assertEqual(resumed.character["BookNumber"], 12)
                self.assertEqual(resumed.state["CurrentSection"], 104)
                self.assertEqual(resumed.inventory["Weapons"], ["Dagger", "Sword"])
                self.assertEqual(resumed.inventory["SpecialItems"], ["Sommerswerd", "Map of the Darklands"])
                self.assertEqual(len(resumed.combat["Log"]), recorded_rounds)

                if combat_mode == "ManualCRT":
                    resumed.combat_round(["combat", "manual"], manual_losses=(1, 1))
                else:
                    resumed.combat_round(["combat", "round", "0"])
                self.assertEqual(len(resumed.combat["Log"]), recorded_rounds + 1)

    def test_later_magnakai_nonstandard_combat_presets_resolve_their_source_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            for section, route, required_rounds in (
                (36, 328, 0), (86, 328, 0), (98, 223, 1), (119, 49, 0),
                (127, 223, 1), (217, 334, 0), (260, 328, 0), (308, 223, 1),
            ):
                assistant.state["Character"]["BookNumber"] = 9
                assistant.set_section(section)
                assistant.start_section_combat()
                assistant.combat["Log"] = [{"Round": index + 1} for index in range(required_rounds)]
                self.assertTrue(assistant.can_evade_combat_now())
                assistant.evade_combat(["combat", "evade"], manual_losses=(0, 0))
                self.assertEqual(assistant.state["CurrentSection"], route)

            assistant.state["Character"]["BookNumber"] = 12
            assistant.set_section(224)
            assistant.start_section_combat()
            self.assertTrue(assistant.can_evade_combat_now())
            assistant.evade_combat(["combat", "evade"], manual_losses=(0, 0))
            self.assertEqual(assistant.state["CurrentSection"], 58)

    def test_later_magnakai_high_confidence_section_effects_apply(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"].update(
                {"BookNumber": 9, "EnduranceCurrent": 20, "EnduranceMax": 30}
            )
            assistant.set_section(48)
            assistant.apply_section_automation(force=True, visit_changed=True)
            book9_endurance = assistant.character["EnduranceCurrent"]

            assistant.state["Character"].update(
                {"BookNumber": 10, "EnduranceCurrent": 20, "MagnakaiDisciplines": []}
            )
            assistant.state["Inventory"]["BackpackItems"] = []
            assistant.set_section(59)
            assistant.apply_section_automation(force=True, visit_changed=True)
            book10_endurance = assistant.character["EnduranceCurrent"]

            assistant.state["Character"].update(
                {"BookNumber": 11, "EnduranceCurrent": 12, "EnduranceMax": 30}
            )
            assistant.set_section(101)
            assistant.apply_section_automation(force=True, visit_changed=True)
            book11_endurance = assistant.character["EnduranceCurrent"]

            assistant.state["Character"].update(
                {"BookNumber": 11, "EnduranceCurrent": 20, "MagnakaiDisciplines": ["Huntmastery"]}
            )
            assistant.state["Inventory"]["BackpackItems"] = []
            assistant.set_section(74)
            assistant.apply_section_automation(force=True, visit_changed=True)
            book11_forced_meal_endurance = assistant.character["EnduranceCurrent"]

            assistant.state["Character"].update({"BookNumber": 12, "EnduranceCurrent": 20})
            assistant.state["Inventory"]["Weapons"] = ["Bow"]
            assistant.set_section(245)
            assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertEqual(book9_endurance, 15)
        self.assertEqual(book10_endurance, 17)
        self.assertEqual(book11_endurance, 30)
        self.assertEqual(book11_forced_meal_endurance, 17)
        self.assertEqual(assistant.inventory["Weapons"], [])

    def test_later_magnakai_audited_item_events_apply_without_guessing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )

            assistant.state["Character"]["BookNumber"] = 9
            assistant.state["Inventory"]["Weapons"] = ["Sword", "Dagger"]
            assistant.set_section(24)
            assistant.apply_section_loss("24-ranger-weapon-loss", "weapon", "Sword")
            book9_loss = assistant.inventory["Weapons"]
            assistant.state["Inventory"]["BackpackItems"] = ["Rope", "Sabito"]
            assistant.set_section(7)
            assistant.apply_section_automation(force=True, visit_changed=True)
            book9_pack = assistant.inventory["BackpackItems"]
            assistant.set_section(87)
            assistant.apply_flow_loot("87-psychic-ring")

            assistant.state["Character"]["BookNumber"] = 10
            assistant.state["Inventory"]["GoldCrowns"] = 0
            assistant.set_section(145)
            assistant.apply_flow_loot("145-gold")
            assistant.apply_flow_loot("145-bullwhip")

            assistant.state["Character"]["BookNumber"] = 11
            assistant.set_section(210)
            assistant.apply_section_automation(force=True, visit_changed=True)

            assistant.state["Character"].update({"BookNumber": 12, "MagnakaiDisciplines": []})
            assistant.set_section(308)
            assistant.apply_flow_loot("308-black-key")
            assistant.apply_flow_loot("308-black-cube")
            no_divination_loot = assistant.current_flow_loot_payload()
            assistant.state["Character"]["MagnakaiDisciplines"] = ["Divination"]
            divination_loot = assistant.current_flow_loot_payload()

        self.assertEqual(book9_loss, ["Dagger"])
        self.assertEqual(book9_pack, ["Sabito"])
        self.assertIn("Psychic Ring", assistant.inventory["SpecialItems"])
        self.assertEqual(assistant.inventory["GoldCrowns"], 9)
        self.assertIn("Bullwhip", assistant.inventory["SpecialItems"])
        self.assertIn("Obsidian Seal", assistant.inventory["SpecialItems"])
        self.assertIn("Black Key", assistant.inventory["BackpackItems"])
        self.assertIn("Black Cube", assistant.inventory["BackpackItems"])
        self.assertTrue(all(item["Applied"] for item in no_divination_loot))
        self.assertTrue(all(not item["Ready"] for item in divination_loot))

    def test_later_magnakai_special_equipment_rules_apply_in_combat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )

            assistant.state["Character"].update(
                {"BookNumber": 11, "CombatSkillCurrent": 20, "EnduranceCurrent": 30, "EnduranceMax": 30}
            )
            assistant.state["Inventory"]["Weapons"] = []
            assistant.state["Inventory"]["SpecialItems"] = ["Ironheart Broadsword"]
            assistant.set_section(204)
            assistant.start_section_combat()
            assistant.set_combat_weapon("Ironheart Broadsword", save=False)
            ironheart_cs = assistant.combat_skill_for_round(1)

            assistant.state["Character"].update(
                {"BookNumber": 12, "CombatSkillCurrent": 20, "EnduranceCurrent": 30, "EnduranceMax": 30}
            )
            assistant.state["Inventory"]["Weapons"] = []
            assistant.state["Inventory"]["SpecialItems"] = ["Helshezag"]
            assistant.set_section(104)
            assistant.start_section_combat()
            assistant.set_combat_weapon("Helshezag", save=False)
            helszag_cs = assistant.combat_skill_for_round(1)
            assistant.combat_round(["combat", "manual"], manual_losses=(0, 0))
            after_first_helshezag_round = (assistant.character["EnduranceCurrent"], assistant.character["EnduranceMax"])
            assistant.combat_round(["combat", "manual"], manual_losses=(0, 0))
            after_second_helshezag_round = (assistant.character["EnduranceCurrent"], assistant.character["EnduranceMax"])

            assistant.state["Inventory"]["SpecialItems"] = []
            assistant.state["Character"].update({"CombatSkillCurrent": 20, "EnduranceCurrent": 20, "EnduranceMax": 30})
            assistant.set_section(159)
            assistant.apply_flow_loot("159-bronin-vest")
            assistant.apply_flow_loot("159-silver-bracers")
            armour_stats = (
                assistant.character["CombatSkillCurrent"],
                assistant.character["EnduranceCurrent"],
                assistant.character["EnduranceMax"],
            )

            assistant.state["Inventory"]["SpecialItems"] = ["Golden Amulet"]
            assistant.set_section(121)
            assistant.apply_section_automation(force=True, visit_changed=True)
            amulet_removed = assistant.inventory["SpecialItems"]

            assistant.state["Inventory"].update({"Weapons": ["Sword"], "SpecialItems": []})
            assistant.set_section(247)
            assistant.start_section_combat()
            unarmed_first = assistant.combat_active_weapon()
            assistant.combat_round(["combat", "manual"], manual_losses=(0, 0))
            assistant.combat_round(["combat", "manual"], manual_losses=(0, 0))
            weapon_after_two_rounds = assistant.combat_active_weapon()
            can_evade_after_two_rounds = assistant.can_evade_combat_now()

        self.assertEqual(ironheart_cs, 28)
        self.assertEqual(helszag_cs, 25)
        self.assertEqual(after_first_helshezag_round, (30, 30))
        self.assertEqual(after_second_helshezag_round, (29, 29))
        self.assertEqual(armour_stats, (25, 22, 32))
        self.assertNotIn("Golden Amulet", amulet_removed)
        self.assertEqual(unarmed_first, "")
        self.assertEqual(weapon_after_two_rounds, "Sword")
        self.assertTrue(can_evade_after_two_rounds)

    def test_later_magnakai_rnt_routes_and_effects_follow_source_modifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"].update(
                {
                    "BookNumber": 9,
                    "MagnakaiDisciplines": ["Huntmastery"],
                    "LoreCirclesCompleted": ["Solaris"],
                }
            )
            assistant.set_section(95)
            book9 = assistant.roll_current_section(raw_roll=4)

            assistant.state["Character"].update(
                {
                    "BookNumber": 11,
                    "MagnakaiDisciplines": lonewolf_redux.MAGNAKAI_DISCIPLINES[:8],
                }
            )
            assistant.set_section(13)
            book11 = assistant.roll_current_section(raw_roll=1)

            assistant.state["Character"].update({"BookNumber": 12, "EnduranceCurrent": 20})
            assistant.set_section(180)
            book12 = assistant.roll_current_section(raw_roll=0)

        self.assertEqual((book9["Total"], book9["Route"]), (9, 238))
        self.assertEqual((book11["Total"], book11["Route"]), (9, 199))
        self.assertEqual((book12["Total"], book12["Route"]), (10, 71))
        self.assertEqual(assistant.character["EnduranceCurrent"], 10)

    def test_book1_section320_applies_the_mandatory_kraan_claw_injury(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"]["EnduranceCurrent"] = 20
            assistant.set_section(320)
            messages = assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertEqual(assistant.character["EnduranceCurrent"], 18)
        self.assertTrue(any("2->" in message or "20->18" in message for message in messages))

    def test_book2_section290_replaces_poisoned_food_with_a_meal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 2
            assistant.state["Inventory"]["BackpackItems"] = ["Meal"]
            assistant.state["Character"]["EnduranceCurrent"] = 20
            assistant.set_section(290)
            assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertEqual(assistant.inventory["BackpackItems"], [])
        self.assertEqual(assistant.character["EnduranceCurrent"], 20)

    def test_book6_jakan_tournament_penalty_and_zero_roll_route(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"].update({"BookNumber": 6, "CombatSkillCurrent": 20})
            assistant.set_section(298)
            assistant.apply_section_automation(force=True, visit_changed=True)
            assistant.set_section(26)
            assistant.start_section_combat()
            modifier = assistant.combat["Modifier"]
            with redirect_stdout(io.StringIO()):
                assistant.combat_round(["combat", "round", "0"])

        self.assertEqual(modifier, -2)
        self.assertEqual(assistant.state["CurrentSection"], 335)

    def test_book7_lorestone_and_bat_swarm_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"].update(
                {"BookNumber": 7, "EnduranceCurrent": 20, "EnduranceMax": 30}
            )
            assistant.set_section(53)
            assistant.apply_section_automation(force=True, visit_changed=True)
            after_bats = assistant.character["EnduranceCurrent"]
            assistant.set_section(250)
            assistant.apply_section_automation(force=True, visit_changed=True)
            after_first_lorestone = assistant.character["EnduranceCurrent"]
            assistant.state["Character"]["EnduranceCurrent"] = 12
            assistant.set_section(267)
            assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertEqual(after_bats, 15)
        self.assertEqual(after_first_lorestone, 30)
        self.assertEqual(assistant.character["EnduranceCurrent"], 30)
        self.assertIn("Lorestone of Herdos", assistant.inventory["SpecialItems"])

    def test_book8_audit_effects_apply_the_source_mandatory_costs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"].update(
                {"BookNumber": 8, "EnduranceCurrent": 25, "EnduranceMax": 30}
            )
            assistant.set_section(18)
            assistant.apply_section_automation(force=True, visit_changed=True)
            after_spear = assistant.character["EnduranceCurrent"]
            assistant.inventory["PocketSpecialItems"] = ["Fireseed"]
            assistant.set_section(81)
            assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertEqual(after_spear, 23)
        self.assertEqual(assistant.character["EnduranceCurrent"], 11)
        self.assertNotIn("Fireseed", assistant.inventory["PocketSpecialItems"])


class LegacySaveCompatibilityTests(unittest.TestCase):
    def test_magnakai_save_keeps_book_identity_and_v1_fields(self) -> None:
        legacy = {
            "Version": "0.5.0",
            "RuleSet": "Magnakai",
            "CurrentSection": 266,
            "Character": {
                "Name": "Legacy Lone Wolf",
                "BookNumber": 7,
                "Disciplines": ["Healing", "Weaponskill"],
                "MagnakaiDisciplines": ["Curing", "Weaponmastery"],
                "MagnakaiRank": "Aspirant",
                "WeaponmasteryWeapons": ["Sword"],
                "LoreCirclesCompleted": ["Circle of Fire"],
                "ImprovedDisciplines": ["Curing"],
                "LegacyKaiComplete": True,
            },
            "Inventory": {
                "Weapons": ["Sword"],
                "BackpackItems": ["Meal"],
                "SpecialItems": ["Book of the Magnakai"],
                "GoldCrowns": 12,
                "QuiverArrows": 8,
                "PocketSpecialItems": ["Silver Key"],
            },
            "CurrentBookStats": {"BookNumber": 7},
            "SectionCheckpoints": [{"Key": "7:266", "Stage": "ready"}],
            "DeathHistory": [{"Type": "combat", "Section": 265}],
            "DeathState": {"Active": True, "Type": "combat"},
            "Conditions": {"Poisoned": True},
            "Storage": {"Vault": ["Legacy item"]},
        }

        result = lonewolf_redux.normalize_state(legacy)

        self.assertEqual(lonewolf_redux.book_title(7), "Castle of Death")
        self.assertEqual(result["Character"]["BookNumber"], 7)
        self.assertEqual(result["CurrentBookStats"]["BookTitle"], "Castle of Death")
        self.assertEqual(result["Character"]["KaiDisciplines"], ["Healing", "Weaponskill"])
        self.assertEqual(result["Character"]["MagnakaiDisciplines"], ["Curing", "Weaponmastery"])
        self.assertEqual(result["Character"]["WeaponmasteryWeapons"], ["Sword"])
        self.assertEqual(result["Inventory"]["QuiverArrows"], 8)
        self.assertEqual(result["Inventory"]["PocketSpecialItems"], ["Silver Key"])
        self.assertEqual(result["Automation"]["SectionCheckpoints"], legacy["SectionCheckpoints"])
        self.assertEqual(result["Automation"]["DeathHistory"], legacy["DeathHistory"])
        self.assertTrue(result["Automation"]["DeathState"]["Active"])
        self.assertEqual(result["Conditions"], legacy["Conditions"])
        self.assertEqual(result["Storage"], legacy["Storage"])

    def test_imported_magnakai_weaponmastery_is_available_in_combat(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {
                    "Character": {
                        "BookNumber": 6,
                        "MagnakaiDisciplines": ["Weaponmastery"],
                        "WeaponmasteryWeapons": ["Sword"],
                    },
                    "Inventory": {"Weapons": ["Sword"]},
                }
            )
            assistant.combat["ActiveWeapon"] = "Sword"

            modifier, notes = assistant.combat_weapon_modifier_and_notes()

        self.assertEqual(modifier, 3)
        self.assertIn("Weaponmastery (Sword): +3 CS", notes)

    def test_book6_setup_carries_campaign_state_and_applies_v1_start_rules(self) -> None:
        source = lonewolf_redux.default_state()
        source["Character"].update({"BookNumber": 5, "KaiDisciplines": ["Healing"]})
        source["Inventory"].update(
            {
                "Weapons": ["Sword"],
                "BackpackItems": ["Meal", "Potion"],
                "SpecialItems": ["Book of the Magnakai"],
                "GoldCrowns": 35,
            }
        )

        result = lonewolf_redux.prepare_book6_state(
            source,
            magnakai_disciplines=["Weaponmastery", "Curing", "Nexus"],
            weaponmastery_weapons=["Sword", "Bow", "Axe"],
            gold_roll=8,
            equipment_choices=["quiver", "rations", "herb_pouch"],
            de_curing_option=3,
            de_weaponskill_option=1,
        )

        self.assertEqual(result["RuleSet"], "Magnakai")
        self.assertEqual(result["Character"]["BookNumber"], 6)
        self.assertEqual(result["Character"]["MagnakaiRank"], 3)
        self.assertEqual(result["Character"]["MagnakaiDisciplines"], ["Weaponmastery", "Curing", "Nexus"])
        self.assertEqual(
            result["Inventory"]["BackpackItems"],
            ["Meal", "Potion"] + ["Special Rations"] * 5,
        )
        self.assertEqual(result["Inventory"]["QuiverArrows"], 6)
        self.assertTrue(result["Inventory"]["HasHerbPouch"])
        self.assertIn("Map of the Stornlands", result["Inventory"]["SpecialItems"])
        self.assertEqual(result["Inventory"]["GoldCrowns"], 50)
        self.assertEqual(result["Conditions"]["BookSixDECuringOption"], 3)

    def test_completed_book5_can_transition_to_book6_in_the_engine(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 5
            assistant.state["Automation"]["Ending"] = {"BookNumber": 5, "Type": "success"}
            assistant.state["CurrentBookStats"] = {"BookNumber": 5, "BookTitle": "Shadow on the Sand"}

            assistant.continue_completed_book(
                book6_magnakai_disciplines=["Curing", "Nexus", "Divination"],
                book6_gold_roll=0,
                book6_equipment_choices=["rope"],
            )

        self.assertEqual(assistant.character["BookNumber"], 6)
        self.assertEqual(assistant.state["CurrentSection"], 1)
        self.assertEqual(assistant.state["Automation"]["Ending"], None)

    def test_book5_completion_advertises_the_magnakai_continuation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 5
            assistant.state["Automation"]["Ending"] = {"BookNumber": 5, "Type": "success"}
            payload = assistant.book_completion_payload()
        self.assertEqual(payload["NextBookNumber"], 6)
        self.assertEqual(payload["NextBookTitle"], "The Kingdoms of Terror")
        self.assertIn("Curing", payload["MagnakaiDisciplineChoices"])

    def test_book6_automation_uses_magnakai_curing_and_huntmastery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {
                    "Character": {
                        "BookNumber": 6,
                        "EnduranceCurrent": 15,
                        "EnduranceMax": 20,
                        "MagnakaiDisciplines": ["Curing", "Huntmastery"],
                    },
                    "CurrentSection": 146,
                }
            )

            self.assertIn("Curing", assistant.current_healing_payload()["Summary"])
            messages = assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertTrue(any("Huntmastery: no Meal needed" in message for message in messages))

    def test_book6_rnt_modifier_and_route_match_v1(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6, "MagnakaiDisciplines": ["Divination"]}, "CurrentSection": 317})
            result = assistant.roll_current_section(raw_roll=9)

        self.assertEqual(result["Total"], 4)
        self.assertEqual(result["Route"], 85)

    def test_book6_archery_tournament_sums_three_picks_then_applies_bow_bonus_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 6, "MagnakaiDisciplines": ["Weaponmastery"], "WeaponmasteryWeapons": ["Bow"]}, "CurrentSection": 340}
            )
            first = assistant.roll_current_section(raw_roll=1)
            second = assistant.roll_current_section(raw_roll=2)
            final = assistant.roll_current_section(raw_roll=3)

        self.assertFalse(first["Complete"])
        self.assertFalse(second["Complete"])
        self.assertTrue(final["Complete"])
        self.assertEqual(final["Subtotal"], 6)
        self.assertEqual(final["Total"], 9)
        self.assertEqual(final["Modifiers"], [{"Label": "Weaponmastery with Bow", "Value": 3, "Applies": True}])

    def test_book6_special_rnt_effects_apply_once_with_v1_zero_as_ten(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6, "EnduranceCurrent": 20, "EnduranceMax": 20}, "CurrentSection": 56})
            first = assistant.roll_current_section(raw_roll=0)
            second = assistant.roll_current_section(raw_roll=0)

        self.assertEqual(first["Total"], 10)
        self.assertEqual(assistant.character["EnduranceCurrent"], 10)
        self.assertIn("already applied", second["ActionMessages"][0])

    def test_book6_loot_table_applies_selected_items_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6}, "CurrentSection": 145})
            assistant.apply_flow_loot("gold")
            assistant.apply_flow_loot("ruby-ring")
            assistant.apply_flow_loot("gold")

        self.assertEqual(assistant.inventory["GoldCrowns"], 12)
        self.assertIn("Ruby Ring", assistant.inventory["SpecialItems"])

    def test_book6_apothecary_and_ticket_choices_charge_source_prices(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 6}, "Inventory": {"GoldCrowns": 15}, "CurrentSection": 2}
            )
            self.assertIn("laumspur", {option["id"] for option in assistant.flow_loot_options()})
            assistant.apply_flow_loot("laumspur")
            assistant.set_section(10)
            assistant.apply_flow_loot("ticket-luyen")

        self.assertEqual(assistant.inventory["GoldCrowns"], 0)
        self.assertIn("Potion of Laumspur", assistant.inventory["BackpackItems"])
        self.assertIn("Riverboat Ticket to Luyen", assistant.inventory["PocketSpecialItems"])

    def test_book6_purchase_choices_are_hidden_when_gold_is_insufficient(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 6}, "Inventory": {"GoldCrowns": 1}, "CurrentSection": 2}
            )

        self.assertEqual(assistant.flow_loot_options(), [])

    def test_book6_shop_purchase_rolls_back_when_weapon_slots_are_full(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 6}, "Inventory": {"GoldCrowns": 10, "Weapons": ["Sword", "Dagger"]}, "CurrentSection": 98}
            )
            assistant.apply_flow_loot("buy-broadsword")

        self.assertEqual(assistant.inventory["GoldCrowns"], 10)
        self.assertEqual(assistant.inventory["Weapons"], ["Sword", "Dagger"])

    def test_book6_mercenary_sale_uses_live_inventory_and_source_price(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 6}, "Inventory": {"GoldCrowns": 4, "Weapons": ["Sword", "Bow"]}, "CurrentSection": 76}
            )
            sales = assistant.current_section_flow_payload()["Shop"]["Sales"]
            assistant.apply_shop_sale("Weapons:1")

        self.assertEqual([(sale["Label"], sale["Price"]) for sale in sales], [("Sword [Weapon]", 3), ("Bow [Weapon]", 5)])
        self.assertEqual(assistant.inventory["Weapons"], ["Bow"])
        self.assertEqual(assistant.inventory["GoldCrowns"], 7)

    def test_book6_weaponsmith_and_cartographer_sales_match_source_prices(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6}, "Inventory": {"GoldCrowns": 0, "SpecialItems": ["Quiver"], "QuiverArrows": 4}, "CurrentSection": 98})
            assistant.apply_shop_sale("arrows")
            assistant.set_section(275)
            assistant.inventory["BackpackItems"] = ["Map of Tekaro"]
            sale = assistant.current_section_flow_payload()["Shop"]["Sales"][0]
            assistant.apply_shop_sale(sale["Id"])

        self.assertEqual(assistant.inventory["QuiverArrows"], 0)
        self.assertEqual(assistant.inventory["BackpackItems"], [])
        self.assertEqual(assistant.inventory["GoldCrowns"], 4)

    def test_book6_curing_applies_on_each_eligible_section_and_stops_at_original_end(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 6, "EnduranceCurrent": 10, "EnduranceMax": 32, "MagnakaiDisciplines": ["Curing"]},
                "Inventory": {"SpecialItems": ["Quiver"], "QuiverArrows": 5},
                "CurrentBookStats": {"BookNumber": 6, "StartingEnduranceMax": 24},
                "CurrentSection": 97,
            })
            assistant.set_section(98)
            flow = assistant.current_section_flow_payload()
            assistant.set_section(100)
            after_second_section = assistant.character["EnduranceCurrent"]
            assistant.character["EnduranceCurrent"] = 24
            assistant.set_section(101)

        self.assertTrue(flow["Healing"]["Applied"])
        self.assertEqual(flow["Healing"]["Name"], "Curing")
        self.assertEqual(flow["Healing"]["TargetEndurance"], 24)
        self.assertEqual(after_second_section, 12)
        self.assertEqual(assistant.character["EnduranceCurrent"], 24)
        self.assertEqual(assistant.arrow_inventory_payload(), {"Arrows": 5, "Quivers": 1, "Capacity": 6, "OpenSlots": 1})

    def test_book6_weaponsmith_uses_source_arrow_prices_and_quiver_capacity(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 6},
                "Inventory": {"GoldCrowns": 2, "SpecialItems": ["Quiver"], "QuiverArrows": 4},
                "CurrentSection": 98,
            })
            flow = assistant.current_section_flow_payload()
            assistant.apply_flow_loot("buy-arrows")
            assistant.apply_shop_sale("arrows")

        self.assertTrue(any(item["id"] == "buy-arrows" and item["Ready"] for item in flow["Loot"]))
        self.assertFalse(any("Quiver" in item["Label"] for item in flow["Shop"]["Sales"]))
        self.assertIn({"Id": "arrows", "Label": "4 Arrows", "Price": 1, "Kind": "arrows", "Quantity": 4}, flow["Shop"]["Sales"])
        self.assertEqual(assistant.inventory["QuiverArrows"], 2)
        self.assertEqual(assistant.inventory["GoldCrowns"], 2)

    def test_book6_final_section_records_campaign_completion(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6}, "CurrentSection": 350})
            assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertIn(6, assistant.character["CompletedBooks"])
        self.assertEqual(assistant.automation["Ending"]["Type"], "success")

    def test_book7_setup_preserves_campaign_and_adds_v1_start_state(self) -> None:
        source = lonewolf_redux.default_state()
        source["Character"].update({"BookNumber": 6, "MagnakaiDisciplines": ["Curing", "Nexus", "Weaponmastery"], "WeaponmasteryWeapons": ["Sword", "Bow", "Axe"]})
        source["Inventory"].update({"SpecialItems": ["Cess"], "BackpackItems": ["Meal"], "GoldCrowns": 20})
        result = lonewolf_redux.prepare_book7_state(source, magnakai_discipline="Divination", weaponmastery_weapon="Mace", gold_roll=5, equipment_choices=["fireseeds", "quiver"])
        self.assertEqual(result["Character"]["BookNumber"], 7)
        self.assertEqual(result["Character"]["MagnakaiRank"], 4)
        self.assertIn("Power-key", result["Inventory"]["PocketSpecialItems"])
        self.assertEqual(result["Inventory"]["QuiverArrows"], 6)
        self.assertEqual(result["Inventory"]["GoldCrowns"], 35)

    def test_book7_terminal_source_section_registers_death(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 7}, "CurrentSection": 349})
            assistant.apply_section_automation(force=True, visit_changed=True)
        self.assertTrue(assistant.death_active())

    def test_book7_oxygen_rnt_applies_the_v1_base_modifier_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 7, "EnduranceCurrent": 20, "EnduranceMax": 20}, "CurrentSection": 26})
            result = assistant.roll_current_section(raw_roll=4)
        self.assertEqual(result["Total"], 7)
        self.assertEqual(assistant.character["EnduranceCurrent"], 13)

    def test_book8_setup_adds_pass_and_fifth_magnakai_rank(self) -> None:
        source = lonewolf_redux.default_state()
        source["Character"].update({"BookNumber": 7, "MagnakaiDisciplines": ["Curing", "Nexus", "Divination", "Weaponmastery"], "WeaponmasteryWeapons": ["Sword", "Bow", "Axe", "Mace"]})
        result = lonewolf_redux.prepare_book8_state(source, magnakai_discipline="Psi-screen", weaponmastery_weapon="Dagger", gold_roll=0, equipment_choices=["rope"])
        self.assertEqual(result["Character"]["BookNumber"], 8)
        self.assertEqual(result["Character"]["MagnakaiRank"], 5)
        self.assertIn("Pass", result["Inventory"]["PocketSpecialItems"])

    def test_standalone_book6_matches_the_v1_magnakai_starting_rules(self) -> None:
        result = lonewolf_redux.create_magnakai_character_state(
            book_number=6,
            name="Standalone Six",
            magnakai_disciplines=["Curing", "Weaponmastery", "Nexus"],
            weaponmastery_weapons=["Sword", "Bow", "Axe"],
            combat_skill_roll=4,
            endurance_roll=7,
            gold_roll=3,
            equipment_choices=["sword", "quiver", "rations", "padded", "axe", "tinderbox", "rope"],
            de_curing_option=3,
            de_weaponskill_option=1,
        )
        self.assertEqual(result["RuleSet"], "Magnakai")
        self.assertEqual(result["Character"]["MagnakaiRank"], 3)
        self.assertEqual(result["Character"]["CombatSkillBase"], 14)
        self.assertEqual(result["Character"]["EnduranceMax"], 27)
        self.assertEqual(result["Inventory"]["GoldCrowns"], 13)
        self.assertIn("Map of the Stornlands", result["Inventory"]["SpecialItems"])
        self.assertEqual(result["Inventory"]["QuiverArrows"], 6)
        self.assertFalse(result["Inventory"]["HasHerbPouch"])

    def test_standalone_book7_and_8_add_their_fixed_pocket_items(self) -> None:
        book7 = lonewolf_redux.create_magnakai_character_state(
            book_number=7,
            magnakai_disciplines=["Curing", "Nexus", "Divination", "Weaponmastery"],
            weaponmastery_weapons=["Sword", "Bow", "Axe", "Mace"],
            gold_roll=0,
            equipment_choices=["quiver", "fireseeds", "rope", "laumspur", "lantern"],
        )
        book8 = lonewolf_redux.create_magnakai_character_state(
            book_number=8,
            magnakai_disciplines=["Curing", "Nexus", "Divination", "Weaponmastery", "Psi-screen"],
            weaponmastery_weapons=["Sword", "Bow", "Axe", "Mace", "Dagger"],
            gold_roll=9,
            equipment_choices=["rope", "laumspur", "lantern", "meals", "fireseeds"],
        )
        self.assertEqual(book7["Character"]["MagnakaiRank"], 4)
        self.assertIn("Power-key", book7["Inventory"]["PocketSpecialItems"])
        self.assertEqual(book7["Inventory"]["QuiverArrows"], 6)
        self.assertEqual(book8["Character"]["MagnakaiRank"], 5)
        self.assertIn("Pass", book8["Inventory"]["PocketSpecialItems"])
        self.assertEqual(book8["Inventory"]["GoldCrowns"], 19)

    def test_magnakai_lore_circles_apply_v1_stat_bonuses_and_route_aliases(self) -> None:
        state = lonewolf_redux.create_magnakai_character_state(
            book_number=6,
            magnakai_disciplines=["Weaponmastery", "Huntmastery", "Curing"],
            weaponmastery_weapons=["Sword", "Bow", "Axe"],
            combat_skill_roll=0,
            endurance_roll=0,
            equipment_choices=["sword", "laumspur", "quiver", "rations", "padded", "tinderbox", "rope"],
        )
        self.assertEqual(state["Character"]["LoreCirclesCompleted"], ["Circle of Fire"])
        self.assertEqual(state["Character"]["CombatSkillBase"], 11)
        self.assertEqual(state["Character"]["EnduranceMax"], 22)

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state = state
            self.assertTrue(assistant.evaluate_flow_condition({"type": "lore_circle", "name": "Fire"}))

    def test_book8_cabin_roll_uses_v1_lore_circle_precedence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state(
                {
                    "Character": {
                        "BookNumber": 8,
                        "LoreCirclesCompleted": ["Circle of Fire", "Circle of Light"],
                    },
                    "CurrentSection": 17,
                }
            )
            result = assistant.roll_current_section(raw_roll=5)

        self.assertEqual(result["Total"], 8)
        self.assertEqual(result["Route"], 77)

    def test_v1_lore_circle_bonus_is_not_applied_twice_during_a_handoff(self) -> None:
        source = lonewolf_redux.default_state()
        source["Character"].update(
            {
                "BookNumber": 6,
                "CombatSkillBase": 21,
                "CombatSkillCurrent": 21,
                "EnduranceMax": 30,
                "EnduranceCurrent": 30,
                "MagnakaiDisciplines": ["Weaponmastery", "Huntmastery", "Curing"],
                "WeaponmasteryWeapons": ["Sword", "Bow", "Axe"],
                "LoreCirclesCompleted": ["Circle of Fire"],
            }
        )
        source["EquipmentBonuses"] = {"LoreCircleCombatSkill": 1, "LoreCircleEndurance": 2}
        result = lonewolf_redux.prepare_book7_state(
            source,
            magnakai_discipline="Divination",
            weaponmastery_weapon="Dagger",
            gold_roll=0,
            equipment_choices=[],
        )
        self.assertEqual(result["Character"]["CombatSkillBase"], 21)
        self.assertEqual(result["Character"]["EnduranceMax"], 30)
        self.assertEqual(result["Character"]["LoreCircleBonuses"], {"CombatSkill": 1, "Endurance": 2})

    def test_standalone_magnakai_creation_rejects_invalid_rank_setup(self) -> None:
        with self.assertRaisesRegex(ValueError, "exactly 4 Magnakai"):
            lonewolf_redux.create_magnakai_character_state(
                book_number=7,
                magnakai_disciplines=["Curing", "Nexus", "Divination"],
            )

    def test_book8_terminal_source_section_registers_death(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8}, "CurrentSection": 281})
            assistant.apply_section_automation(force=True, visit_changed=True)
        self.assertTrue(assistant.death_active())

    def test_magnakai_final_sections_complete_books7_to12(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            completed = []
            for book_number in range(7, 13):
                assistant.state = lonewolf_redux.normalize_state(
                    {"Character": {"BookNumber": book_number}, "CurrentSection": 350}
                )
                assistant.apply_section_automation(force=True, visit_changed=True)
                completed.append(book_number in assistant.character["CompletedBooks"])

        self.assertEqual(completed, [True] * 6)

    def test_books9_to12_source_terminal_deaths_lock_permadeath_runs(self) -> None:
        terminal_sections = {
            9: [4, 20, 44, 73, 112, 125, 152, 195, 211, 340],
            10: [10, 17, 24, 55, 63, 74, 91, 95, 189, 207, 214, 243, 264, 343, 347],
            11: [11, 46, 57, 98, 99, 104, 111, 214, 236, 239, 324, 328],
            12: [3, 19, 38, 40, 62, 69, 72, 73, 90, 122, 132, 199, 208, 250, 277, 318, 331, 340, 341, 345],
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            for difficulty in ("Easy", "Normal", "Hard", "Veteran"):
                for book_number, sections in terminal_sections.items():
                    for section in sections:
                        assistant.state = lonewolf_redux.normalize_state(
                            {"Character": {"BookNumber": book_number}, "CurrentSection": section}
                        )
                        assistant.set_run_configuration(difficulty, True, "DataFile")
                        assistant.apply_section_automation(force=True, visit_changed=True)
                        recovery = assistant.death_recovery_payload()
                        self.assertTrue(assistant.death_active(), (difficulty, book_number, section))
                        self.assertEqual(assistant.run_state["Status"], "Dead")
                        self.assertFalse(recovery["CanRepeat"])
                        self.assertFalse(recovery["CanRewind"])

    def test_book7_and_8_source_choice_overlays_keep_all_explicit_routes(self) -> None:
        expected_routes = {
            7: {
                100: {34, 270},
                315: {122, 254, 309},
                338: {315},
            },
            8: {
                89: {266, 348},
                126: {16, 141},
                141: {59, 338},
                244: {20, 37, 89},
                299: {266, 348},
                316: {139, 204, 242},
                338: {7, 133},
            },
        }
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            for book_number, sections in expected_routes.items():
                for section, expected in sections.items():
                    entry = assistant.section_flow_entry(book_number, section)
                    actual = {
                        route["Section"]
                        for route in assistant.flow_source_route_payload(entry)
                    }
                    self.assertEqual(actual, expected, (book_number, section))

    def test_book6_and_7_source_roll_overlays_follow_printed_boundaries(self) -> None:
        cases = [
            (6, 95, 3, 155), (6, 95, 4, 12),
            (6, 101, 4, 348), (6, 101, 5, 207),
            (6, 170, 5, 23), (6, 170, 6, 265),
            (6, 178, 7, 296), (6, 178, 8, 303),
            (6, 243, 3, 155), (6, 243, 4, 292), (6, 243, 9, 264),
            (6, 268, 5, 155), (6, 268, 6, 236), (6, 268, 9, 75),
            (7, 35, 4, 97), (7, 35, 5, 246),
            (7, 39, 4, 344), (7, 39, 5, 58),
            (7, 55, 2, 189), (7, 55, 3, 62),
            (7, 116, 2, 77), (7, 116, 3, 198), (7, 116, 7, 235),
            (7, 128, 1, 77), (7, 128, 2, 198),
            (7, 166, 2, 275), (7, 166, 3, 222), (7, 166, 8, 311),
            (7, 175, 8, 19), (7, 185, 8, 241), (7, 185, 9, 106),
            (7, 255, 2, 154), (7, 255, 3, 208), (7, 255, 9, 52),
            (7, 327, 4, 184), (7, 327, 5, 4),
            (7, 343, 7, 69), (7, 343, 8, 197),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            for book_number, section, raw_roll, expected_route in cases:
                assistant.state = lonewolf_redux.normalize_state(
                    {"Character": {"BookNumber": book_number, "EnduranceCurrent": 19, "EnduranceMax": 19}, "CurrentSection": section}
                )
                result = assistant.evaluate_roll_flow(
                    assistant.current_section_flow_entry() or {}, raw_roll
                )
                self.assertEqual(
                    result["Route"], expected_route,
                    (book_number, section, raw_roll),
                )

            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 6, "MagnakaiDisciplines": ["Huntmastery"]}, "CurrentSection": 101}
            )
            self.assertEqual(assistant.evaluate_roll_flow(assistant.current_section_flow_entry() or {}, 2)["Route"], 207)

            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 6, "SpecialItems": ["Silver Bow of Duadon"]}, "CurrentSection": 178}
            )
            self.assertEqual(assistant.evaluate_roll_flow(assistant.current_section_flow_entry() or {}, 7)["Route"], 296)

            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 7, "MagnakaiDisciplines": ["Nexus"]}, "CurrentSection": 175}
            )
            self.assertEqual(assistant.evaluate_roll_flow(assistant.current_section_flow_entry() or {}, 6)["Route"], 314)

            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 7}, "CurrentSection": 175}
            )
            self.assertEqual(assistant.evaluate_roll_flow(assistant.current_section_flow_entry() or {}, 6)["Route"], 19)

    def test_every_configured_random_number_table_roll_has_a_defined_outcome(self) -> None:
        profiles = ({}, {"KaiDisciplines": lonewolf_redux.KAI_DISCIPLINES, "MagnakaiDisciplines": lonewolf_redux.MAGNAKAI_DISCIPLINES, "WeaponmasteryWeapons": ["Bow", "Sword"], "Weapons": ["Sommerswerd", "Bow", "Sword"], "BackpackItems": ["Rope", "Lantern"], "SpecialItems": ["Silver Bow of Duadon"], "MagnakaiRank": 20})
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            for profile in profiles:
                for raw_book_number, sections in assistant.section_flows.items():
                    if not str(raw_book_number).isdigit() or not isinstance(sections, dict):
                        continue
                    for raw_section, flow in sections.items():
                        if not str(raw_section).isdigit() or not isinstance(flow, dict) or not isinstance(flow.get("roll"), dict):
                            continue
                        book_number, section = int(raw_book_number), int(raw_section)
                        character = {"BookNumber": book_number, "EnduranceCurrent": 50, "EnduranceMax": 50, "CombatSkillCurrent": 50, "CombatSkillMax": 50}
                        character.update(profile)
                        assistant.state = lonewolf_redux.normalize_state({"Character": character, "CurrentSection": section})
                        for raw_roll in range(10):
                            result = assistant.evaluate_roll_flow(flow, raw_roll)
                            self.assertTrue(
                                result.get("Route") is not None or result.get("Actions") or result.get("Outcome"),
                                (book_number, section, raw_roll),
                            )

    def test_book6_archery_tournament_routes_its_completed_total(self) -> None:
        cases = [
            ([], (0, 0, 7), 103),
            ([], (0, 0, 8), 26),
            (["Weaponmastery"], (0, 0, 4), 103),
            (["Weaponmastery"], (0, 0, 5), 26),
        ]
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            for disciplines, rolls, expected_route in cases:
                assistant.state = lonewolf_redux.normalize_state(
                    {"Character": {"BookNumber": 6, "MagnakaiDisciplines": disciplines, "WeaponmasteryWeapons": ["Bow"]}, "CurrentSection": 340}
                )
                results = [assistant.roll_current_section(raw_roll) for raw_roll in rolls]
                self.assertEqual(results[-1]["Route"], expected_route, (disciplines, rolls))

    def test_book8_section287_vordaks_have_no_source_timer_and_route_on_victory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.autosave = lambda: None
            assistant.state = lonewolf_redux.normalize_state(
                {"Character": {"BookNumber": 8, "MagnakaiDisciplines": ["Psi-surge"]}, "CurrentSection": 287}
            )
            assistant.start_section_combat("book8-287")
            self.assertEqual(len(assistant.combat["EnemyQueue"]), 2)
            self.assertEqual(assistant.combat["RoundLimit"], 0)
            self.assertEqual(assistant.combat["VictoryRoute"], 79)
            assistant.combat_round(["combat", "manual"], manual_losses=(999, 0))
            self.assertTrue(assistant.combat["Active"])
            assistant.combat_round(["combat", "manual"], manual_losses=(999, 0))
            self.assertFalse(assistant.combat["Active"])
            self.assertEqual(assistant.state["CurrentSection"], 79)

    def test_book8_giak_scroll_is_added_to_pocket_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8}, "CurrentSection": 312})
            assistant.apply_section_automation(force=True, visit_changed=True)
        self.assertIn("Giak Scroll", assistant.inventory["PocketSpecialItems"])
        self.assertNotIn("Giak Scroll", assistant.inventory["SpecialItems"])

    def test_magnakai_flow_conditions_cover_rank_lore_and_weaponmastery(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8, "MagnakaiDisciplines": ["Weaponmastery"], "MagnakaiRank": 5, "WeaponmasteryWeapons": ["Bow"], "LoreCirclesCompleted": ["Fire"]}})
        self.assertTrue(assistant.evaluate_flow_condition({"type": "magnakai_rank_gte", "value": 4}))
        self.assertTrue(assistant.evaluate_flow_condition({"type": "lore_circle", "name": "Fire"}))
        self.assertTrue(assistant.evaluate_flow_condition({"type": "weaponmastery_weapon", "name": "Bow"}))

    def test_reader_marks_explicit_magnakai_route_gates_and_engine_enforces_them(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "books" / "09tcof"
            source.mkdir(parents=True)
            (source / "sect23.htm").write_text(
                '<p class="choice">If you have the Magnakai Discipline of Pathsmanship, turn to <a href="sect337.htm">337</a>.</p>',
                encoding="utf-8",
            )
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 9}, "CurrentSection": 23})
            locked = assistant.current_section_flow_payload()["SourceRoutes"][0]
            assistant.follow_route(337)
            locked_section = assistant.state["CurrentSection"]

            assistant.state["Character"]["MagnakaiDisciplines"] = ["Pathsmanship"]
            unlocked = assistant.current_section_flow_payload()["SourceRoutes"][0]
            assistant.follow_route(337)

        self.assertFalse(locked["Available"])
        self.assertIn("Pathsmanship", locked["BlockedReason"])
        self.assertEqual(locked_section, 23)
        self.assertTrue(unlocked["Available"])
        self.assertEqual(assistant.state["CurrentSection"], 337)

    def test_required_combat_route_cannot_be_followed_before_the_current_fight_is_won(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.create_book1_character_state(
                kai_disciplines=["Sixth Sense", "Hunting", "Healing", "Weaponskill", "Mindblast"]
            )
            assistant.set_run_configuration("Normal", False, "ManualCRT")
            with redirect_stdout(io.StringIO()):
                assistant.set_section(255)
                assistant.follow_route(82)
                blocked_section = assistant.state["CurrentSection"]
                assistant.start_section_combat("255-gourgaz")
                assistant.follow_route(82)
                active_section = assistant.state["CurrentSection"]
                assistant.combat_round(["combat", "manual"], manual_losses=(30, 0))

        self.assertEqual(blocked_section, 255)
        self.assertEqual(active_section, 255)
        self.assertFalse(assistant.combat["Active"])
        self.assertEqual(assistant.state["CurrentSection"], 82)
        self.assertTrue(assistant.state["CombatHistory"][-1]["VisitKey"].startswith("1:255:"))

    def test_reader_recognizes_explicit_item_rank_and_arrow_route_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 12, "MagnakaiRank": 5}})

            rope_condition, rope_reason = assistant.infer_source_route_condition(
                "If you have a Rope and wish to use it, turn to 48."
            )
            rank_condition, rank_reason = assistant.infer_source_route_condition(
                "If you have reached the rank of Principalin or higher, turn to 12."
            )
            arrow_condition, arrow_reason = assistant.infer_source_route_condition(
                "If you have at least two Arrows in your Quiver, turn to 344."
            )
            ticket_condition, ticket_reason = assistant.infer_source_route_condition(
                "If you purchased a Riverboat Ticket for the riverboat at Soren, turn to 59."
            )

            self.assertFalse(assistant.evaluate_flow_condition(rope_condition))
            self.assertFalse(assistant.evaluate_flow_condition(rank_condition))
            self.assertFalse(assistant.evaluate_flow_condition(arrow_condition))
            self.assertFalse(assistant.evaluate_flow_condition(ticket_condition))
            assistant.inventory["BackpackItems"] = ["Rope"]
            assistant.inventory["PocketSpecialItems"] = ["Riverboat Ticket to Luyen"]
            assistant.inventory["QuiverArrows"] = 2
            assistant.character["MagnakaiRank"] = 6

        self.assertTrue(assistant.evaluate_flow_condition(rope_condition))
        self.assertTrue(assistant.evaluate_flow_condition(rank_condition))
        self.assertTrue(assistant.evaluate_flow_condition(arrow_condition))
        self.assertEqual(rope_reason, "Requires Rope.")
        self.assertEqual(rank_reason, "Requires Principalin rank.")
        self.assertEqual(arrow_reason, "Requires at least 2 Arrows.")
        self.assertEqual(ticket_reason, "Requires Riverboat Ticket.")

    def test_reader_preserves_compound_magnakai_and_named_item_route_gates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            source = base / "books"
            (source / "12tmod").mkdir(parents=True)
            (source / "12tmod" / "sect176.htm").write_text(
                '<p class="choice">If you possess either the Dagger of Vashna or the sword Helshezag and wish to use either of them, turn to <a href="sect230.htm">230</a>.</p>',
                encoding="utf-8",
            )
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=source,
            )
            assistant.state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 11, "MagnakaiRank": 7, "MagnakaiDisciplines": ["Pathsmanship"]},
            })
            compound, reason = assistant.infer_source_route_condition(
                "If you possess the Magnakai Discipline of Pathsmanship and have reached the rank of Scion-kai, or if you possess the Magnakai Discipline of Animal Control, turn to 309."
            )
            self.assertFalse(assistant.evaluate_flow_condition(compound))
            assistant.character["MagnakaiDisciplines"].append("Animal Control")
            self.assertTrue(assistant.evaluate_flow_condition(compound))
            self.assertIn("Scion-Kai", reason)

            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 12}, "CurrentSection": 176})
            locked = next(route for route in assistant.current_section_flow_payload()["SourceRoutes"] if route["Section"] == 230)
            assistant.follow_route(230)
            self.assertEqual(assistant.state["CurrentSection"], 176)
            assistant.inventory["SpecialItems"] = ["Helshezag"]
            unlocked = next(route for route in assistant.current_section_flow_payload()["SourceRoutes"] if route["Section"] == 230)
            assistant.follow_route(230)

        self.assertFalse(locked["Available"])
        self.assertIn("Helshezag", locked["BlockedReason"])
        self.assertTrue(unlocked["Available"])
        self.assertEqual(assistant.state["CurrentSection"], 230)

    def test_endurance_max_automation_clamps_current_endurance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"EnduranceCurrent": 24, "EnduranceMax": 24}})
        assistant.apply_automation_stat({"stat": "end_max", "delta": -4})
        self.assertEqual(assistant.character["EnduranceMax"], 20)
        self.assertEqual(assistant.character["EnduranceCurrent"], 20)

    def test_book8_rnt_uses_magnakai_rank_and_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8, "MagnakaiRank": 4}, "CurrentSection": 284})
            result = assistant.roll_current_section(raw_roll=3)
        self.assertEqual(result["Total"], 6)
        self.assertEqual(result["Route"], 119)

    def test_later_magnakai_unambiguous_rnt_rules_apply_source_modifiers_and_routes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )

            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 9}, "CurrentSection": 347})
            self.assertEqual(assistant.roll_current_section(raw_roll=6)["Route"], 260)
            assistant.set_section(347)
            self.assertEqual(assistant.roll_current_section(raw_roll=7)["Route"], 119)
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 9, "MagnakaiDisciplines": ["Divination"]}, "CurrentSection": 347})
            self.assertEqual(assistant.roll_current_section(raw_roll=0)["Route"], 36)

            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 10, "MagnakaiDisciplines": ["Huntmastery"], "EnduranceCurrent": 24, "EnduranceMax": 24}, "CurrentSection": 166})
            river = assistant.roll_current_section(raw_roll=0)
            self.assertEqual(river["Total"], 8)
            self.assertEqual(river["Route"], 186)
            self.assertEqual(assistant.character["EnduranceCurrent"], 16)

            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 10, "MagnakaiDisciplines": ["Curing"], "EnduranceCurrent": 24, "EnduranceMax": 24}, "CurrentSection": 203})
            arrows = assistant.roll_current_section(raw_roll=0)
            self.assertEqual(arrows["Total"], 7)
            self.assertEqual(arrows["Route"], 190)
            self.assertEqual(assistant.character["EnduranceCurrent"], 17)

            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 12, "LoreCirclesCompleted": ["Solaris"], "EnduranceCurrent": 24, "EnduranceMax": 24}, "CurrentSection": 172})
            fall = assistant.roll_current_section(raw_roll=0)
            self.assertEqual(fall["Total"], 8)
            self.assertEqual(fall["Route"], 222)
            self.assertEqual(assistant.character["EnduranceCurrent"], 16)

            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 10, "MagnakaiDisciplines": ["Weaponmastery"], "WeaponmasteryWeapons": ["Bow"]}, "CurrentSection": 70})
            self.assertEqual(assistant.roll_current_section(raw_roll=5)["Route"], 195)
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 11, "MagnakaiDisciplines": ["Weaponmastery"], "WeaponmasteryWeapons": ["Bow"]}, "CurrentSection": 322})
            self.assertEqual(assistant.roll_current_section(raw_roll=6)["Route"], 286)
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 12, "MagnakaiDisciplines": ["Weaponmastery", "Huntmastery"], "WeaponmasteryWeapons": ["Bow"], "MagnakaiRank": 9}, "CurrentSection": 324})
            self.assertEqual(assistant.roll_current_section(raw_roll=4)["Route"], 287)

            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 9}, "Inventory": {"SpecialItems": ["First", "Second"], "BackpackItems": ["Rope"]}, "CurrentSection": 201})
            self.assertEqual(assistant.roll_current_section(raw_roll=7)["Outcome"], "Second Special Item stolen")
            self.assertEqual(assistant.inventory["SpecialItems"], ["First"])
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 9}, "Inventory": {"SpecialItems": ["Only Special"], "BackpackItems": ["Rope"]}, "CurrentSection": 201})
            self.assertEqual(assistant.roll_current_section(raw_roll=0)["Outcome"], "First Backpack Item stolen")
            self.assertEqual(assistant.inventory["BackpackItems"], [])

    def test_book8_source_entry_effect_restores_endurance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8, "EnduranceCurrent": 8, "EnduranceMax": 24}, "CurrentSection": 100})
            assistant.apply_section_automation(force=True, visit_changed=True)
        self.assertEqual(assistant.character["EnduranceCurrent"], 24)

    def test_book8_route_payment_matches_source_cost(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8}, "Inventory": {"GoldCrowns": 25}, "CurrentSection": 244})
            assistant.follow_route(20)
        self.assertEqual(assistant.inventory["GoldCrowns"], 5)
        self.assertEqual(assistant.state["CurrentSection"], 20)

    def test_book8_levitron_escape_route_persists_source_flag(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8}, "CurrentSection": 267})
            assistant.follow_route(350)
        self.assertTrue(assistant.automation_flags["book8LevitronEscapeRoute"])

    def test_book8_grey_ring_exchange_uses_the_source_eligible_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8}, "Inventory": {"SpecialItems": ["Lodestone", "Shield"]}, "CurrentSection": 242})
            candidates = assistant.current_loss_choices_payload()[0]["Candidates"]
            assistant.apply_section_loss("grey-ring-exchange", "special", "Lodestone")

        self.assertEqual([candidate["Item"] for candidate in candidates], ["Lodestone"])
        self.assertNotIn("Lodestone", assistant.inventory["SpecialItems"])
        self.assertIn("Grey Crystal Ring", assistant.inventory["SpecialItems"])

    def test_book8_riddle_penalty_removes_the_fourth_special_item(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 8}, "Inventory": {"SpecialItems": ["One", "Two", "Three", "Four"]}, "CurrentSection": 269})
            assistant.apply_section_automation(force=True, visit_changed=True)

        self.assertEqual(assistant.inventory["SpecialItems"], ["One", "Two", "Three"])

    def test_book7_tainted_water_clears_food_then_offers_two_item_losses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 7}, "Inventory": {"BackpackItems": ["Meal", "Rope", "Special Rations", "Lantern", "Knife"]}, "CurrentSection": 158})
            assistant.apply_section_automation(force=True, visit_changed=True)
            assistant.apply_section_loss("tainted-water-loss-one", "backpack", "Rope")
            assistant.apply_section_loss("tainted-water-loss-two", "backpack", "Lantern")

        self.assertEqual(assistant.inventory["BackpackItems"], ["Knife"])

    def test_book7_all_gear_confiscation_stashes_and_restores_pocket_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 7}, "Inventory": {"Weapons": ["Sword"], "BackpackItems": ["Rope"], "SpecialItems": ["Shield"], "PocketSpecialItems": ["Power-key"], "HerbPouchItems": ["Aloe"], "GoldCrowns": 11}, "CurrentSection": 335})
            assistant.apply_section_automation(force=True, visit_changed=True)
            assistant.apply_automation_action({"type": "gear", "available": True})

        self.assertEqual(assistant.inventory["Weapons"], ["Sword"])
        self.assertEqual(assistant.inventory["BackpackItems"], ["Rope"])
        self.assertEqual(assistant.inventory["SpecialItems"], ["Shield"])
        self.assertEqual(assistant.inventory["PocketSpecialItems"], ["Power-key"])
        self.assertEqual(assistant.inventory["HerbPouchItems"], ["Aloe"])
        self.assertEqual(assistant.inventory["GoldCrowns"], 11)

    def test_book7_story_route_persists_source_flags(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 7}, "CurrentSection": 138})
            assistant.follow_route(118)
        self.assertTrue(assistant.automation_flags["book7ZahdaBlueBeamPursuit"])
        self.assertTrue(assistant.automation_flags["book7BlueBeamRoute"])

    def test_book7_source_entry_effect_loses_quiver_arrows(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 7}, "Inventory": {"QuiverArrows": 6}, "CurrentSection": 7})
            assistant.apply_section_automation(force=True, visit_changed=True)
        self.assertEqual(assistant.inventory["QuiverArrows"], 0)

    def test_book7_curing_body_loot_filters_blue_pills(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 7, "MagnakaiDisciplines": ["Curing"]}, "CurrentSection": 227})
            options = {item["id"] for item in assistant.flow_loot_options()}
        self.assertIn("sabito", options)
        self.assertNotIn("blue-pills", options)

    def test_book6_warhammer_roll_uses_only_the_printed_huntmastery_bonus(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6, "MagnakaiDisciplines": ["Weaponmastery", "Huntmastery"]}, "Inventory": {"BackpackItems": ["Rope", "Rope"]}, "CurrentSection": 101})
            result = assistant.roll_current_section(raw_roll=0)
        self.assertEqual(result["Total"], 3)

    def test_book6_rats_remove_all_meals_and_special_rations(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6}, "Inventory": {"BackpackItems": ["Meal", "Rope", "Special Rations", "Meal"]}, "CurrentSection": 35})
            assistant.apply_section_automation(force=True, visit_changed=True)
        self.assertEqual(assistant.inventory["BackpackItems"], ["Rope"])

    def test_book6_living_strands_offer_special_weapon_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6}, "Inventory": {"SpecialItems": ["Sommerswerd", "Shield"]}, "CurrentSection": 4})
            choice = assistant.current_loss_choices_payload()[0]
        self.assertEqual([candidate["Item"] for candidate in choice["Candidates"]], ["Sommerswerd"])

    def test_completed_book6_continues_through_engine_to_book7(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state["Character"].update({"BookNumber": 6, "MagnakaiDisciplines": ["Curing", "Nexus", "Weaponmastery"], "WeaponmasteryWeapons": ["Sword", "Bow", "Axe"]})
            assistant.state["Automation"]["Ending"] = {"BookNumber": 6, "Type": "success"}
            assistant.continue_completed_book(book6_magnakai_disciplines="Divination", book6_weaponmastery_weapons="Mace", book6_gold_roll=0)
        self.assertEqual(assistant.character["BookNumber"], 7)

    def test_magnakai_combat_catalogue_loads_source_encounters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            self.assertGreaterEqual(len(assistant.section_flows["6"]), 70)
            self.assertGreaterEqual(len(assistant.section_flows["7"]), 78)
            self.assertGreaterEqual(len(assistant.section_flows["8"]), 67)
            assistant.state["Character"].update({"BookNumber": 6, "MagnakaiDisciplines": ["Animal Control"]})
            assistant.set_section(71)
            assistant.start_section_combat()

        self.assertEqual(assistant.combat["EnemyName"], "Redbeard")
        self.assertEqual(assistant.combat["EnemyCombatSkill"], 19)
        self.assertEqual(assistant.combat["EnemyEnduranceMax"], 28)
        self.assertEqual(assistant.combat["Modifier"], 2)
        self.assertEqual(assistant.combat["VictoryRoute"], 237)

    def test_later_magnakai_combat_catalogue_starts_source_encounters(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 9
            assistant.set_section(10)
            assistant.start_section_combat()
            book9 = {
                "name": assistant.combat["EnemyName"],
                "cs": assistant.combat["EnemyCombatSkill"],
                "endurance": assistant.combat["EnemyEnduranceMax"],
                "route": assistant.combat["VictoryRoute"],
            }

            assistant.state["Character"]["BookNumber"] = 12
            assistant.set_section(171)
            assistant.start_section_combat()
            book12 = {
                "cs": assistant.combat["EnemyCombatSkill"],
                "endurance": assistant.combat["EnemyEnduranceMax"],
                "route": assistant.combat["VictoryRoute"],
            }

        self.assertEqual(book9, {"name": "Zakhan Kimah", "cs": 30, "endurance": 38, "route": 350})
        self.assertEqual(book12, {"cs": 45, "endurance": 48, "route": 240})

    def test_magnakai_v1_entry_rule_manifest_remains_covered(self) -> None:
        expected = {
            6: {2, 4, 8, 10, 16, 17, 27, 35, 37, 40, 44, 48, 49, 50, 51, 54, 62, 65, 76, 85, 88, 96, 98, 106, 109, 111, 112, 113, 123, 124, 137, 139, 141, 145, 146, 153, 157, 158, 160, 164, 165, 169, 171, 172, 174, 187, 190, 191, 197, 200, 205, 207, 209, 211, 212, 214, 220, 222, 223, 232, 245, 246, 248, 252, 253, 266, 273, 275, 276, 278, 282, 293, 295, 297, 301, 304, 306, 307, 310, 313, 315, 316, 318, 322, 328, 348},
            7: {1, 5, 7, 10, 15, 18, 31, 32, 42, 43, 44, 58, 59, 60, 73, 80, 88, 103, 104, 105, 107, 108, 112, 120, 122, 134, 148, 154, 155, 158, 170, 186, 190, 198, 199, 219, 220, 222, 227, 238, 262, 264, 265, 271, 284, 297, 301, 304, 305, 311, 313, 324, 333, 335, 340, 344},
            8: {1, 7, 15, 16, 34, 39, 40, 59, 87, 100, 104, 105, 115, 129, 139, 146, 150, 152, 156, 159, 170, 175, 201, 202, 226, 228, 230, 242, 258, 269, 274, 294, 306, 312, 325, 337},
        }
        root = Path(lonewolf_redux.__file__).resolve().parent / "data"
        for book_number, sections in expected.items():
            simple = json.loads((root / f"book{book_number}-simple-automations.json").read_text(encoding="utf-8"))[str(book_number)]
            flows = json.loads((root / f"book{book_number}-section-flows.json").read_text(encoding="utf-8"))[str(book_number)]
            covered = {int(section) for section in simple} | {int(section) for section in flows}
            self.assertTrue(sections.issubset(covered), f"Book {book_number} missing {sorted(sections - covered)}")

    def test_magnakai_combat_and_rnt_catalogue_totals_remain_source_complete(self) -> None:
        expected_combat = {6: 28, 7: 39, 8: 37, 9: 38, 10: 40, 11: 37, 12: 59}
        expected_rnt = {6: 22, 7: 22, 8: 16, 9: 20, 10: 27, 11: 29, 12: 40}
        root = Path(lonewolf_redux.__file__).resolve().parent / "data"
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=root,
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            for book_number in expected_combat:
                flows = assistant.section_flows[str(book_number)]
                combat_count = sum(len(entry.get("combat", [])) for entry in flows.values() if isinstance(entry, dict))
                rnt_count = sum(
                    1
                    for entry in flows.values()
                    if isinstance(entry, dict)
                    and (
                        "roll" in entry
                        or "stagedRoll" in entry
                        or "diceGame" in entry
                        or any(
                            str(loot.get("id") or "") == "book12-145-adgana"
                            for loot in entry.get("loot", [])
                            if isinstance(loot, dict)
                        )
                    )
                )
                self.assertEqual(combat_count, expected_combat[book_number])
                self.assertEqual(rnt_count, expected_rnt[book_number])

    def test_book10_128_requires_and_applies_the_chosen_weapon(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"].update({"BookNumber": 10, "MagnakaiDisciplines": ["Huntmastery"]})
            assistant.state["Inventory"]["Weapons"] = ["Dagger", "Axe"]
            assistant.set_section(128)
            self.assertTrue(assistant.roll_current_section(7)["Blocked"])
            assistant.set_roll_selection("book10-128-strike-weapon", "Dagger")
            result = assistant.roll_current_section(7)
            self.assertEqual((result["Total"], result["Route"]), (6, 95))
            assistant.set_roll_selection("book10-128-strike-weapon", "Axe")
            result = assistant.roll_current_section(7)
            self.assertEqual((result["Total"], result["Route"]), (10, 233))

    def test_book10_218_dice_game_books_gold_and_can_leave(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 10
            assistant.state["Inventory"]["GoldCrowns"] = 10
            assistant.set_section(218)
            with mock.patch.object(lonewolf_redux, "random_digit", side_effect=[1, 1, 2, 2, 3, 3]):
                assistant.play_dice_game("book10-218-lune-dice")
            game = assistant.current_dice_game_payload()
            self.assertEqual(assistant.inventory["GoldCrowns"], 13)
            self.assertEqual(game["LastResult"]["OpponentTotals"], [2, 4])
            self.assertEqual(game["LastResult"]["PlayerTotal"], 6)
            self.assertTrue(game["LastResult"]["Won"])
            assistant.leave_dice_game("book10-218-lune-dice")
            self.assertEqual(assistant.state["CurrentSection"], 29)

    def test_adgana_consumes_a_dose_adds_combat_skill_and_checks_addiction(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"].update({"BookNumber": 12, "EnduranceMax": 20, "EnduranceCurrent": 20})
            assistant.state["Inventory"]["SpecialItems"] = ["Dose of Adgana"]
            assistant.set_section(2)
            self.assertEqual(assistant.current_adgana_payload()["Bonus"], 6)
            assistant.prepare_adgana_for_current_combat()
            self.assertNotIn("Dose of Adgana", assistant.inventory["SpecialItems"])
            assistant.start_section_combat()
            modifier, notes = assistant.combat_weapon_modifier_and_notes()
            self.assertEqual(assistant.combat["AdganaBonus"], 6)
            self.assertIn("Adgana: +6 CS", notes)
            self.assertEqual(modifier, 6)
            assistant.combat["EnemyEnduranceCurrent"] = 0
            assistant.combat["Log"] = [{"Round": 1, "PlayerLoss": 0, "EnemyLoss": 27}]
            with mock.patch.object(lonewolf_redux, "random_digit", return_value=1):
                self.assertTrue(assistant.route_after_combat_round())
            self.assertEqual(assistant.character["EnduranceMax"], 16)
            self.assertTrue(assistant.automation_flags["adganaUsed"])
            self.assertTrue(assistant.state["CombatHistory"][-1]["Adgana"]["Addicted"])
            assistant.state["Inventory"]["SpecialItems"] = ["Dose of Adgana"]
            assistant.set_section(2)
            self.assertEqual(assistant.current_adgana_payload()["Bonus"], 3)

    def test_magnakai_combat_restrictions_and_conditional_damage_match_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"].update({"BookNumber": 6, "MagnakaiDisciplines": ["Curing"]})
            assistant.state["Inventory"]["Weapons"] = ["Bow", "Sword"]
            assistant.set_section(47)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_active_weapon(), "Sword")

            assistant.state["Character"]["BookNumber"] = 7
            assistant.set_section(76)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["PlayerLossMultiplier"], 3)
            assistant.set_section(301)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat["PlayerLossMultiplier"], 1)
            assistant.state["Character"]["MagnakaiDisciplines"] = []
            assistant.start_section_combat()

        self.assertEqual(assistant.combat["PlayerLossMultiplier"], 2)

    def test_magnakai_combat_threshold_route_stops_before_enemy_death(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"]["BookNumber"] = 6
            assistant.set_section(78)
            assistant.start_section_combat()
            assistant.combat["EnemyEnduranceCurrent"] = 11
            assistant.combat["Log"] = [{"Round": 1, "PlayerLoss": 0, "EnemyLoss": 19}]
            self.assertTrue(assistant.route_after_combat_round())

        self.assertFalse(assistant.combat["Active"])
        self.assertEqual(assistant.state["CurrentSection"], 180)

    def test_magnakai_temporary_unarmed_and_de_weaponskill_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"].update({"BookNumber": 6, "WeaponskillWeapon": "Sword"})
            assistant.state.setdefault("Conditions", {})["BookSixDEWeaponskillOption"] = 1
            assistant.state["Inventory"]["Weapons"] = ["Sword"]
            assistant.start_combat(["combat", "start", "Test", "10", "10"])
            modifier, notes = assistant.combat_weapon_modifier_and_notes()
            self.assertEqual(modifier, 2)
            self.assertIn("Weaponskill (Sword): +2 CS", notes)

            assistant.state["Character"]["BookNumber"] = 7
            assistant.set_section(219)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_active_weapon(), "")
            assistant.combat["Log"] = [{"Round": 1}, {"Round": 2}]

        self.assertEqual(assistant.combat_active_weapon(), "Sword")

    def test_book6_tournament_uses_target_points_without_harming_endurance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"].update({"BookNumber": 6, "EnduranceCurrent": 17, "EnduranceMax": 20})
            assistant.state["Automation"]["Flags"]["book6KalteBowPenalty"] = True
            assistant.set_section(26)
            assistant.start_section_combat()
            self.assertEqual(assistant.combat_active_weapon(), "Bow")
            self.assertTrue(assistant.combat["UsePlayerTargetEndurance"])
            self.assertEqual(assistant.combat["PlayerTargetEnduranceCurrent"], 50)
            self.assertEqual(assistant.combat["Modifier"], -4)

            assistant.combat["PlayerTargetEnduranceCurrent"] = 0
            assistant.combat["Log"] = [{"Round": 1, "PlayerLoss": 50, "EnemyLoss": 0}]
            self.assertTrue(assistant.route_after_combat_round())

        self.assertEqual(assistant.state["CurrentSection"], 183)
        self.assertEqual(assistant.character["EnduranceCurrent"], 17)

    def test_book6_de_curing_options_control_healing_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state", books_dir=base / "books",
            )
            assistant.state["Character"].update({"BookNumber": 6, "MagnakaiDisciplines": ["Curing"]})
            assistant.state["CurrentBookStats"] = {}
            assistant.state.setdefault("Conditions", {})["BookSixDECuringOption"] = 1
            amount, note = assistant.apply_healing_cap(16)
            self.assertEqual(amount, 15)
            self.assertIn("Curing cap", note)

            assistant.state["Character"]["MagnakaiDisciplines"] = []
            assistant.state["Character"]["KaiDisciplines"] = ["Healing"]
            assistant.state["Conditions"]["BookSixDECuringOption"] = 0
            self.assertFalse(assistant.current_healing_payload()["Available"])

            assistant.state["Conditions"]["BookSixDECuringOption"] = 2
            healing = assistant.current_healing_payload()
            self.assertTrue(healing["Available"])
            self.assertIn("Healing restores 1 END", healing["Summary"])


class CampaignEntryPointTests(unittest.TestCase):
    @staticmethod
    def source_text(name: str) -> str:
        root = Path(saa_main.__file__).resolve().parent
        return (root / name).read_text(encoding="utf-8")

    def test_home_page_exposes_book_one_campaign_entries(self) -> None:
        index_html = self.source_text("index.html")
        self.assertIn('assistant.html?campaign=new&amp;book=1', index_html)
        self.assertIn('assistant.html?campaign=new&book=1', index_html)
        self.assertIn('campaignStartLink = book.number === 1', index_html)

    def test_books_six_to_twelve_are_exposed_as_playable_testing_books(self) -> None:
        index_html = self.source_text("index.html")
        library_html = self.source_text("library.html")
        assistant_html = self.source_text("assistant.html")
        self.assertIn("testingBook(6, 'The Kingdoms of Terror'", index_html)
        self.assertIn("testingBook(7, 'Castle of Death'", index_html)
        self.assertIn("testingBook(8, 'The Jungle of Horrors'", index_html)
        self.assertIn("testingBook(9, 'The Cauldron of Fear'", index_html)
        self.assertIn("testingBook(12, 'The Masters of Darkness'", index_html)
        self.assertIn("Playable testing build", index_html)
        self.assertIn("Open Test Reader", index_html)
        self.assertIn('assistant.html?browse=1&amp;book=6', library_html)
        self.assertIn('assistant.html?browse=1&amp;book=7', library_html)
        self.assertIn('assistant.html?browse=1&amp;book=8', library_html)
        self.assertIn('assistant.html?browse=1&amp;book=9', library_html)
        self.assertIn('assistant.html?browse=1&amp;book=12', library_html)
        self.assertIn('data-book="6">Book 6</button>', assistant_html)
        self.assertIn('data-book="7">Book 7</button>', assistant_html)
        self.assertIn('data-book="8">Book 8</button>', assistant_html)
        self.assertIn('data-book="9">Book 9</button>', assistant_html)
        self.assertIn('data-book="12">Book 12</button>', assistant_html)

    def test_reader_toolbar_switches_to_the_active_series(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn('data-reader-series="kai"', assistant_html)
        self.assertIn('data-reader-series="magnakai"', assistant_html)
        self.assertIn('data-reader-series="grand-master"', assistant_html)
        self.assertIn('data-reader-series="new-order"', assistant_html)
        self.assertNotIn('Book 8 is not in testing yet.', assistant_html)
        self.assertNotIn('Book 9 is not in testing yet.', assistant_html)
        self.assertNotIn('Book 12 is not in testing yet.', assistant_html)
        self.assertIn("? 'new-order'", assistant_html)
        self.assertIn("? 'grand-master'", assistant_html)

    def test_magnakai_sheet_leads_with_the_current_discipline_set(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn("const isMagnakai = Number(c.BookNumber) >= 6;", assistant_html)
        self.assertIn("powerPanel('Magnakai Disciplines', magnakaiDisciplines, magnakaiKnown)", assistant_html)
        self.assertIn("powerPanel(isMagnakai ? 'Kai Disciplines (Legacy)' : 'Kai Disciplines'", assistant_html)
        self.assertLess(
            assistant_html.index("powerPanel('Magnakai Disciplines', magnakaiDisciplines, magnakaiKnown)"),
            assistant_html.index("powerPanel(isMagnakai ? 'Kai Disciplines (Legacy)' : 'Kai Disciplines'")
        )

    def test_home_current_section_uses_live_state_and_only_resumes(self) -> None:
        index_html = self.source_text("index.html")
        self.assertIn("fetch('/api/state?ts=' + Date.now()", index_html)
        self.assertIn("window.location.href = 'assistant.html?surface=campaign&resume=1';", index_html)
        self.assertNotIn('assistant.html?book=${book.number}&section=${section}', index_html)

    def test_assistant_honors_campaign_start_without_mutating_until_begin(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn("pageParams.get('campaign') === 'new'", assistant_html)
        self.assertIn('function shouldShowBook1Creation()', assistant_html)
        self.assertIn('function confirmCampaignReplacement()', assistant_html)
        self.assertIn('clearCampaignStartRequest();', assistant_html)

    def test_active_game_modes_are_visible_and_editable_during_play(self) -> None:
        assistant_html = self.source_text("assistant.html")
        server_source = self.source_text("app_server.py")
        self.assertIn('<div class="quick-title">Game Modes</div>', assistant_html)
        self.assertIn('id="runConfigurationForm"', assistant_html)
        self.assertIn("action: 'set_run_configuration'", assistant_html)
        self.assertIn('if action == "set_run_configuration":', server_source)

    def test_book6_optional_rules_explain_their_effects(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn("Optional Book 6 rules carried over from the original assistant.", assistant_html)
        self.assertIn("Curing cap limits Curing and Healing to 15 END restored in Book 6.", assistant_html)
        self.assertIn("lets you drink a potion instead of attacking in combat", assistant_html)
        self.assertIn("gain +2 Combat Skill in Book 6", assistant_html)
        self.assertIn("function syncBook6HerbPouchChoice", assistant_html)
        self.assertIn("Herb Pouch requires the Herb Pouch Curing Option", assistant_html)
        self.assertIn("function syncBook6SetupRequirements", assistant_html)
        self.assertIn("data-book6-exchange-status", assistant_html)
        self.assertIn("Choose ${requiredExchanges} Weapon Exchange", assistant_html)

    def test_campaign_entry_keeps_setup_visible_and_protects_existing_campaigns(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn("const cliActive = isCliMode() && !campaignStartRequested;", assistant_html)
        self.assertIn("if (isNativeSurface) {", assistant_html)
        self.assertIn("renderNativeSurface({", assistant_html)
        self.assertIn('data-campaign-cancel', assistant_html)
        self.assertIn("const campaignEntry = campaignStartRequested && card.dataset.campaignEntry === 'true';", assistant_html)
        self.assertGreaterEqual(assistant_html.count('if (!confirmCampaignReplacement()) return;'), 3)

        cancel_start = assistant_html.index('if (button.dataset.creationCancel !== undefined)')
        cancel_end = assistant_html.index('if (button.dataset.campaignCancel !== undefined)', cancel_start)
        self.assertNotIn('clearCampaignStartRequest', assistant_html[cancel_start:cancel_end])

    def test_completion_ui_contains_magnakai_campaign_handoffs(self) -> None:
        assistant_html = self.source_text("assistant.html")
        server_source = self.source_text("app_server.py")
        self.assertIn("nextBook >= 22 && nextBook <= 29", assistant_html)
        self.assertIn("Choose exactly 3 Magnakai Disciplines", assistant_html)
        self.assertIn("Grand Master Discipline", assistant_html)
        self.assertIn("New New Order Discipline", assistant_html)
        self.assertIn("New Magnakai Discipline", assistant_html)
        self.assertIn("Continue to Book ${escapeHtml(nextBook)}", assistant_html)
        self.assertIn("Leave Behind Before Field Issue", assistant_html)
        self.assertIn("transitionDrops: formData.getAll('transitionDrops')", assistant_html)
        self.assertIn("transition_drops=payload.get(\"transitionDrops\")", server_source)

    def test_cli_new_creates_a_fresh_book6_magnakai_campaign(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            responses = [
                "", "n", "",  # Normal, no permadeath, automatic CRT
                "6", "CLI Six",
                "3", "3", "8",  # Curing, Invisibility, Nexus
                "0", "0",  # Book 6 DE options
                "1", "1", "2", "3", "4", "6", "6",
            ]
            with mock.patch("builtins.input", side_effect=responses), \
                 mock.patch.object(assistant, "write_current_position"), \
                 mock.patch.object(assistant, "show_sheet"), \
                 redirect_stdout(io.StringIO()):
                assistant.start_new_game()

        self.assertEqual(assistant.character["Name"], "CLI Six")
        self.assertEqual(assistant.character["BookNumber"], 6)
        self.assertEqual(assistant.character["MagnakaiRank"], 3)
        self.assertIn("Map of the Stornlands", assistant.inventory["SpecialItems"])
        self.assertEqual(len(assistant.character["Book6Setup"]["EquipmentChoices"]), 7)


class RunFeatureParityTests(unittest.TestCase):
    def assistant(self, temp_dir: str) -> lonewolf_redux.LoneWolfReduxAssistant:
        base = Path(temp_dir)
        return lonewolf_redux.LoneWolfReduxAssistant(
            save_dir=base / "saves",
            data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data",
            state_data_dir=base / "state",
            books_dir=base / "books",
        )

    def test_v1_run_metadata_migrates_without_claiming_to_validate_its_signature(self) -> None:
        migrated = lonewolf_redux.normalize_state({
            "Run": {
                "Id": "v1-run",
                "Difficulty": "Hard",
                "Permadeath": True,
                "IntegrityState": "Clean",
                "Signature": "v1-signature",
            },
            "Settings": {"CombatMode": "ManualCRT"},
        })
        run = migrated["Run"]
        self.assertEqual(run["Difficulty"], "Hard")
        self.assertTrue(run["Permadeath"])
        self.assertEqual(run["CombatMode"], "ManualCRT")
        self.assertEqual(run["LegacySignature"], "v1-signature")
        self.assertEqual(run["SignatureVersion"], lonewolf_redux.RUN_SIGNATURE_VERSION)
        self.assertEqual(run["Signature"], "")

    def test_difficulty_rules_cover_loss_healing_and_book_transition(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.set_run_configuration("Story", True, "DataFile")
            self.assertFalse(assistant.permadeath_enabled())
            self.assertIn("Story", assistant.change_endurance(-5))
            self.assertEqual(assistant.character["EnduranceCurrent"], 20)

            assistant.set_run_configuration("Easy", False, "DataFile")
            assistant.change_endurance(-5)
            self.assertEqual(assistant.character["EnduranceCurrent"], 17)
            self.assertEqual(assistant.restore_endurance_for_book_transition(), "Easy mode restored END 17->20 for the next book.")

            assistant.set_run_configuration("Hard", False, "DataFile")
            self.assertEqual(assistant.apply_healing_cap(11), (10, "Healing is capped at 10 END per book in this difficulty."))
            self.assertEqual(assistant.apply_healing_cap(1), (0, "Healing is capped at 10 END per book in this difficulty."))

    def test_in_place_game_mode_changes_preserve_the_active_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.set_run_configuration("Normal", False, "DataFile")
            run_id = assistant.run_state["Id"]
            started_on = assistant.run_state["StartedOn"]

            assistant.update_run_configuration("Hard", True, "ManualCRT")
            self.assertEqual(assistant.run_state["Id"], run_id)
            self.assertEqual(assistant.run_state["StartedOn"], started_on)
            self.assertEqual(assistant.difficulty(), "Hard")
            self.assertTrue(assistant.permadeath_enabled())
            self.assertEqual(assistant.combat_mode(), "ManualCRT")

            assistant.update_run_configuration("Story", True)
            self.assertFalse(assistant.permadeath_enabled())

    def test_permadeath_and_achievement_gates_are_enforced(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.set_run_configuration("Hard", True, "DataFile")
            assistant.save_section_checkpoint("ready")
            assistant.register_death("instant", "fixture")
            self.assertEqual(assistant.run_state["Status"], "Dead")
            self.assertFalse(assistant.death_recovery_payload()["CanRepeat"])
            with redirect_stdout(io.StringIO()):
                assistant.restore_death_checkpoint("repeat")
            self.assertTrue(assistant.death_active())

            assistant.set_run_configuration("Story", False, "DataFile")
            combat_definition = next(item for item in lonewolf_redux.LONE_WOLF_ACHIEVEMENTS if item["Id"] == "lw1_first_blood")
            self.assertFalse(assistant.achievement_available(combat_definition)[0])
            assistant.set_run_configuration("Hard", True, "DataFile")
            challenge_definition = next(item for item in lonewolf_redux.LONE_WOLF_ACHIEVEMENTS if item["Id"] == "only_one_life")
            self.assertTrue(assistant.achievement_available(challenge_definition)[0])

    def test_signed_run_detects_edits_and_manual_crt_records_player_result(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.set_run_configuration("Normal", False, "ManualCRT")
            path = Path(temp_dir) / "run.json"
            assistant.save_game(str(path), quiet=True)
            saved = json.loads(path.read_text(encoding="utf-8"))
            saved["Inventory"]["GoldCrowns"] = 49
            path.write_text(json.dumps(saved), encoding="utf-8")
            self.assertTrue(assistant.load_game(str(path), quiet=True))
            self.assertEqual(assistant.run_state["IntegrityState"], "Tampered")

            assistant.start_combat(["combat", "start", "Test", "10", "10"])
            with redirect_stdout(io.StringIO()):
                assistant.combat_round(["combat", "manual"], manual_losses=(3, 2))
            round_entry = assistant.combat["Log"][-1]
            self.assertEqual(round_entry["CRTColumn"], "Manual")
            self.assertEqual(round_entry["EnemyLoss"], 3)
            self.assertEqual(round_entry["PlayerLoss"], 2)

    def test_sommerswerd_rules_follow_hard_and_veteran_requirements(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.inventory["SpecialItems"] = ["Sommerswerd"]
            assistant.start_combat(["combat", "start", "Test", "10", "10"])
            assistant.set_combat_weapon("Sommerswerd", save=False)
            assistant.set_run_configuration("Hard", False, "DataFile")
            modifier, _ = assistant.combat_weapon_modifier_and_notes()
            self.assertEqual(modifier, 4)
            assistant.set_run_configuration("Veteran", False, "DataFile")
            modifier, notes = assistant.combat_weapon_modifier_and_notes()
            self.assertEqual(modifier, 0)
            self.assertIn("Veteran: Sommerswerd power needs text permission", notes)
            assistant.combat["SommerswerdAllowed"] = True
            modifier, _ = assistant.combat_weapon_modifier_and_notes()
            self.assertEqual(modifier, 4)

    def test_next_book_opens_before_setup_and_temporary_gear_does_not_cross_the_boundary(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.ensure_book_completed(1)
            self.assertEqual(assistant.open_next_book(), 2)
            self.assertEqual(assistant.character["BookNumber"], 1)
            self.assertTrue(assistant.pending_book_setup_payload()["Active"])
            self.assertEqual(assistant.pending_book_setup_payload()["NextBookNumber"], 2)

            state = lonewolf_redux.normalize_state({
                "Character": {"BookNumber": 5},
                "Inventory": {"Weapons": [], "BackpackItems": [], "SpecialItems": []},
                "Automation": {
                    "Flags": {"weaponsAvailable": False, "backpackAvailable": False, "backpackItemsAvailable": False},
                    "Stored": {"confiscatedEquipment": {"Weapons": ["Sword"], "BackpackItems": ["Rope"]}},
                },
            })
            prepared = lonewolf_redux.prepare_book6_state(
                state,
                magnakai_disciplines=["Curing", "Nexus", "Weaponmastery"],
                weaponmastery_weapons=["Sword", "Axe", "Bow"],
                equipment_choices=["sword", "warhammer", "laumspur", "tinderbox", "kai-shield", "helmet", "torch"],
            )
            self.assertEqual(prepared["Automation"]["Stored"], {})
            self.assertTrue(prepared["Automation"]["Flags"]["weaponsAvailable"])
            self.assertTrue(prepared["Automation"]["Flags"]["backpackAvailable"])
            self.assertNotIn("Rope", prepared["Inventory"]["BackpackItems"])

            state["Inventory"]["Weapons"] = ["Sword", "Warhammer"]
            state["Automation"]["Flags"]["weaponsAvailable"] = True
            with self.assertRaisesRegex(ValueError, "Taking Bow needs a Weapon exchange"):
                lonewolf_redux.prepare_book6_state(
                    state,
                    magnakai_disciplines=["Curing", "Nexus", "Weaponmastery"],
                    weaponmastery_weapons=["Sword", "Axe", "Bow"],
                    equipment_choices=["bow"],
                )

            with self.assertRaisesRegex(ValueError, "Herb Pouch requires DE Curing option 3"):
                lonewolf_redux.prepare_book6_state(
                    state,
                    magnakai_disciplines=["Curing", "Nexus", "Weaponmastery"],
                    weaponmastery_weapons=["Sword", "Axe", "Bow"],
                    equipment_choices=["sword", "warhammer", "laumspur", "tinderbox", "kai-shield", "helmet", "herb-pouch"],
                )

    def test_inventory_order_is_saved_and_sommerswerd_is_the_first_combat_weapon(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.inventory["Weapons"] = ["Axe", "Sword"]
            assistant.inventory["SpecialItems"] = ["Shield", "Sommerswerd"]
            with redirect_stdout(io.StringIO()):
                self.assertTrue(assistant.reorder_inventory("weapon", 1, 0))
            self.assertEqual(assistant.inventory["Weapons"], ["Sword", "Axe"])
            self.assertEqual(assistant.available_combat_weapons()[0], "Sommerswerd")


class CardSizingTests(unittest.TestCase):
    def test_dashboard_card_sizes_have_distinct_widths(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        assistant_html = (root / "assistant.html").read_text(encoding="utf-8")

        self.assertIn("#view.view-card-grid > .dashboard-card.card-size-small", assistant_html)
        self.assertIn("flex: 0 1 220px;", assistant_html)
        self.assertIn("max-width: 220px;", assistant_html)
        self.assertIn("min-height: 150px;", assistant_html)
        self.assertIn(
            ".quick-panel > .dashboard-card.card-size-small .quick-drop-list",
            assistant_html,
        )
        self.assertIn("overflow-x: hidden;", assistant_html)
        self.assertIn(
            ".quick-panel > .dashboard-card.card-size-small .quick-drop-list .item-row",
            assistant_html,
        )
        self.assertIn("flex-wrap: wrap;", assistant_html)
        self.assertIn("#view.view-card-grid > .dashboard-card.card-size-medium", assistant_html)
        self.assertIn("flex: 0 0 calc(50% - 0.325rem);", assistant_html)
        self.assertIn('class="stat-adjust-line"', assistant_html)
        self.assertIn('class="stat-set-line"', assistant_html)
        self.assertIn("options.resizable === false", assistant_html)
        self.assertIn("resizable: false", assistant_html)


class UiPreferencePersistenceTests(unittest.TestCase):
    def test_card_dimensions_are_allowlisted_and_round_trip(self) -> None:
        dimensions_key = "lonewolf_redux.cards.dimensions.view-sheet"
        dimensions = {
            "action-chart": {"width": 480, "height": 260},
            "choices": {"width": 320, "height": 180},
        }
        rejected_key = "lonewolf_redux.cards.unapproved.view-sheet"

        self.assertIn("lonewolf_redux.cards.dimensions.", app_server.UI_PREFERENCE_PREFIXES)
        self.assertTrue(app_server.is_ui_preference_key(dimensions_key))
        self.assertFalse(app_server.is_ui_preference_key(rejected_key))

        with tempfile.TemporaryDirectory() as temp_dir:
            preferences_file = Path(temp_dir) / "ui-preferences.json"
            payload = {
                "version": 1,
                "values": {
                    dimensions_key: json.dumps(dimensions),
                    rejected_key: "must not persist",
                },
            }
            with mock.patch.object(app_server, "UI_PREFERENCES_FILE", preferences_file):
                saved = app_server.save_ui_preferences(payload)
                loaded = app_server.load_ui_preferences()

        self.assertEqual(saved, loaded)
        self.assertNotIn(rejected_key, loaded["values"])
        self.assertEqual(
            json.loads(loaded["values"][dimensions_key]),
            dimensions,
        )


class CardLayoutInteractionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(saa_main.__file__).resolve().parent
        cls.assistant_html = (cls.root / "assistant.html").read_text(encoding="utf-8")

    @classmethod
    def function_source(cls, name: str) -> str:
        match = re.search(
            rf"(?:async\s+)?function\s+{re.escape(name)}\b",
            cls.assistant_html,
        )
        if not match:
            raise AssertionError(f"JavaScript function {name!r} was not found")

        parameters_start = cls.assistant_html.find("(", match.end())
        if parameters_start < 0:
            raise AssertionError(f"JavaScript function {name!r} has no parameter list")
        parameter_depth = 0
        quote = ""
        escaped = False
        parameters_end = -1
        for index in range(parameters_start, len(cls.assistant_html)):
            character = cls.assistant_html[index]
            if quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = ""
                continue
            if character in {"'", '"', "`"}:
                quote = character
            elif character == "(":
                parameter_depth += 1
            elif character == ")":
                parameter_depth -= 1
                if parameter_depth == 0:
                    parameters_end = index
                    break
        if parameters_end < 0:
            raise AssertionError(f"JavaScript function {name!r} has no closing parenthesis")

        start = cls.assistant_html.find("{", parameters_end)
        depth = 0
        quote = ""
        escaped = False
        for index in range(start, len(cls.assistant_html)):
            character = cls.assistant_html[index]
            if quote:
                if escaped:
                    escaped = False
                elif character == "\\":
                    escaped = True
                elif character == quote:
                    quote = ""
                continue
            if character in {"'", '"', "`"}:
                quote = character
            elif character == "{":
                depth += 1
            elif character == "}":
                depth -= 1
                if depth == 0:
                    return cls.assistant_html[match.start():index + 1]
        raise AssertionError(f"JavaScript function {name!r} has no closing brace")

    def test_release_metadata_is_3_7_0_internal_testing(self) -> None:
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        building = (self.root / "docs" / "BUILDING.md").read_text(encoding="utf-8")
        user_guide = (self.root / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")
        changelog = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        installer = (
            self.root / "installer" / "LoneWolf_ActionAssistant.iss"
        ).read_text(encoding="utf-8")
        version_info = (self.root / "version_info.txt").read_text(encoding="utf-8")

        self.assertIn("# Lone Wolf Action Assistant 3.7.0 Internal Testing", readme)
        self.assertIn("Version: **3.7.0 Internal Testing**", readme)
        self.assertIn("# Building Lone Wolf Action Assistant 3.7.0 Internal Testing", building)
        self.assertIn("# Lone Wolf Action Assistant 3.7.0 Internal Testing", user_guide)
        self.assertIn("## 3.7.0 - Internal Testing", changelog)
        self.assertIn('#define AppVersion "3.7.0"', installer)
        self.assertIn("filevers=(3, 7, 0, 0)", version_info)
        self.assertIn("prodvers=(3, 7, 0, 0)", version_info)
        self.assertIn("StringStruct(u'FileVersion', u'3.7.0')", version_info)
        self.assertIn("StringStruct(u'ProductVersion', u'3.7.0')", version_info)

    def test_movable_cards_get_a_dedicated_drag_handle(self) -> None:
        self.assertIn("data-card-drag-handle", self.assistant_html)
        self.assertIn(".card-drag-handle", self.assistant_html)
        self.assertRegex(
            self.assistant_html,
            r"<button\b[^>]*\bdata-card-drag-handle\b",
        )

    def test_tabs_are_collapse_only_and_have_no_card_menu(self) -> None:
        decorate_interface = self.function_source("decorateInterfaceCards")
        match = re.search(
            r"decorateCards\(\s*['\"]tabs['\"]\s*,[\s\S]*?,\s*\{(?P<options>[\s\S]*?)\}\s*\)",
            decorate_interface,
        )
        self.assertIsNotNone(match, "tabs must be decorated with explicit options")
        options = match.group("options")
        for option in ("movable", "resizable", "closeable", "menu"):
            self.assertRegex(options, rf"\b{option}\s*:\s*false\b")

    def test_legacy_native_html_drag_system_is_removed(self) -> None:
        self.assertNotIn('draggable="true"', self.assistant_html)
        self.assertNotRegex(
            self.assistant_html,
            r"addEventListener\(\s*['\"](?:dragstart|dragover|drop|dragend)['\"]",
        )

    def test_pointer_drag_has_commit_and_cancel_paths(self) -> None:
        for event_name in ("pointerdown", "pointermove", "pointerup", "pointercancel"):
            self.assertRegex(
                self.assistant_html,
                rf"addEventListener\(\s*['\"]{event_name}['\"]",
            )
        self.assertIn("setPointerCapture", self.assistant_html)
        self.assertRegex(
            self.assistant_html,
            r"addEventListener\(\s*['\"]pointercancel['\"][\s\S]{0,240}"
            r"(?:cancel|clear|finish|end)[A-Za-z0-9_$]*CardDrag",
        )
        self.assertRegex(
            self.assistant_html,
            r"(?:event\.key|key)\s*(?:={2,3}|!={1,2})\s*['\"]Escape['\"][\s\S]{0,180}"
            r"(?:cancel|clear|finish|end)[A-Za-z0-9_$]*CardDrag",
        )

    def test_pointer_drop_requires_same_parent_and_scope(self) -> None:
        functions = [
            self.function_source("cardDragTargetAtPoint"),
            self.function_source("completeCardDrag"),
        ]
        boundary_functions = [
            source
            for source in functions
            if (
                re.search(
                    r"(?:source|dragged)\.parentElement\s*={2,3}\s*target\.parentElement"
                    r"|target\.parentElement\s*={2,3}\s*(?:source|dragged)\.parentElement",
                    source,
                )
                or len(re.findall(r"(?:source|target)\.parentElement\s*={2,3}\s*state\.parent", source)) >= 2
                or (
                    "state.source.parentElement === state.parent" in source
                    and "drop.target.parentElement === state.parent" in source
                )
            )
            and (
                re.search(
                    r"(?:source|dragged)\.dataset\.cardScope\s*={2,3}\s*target\.dataset\.cardScope"
                    r"|target\.dataset\.cardScope\s*={2,3}\s*(?:source|dragged)\.dataset\.cardScope",
                    source,
                )
                or "drop.target.dataset.cardScope === state.scope" in source
                or "target.dataset.cardScope === state.scope" in source
            )
        ]
        self.assertTrue(
            boundary_functions,
            "a card-drop boundary helper must require the same direct parent and card scope",
        )

    def test_move_card_uses_direct_same_parent_siblings(self) -> None:
        move_card = self.function_source("moveCard")
        self.assertRegex(
            move_card,
            r"(?:parentElement|\.children|:scope\s*>)",
        )
        self.assertRegex(move_card, r"(?:direct[A-Za-z0-9_$]*Cards|cardsForContainer)\s*\(")

        direct_helper = self.function_source("directScopedCards")
        self.assertRegex(direct_helper, r"\.children\b|querySelectorAll\(\s*['\"]:scope\s*>")
        self.assertIn("cardScope", direct_helper)

    def test_non_closeable_tabs_ignore_legacy_closed_state(self) -> None:
        decorate_cards = self.function_source("decorateCards")
        hidden_assignment = re.search(r"card\.hidden\s*=\s*(?P<value>[^;]+);", decorate_cards)
        self.assertIsNotNone(hidden_assignment)
        self.assertRegex(
            hidden_assignment.group("value"),
            r"closeable|options\.closeable",
        )
        self.assertIn("closed.has(id)", hidden_assignment.group("value"))

    def test_persisted_layout_keeps_all_direct_siblings_including_hidden_cards(self) -> None:
        direct_helper = self.function_source("directScopedCards")
        persistence = self.function_source("persistDirectCardOrder")
        merge = self.function_source("mergedCardLayout")

        self.assertRegex(direct_helper, r"\.children\b|querySelectorAll\(\s*['\"]:scope\s*>")
        self.assertNotRegex(
            direct_helper,
            r":not\(\[hidden\]\)|!\s*\w+\.hidden|\.hidden\s*={2,3}\s*false",
        )
        self.assertIn("directScopedCards(parent, scope)", persistence)
        self.assertIn("setCardLayout(scope, mergedCardLayout(scope, ids))", persistence)
        self.assertIn("getCardLayout(scope)", merge)
        self.assertRegex(merge, r"currentSet\.has\(id\)\s*\?[\s\S]*:\s*id")

    def test_free_resize_contract_exposes_custom_auto_and_a_dedicated_handle(self) -> None:
        self.assertIn("cardDimensionsPrefix", self.assistant_html)
        self.assertIn("lonewolf_redux.cards.dimensions.", self.assistant_html)
        self.assertIn(".card-resize-handle", self.assistant_html)
        self.assertRegex(
            self.assistant_html,
            r"<button\b[^>]*\bdata-card-resize-handle\b",
        )
        self.assertRegex(
            self.assistant_html,
            r"(?:data-card-resizable|dataset\.cardResizable)",
        )
        self.assertIn(".card-size-auto", self.assistant_html)
        self.assertIn(".card-size-custom", self.assistant_html)

    def test_card_dimension_helpers_use_per_scope_ui_preferences(self) -> None:
        get_dimensions = self.function_source("getCardDimensions")
        get_dimension = self.function_source("getCardDimension")
        set_dimensions = self.function_source("setCardDimensions")
        clear_dimensions = self.function_source("clearCardDimensions")

        helper_source = "\n".join(
            (get_dimensions, get_dimension, set_dimensions, clear_dimensions)
        )
        self.assertIn("cardDimensionsPrefix", helper_source)
        self.assertRegex(
            helper_source,
            r"cardStorageKey\(\s*cardDimensionsPrefix\s*,\s*scope\s*\)",
        )
        self.assertIn("setJsonStorage", set_dimensions)
        self.assertRegex(get_dimension, r"\bwidth\b")
        self.assertRegex(get_dimension, r"\bheight\b")
        self.assertRegex(clear_dimensions, r"\bdelete\b")

        reset_scope = self.function_source("resetCardScope")
        reset_all = self.function_source("resetAllCardLayouts")
        self.assertIn("cardDimensionsPrefix", reset_scope)
        self.assertIn("cardDimensionsPrefix", reset_all)

    def test_presets_and_auto_clear_custom_card_dimensions(self) -> None:
        get_size = self.function_source("getCardSize")
        set_size = self.function_source("setCardSize")

        self.assertRegex(get_size, r"['\"]auto['\"]")
        self.assertRegex(set_size, r"['\"]auto['\"]")
        self.assertIn("clearCardDimensions", set_size)
        for preset in ("small", "medium", "large"):
            self.assertRegex(set_size, rf"['\"]{preset}['\"]")

    def test_pointer_resize_has_live_commit_and_every_cancel_path(self) -> None:
        start_resize = self.function_source("startCardResize")
        update_resize = self.function_source("updateCardResize")
        complete_resize = self.function_source("completeCardResize")
        cancel_resize = self.function_source("cancelCardResize")
        render = self.function_source("render")

        self.assertIn("cardResizeState", self.assistant_html)
        self.assertIn("setPointerCapture", start_resize)
        self.assertRegex(update_resize, r"\bwidth\b")
        self.assertRegex(update_resize, r"\bheight\b")
        self.assertNotIn("setCardDimensions", update_resize)
        self.assertIn("setCardDimensions", complete_resize)
        self.assertNotIn("setCardDimensions", cancel_resize)
        self.assertIn("cancelCardResize", render)

        for event_name in ("pointerdown", "pointermove", "pointerup", "pointercancel"):
            self.assertRegex(
                self.assistant_html,
                rf"addEventListener\(\s*['\"]{event_name}['\"]",
            )
        self.assertRegex(
            self.assistant_html,
            r"addEventListener\(\s*['\"]blur['\"][\s\S]*?cancelCardResize",
        )
        self.assertRegex(
            self.assistant_html,
            r"addEventListener\(\s*['\"]visibilitychange['\"][\s\S]*?cancelCardResize",
        )
        self.assertRegex(
            self.assistant_html,
            r"(?:event\.key|key)\s*(?:={2,3}|!={1,2})\s*['\"]Escape['\"]"
            r"[\s\S]*?cancelCardResize",
        )

    def test_resize_eligibility_keeps_static_and_campaign_cards_protected(self) -> None:
        decorate_cards = self.function_source("decorateCards")
        decorate_interface = self.function_source("decorateInterfaceCards")

        self.assertIn("options.resizable", decorate_cards)
        self.assertIn("campaignEntry", decorate_cards)
        self.assertRegex(
            decorate_cards,
            r"(?:dataset\.cardResizable|data-card-resizable)",
        )
        self.assertIn("data-card-resize-handle", self.assistant_html)

        tabs_match = re.search(
            r"decorateCards\(\s*['\"]tabs['\"]\s*,[\s\S]*?,\s*"
            r"\{(?P<options>[\s\S]*?)\}\s*\)",
            decorate_interface,
        )
        self.assertIsNotNone(tabs_match)
        self.assertRegex(
            tabs_match.group("options"),
            r"\bresizable\s*:\s*false\b",
        )

    def test_dynamic_cards_keep_stable_dimension_ids(self) -> None:
        self.assertIn('data-card-id="combat-controls"', self.assistant_html)
        self.assertIn('data-card-id="death-outcome"', self.assistant_html)

    def test_auto_size_is_content_driven_and_tall_quick_cards_remain_reorderable(self) -> None:
        self.assertRegex(
            self.assistant_html,
            r"\.dashboard-card\.card-size-auto\s*\{[^}]*"
            r"flex\s*:\s*0\s+1\s+auto[^}]*width\s*:\s*fit-content",
        )
        auto_scroll = self.function_source("autoScrollCardDrag")
        self.assertIn("quickPanel", auto_scroll)
        self.assertIn("scroller.scrollBy", auto_scroll)


class LibraryProductionTests(unittest.TestCase):
    def test_library_uses_the_campaign_command_layout(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        index_html = (root / "index.html").read_text(encoding="utf-8")

        self.assertIn('href="assets/css/lw-library.css"', index_html)
        self.assertIn("Stand Alone Application", index_html)
        self.assertIn('class="library-hero__mark"', index_html)
        self.assertIn('assets/images/lone-wolf-title-banner.png', index_html)
        self.assertIn('id="currentBtn"', index_html)
        self.assertIn("Start Current Campaign", index_html)
        self.assertIn('id="seriesTabs"', index_html)
        self.assertIn('data-library-series-panel="magnakai"', index_html)
        self.assertIn("function renderCurrentCampaign(position)", index_html)
        self.assertIn("function selectLibrarySeries(series)", index_html)
        self.assertIn("lonewolf:campaign-state", index_html)
        self.assertIn("set_library_book_read", index_html)
        self.assertIn("loadCampaignReadStatus", index_html)
        self.assertTrue((root / "assets" / "css" / "lw-library.css").is_file())

    def test_paper_theme_is_available_before_and_after_runtime_settings_load(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        settings_js = (root / "assets" / "js" / "lw-settings.js").read_text(encoding="utf-8")
        early_appearance_js = (root / "assets" / "js" / "lw-appearance-early.js").read_text(encoding="utf-8")

        self.assertIn("id: 'paper'", settings_js)
        self.assertIn("name: 'Paper'", settings_js)
        self.assertIn("'paper': {", early_appearance_js)
        self.assertIn("'--lw-reader-page': '#f3eddd'", settings_js)
        self.assertIn("if (clean.theme === 'paper')", settings_js)
        campaign_css = (root / "assets" / "css" / "lw-campaign.css").read_text(encoding="utf-8")
        self.assertIn(".lw-story-panel .story-prose { max-width: 700px; color: var(--lw-ui-ink);", campaign_css)

    def test_library_read_marks_are_saved_with_the_campaign(self) -> None:
        root = Path(lonewolf_redux.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=root / "data", state_data_dir=base / "state", books_dir=base / "books"
            )
            with redirect_stdout(io.StringIO()):
                assistant.set_library_book_read(6, True)
            self.assertEqual(assistant.state["LibraryReadBooks"], [6])
            path = base / "save.json"
            assistant.save_game(str(path), quiet=True)

            loaded = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "other-saves", data_dir=root / "data", state_data_dir=base / "other-state", books_dir=base / "books"
            )
            self.assertTrue(loaded.load_game(str(path), quiet=True))
            self.assertEqual(loaded.state["LibraryReadBooks"], [6])

        normalized = lonewolf_redux.normalize_state({"LibraryReadBooks": [6, "6", 0, 99, "bad"]})
        self.assertEqual(normalized["LibraryReadBooks"], [6])


class RecoveryTimelineTests(unittest.TestCase):
    def test_book6_terminal_loop_recovers_to_the_last_real_decision(self) -> None:
        root = Path(lonewolf_redux.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            book_dir = base / "books" / "06tkot"
            book_dir.mkdir(parents=True)
            (book_dir / "sect146.htm").write_text(
                "<p class='choice'>Ride to Amory. <a href='sect96.htm'>Turn to 96</a>.</p>"
                "<p class='choice'>Head for Soren. <a href='sect247.htm'>Turn to 247</a>.</p>",
                encoding="utf-8",
            )
            (book_dir / "sect96.htm").write_text(
                "<p class='choice'>If you possess a Cess, <a href='sect49.htm'>turn to 49</a>.</p>"
                "<p class='choice'>If you do not possess this Special Item, <a href='sect221.htm'>turn to 221</a>.</p>",
                encoding="utf-8",
            )
            (book_dir / "sect49.htm").write_text(
                "<p class='choice'><a href='sect129.htm'>Turn to 129</a>.</p>", encoding="utf-8"
            )
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves", data_dir=root / "data", state_data_dir=base / "state", books_dir=base / "books"
            )
            assistant.state["RuleSet"] = "Magnakai"
            assistant.state["Character"].update({"BookNumber": 6, "MagnakaiDisciplines": ["Curing"]})
            assistant.state["Inventory"]["SpecialItems"] = ["Cess"]

            assistant.set_section(146)
            assistant.set_section(96)
            routes = assistant.current_section_flow_payload()["SourceRoutes"]
            self.assertEqual([(route["Section"], route["Available"]) for route in routes], [(49, True), (221, False)])
            assistant.set_section(49)
            assistant.set_section(129)
            self.assertTrue(assistant.death_active())

            recovery = assistant.recovery_timeline_payload()
            self.assertTrue(recovery["Timeline"][1]["ForcedTerminalRoute"])
            self.assertEqual(recovery["Recommended"]["Section"], 146)
            with redirect_stdout(io.StringIO()):
                assistant.restore_section_checkpoint(recovery["Recommended"]["Key"])
            self.assertFalse(assistant.death_active())
            self.assertEqual(assistant.state["CurrentSection"], 146)
            self.assertIn("Cess", assistant.inventory["SpecialItems"])


class CampaignDeskProductionTests(unittest.TestCase):
    def test_borderless_surfaces_share_the_recovery_background(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        foundation_css = (root / "assets" / "css" / "lw-ui-foundation.css").read_text(encoding="utf-8")

        self.assertIn("--lw-borderless-surface: color-mix(in srgb, #3d8562 7%, var(--lw-bg));", foundation_css)
        self.assertIn("--lw-panel: var(--lw-borderless-surface);", foundation_css)
        self.assertIn("--lw-ui-surface: var(--lw-borderless-surface);", foundation_css)
        self.assertIn(".lw-recovery-path", foundation_css)
        self.assertIn(".lw-section-activity__drawer", foundation_css)
        self.assertIn("--lw-borderless-control: var(--lw-ui-selected);", foundation_css)
        self.assertIn("Borderless actions share the campaign ribbon treatment", foundation_css)
        self.assertIn('html[data-lw-theme="paper"]', foundation_css)
        self.assertIn("--lw-borderless-control: #e1d7c1;", foundation_css)
        self.assertIn("background: var(--lw-borderless-control) !important;", foundation_css)
        self.assertIn("background: var(--lw-borderless-control-hover) !important;", foundation_css)
        self.assertIn("Selected tabs, persistent primary commands", foundation_css)
        self.assertIn("#currentBtn, [aria-selected=\"true\"]", foundation_css)
        self.assertIn("button.danger, .lw-ui-button--danger", foundation_css)

    def test_campaign_desk_keeps_reader_and_live_assistant_together(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        assistant_html = (root / "assistant.html").read_text(encoding="utf-8")

        self.assertIn('href="assets/css/lw-campaign.css"', assistant_html)
        self.assertIn('class="workspace lw-native" id="workspace"', assistant_html)
        self.assertIn('id="campaignMain"', assistant_html)
        self.assertIn('id="storyPanel"', assistant_html)
        self.assertIn('id="campaignGlance"', assistant_html)
        self.assertIn('id="campaignRail"', assistant_html)
        self.assertIn("['disciplines', 'Disciplines']", assistant_html)
        self.assertIn("function renderCampaignDisciplines()", assistant_html)
        self.assertIn("function renderCampaignCombat()", assistant_html)
        self.assertIn("Combat in progress", assistant_html)
        self.assertIn("Fight complete:", assistant_html)
        self.assertIn("Round record", assistant_html)
        self.assertIn("id=\"sectionActivity\"", assistant_html)
        self.assertIn("function renderSectionActivity()", assistant_html)
        self.assertIn("function stashLegacyView()", assistant_html)
        self.assertIn("function deathCombatRecord(death)", assistant_html)
        self.assertIn("Combat Record", assistant_html)
        self.assertIn("'Magnakai Disciplines'", assistant_html)
        self.assertIn("'Kai Disciplines'", assistant_html)
        self.assertIn("if (isNativeSurface && nativeSurface === 'campaign') campaignTab = 'combat';", assistant_html)
        self.assertIn("function renderCampaignSurface()", assistant_html)
        self.assertIn("function campaignResumeCopy()", assistant_html)
        self.assertIn("function campaignObjectiveCopy()", assistant_html)
        self.assertIn("const BOOK_OBJECTIVES = Object.freeze({", assistant_html)
        for book_number in range(1, 30):
            self.assertRegex(assistant_html, rf"\n\s*{book_number}: '[^']+")
        self.assertIn("Prepare to confront ${enemy}", assistant_html)
        self.assertIn("Resolve the section check", assistant_html)
        self.assertIn("Choose what you leave behind", assistant_html)
        self.assertIn("Decide what to take with you", assistant_html)
        self.assertIn("campaignAdvancedThisVisit", assistant_html)
        self.assertIn("Last time", assistant_html)
        self.assertIn("Current objective", assistant_html)
        self.assertRegex(
            assistant_html,
            r"stashLegacyView\(\);\s*toolMount\.innerHTML\s*=\s*'';\s*mountView\(toolMount\);",
        )
        self.assertIn("function renderStoryInto(target, variant)", assistant_html)
        self.assertIn("function renderCampaignRail()", assistant_html)
        self.assertIn("function recoveryTimelineHtml(compact = false)", assistant_html)
        self.assertIn("if (!currentDeath().Active) return '';", assistant_html)
        self.assertIn("data-checkpoint-recovery", assistant_html)
        self.assertNotIn("choiceGroup('Story Routes'", assistant_html)
        self.assertIn("function campaignSeriesForBook(bookNumber)", assistant_html)
        self.assertIn("data-rail-current", assistant_html)
        self.assertIn("data-rail-book", assistant_html)
        self.assertIn("renderCampaignRail();", assistant_html)
        self.assertTrue((root / "assets" / "css" / "lw-campaign.css").is_file())


class ReaderToolsProductionTests(unittest.TestCase):
    def test_reader_and_tools_share_the_existing_campaign_state(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        assistant_html = (root / "assistant.html").read_text(encoding="utf-8")
        shell_js = (root / "assets" / "js" / "lw-shell.js").read_text(encoding="utf-8")

        self.assertIn('href="assets/css/lw-reader-tools.css"', assistant_html)
        self.assertIn('id="readerCompanion"', assistant_html)
        self.assertIn('id="toolsNavigation"', assistant_html)
        self.assertIn("function renderReaderCompanion()", assistant_html)
        self.assertIn("function renderToolsNavigation()", assistant_html)
        self.assertIn("document.body.classList.toggle('lw-console-active', isCliMode())", assistant_html)
        self.assertIn('data-view="${id}"', assistant_html)
        self.assertIn("Command console", shell_js)
        reader_css = (root / "assets" / "css" / "lw-reader-tools.css").read_text(encoding="utf-8")
        self.assertIn("html.lw-surface-borderless .lw-reading-surface .book-choice", reader_css)
        self.assertIn("color: #263334 !important;", reader_css)
        foundation_css = (root / "assets" / "css" / "lw-ui-foundation.css").read_text(encoding="utf-8")
        self.assertIn(":not(.book-choice):not(.active)", foundation_css)
        self.assertTrue((root / "assets" / "css" / "lw-reader-tools.css").is_file())


class SettingsInstallProductionTests(unittest.TestCase):
    def test_settings_and_book_manager_use_the_unified_production_surfaces(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        index_html = (root / "index.html").read_text(encoding="utf-8")
        assistant_html = (root / "assistant.html").read_text(encoding="utf-8")
        installer_html = (root / "install-books.html").read_text(encoding="utf-8")

        self.assertNotIn('id="settingsModal"', index_html)
        self.assertIn('assistant.html?surface=tools&amp;tool=settings&amp;resume=1', index_html)
        self.assertIn('href="assets/css/lw-settings-install.css"', assistant_html)
        self.assertIn('class="settings-command lw-ui-panel"', assistant_html)
        self.assertIn('class="settings-workspace"', assistant_html)
        self.assertIn('class="lw-install-page"', installer_html)
        self.assertIn('id="bookManager"', installer_html)
        self.assertIn('async function loadBookStatus()', installer_html)
        self.assertIn("'TheStormsOfChai'", installer_html)
        self.assertIn("callNative('zips')", installer_html)
        self.assertTrue((root / "assets" / "css" / "lw-settings-install.css").is_file())

    def test_selected_and_primary_controls_keep_nested_labels_legible(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        foundation_css = (root / "assets" / "css" / "lw-ui-foundation.css").read_text(encoding="utf-8")
        shell_css = (root / "assets" / "css" / "lw-shell.css").read_text(encoding="utf-8")

        self.assertIn(".lw-ui-button--primary > strong", foundation_css)
        self.assertIn(".lw-ui-button--primary > small", foundation_css)
        self.assertIn("button.active > strong", shell_css)
        self.assertIn("button.active > small", shell_css)


class DistributionNoticeTests(unittest.TestCase):
    def test_notice_matches_and_ships_with_the_authorized_release(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        notice = (root / "NOTICE.md").read_text(encoding="utf-8")
        spec = (root / "LoneWolf_ActionAssistant.spec").read_text(encoding="utf-8")
        build_script = (root / "build.ps1").read_text(encoding="utf-8")

        self.assertIn("cleared for distribution", notice)
        self.assertNotIn("do not redistribute the Lone Wolf book text, illustrations", notice)
        self.assertIn('("NOTICE.md", ".")', spec)
        self.assertIn("'NOTICE.md'", build_script)


class SoundtrackPackagingTests(unittest.TestCase):
    def test_manifest_matches_packaged_mp3_masters_and_credits(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        manifest_path = root / "assets" / "audio" / "music-manifest.json"
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        spec = (root / "LoneWolf_ActionAssistant.spec").read_text(encoding="utf-8")
        credits = (root / "THIRD_PARTY_MUSIC.md").read_text(encoding="utf-8")

        self.assertEqual(manifest.get("version"), 1)
        self.assertEqual(len(manifest.get("tracks", [])), 16)
        self.assertIn('("assets", "assets")', spec)
        self.assertIn('("THIRD_PARTY_MUSIC.md", ".")', spec)
        self.assertIn("Creative Commons Attribution 4.0", credits)
        self.assertIn("Pixabay Content License", credits)

        for track in manifest["tracks"]:
            asset = root / track["path"]
            self.assertTrue(asset.is_file(), track["id"])
            self.assertEqual(asset.stat().st_size, track["bytes"], track["id"])
            self.assertEqual(
                hashlib.sha256(asset.read_bytes()).hexdigest(),
                track["sha256"],
                track["id"],
            )
            self.assertTrue(track["sourceUrl"].startswith("https://"), track["id"])
            self.assertTrue(track["licenseUrl"].startswith("https://"), track["id"])
            self.assertIn("all-approved-tracks", track["playlists"], track["id"])


class SoundtrackPlayerTests(unittest.TestCase):
    def test_shared_player_uses_manifest_preferences_and_compact_surfaces(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        player = (root / "assets" / "js" / "lw-music.js").read_text(encoding="utf-8")
        settings = (root / "assets" / "js" / "lw-settings.js").read_text(encoding="utf-8")
        assistant = (root / "assistant.html").read_text(encoding="utf-8")

        self.assertIn("assets/audio/music-manifest.json", player)
        self.assertIn("sessionStorage", player)
        self.assertIn("beforeunload", player)
        self.assertIn("data-lw-music-action", player)
        self.assertIn("playerCardMarkup('campaign')", assistant)
        self.assertIn("compactMarkup('reader')", assistant)
        for preference in (
            "lonewolf_redux.music.enabled.v1",
            "lonewolf_redux.music.volume.v1",
            "lonewolf_redux.music.playlist.v1",
            "lonewolf_redux.music.shuffle.v1",
            "lonewolf_redux.music.repeat.v1",
        ):
            self.assertIn(preference, settings)
            self.assertIn(preference, app_server.UI_PREFERENCE_KEYS)

    def test_surface_navigation_preserves_the_shared_music_player(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        assistant = (root / "assistant.html").read_text(encoding="utf-8")
        shell = (root / "assets" / "js" / "lw-shell.js").read_text(encoding="utf-8")

        self.assertIn("function navigateAssistantSurface(url, options = {})", shell)
        self.assertIn("lonewolf:navigate-surface", shell)
        self.assertIn("history.pushState", shell)
        self.assertIn("function applyNativeSurfaceNavigation(url)", assistant)
        self.assertIn("document.addEventListener('lonewolf:navigate-surface'", assistant)
        self.assertIn("let nativeSurface", assistant)

    def test_tools_and_campaign_expose_full_soundtrack_player(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        player = (root / "assets" / "js" / "lw-music.js").read_text(encoding="utf-8")
        assistant = (root / "assistant.html").read_text(encoding="utf-8")
        build = (root / "build.ps1").read_text(encoding="utf-8")
        self.assertIn("['soundtrack', 'Soundtrack'", assistant)
        self.assertIn("playerCardMarkup('campaign')", assistant)
        self.assertIn("playerCardMarkup('tools')", assistant)
        for control in ("setPlaylist", "setShuffle", "setRepeat", "setEnabled", "selectTrack", "Music credits and licenses"):
            self.assertIn(control, player)
        self.assertIn("THIRD_PARTY_MUSIC.md", build)


class ServiceTests(unittest.TestCase):
    def test_service_self_test(self) -> None:
        self.assertEqual(saa_main.run_self_test(), 0)


class FrozenCliTests(unittest.TestCase):
    def test_xterm_terminal_matches_live_pty_backend(self) -> None:
        # Frozen builds use pipe transport and local browser-side line editing;
        # source builds retain ConPTY. The page still understands WinPTY so an
        # older already-open shell can reconnect without losing terminal setup.
        root = Path(saa_main.__file__).resolve().parent
        assistant_html = (root / "assistant.html").read_text(encoding="utf-8")
        index_html = (root / "index.html").read_text(encoding="utf-8")
        saa_main_src = Path(saa_main.__file__).read_text(encoding="utf-8")

        self.assertIn("convertEol: true", assistant_html)
        self.assertIn("ptyBackend === 'winpty'", assistant_html)
        self.assertIn("windowsPty = { backend: 'winpty' }", assistant_html)
        self.assertIn("lonewolf_redux.ptyBackend", assistant_html)
        self.assertIn("lonewolf_redux.ptyBackend", index_html)
        self.assertIn("ptyBackend={pty_backend}", saa_main_src)
        self.assertIn('"pipes" if getattr(sys, "frozen", False) else "conpty"', saa_main_src)
        self.assertIn("handlePipeInput", assistant_html)
        self.assertIn("inputHistory", assistant_html)
        self.assertIn("submitLocalInput", assistant_html)

    def test_winpty_submits_xterm_standalone_enter_as_crlf(self) -> None:
        self.assertEqual(ws_server.normalize_winpty_input("\r"), "\r\n")

    def test_winpty_preserves_other_terminal_input(self) -> None:
        for text in ("s", "pasted command", "\x7f", "\x08", "\x1b[A", "line\rnext"):
            with self.subTest(text=repr(text)):
                self.assertEqual(ws_server.normalize_winpty_input(text), text)

    def test_embedded_terminal_follows_fresh_keyboard_input(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        assistant_html = (root / "assistant.html").read_text(encoding="utf-8")

        self.assertIn("scrollOnUserInput: true", assistant_html)

    def test_parent_console_is_attached_when_missing(self) -> None:
        kernel32 = mock.Mock()
        kernel32.GetConsoleWindow.return_value = 0
        kernel32.AttachConsole.return_value = 1

        self.assertTrue(saa_main._attach_parent_console(kernel32))
        kernel32.AttachConsole.assert_called_once_with(0xFFFFFFFF)

    def test_existing_console_is_reused(self) -> None:
        kernel32 = mock.Mock()
        kernel32.GetConsoleWindow.return_value = 123

        self.assertTrue(saa_main._attach_parent_console(kernel32))
        kernel32.AttachConsole.assert_not_called()

    def test_cli_dispatch_stops_cleanly_when_stdio_is_unavailable(self) -> None:
        with (
            mock.patch.object(saa_main.sys, "frozen", True, create=True),
            mock.patch.object(saa_main.sys, "argv", ["saa_main.py", "--cli"]),
            mock.patch.object(saa_main.sys, "stdout", mock.Mock()),
            mock.patch.object(saa_main.sys, "stderr", mock.Mock()),
            mock.patch.object(saa_main, "_prepare_cli_stdio", return_value=False),
            mock.patch.object(saa_main.lonewolf_redux, "main") as cli_main,
        ):
            self.assertEqual(saa_main.main(), 1)

        cli_main.assert_not_called()

    def test_frozen_terminal_reuses_main_executable(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            paths = mock.Mock(
                user_data=root / "data",
                saves=root / "saves",
                resource_data=root / "resources",
                books_lw=root / "books" / "lw",
            )
            with (
                mock.patch.object(ws_server.sys, "frozen", True, create=True),
                mock.patch.object(ws_server.sys, "executable", r"C:\App\Lone Wolf Action Assistant.exe"),
                mock.patch.object(ws_server, "PATHS", paths),
            ):
                command = ws_server.build_command()

        self.assertEqual(command[:2], [r"C:\App\Lone Wolf Action Assistant.exe", "--cli"])
        self.assertIn("--save-dir", command)
        self.assertNotIn("CLI.exe", " ".join(command))

    def test_frozen_terminal_uses_pipe_transport(self) -> None:
        with (
            mock.patch.object(ws_server.os, "name", "nt"),
            mock.patch.object(ws_server.sys, "frozen", True, create=True),
            mock.patch.object(ws_server, "terminal_session_pipes", new=mock.AsyncMock()) as pipes,
            mock.patch.object(ws_server, "build_command", return_value=["app.exe", "--cli"]),
        ):
            websocket = mock.Mock()
            websocket.request.headers.get.return_value = "http://localhost:8797"
            asyncio.run(ws_server.terminal_session(websocket))

        pipes.assert_awaited_once()
        self.assertEqual(pipes.await_args.kwargs["env"][ws_server.PIPE_CLI_ENV], "1")

    def test_pipe_cli_dispatch_bypasses_console_attachment(self) -> None:
        with (
            mock.patch.object(saa_main.sys, "frozen", True, create=True),
            mock.patch.object(saa_main.sys, "argv", ["saa_main.py", "--cli"]),
            mock.patch.dict(saa_main.os.environ, {saa_main.PIPE_CLI_ENV: "1"}),
            mock.patch.object(saa_main, "_prepare_pipe_cli_stdio", return_value=True) as pipe_stdio,
            mock.patch.object(saa_main, "_prepare_cli_stdio") as console_stdio,
            mock.patch.object(saa_main.lonewolf_redux, "main") as cli_main,
        ):
            self.assertEqual(saa_main.main(), 0)

        pipe_stdio.assert_called_once_with()
        console_stdio.assert_not_called()
        cli_main.assert_called_once_with()


class CliPanelLayoutTests(unittest.TestCase):
    def test_default_panel_width_shrinks_with_the_live_terminal(self) -> None:
        stdout = mock.Mock()
        stdout.fileno.return_value = 42
        with (
            mock.patch.object(lonewolf_redux.sys, "stdout", stdout),
            mock.patch.object(
                lonewolf_redux.os,
                "get_terminal_size",
                return_value=mock.Mock(columns=49, lines=24),
            ) as get_terminal_size,
        ):
            self.assertEqual(lonewolf_redux.panel_width(), 48)

        get_terminal_size.assert_called_once_with(42)

    def test_default_panel_width_keeps_the_legacy_wide_size(self) -> None:
        stdout = mock.Mock()
        stdout.fileno.return_value = 42
        with (
            mock.patch.object(lonewolf_redux.sys, "stdout", stdout),
            mock.patch.object(
                lonewolf_redux.os,
                "get_terminal_size",
                return_value=mock.Mock(columns=100, lines=24),
            ),
        ):
            self.assertEqual(lonewolf_redux.panel_width(), lonewolf_redux.SCREEN_WIDTH)

        self.assertEqual(lonewolf_redux.panel_width(37), 37)

    def test_rendered_panels_fit_a_narrow_terminal(self) -> None:
        output = io.StringIO()
        with (
            mock.patch.object(
                lonewolf_redux.shutil,
                "get_terminal_size",
                return_value=mock.Mock(columns=49, lines=24),
            ),
            mock.patch.object(lonewolf_redux, "terminal_supports_ansi", return_value=False),
            redirect_stdout(output),
        ):
            lonewolf_redux.panel_header("Inventory")
            lonewolf_redux.panel_pair_row(
                "Gold Crowns",
                6,
                "Weapons",
                "2/2",
            )
            lonewolf_redux.panel_footer()

        lines = [line for line in output.getvalue().splitlines() if line]
        self.assertTrue(lines)
        self.assertTrue(all(len(line) <= 48 for line in lines))


class CreationDraftTests(unittest.TestCase):
    def test_book1_draft_uses_supplied_rolls_without_mutating_campaign(self) -> None:
        before = json.dumps(app_server.ASSISTANT.state, sort_keys=True)
        with mock.patch("app_server.secrets.randbelow", side_effect=AssertionError("unexpected roll")):
            draft = app_server.create_book1_creation_draft(
                {
                    "bookNumber": 1,
                    "includeWeaponskill": True,
                    "rolls": {
                        "combatSkillRoll": 3,
                        "enduranceRoll": 2,
                        "goldRoll": 7,
                        "startingFindRoll": 4,
                        "weaponskillRoll": 8,
                    },
                }
            )

        self.assertEqual(draft["combatSkill"], 13)
        self.assertEqual(draft["enduranceBase"], 22)
        self.assertEqual(draft["endurance"], 26)
        self.assertEqual(draft["goldCrowns"], 7)
        self.assertEqual(draft["startingFind"]["Name"], "Chainmail Waistcoat")
        self.assertEqual(draft["weaponskillWeapon"], "Quarterstaff")
        self.assertEqual(before, json.dumps(app_server.ASSISTANT.state, sort_keys=True))

    def test_book1_draft_generates_missing_rolls_and_auto_disciplines(self) -> None:
        with mock.patch("app_server.secrets.randbelow", side_effect=[1, 2, 3, 9]):
            draft = app_server.create_book1_creation_draft(
                {"bookNumber": 1, "autoGenerate": True, "rolls": {}}
            )

        self.assertEqual(
            [
                draft["combatSkillRoll"],
                draft["enduranceRoll"],
                draft["goldRoll"],
                draft["startingFindRoll"],
            ],
            [1, 2, 3, 9],
        )
        self.assertEqual(draft["goldCrowns"], 15)
        self.assertEqual(len(draft["kaiDisciplines"]), 5)
        self.assertEqual(len(set(draft["kaiDisciplines"])), 5)
        self.assertTrue(set(draft["kaiDisciplines"]).issubset(app_server.lonewolf_redux.KAI_DISCIPLINES))

    def test_new_book1_auto_generation_uses_unique_disciplines(self) -> None:
        fake_assistant = mock.Mock()
        captured = {}

        def create_state(**kwargs):
            captured.update(kwargs)
            return {}

        with (
            mock.patch.object(app_server, "ASSISTANT", fake_assistant),
            mock.patch.object(app_server.lonewolf_redux, "create_book1_character_state", side_effect=create_state),
        ):
            app_server.apply_new_game({"bookNumber": 1, "autoGenerate": True})

        disciplines = captured["kai_disciplines"]
        self.assertEqual(len(disciplines), 5)
        self.assertEqual(len(set(disciplines)), 5)
        self.assertTrue(set(disciplines).issubset(app_server.lonewolf_redux.KAI_DISCIPLINES))


class SavePathContainmentTests(unittest.TestCase):
    def test_empty_path_passes_through(self) -> None:
        self.assertEqual(app_server.confine_save_path(""), "")
        self.assertEqual(app_server.confine_save_path(None), "")

    def test_catalog_index_passes_through_only_for_load(self) -> None:
        self.assertEqual(app_server.confine_save_path("2", allow_index=True), "2")
        # A save action must not treat a bare number as a catalog index.
        self.assertNotEqual(app_server.confine_save_path("2"), "2")

    def test_plain_name_resolves_inside_saves(self) -> None:
        resolved = Path(app_server.confine_save_path("my-hero.json"))
        self.assertEqual(resolved.parent, app_server.PATHS.saves.resolve())

    def test_directory_escape_is_rejected(self) -> None:
        for attempt in ("../../../pwned.json", "..\\..\\pwned.json"):
            with self.assertRaisesRegex(ValueError, "stay inside the saves folder"):
                app_server.confine_save_path(attempt)


class SpecialItemCapacityTests(unittest.TestCase):
    def assistant(self, temp_dir: str) -> lonewolf_redux.LoneWolfReduxAssistant:
        root = Path(lonewolf_redux.__file__).resolve().parent
        return lonewolf_redux.LoneWolfReduxAssistant(
            save_dir=Path(temp_dir) / "saves",
            data_dir=root / "data",
            state_data_dir=Path(temp_dir) / "state",
            books_dir=Path(temp_dir) / "books",
        )

    def test_book_eight_limit_counts_pocket_special_items(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.character["BookNumber"] = 8
            assistant.inventory["SpecialItems"] = [f"Special {index}" for index in range(11)]
            assistant.inventory["PocketSpecialItems"] = ["Pass"]

            self.assertEqual(lonewolf_redux.special_item_count(assistant.inventory), 12)
            self.assertEqual(
                lonewolf_redux.special_item_capacity_text(assistant.inventory, 8), "12/12"
            )
            self.assertFalse(assistant.add_inventory_item("special", "Grey Crystal Ring"))
            self.assertFalse(assistant.add_inventory_item("pocket", "Giak Scroll"))
            self.assertIn(
                "could not add Grey Crystal Ring",
                assistant.apply_automation_action(
                    {"type": "add_item", "container": "special", "name": "Grey Crystal Ring"}
                ),
            )

    def test_books_before_eight_keep_the_original_no_cap_rule(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir)
            assistant.character["BookNumber"] = 7
            assistant.inventory["SpecialItems"] = [f"Special {index}" for index in range(12)]

            self.assertIsNone(lonewolf_redux.special_item_limit(7))
            self.assertTrue(assistant.add_inventory_item("special", "Kazan-Oud Platinum Amulet"))
            self.assertEqual(lonewolf_redux.special_item_count(assistant.inventory), 13)

    def test_transition_drops_can_leave_special_and_pocket_items_behind(self) -> None:
        inventory = {
            "Weapons": ["Sword"],
            "BackpackItems": ["Rope"],
            "SpecialItems": ["Sommerswerd", "Silver Helm"],
            "PocketSpecialItems": ["Pass"],
        }

        messages = lonewolf_redux.apply_later_magnakai_transition_drops(
            inventory, ["special:1", "pocket:0"]
        )

        self.assertEqual(inventory["SpecialItems"], ["Sommerswerd"])
        self.assertEqual(inventory["PocketSpecialItems"], [])
        self.assertEqual(messages, ["Left behind: Silver Helm", "Left behind: Pass"])

    def test_new_setup_rejects_more_than_twelve_special_items(self) -> None:
        state = lonewolf_redux.default_state()
        state["Character"]["BookNumber"] = 8
        state["Inventory"]["SpecialItems"] = [f"Special {index}" for index in range(12)]
        state["Inventory"]["PocketSpecialItems"] = ["Pass"]

        with self.assertRaisesRegex(ValueError, "at most 12 Special Items"):
            lonewolf_redux.validate_special_item_capacity(state)


class CorruptSaveTests(unittest.TestCase):
    def test_corrupt_save_load_returns_false_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "broken.json"
            target.write_text("{ not valid json ", encoding="utf-8")
            with mock.patch.object(app_server.ASSISTANT, "save_dir", Path(temp)):
                self.assertFalse(app_server.ASSISTANT.load_game(str(target), quiet=True))

    def test_save_retries_a_transient_replace_lock(self) -> None:
        root = Path(lonewolf_redux.__file__).resolve().parent
        with tempfile.TemporaryDirectory() as temp:
            base = Path(temp)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=root / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )
            target = base / "saves" / "retry.json"
            real_replace = lonewolf_redux.os.replace
            calls = 0

            def lock_once(source: Path, destination: Path) -> None:
                nonlocal calls
                calls += 1
                if calls == 1:
                    raise PermissionError("temporary test lock")
                real_replace(source, destination)

            with mock.patch.object(lonewolf_redux.os, "replace", side_effect=lock_once):
                self.assertTrue(assistant.save_game(str(target), quiet=True))

            self.assertEqual(calls, 2)
            self.assertTrue(target.is_file())


class RequestGuardTests(unittest.TestCase):
    def setUp(self) -> None:
        import http.client

        self.http_client = http.client
        self.server, self.thread = app_server.start_server(port=0)
        self.port = int(self.server.server_address[1])
        self.local_origin = f"http://127.0.0.1:{self.port}"

    def tearDown(self) -> None:
        app_server.stop_server(self.server, self.thread)

    def _post(self, body: dict, headers: dict, host: str | None = None) -> int:
        connection = self.http_client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.putrequest("POST", "/api/action", skip_host=True, skip_accept_encoding=True)
        connection.putheader("Host", host or f"127.0.0.1:{self.port}")
        for key, value in headers.items():
            connection.putheader(key, value)
        data = json.dumps(body).encode("utf-8")
        connection.putheader("Content-Length", str(len(data)))
        connection.endheaders()
        connection.send(data)
        status = connection.getresponse().status
        connection.close()
        return status

    def test_same_origin_json_request_is_accepted(self) -> None:
        headers = {"Content-Type": "application/json", "Origin": self.local_origin}
        self.assertEqual(self._post({"action": "save", "path": ""}, headers), 200)

    def test_cross_origin_is_rejected(self) -> None:
        headers = {"Content-Type": "application/json", "Origin": "http://evil.example"}
        self.assertEqual(self._post({"action": "shutdown"}, headers), 403)

    def test_non_json_content_type_is_rejected(self) -> None:
        self.assertEqual(self._post({"action": "shutdown"}, {"Content-Type": "text/plain"}), 403)

    def test_rebinding_host_is_rejected(self) -> None:
        headers = {"Content-Type": "application/json", "Origin": self.local_origin}
        self.assertEqual(self._post({"action": "save", "path": ""}, headers, host="attacker.example"), 403)


class CrtRobustnessTests(unittest.TestCase):
    def test_malformed_lookup_raises_runtimeerror_not_keyerror(self) -> None:
        assistant = app_server.ASSISTANT
        original = assistant.crt
        try:
            assistant.crt = {"0": {}}  # column present, requested roll missing
            with self.assertRaises(RuntimeError):
                assistant.get_crt_result(0, 5)
            assistant.crt = {"not-an-int": {"5": {"EnemyLoss": 0, "PlayerLoss": 0}}}
            with self.assertRaises(RuntimeError):
                assistant.get_crt_result(0, 5)
        finally:
            assistant.crt = original

    def test_corrupt_crt_file_loads_as_none(self) -> None:
        assistant = app_server.ASSISTANT
        original_crt = assistant.crt
        original_dir = assistant.data_dir
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "crt.json").write_text("{ broken", encoding="utf-8")
            assistant.data_dir = Path(temp)
            try:
                assistant.load_crt()
                self.assertIsNone(assistant.crt)
            finally:
                assistant.data_dir = original_dir
                assistant.crt = original_crt


class KaiDisciplineLoadTests(unittest.TestCase):
    def test_normalize_dedupes_and_drops_unknown_disciplines(self) -> None:
        raw = lonewolf_redux.default_state()
        raw["Character"]["KaiDisciplines"] = ["Camouflage", "Camouflage", "Bogus", "Healing"]
        normalized = lonewolf_redux.normalize_state(raw)
        self.assertEqual(normalized["Character"]["KaiDisciplines"], ["Camouflage", "Healing"])


class NoblesRemovalTests(unittest.TestCase):
    def test_legacy_nobles_only_save_migrates_to_gold_crowns(self) -> None:
        migrated = lonewolf_redux.normalize_state({"Inventory": {"Nobles": 33}})
        self.assertEqual(migrated["Inventory"]["GoldCrowns"], 33)
        self.assertNotIn("Nobles", migrated["Inventory"])

    def test_gold_crowns_helpers_have_no_nobles_alias(self) -> None:
        self.assertTrue(hasattr(app_server.ASSISTANT, "adjust_gold_crowns"))
        self.assertFalse(hasattr(app_server.ASSISTANT, "adjust_nobles"))
        self.assertFalse(hasattr(app_server.ASSISTANT, "change_nobles"))


class WebSocketOriginTests(unittest.TestCase):
    def test_missing_and_local_origins_are_allowed(self) -> None:
        for origin in (None, "", "http://127.0.0.1:8797", "http://localhost:12345", "http://[::1]:8798"):
            self.assertTrue(ws_server.origin_is_local(origin), origin)

    def test_foreign_origins_are_blocked(self) -> None:
        for origin in ("http://evil.example", "https://attacker.example:443", "http://127.0.0.1.evil.example"):
            self.assertFalse(ws_server.origin_is_local(origin), origin)


class AsListTests(unittest.TestCase):
    def test_returns_fresh_list_that_does_not_alias_source(self) -> None:
        source = ["a", "b"]
        result = lonewolf_redux.as_list(source)
        result.append("c")
        self.assertEqual(source, ["a", "b"])  # source untouched by mutation
        self.assertEqual(result, ["a", "b", "c"])

    def test_wraps_and_normalizes_non_list_inputs(self) -> None:
        self.assertEqual(lonewolf_redux.as_list(None), [])
        self.assertEqual(lonewolf_redux.as_list("solo"), ["solo"])


class GreyStarResidueRemovedTests(unittest.TestCase):
    def test_new_character_has_no_willpower_or_magick_keys(self) -> None:
        import io
        import contextlib

        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            app_server.apply_new_game({"bookNumber": 1, "autoGenerate": True})
        character = app_server.ASSISTANT.state["Character"]
        for key in ("WillpowerCurrent", "WillpowerBase", "LesserMagicks", "HigherMagicks"):
            self.assertNotIn(key, character)

    def test_karmo_potion_doubles_endurance_without_willpower_keyerror(self) -> None:
        import io
        import contextlib

        assistant = app_server.ASSISTANT
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            app_server.apply_new_game({"bookNumber": 1, "autoGenerate": True})
        assistant.character["EnduranceMax"] = 25
        assistant.character["EnduranceCurrent"] = 10
        assistant.inventory["BackpackItems"] = ["Karmo Potion"]
        with contextlib.redirect_stdout(buf):
            assistant.use_item("backpack", "Karmo Potion")  # previously KeyError on WillpowerCurrent
        self.assertEqual(assistant.character["EnduranceCurrent"], 20)
        with contextlib.redirect_stdout(buf):
            assistant.finish_karmo_potion()
        self.assertEqual(assistant.character["EnduranceCurrent"], 10)

    def test_alether_berries_are_consumed_for_their_combat_skill_bonus(self) -> None:
        import contextlib

        assistant = app_server.ASSISTANT
        with contextlib.redirect_stdout(io.StringIO()):
            app_server.apply_new_game({"bookNumber": 1, "autoGenerate": True})
        before = assistant.character["CombatSkillCurrent"]
        assistant.inventory["BackpackItems"] = ["Alether Berries"]
        with contextlib.redirect_stdout(io.StringIO()):
            assistant.use_item("backpack", "Alether Berries")
        self.assertEqual(assistant.character["CombatSkillCurrent"], before + 2)
        self.assertNotIn("Alether Berries", assistant.inventory["BackpackItems"])

    def test_willpower_and_staff_helpers_are_gone(self) -> None:
        for attr in (
            "combat_uses_magical_staff",
            "has_available_staff",
            "change_willpower",
            "adjust_willpower",
            "pay_willpower_cost",
        ):
            self.assertFalse(hasattr(app_server.ASSISTANT, attr), attr)


class CheatSessionTests(unittest.TestCase):
    @staticmethod
    def fixture_session(*effects: str) -> tuple[cheat_session.CheatSession, dict[str, str]]:
        phrases = {effect: f"fixture-{index}" for index, effect in enumerate(effects, 1)}
        digest_map = {
            cheat_session.digest_code(phrase): effect for effect, phrase in phrases.items()
        }
        return cheat_session.CheatSession(digest_map), phrases

    @staticmethod
    def assistant(temp_dir: str, session: cheat_session.CheatSession) -> lonewolf_redux.LoneWolfReduxAssistant:
        root = Path(lonewolf_redux.__file__).resolve().parent
        base = Path(temp_dir)
        return lonewolf_redux.LoneWolfReduxAssistant(
            save_dir=base / "saves",
            data_dir=root / "data",
            state_data_dir=base / "state",
            books_dir=base / "books",
            cheat_provider=session,
        )

    def test_toggle_is_case_insensitive_and_achievement_lock_is_session_sticky(self) -> None:
        session, phrases = self.fixture_session("max_cs")
        digest = cheat_session.digest_code(phrases["max_cs"].upper())
        enabled = session.toggle_digest(digest)
        disabled = session.toggle_digest(digest)

        self.assertTrue(enabled["enabled"])
        self.assertFalse(disabled["enabled"])
        self.assertFalse(session.is_active("max_cs"))
        self.assertTrue(session.achievements_locked())

    def test_forced_rolls_are_mutually_exclusive(self) -> None:
        session, phrases = self.fixture_session("force_nine", "force_zero")
        session.toggle_digest(cheat_session.digest_code(phrases["force_nine"]))
        self.assertEqual(session.forced_digit(), 9)
        session.toggle_digest(cheat_session.digest_code(phrases["force_zero"]))
        self.assertEqual(session.forced_digit(), 0)
        self.assertFalse(session.is_active("force_nine"))

    def test_session_effects_survive_new_assistant_and_do_not_enter_save_json(self) -> None:
        session, phrases = self.fixture_session("max_health", "max_cs")
        session.toggle_digest(cheat_session.digest_code(phrases["max_health"]))
        session.toggle_digest(cheat_session.digest_code(phrases["max_cs"]))
        with tempfile.TemporaryDirectory() as temp_dir:
            first = self.assistant(temp_dir, session)
            base_end = first.character["EnduranceMax"]
            path = Path(temp_dir) / "saves" / "clean.json"
            first.save_game(str(path), quiet=True)
            second = self.assistant(temp_dir, session)
            saved = json.loads(path.read_text(encoding="utf-8"))

        self.assertEqual(second.effective_endurance_current(), 99)
        self.assertEqual(second.effective_combat_skill(), 99)
        self.assertEqual(saved["Character"]["EnduranceMax"], base_end)
        self.assertNotIn("Cheat", json.dumps(saved))

    def test_developer_sandbox_blocks_save_and_restores_snapshot(self) -> None:
        session, phrases = self.fixture_session("developer_sight")
        digest = cheat_session.digest_code(phrases["developer_sight"])
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir, session)
            original = int(assistant.character["CombatSkillCurrent"])
            with redirect_stdout(io.StringIO()):
                assistant.toggle_cheat_digest(digest)
                assistant.character["CombatSkillCurrent"] = original + 50
                blocked_path = Path(temp_dir) / "saves" / "sandbox.json"
                assistant.save_game(str(blocked_path), quiet=True)
                assistant.toggle_cheat_digest(digest)

            self.assertFalse(blocked_path.exists())
            self.assertEqual(assistant.character["CombatSkillCurrent"], original)

    def test_resource_guards_preserve_costs_but_keep_gains(self) -> None:
        session, phrases = self.fixture_session("infinite_gold", "infinite_meals")
        session.toggle_digest(cheat_session.digest_code(phrases["infinite_gold"]))
        session.toggle_digest(cheat_session.digest_code(phrases["infinite_meals"]))
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir, session)
            assistant.inventory["GoldCrowns"] = 10
            assistant.inventory["BackpackItems"] = ["Meal", "Meal"]
            before = assistant.cheat_resource_snapshot()
            assistant.inventory["GoldCrowns"] = 3
            assistant.inventory["BackpackItems"] = []
            assistant.finalize_cheat_resources(before)
            self.assertEqual(assistant.inventory["GoldCrowns"], 10)
            self.assertEqual(assistant.inventory["BackpackItems"].count("Meal"), 2)

            before = assistant.cheat_resource_snapshot()
            assistant.inventory["GoldCrowns"] = 15
            assistant.finalize_cheat_resources(before)
            self.assertEqual(assistant.inventory["GoldCrowns"], 15)

    def test_bottomless_inventory_and_all_disciplines_are_effective_only(self) -> None:
        session, phrases = self.fixture_session("bottomless_inventory", "all_disciplines")
        session.toggle_digest(cheat_session.digest_code(phrases["bottomless_inventory"]))
        session.toggle_digest(cheat_session.digest_code(phrases["all_disciplines"]))
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir, session)
            assistant.inventory["Weapons"] = ["Axe", "Sword"]
            self.assertTrue(assistant.add_inventory_item("weapon", "Spear"))
            self.assertEqual(set(assistant.effective_disciplines()), set(lonewolf_redux.KAI_DISCIPLINES))
            self.assertEqual(assistant.character["KaiDisciplines"], [])

    def test_one_round_combat_and_god_mode_use_effective_stats(self) -> None:
        session, phrases = self.fixture_session("one_round_combat", "god_mode")
        session.toggle_digest(cheat_session.digest_code(phrases["one_round_combat"]))
        session.toggle_digest(cheat_session.digest_code(phrases["god_mode"]))
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir, session)
            with redirect_stdout(io.StringIO()):
                assistant.start_combat(["combat", "start", "Fixture Enemy", "50", "200"])
                assistant.combat_round(["combat", "round", "0"])

            self.assertFalse(assistant.combat["Active"])
            self.assertEqual(assistant.effective_combat_skill(), 99)
            self.assertEqual(assistant.effective_endurance_current(), 99)
            self.assertEqual(assistant.state["CombatHistory"][-1]["Outcome"], "Victory")

    def test_unkillable_restores_full_latest_safe_checkpoint(self) -> None:
        session, phrases = self.fixture_session("unkillable")
        session.toggle_digest(cheat_session.digest_code(phrases["unkillable"]))
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir, session)
            assistant.character["EnduranceCurrent"] = 17
            assistant.save_section_checkpoint("ready")
            assistant.character["EnduranceCurrent"] = 1
            with redirect_stdout(io.StringIO()):
                assistant.register_death("instant", "fixture failure")

            self.assertEqual(assistant.character["EnduranceCurrent"], 17)
            self.assertFalse(assistant.death_active())

    def test_achievement_sync_is_suppressed_after_activation(self) -> None:
        session, phrases = self.fixture_session("max_cs")
        session.toggle_digest(cheat_session.digest_code(phrases["max_cs"]))
        with tempfile.TemporaryDirectory() as temp_dir:
            assistant = self.assistant(temp_dir, session)
            with mock.patch.object(assistant, "achievement_satisfied", return_value=True):
                self.assertEqual(assistant.sync_achievements(), [])
            self.assertEqual(assistant.achievement_unlocked_ids(), set())

    def test_desktop_bridge_requires_token_and_returns_authoritative_status(self) -> None:
        import urllib.error
        import urllib.request

        server, thread = app_server.start_server(port=0)
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/api/internal/session-cheats"
            client = cheat_session.RemoteCheatClient(url, app_server.CHEAT_SESSION.token)
            self.assertEqual(client.status()["active"], app_server.CHEAT_SESSION.status()["active"])

            request = urllib.request.Request(
                url,
                data=b'{"operation":"status"}',
                headers={"Content-Type": "application/json", "X-LoneWolf-Session": "invalid"},
                method="POST",
            )
            with self.assertRaises(urllib.error.HTTPError) as raised:
                urllib.request.urlopen(request, timeout=3)
            self.assertEqual(raised.exception.code, 403)
            raised.exception.close()
        finally:
            app_server.stop_server(server, thread)

    def test_remote_client_survives_a_stale_token_and_prefers_live_token_file(self) -> None:
        server, thread = app_server.start_server(port=0)
        try:
            url = f"http://127.0.0.1:{server.server_address[1]}/api/internal/session-cheats"
            stale = cheat_session.RemoteCheatClient(url, "stale-token")
            self.assertEqual(stale.status(), {})

            with tempfile.TemporaryDirectory() as temp_dir:
                token_file = Path(temp_dir) / "cheat-session.json"
                token_file.write_text(
                    json.dumps({"url": url, "token": app_server.CHEAT_SESSION.token}),
                    encoding="utf-8",
                )
                provider = cheat_session.provider_from_environment({
                    "LONEWOLF_SAA_CHEAT_FILE": str(token_file),
                    "LONEWOLF_SAA_CHEAT_URL": url,
                    "LONEWOLF_SAA_CHEAT_TOKEN": "stale-token",
                })
                self.assertIsInstance(provider, cheat_session.RemoteCheatClient)
                self.assertEqual(provider.status()["active"], app_server.CHEAT_SESSION.status()["active"])
        finally:
            app_server.stop_server(server, thread)


if __name__ == "__main__":
    unittest.main()
