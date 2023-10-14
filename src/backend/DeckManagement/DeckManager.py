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

# Import own modules
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.PageManager import PageManager
class DeckManager:
    def __init__(self):
        self.deck_controller = []
        self.page_manager = PageManager()
        self.page_manager.load_pages()
    def load_decks(self):
        decks=DeviceManager().enumerate()
        for deck in decks:
            deck_controller = DeckController(deck)
            self.deck_controller.append(deck_controller)