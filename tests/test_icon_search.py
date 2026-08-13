"""
Tests for the matching of the icon browser.

Icon names are long and machine generated, which is exactly the case the old
fuzz.ratio() over the whole name got wrong: searching "battery" scored
"battery-level-90-charged-symbolic" below the cutoff and hid every result.

Run with:

    python3 -m unittest discover -s tests -t .
"""
import unittest

from src.backend.IconPackManagement.Icon import Icon
from src.backend.IconPackManagement import IconSearch


class FakePack:
    def __init__(self, name: str):
        self.name = name


def make_icon(name: str, category: str = "", pack: str = "Test Pack") -> Icon:
    return Icon(icon_pack=FakePack(pack), path=f"/tmp/{pack}/{category}/{name}.png", category=category)


class TestIconSearch(unittest.TestCase):
    def search(self, icons: list[Icon], query: str, match_pack_name: bool = False) -> list[str]:
        return [icon.name for icon in IconSearch.search_icons(icons, query, match_pack_name=match_pack_name)]

    def test_long_generated_names_are_found(self):
        icons = [
            make_icon("battery-level-90-charged-symbolic"),
            make_icon("weather-clear-night-symbolic"),
        ]
        self.assertEqual(self.search(icons, "battery"), ["battery-level-90-charged-symbolic"])

    def test_empty_query_returns_everything(self):
        icons = [make_icon("b-icon"), make_icon("a-icon")]
        self.assertEqual(self.search(icons, ""), ["a-icon", "b-icon"])

    def test_exact_match_comes_first(self):
        icons = [
            make_icon("battery-low-symbolic"),
            make_icon("battery"),
            make_icon("indicator-battery"),
        ]
        self.assertEqual(self.search(icons, "battery")[0], "battery")

    def test_prefix_beats_match_inside_the_name(self):
        icons = [
            make_icon("indicator-battery-full"),
            make_icon("battery-full"),
        ]
        self.assertEqual(self.search(icons, "battery"), ["battery-full", "indicator-battery-full"])

    def test_shorter_name_wins_on_equal_score(self):
        icons = [
            make_icon("battery-level-90-charged-symbolic"),
            make_icon("battery-low"),
        ]
        self.assertEqual(self.search(icons, "battery")[0], "battery-low")

    def test_all_words_have_to_match(self):
        icons = [
            make_icon("battery-low-symbolic"),
            make_icon("battery-full-symbolic"),
        ]
        self.assertEqual(self.search(icons, "battery low"), ["battery-low-symbolic"])

    def test_words_can_match_in_any_order(self):
        icons = [make_icon("network-wireless-signal-good-symbolic")]
        self.assertEqual(self.search(icons, "good network"), ["network-wireless-signal-good-symbolic"])

    def test_category_is_searched(self):
        icons = [
            make_icon("volume-high", category="Audio"),
            make_icon("folder-open", category="Places"),
        ]
        self.assertEqual(self.search(icons, "audio"), ["volume-high"])

    def test_name_match_beats_category_match(self):
        icons = [
            make_icon("brightness", category="Display"),
            make_icon("wallpaper", category="Brightness"),
        ]
        self.assertEqual(self.search(icons, "brightness"), ["brightness", "wallpaper"])

    def test_pack_name_is_only_searched_across_packs(self):
        icons = [make_icon("volume-high", pack="Material Symbols")]
        self.assertEqual(self.search(icons, "material"), [])
        self.assertEqual(self.search(icons, "material", match_pack_name=True), ["volume-high"])

    def test_typos_still_match(self):
        icons = [make_icon("battery-level-90-charged-symbolic")]
        self.assertEqual(self.search(icons, "batery"), ["battery-level-90-charged-symbolic"])

    def test_unrelated_icons_are_dropped(self):
        icons = [make_icon("weather-clear-night-symbolic")]
        self.assertEqual(self.search(icons, "battery"), [])

    def test_browse_order_groups_categories(self):
        icons = [
            make_icon("volume-low", category="Audio"),
            make_icon("folder", category="Places"),
            make_icon("volume-high", category="Audio"),
        ]
        self.assertEqual(self.search(icons, ""), ["volume-high", "volume-low", "folder"])

    def test_browse_order_groups_packs_across_packs(self):
        icons = [
            make_icon("arrow", pack="Bootstrap"),
            make_icon("alarm", pack="Material Symbols"),
            make_icon("bell", pack="Bootstrap"),
        ]
        self.assertEqual(self.search(icons, "", match_pack_name=True), ["arrow", "bell", "alarm"])


if __name__ == "__main__":
    unittest.main()
