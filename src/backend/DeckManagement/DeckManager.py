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
import threading
import time
from StreamDeck.DeviceManager import DeviceManager
from StreamDeck.Devices import StreamDeck
from StreamDeck.ImageHelpers import PILHelper
from loguru import logger as log
from usbmonitor import USBMonitor
import usb.core
import usb.util
import os

# Import own modules
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.SettingsManager import SettingsManager
from src.backend.DeckManagement.HelperMethods import get_sys_param_value, recursive_hasattr
from src.backend.DeckManagement.Subclasses.FakeDeck import FakeDeck

import gi
from gi.repository import GLib

# Import globals
import globals as gl

class DeckManager:
    def __init__(self):
        #TODO: Maybe outsource some objects
        self.deck_controller: list[DeckController] = []
        self.fake_deck_controller = []
        self.settings_manager = SettingsManager()
        self.page_manager = gl.page_manager
        # self.page_manager.load_pages()

        # USB monitor to detect connections and disconnections
        self.usb_monitor = USBMonitor()
        self.usb_monitor.start_monitoring(on_connect=self.on_connect, on_disconnect=self.on_disconnect)

        resume_thread = DetectResumeThread(self)
        return
        resume_thread.start() #TODO

    def load_decks(self):
        decks=DeviceManager().enumerate()
        for deck in decks:
            try:
                if not deck.is_open():
                    deck.open()
            except:
                log.error("Failed to open deck. Maybe it's already connected to another instance?")
                continue
            deck_controller = DeckController(self, deck)
            self.deck_controller.append(deck_controller)

        # Load fake decks
        self.load_fake_decks()

    def load_fake_decks(self):
        old_n_fake_decks = len(self.fake_deck_controller)
        n_fake_decks = int(gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json")).get("dev", {}).get("n-fake-decks", 0))

        if n_fake_decks > old_n_fake_decks:
            log.info(f"Loading {n_fake_decks - old_n_fake_decks} fake deck(s)")
            # Load difference in number of fake decks
            for controller in range(n_fake_decks - old_n_fake_decks):
                a = f"Fake Deck {len(self.fake_deck_controller)+1}"
                fake_deck = FakeDeck(serial_number = f"fake-deck-{len(self.fake_deck_controller)+1}", deck_type=f"Fake Deck {len(self.fake_deck_controller)+1}")
                self.add_newly_connected_deck(fake_deck, is_fake=True)

            # Update header deck switcher if the new deck is the only one
            if len(self.deck_controller) == 1 and False:
                # Check if ui is loaded - if not it will grab the controller automatically
                if recursive_hasattr(gl, "app.main_win.header_bar.deckSwitcher"):
                    gl.app.main_win.header_bar.deckSwitcher.set_show_switcher(True)

        elif n_fake_decks < old_n_fake_decks:
            # Remove difference in number of fake decks
            log.info(f"Removing {old_n_fake_decks - n_fake_decks} fake deck(s)")
            for controller in self.fake_deck_controller[-(old_n_fake_decks - n_fake_decks):]:
                # Remove controller from fake_decks
                self.fake_deck_controller.remove(controller)
                # Remove controller from main list
                self.deck_controller.remove(controller)
                # Remove deck page on stack
                gl.app.main_win.leftArea.deck_stack.remove_page(controller)

            # Update header deck switcher if there are no more decks
            if len(self.deck_controller) == 0 and False:
                # Check if ui is loaded - if not it will grab the controller automatically
                if recursive_hasattr(gl, "app.main_win.header_bar.deckSwitcher"):
                    gl.app.main_win.header_bar.deckSwitcher.set_show_switcher(False)
        if hasattr(gl.app, "main_win"):
            gl.app.main_win.check_for_errors()

    def on_connect(self, device_id, device_info):
        log.info(f"Device {device_id} with info: {device_info} connected")
        # Check if it is a supported device
        if device_info["ID_VENDOR"] != "Elgato":
            return
        
        self.connect_new_decks()

    def connect_new_decks(self):
        # Get already loaded deck serial ids
        loaded_deck_ids = []
        for controller in self.deck_controller:
            loaded_deck_ids.append(controller.deck.id())

        for deck in DeviceManager().enumerate():
            if deck.id() in loaded_deck_ids:
                continue
            # Add deck
            self.add_newly_connected_deck(deck)

        gl.app.main_win.check_for_errors()


    def on_disconnect(self, device_id, device_info):
        log.info(f"Device {device_id} with info: {device_info} disconnected")
        if device_info["ID_VENDOR"] != "Elgato":
            return

        for controller in self.deck_controller:
            if not controller.deck.connected():
                self.remove_controller(controller)

        gl.app.main_win.check_for_errors()

    def remove_controller(self, deck_controller: DeckController) -> None:
        self.deck_controller.remove(deck_controller)
        gl.app.main_win.leftArea.deck_stack.remove_page(deck_controller)
        deck_controller.delete()
        del deck_controller

    def add_newly_connected_deck(self, deck:StreamDeck, is_fake: bool = False):
        deck_controller = DeckController(self, deck)

        # Check if ui is loaded - if not it will grab the controller automatically
        if recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            # Add to deck stack
            GLib.idle_add(gl.app.main_win.leftArea.deck_stack.add_page, deck_controller)

        if recursive_hasattr(gl, "app.main_win.sidebar.page_selector"):
            GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)



        self.deck_controller.append(deck_controller)
        if is_fake:
            self.fake_deck_controller.append(deck_controller)

        if not recursive_hasattr(gl, "app.main_win."):
            return
        gl.app.main_win.check_for_errors()

    def close_all(self):
        log.info("Closing all decks")
        for controller in self.deck_controller:
            if controller.deck is None:
                return
            if not controller.deck.is_open():
                return
            
            log.info(f"Closing deck: {controller.deck.get_serial_number()}")
            controller.clear()
            controller.deck.close()

    def reset_all_decks(self):
        # Find all USB devices
        devices = usb.core.find(find_all=True)
        for device in devices:
            try:
                # Check if it's a StreamDeck
                if device.idVendor == DeviceManager.USB_VID_ELGATO and device.idProduct in [
                    DeviceManager.USB_PID_STREAMDECK_ORIGINAL,
                    DeviceManager.USB_PID_STREAMDECK_ORIGINAL_V2,
                    DeviceManager.USB_PID_STREAMDECK_MINI,
                    DeviceManager.USB_PID_STREAMDECK_XL,
                    DeviceManager.USB_PID_STREAMDECK_MK2,
                    DeviceManager.USB_PID_STREAMDECK_PEDAL,
                    DeviceManager.USB_PID_STREAMDECK_PLUS
                ]:
                    # Reset deck
                    usb.util.dispose_resources(device)
                    device.reset()
            except:
                log.error("Failed to reset deck, maybe it's already connected to another instance? Skipping...")

    def get_device_by_serial(self, serial: str):
        for deck in DeviceManager().enumerate():
            if not deck.is_open():
                try:
                    deck.open()
                except:
                    return
            if deck.get_serial_number() == serial:
                return deck

    def on_resumed(self):
        log.info("Resume from suspend detected, reloading decks...")
        time.sleep(2) # Give the kernel some time to handle the usb devices
        n_removed = 0
        for deck_controller in self.deck_controller:
            new_device = self.get_device_by_serial(deck_controller.serial_number())
            if new_device:
                log.info(f"Replacing deck")
                deck_controller.deck = new_device
                deck_controller.update_all_inputs()

                deck_controller.deck.set_key_callback(deck_controller.key_event_callback)
                deck_controller.deck.set_dial_callback(deck_controller.dial_event_callback)
                deck_controller.deck.set_touchscreen_callback(deck_controller.touchscreen_event_callback)

                # deck_controller.deck._setup_reader(deck_controller.deck._read)

            else:
                n_removed += 1
                log.info(f"Removing deck")
                deck_controller.deck.close()
                deck_controller.media_player.running = False
                self.remove_controller(deck_controller)

        if n_removed > 0:
            self.connect_new_decks()

class DetectResumeThread(threading.Thread):
    def __init__(self, deck_manager: DeckManager):
        super().__init__()
        self.deck_manager = deck_manager

        self.last_1 = time.time()
        self.last_2 = time.time()

    def run(self):
        while gl.threads_running:
            self.last_1 = time.time()
            if time.time() - self.last_1 >= 5 or time.time() - self.last_2 >= 5:
                self.deck_manager.on_resumed()
            self.last_2 = time.time()
            if time.time() - self.last_1 >= 5 or time.time() - self.last_2 >= 5:
                self.deck_manager.on_resumed()
            
            time.sleep(2)