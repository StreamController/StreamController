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
import types


# Import own modules
from src.backend.DeckManagement.BetterDeck import BetterDeck
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.SettingsManager import SettingsManager
from src.backend.DeckManagement.HelperMethods import get_sys_param_value, recursive_hasattr
from src.backend.DeckManagement.Subclasses.FakeDeck import FakeDeck

from src.backend.DeckManagement.beta_resume import _read as beta_read

import gi
gi.require_version("Xdp", "1.0")
from gi.repository import GLib, Xdp

# Import globals
import globals as gl

ELGATO_VENDOR_ID = "0fd9"

class DeckManager:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        self.physical_controllers: list[DeckController] = []
        self.virtual_controllers: list[DeckController] = []

        self.resume_from_suspend = gl.settings_manager.get_app_settings().get("system", {}).get("beta-resume-mode", True)

        self._usb_monitor: USBMonitor = USBMonitor()
        self._usb_monitor.start_monitoring(on_connect=self._on_deck_connected, on_disconnect=self._on_deck_disconnected)

        portal = Xdp.Portal.new()
        uses_flatpak = portal.running_under_flatpak()

        if uses_flatpak:
            GLib.timeout_add_seconds(2, self._on_deck_disconnected)

        resume_thread = DetectResumeThread(self)
        if not self.resume_from_suspend:
            resume_thread.start()

    def reset_all_decks(self):
        for deck in self.get_all_decks():
            deck.reset()

    def close_all_decks(self):
        for controller in self.get_all_controllers():
            if not controller.deck:
                continue

            if not controller.deck.is_open():
                continue

            controller.clear()
            controller.deck.close()

    def resume_suspend(self):
        """
        This will get called after the Operating System is being woken from suspend
        :return:
        """
        time.sleep(2)

        self.remove_all_physical_controllers()
        self.add_all_physical_decks()

    def load_all_decks(self):
        """
        Will load all decks and controllers. If there are currently controllers that exist they will be removed first.
        :return:
        """
        self.remove_all_controllers()

        if not gl.cli_args.skip_hardware_decks:
            self.add_all_physical_decks()

        self.add_all_virtual_decks()

    # Events

    def _on_deck_connected(self, device_id = None, device_info = None):
        """
        Gets called when a StreamDeck gets connected
        :param device_id: The device id of the StreamDeck
        :param device_info: Info about the device
        :return:
        """
        device_info = device_info or {}

        if device_info.get("ID_VENDOR_ID", "") != ELGATO_VENDOR_ID:
            return

        self.add_physical_deck_by_id(device_id)

    def _on_deck_disconnected(self, device_id, device_info: dict):
        """
        Gets called when a StreamDeck does not run under flatpak and is disconnected.
        :param device_id: The device id of the StreamDeck
        :param device_info: Info about the device
        :return:
        """
        log.info(f"Device {device_id} with info: {device_info} disconnected")

        if device_info["ID_VENDOR_ID"] != ELGATO_VENDOR_ID:
            return

        for controller in self.physical_controllers:
            if not controller.deck.connected():
                self.remove_physical_controller(controller)

        gl.app.main_win.check_for_errors()

    def _on_deck_disconnected_flatpak(self):
        """
        Gets called when the application runs under flatpak and a StreamDeck got removed
        :return:
        """
        for controller in self.physical_controllers[:]:  # Copy to avoid modification during iteration
            if not controller.deck.connected():
                self.remove_physical_controller(controller)
                gl.app.main_win.check_for_errors()
        return gl.threads_running  # Continue if app is still running

    # Add Deck

    def add_deck(self, deck: StreamDeck, is_virtual: bool = False):
        """
        Adds a new StreamDeck by creating a Controller for it
        :param deck: The StreamDeck to add
        :param is_virtual: Weather the StreamDeck is physical or not
        :return:
        """

        deck_controller = DeckController(self, deck)

        # Todo: Make it easier to call
        if recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            # Add to deck stack
            GLib.idle_add(gl.app.main_win.leftArea.deck_stack.add_page, deck_controller)

        if recursive_hasattr(gl, "app.main_win.sidebar.page_selector"):
            GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)

        if is_virtual:
            self.virtual_controllers.append(deck_controller)
        else:
            self.physical_controllers.append(deck_controller)

        if not recursive_hasattr(gl, "app.main_win."):
            return

        gl.app.main_win.check_for_errors()

    def add_all_physical_decks(self):
        """
        Adds all physical decks
        :return:
        """
        decks = self.get_all_decks()

        for deck in decks:
            try:
                if not deck.is_open():
                    deck.open(self.resume_from_suspend)
            except Exception as e:
                return

            self.add_deck(deck)

    def add_physical_deck_by_id(self, device_id, is_virtual: bool = False):
        """
        Adds a new StreamDeck by creating a Controller for it using the device id
        :param device_id: The device ID of the StreamDeck
        :param is_virtual: Weather the StreamDeck is physical or not
        :return:
        """

        deck_ids = self.get_physical_deck_ids()

        for deck in self.get_all_decks():
            if deck.id() in deck_ids:
                continue

            if deck.id() != device_id:
                continue

            self.add_deck(deck, is_virtual)

    def add_all_virtual_decks(self):
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))

        virtual_deck_amount = int(settings.get("dev", {}).get("n-fake-decks", 0))
        old_virtual_deck_amount = len(self.virtual_controllers)

        virtual_deck_difference = virtual_deck_amount - old_virtual_deck_amount

        if virtual_deck_difference > 0:
            for i in range(virtual_deck_difference):
                index = len(self.virtual_controllers) + 1
                name = f"Fake Deck {index}"

                virtual_deck = FakeDeck(
                    serial_number=f"fake-deck-{index}",
                    deck_type=name
                )
                self.add_deck(virtual_deck, True)
        elif virtual_deck_difference < 0:
            to_remove = self.virtual_controllers[virtual_deck_difference:]

            for controller in to_remove:
                self.remove_virtual_controller(controller)
                gl.app.main_win.leftArea.deck_stack.remove_page(controller)

        if hasattr(gl.app, "main_win"):
            gl.app.main_win.check_for_errors()

    # Remove Controller

    def remove_controller(self, controller: DeckController):
        """
        Tries removing a controller from the physical or virtual controllers
        :param controller: The controller to remove
        :return:
        """
        self.remove_physical_controller(controller)
        self.remove_virtual_controller(controller)

    def remove_all_controllers(self):
        """
        Removes all physical and virutal deck controllers
        :return:
        """
        self.remove_all_physical_controllers()
        self.remove_all_virtual_controllers()

    def remove_physical_controller(self, controller: DeckController):
        """
        Removes a physical deck controller
        :param controller: Deck controller to remove
        """
        if controller not in self.physical_controllers:
            return

        if controller.deck and controller.deck.is_open():
            controller.deck.close()

        self.physical_controllers.remove(controller)

    def remove_all_physical_controllers(self):
        """
        Removes all physical deck controllers
        :return:
        """
        for controller in self.physical_controllers:
            self.remove_physical_controller(controller)

    def remove_virtual_controller(self, controller: DeckController):
        """
        Removes a virtual deck controller
        :param controller: Deck controller to remove
        """
        if controller not in self.virtual_controllers:
            return

        if controller.deck.is_open():
            controller.deck.close()

        self.virtual_controllers.remove(controller)

    def remove_all_virtual_controllers(self):
        """
        Removes all virtual deck controllers
        :return:
        """
        for controller in self.virtual_controllers:
            self.remove_virtual_controller(controller)

    # Get Controllers

    def get_all_controllers(self) -> list[DeckController]:
        """
        Get all currently active controllers. Physical and Virtual controllers get combined
        :return: A combined list of physical and virtual controllers
        """
        return self.physical_controllers + self.virtual_controllers

    def get_physical_controllers(self):
        """
        Get all currently active physical controllers.
        :return: A list of physical controllers
        """
        return self.physical_controllers

    def get_virtual_controllers(self):
        """
        Get all currently active virtual controllers.
        :return: A list of virtual controllers
        """
        return self.virtual_controllers

    def get_controller_for_deck(self, deck: StreamDeck) -> DeckController | None:
        """
        Returns the corresponding controller depending on the deck. This can be either physical or virtual
        :param deck: The StreamDeck that the controller should be associated with
        :return: The actual controller that the deck belongs to
        """
        for controller in self.get_all_controllers():
            if controller.deck is deck:
                return controller

        return None

    # Get Ids

    def get_all_loaded_deck_ids(self) -> list:
        """
        Gets all deck ids for physical and virtual decks combined
        :return: A list containing physical and virtual deck ids
        """
        return [controller.get_device_id() for controller in self.get_all_controllers()]

    def get_physical_deck_ids(self) -> list:
        """
        Gets all physical deck ids
        :return: A list containing physical deck ids
        """
        return [controller.get_device_id() for controller in self.physical_controllers]

    def get_virtual_deck_ids(self) -> list:
        """
        Gets all virtual deck ids
        :return: A list containing virtual deck ids
        """
        return [controller.get_device_id() for controller in self.virtual_controllers]

    # Get Serial Numbers

    def get_all_loaded_serial_numbers(self) -> list:
        """
        Gets all serial numbers for physical and virtual decks combined
        :return: A list containing physical and virtual deck serial numbers
        """
        return [controller.get_serial_number() for controller in self.get_all_controllers()]

    def get_physical_deck_serials(self) -> list:
        """
        Gets serial numbers for all physical decks
        :return: A list containing physical deck serial numbers
        """
        return [controller.get_serial_number() for controller in self.physical_controllers]

    def get_virtual_deck_serials(self) -> list:
        """
        Gets serial numbers for all virtual decks
        :return: A list containing virtual deck serial numbers
        """
        return [controller.get_serial_number() for controller in self.virtual_controllers]

    # Get Deck

    @staticmethod
    def get_all_decks() -> list[StreamDeck]:
        """
        Gets all currently connected physical decks
        :return: A list containing all physical StreamDecks
        """
        return [deck for deck in DeviceManager().enumerate()]

    def get_deck_by_serial(self, serial: str) -> BetterDeck | None:
        """
        Gets a deck by serial number
        :param serial: Serial number of the deck
        :return: The StreamDeck that the serial number belongs to
        """
        for controller in self.get_all_controllers():
            if controller.deck.get_serial_number() != serial:
                continue

            return controller.deck
        return None

class DetectResumeThread(threading.Thread):
    def __init__(self, deck_manager: DeckManager):
        super().__init__(name="DetectResumeThread")
        self.deck_manager = deck_manager
        self._last_check = time.time()

    def run(self):
        while gl.threads_running:
            time.sleep(2)

            now = time.time()
            elapsed = now - self._last_check

            # If more than 5 seconds have passed, system likely resumed from sleep
            if elapsed > 5:
                self.deck_manager.resume_suspend()

            self._last_check = now
