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
from StreamDeck.ProductIDs import USBProductIDs, USBVendorIDs
from StreamDeck.ImageHelpers import PILHelper
from loguru import logger as log
from usbmonitor import USBMonitor
import usb.core
import usb.util
import os


# Import own modules
from src.backend.DeckManagement.Subclasses.RemoteDeckManager import RemoteDeckManager
from src.backend.DeckManagement.Subclasses.RemoteDeck import RemoteDeck
from StreamDeck.Devices.RotatedDeck import RotatedDeck
from src.backend.DeckManagement.DeckController import DeckController
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.SettingsManager import SettingsManager
from src.backend.DeckManagement.HelperMethods import get_sys_param_value, recursive_hasattr
from src.backend.DeckManagement.Subclasses.FakeDeck import DEFAULT_FAKE_DECK_TYPE, FakeDeck

# Import globals first to get IS_MAC
import globals as gl

import gi
from gi.repository import GLib

if not gl.IS_MAC:
    gi.require_version("Xdp", "1.0")
    from gi.repository import Xdp

ELGATO_VENDOR_ID = "0fd9"


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

        self.flatpak_disconnect_thread = FlatpakDeckDisconnectThread(self)

        self.flatpak = False
        if not gl.IS_MAC:
            portal = Xdp.Portal.new()
            self.flatpak = portal.running_under_flatpak() # on_disconnect is not working under Flatpak - we use a separate thread #TODO: Find a better solution
        if self.flatpak:
            log.info("Running under Flatpak. Using separate thread to detect device disconnection.")
            self.flatpak_disconnect_thread.start()

        self.beta_resume_mode = gl.settings_manager.get_app_settings().get("system", {}).get("beta-resume-mode", True)
        log.info(f"Beta resume mode: {self.beta_resume_mode}")

        resume_thread = DetectResumeThread(self)
        if not self.beta_resume_mode:
            resume_thread.start()

        self.remote_deck_manager = RemoteDeckManager(self)
        if gl.settings_manager.get_app_settings().get("dev", {}).get("n-remote-decks", 0) > 0:
            self.load_remote_decks()

    def check_for_errors_if_window_ready(self):
        if recursive_hasattr(gl, "app.main_win.check_for_errors"):
            gl.app.main_win.check_for_errors()

    def load_remote_decks(self):
        print(" load remote decks")
        self.remote_deck_manager.start()
        for controller in self.remote_deck_manager.deck_controllers:
            if controller in self.deck_controller:
                continue

            self.deck_controller.append(controller)
            if recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
                # Add to deck stack
                for controller in self.remote_deck_manager.deck_controllers:
                    GLib.idle_add(gl.app.main_win.leftArea.deck_stack.add_page, controller)

        if recursive_hasattr(gl, "app.main_win.sidebar.page_selector"):
            GLib.idle_add(gl.app.main_win.sidebar.page_selector.update)

        self.check_for_errors_if_window_ready()

    def remove_remote_decks(self):
        for controller in self.remote_deck_manager.deck_controllers:
            self.remove_controller(controller)
        self.check_for_errors_if_window_ready()
        self.remote_deck_manager.stop()

    def load_decks(self):
        if not gl.argparser.parse_args().skip_load_hardware_decks:
            self.load_hardware_decks()

        self.load_fake_decks()
    
    def load_hardware_decks(self):
        if gl.IS_MAC:
            return
        decks=DeviceManager().enumerate()
        for deck in decks:
            try:
                if not deck.is_open():
                    deck.open(self.beta_resume_mode)
            except:
                log.error("Failed to open deck. Maybe it's already connected to another instance?")
                continue
            deck_controller = DeckController(self, deck)
            self.deck_controller.append(deck_controller)

    def get_fake_deck_types(self) -> list[str]:
        """
        One deck type per configured fake deck. Decks without a configured type
        (eg. right after the number of fake decks was increased) fall back to
        the default model.
        """
        dev_settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json")).get("dev", {})
        n_fake_decks = int(dev_settings.get("n-fake-decks", 0))
        configured_types = dev_settings.get("fake-deck-types", [])

        types: list[str] = []
        for i in range(n_fake_decks):
            deck_type = configured_types[i] if i < len(configured_types) else None
            types.append(deck_type or DEFAULT_FAKE_DECK_TYPE)

        return types

    def load_fake_decks(self):
        """
        Syncs the loaded fake decks with the settings - both their number and
        their deck types. Called whenever one of those settings changes, so no
        restart is needed.
        """
        types = self.get_fake_deck_types()

        # Everything up to the first deck whose type changed can stay - the ones
        # behind it have to be rebuilt because the serial numbers are tied to the
        # position in the list
        n_keep = min(len(types), len(self.fake_deck_controller))
        for i, controller in enumerate(self.fake_deck_controller):
            # controller.deck is a RotatedDeck, the fake deck itself sits behind it
            fake_deck = getattr(controller.deck, "deck", controller.deck)
            if i >= len(types) or fake_deck.model_name != types[i]:
                n_keep = i
                break

        for controller in self.fake_deck_controller[n_keep:]:
            log.info(f"Removing fake deck {controller.deck.get_serial_number()}")
            # Remove controller from fake_decks
            self.fake_deck_controller.remove(controller)
            # Remove controller from main list
            self.deck_controller.remove(controller)
            # Remove deck page on stack
            if recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
                gl.app.main_win.leftArea.deck_stack.remove_page(controller)

        for i in range(n_keep, len(types)):
            log.info(f"Loading fake deck {i+1} of type {types[i]}")
            fake_deck = FakeDeck(serial_number=f"fake-deck-{i+1}", deck_type=types[i])
            self.add_newly_connected_deck(fake_deck, is_fake=True)

        self.check_for_errors_if_window_ready()

    def on_connect(self, device_id, device_info):
        log.info(f"Device {device_id} with info: {device_info} connected")
        # Check if it is a supported device
        if device_info["ID_VENDOR_ID"] != ELGATO_VENDOR_ID:
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

        self.check_for_errors_if_window_ready()


    def on_disconnect(self, device_id, device_info):
        log.info(f"Device {device_id} with info: {device_info} disconnected")
        if device_info["ID_VENDOR_ID"] != ELGATO_VENDOR_ID:
            return

        for controller in self.deck_controller:
            if not controller.deck.connected():
                self.remove_controller(controller)

        self.check_for_errors_if_window_ready()

    def remove_controller(self, deck_controller: DeckController) -> None:
        self.deck_controller.remove(deck_controller)
        if recursive_hasattr(gl, "app.main_win.leftArea.deck_stack"):
            # remove_controller() is called from non-GTK threads (e.g.
            # FlatpakDeckDisconnectThread, udev callbacks); route the GTK call
            # through the main loop like add_newly_connected_deck() does for
            # add_page().
            GLib.idle_add(gl.app.main_win.leftArea.deck_stack.remove_page, deck_controller)
        deck_controller.delete()

        # delete() stops the reader thread, which up to now was the only thing that
        # ever closed the device on a disconnect. A device left open makes libusb
        # abort once the process exits (see issue #631)
        try:
            if deck_controller.deck is not None and deck_controller.deck.is_open():
                deck_controller.deck.close()
        except Exception as e:
            log.error(f"Failed to close deck of removed controller. Error: {e}")

        del deck_controller

    def get_controller_for_deck(self, deck: StreamDeck) -> DeckController | None:
        for controller in self.deck_controller:
            if controller.deck is deck:
                return controller

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
        self.check_for_errors_if_window_ready()

    def close_all(self):
        log.info("Closing all decks")
        for controller in self.deck_controller:
            # continue, not return - one deck that is already gone must not keep
            # the remaining ones open. An open HID device at interpreter exit makes
            # libusb abort (see issue #631)
            if controller.deck is None:
                continue
            if not controller.deck.is_open():
                continue

            try:
                log.info(f"Closing deck: {controller.deck.get_serial_number()}")
            except Exception as e:
                log.error(f"Failed to get serial number of deck to close. Error: {e}")

            # The reader thread has to be gone before the device is closed,
            # see DeckController.stop_reader()
            controller.stop_reader()

            try:
                controller.clear()
            except Exception as e:
                log.error(f"Failed to clear deck before closing it. Error: {e}")

            try:
                controller.deck.close()
            except Exception as e:
                log.error(f"Failed to close deck. Error: {e}")

    def stop_usb_monitoring(self):
        self.usb_monitor.stop_monitoring(timeout=2)

    def reset_all_decks(self):
        # Find all USB devices
        devices = usb.core.find(find_all=True)
        for device in devices:
            try:
                # Check if it's a StreamDeck
                if device.idVendor == USBVendorIDs.USB_VID_ELGATO and device.idProduct in [
                    USBProductIDs.USB_PID_STREAMDECK_ORIGINAL,
                    USBProductIDs.USB_PID_STREAMDECK_ORIGINAL_V2,
                    USBProductIDs.USB_PID_STREAMDECK_MINI,
                    USBProductIDs.USB_PID_STREAMDECK_XL,
                    USBProductIDs.USB_PID_STREAMDECK_MK2,
                    USBProductIDs.USB_PID_STREAMDECK_PEDAL,
                    USBProductIDs.USB_PID_STREAMDECK_PLUS,
                    USBProductIDs.USB_PID_STREAMDECK_NEO
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
                current_rotation = deck_controller.deck.get_rotation()
                deck_controller.deck = RotatedDeck(new_device, current_rotation)
                # The device was just reset, so what we believe is on it is stale -
                # without this, the page reload below skips every key whose image is unchanged
                deck_controller.invalidate_render_caches()

                deck_controller.deck.set_key_callback(deck_controller.key_event_callback)
                deck_controller.deck.set_dial_callback(deck_controller.dial_event_callback)
                deck_controller.deck.set_touchscreen_callback(deck_controller.touchscreen_event_callback)

                # Reset cached signatures so resume always refreshes media/background state.
                if hasattr(deck_controller, "_last_background_signature"):
                    deck_controller._last_background_signature = None
                if hasattr(deck_controller, "_last_screensaver_signature"):
                    deck_controller._last_screensaver_signature = None

                # Force reload of current page to restore backgrounds/screensaver/media on device.
                if deck_controller.active_page is not None:
                    deck_controller.load_page(
                        deck_controller.active_page,
                        allow_reload=True,
                        force_background_reload=True,
                    )
                else:
                    deck_controller.load_default_page()

                # deck_controller.deck._setup_reader(deck_controller.deck._read)

            else:
                n_removed += 1
                log.info(f"Removing deck")
                deck_controller.deck.close()
                deck_controller.media_player.running = False
                self.remove_controller(deck_controller)

        if n_removed > 0:
            self.connect_new_decks()

    def get_connected_serials(self) -> list[str]:
        return [controller.serial_number() for controller in self.deck_controller]


class FlatpakDeckDisconnectThread(threading.Thread):
    def __init__(self, deck_manager: DeckManager):
        super().__init__(name="FlatpakDeckDisconnectThread")
        self.deck_manager = deck_manager

    def run(self):
        while gl.threads_running:
            time.sleep(2)
            for controller in self.deck_manager.deck_controller:
                if not controller.deck.connected():
                    self.deck_manager.remove_controller(controller)
                    self.deck_manager.check_for_errors_if_window_ready()

class DetectResumeThread(threading.Thread):
    def __init__(self, deck_manager: DeckManager):
        super().__init__(name="DetectResumeThread")
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
