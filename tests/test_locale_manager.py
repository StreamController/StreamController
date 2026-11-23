import unittest
from pathlib import Path

from locales.LocaleManager import LocaleManager


class TestLocaleManager(unittest.TestCase):
    def setUp(self):
        self.manager = LocaleManager(Path(__file__).resolve().parents[1] / "locales" / "locales.csv")
        self.manager.set_language("fr_FR")

    def test_french_apostrophes_are_literal(self):
        self.assertEqual(self.manager.get("action-configurator-header"), "Configurer l'action")

    def test_quotes_survive_while_markup_characters_are_escaped(self):
        self.manager.locale_data["example"] = {"fr_FR": '''L'écran "A&B" <OK>'''}
        self.assertEqual(self.manager.get("example"), '''L'écran "A&amp;B" &lt;OK&gt;''')
