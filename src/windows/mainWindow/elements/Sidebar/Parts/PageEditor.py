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

from src.windows.mainWindow.elements.Sidebar.Parts.Pages import PagesGroup

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk


class PageEditor(Gtk.Box):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.clamp = Adw.Clamp()
        self.set_margin_top(40)
        self.append(self.clamp)

        self.main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, hexpand=True)
        self.clamp.set_child(self.main_box)

        self.pages_group = PagesGroup()
        self.main_box.append(self.pages_group)
