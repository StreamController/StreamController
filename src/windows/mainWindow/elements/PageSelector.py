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
from gi.repository import Gtk, Adw, Gio, GObject, Pango, GLib

# Import Python modules
from loguru import logger as log
import os
from fuzzywuzzy import fuzz

# Import globas
import globals as gl

# Import own modules
from src.windows.PageManager.PageManager import PageManager
from src.backend.DeckManagement.HelperMethods import natural_keys
from src.Signals import Signals

class PageSelector(Gtk.Box):
    def __init__(self, main_window, page_manager, **kwargs):
        self.main_window = main_window
        self.page_manager = page_manager
        self.page_rows: list["PageRow"] = []
        self.selected_page_path: str = None
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, **kwargs)
        self.build()

    def build(self):
        # Label
        self.label = Gtk.Label(label=gl.lm.get("header-page-selector-page-label"), margin_start=3, margin_end=7, css_classes=["bold"])
        self.append(self.label)

        # Right area
        self.sidebar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, css_classes=["linked"])
        self.append(self.sidebar)

        # Dropdown
        self.drop_down = Gtk.MenuButton(css_classes=["header-page-dropdown"], hexpand=False,
                                        tooltip_text=gl.lm.get("header-page-selector-drop-down-hint"))

        self.drop_down_label = Gtk.Label(label="", hexpand=True, xalign=0, max_width_chars=15,
                                         ellipsize=Pango.EllipsizeMode.END)
        self.drop_down_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=6)
        self.drop_down_box.append(self.drop_down_label)
        self.drop_down_box.append(Gtk.Image(icon_name="pan-down-symbolic"))
        self.drop_down.set_child(self.drop_down_box)

        self.popover = Gtk.Popover()
        self.popover.connect("show", self.on_popover_show)
        self.drop_down.set_popover(self.popover)

        self.popover_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6, width_request=250)
        self.popover.set_child(self.popover_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text=gl.lm.get("header-page-selector-search-hint"))
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.search_entry.connect("activate", self.on_search_activate)
        self.popover_box.append(self.search_entry)

        self.scrolled_window = Gtk.ScrolledWindow(propagate_natural_height=True, max_content_height=300,
                                                  hscrollbar_policy=Gtk.PolicyType.NEVER)
        self.popover_box.append(self.scrolled_window)

        self.list_box = Gtk.ListBox(css_classes=["navigation-sidebar"], selection_mode=Gtk.SelectionMode.SINGLE)
        self.list_box.set_filter_func(self.filter_func)
        self.list_box.set_sort_func(self.sort_func)
        # row-activated is only emitted for explicit user activation, so searching never changes the page
        self.list_box.connect("row-activated", self.on_row_activated)
        self.scrolled_window.set_child(self.list_box)

        self.update()
        self.sidebar.append(self.drop_down)

        # Settings button
        self.open_settings_button = Gtk.Button(icon_name="folder-documents-symbolic", tooltip_text=gl.lm.get("header-page-selector-page-settings-hint"))
        self.open_settings_button.connect("clicked", self.on_click_open_page_settings)
        self.sidebar.append(self.open_settings_button)

        # Manager button
        self.open_manager_button = Gtk.Button(icon_name="folder-open-symbolic", tooltip_text=gl.lm.get("header-page-selector-page-manager-hint"))
        self.open_manager_button.connect("clicked", self.on_click_open_page_manager)
        self.sidebar.append(self.open_manager_button)

        gl.signal_manager.connect_signal(signal=Signals.ChangePage, callback=self.update_selected)
        gl.signal_manager.connect_signal(signal=Signals.PageRename, callback=self.update)
        gl.signal_manager.connect_signal(signal=Signals.PageAdd, callback=self.update)
        gl.signal_manager.connect_signal(signal=Signals.PageDelete, callback=self.update)
    
    def update(self, *args, **kwargs):
        self.page_rows.clear()
        self.list_box.remove_all()

        for page_path in self.page_manager.get_pages():
            page_row = PageRow(page_path)
            self.page_rows.append(page_row)
            self.list_box.append(page_row)

        self.update_selected()

    def set_selected(self, page_path: str):
        for page_row in self.page_rows:
            if page_row.page_path == page_path:
                self.selected_page_path = page_path
                self.list_box.select_row(page_row)
                self.drop_down_label.set_label(page_row.page_name)
                return

    def update_selected(self, *args, **kwargs):
        child = self.main_window.leftArea.deck_stack.get_visible_child()
        if child is None:
            self.drop_down.set_sensitive(False)
            return
        else:
            self.drop_down.set_sensitive(True)
        active_controller = child.deck_controller
        if active_controller.is_sticky_editing():
            # The sticky page is not one of the selectable pages
            self.selected_page_path = None
            self.list_box.unselect_all()
            self.drop_down_label.set_label(gl.lm.get("deck.sticky-actions.button"))
            return

        page = active_controller.active_page
        if page is None:
            return
        page_path = page.json_path
        self.set_selected(page_path)

    def on_popover_show(self, popover: Gtk.Popover):
        self.search_entry.set_text("")
        self.list_box.invalidate_filter()
        self.list_box.invalidate_sort()
        GLib.idle_add(self.search_entry.grab_focus)

    def on_search_changed(self, search_entry: Gtk.SearchEntry):
        self.list_box.invalidate_filter()
        self.list_box.invalidate_sort()

    def on_search_activate(self, search_entry: Gtk.SearchEntry):
        # Activate the best match
        index = 0
        while (page_row := self.list_box.get_row_at_index(index)) is not None:
            if self.filter_func(page_row):
                self.on_row_activated(self.list_box, page_row)
                return
            index += 1

    def on_row_activated(self, list_box: Gtk.ListBox, row: "PageRow"):
        self.popover.popdown()

        if row.page_path == self.selected_page_path:
            return

        self.on_change_page(row.page_path)

    def on_change_page(self, page_path: str):
        active_child = self.main_window.leftArea.deck_stack.get_visible_child()
        if active_child is None:
            return

        active_controller = active_child.deck_controller
        if active_controller is None:
            return

        page = gl.page_manager.get_page(path=page_path, deck_controller = active_controller)
        log.info(f"Load page: {page}")
        active_controller.load_page(page)

    def filter_func(self, page_row: "PageRow") -> bool:
        search = self.search_entry.get_text().strip()
        if search == "":
            return True

        return self.calc_ratio(page_row.page_name, search) > 50

    def sort_func(self, page_row_1: "PageRow", page_row_2: "PageRow") -> int:
        """
        -1 if page_row_1 should come before page_row_2
        1 if page_row_1 should come after page_row_2
        0 if they are equal
        """
        search = self.search_entry.get_text().strip()

        if search != "":
            ratio_1 = self.calc_ratio(page_row_1.page_name, search)
            ratio_2 = self.calc_ratio(page_row_2.page_name, search)
            if ratio_1 != ratio_2:
                return -1 if ratio_1 > ratio_2 else 1

        # Sort alphabetically
        key_1 = self.natural_sort_key(page_row_1.page_name)
        key_2 = self.natural_sort_key(page_row_2.page_name)
        if key_1 == key_2:
            return 0
        return -1 if key_1 < key_2 else 1

    def natural_sort_key(self, page_name: str) -> list[tuple]:
        # Wrap the parts in tuples of the same shape to keep ints and strings comparable
        return [(0, part, "") if isinstance(part, int) else (1, 0, part) for part in natural_keys(page_name)]

    def calc_ratio(self, page_name: str, search: str) -> int:
        page_name = page_name.lower()
        search = search.lower()

        if search in page_name:
            # Prefer earlier matches
            return 200 - page_name.index(search)

        return fuzz.partial_ratio(page_name, search)

    def on_click_open_page_manager(self, button):
        if gl.page_manager_window is not None:
            gl.page_manager_window.present()
        gl.page_manager_window = PageManager(main_win=gl.app.main_win)
        gl.page_manager_window.present()

    def on_click_open_page_settings(self, button):
        self.on_click_open_page_manager(button)

        if self.selected_page_path is None:
            return
        gl.page_manager_window.page_selector.activate_page(self.selected_page_path)


class PageRow(Gtk.ListBoxRow):
    def __init__(self, page_path: str):
        super().__init__()
        self.page_path = page_path
        self.page_name = os.path.splitext(os.path.basename(page_path))[0]

        self.label = Gtk.Label(label=self.page_name, hexpand=True, xalign=0,
                               ellipsize=Pango.EllipsizeMode.END)
        self.set_child(self.label)