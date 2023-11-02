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
# Import Python modules
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.ImageHelpers import PILHelper
from loguru import logger as log

# Import own modules
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.PageManager import PageManager
from src.backend.SettingsManager import SettingsManager
from src.backend.DeckManagement.HelperMethods import get_sys_param_value
from src.backend.DeckManagement.Subclasses.FakeDeck import FakeDeck

# Import globals
import globals as gl

class DeckManager:
    def __init__(self):
        #TODO: Maybe outsource some objects
        self.deck_controller = []
        self.settings_manager = SettingsManager()
        self.page_manager = gl.page_manager
        # self.page_manager.load_pages()
    def load_decks(self):
        decks=DeviceManager().enumerate()
        for deck in decks:
            deck_controller = DeckController(self, deck)
            self.deck_controller.append(deck_controller)

        # Load fake decks
        self.load_fake_decks()

    def load_fake_decks(self):
        n_fake_decks = get_sys_param_value("--fake")
        if n_fake_decks == None:
            return
        if not n_fake_decks.isdigit():
            return
        n_fake_decks = int(n_fake_decks)
        log.info(f"Loading {n_fake_decks} fake deck(s)")
        for i in range(n_fake_decks):
            fake_deck_controller = DeckController(self, FakeDeck(serial_number = f"fake-deck-{i+1}", deck_type=f"Fake Deck {i+1}"))
            self.deck_controller.append(fake_deck_controller)