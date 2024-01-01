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
from gi.repository import Gtk, GLib

# Import python modules
from loguru import logger as log
import threading
from functools import cmp_to_key

class DynamicFlowBox(Gtk.Box):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.start_index = 0
        self.N_ITEMS_PER_PAGE = 50

        self.all_items: list = []
        self.filtered_items: list = []
        self.sorted_items: list = []

        self.factory:callable = None
        self.filter:callable = None
        self.sort:callable = None
        
        self.build()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True, margin_bottom=10)
        self.append(self.scrolled_window)

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.scrolled_window.set_child(self.scrolled_box)

        self.flow_box = Gtk.FlowBox(orientation=Gtk.Orientation.HORIZONTAL)
        self.scrolled_box.append(self.flow_box)

        # Fix stretching of flow_box children
        self.scrolled_box.append(Gtk.Box(vexpand=True))

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.append(self.nav_box)

        self.prev_button = Gtk.Button(label="Go Back", sensitive=False)
        self.prev_button.connect("clicked", self.on_prev)
        self.nav_box.append(self.prev_button)

        self.nav_box.append(Gtk.Box(hexpand=True))

        self.next_button = Gtk.Button(label="Go Next")
        self.next_button.connect("clicked", self.on_next)
        self.nav_box.append(self.next_button)


    def load_items(self):
        start = self.start_index
        end = self.start_index + self.N_ITEMS_PER_PAGE

        self.load_list(self.get_list_to_load()[start:end])

    def get_list_to_load(self) -> list:
        if self.filter is not None:
            return self.filtered_items
        if self.sort is not None:
            return self.sorted_items

        return self.all_items

    def add_item(self, item, invalidate_filter: bool = False):
        self.all_items.append(item)
        if invalidate_filter:
            self.invalidate_filter()

    def load_list(self, items):
        # self.remove_all()
        while self.flow_box.get_first_child() is not None:
            child = self.flow_box.get_first_child()
            if hasattr(child, "disconnect_signals"):
                child.disconnect_signals()
            self.flow_box.remove(child)

        for item in items:
            widget = self.get_item_widget(item)
            if widget is None:
                continue
            self.flow_box.append(widget)

    def get_item_widget(self, item) -> Gtk.Widget:
        if callable(self.factory):
            return self.factory(item)
        
    def set_factory(self, factory: callable):
        if not callable(factory):
            log.warning("Chosen factory is not callable")
            return
        self.factory = factory

    def on_next(self, button):
        self.start_index += self.N_ITEMS_PER_PAGE
        self.start_index = min(self.start_index, len(self.all_items) - self.N_ITEMS_PER_PAGE)
        self.load_items()

        # Set sensitivity
        self.prev_button.set_sensitive(self.start_index > 0)
        self.next_button.set_sensitive(self.start_index + self.N_ITEMS_PER_PAGE < len(self.get_list_to_load()))

    def on_prev(self, button):
        self.start_index -= self.N_ITEMS_PER_PAGE
        self.start_index = max(0, self.start_index)
        self.load_items()

        # Set sensitivity
        self.prev_button.set_sensitive(self.start_index > 0)
        self.next_button.set_sensitive(self.start_index + self.N_ITEMS_PER_PAGE < len(self.get_list_to_load()))

    def invalidate_filter(self):
        self.filtered_items = []
        for item in self.all_items:
            if not callable(self.filter):
                pass 
            elif not self.filter(item):
                continue
            self.filtered_items.append(item)
        self.load_items()

    def invalidate_sort(self):
        if not callable(self.sort):
            self.sorted_items = self.filtered_items
        self.sorted_items = sorted(self.filtered_items, key=cmp_to_key(self.sort))
        


    def set_filter_func(self, filter: callable) -> None:
        if not callable(filter):
            log.warning("Chosen filter is not callable")
            return
        self.filter = filter
        self.invalidate_filter()

    def set_sort_func(self, sort: callable) -> None:
        if not callable(sort):
            log.warning("Chosen sort function is not callable")
            return
        self.sort = sort