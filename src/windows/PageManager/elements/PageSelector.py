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
from functools import lru_cache
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gio, Pango, GLib

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.PageManager.PageManager import PageManager

# Import own modules
from GtkHelper.GtkHelper import EntryDialog
from src.backend.DeckManagement.HelperMethods import natural_keys

# Import python modules
import os
from fuzzywuzzy import fuzz
import re

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

        self.header = Adw.HeaderBar(css_classes=["flat"])
        self.main_box.append(self.header)

        self.search_entry = Gtk.SearchEntry(placeholder_text=gl.lm.get("page-manager.page-selector.search-hint"), hexpand=True, margin_start=7, margin_end=7, margin_top=7, margin_bottom=7)
        self.search_entry.connect("changed", self.on_search_changed)
        self.header.set_title_widget(self.search_entry)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=False, vexpand=True)
        self.main_box.append(self.scrolled_window)

        self.clamp = Adw.Clamp()
        self.scrolled_window.set_child(self.clamp)

        self.clamp_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.clamp.set_child(self.clamp_box)


        self.list_box = Gtk.ListBox(css_classes=["navigation-sidebar"], selection_mode=Gtk.SelectionMode.SINGLE)
        self.list_box.set_sort_func(self.sort_func)
        self.list_box.set_filter_func(self.filter_func)
        self.list_box.connect("row-selected", self.on_row_activated)
        self.clamp_box.append(self.list_box)

        self.main_box.append(Gtk.Box()) # Push button to the bottom

        self.add_new_button = AddNewButton(page_manager=self.page_manager, margin_top=7, margin_start=7, margin_end=7, margin_bottom=7)
        self.main_box.append(self.add_new_button)

    def load_pages(self) -> None:
        self.page_rows.clear()
        self.list_box.remove_all()
        pages = gl.page_manager.get_pages()
        for page_path in pages:
            self.add_row_by_path(page_path)

    def on_row_activated(self, list_box: Gtk.ListBox, row: "PageRow") -> None:
        if row is None:
            self.page_manager.page_editor.main_stack.set_visible_child_name("no-page")
            self.page_manager.page_editor.menu_button.set_page_specific_actions_enabled(False)
            return
        self.page_manager.page_editor.menu_button.set_page_specific_actions_enabled(True)
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
        page_row = PageRow(page_manager=self.page_manager, page_path=path)
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
            # Split the page names into parts and convert numbers to integers
            item_1_parts = natural_keys(item_1_page_name)
            item_2_parts = natural_keys(item_2_page_name)

            # Compare each part
            for part1, part2 in zip(item_1_parts, item_2_parts):
                # If the parts are different, return -1 or 1 immediately
                if part1 < part2:
                    return -1
                elif part1 > part2:
                    return 1
        
        fuzz1 = self.calc_ratio(item_1_page_name, search)
        fuzz2 = self.calc_ratio(item_2_page_name, search)

        if fuzz1 > fuzz2:
            return -1
        elif fuzz1 < fuzz2:
            return 1
        return 0
    
    def filter_func(self, item) -> bool:
        search = self.search_entry.get_text()
        if search == "":
            return True

        page_name = os.path.splitext(os.path.basename(item.page_path))[0]

        return self.calc_ratio(page_name, search) > 50
    
    @lru_cache(maxsize=1000)
    def calc_ratio(self, str1, str2) -> int:
        return fuzz.ratio(str1.lower(), str2.lower())

        
    def on_search_changed(self, search_entry: Gtk.SearchEntry) -> None:
        # self.list_box.invalidate_filter()
        # self.list_box.invalidate_sort()
        GLib.idle_add(self.list_box.invalidate_filter)
        GLib.idle_add(self.list_box.invalidate_sort)

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
                           confirm_label=gl.lm.get("page-manager.page-selector.add-dialog.confirm"),
                           cancel_label=gl.lm.get("page-manager.page-selector.add-dialog.cancel"),
                           empty_warning=gl.lm.get("page-manager.page-selector.add-dialog.empty-warning"),
                           already_exists_warning=gl.lm.get("page-manager.page-selector.add-dialog.already-exists-warning"),
                           forbid_answers=gl.page_manager.get_page_names())
        
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

        self.label = Gtk.Label(label="", hexpand=True, xalign=0, ellipsize=Pango.EllipsizeMode.END)
        self.set_page_path(self.page_path)
        self.main_box.append(self.label)

        self.menu_button = Gtk.Button(icon_name="user-trash-symbolic", halign=Gtk.Align.END, css_classes=["flat"])
        self.main_box.append(self.menu_button) #TODO: Not implemented

        self.menu_button.connect("clicked", self.on_menu_click)
    
    def set_page_path(self, page_path: str) -> None:
        self.page_path = page_path
        self.label.set_text(os.path.splitext(os.path.basename(self.page_path))[0])

    def on_menu_click(self, *args):
        dialog = DeletePageConfirmationDialog(self.page_path, self.page_manager)
        dialog.present()

class DeletePageConfirmationDialog(Adw.MessageDialog):
    def __init__(self, path: str, page_manager, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_path = path
        self.page_manager = page_manager

        self.set_transient_for(page_manager)
        self.set_modal(True)
        self.set_title(gl.lm.get("page-manager.page-editor.delete-page-confirm.title"))
        self.add_response("cancel", gl.lm.get("page-manager.page-editor.delete-page-confirm.cancel"))
        self.add_response("delete", gl.lm.get("page-manager.page-editor.delete-page-confirm.delete"))
        self.set_default_response("cancel")
        self.set_close_response("cancel")
        self.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)

        page_name = os.path.splitext(os.path.basename(self.page_path))[0]
        self.set_body(f'{gl.lm.get("page-manager.page-editor.delete-page-confirm.body")}"{page_name}"?')

        self.connect("response", self.on_response)

    def on_response(self, dialog: Adw.MessageDialog, response: int) -> None:
        if response == "delete":
            self.page_manager.remove_page_by_path(self.page_path)
        self.destroy()