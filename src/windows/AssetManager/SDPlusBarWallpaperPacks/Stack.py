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
from src.windows.AssetManager.SDPlusBarWallpaperPacks.PackChooser import SDPlusBarWallpaperPackChooser
from src.windows.AssetManager.SDPlusBarWallpaperPacks.SDPlusBarWallpaper.SDPlusBarWallpaperChooser import SDPlusBarWallpaperChooserPage

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager

class SDPlusBarWallpaperPackChooserStack(Gtk.Stack):
    def __init__(self, asset_manager: "AssetManager", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.asset_manager = asset_manager

        self.build()

    def build(self):
        self.pack_chooser = SDPlusBarWallpaperPackChooser(self.asset_manager)
        self.add_titled(self.pack_chooser, "pack-chooser", "Chooser")

        self.wallpaper_chooser = SDPlusBarWallpaperChooserPage(self.asset_manager)
        self.add_titled(self.wallpaper_chooser, "wallpaper-chooser", "SD+ Bar Wallpaper Chooser")

    def show_for_path(self, path):
        packs = gl.sd_plus_bar_wallpaper_pack_manager.get_wallpaper_packs()
        for pack in packs.values():
            wallpapers = pack.get_wallpapers()
            for wallpaper in wallpapers:
                if wallpaper.path == path:
                    self.wallpaper_chooser.load_for_pack(pack)
                    self.wallpaper_chooser.select_wallpaper(path=path)
                    self.set_visible_child(self.wallpaper_chooser)
                    self.asset_manager.asset_chooser.set_visible_child_name("sd-plus-bar-wallpaper-packs")
                    self.asset_manager.back_button.set_visible(True)
                    return
