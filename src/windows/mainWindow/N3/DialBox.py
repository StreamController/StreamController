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
import time
import gi

from StreamDeck.Devices.StreamDeck import DialEventType, TouchscreenEventType

from src.backend.DeckManagement.InputIdentifier import Input
from src.backend.DeckManagement.HelperMethods import recursive_hasattr
from src.windows.mainWindow.elements.Dial import Dial

import globals as gl

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk, Adw, Gdk, GLib, Gio

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage
    from src.backend.DeckManagement.DeckController import DeckController

class N3DialBox(Gtk.Box):
    def __init__(self, deck_controller: "DeckController", page_settings_page: "PageSettingsPage", **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.deck_controller = deck_controller
        self.set_hexpand(True)
        self.set_homogeneous(True)
        self.page_settings_page = page_settings_page

        self.dials: list[Dial] = []
        self.build()


    def build(self):
        dial = Dial(self, Input.Dial("0"))
        self.dials.append(dial)
        self.append(dial)

        bottom = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        for i in range(1,self.deck_controller.deck.dial_count()):
            dial = Dial(self, Input.Dial(str(i)))
            self.dials.append(dial)
            bottom.append(dial)
        self.append(bottom)
