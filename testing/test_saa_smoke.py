"""Standalone-app smoke tests that don't require licensed book content."""

from __future__ import annotations

import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

import app_server
import book_manager
import saa_main


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

    def test_assistant_honors_campaign_start_without_mutating_until_begin(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn("pageParams.get('campaign') === 'new'", assistant_html)
        self.assertIn('function shouldShowBook1Creation()', assistant_html)
        self.assertIn('function confirmCampaignReplacement()', assistant_html)
        self.assertIn('clearCampaignStartRequest();', assistant_html)

    def test_campaign_entry_keeps_setup_visible_and_protects_existing_campaigns(self) -> None:
        assistant_html = self.source_text("assistant.html")
        self.assertIn("if (isCliMode() && !campaignStartRequested)", assistant_html)
        self.assertIn('data-campaign-cancel', assistant_html)
        self.assertIn("const campaignEntry = campaignStartRequested && card.dataset.campaignEntry === 'true';", assistant_html)
        self.assertGreaterEqual(assistant_html.count('if (!confirmCampaignReplacement()) return;'), 3)

        cancel_start = assistant_html.index('if (button.dataset.creationCancel !== undefined)')
        cancel_end = assistant_html.index('if (button.dataset.campaignCancel !== undefined)', cancel_start)
        self.assertNotIn('clearCampaignStartRequest', assistant_html[cancel_start:cancel_end])


class CardSizingTests(unittest.TestCase):
    def test_dashboard_card_sizes_have_distinct_widths(self) -> None:
        root = Path(saa_main.__file__).resolve().parent
        assistant_html = (root / "assistant.html").read_text(encoding="utf-8")

        self.assertIn("#view.view-card-grid > .dashboard-card.card-size-small", assistant_html)
        self.assertIn("flex: 0 0 170px;", assistant_html)
        self.assertIn("min-height: 150px;", assistant_html)
        self.assertIn("#view.view-card-grid > .dashboard-card.card-size-medium", assistant_html)
        self.assertIn("flex: 0 0 calc(50% - 0.325rem);", assistant_html)
        self.assertIn('class="stat-adjust-line"', assistant_html)
        self.assertIn('class="stat-set-line"', assistant_html)
        self.assertIn("options.resizable === false", assistant_html)
        self.assertIn("resizable: false", assistant_html)


class ServiceTests(unittest.TestCase):
    def test_service_self_test(self) -> None:
        self.assertEqual(saa_main.run_self_test(), 0)


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


if __name__ == "__main__":
    unittest.main()
