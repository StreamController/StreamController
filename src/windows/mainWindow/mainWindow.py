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
from src.windows.mainWindow.elements.leftArea import LeftArea
from src.windows.mainWindow.elements.rightArea import RightArea
from src.windows.mainWindow.headerBar import HeaderBar

class MainWindow(Gtk.ApplicationWindow):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.set_size_request(1000, 600)
        self.build()

    @log.catch
    def build(self):
        log.trace("Building main window")

        self.mainBox = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True)
        self.set_child(self.mainBox)

        self.mainPaned = Gtk.Paned(orientation=Gtk.Orientation.HORIZONTAL, hexpand=True, vexpand=True, tooltip_text="Resize")
        self.mainBox.append(self.mainPaned)

        self.leftArea = LeftArea(margin_end=3, width_request=500)
        self.mainPaned.set_start_child(self.leftArea)

        self.rightArea = RightArea(margin_start=3, width_request=180)
        self.mainPaned.set_end_child(self.rightArea)

        # Add header bar
        self.headerBar = HeaderBar(self.leftArea.deckStack)
        self.set_titlebar(self.headerBar)