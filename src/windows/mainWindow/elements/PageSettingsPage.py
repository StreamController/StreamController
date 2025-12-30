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
from src.windows.mainWindow.elements.DeckConfig import DeckConfig

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.DeckStack import DeckStackChild

class PageSettingsPage(Gtk.Overlay):
    """
    Child of DeckStackChild
    This stack features one page for the key grid and one for the page settings
    """
    def __init__(self, deck_stack_child: "DeckStackChild", deck_controller, **kwargs):
        self.deck_controller = deck_controller
        self.deck_stack_child = deck_stack_child
        super().__init__(hexpand=True, vexpand=True)
        self.build()

    def build(self):
        self.global_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.global_box)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.global_box.append(self.main_box)

        self.deck_config = DeckConfig(self)
        self.main_box.append(self.deck_config)

    def on_open_deck_settings_button_click(self, button):
        self.deck_stack_child.set_visible_child_name("deck-settings")


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