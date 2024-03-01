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
from gi.repository import Gtk, Adw, Gdk, GLib, Gio

# Import Python modules 
from loguru import logger as log
import os

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

        # Store the copied key from the page
        self.copied_key:dict = None

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
        print("loop")
        for coords, image in tasks.items():
            self.buttons[coords[0]][coords[1]].set_image(image)
        print("loop end")

    def select_key(self, x: int, y: int):
        self.buttons[x][y].on_focus_in()
        self.buttons[x][y].image.grab_focus()

class KeyButton(Gtk.Frame):
    def __init__(self, key_grid:KeyGrid, coords, **kwargs):
        super().__init__(**kwargs)
        self.set_css_classes(["key-button-frame-hidden"])
        self.coords = coords
        self.key_grid = key_grid

        self.pixbuf = None

        # self.button = Gtk.Button(hexpand=True, vexpand=True, css_classes=["key-button"])
        # self.set_child(self.button)

        self.image = Gtk.Image(hexpand=True, vexpand=True, css_classes=["key-image", "key-button"])
        self.image.set_overflow(Gtk.Overflow.HIDDEN)
        self.set_child(self.image)

        # self.button.connect("clicked", self.on_click)

        focus_controller = Gtk.EventControllerFocus()
        self.add_controller(focus_controller)
        focus_controller.connect("enter", self.on_focus_in)

        # Click ctrl
        self.right_click_ctrl = Gtk.GestureClick().new()
        self.right_click_ctrl.connect("pressed", self.on_click)
        self.right_click_ctrl.set_button(0)
        self.image.add_controller(self.right_click_ctrl)

        # Make image focusable
        self.set_focus_child(self.image)
        self.image.set_focusable(True)

    def set_image(self, image):
        # Check if we can perform the next checks
        if recursive_hasattr(self, "key_grid.deck_page.grid_page"):
            # Check if this keygrid is on the screen
            if self.key_grid.deck_page.stack.get_visible_child() != self.key_grid.deck_page.grid_page:
                return
            # Check if this deck is on the screen
            if self.key_grid.deck_page.deck_stack.get_visible_child() != self.key_grid.deck_page:
                return

        self.pixbuf = image2pixbuf(image.convert("RGBA"), force_transparency=True)
        self.show_pixbuf(self.pixbuf)

        # update righthand side key preview if possible
        if recursive_hasattr(gl, "app.main_win.rightArea"):
            self.set_right_preview(self.pixbuf)

    def set_right_preview(self, pixbuf):
        right_area = gl.app.main_win.rightArea
        if pixbuf is None:
            return
        if not recursive_hasattr(gl, "app.main_win.rightArea"):
            return
        if right_area.key_editor.label_editor.label_group.expander.active_coords != (self.coords[1], self.coords[0]):
            return
        if gl.app.main_win.leftArea.deck_stack.get_visible_child().deck_controller != self.key_grid.deck_controller:
            return
        GLib.idle_add(right_area.key_editor.icon_selector.image.set_from_pixbuf, pixbuf)

    def show_pixbuf(self, pixbuf):
        self.pixbuf = pixbuf
        GLib.idle_add(self.image.set_from_pixbuf, self.pixbuf)

    def on_click(self, gesture, n_press, x, y):
        if gesture.get_current_button() == 1 and n_press == 1:
            # Single left click
            # Select key
            self.image.grab_focus()

        elif gesture.get_current_button() == 1 and n_press == 2:
            # Double left click
            # Simulate key press
            self.simulate_press()
            
        elif gesture.get_current_button() == 3 and n_press == 1:
            # Single right click
            # Open context menu
            popover = KeyButtonContextMenu(self)
            popover.popup()

    def simulate_press(self):
        ## Check if double click to emulate is turned on in the settings
        settings = gl.settings_manager.load_settings_from_file(os.path.join(gl.DATA_PATH, "settings", "settings.json"))
        if not settings.get("key-grid", {}).get("emulate-at-double-click", True):
            return
        
        deck = self.key_grid.deck_controller.deck
        key = self.key_grid.deck_controller.coords_to_index(reversed(self.coords))
        self.key_grid.deck_controller.key_change_callback(deck, key, True)
        # Release key after 100ms
        GLib.timeout_add(100, self.key_grid.deck_controller.key_change_callback, deck, key, False)

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
        # Update settings on the righthand side of the screen
        if not recursive_hasattr(gl, "app.main_win.rightArea"):
            return
        right_area = gl.app.main_win.rightArea
        right_area.load_for_coords((self.coords[1], self.coords[0]))
        # Update preview
        if self.pixbuf is not None:
            self.set_right_preview(self.pixbuf)
        # self.set_css_classes(["key-button-frame"])
        # self.button.set_css_classes(["key-button-new-small"])
        self.set_visible(True)

    # Modifier
    def on_copy(self):
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        y, x = self.coords
        key_dict = active_page.dict["keys"][f"{x}x{y}"]

        gl.app.main_win.key_dict = key_dict

    def on_cut(self):
        self.on_copy()
        self.on_remove()

    def on_paste(self):
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        y, x = self.coords
        
        active_page.dict["keys"][f"{x}x{y}"] = gl.app.main_win.key_dict
        active_page.reload_similar_pages(page_coords=f"{x}x{y}", reload_self=True)

        # Reload ui
        gl.app.main_win.rightArea.load_for_coords((x, y))

    def on_remove(self):
        active_page = self.key_grid.deck_controller.active_page
        if active_page is None:
            return
        y, x = self.coords

        del active_page.dict["keys"][f"{x}x{y}"]
        active_page.save()
        active_page.load()

        # Stop video/gif task if present
        key_index = self.key_grid.deck_controller.coords_to_index(reversed(self.coords))
        if key_index in self.key_grid.deck_controller.media_handler.video_tasks.keys():
            del self.key_grid.deck_controller.media_handler.video_tasks[key_index]

        active_page.reload_similar_pages(page_coords=f"{x}x{y}", reload_self=True)

        # Reload ui
        gl.app.main_win.rightArea.load_for_coords((x, y))


class KeyButtonContextMenu(Gtk.PopoverMenu):
    def __init__(self, key_button:KeyButton, **kwargs):
        super().__init__(**kwargs)
        self.key_button = key_button
        self.build()

    def build(self):
        self.set_parent(self.key_button)
        self.set_has_arrow(False)

        self.main_menu = Gio.Menu.new()

        self.copy_paste_menu = Gio.Menu.new()
        self.remove_menu = Gio.Menu.new()

        # Add actions to menus
        self.copy_paste_menu.append("Copy", "win.copy")
        self.copy_paste_menu.append("Cut", "win.cut")
        self.copy_paste_menu.append("Paste", "win.paste")
        self.remove_menu.append("Remove", "win.remove")

        # Add sections to menu
        self.main_menu.append_section(None, self.copy_paste_menu)
        self.main_menu.append_section(None, self.remove_menu)

        self.set_menu_model(self.main_menu)