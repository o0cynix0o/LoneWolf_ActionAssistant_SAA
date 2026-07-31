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

    def test_release_metadata_is_3_1_7(self) -> None:
        readme = (self.root / "README.md").read_text(encoding="utf-8")
        building = (self.root / "docs" / "BUILDING.md").read_text(encoding="utf-8")
        user_guide = (self.root / "docs" / "USER_GUIDE.md").read_text(encoding="utf-8")
        changelog = (self.root / "CHANGELOG.md").read_text(encoding="utf-8")
        installer = (
            self.root / "installer" / "LoneWolf_ActionAssistant.iss"
        ).read_text(encoding="utf-8")
        version_info = (self.root / "version_info.txt").read_text(encoding="utf-8")

        self.assertIn("# Lone Wolf Action Assistant 3.1.7", readme)
        self.assertIn("Version: **3.1.7**", readme)
        self.assertIn("# Building Lone Wolf Action Assistant 3.1.7", building)
        self.assertIn("# Lone Wolf Action Assistant 3.1.7", user_guide)
        self.assertIn("## 3.1.7", changelog)
        self.assertIn('#define AppVersion "3.1.7"', installer)
        self.assertIn("filevers=(3, 1, 7, 0)", version_info)
        self.assertIn("prodvers=(3, 1, 7, 0)", version_info)
        self.assertIn("StringStruct(u'FileVersion', u'3.1.7')", version_info)
        self.assertIn("StringStruct(u'ProductVersion', u'3.1.7')", version_info)

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
