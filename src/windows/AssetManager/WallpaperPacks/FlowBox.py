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

# Import python modules
import os
import json

# Import own modules
from src.windows.AssetManager.IconPacks.Preview import IconPackPreview
# Import typing

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.WallpaperPacks.PackChooser import WallpaperPackChooser
    from src.windows.AssetManager.WallpaperPacks.Preview import WallpaperPackPreview

class WallpaperPackFlowBox(Gtk.Box):
    def __init__(self, wallpaper_chooser: "WallpaperPackChooser", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.set_orientation(Gtk.Orientation.HORIZONTAL)
        self.set_hexpand(True)

        self.callback_func = None
        self.callback_args = ()
        self.callback_kwargs = {}

        self.icon_chhoser:"WallpaperPackChooser" = wallpaper_chooser

        self.all_assets:list["WallpaperPackPreview"] = []

        self.build()

    def build(self):
        self.flow_box = Gtk.FlowBox(hexpand=True, orientation=Gtk.Orientation.HORIZONTAL, selection_mode=Gtk.SelectionMode.NONE)
        self.append(self.flow_box)