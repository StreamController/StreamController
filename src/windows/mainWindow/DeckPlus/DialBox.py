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
from typing import TYPE_CHECKING

import gi

from src.backend.DeckManagement.InputIdentifier import Input
from src.windows.mainWindow.DeckPlus.Dial import Dial
from src.windows.mainWindow.DeckPlus.DialContextMenu import DialContextMenu

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gtk

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import DeckController
    from src.windows.mainWindow.elements.PageSettingsPage import PageSettingsPage

__all__ = [
    "Dial",
    "DialBox",
    "DialContextMenu",
]


class DialBox(Gtk.Box):
    def __init__(self, deck_controller: "DeckController", page_settings_page: "PageSettingsPage", **kwargs):
        super().__init__(**kwargs)
        self.deck_controller = deck_controller
        self.set_hexpand(True)
        self.set_homogeneous(True)
        self.page_settings_page = page_settings_page

        self.dials: list[Dial] = []
        self.build()


    def build(self):
        for i in range(self.deck_controller.deck.dial_count()):
            dial = Dial(self, Input.Dial(str(i)))
            self.dials.append(dial)
            self.append(dial)
