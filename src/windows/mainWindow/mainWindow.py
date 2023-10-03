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

# Import own modules
from src.windows.mainWindow.elements.leftStack import LeftStack

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.build()

    @log.catch
    def build(self):
        log.trace("Building main window")
        # Demo
        self.mainBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.mainBox)

        self.paned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL)
        self.mainBox.append(self.paned)

        self.paned.set_start_child(LeftStack(hexpand=True, margin_end=3, width_request=500))
        self.paned.set_end_child(Gtk.Button(label="hello world", hexpand=True, margin_start=3, width_request=100))