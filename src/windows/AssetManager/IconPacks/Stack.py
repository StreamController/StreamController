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

# Import own modules
from src.windows.AssetManager.IconPacks.PackChooser import IconPackChooser
from src.windows.AssetManager.IconPacks.Icons.IconChooser import IconChooserPage

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager

class IconPackChooserStack(Gtk.Stack):
    def __init__(self, asset_manager: "AssetManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_manager = asset_manager

        self.on_loads_finished_tasks: list[callable] = []

        self.build()

    def build(self):
        self.pack_chooser = IconPackChooser(self, self.asset_manager)
        self.add_titled(self.pack_chooser, "pack-chooser", "Chooser")

        self.icon_chooser = IconChooserPage(self, self.asset_manager)
        self.add_titled(self.icon_chooser, "icon-chooser", "Icon Chooser")


    def show_for_path(self, path):
        if not self.get_is_build_finished():
            self.on_loads_finished_tasks.append(lambda: self.show_for_path(path))
            return
        packs = gl.icon_pack_manager.get_icon_packs()
        for pack in packs.values():
            icons = pack.get_icons()
            for icon in icons:
                if icon.path == path:
                    self.icon_chooser.load_for_pack(pack)
                    self.icon_chooser.select_icon(path=path)
                    self.set_visible_child(self.icon_chooser)
                    self.asset_manager.asset_chooser.set_visible_child_name("icon-packs")
                    self.asset_manager.back_button.set_visible(True)
                    return
                
    def get_is_build_finished(self):
        return self.pack_chooser.build_finished and self.icon_chooser.build_finished
                
    def on_load_finished(self):
        if self.get_is_build_finished():
            for task in self.on_loads_finished_tasks.copy():
                task()
                self.on_loads_finished_tasks.remove(task)