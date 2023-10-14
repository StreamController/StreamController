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
from src.windows.mainWindow.elements.DeckPage import DeckPage

class DeckStack(Gtk.Stack):
    def __init__(self, deck_manager, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager
        self.add_pages()
        self.build()

    def build(self):
        pass

    def add_pages(self)
        deck_names = []
        deck_numbers = []
        print("loading", self.deck_manager.deck_controller)
        print(len(self.deck_manager.deck_controller))
        for deck_controller in self.deck_manager.deck_controller:
            print("1")
            deck_type = deck_controller.deck.deck_type()
            deck_numbers.append(str(deck_controller.deck.get_serial_number()))
            if deck_type not in deck_names:
                deck_names.append(deck_type)
                continue
            # name already exists
            while deck_type in deck_names:
                if deck_type[-1].isdigit():
                    deck_type = deck_type[:-1] + chr(ord(deck_type[-1]) + 1)
                else:
                    deck_type = deck_type + " 2"

            deck_names.append(deck_type)
        
        for i in range(len(deck_names)):
            # self.add_titled(Gtk.Label(label=f"Deck {deck_names[i]}"), deck_ids[i], deck_names[i])
            page = DeckPage(self.deck_manager.deck_controller[i])
            self.add_titled(page, deck_numbers[i], deck_names[i])
            # self.set_visible_child_name(deck_ids[i])