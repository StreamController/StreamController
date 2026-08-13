"""
Author: Core447
Year: 2025

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
from src.windows.AssetManager.CustomIconPacks.PackChooser import CustomIconPackChooser
from src.windows.AssetManager.IconPacks.Icons.IconChooser import IconChooserPage
from src.backend.IconPackManagement import CustomIconPack

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.backend.IconPackManagement.IconPack import IconPack


class CustomIconPackChooserStack(Gtk.Stack):
    def __init__(self, asset_manager: "AssetManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_manager = asset_manager

        self.on_loads_finished_tasks: list[callable] = []

        self.build()

    def build(self):
        self.pack_chooser = CustomIconPackChooser(self, self.asset_manager)
        self.add_titled(self.pack_chooser, "pack-chooser", "Chooser")

        self.icon_chooser = IconChooserPage(self, self.asset_manager)
        self.add_titled(self.icon_chooser, "icon-chooser", "Icon Chooser")

    def show_pack(self, pack: "IconPack") -> None:
        self.icon_chooser.load_for_pack(pack)
        self.set_visible_child_name("icon-chooser")
        self.asset_manager.back_button.set_visible(True)

    def show_all_icons(self) -> None:
        self.icon_chooser.load_all_packs()
        self.set_visible_child_name("icon-chooser")
        self.asset_manager.back_button.set_visible(True)

    def show_for_path(self, path):
        if not self.get_is_build_finished():
            self.on_loads_finished_tasks.append(lambda: self.show_for_path(path))
            return

        for pack in CustomIconPack.get_custom_icon_packs().values():
            for icon in pack.get_icons():
                if icon.path == path:
                    self.icon_chooser.select_icon(path=path)
                    self.asset_manager.asset_chooser.set_visible_child_name("custom-asset-packs")
                    self.show_pack(pack)
                    return

    def get_is_build_finished(self):
        return (hasattr(self, "pack_chooser") and self.pack_chooser.build_finished
                and hasattr(self, "icon_chooser") and self.icon_chooser.build_finished)

    def on_load_finished(self):
        if self.get_is_build_finished():
            for task in self.on_loads_finished_tasks.copy():
                task()
                self.on_loads_finished_tasks.remove(task)
