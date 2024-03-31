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
# Import gtk modules
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Gdk, GLib

# Import python modules
import functools

class DynamicFlowBox(Gtk.Box):
    def __init__(self, base_class: type, *args, **kwargs):
        """
        base_class: The class of the items in the flow box. Its constructor is not allowed to require any arguments because empty
                    placeholder objects will be created in the flowbox.
                    You have to use the factory to configure the items.
        """
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.VERTICAL)

        self.N_ITEMS_PER_PAGE = 50

        self.base_class = base_class
        self.items: list = []

        self.sort_func: callable = None
        self.filter_func: callable = None
        self.factory_func: callable = None

        self.build()

        self.generate_placeholders()

    def build(self):
        self.scrolled_window = Gtk.ScrolledWindow(hexpand=True, vexpand=True)
        self.append(self.scrolled_window)

        self.scrolled_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        self.scrolled_window.set_child(self.scrolled_box)

        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL,
                                    selection_mode=Gtk.SelectionMode.SINGLE)
        self.scrolled_box.append(self.flow_box)

        # Fix stretch
        self.scrolled_box.append(Gtk.Box(vexpand=True))

        self.nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                               margin_top=15, margin_bottom=15, margin_start=15, margin_end=15)
        self.append(self.nav_box)

        self.back_button = Gtk.Button(icon_name="com.core447.StreamController-go-previous-symbolic")
        self.back_button.connect("clicked", self.on_back)
        self.nav_box.append(self.back_button)

        self.nav_box.append(Gtk.Box(hexpand=True))

        self.next_button = Gtk.Button(icon_name="com.core447.StreamController-go-next-symbolic")
        self.next_button.connect("clicked", self.on_next)
        self.nav_box.append(self.next_button)

    def generate_placeholders(self):
        for i in range(self.N_ITEMS_PER_PAGE):
            placeholder = self.base_class()
            self.flow_box.append(placeholder)


    def filter_items(self, items: list):
        if not callable(self.filter_func):
            return items
        
        filtered_items = []
        for item in items:
            if self.filter_func(item):
                filtered_items.append(item)
        return filtered_items

    def sort_items(self, items: list):
        if not callable(self.sort_func):
            return items
        
        return sorted(items, key=functools.cmp_to_key(self.sort_func))


    def get_items_to_show(self) -> list:
        filtered_items = self.filter_items(self.items)
        sorted_items = self.sort_items(filtered_items)
        return sorted_items
    

    def show_range(self, start: int, end: int) -> None:
        if not callable(self.factory_func):
            raise ValueError("factory_func must be callable")
        
        items = self.get_items_to_show()

        self.current_start_index = start

        for i, item in enumerate(items[start:end]):
            preview = self.flow_box.get_child_at_index(i)
            if preview is None:
                return
            
            preview.set_visible(True)
            # self.factory_func(preview, item)
            GLib.idle_add(self.factory_func, preview, item)

        # Hide left over placeholders
        for i in range(len(items[start:end]), self.N_ITEMS_PER_PAGE):
            preview = self.flow_box.get_child_at_index(i)
            if preview is None:
                return
            preview.set_visible(False)

        if start == 0:
            self.back_button.set_sensitive(False)
        else:
            self.back_button.set_sensitive(True)

        if end < len(items):
            self.next_button.set_sensitive(True)
        else:
            self.next_button.set_sensitive(False)


    def on_next(self, *args):
        self.current_start_index += self.N_ITEMS_PER_PAGE
        self.show_range(self.current_start_index, self.current_start_index + self.N_ITEMS_PER_PAGE)

    def on_back(self, *args):
        self.current_start_index -= self.N_ITEMS_PER_PAGE
        self.show_range(self.current_start_index, self.current_start_index + self.N_ITEMS_PER_PAGE)


    def set_item_list(self, items: list) -> None:
        self.items = items

    def set_factory(self, factory_func: callable) -> None:
        self.factory_func = factory_func

    def set_sort_func(self, sort_func: callable) -> None:
        self.sort_func = sort_func

    def set_filter_func(self, filter_func: callable) -> None:
        self.filter_func = filter_func