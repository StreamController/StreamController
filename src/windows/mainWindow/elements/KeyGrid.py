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
from gi.repository import Gtk, Adw, Gdk, GLib

# Import Python modules 
from loguru import logger as log

# Imort globals
import globals as gl

# Import own modules
from src.backend.DeckManagement.ImageHelpers import image2pixbuf
class KeyGrid(Gtk.Grid):
    """
    Child of PageSettingsPage
    Key grid for the button config
    """
    def __init__(self, deck_controller, deck_page, **kwargs):
        super().__init__(**kwargs)
        self.set_halign(Gtk.Align.CENTER)
        self.set_valign(Gtk.Align.CENTER)
        self.deck_controller = deck_controller
        self.deck_page = deck_page

        self.buttons = [[None] * deck_controller.deck.key_layout()[1] for i in range(deck_controller.deck.key_layout()[0])]

        self.build()

        self.load_from_changes()

    
    def build(self):
        layout = self.deck_controller.deck.key_layout()
        for x in range(layout[0]):
            for y in range(layout[1]):
                button = KeyButton(self, x*y)
                self.attach(button, y, layout[0] - x, 1, 1)
                x = layout[0] - 1 - x
                self.buttons[x][y] = button

        return
        log.debug(self.deck_controller.deck.key_layout())
        l = Gtk.Label(label="Key Grid")
        self.attach(l, 0, 0, 1, 1)


    def load_from_changes(self):
        # Applt changes made before creation of self
        if not hasattr(self.deck_controller, "ui_grid_buttons_changes_while_hidden"):
            return
        tasks = self.deck_controller.ui_grid_buttons_changes_while_hidden
        for coords, pixbuf in tasks.items():
            self.buttons[coords[0]][coords[1]].image.set_from_pixbuf(pixbuf)


class KeyButton(Gtk.Button):
    def __init__(self, key_grid, key, **kwargs):
        super().__init__(**kwargs)
        self.set_css_classes(["key-button"])
        self.key = key
        self.key_grid = key_grid

        self.image = Gtk.Image(hexpand=True, vexpand=True, css_classes=["key-image"])
        self.image.set_overflow(Gtk.Overflow.HIDDEN)
        self.set_child(self.image)

    def set_image(self, image):
        # Check if this keygrid is on the screen
        if self.key_grid.deck_page.stack.get_visible_child() != self.key_grid.deck_page.grid_page:
            return
        # Check if this deck is on the screen
        if self.key_grid.deck_page.deck_stack.get_visible_child() != self.key_grid.deck_page:
            return

        pixbuf = image2pixbuf(image.convert("RGBA"), force_transparency=True)
        GLib.idle_add(self.image.set_from_pixbuf, pixbuf)