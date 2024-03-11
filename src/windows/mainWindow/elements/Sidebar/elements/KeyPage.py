"""
Author: Core447
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
from gi.repository import Gtk, Adw

# import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.mainWindow.elements.Sidebar.Sidebar import Sidebar

class KeyPage(Gtk.Box):
    def __init__(self, sidebar: "Sidebar"):
        super().__init__(orientation=Gtk.Orientation.VERTICAL)
        self.sidebar = sidebar

    