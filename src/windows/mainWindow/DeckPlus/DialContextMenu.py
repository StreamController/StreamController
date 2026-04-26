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
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Gio, Gtk

if TYPE_CHECKING:
    from src.windows.mainWindow.DeckPlus.Dial import Dial


class DialContextMenu(Gtk.PopoverMenu):
    def __init__(self, dial: "Dial", **kwargs):
        super().__init__(**kwargs)
        self.dial = dial
        self.build()

        self.connect("closed", self.on_close)

    def build(self):
        self.set_has_arrow(False)

        self.main_menu = Gio.Menu.new()

        self.copy_paste_menu = Gio.Menu.new()
        self.remove_menu = Gio.Menu.new()

        # Add actions to menus
        self.copy_paste_menu.append("Copy", "dial.copy")
        self.copy_paste_menu.append("Cut", "dial.cut")
        self.copy_paste_menu.append("Paste", "dial.paste")
        self.remove_menu.append("Remove", "dial.remove")
        self.remove_menu.append("Update", "dial.update")

        # Add sections to menu
        self.main_menu.append_section(None, self.copy_paste_menu)
        self.main_menu.append_section(None, self.remove_menu)

        self.set_menu_model(self.main_menu)

    def popup(self):
        """Override popup to set parent just before showing"""
        if self.dial and not self.get_parent():
            self.set_parent(self.dial)
        super().popup()

    def on_close(self, *args, **kwargs):
        return
    
    def on_open(self, *args, **kwargs):
        return
