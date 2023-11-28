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

    def get_list_box(self) -> Gtk.ListBox:
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

    def reorder_child_after(self, child, after):
        childs = self.get_rows()
        after_index = childs.index(after)

        if after_index is None:
            log.warning("After child could not be found. Please add it first")
            return
        
        # Remove child from list
        childs.remove(child)

        # Add child in new position
        childs.insert(after_index, child)

        # Remove all childs
        self.clear()

        # Add all childs in new order
        for child in childs:
            self.add_row(child)

    def remove_child(self, child:Gtk.Widget) -> None:
        self.get_list_box().remove(child)


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
    
class AttributeRow(Adw.PreferencesRow):
    def __init__(self, title:str, attr:str, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.title = title
        self.attr_str = attr
        self.build()

    def build(self):
        self.main_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True,
                                margin_top=15, margin_bottom=15)
        self.set_child(self.main_box)

        self.title_label = Gtk.Label(label=self.title, xalign=0, hexpand=True, margin_start=15)
        self.main_box.append(self.title_label)

        self.attribute_label = Gtk.Label(label=self.attr_str, halign=0, margin_end=15)
        self.main_box.append(self.attribute_label)

    def set_title(self, title:str):
        self.title_label.set_label(title)

    def set_url(self, attr:str):
        if attr is None:
            attr = "N/A"
        self.attribute_label.set_label(attr)