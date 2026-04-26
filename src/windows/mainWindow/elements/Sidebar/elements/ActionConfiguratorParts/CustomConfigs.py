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
from gi.repository import Gtk


class CustomConfigs(Gtk.Box):
    def __init__(self, parent, **kwargs):
        super().__init__(orientation=Gtk.Orientation.VERTICAL, **kwargs)
        self.parent = parent

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.append(self.main_box)

    def load_for_action(self, action):
        # Append custom config area
        custom_config_area = action.get_custom_config_area()
        
        if custom_config_area is None:
            self.hide()
            return

        # Clear
        self.clear()

        # Append custom content
        self.main_box.append(custom_config_area)

        # Show
        self.show()

    def clear(self):
        while self.main_box.get_first_child() is not None:
            self.main_box.remove(self.main_box.get_first_child())
