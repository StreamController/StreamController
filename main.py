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
import setproctitle

setproctitle.setproctitle("StreamController")

# "install" patches
from src.patcher.patcher import Patcher
patcher = Patcher()
patcher.patch()

import os
import threading

from loguru import logger as log

import globals as gl

if not gl.IS_MAC:
    from dbus.mainloop.glib import DBusGMainLoop

from autostart import setup_autostart
from src.app import App
from src.backend.DeckManagement.DeckManager import DeckManager
from src.cli.dispatcher import handle_listing_commands, make_api_calls
from src.runtime.init import (
    config_logger,
    create_cache_folder,
    create_global_objects,
    quit_running,
    reset_all_decks,
    setup_migrations,
    update_assets,
)

main_path = os.path.abspath(os.path.dirname(__file__))
gl.MAIN_PATH = main_path


class Main:
    def __init__(self, application_id, deck_manager):
        # Launch gtk application
        self.app = App(application_id=application_id, deck_manager=deck_manager)

        gl.app = self.app

        self.app.run(gl.argparser.parse_args().app_args)


@log.catch
def load():
    log.info("Loading app")
    gl.deck_manager = DeckManager()
    gl.deck_manager.load_decks()
    gl.main = Main(application_id="com.core447.StreamController", deck_manager=gl.deck_manager)


@log.catch
def main():
    # Handle listing commands first (they don't need full initialization)
    if handle_listing_commands():
        return

    if make_api_calls():
        return

    gsk_render_env_var = os.environ.get("GSK_RENDERER")
    if gsk_render_env_var != "ngl":
        log.warning('Should you get an Gtk X11 error preventing the app from starting please add '
                    'GSK_RENDERER=ngl to your "/etc/environment" file')

    if not gl.IS_MAC:
        DBusGMainLoop(set_as_default=True)
        # Dbus
        quit_running()

    reset_all_decks()

    config_logger()

    setup_migrations()

    create_global_objects(main_path)

    app_settings = gl.settings_manager.get_app_settings()
    auto_start = app_settings.get("system", {}).get("autostart", True)
    setup_autostart(auto_start)

    create_cache_folder()
    threading.Thread(target=update_assets, name="update_assets").start()
    load()


if __name__ == "__main__":
    main()


log.trace("Reached end of main.py")
