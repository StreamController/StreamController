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
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import Python modules
from loguru import logger as log
import sys
import os

# Import own modules
from src.windows.mainWindow.deckSwitcher import DeckSwitcher
from src.windows.mainWindow.elements.PageSelector import PageSelector
from src.windows.Store.Store import Store
from src.windows.Settings.Settings import Settings

# Import globals
import globals as gl

class HeaderBar(Gtk.HeaderBar):
    def __init__(self, deck_manager, main_window, deck_stack, **kwargs):
        super().__init__(**kwargs)
        self.deck_manager = deck_manager
        self.deckStack = deck_stack
        self.main_window = main_window
        self.build()

    def build(self):
        # Page selector
        self.page_selector = PageSelector(self.main_window, self.deck_manager.page_manager)
        self.pack_start(self.page_selector)

        # Deck selector
        self.deckSwitcher = DeckSwitcher(main_window = self.main_window)
        self.deckSwitcher.switcher.set_stack(self.deckStack)
        self.set_title_widget(self.deckSwitcher)

        ## Hamburger menu actions
        # Open store
        self.open_store_action = Gio.SimpleAction.new("open-store", None)
        self.open_store_action.connect("activate", self.on_open_store)
        self.main_window.add_action(self.open_store_action)
        # Open settings
        self.open_settings_action = Gio.SimpleAction.new("open-settings", None)
        self.open_settings_action.connect("activate", self.on_open_settings)
        self.main_window.add_action(self.open_settings_action)
        # Quit App
        self.quit_action = Gio.SimpleAction.new("quit", None)
        self.quit_action.connect("activate", self.on_quit)
        self.main_window.add_action(self.quit_action)
        # Open About
        self.open_about_action = Gio.SimpleAction.new("open-about", None)
        self.open_about_action.connect("activate", self.on_open_about)
        self.main_window.add_action(self.open_about_action)

        # Menu
        self.menu = Gio.Menu.new()
        self.menu.append(gl.lm.get("open-store"), "win.open-store")
        self.menu.append(gl.lm.get("open-settings"), "win.open-settings")
        self.menu.append(gl.lm.get("quit"), "win.quit")
        self.menu.append(gl.lm.get("open-about"), "win.open-about")

        # Popover
        self.popover = Gtk.PopoverMenu()
        self.popover.set_menu_model(self.menu)

        # Create a menu button
        self.hamburger_menu = Gtk.MenuButton()
        self.hamburger_menu.set_popover(self.popover)
        self.hamburger_menu.set_icon_name("open-menu-symbolic")
        self.pack_end(self.hamburger_menu)

        # Config deck button
        self.config_button = Gtk.Button(label=gl.lm.get("toggle-config-to-deck"))
        self.config_button.connect("clicked", self.on_config_button_click)
        self.pack_end(self.config_button)

    def on_config_button_click(self, button):
        active_page = self.deckStack.get_visible_child().get_visible_child_name()

        if active_page == "Page Settings":
            self.deckStack.get_visible_child().set_visible_child_name("Deck Settings")
            button.set_label(gl.lm.get("toggle-config-to-page"))
        elif active_page == "Deck Settings":
            self.deckStack.get_visible_child().set_visible_child_name("Page Settings")
            button.set_label(gl.lm.get("toggle-config-to-deck"))

    def on_open_store(self, action, parameter):
        self.store = Store(application=gl.app, main_window=gl.app.main_win)
        self.store.present()

    def on_open_settings(self, action, parameter):
        self.settings = Settings()
        self.settings.present()

    def on_quit(self, action, parameter):
        # Close all decks
        gl.deck_manager.close_all()
        # TODO: Find better way - sys.exit doesn't work because it waits for the threads to finish
        os._exit(0)

    def on_open_about(self, action, parameter):
        self.about = Adw.AboutWindow(transient_for=self.main_window)
        self.about.set_application_name("StreamController")
        self.about.set_version(gl.app_version)
        self.about.set_developers(["Core447"])
        self.about.set_developer_name("Core447")
        self.about.set_license_type(Gtk.License.GPL_3_0)
        self.about.set_comments("Control your StreamDeck")
        self.about.set_website("https://github.com/StreamController/StreamController")
        self.about.set_issue_url("https://github.com/StreamController/StreamController/issues")
        self.about.add_credit_section("Contributors", ["Core447"])
        self.about.set_copyright("Copyright (C) 2024 Core447")
        self.about.set_application_icon("com.core447.StreamController")
        self.about.set_visible(True)

        self.about.add_legal_section(
            "Stream Deck",
            "Stream Deck is a trademark owned by Elgato/Corsair Memory, Inc.",
            Gtk.License.CUSTOM,
            license=None,
        )

        self.about.set_debug_info("".join(gl.logs))
        self.about.set_debug_info_filename(os.path.join(gl.DATA_PATH, "logs/logs.log"))

        self.about.set_release_notes(gl.release_notes)  
        self.about.set_release_notes_version(gl.app_version)