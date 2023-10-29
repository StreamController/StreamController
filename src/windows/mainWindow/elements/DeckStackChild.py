"""
Author: Core447
Year: 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import own modules
from src.windows.mainWindow.elements.PageSettings.PageSettings import PageSettings
from src.windows.mainWindow.elements.DeckSettings.DeckSettingsPage import DeckSettingsPage
from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

class DeckStackChild(Gtk.Stack):
    """
    Child of DeckStack
    This stack features one page for the page specific settings and one for the deck settings
    """
    def __init__(self, deck_stack, deck_controller, **kwargs):
        super().__init__(**kwargs)
        self.deck_stack = deck_stack
        self.deck_controller = deck_controller

        self.build()

    def build(self):
        self.page_settings = PageSettingsPage(self, self.deck_controller)
        self.deck_settings = DeckSettingsPage(self, self.deck_controller)

        self.add_named(self.page_settings, "Page Settings")
        self.add_named(self.deck_settings, "Deck Settings")