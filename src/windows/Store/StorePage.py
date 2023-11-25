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
from gi.repository import Gtk

# Typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.Store.Store import Store

class StorePage(Gtk.Box):
    def __init__(self, store: "Store"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.set_margin_start(15)
        self.set_margin_end(15)
        self.set_margin_top(15)
        self.set_margin_bottom(15)

        self.store = store

        self.build()

    def build(self):
        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, margin_bottom=15)
        self.append(self.nav_box)

        self.search_entry = Gtk.SearchEntry(placeholder_text="Search", hexpand=True)
        self.search_entry.connect("search-changed", self.on_search_changed)
        self.nav_box.append(self.search_entry)

        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True)
        self.append(self.scrolled_window)

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.scrolled_window.set_child(self.scrolled_box)

        self.flow_box = Gtk.FlowBox(orientation=Gtk.Orientation.HORIZONTAL)
        self.scrolled_box.append(self.flow_box)

        # Add vexpand box to the bottom to avoid unwanted stretching of the flowbox children
        self.scrolled_box.append(Gtk.Box(hexpand=True, vexpand=True))

    def on_search_changed(self, entry: Gtk.SearchEntry):
        pass