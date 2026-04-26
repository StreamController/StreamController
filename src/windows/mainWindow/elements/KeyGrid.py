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
from typing import TYPE_CHECKING

import gi
from loguru import logger as log

from src.backend.DeckManagement.InputIdentifier import Input
from src.windows.mainWindow.elements.KeyButton import KeyButton
from src.windows.mainWindow.elements.KeyButtonContextMenu import KeyButtonContextMenu

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import GLib, Gtk

if TYPE_CHECKING:
    from src.backend.DeckManagement.DeckController import ControllerKey

__all__ = [
    "KeyButton",
    "KeyButtonContextMenu",
    "KeyGrid",
]


class KeyGrid(Gtk.Grid):
    """
    Child of PageSettingsPage
    Key grid for the button config
    """
    def __init__(self, deck_controller, page_settings_page, **kwargs):
        super().__init__(**kwargs)
        self.deck_controller = deck_controller
        self.page_settings_page = page_settings_page

        self.selected_key = None # The selected key, indicated by a blue frame around it

        [y, x] = self.deck_controller.deck.key_layout()
        self.buttons = [[None] * y for i in range(x)]

        # Store the copied key from the page
        self.copied_key:dict = None

        self.build()

        self.connect("map", self.on_map)
        self.connect("unmap", self.on_unmap)

        self.load_from_changes()

        GLib.idle_add(self.select_key, 0, 0)

    def regenerate_buttons(self):
        [y, x] = self.deck_controller.deck.key_layout()
        self.buttons = [[None] * y for i in range(x)]
    
    def build(self):
        self.clear()

        layout = self.deck_controller.deck.key_layout()
        for x in range(layout[1]):
            for y in range(layout[0]):
                button = KeyButton(self, (x, y))
                self.attach(button, x, y, 1, 1)
                button._set_visible(False) # Hide buttons per default - they will be shown when the the grid is mapped to prevent large grids to resize every child
                self.buttons[x][y] = button
        return
        log.debug(self.deck_controller.deck.key_layout())
        l = Gtk.Label(label="Key Grid")
        self.attach(l, 0, 0, 1, 1)

    def load_from_changes(self):
        # Applt changes made before creation of self
        if not hasattr(self.deck_controller, "ui_image_changes_while_hidden"):
            return
        tasks = self.deck_controller.ui_image_changes_while_hidden
        for identifier, image in list(tasks.items()):
            if not isinstance(identifier, Input.Key):
                continue
            x, y = identifier.coords
            self.buttons[x][y].set_image(image)

            try:
                tasks.pop(identifier)
            except KeyError:
                pass
        
    def select_key(self, x: int, y: int):
        self.buttons[x][y].on_focus_in()
        self.buttons[x][y].image.grab_focus()

    def on_map(self, widget):
        self.load_from_changes()

        # Only show buttons when the grid is mapped to prevent large grids to resize every child
        self.set_buttons_visible(True)

    def on_unmap(self, widget):
        # Only show buttons when the grid is mapped to prevent large grids to resize every child
        self.set_buttons_visible(False)

    def clear(self):
        while self.get_first_child() is not None:
            self.remove(self.get_first_child())

    def set_buttons_visible(self, visible):
        for i in range(len(self.buttons)):
            for j in range(len(self.buttons[i])):
                self.buttons[i][j]._set_visible(visible)
        return
        for x in range(self.deck_controller.deck.key_layout()[1]):
            for y in range(self.deck_controller.deck.key_layout()[0]):
                self.buttons[x][y]._set_visible(visible)
