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

# Import Python modules
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.deckSwitcher import DeckSwitcher
from src.windows.mainWindow.elements.PageSelector import PageSelector

class HeaderBar(Gtk.HeaderBar):
    def __init__(self, deck_manager, main_window, deck_stack, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager
        self.deckStack = deck_stack
        self.main_window = main_window
        self.build()

    def build(self):
        # Page selector
        self.page_selector = PageSelector(self.main_window, self.deck_manager.page_manager)
        self.pack_start(self.page_selector)

        # Deck selector
        self.deckSwitcher = DeckSwitcher(hexpand=False, margin_start=75, margin_end=75, width_request=500)
        self.deckSwitcher.set_stack(self.deckStack)
        self.set_title_widget(self.deckSwitcher)