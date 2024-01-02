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

class ErrorPage(Gtk.Box):
    def __init__(self, main_window):
        super().__init__(halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                         orientation=Gtk.Orientation.VERTICAL)
        self.main_window = main_window

        self.error_label = Gtk.Label(label="Error")
        self.append(self.error_label)

        self.description_label = Gtk.Label(label="No Page Selected")
        self.append(self.description_label)