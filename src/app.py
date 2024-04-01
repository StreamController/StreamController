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
# Import gtk modules
import signal
import sys
import threading
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Xdp", "1.0")
from gi.repository import Gtk, Adw, Gdk, Gio, Xdp

# Import Python modules
from loguru import logger as log
import os

# Import own modules
from src.windows.mainWindow.mainWindow import MainWindow
from src.windows.AssetManager.AssetManager import AssetManager
from src.windows.Store.Store import Store
from src.windows.Shortcuts.Shortcuts import ShortcutsWindow
from src.windows.Onboarding.OnboardingWindow import OnboardingWindow
from src.windows.Permissions.FlatpakPermissionRequest import FlatpakPermissionRequestWindow

# Import globals
import globals as gl

class App(Adw.Application):
    def __init__(self, deck_manager, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager

        self.register_sigint_handler()

        self.connect("activate", self.on_activate)

        css_provider = Gtk.CssProvider()
        css_provider.load_from_path(os.path.join(gl.top_level_dir, "style.css"))
        Gtk.StyleContext.add_provider_for_display(Gdk.Display.get_default(), css_provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

        allow_white_mode = gl.settings_manager.get_app_settings().get("ui", {}).get("allow-white-mode", False)

        self.style_manager = self.get_style_manager()
        if allow_white_mode:
            self.style_manager.set_color_scheme(Adw.ColorScheme.PREFER_DARK)
        else:
            self.style_manager.set_color_scheme(Adw.ColorScheme.FORCE_DARK) # Not everything looks good in light mode at the moment #TODO

    def on_activate(self, app):
        log.trace("running: on_activate")
        self.main_win = MainWindow(application=app, deck_manager=self.deck_manager)
        if not gl.argparser.parse_args().b:
            self.main_win.present()

        self.show_onboarding()
        # self.show_permissions()

        self.shortcuts = ShortcutsWindow(app=app, application=app)
        # self.shortcuts.present()

        on_reopen_action = Gio.SimpleAction.new("reopen", None)
        on_reopen_action.connect("activate", self.on_reopen)
        self.add_action(on_reopen_action)

        log.success("Finished loading app")

    def on_reopen(self, *args, **kwargs):
        self.main_win.present()
        log.info("awake")

    def let_user_select_asset(self, default_path, callback_func=None, *callback_args, **callback_kwargs):
        self.asset_manager = AssetManager(application=self, main_window=self.main_win)
        gl.asset_manager = self.asset_manager
        self.asset_manager.show_for_path(default_path, callback_func, *callback_args, **callback_kwargs)

    def show_onboarding(self):
        if os.path.exists(os.path.join(gl.DATA_PATH, ".skip-onboarding")):
            return

        self.onboarding = OnboardingWindow(application=self, main_win=self.main_win)
        self.onboarding.show()

        # Disable onboarding for future sessions
        with open(os.path.join(gl.DATA_PATH, ".skip-onboarding"), "w") as f:
            f.write("")

    def show_permissions(self):
        portal = Xdp.Portal.new()
        if not portal.running_under_flatpak():
            return
        if os.path.exists(os.path.join(gl.DATA_PATH, ".skip-permissions")):
            return
        self.permissions = FlatpakPermissionRequestWindow(application=self, main_window=self.main_win)
        if hasattr(self, "onboarding"):
            if self.onboarding.is_visible():
                return
        self.permissions.present()

    def on_quit(self, *args):
        log.info("Quitting...")

        gl.window_grabber.poll = False

        # Force quit if normal quit is not possible
        timer = threading.Timer(6, self.force_quit)
        timer.setDaemon(True)
        timer.start()

        for ctrl in gl.deck_manager.deck_controller:
                ctrl.delete()

        gl.plugin_manager.loop_daemon = False
        log.debug("non-daemon threads:")
        for thread in threading.enumerate():
            if thread.daemon:
                continue
            log.debug(f"name: {thread.name}, id: {thread.ident} id2: {thread.native_id}")
            

        # Close all decks
        gl.deck_manager.close_all()
        # Stop timer
        timer.cancel()
        log.success("Stopped StreamController. Have a nice day!")
        sys.exit(0)

    def force_quit(self):
        log.info("Forcing quit...")
        os._exit(1)

    def register_sigint_handler(self):
        signal.signal(signal.SIGINT, self.on_quit)