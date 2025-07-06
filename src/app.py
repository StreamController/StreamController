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
# Import python modules
from ast import main
import multiprocessing
import signal
import sys
import threading
import asyncio
import gi

from src.windows.Store.ResponsibleNotesDialog import ResponsibleNotesDialog
from src.windows.Donate.DonateWindow import DonateWindow
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
gi.require_version("Xdp", "1.0")
from gi.repository import Gtk, Adw, Gdk, Gio, Xdp, GLib

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

from src.Signals import Signals

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

        icon_theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        icon_theme.add_search_path(os.path.join(gl.top_level_dir, "Assets", "icons"))

        app_settings = gl.settings_manager.get_app_settings()
        
        allow_white_mode = app_settings.get("ui", {}).get("allow-white-mode", False)

        # increment app launches
        app_settings.setdefault("general", {})
        app_settings["general"]["app-launches"] = app_settings["general"].get("app-launches", 0) + 1
        gl.settings_manager.save_app_settings(app_settings)

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
        # self.show_donate()
        self.main_win.on_finished.append(self.show_donate())
        # self.show_permissions()

        self.shortcuts = ShortcutsWindow(app=app, application=app)
        # self.shortcuts.present()

        on_reopen_action = Gio.SimpleAction.new("reopen", None)
        on_reopen_action.connect("activate", self.on_reopen)
        self.add_action(on_reopen_action)

        on_quit_action = Gio.SimpleAction.new("quit", None)
        on_quit_action.connect("activate", self.on_quit)
        self.add_action(on_quit_action)

        self.add_signals()

        # Do tasks
        gl.app = self
        for task in gl.app_loading_finished_tasks:
            if callable(task):
                task()
        change_page_action = Gio.SimpleAction.new("change_page", GLib.VariantType("as")) # as = array of strings
        change_page_action.connect("activate", self.on_change_page)
        self.add_action(change_page_action)

        log.success("Finished loading app")

    def on_reopen(self, *args, **kwargs):
        self.main_win.present()
        log.info("awake")

        self.show_donate(ignore_background_launch=True)

    def let_user_select_asset(self, default_path, callback_func=None, *callback_args, **callback_kwargs):
        self.asset_manager = AssetManager(application=self, main_window=self.main_win)
        gl.asset_manager = self.asset_manager
        self.asset_manager.show_for_path(default_path, callback_func, *callback_args, **callback_kwargs)

    def show_donate(self, ignore_background_launch: bool = False):
        if not ignore_background_launch and gl.argparser.parse_args().b:
            return
        if gl.showed_donate_window:
            return
        gl.showed_donate_window = True

        app_settings = gl.settings_manager.get_app_settings()
        if not app_settings.get("general", {}).get("show-donate-window", True) or app_settings.get("general", {}).get("app-launches", 0) < 3 or hasattr(self, "onboarding") or hasattr(self, "permissions"):
            return

        self.donate = DonateWindow()
        self.donate.present(self.main_win)

    def show_onboarding(self):
        if gl.argparser.parse_args().b:
            return
        if os.path.exists(os.path.join(gl.DATA_PATH, ".skip-onboarding")):
            return

        self.onboarding = OnboardingWindow(application=self, main_win=self.main_win)
        self.onboarding.present(self.main_win)

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

        self.main_win.destroy()

        gl.signal_manager.trigger_signal(Signals.AppQuit)

        gl.threads_running = False

        # Force quit if normal quit is not possible
        timer = threading.Timer(6, self.force_quit)
        timer.name = "force_quit_timer"
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

        for child in multiprocessing.active_children():
            child.terminate()

        gl.tray_icon.stop()

        # Close all decks
        gl.deck_manager.close_all()
        # Stop timer
        log.success("Stopped StreamController. Have a nice day!")
        sys.exit(0)

    def force_quit(self):
        log.info("Forcing quit...")
        os._exit(1)

    def register_sigint_handler(self):
        signal.signal(signal.SIGINT, self.on_quit)

    def add_signals(self):
        self.update_all_assets_action = Gio.SimpleAction.new("update-all-assets", None)
        self.update_all_assets_action.connect("activate", self.update_all_assets)
        self.add_action(self.update_all_assets_action)

        self.install_plugin_action = Gio.SimpleAction.new("install-plugin", GLib.VariantType("s"))
        self.install_plugin_action.connect("activate", self.install_plugin)
        self.add_action(self.install_plugin_action)

    def update_all_assets(self, *args, **kwargs):
        threading.Thread(target=self._update_all_assets, name="update_all_assets").start()

    @log.catch
    def _update_all_assets(self):
        self.set_working(True)

        asyncio.run(gl.store_backend.update_everything())

        self.set_working(False)

        gl.app.send_notification("dialog-information-symbolic", "All assets updated", "All assets have been updated")

    def install_plugin(self, action, plugin_id: GLib.Variant):
        plugin_id = plugin_id.unpack()
        threading.Thread(target=self._install_plugin, args=(plugin_id,), name="install_plugin").start()

    @log.catch
    def _install_plugin(self, plugin_id: str):
        plugin = asyncio.run(gl.store_backend.get_plugin_for_id(plugin_id=plugin_id))

        self.set_working(True)

        if plugin is None:
            gl.app.send_notification("dialog-information-symbolic", "Failed to install plugin",
                                     f"The plugin {plugin_id} could not be installed")
            self.set_working(False)
            return
        
        success = asyncio.run(gl.store_backend.install_plugin(plugin))
        if not success:
            gl.app.send_notification("dialog-information-symbolic", "Failed to install plugin",
                                     f"The plugin {plugin_id} could not be installed")
        else:
            gl.app.send_notification("dialog-information-symbolic", "Plugin installed",
                                     f"The plugin {plugin_id} was successfully installed")

        self.set_working(False)            

    def set_working(self, working: bool) -> None:
        if working:
            GLib.idle_add(gl.app.mark_busy)
            GLib.idle_add(gl.app.main_win.set_cursor_from_name, "wait")
        else:
            GLib.idle_add(gl.app.unmark_busy)
            GLib.idle_add(gl.app.main_win.set_cursor_from_name, "default")

    def send_notification(self,
                          icon_name: str,
                          title: str,
                          body: str,
                          button: tuple[str, str, GLib.Variant] = None,
                          category: str = "im.error") -> None:
        show_notifications = gl.settings_manager.get_app_settings().get("ui", {}).get("show-notifications", True)
        if not show_notifications:
            return

        notif = Gio.Notification()
        notif.set_icon(Gio.Icon.new_for_string(icon_name))
        notif.set_category(category)
        notif.set_title(title)
        notif.set_body(body)
        if button:
            notif.add_button_with_target(button[0], button[1], button[2])

        GLib.idle_add(super().send_notification, "com.core447.StreamController", notif)
    def on_change_page(self, action, data: GLib.Variant, *args):
        """
        page_name can be either the name or the path of the page
        """
        serial_number, page_name = data.unpack()

        for controller in self.deck_manager.deck_controller:
            if controller.serial_number() == serial_number:
                page_path = gl.page_manager.find_matching_page_path(page_name)

                if controller is not None:
                    if controller.active_page is not None:
                        if os.path.abspath(page_path) == os.path.abspath(controller.active_page.json_path):
                            continue

                page = gl.page_manager.get_page(page_path, controller)
                if page_path is None:
                    continue

                controller.load_page(page)

    def send_outdated_plugin_notification(self, plugin_id: str) -> None:
        self.send_notification(
            "software-update-available-symbolic",
            "Plugin out of date",
            f"The plugin {plugin_id} is out of date and needs to be updated"
        )

    def send_missing_plugin_notification(self, plugin_id: str) -> None:
        self.send_notification(
            "dialog-information-symbolic",
            "Plugin missing",
            f"The plugin {plugin_id} is missing. Please install it.",
            button=("Install", "app.install-plugin", GLib.Variant.new_string(plugin_id))
        )
    def open_store(self, callback_agreed: bool = None) -> None:
        app_settings = gl.settings_manager.get_app_settings()
        agreed = app_settings.get("store", {}).get("responsibility-notes-agreed", False)

        if not agreed:
            if callback_agreed is None:
                resp_dialog = ResponsibleNotesDialog(self.get_active_window(), self.open_store)
                resp_dialog.present()
            return
        
        if gl.store is None:
            gl.store = Store(application=self, main_window=self.main_win)
        gl.store.present()