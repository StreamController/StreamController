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
from gi.repository import Gtk, Adw

# Import Python modules 
from loguru import logger as log

# Import own modules
from src.windows.mainWindow.elements.KeyGrid import KeyGrid
from src.windows.mainWindow.elements.DeckSettings import DeckSettings

class DeckPage(Gtk.Box):
    def __init__(self):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.build()

    def build(self):
        # Add stack
        self.stack = Gtk.Stack(hexpand=True, vexpand=True)
        self.append(self.stack)

        # Add switcher
        self.switcher_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.append(self.switcher_box)
        self.switcher = Switcher(self)
        self.switcher_box.append(self.switcher)
        
        ## Add stack pages
        # Add key grid
        self.grid_page = KeyGrid(self.deck_controller, self)
        self.stack.add_titled(self.grid_page, "keys", "Page Key Grid")

        # Add settings
        self.settings_page = DeckSettings(self)
        self.stack.add_titled(self.settings_page, "settings", "Page Settings")


class Switcher(Gtk.StackSwitcher):
    def __init__(self, deck_page, **kwargs):
        super().__init__(stack=deck_page.stack, **kwargs)
        self.deck_page = deck_page
        self.set_hexpand(True)
        self.set_margin_start(10)
        self.set_margin_end(10)
        self.build()

    def build(self):
        pass