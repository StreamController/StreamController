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
from src.windows.AssetManager.IconPacks.Icons.IconChooser import IconChooser

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager

class IconPackChooserStack(Gtk.Stack):
    def __init__(self, asset_manager: "AssetManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_manager = asset_manager

        self.build()

    def build(self):
        self.pack_chooser = IconPackChooser(self.asset_manager)
        self.add_titled(self.pack_chooser, "chooser", "Chooser")

        self.icon_chooser = IconChooserPage(self.asset_manager)
        self.add_titled(self.icon_chooser, "icon-chooser", "Icon Chooser")

        