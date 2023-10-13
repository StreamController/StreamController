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

class KeyGrid(Gtk.Grid):
    def __init__(self, deck_controller, deck_page, **kwargs):
        super().__init__(**kwargs)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.deck_controller = deck_controller
        self.deck_page = deck_page
        self.build()
    
    def build(self):
        layout = self.deck_controller.deck.key_layout()
        for y in range(layout[0]):
            for x in range(layout[1]):
                self.attach(KeyButton(x*y), x, y, 1, 1)

        return
        log.debug(self.deck_controller.deck.key_layout())
        l = Gtk.Label(label="Key Grid")
        self.attach(l, 0, 0, 1, 1)


class KeyButton(Gtk.Button):
    def __init__(self, key, **kwargs):
        super().__init__(**kwargs)
        self.set_css_classes(["key-button"])
        self.key = key