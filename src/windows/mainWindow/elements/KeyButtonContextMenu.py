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
from typing import TYPE_CHECKING

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gio, Gtk

if TYPE_CHECKING:
    from src.windows.mainWindow.elements.KeyButton import KeyButton


class KeyButtonContextMenu(Gtk.PopoverMenu):
    def __init__(self, key_button: "KeyButton", **kwargs):
        super().__init__(**kwargs)
        self.key_button = key_button
        self.build()

        self.connect("closed", self.on_close)

        # gl.app.set_accels_for_action("context.test", ["<Primary>t"])

    def on_test(self, *args, **kwargs):
        pass

    def build(self):
        self.set_parent(self.key_button)
        self.set_has_arrow(False)

        self.main_menu = Gio.Menu.new()

        self.copy_paste_menu = Gio.Menu.new()
        self.remove_menu = Gio.Menu.new()

        # Add actions to menus
        self.copy_paste_menu.append("Copy", "key.copy")
        self.copy_paste_menu.append("Cut", "key.cut")
        self.copy_paste_menu.append("Paste", "key.paste")
        self.remove_menu.append("Remove", "key.remove")
        self.remove_menu.append("Update", "key.update")

        # Add sections to menu
        self.main_menu.append_section(None, self.copy_paste_menu)
        self.main_menu.append_section(None, self.remove_menu)

        self.set_menu_model(self.main_menu)

    def on_close(self, *args, **kwargs):
        return
        gl.app.main_win.remove_accel_actions()
    
    def on_open(self, *args, **kwargs):
        return
        gl.app.main_win.add_accel_actions()
