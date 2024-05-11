"""
Year: 2024

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
any later version.

This programm comes with ABSOLUTELY NO WARRANTY!

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>.
"""

import gi
from gi.repository import Gtk, Adw

from fuzzywuzzy import fuzz

class StorePageSection(Gtk.Stack):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.add_named(self.main_box, "main")

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

        # Add vexpand box to the bottom to avoid unwanted stretching of the flowbox children
        self.bottom_box = Gtk.Box(hexpand=True, vexpand=True)
        self.scrolled_box.append(self.bottom_box)

        # Nothing here box
        self.nothing_here = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True, vexpand=True,
                                        halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
        self.nothing_here = Adw.StatusPage(
            title="Nothing here",
            icon_name="face-sad-symbolic"
        )
        self.add_named(self.nothing_here, "nothing")

        self.set_visible_child(self.nothing_here)

    def append_child(self, item):
        self.flow_box.append(item)
        self.set_visible_child(self.main_box)

    def on_search_changed(self, search_entry):
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