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
from gi.repository import Gtk, Adw

# Import Python modules
from loguru import logger as log


class BetterExpander(Adw.ExpanderRow):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def set_sort_func(self, *args, **kwargs):
        revealer_list_box = self.get_list_box()
        revealer_list_box.set_sort_func(*args, **kwargs)

    def set_filter_func(self, *args, **kwargs):
        revealer_list_box = self.get_list_box()
        revealer_list_box.set_filter_func(*args, **kwargs)

    def invalidate_filter(self):
        list_box = self.get_list_box()
        list_box.invalidate_filter()

    def invalidate_sort(self):
        list_box = self.get_list_box()
        list_box.invalidate_sort()

    def get_rows(self):
        revealer_list_box = self.get_list_box()
        if revealer_list_box is None:
            return
        
        rows = []
        child = revealer_list_box.get_first_child()
        while child is not None:
            rows.append(child)
            child = child.get_next_sibling()

        return rows

    def get_list_box(self):
        expander_box = self.get_first_child()
        if expander_box is None:
            return
        
        expander_list_box = expander_box.get_first_child()
        if expander_list_box is None:
            return
        
        revealer = expander_list_box.get_next_sibling()
        revealer_list_box = revealer.get_first_child()

        return revealer_list_box
        
    def clear(self):
        revealer_list_box = self.get_list_box()
        revealer_list_box.remove_all()

class BetterPreferencesGroup(Adw.PreferencesGroup):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clear(self):
        list_box = self.get_list_box()
        list_box.remove_all()

    def set_sort_func(self, *args, **kwargs):
        list_box = self.get_list_box()
        list_box.set_sort_func(*args, **kwargs)

    def set_filter_func(self, *args, **kwargs):
        list_box = self.get_list_box()
        list_box.set_filter_func(*args, **kwargs)

    def invalidate_filter(self):
        list_box = self.get_list_box()
        list_box.invalidate_filter()

    def invalidate_sort(self):
        list_box = self.get_list_box()
        list_box.invalidate_sort()

    def get_rows(self):
        list_box = self.get_list_box()
        if list_box is None:
            return
        
        rows = []
        child = list_box.get_first_child()
        while child is not None:
            rows.append(child)
            child = child.get_next_sibling()

        return rows

    def get_list_box(self):
        first_box = self.get_first_child()
        second_box = first_box.get_first_child()
        third_box = second_box.get_next_sibling()
        list_box = third_box.get_first_child()

        return list_box