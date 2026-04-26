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
import gi

import globals as gl
from src.windows.mainWindow.elements.DeckSettings.DeckGroupParts.Brightness import Brightness
from src.windows.mainWindow.elements.DeckSettings.DeckGroupParts.Rotation import Rotation
from src.windows.mainWindow.elements.DeckSettings.DeckGroupParts.Screensaver import Screensaver

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw

__all__ = [
    "Brightness",
    "DeckGroup",
    "Rotation",
    "Screensaver",
]


class DeckGroup(Adw.PreferencesGroup):
    def __init__(self, settings_page):
        super().__init__(title=gl.lm.get("deck.deck-group.title"), description=gl.lm.get("deck.deck-group.description"))
        self.deck_serial_number = settings_page.deck_serial_number

        self.brightness = Brightness(settings_page, self.deck_serial_number)
        self.screensaver = Screensaver(settings_page, self.deck_serial_number)
        self.rotation = Rotation(settings_page, self.deck_serial_number)

        self.add(self.brightness)
        self.add(self.screensaver)
        self.add(self.rotation)
