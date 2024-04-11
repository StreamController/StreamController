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
import threading
import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Gtk, Adw, GLib

# Import own modules
from src.windows.AssetManager.ChooserPage import ChooserPage
from src.windows.AssetManager.WallpaperPacks.Wallpapers.WallpaperFlowBox import WallpaperFlowBox
from src.windows.AssetManager.WallpaperPacks.Wallpapers.WallpaperPreview import WallpaperPreview
from src.windows.AssetManager.IconPacks.Preview import IconPackPreview

# Import python modules
import os
from fuzzywuzzy import fuzz

# Import typing
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from src.windows.AssetManager.AssetManager import AssetManager
    from src.backend.WallpaperPackManagement.WallpaperPack import WallpaperPack

class WallpaperChooserPage(ChooserPage):
    def __init__(self, asset_manager: "AssetManager"):
        super().__init__()
        self.asset_manager = asset_manager

        self.selected_wallpaper: str = None

        # self.build()
        threading.Thread(target=self.build).start()

    def build(self):
        self.set_loading(True)
        
        self.type_box.set_visible(False)

        self.wallpaper_flow = WallpaperFlowBox(WallpaperPreview, self)
        self.wallpaper_flow.set_factory(self.preview_factory)
        self.wallpaper_flow.set_filter_func(self.filter_func)
        self.wallpaper_flow.set_sort_func(self.sort_func)
        # Remove default scrolled window
        self.main_box.remove(self.scrolled_window)
        # Add dynamic flow box
        self.main_box.append(self.wallpaper_flow)

        # Connect flow box select signal
        self.wallpaper_flow.flow_box.connect("child-activated", self.on_child_activated)

        self.set_loading(False)

    def load_for_pack(self, pack: "WallpaperPack"):
        self.wallpaper_flow.set_item_list(pack.get_wallpapers())
        self.wallpaper_flow.show_range(0, 50)

    def select_wallpaper(self, path) -> None:
        self.selected_wallpaper = path

    def on_child_activated(self, flow_box, child):
        self.asset_manager.callback_func(child.wallpaper.path, *self.asset_manager.callback_args, **self.asset_manager.callback_kwargs)
        self.asset_manager.close()
        self.asset_manager.destroy()

    def preview_factory(self, preview: WallpaperPreview, wallpaper):
        preview.set_wallpaper(wallpaper)
        if self.selected_wallpaper == wallpaper.path:
            self.wallpaper_flow.flow_box.select_child(preview)
    
    def filter_func(self, item) -> bool:
        search = self.search_entry.get_text()
        if search == "":
            return True

        file_name = os.path.splitext(os.path.basename(item.path))[0]
        if fuzz.ratio(file_name.lower(), search.lower()) < 50:
            return False
        return True

    def sort_func(self, item1, item2) -> bool:
        # return -1 if child1 should come before child2
        # return 1 if child1 should come after child2
        # return 0 if they are equal
        search = self.search_entry.get_text()
        if search == "":
            # Sort alphabetically
            if os.path.splitext(os.path.basename(item1.path))[0] < os.path.splitext(os.path.basename(item2.path))[0]:
                return -1
            if os.path.splitext(os.path.basename(item1.path))[0] > os.path.splitext(os.path.basename(item2.path))[0]:
                return 1
            return 0
        fuzz1 = fuzz.ratio(os.path.splitext(os.path.basename(item1.path))[0].lower(), search.lower())
        fuzz2 = fuzz.ratio(os.path.splitext(os.path.basename(item2.path))[0].lower(), search.lower())

        if fuzz1 > fuzz2:
            return -1
        elif fuzz1 < fuzz2:
            return 1
        
        return 0
    
    def on_search_changed(self, entry):
        self.wallpaper_flow.show_range(0, 50)