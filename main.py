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
print(r""" _____ _                            _____             _             _ _           
/  ___| |                          /  __ \           | |           | | |          
\ `--.| |_ _ __ ___  __ _ _ __ ___ | /  \/ ___  _ __ | |_ _ __ ___ | | | ___ _ __ 
 `--. \ __| '__/ _ \/ _` | '_ ` _ \| |    / _ \| '_ \| __| '__/ _ \| | |/ _ \ '__|
/\__/ / |_| | |  __/ (_| | | | | | | \__/\ (_) | | | | |_| | | (_) | | |  __/ |   
\____/ \__|_|  \___|\__,_|_| |_| |_|\____/\___/|_| |_|\__|_|  \___/|_|_|\___|_|   
""")


# Import Python modules
import setproctitle

setproctitle.setproctitle("StreamController")

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
from src.backend.PageManagement.PageManagerBackend import PageManagerBackend
from src.backend.SettingsManager import SettingsManager
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.DeckManagement.HelperMethods import get_sys_args_without_param
from src.backend.IconPackManagement.IconPackManager import IconPackManager
from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
from src.backend.Store.StoreBackend import StoreBackend, NoConnectionError
from autostart import setup_autostart
from src.Signals.SignalManager import SignalManager
from src.backend.WindowGrabber.WindowGrabber import WindowGrabber
from src.backend.GnomeExtensions import GnomeExtensions
from src.backend.PermissionManagement.FlatpakPermissionManager import FlatpakPermissionManager
from src.backend.LockScreenManager.LockScreenManager import LockScreenManager
from src.tray import TrayIcon

# Migration
from src.backend.Migration.MigrationManager import MigrationManager
from src.backend.Migration.Migrators.Migrator_1_5_0 import Migrator_1_5_0
from src.backend.Migration.Migrators.Migrator_1_5_0_beta_5 import Migrator_1_5_0_beta_5

# Import globals
import globals as gl

def write_logs(record):
    gl.logs.append(record)

def config_logger():
    log.remove()
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

    log.info("Loading app")
    gl.deck_manager = DeckManager()
    gl.deck_manager.load_decks()
    gl.main = Main(application_id="com.core447.StreamController", deck_manager=gl.deck_manager)

@log.catch
def create_cache_folder():
    os.makedirs(os.path.join(gl.DATA_PATH, "cache"), exist_ok=True)

def create_global_objects():
    # Setup locales
    gl.tray_icon = TrayIcon()
    # gl.tray_icon.run_detached()

    gl.lm = LocaleManager(csv_path=os.path.join("locales", "locales.csv"))
    gl.lm.set_to_os_default()
    gl.lm.set_fallback_language("en_US")

    gl.flatpak_permission_manager = FlatpakPermissionManager()

    gl.gnome_extensions = GnomeExtensions()

    gl.settings_manager = SettingsManager()

    gl.signal_manager = SignalManager()

    gl.media_manager = MediaManager()
    gl.asset_manager_backend = AssetManagerBackend()
    gl.page_manager = PageManagerBackend(gl.settings_manager)
    gl.page_manager.remove_old_backups()
    gl.page_manager.backup_pages()
    gl.icon_pack_manager = IconPackManager()
    gl.wallpaper_pack_manager = WallpaperPackManager()

    # Store
    gl.store_backend = StoreBackend()

    # Plugin Manager
    gl.plugin_manager = PluginManager()
    gl.plugin_manager.load_plugins(show_notification=True)
    gl.plugin_manager.generate_action_index()

    gl.window_grabber = WindowGrabber()
    gl.lock_screen_detector = LockScreenManager()

    
    # gl.dekstop_grabber = DesktopGrabber()

@log.catch
def update_assets():
    settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
    auto_update = settings.get("store", {}).get("auto-update", True)

    if gl.argparser.parse_args().devel:
        auto_update = False

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
                DeviceManager.USB_PID_STREAMDECK_PEDAL,
                DeviceManager.USB_PID_STREAMDECK_PLUS
            ]:
                # Reset deck
                usb.util.dispose_resources(device)
                device.reset()
        except:
            log.error("Failed to reset deck, maybe it's already connected to another instance? Skipping...")

def quit_running():
    log.info("Checking if another instance is running")
    session_bus = dbus.SessionBus()
    obj: dbus.BusObject = None
    action_interface: dbus.Interface = None
    try:
        obj = session_bus.get_object("com.core447.StreamController", "/com/core447/StreamController")
        action_interface = dbus.Interface(obj, "org.gtk.Actions")
    except dbus.exceptions.DBusException as e:
        log.info("No other instance running, continuing")
        log.error(e)
    except ValueError as e:
        log.info("The last instance has not been properly closed, continuing... This may cause issues")

    if None not in [obj, action_interface]:
        if gl.argparser.parse_args().close_running:
            log.info("Closing running instance")
            try:
                action_interface.Activate("quit", [], [])
            except dbus.exceptions.DBusException as e:
                if "org.freedesktop.DBus.Error.NoReply" in str(e):
                    log.error("Could not close running instance: " + str(e))
                    sys.exit(0)
            time.sleep(5)

        else:
            action_interface.Activate("reopen", [], [])
            log.info("Already running, exiting")
            sys.exit(0)

def make_api_calls():
    if not gl.argparser.parse_args().change_page:
        return
    
    session_bus = dbus.SessionBus()
    obj: dbus.BusObject = None
    action_interface: dbus.Interface = None
    try:
        obj = session_bus.get_object("com.core447.StreamController", "/com/core447/StreamController")
        action_interface = dbus.Interface(obj, "org.gtk.Actions")
    except dbus.exceptions.DBusException as e:
        obj = None
    except ValueError as e:
        obj = None

    for serial_number, page_name in gl.argparser.parse_args().change_page:
        if None in [obj, action_interface] or gl.argparser.parse_args().close_running:
            gl.api_page_requests[serial_number] = page_name
        else:
            # Other instance is running - call dbus interfaces
            action_interface.Activate("change_page", [[serial_number, page_name]], [])


    
@log.catch
def main():
    DBusGMainLoop(set_as_default=True)
    # Dbus
    make_api_calls()
    quit_running()

    reset_all_decks()

    migration_manager = MigrationManager()
    # Add migrators
    migration_manager.add_migrator(Migrator_1_5_0())
    migration_manager.add_migrator(Migrator_1_5_0_beta_5())
    # Run migrators
    migration_manager.run_migrators()

    create_global_objects()

    app_settings = gl.settings_manager.get_app_settings()
    app_settings = gl.settings_manager.get_app_settings()
    auto_start = app_settings.get("system", {}).get("autostart", True)
    setup_autostart(auto_start)
    
    create_cache_folder()
    threading.Thread(target=update_assets, name="update_assets").start()
    load()

if __name__ == "__main__":
    main()


log.trace("Reached end of main.py")