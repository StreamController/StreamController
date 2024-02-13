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
from dbus.mainloop.glib import DBusGMainLoop

# Import own modules
from src.app import App
from src.backend.DeckManagement.DeckManager import DeckManager
from locales.LocaleManager import LocaleManager
from src.backend.MediaManager import MediaManager
from src.backend.AssetManager import AssetManager
from src.backend.PageManagement.PageManager import PageManager
from src.backend.SettingsManager import SettingsManager
from src.backend.PluginManager.PluginManager import PluginManager
from src.backend.DeckManagement.HelperMethods import get_sys_args_without_param
from src.backend.IconPackManagement.IconPackManager import IconPackManager
from src.backend.WallpaperPackManagement.WallpaperPackManager import WallpaperPackManager
from src.windows.Store.StoreBackend import StoreBackend
from autostart import setup_autostart

# Import globals
import globals as gl

def config_logger():
    log.remove(0)
    # Create log files
    log.add(os.path.join(gl.DATA_PATH, "logs/logs.log"), rotation="3 days", backtrace=True, diagnose=True, level="TRACE")
    # Set min level to print
    log.add(sys.stderr, level="TRACE")

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
    # localeManager.set_fallback_language("en_US")
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


    gl.media_manager = MediaManager()
    gl.asset_manager = AssetManager()
    gl.settings_manager = SettingsManager()
    gl.page_manager = PageManager(gl.settings_manager)
    gl.icon_pack_manager = IconPackManager()
    gl.wallpaper_pack_manager = WallpaperPackManager()

    # Store
    gl.store_backend = StoreBackend()

    # Plugin Manager
    gl.plugin_manager = PluginManager()
    gl.plugin_manager.load_plugins()
    gl.plugin_manager.generate_action_index()

def update_assets():
    settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
    auto_update = settings.get("store", {}).get("auto-update", True)
    if not auto_update:
        log.info("Skipping store asset update")
        return

    log.info("Updating store assets")
    start = time.time()
    asyncio.run(gl.store_backend.update_everything())
    log.info(f"Updating store assets took {time.time() - start} seconds")

if __name__ == "__main__":
    # Dbus
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

    setup_autostart(True)

    create_global_objects()
    create_cache_folder()
    log.info("Starting thread: update_assets")
    threading.Thread(target=update_assets).start()
    load()


log.trace("Reached end of main.py")