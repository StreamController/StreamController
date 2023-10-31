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

# Import own modules
from src.app import App
from src.backend.DeckManagement.DeckManager import DeckManager
from locales.LocaleManager import LocaleManager
from src.backend.MediaManager import MediaManager
from src.backend.AssetManager import AssetManager
from src.backend.PageManagement.PageManager import PageManager
from src.backend.SettingsManager import SettingsManager
from src.backend.PluginManager.PluginManager import PluginManager

# Import globals
import globals as gl

def config_logger():
    log.remove(0)
    # Create log files
    log.add("logs/logs.log", rotation="3 days", backtrace=True, diagnose=True, level="TRACE")
    # Set min level to print
    log.add(sys.stderr, level="TRACE")

class Main:
    def __init__(self, application_id, deck_manager):
        # Launch gtk application
        self.app = App(application_id=application_id, deck_manager=deck_manager)

        gl.app = self.app

        self.app.run(sys.argv)

@log.catch
def load():
    config_logger()
    # Setup locales
    localeManager = LocaleManager()
    localeManager.set_to_os_default()
    gl.lm = localeManager

    log.info("Loading app")
    gl.deck_manager = DeckManager()
    gl.deck_manager.load_decks()
    gl.main = Main(application_id="com.core447.StreamController", deck_manager=gl.deck_manager)

@log.catch
def create_cache_folder():
    if not os.path.exists("cache"):
        os.makedirs("cache")

def create_global_objects():
    # Plugin Manager
    gl.plugin_manager = PluginManager()
    gl.plugin_manager.load_plugins()
    gl.plugin_manager.generate_action_index()

    gl.media_manager = MediaManager()
    gl.asset_manager = AssetManager()
    gl.settings_manager = SettingsManager()
    gl.page_manager = PageManager(gl.settings_manager)


if __name__ == "__main__":
    create_global_objects()
    create_cache_folder()
    load()


log.trace("Reached end of main.py")