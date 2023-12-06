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
from gi.repository import Gtk, Adw, Gio

import globals as gl

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.app import App

class PageManager(Gtk.ApplicationWindow):
    def __init__(self, app:"App"):
        super().__init__(title="Page Manager", default_width=400, default_height=600)
        self.set_transient_for(app.main_win)

        self.build()

    def build(self):
        # Title bar
        self.title_bar = Gtk.HeaderBar()
        self.set_titlebar(self.title_bar)

        # Main box
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL,
                                margin_start=10, margin_end=10,
                                margin_top=10, margin_bottom=10)
        self.set_child(self.main_box)

        # Search entry
        self.search_entry = Gtk.SearchEntry(placeholder_text=gl.lm.get("page-manager-search-hint"),
                                            hexpand=True,
                                            margin_bottom=10)
        # self.search_entry.connect("search-changed", self.on_search_changed)
        self.main_box.append(self.search_entry)

        # Scrolled window
        self.scrolled_window = Gtk.ScrolledWindow(vexpand=True)
        self.main_box.append(self.scrolled_window)
        
        # Scrolled box
        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.scrolled_window.set_child(self.scrolled_box)

        # Page box
        self.page_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.scrolled_box.append(self.page_box)

        # Load page buttons
        self.load_pages()

        # Add new button
        self.add_button = Gtk.Button(label=gl.lm.get("page-manager-add-page"),
                                     css_classes=["add-button"])
        # self.add_button.connect("clicked", self.on_add_page)
        self.main_box.append(self.add_button)

    def load_pages(self):
        pages = gl.page_manager.get_pages(remove_extension=True)
        for page in pages:
            self.page_box.append(PageButton(page_manager=self, page_name=page))



class PageButton(Gtk.Box):
    def __init__(self, page_manager:PageManager, page_name:str):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL,
                         margin_bottom=10)

        self.page_manager = page_manager
        self.page_name = page_name

        self.build()

    def build(self):
        self.main_button = Gtk.Button(hexpand=True, height_request=50,
                                      label=self.page_name,
                                      css_classes=["no-round-right"])
        self.append(self.main_button)

        self.append(Gtk.Separator(orientation=Gtk.Orientation.VERTICAL))

        self.config_button = Gtk.Button(height_request=50,
                                        icon_name="view-more",
                                        css_classes=["no-round-left"])
        self.config_button.connect("clicked", self.on_config)
        self.append(self.config_button)

    def on_config(self, button):
        context = KeyButtonContextMenu(self)
        context.popup()


class KeyButtonContextMenu(Gtk.PopoverMenu):
    def __init__(self, page_button:PageButton):
        super().__init__()
        self.page_button = page_button
        self.build()
        
    def build(self):
        self.set_has_arrow(False)
        self.set_parent(self.page_button.config_button)

        self.main_menu = Gio.Menu.new()
        
        # Rename action
        rename_action = Gio.SimpleAction.new("rename", None)
        remove_action = Gio.SimpleAction.new("remove", None)

        # Add actions to window
        self.page_button.page_manager.add_action(rename_action)
        self.page_button.page_manager.add_action(remove_action)

        # Connect actions
        rename_action.connect("activate", self.on_rename)
        remove_action.connect("activate", self.on_remove)

        self.main_menu.append(gl.lm.get("page-manager-rename"), "win.rename")
        self.main_menu.append(gl.lm.get("page-manager-remove"), "win.remove")

        self.set_menu_model(self.main_menu)

    def on_rename(self, action, param):
        old_name = self.page_button.main_button.get_label()
        new_name = old_name + "-copy"
        gl.page_manager.rename_page(old_name, new_name)
        self.page_button.main_button.set_label(new_name)

    def on_remove(self, action, param):
        gl.page_manager.remove_page(self.page_button.main_button.get_label())
        self.page_button.page_manager.page_box.remove(self.page_button)