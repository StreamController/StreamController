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

from globals import deck_manager
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

# Todos:
# When adding virtual devices over the UI you can break it.
# This is because we get 2+ calls to add devices, making it so both modify the list at the same time, resulting in a conflict.
# This can be resolved by checking if the method is resolved before starting another call

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
        """Reset all currently connected decks."""
        for deck in self.get_all_decks():
            deck.reset()

    def close_all_decks(self):
        """Close all physical and virtual decks if they are open."""
        for controller in self.get_all_controllers():
            if not controller.deck:
                continue

            if not controller.deck.is_open():
                continue

            controller.clear()
            controller.deck.close()

    def resume_suspend(self):
        """Handle actions required when the system resumes from suspend."""
        time.sleep(2)

        self.remove_all_physical_controllers()
        self.add_all_physical_decks()

    def load_all_decks(self):
        """Load all deck controllers after clearing any existing ones."""
        self.remove_all_controllers()

        if not gl.cli_args.skip_hardware_decks:
            self.add_all_physical_decks()

        self.add_all_virtual_decks()

    # Events

    def _on_deck_connected(self, device_id = None, device_info = None):
        """
        Callback for when a StreamDeck device is connected.

        :param: device_id: The unique ID of the connected device.
        :param: device_info: A dictionary containing device metadata.
        """
        device_info = device_info or {}

        if device_info.get("ID_VENDOR_ID", "") != ELGATO_VENDOR_ID:
            return

        self.add_physical_deck_by_id(device_id)

    def _on_deck_disconnected(self, device_id, device_info: dict):
        """
        Callback for when a StreamDeck device is disconnected.
        :param device_id: The unique ID of the disconnected device.
        :param device_info: A dictionary containing device metadata.
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
        """Callback for handling disconnections in a Flatpak environment."""
        for controller in self.physical_controllers[:]:  # Copy to avoid modification during iteration
            if not controller.deck.connected():
                self.remove_physical_controller(controller)
                gl.app.main_win.check_for_errors()
        return gl.threads_running  # Continue if app is still running

    # Add Deck

    def add_deck(self, deck: StreamDeck, is_virtual: bool = False):
        """
        Add a StreamDeck to the application by creating a controller for it.
        :param deck: The StreamDeck instance.
        :param is_virtual: Whether the deck is virtual (fake) or physical.
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
        """Detect and add all connected physical StreamDeck devices."""
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
        Add a physical StreamDeck using its device ID.
        :param device_id: The ID of the device to add.
        :param is_virtual: Whether to treat the deck as virtual (default: False).
        """

        deck_ids = self.get_physical_deck_ids()

        for deck in self.get_all_decks():
            if deck.id() in deck_ids:
                continue

            if deck.id() != device_id:
                continue

            self.add_deck(deck, is_virtual)

    def add_all_virtual_decks(self):
        """Add all virtual (fake) decks based on the application settings."""
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
        Remove a controller, whether physical or virtual.
        :param controller: The controller instance to remove.
        """
        self.remove_physical_controller(controller)
        self.remove_virtual_controller(controller)

    def remove_all_controllers(self):
        """Remove all controllers, both physical and virtual."""
        self.remove_all_physical_controllers()
        self.remove_all_virtual_controllers()

    def remove_physical_controller(self, controller: DeckController):
        """
        Remove a specific physical deck controller.
        :param controller: The controller to remove.
        """
        if controller not in self.physical_controllers:
            return

        if controller.deck and controller.deck.is_open():
            controller.deck.close()

        self.physical_controllers.remove(controller)

    def remove_all_physical_controllers(self):
        """Remove all physical deck controllers."""
        for controller in self.physical_controllers:
            self.remove_physical_controller(controller)

    def remove_virtual_controller(self, controller: DeckController):
        """
        Remove a specific virtual deck controller.
        :param controller: The controller to remove.
        """
        if controller not in self.virtual_controllers:
            return

        if controller.deck.is_open():
            controller.deck.close()

        self.virtual_controllers.remove(controller)

    def remove_all_virtual_controllers(self):
        """Remove all virtual deck controllers."""
        for controller in self.virtual_controllers:
            self.remove_virtual_controller(controller)

    # Get Controllers

    def get_all_controllers(self) -> list[DeckController]:
        """
        Get a combined list of all physical and virtual deck controllers.
        :return: List of all deck controllers.
        """
        return self.physical_controllers + self.virtual_controllers

    def get_physical_controllers(self):
        """Return a list of all active physical deck controllers."""
        return self.physical_controllers

    def get_virtual_controllers(self):
        """Return a list of all active virtual deck controllers."""
        return self.virtual_controllers

    def get_controller_for_deck(self, deck: StreamDeck) -> DeckController | None:
        """
        Retrieve the controller instance for a specific StreamDeck.
        :param deck: The StreamDeck object.
        :return: The associated controller, or None if not found.
        """
        for controller in self.get_all_controllers():
            if controller.deck is deck:
                return controller

        return None

    # Get Ids

    def get_all_loaded_deck_ids(self) -> list:
        """
        Retrieve all loaded deck device IDs.
        :return: List of device IDs from both physical and virtual decks.
        """
        return [controller.get_device_id() for controller in self.get_all_controllers()]

    def get_physical_deck_ids(self) -> list:
        """Return a list of device IDs for all physical decks."""
        return [controller.get_device_id() for controller in self.physical_controllers]

    def get_virtual_deck_ids(self) -> list:
        """Return a list of device IDs for all virtual decks."""
        return [controller.get_device_id() for controller in self.virtual_controllers]

    # Get Serial Numbers

    @staticmethod
    def get_all_serial_numbers() -> list:
        """
        Retrieve the serial numbers of all currently connected decks (not necessarily loaded).
        :return: List of serial numbers.
        """
        return [deck.get_serial_number() for deck in DeckManager.get_all_decks()]

    def get_all_loaded_serial_numbers(self) -> list:
        """
        Retrieve serial numbers from all currently loaded controllers.
        :return: List of serial numbers from physical and virtual decks.
        """
        return [controller.get_serial_number() for controller in self.get_all_controllers()]

    def get_physical_deck_serials(self) -> list:
        """Return serial numbers for all physical decks."""
        return [controller.get_serial_number() for controller in self.physical_controllers]

    def get_virtual_deck_serials(self) -> list:
        """Return serial numbers for all virtual decks."""
        return [controller.get_serial_number() for controller in self.virtual_controllers]

    # Get Deck

    @staticmethod
    def get_all_decks() -> list[StreamDeck]:
        """
        Retrieve all connected physical StreamDeck devices.
        :return: List of StreamDeck objects.
        """
        return [deck for deck in DeviceManager().enumerate()]

    @staticmethod
    def get_deck_by_serial(serial: str) -> BetterDeck | None:
        """
        Find a deck by its serial number.
        :param serial: The serial number to search for.
        :return: The matching StreamDeck instance, or None if not found.
        """
        for deck in DeckManager.get_all_decks():
            if deck.get_serial_number() != serial:
                continue
            return deck
        return None

    def get_deck_from_controller_by_serial(self, serial: str) -> BetterDeck | None:
        """
        Retrieve a deck from its controller using the serial number.
        :param serial: The serial number of the deck.
        :return: The deck object, or None if not found.
        """
        for controller in self.get_all_controllers():
            if controller.get_serial_number() != serial:
                continue
            return controller.deck
        return None

    @staticmethod
    def get_deck_by_id(device_id) -> BetterDeck | None:
        """
        Find a deck using its device ID.
        :param device_id: The device ID to search for.
        :return: The matching StreamDeck instance, or None if not found.
        """
        for deck in DeckManager.get_all_decks():
            if deck.id() != device_id:
                continue
            return deck
        return None

    def get_deck_from_controller_by_id(self, device_id) -> BetterDeck | None:
        """
        Retrieve a deck from its controller using the device ID.
        :param device_id: The ID of the deck.
        :return: The deck object, or None if not found.
        """
        for controller in self.get_all_controllers():
            if controller.get_device_id() != device_id:
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
