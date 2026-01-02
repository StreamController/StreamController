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
from gi.repository import Gtk, Adw, GLib

# Import own modules
from src.windows.AssetManager.Preview import Preview

# Import python modules
import os

# Import globals
import globals as gl

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.backend.SDPlusBarWallpaperPackManagement.SDPlusBarWallpaper import SDPlusBarWallpaper

class SDPlusBarWallpaperPreview(Preview):
    def __init__(self):
        super().__init__()

        self.wallpaper: "SDPlusBarWallpaper" = None

    def on_click_info(self, *args):
        gl.app.asset_manager.show_info(
            internal_path = self.wallpaper.path,
            licence_name = self.wallpaper.get_attribution().get("license"),
            license_url = self.wallpaper.get_attribution().get("license-url"),
            author = self.wallpaper.get_attribution().get("copyright"),
            license_comment = self.wallpaper.get_attribution().get("comment"),
            original_url = self.wallpaper.get_attribution().get("original-url")
        )

    def set_wallpaper(self, icon: "SDPlusBarWallpaper") -> None:
        self.wallpaper = icon

        GLib.idle_add(self.set_text, os.path.splitext(os.path.basename(self.wallpaper.path))[0])
        GLib.idle_add(self.set_image, self.wallpaper.path)

