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
# Import gi
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.PageManager.PageManager import PageManager

# Import own modules
from GtkHelper.GtkHelper import EntryDialog

# Import python modules
import os
from fuzzywuzzy import fuzz

# Import globals
import globals as gl


class PageSelector(Adw.NavigationPage):
    def __init__(self, page_manager: "PageManager"):
        super().__init__(title=gl.lm.get("page-manager.page-selector.title"))
        self.page_manager = page_manager
        self.page_rows: list[PageRow] = []
        self.build()

        self.list_box.select_row(None)

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.set_child(self.main_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text=gl.lm.get("page-manager.page-selector.search-hint"), hexpand=True, margin_start=7, margin_end=7, margin_top=7, margin_bottom=7)
        self.search_entry.connect("changed", self.on_search_changed)
        self.main_box.append(self.search_entry)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.main_box.append(self.scrolled_window)

        self.clamp = Adw.Clamp()
        self.scrolled_window.set_child(self.clamp)

        self.clamp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.clamp.set_child(self.clamp_box)


        self.list_box = Gtk.ListBox(css_classes=["navigation-sidebar"], selection_mode=Gtk.SelectionMode.SINGLE)
        self.list_box.set_sort_func(self.sort_func)
        self.list_box.connect("row-selected", self.on_row_activated)
        self.clamp_box.append(self.list_box)

        self.main_box.append(Gtk.Box()) # Push button to the bottom

        self.add_new_button = AddNewButton(page_manager=self.page_manager, margin_top=7, margin_start=7, margin_end=7, margin_bottom=7)
        self.main_box.append(self.add_new_button)

    def load_pages(self) -> None:
        self.page_rows.clear()
        pages = gl.page_manager.get_pages()
        for page_path in pages:
            self.add_row_by_path(page_path)

    def on_row_activated(self, list_box: Gtk.ListBox, row: "PageRow") -> None:
        if row is None:
            self.page_manager.page_editor.main_stack.set_visible_child_name("no-page")
            return
        self.page_manager.page_editor.main_stack.set_visible_child_name("editor")
        self.page_manager.page_editor.load_for_page(row.page_path)

    def rename_page_row(self, old_path: str, new_path: str) -> None:
        for page_row in self.page_rows:
            if page_row.page_path == old_path:
                page_row.set_page_path(new_path)

    def remove_row_with_path(self, path: str) -> None:
        for page_row in self.page_rows:
            if page_row.page_path == path:
                self.list_box.remove(page_row)
                return
            
    def add_row_by_path(self, path: str) -> None:
        page_row = PageRow(page_manager=self, page_path=path)
        self.page_rows.append(page_row)
        self.list_box.append(page_row)
    
    def sort_func(self, item1, item2) -> bool:
        """
        -1 if child1 should come before child2
        1 if child1 should come after child2
        0 if they are equal
        """
        item_1_page_name = os.path.splitext(os.path.basename(item1.page_path))[0].lower()
        item_2_page_name = os.path.splitext(os.path.basename(item2.page_path))[0].lower()

        search = self.search_entry.get_text()
        if search == "":
            # Sort alphabetically
            if item_1_page_name < item_2_page_name:
                return -1
            if item_1_page_name > item_2_page_name:
                return 1
            return 0
        
        fuzz1 = fuzz.ratio(item_1_page_name.lower(), search.lower())
        fuzz2 = fuzz.ratio(item_2_page_name.lower(), search.lower())

        if fuzz1 > fuzz2:
            return -1
        elif fuzz1 < fuzz2:
            return 1
        return 0
        
    def on_search_changed(self, search_entry: Gtk.SearchEntry) -> None:
        self.list_box.invalidate_sort()

class AddNewButton(Gtk.Button):
    def __init__(self, page_manager: "PageManager", *args, **kwargs):
        self.page_manager = page_manager
        super().__init__(*args, **kwargs)
        self.set_label(gl.lm.get("page-manager.page-selector.add-new"))
        self.set_css_classes(["suggested-action"])

        self.connect("clicked", self.on_clicked)

    def on_clicked(self, button: Gtk.Button) -> None:
        dial = EntryDialog(parent_window=self.page_manager,
                           dialog_title=gl.lm.get("page-manager.page-selector.add-dialog.title"),
                           placeholder=gl.lm.get("page-manager.page-selector.add-dialog.placeholder"),
                           confirm_label=gl.lm.get("page-manager.page-selector.add-dialog.confirm"))
        dial.show(callback_func=self.page_manager.add_page_from_name)



class PageRow(Gtk.ListBoxRow):
    def __init__(self, page_manager: "PageManager", page_path: str):
        super().__init__()
        self.page_manager = page_manager
        self.page_path = page_path
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.main_box)

        self.label = Gtk.Label(label="", hexpand=True, xalign=0)
        self.set_page_path(self.page_path)
        self.main_box.append(self.label)

        self.menu_button = Gtk.Button(icon_name="open-menu-symbolic", halign=Gtk.Align.END, css_classes=["flat"])
        # self.main_box.append(self.menu_button) #TODO: Not implemented
    
    def set_page_path(self, page_path: str) -> None:
        self.page_path = page_path
        self.label.set_text(os.path.splitext(os.path.basename(self.page_path))[0])