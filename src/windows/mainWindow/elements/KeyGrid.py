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
from src.backend.DeckManagement.HelperMethods import recursive_hasattr

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

        self.selected_key = None # The selected key, indicated by a blue frame around it

        self.buttons = [[None] * deck_controller.deck.key_layout()[1] for i in range(deck_controller.deck.key_layout()[0])]

        self.build()

        self.load_from_changes()

    
    def build(self):
        layout = self.deck_controller.deck.key_layout()
        for x in range(layout[0]):
            for y in range(layout[1]):
                button = KeyButton(self, (layout[0] - x - 1, y))
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
            self.buttons[coords[0]][coords[1]].show_pixbuf(pixbuf)

class KeyButton(Gtk.Frame):
    def __init__(self, key_grid, coords, **kwargs):
        super().__init__(**kwargs)
        self.set_css_classes(["key-button-frame-hidden"])
        self.coords = coords
        self.key_grid = key_grid

        self.pixbuf = None

        self.button = Gtk.Button(hexpand=True, vexpand=True, css_classes=["key-button"])
        self.set_child(self.button)

        self.image = Gtk.Image(hexpand=True, vexpand=True, css_classes=["key-image"])
        self.image.set_overflow(Gtk.Overflow.HIDDEN)
        self.button.set_child(self.image)

        self.button.connect("clicked", self.on_click)

        focus_controller = Gtk.EventControllerFocus()
        self.add_controller(focus_controller)
        focus_controller.connect("enter", self.on_focus_in)

    def set_image(self, image):
        # Check if this keygrid is on the screen
        if self.key_grid.deck_page.stack.get_visible_child() != self.key_grid.deck_page.grid_page:
            return
        # Check if this deck is on the screen
        if self.key_grid.deck_page.deck_stack.get_visible_child() != self.key_grid.deck_page:
            return

        self.pixbuf = image2pixbuf(image.convert("RGBA"), force_transparency=True)
        self.show_pixbuf(self.pixbuf)

        # update righthand side key preview
        if not recursive_hasattr(gl, "app.main_win.rightArea"): return
        right_area = gl.app.main_win.rightArea
        if right_area.key_editor.label_editor.label_group.expander.active_coords == (self.coords[1], self.coords[0]):
            self.set_right_preview(self.pixbuf)

    def set_right_preview(self, pixbuf):
        right_area = gl.app.main_win.rightArea
        # pixbuf = self.image.get_pixbuf()
        if pixbuf != None:
            GLib.idle_add(right_area.key_editor.icon_selector.image.set_from_pixbuf, pixbuf)

    def show_pixbuf(self, pixbuf):
        self.pixbuf = pixbuf
        GLib.idle_add(self.image.set_from_pixbuf, self.pixbuf)

    def on_click(self, button):
        # Update settings on the righthand side of the screen
        right_area = gl.app.main_win.rightArea
        right_area.load_for_coords((self.coords[1], self.coords[0]))
        # Update preview
        if self.pixbuf is not None:
            self.set_right_preview(self.pixbuf)
        # self.set_css_classes(["key-button-frame"])
        # self.button.set_css_classes(["key-button-new-small"])
        self.set_visible(True)

    def set_visible(self, visible):
        if visible:
            # Hide other frames
            if self.key_grid.selected_key not in [self, None]:
                # self.key_grid.selected_key.set_css_classes(["key-button-frame-hidden"])
                self.key_grid.selected_key.set_visible(False)
            self.set_css_classes(["key-button-frame"])
            self.key_grid.selected_key = self
        else:
            self.set_css_classes(["key-button-frame-hidden"])
            self.key_grid.selected_key = None


    def on_focus_in(self, *args):
        self.on_click(self)