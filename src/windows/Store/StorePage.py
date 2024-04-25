"""
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
from gi.repository import Gtk, GLib

# Import python modules
from fuzzywuzzy import fuzz
import threading
from loguru import logger as log

# Import own modules
from src.windows.Store.InfoPage import InfoPage
from GtkHelper.GtkHelper import ErrorPage
from src.windows.Store.NoConnectionError import NoConnectionError
from packaging import version

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store

# Import globals
import globals as gl

class StorePage(Gtk.Stack):
    def __init__(self, store: "Store"):
        super().__init__()
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_margin_start(15)
        self.set_margin_end(15)
        self.set_margin_top(15)
        self.set_margin_bottom(15)
        self.set_transition_duration(200)
        self.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)

        self.store = store

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.add_titled(self.main_box, "Store", "Store")

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.main_box.append(self.nav_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search", hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.nav_box.append(self.search_entry)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True)
        self.main_box.append(self.scrolled_window)

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True)
        self.scrolled_window.set_child(self.scrolled_box)

        self.flow_box = Gtk.FlowBox(orientation=Gtk.Orientation.HORIZONTAL, selection_mode=Gtk.SelectionMode.NONE, homogeneous=True)
        self.flow_box.set_filter_func(self.filter_func)
        self.flow_box.set_sort_func(self.sort_func)
        self.scrolled_box.append(self.flow_box)

        self.loading_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                                   visible=False, valign=Gtk.Align.CENTER)
        self.scrolled_box.append(self.loading_box)

        self.spinner = Gtk.Spinner(spinning=False)
        self.loading_box.append(self.spinner)

        self.loading_text = Gtk.Label(label=gl.lm.get("store.page.loading-spinner.label"))
        self.loading_box.append(self.loading_text)

        # Add vexpand box to the bottom to avoid unwanted stretching of the flowbox children
        self.bottom_box = Gtk.Box(hexpand=True, vexpand=True)
        self.scrolled_box.append(self.bottom_box)

        # Info page
        self.info_page = InfoPage(self)
        self.add_titled(self.info_page, "Info", "Info")

        # Error page
        self.no_connection_page = NoConnectionError()
        self.add_titled(self.no_connection_page, "Error", "Error")

    def on_search_changed(self, entry: Gtk.SearchEntry):
        self.flow_box.invalidate_filter()
        self.flow_box.invalidate_sort()

    def filter_func(self, item):
        """
        Filters the given item based on the search string and their number of github stars.

        Parameters:
            item (object): The item to be filtered.

        Returns:
            bool: True if the item passes the filter, False otherwise.
        """
        search_string = self.search_entry.get_text()

        if search_string == "":
            return True
        
        item_name = item.name_label.get_text()
        
        fuzz_ratio = fuzz.ratio(search_string.lower(), item_name.lower())

        MIN_FUZZY_SCORE = 40

        return fuzz_ratio >= MIN_FUZZY_SCORE
    
    def sort_func(self, item_a, item_b):
        search_string = self.search_entry.get_text()

        if search_string == "":
            if  item_a.name_label.get_text() < item_b.name_label.get_text():
                return -1
            if item_a.name_label.get_text() > item_b.name_label.get_text():
                return 1
            return 0

            # Sort by stars - currently not used
            if item_a.stars > item_b.stars:
                return -1
            if item_a.stars < item_b.stars:
                return 1
            return 0
        
        item_a_fuzz = fuzz.ratio(search_string.lower(), item_a.name_label.get_text().lower())
        item_b_fuzz = fuzz.ratio(search_string.lower(), item_b.name_label.get_text().lower())

        # Set to 0 because stars are currently disabled for api rate limit reasons
        item_a_stars = 0 # item_a.stars/item_b.stars
        item_b_stars = 0 # item_a.stars/item_b.stars

        if item_a_stars > 1 or item_b_stars > 1:
            item_a_stars = item_b.stars/item_a.stars
            item_b_stars = item_b.stars/item_a.stars

        total_a = (item_a_fuzz + item_a_stars)/2
        total_b = (item_b_fuzz + item_b_stars)/2

        if total_a > total_b:
            return -1
        if total_a < total_b:
            return 1
        return 0
    
    def set_loading(self):
        GLib.idle_add(self.flow_box.set_visible, False)
        GLib.idle_add(self.bottom_box.set_visible, False)
        GLib.idle_add(self.loading_box.set_visible, True)
        # threading.Thread(target=self.spinner.set_spinning, args=(True,), name="spinner_thread").start()
        GLib.idle_add(self.spinner.set_spinning, True)

    def set_loaded(self):
        GLib.idle_add(self.flow_box.set_visible, True)
        GLib.idle_add(self.bottom_box.set_visible, True)
        GLib.idle_add(self.loading_box.set_visible, False)
        GLib.idle_add(self.spinner.set_spinning, False)

    def set_info_visible(self, visible:bool):
        if visible:
            self.set_visible_child(self.info_page)
            self.store.back_button.set_visible(True)
        else:
            self.set_visible_child(self.main_box)
            self.store.back_button.set_visible(False)

    def show_connection_error(self):
        self.set_visible_child(self.no_connection_page)

    def hide_connection_error(self):
        self.set_visible_child(self.main_box)

    def check_required_version(self, app_version_to_check: str, is_min_app_version: bool = False):
        if is_min_app_version:
            if app_version_to_check is None:
                return True
            min_version = version.parse(app_version_to_check)
            app_version = version.parse(gl.app_version)

            return min_version < app_version