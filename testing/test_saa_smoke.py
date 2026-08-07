"""Standalone-app smoke tests that don't require licensed book content."""

from __future__ import annotations

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
        expected_books = set(range(1, 13))
        self.assertEqual(set(lonewolf_redux.BOOKS), expected_books)

        root = Path(lonewolf_redux.__file__).resolve().parent
        for book_number in expected_books:
            self.assertTrue((root / "data" / f"book{book_number}-simple-automations.json").is_file())
            self.assertTrue((root / "data" / f"book{book_number}-section-flows.json").is_file())

        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(
                save_dir=base / "saves",
                data_dir=root / "data",
                state_data_dir=base / "state",
                books_dir=base / "books",
            )

        self.assertTrue(expected_books.issubset({int(key) for key in assistant.section_automation}))
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
        self.assertEqual(result["Inventory"]["BackpackItems"], ["Special Rations"] * 5)
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
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6}, "Inventory": {"GoldCrowns": 0, "QuiverArrows": 3}, "CurrentSection": 98})
            assistant.apply_shop_sale("arrows")
            assistant.set_section(275)
            assistant.inventory["BackpackItems"] = ["Map of Tekaro"]
            sale = assistant.current_section_flow_payload()["Shop"]["Sales"][0]
            assistant.apply_shop_sale(sale["Id"])

        self.assertEqual(assistant.inventory["QuiverArrows"], 0)
        self.assertEqual(assistant.inventory["BackpackItems"], [])
        self.assertEqual(assistant.inventory["GoldCrowns"], 4)

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

            self.assertFalse(assistant.evaluate_flow_condition(rope_condition))
            self.assertFalse(assistant.evaluate_flow_condition(rank_condition))
            self.assertFalse(assistant.evaluate_flow_condition(arrow_condition))
            assistant.inventory["BackpackItems"] = ["Rope"]
            assistant.inventory["QuiverArrows"] = 2
            assistant.character["MagnakaiRank"] = 6

        self.assertTrue(assistant.evaluate_flow_condition(rope_condition))
        self.assertTrue(assistant.evaluate_flow_condition(rank_condition))
        self.assertTrue(assistant.evaluate_flow_condition(arrow_condition))
        self.assertEqual(rope_reason, "Requires Rope.")
        self.assertEqual(rank_reason, "Requires Principalin rank.")
        self.assertEqual(arrow_reason, "Requires at least 2 Arrows.")

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

    def test_book6_warhammer_roll_uses_source_item_and_discipline_modifiers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            base = Path(temp_dir)
            assistant = lonewolf_redux.LoneWolfReduxAssistant(save_dir=base / "saves", data_dir=Path(lonewolf_redux.__file__).resolve().parent / "data", state_data_dir=base / "state", books_dir=base / "books")
            assistant.state = lonewolf_redux.normalize_state({"Character": {"BookNumber": 6, "MagnakaiDisciplines": ["Weaponmastery", "Huntmastery"]}, "Inventory": {"BackpackItems": ["Rope", "Rope"]}, "CurrentSection": 101})
            result = assistant.roll_current_section(raw_roll=0)
        self.assertEqual(result["Total"], 5)

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
        expected_rnt = {6: 22, 7: 22, 8: 16, 9: 20, 10: 25, 11: 29, 12: 39}
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
                    if isinstance(entry, dict) and ("roll" in entry or "stagedRoll" in entry)
                )
                self.assertEqual(combat_count, expected_combat[book_number])
                self.assertEqual(rnt_count, expected_rnt[book_number])

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

    def test_reader_toolbar_switches_to_the_magnakai_series(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn('data-reader-series="kai"', assistant_html)
        self.assertIn('data-reader-series="magnakai"', assistant_html)
        self.assertNotIn('Book 8 is not in testing yet.', assistant_html)
        self.assertNotIn('Book 9 is not in testing yet.', assistant_html)
        self.assertNotIn('Book 12 is not in testing yet.', assistant_html)
        self.assertIn("const readerSeries = book.number >= 6 ? 'magnakai' : 'kai';", assistant_html)

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
        self.assertIn("window.location.href = 'assistant.html?resume=1';", index_html)
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
        self.assertIn("if (isCliMode() && !campaignStartRequested)", assistant_html)
        self.assertIn('data-campaign-cancel', assistant_html)
        self.assertIn("const campaignEntry = campaignStartRequested && card.dataset.campaignEntry === 'true';", assistant_html)
        self.assertGreaterEqual(assistant_html.count('if (!confirmCampaignReplacement()) return;'), 3)

        cancel_start = assistant_html.index('if (button.dataset.creationCancel !== undefined)')
        cancel_end = assistant_html.index('if (button.dataset.campaignCancel !== undefined)', cancel_start)
        self.assertNotIn('clearCampaignStartRequest', assistant_html[cancel_start:cancel_end])

    def test_completion_ui_contains_magnakai_campaign_handoffs(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn("nextBook >= 2 && nextBook <= 12", assistant_html)
        self.assertIn("Choose exactly 3 Magnakai Disciplines", assistant_html)
        self.assertIn("New Magnakai Discipline", assistant_html)
        self.assertIn("Continue to Book ${escapeHtml(nextBook)}", assistant_html)

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

    def test_release_metadata_is_3_4_5_internal_testing(self) -> None:
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        building = (self.root / "docs" / "BUILDING.md").read_text(encoding="utf-8")
        user_guide = (self.root / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")
        changelog = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        installer = (
            self.root / "installer" / "LoneWolf_ActionAssistant.iss"
        ).read_text(encoding="utf-8")
        version_info = (self.root / "version_info.txt").read_text(encoding="utf-8")

        self.assertIn("# Lone Wolf Action Assistant 3.4.5 Internal Testing", readme)
        self.assertIn("Version: **3.4.5 Internal Testing**", readme)
        self.assertIn("# Building Lone Wolf Action Assistant 3.4.5 Internal Testing", building)
        self.assertIn("# Lone Wolf Action Assistant 3.4.5 Internal Testing", user_guide)
        self.assertIn("## 3.4.5 - Internal Testing", changelog)
        self.assertIn('#define AppVersion "3.4.5"', installer)
        self.assertIn("filevers=(3, 4, 5, 0)", version_info)
        self.assertIn("prodvers=(3, 4, 5, 0)", version_info)
        self.assertIn("StringStruct(u'FileVersion', u'3.4.5')", version_info)
        self.assertIn("StringStruct(u'ProductVersion', u'3.4.5')", version_info)

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


class SeriesSigilTests(unittest.TestCase):
    def test_all_series_share_the_theme_aware_wolf_mask(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        index_html = (root / "index.html").read_text(encoding="utf-8")

        self.assertIn("assets/images/series-sigil-wolf-mask.png", index_html)
        self.assertIn("background: currentColor;", index_html)
        self.assertIn("-webkit-mask:", index_html)
        self.assertIn("mask: url('assets/images/series-sigil-wolf-mask.png')", index_html)
        self.assertIn('<span class="series-emblem" aria-hidden="true"></span>', index_html)
        self.assertIn('data-series="kai" role="img" aria-label="Kai series emblem"', index_html)
        self.assertIn("seriesDivider.dataset.series = series;", index_html)
        self.assertNotIn("symbol-kai", index_html)
        self.assertNotIn("symbol-magnakai", index_html)
        self.assertNotIn("symbol-grand-master", index_html)
        self.assertNotIn("symbol-new-order", index_html)
        self.assertNotIn("series-sigil-wolf-source.png", index_html)

        self.assertTrue((root / "assets" / "images" / "series-sigil-wolf-mask.png").is_file())
        self.assertTrue((root / "design-assets" / "series-sigil-wolf-source.png").is_file())
        self.assertTrue((root / "design-assets" / "README.md").is_file())


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


class ServiceTests(unittest.TestCase):
    def test_service_self_test(self) -> None:
        self.assertEqual(saa_main.run_self_test(), 0)


class FrozenCliTests(unittest.TestCase):
    def test_xterm_terminal_matches_live_pty_backend(self) -> None:
        # The PTY backend differs by build (ConPTY from source, WinPTY when
        # frozen), so the shell passes the live backend to the page instead of
        # xterm guessing. xterm must always translate LF -> CRLF (staircase
        # fix) and apply the winpty compatibility rules only for WinPTY.
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
        self.assertIn('"winpty" if getattr(sys, "frozen", False) else "conpty"', saa_main_src)

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


class CorruptSaveTests(unittest.TestCase):
    def test_corrupt_save_load_returns_false_without_raising(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "broken.json"
            target.write_text("{ not valid json ", encoding="utf-8")
            with mock.patch.object(app_server.ASSISTANT, "save_dir", Path(temp)):
                self.assertFalse(app_server.ASSISTANT.load_game(str(target), quiet=True))


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


if __name__ == "__main__":
    unittest.main()
