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
import gi
from loguru import logger as log

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


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
        rows = self.get_rows()
        list_box = self.get_list_box()
        list_box.remove_all()
        for row in rows:
            row = None
            del row
        del rows

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

    def get_index_of_child(self, child):
        for i, action in enumerate(self.actions):
            if action == child:
                return i

        raise ValueError("Child not found")

    def get_arrow_image(self) -> Gtk.Image:
        box: Gtk.Box = self.get_child()
        list_box: Gtk.ListBox = box.get_first_child()

        adw_action_row: Adw.ActionRow = list_box.get_first_child()
        box: Gtk.Box = adw_action_row.get_child()

        box: Gtk.Box = box.get_last_child()
        image: Gtk.Image = box.get_last_child()

        return image
