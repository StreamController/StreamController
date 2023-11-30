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
from StreamDeck.Devices import StreamDeck
from StreamDeck.ImageHelpers import PILHelper
from loguru import logger as log
from usbmonitor import USBMonitor

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

        # USB monitor to detect connections and disconnections
        self.usb_monitor = USBMonitor()
        self.usb_monitor.start_monitoring(on_connect=self.on_connect, on_disconnect=self.on_disconnect)

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

    def on_connect(self, device_id, device_info):
        log.info(f"Device {device_id} with info: {device_info} connected")
        # Check if it is a supported device
        if device_info["ID_VENDOR"] != "Elgato":
            pass
            # return

        # Get already loaded deck serial ids
        loaded_deck_ids = []
        for controller in self.deck_controller:
            loaded_deck_ids.append(controller.deck.id())
        
        for deck in DeviceManager().enumerate():
            if deck.id() in loaded_deck_ids:
                continue

            # Add deck
            self.add_newly_connected_deck(deck)


    def on_disconnect(self, device_id, device_info):
        log.info(f"Device {device_id} with info: {device_info} disconnected")

        for controller in self.deck_controller:
            if not controller.deck.connected():
                self.deck_controller.remove(controller)
                gl.app.main_win.leftArea.deck_stack.remove_page(controller)

                controller.delete()

                del controller

    def add_newly_connected_deck(self, deck:StreamDeck):
        deck_controller = DeckController(self, deck)

        # Add to deck stack
        gl.app.main_win.leftArea.deck_stack.add_page(deck_controller)


        self.deck_controller.append(deck_controller)