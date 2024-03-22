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
import sys
from loguru import logger as log
import os
import time
import asyncio
import threading
import dbus
import dbus.service
import argparse
import usb.core
import usb.util
from StreamDeck.DeviceManager import DeviceManager
from dbus.mainloop.glib import DBusGMainLoop

# Import own modules
from src.app import App
from src.backend.DeckManagement.DeckManager import DeckManager
from locales.LocaleManager import LocaleManager
from src.backend.MediaManager import MediaManager
from src.backend.AssetManagerBackend import AssetManagerBackend
from src.backend.PageManagement.PageManager import PageManager
from src.backend.SettingsManager import SettingsManager
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.DeckManagement.HelperMethods import get_sys_args_without_param
from src.backend.IconPackManagement.IconPackManager import IconPackManager
from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
from src.windows.Store.StoreBackend import StoreBackend, NoConnectionError
from autostart import setup_autostart
from src.Signals.SignalManager import SignalManager
from src.backend.DesktopGrabber import DesktopGrabber

# Import globals
import globals as gl

def write_logs(record):
    gl.logs.append(record)

def config_logger():
    log.remove(0)
    # Create log files
    log.add(os.path.join(gl.DATA_PATH, "logs/logs.log"), rotation="3 days", backtrace=True, diagnose=True, level="TRACE")
    # Set min level to print
    log.add(sys.stderr, level="TRACE")
    log.add(write_logs, level="TRACE")

class Main:
    def __init__(self, application_id, deck_manager):
        # Launch gtk application
        self.app = App(application_id=application_id, deck_manager=deck_manager)

        gl.app = self.app

        self.app.run(gl.argparser.parse_args().app_args)

@log.catch
def load():
    config_logger()
    # Setup locales
    localeManager = LocaleManager(locales_path="locales")
    localeManager.set_to_os_default()
    localeManager.set_fallback_language("en_US")
    gl.lm = localeManager

    log.info("Loading app")
    gl.deck_manager = DeckManager()
    gl.deck_manager.load_decks()
    gl.main = Main(application_id="com.core447.StreamController", deck_manager=gl.deck_manager)

@log.catch
def create_cache_folder():
    os.makedirs(os.path.join(gl.DATA_PATH, "cache"), exist_ok=True)

def create_global_objects():
    # Argparser
    gl.argparser = argparse.ArgumentParser()
    gl.argparser.add_argument("-b", help="Open in background", action="store_true")
    gl.argparser.add_argument("app_args", nargs="*")

    gl.settings_manager = SettingsManager()

    gl.signal_manager = SignalManager()

    gl.media_manager = MediaManager()
    gl.asset_manager_backend = AssetManagerBackend()
    gl.page_manager = PageManager(gl.settings_manager)
    gl.icon_pack_manager = IconPackManager()
    gl.wallpaper_pack_manager = WallpaperPackManager()

    # Store
    gl.store_backend = StoreBackend()

    # Plugin Manager
    gl.plugin_manager = PluginManager()
    gl.plugin_manager.load_plugins()
    gl.plugin_manager.generate_action_index()

    
    # gl.dekstop_grabber = DesktopGrabber()

def update_assets():
    settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
    auto_update = settings.get("store", {}).get("auto-update", True)
    if not auto_update:
        log.info("Skipping store asset update")
        return

    log.info("Updating store assets")
    start = time.time()
    number_of_installed_updates = asyncio.run(gl.store_backend.update_everything())
    if isinstance(number_of_installed_updates, NoConnectionError):
        log.error("Failed to update store assets")
        if hasattr(gl.app, "main_win"):
            gl.app.main_win.show_error_toast("Failed to update store assets")
        return
    log.info(f"Updating {number_of_installed_updates} store assets took {time.time() - start} seconds")

    if number_of_installed_updates <= 0:
        return

    # Show toast in ui
    if hasattr(gl.app, "main_win"):
        gl.app.main_win.show_info_toast(f"{number_of_installed_updates} assets updated")

@log.catch
def reset_all_decks():
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
            ]:
                # Reset deck
                usb.util.dispose_resources(device)
                device.reset()
        except:
            log.error("Failed to reset deck, maybe it's already connected to another instance? Skipping...")

if __name__ == "__main__":
    # Dbus
    log.info("Checking if another instance is running")
    DBusGMainLoop(set_as_default=True)
    session_bus = dbus.SessionBus()
    try:
        obj = session_bus.get_object("com.core447.StreamController", "/com/core447/StreamController")
        action_interface = dbus.Interface(obj, "org.gtk.Actions")
        action_interface.Activate("reopen", [], [])
        log.info("Already running, exiting")
        exit()
    except dbus.exceptions.DBusException as e:
        print(e)
        log.info("No other instance running, continuing")

    reset_all_decks()

    setup_autostart()

    create_global_objects()
    create_cache_folder()
    threading.Thread(target=update_assets).start()
    load()


log.trace("Reached end of main.py")