"""
Author: Core447
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
# Import gtk modules
import threading
import gi

from src.backend.DeckManagement.InputIdentifier import Input

from loguru import logger as log

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import own modules
from src.windows.mainWindow.elements.KeyGrid import KeyGrid
from src.windows.mainWindow.DeckPlus.ScreenBar import ScreenBar
from src.windows.mainWindow.N3.DialBox import N3DialBox

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

class N3DeckConfig(Gtk.Box):
    def __init__(self, page_settings_page: "PageSettingsPage"):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, homogeneous=False,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.page_settings_page = page_settings_page

        self.active_widget = None
        self.build()

    def build(self):

        # Add key grid
        self.grid = KeyGrid(self.page_settings_page.deck_controller, self.page_settings_page)

        # Custom CSS classes for no image buttons
        for x in range(3):
            self.grid.buttons[x][2].image.set_css_classes(['key-image', 'key-button-no-image'])

        self.append(self.grid)

        # Add right side with dials
        self.dial_box = N3DialBox(self.page_settings_page.deck_controller, self.page_settings_page)
        self.append(self.dial_box)
