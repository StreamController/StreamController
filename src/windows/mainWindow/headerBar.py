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

# Import own modules
from src.windows.mainWindow.deckSwitcher import DeckSwitcher
from src.windows.mainWindow.elements.PageSelector import PageSelector
from src.windows.Store.Store import Store

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

        # Hamburger menu actions
        self.open_store_action = Gio.SimpleAction.new("open-store", None)
        self.open_store_action.connect("activate", self.on_open_store)
        self.main_window.add_action(self.open_store_action)

        # Menu
        self.menu = Gio.Menu.new()
        self.menu.append(gl.lm.get("open-store"), "win.open-store")

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