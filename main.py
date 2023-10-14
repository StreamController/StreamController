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

def config_logger():
    log.remove(0)
    # Create log files
    log.add("logs/logs.log", rotation="3 days", backtrace=True, diagnose=True, level="TRACE")
    # Set min level to print
    log.add(sys.stderr, level="DEBUG")

class Main:
    def __init__(self, application_id, deck_manager):
        # Launch gtk application
        app = App(application_id=application_id, deck_manager=deck_manager)
        app.run(sys.argv)

@log.catch
def load():
    config_logger()
    log.info("Loading app")
    deck_manager = DeckManager()
    deck_manager.load_decks()
    Main(application_id="com.core447.StreamController", deck_manager=deck_manager)

@log.catch
def create_cache_folder():
    if not os.path.exists("cache"):
        os.makedirs("cache")


if __name__ == "__main__":
    create_cache_folder()
    load()


log.trace("Reached end of main.py")