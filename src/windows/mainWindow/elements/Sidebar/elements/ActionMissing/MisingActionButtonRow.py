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

from src.windows.mainWindow.elements.Sidebar.elements.ActionMissing.MissingRow import MissingRow

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, Gdk, GLib, Pango

import globals as gl

class MissingActionButtonRow(MissingRow):
    def __init__(self, action_id:str, page_coords:str, index:int):
        super().__init__(
            action_id=action_id,
            page_coords=page_coords,
            index=index,
            install_label="Install missing plugin",
            install_failed_label="Install failed",
            installing_label="Installing..."
        )