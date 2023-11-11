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
from gi.repository import Gtk, Adw, Gio, GObject

# Import Python modules
from loguru import logger as log
import os

# Import globas
import globals as gl

class PageSelector(Gtk.Box):
    def __init__(self, main_window, page_manager):
        self.main_window = main_window
        self.page_manager = page_manager
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL)
        self.build()

    def build(self):
        # Label
        self.label = Gtk.Label(label="Page:", margin_start=3, margin_end=7, css_classes=["bold"])
        self.append(self.label)

        # Right area
        self.right_area = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        self.append(self.right_area)

        # Dropdown
        self.pages_model = Gtk.StringList()
        self.drop_down = Gtk.DropDown()
        self.drop_down.set_model(self.pages_model)
        self.update()
        self.drop_down.set_tooltip_text("Select page for active deck")
        self.drop_down.connect("notify::selected", self.on_change_page)
        self.right_area.append(self.drop_down)

        # Settings button
        self.settings_button = Gtk.Button(icon_name="settings", tooltip_text="Open Page Manager")
        self.right_area.append(self.settings_button)
    
    def update(self):
        pages = self.page_manager.get_pages()
        self.clear_model()
        for page in pages:
            self.pages_model.append(os.path.splitext(page)[0])

    def clear_model(self):
        for i in range(self.pages_model.get_n_items()):
            self.pages_model.remove(0)

    def set_selected(self, page_name):
        for i in range(self.pages_model.get_n_items()):
            if self.pages_model.get_item(i).get_string() == page_name:
                self.drop_down.set_selected(i)
                return
            
    def update_selected(self):
        active_controller = self.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        page_name = active_controller.active_page.get_name()
        self.set_selected(page_name)

    def on_change_page(self, drop_down, *args):
        active_controller = self.main_window.leftArea.deck_stack.get_visible_child().deck_controller
        page = gl.page_manager.get_page(self.pages_model.get_item(drop_down.get_selected()).get_string(), deck_controller = active_controller)
        active_controller.load_page(page)