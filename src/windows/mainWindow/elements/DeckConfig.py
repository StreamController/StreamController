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


gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw

# Import own modules
from src.windows.mainWindow.elements.KeyGrid import KeyGrid
from src.windows.mainWindow.DeckPlus.ScreenBar import ScreenBar
from src.windows.mainWindow.DeckPlus.DialBox import DialBox
from src.windows.mainWindow.DeckNeo.ScreenRow import ScreenRow as NeoScreenRow

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

class DeckConfig(Gtk.Box):
    def __init__(self, page_settings_page: "PageSettingsPage"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, homogeneous=False,
                         halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.page_settings_page = page_settings_page

        self.active_widget = None
        self.screenbar = None
        self.screen_row = None
        self.build()

    def build(self):
        # Add key grid
        self.grid = KeyGrid(self.page_settings_page.deck_controller, self.page_settings_page)
        self.append(self.grid)

        if self.page_settings_page.deck_controller.deck.is_touch():
            self.screenbar = ScreenBar(self.page_settings_page, Input.Touchscreen("sd-plus"))
            self.append(self.screenbar)
        elif self.page_settings_page.deck_controller.has_screen():
            self.screen_row = NeoScreenRow(self.page_settings_page)
            self.screenbar = self.screen_row.screenbar
            self.append(self.screen_row)

        self.dial_box = DialBox(self.page_settings_page.deck_controller, self.page_settings_page)
        self.append(self.dial_box)

        self.apply_rotation_layout()

    def get_screen_child(self) -> Gtk.Widget:
        """The child holding the screen - on the Neo it also holds the touch keys next to it"""
        if self.screen_row is not None:
            return self.screen_row
        return self.screenbar

    def rebuild_for_rotation(self):
        """Re-create the parts whose size depends on the rotation, then re-lay them out."""
        # Whatever was selected is about to be destroyed
        self.active_widget = None

        for child in [self.grid, self.get_screen_child(), self.dial_box]:
            if child is not None:
                self.remove(child)

        self.screenbar = None
        self.screen_row = None
        self.build()

    def apply_rotation_layout(self):
        """
        Lay the parts out the way the deck is physically oriented.

        Unrotated the order top to bottom is grid, screenbar, dials. Turning the deck
        clockwise (90) moves the top to the right, turning it the other way (270)
        moves it to the left.
        """
        rotation = self.page_settings_page.deck_controller.deck.get_rotation()

        children = [self.grid]
        screen_child = self.get_screen_child()
        if screen_child is not None:
            children.append(screen_child)
        children.append(self.dial_box)

        if rotation % 180 == 0:
            self.set_orientation(Gtk.Orientation.VERTICAL)
            if rotation == 180:
                children.reverse()
        else:
            self.set_orientation(Gtk.Orientation.HORIZONTAL)
            if rotation == 90:
                children.reverse()

        previous = None
        for child in children:
            self.reorder_child_after(child, previous)
            previous = child
