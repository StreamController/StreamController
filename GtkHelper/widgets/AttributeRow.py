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

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


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
