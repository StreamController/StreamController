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
        search_string = self.search_entry.get_text().strip().lower()

        if search_string == "":
            return True

        name = item.name_label.get_text().lower()
        author = item.author_label.get_text().lower()

        name_score = fuzz.ratio(search_string, name)
        author_score = fuzz.ratio(search_string, author)

        MIN_FUZZY_SCORE = 40

        return name_score >= MIN_FUZZY_SCORE or author_score >= MIN_FUZZY_SCORE
    
    def sort_func(self, item_a, item_b):
        search_string = self.search_entry.get_text().strip().lower()

        def get_combined_score(item):
            name = item.name_label.get_text().lower()
            author = item.author_label.get_text().lower()

            name_score = fuzz.ratio(search_string, name)
            author_score = fuzz.ratio(search_string, author)
            return max(name_score, author_score)

        if search_string == "":
            return (item_a.name_label.get_text() > item_b.name_label.get_text()) - \
                (item_a.name_label.get_text() < item_b.name_label.get_text())

        score_a = get_combined_score(item_a)
        score_b = get_combined_score(item_b)

        print((score_b > score_a) - (score_b < score_a))

        return (score_b > score_a) - (score_b < score_a)